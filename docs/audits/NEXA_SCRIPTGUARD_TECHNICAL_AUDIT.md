# Auditoría técnica integral de NEXA ScriptGuard

**Fecha:** 2026-11-20<br>
**Base:** `main`, commit `8baf765`; árbol de trabajo con cambios preexistentes.<br>
**Alcance:** implementación Python y prototipo Rust existentes en el árbol de trabajo, reglas, pruebas, documentación, manifiestos y workflows del repositorio. No se modificaron motores ni reglas.

## 1. Resumen ejecutivo

NEXA ScriptGuard es un **prototipo experimental de análisis estático heurístico**, no un analizador semántico completo de Bash ni un límite de seguridad. Python aplica cinco reglas regex a líneas físicas y dos correlaciones limitadas de variables; Rust es un ejecutable independiente con dos búsquedas de cadenas. Ninguno ejecuta intencionalmente el script analizado. Un resultado sin hallazgos no demuestra que un script sea seguro.

Las brechas más importantes son:

1. **Integridad de entrada:** se comprobó que una salida Python cuyo archivo es un enlace duro al archivo analizado sobrescribe este último, pese a la validación de rutas. Esto contradice la expectativa de análisis de solo lectura.
2. **Exactitud:** no existe un parser Bash real. Cadenas literales, comentarios en línea y heredocs producen falsos positivos; continuaciones, variantes sintácticas y flujo entre variables producen falsos negativos.
3. **Confidencialidad:** `--redact` es opcional, solo cubre ciertos patrones y campos, y se comprobó que deja intacto un valor sintético de autorización Bearer. Rust imprime líneas completas sin redacción.
4. **Disponibilidad:** el límite de entrada de 5 MiB no limita el número ni el tamaño acumulado de hallazgos o reportes. En una prueba de 802 bytes se generaron 100 hallazgos y 123.305 bytes de JSON.
5. **Trazabilidad e interoperabilidad:** las correlaciones no incluyen evidencia de origen ni cadena de flujo; sus IDs aparecen en resultados SARIF pero no en el catálogo de reglas del driver. Los formatos no exponen los mismos datos.
6. **Madurez:** no hay integración entre motores, fuzzing, análisis de concurrencia, corpus de exactitud ni validación integral de SARIF. La suite existente es útil como smoke test, no como certificación de cobertura.

**Recomendación:** mantener la etiqueta alfa y no utilizar el resultado como única barrera de seguridad. Priorizar integridad, privacidad y límites antes de ampliar detecciones o integrar motores.

## 2. Alcance, método y límites de la comparación

Se revisaron línea por línea [`__main__.py`](../../nexa_scriptguard/__main__.py), [`contextual.py`](../../nexa_scriptguard/contextual.py), [`bash.json`](../../nexa_scriptguard/bash.json), [`main.rs`](../../rust/nexa-scriptguard-helper/src/main.rs) y [`test_scanner.py`](../../tests/test_scanner.py), además de README, política de seguridad, manifiestos y workflows. Se realizaron pruebas focalizadas con archivos temporales y entradas sintéticas; **ningún script de muestra fue ejecutado**.

La arquitectura acordada en la conversación anterior no está disponible en los materiales accesibles de esta sesión. El [README](../../README.md) sí declara el alcance alfa y que una versión local más amplia aún no está sincronizada. Por lo tanto, la matriz compara el código con las capacidades pedidas en esta solicitud y con lo que el repositorio documenta, **no certifica diferencias contra un documento arquitectónico anterior no accesible**. Tampoco se verificó la existencia o el contenido de aquella versión local.

Clasificación: **implementado** significa presente en el alcance descrito, no completo para todos los casos; **parcial** indica cobertura o garantías limitadas; **pendiente** significa no encontrado en el código revisado. Las severidades de los hallazgos de esta auditoría indican prioridad de ingeniería, no son las severidades emitidas por las reglas del producto.

## 3. Arquitectura y recorrido real

### Python

1. La CLI resuelve y verifica el archivo y compara rutas de salida ([`__main__.py:121`](../../nexa_scriptguard/__main__.py#L121)); carga reglas JSON locales.
2. `inspect` lee hasta 5 MiB + 1 byte, rechaza exceso, decodifica UTF-8 con reemplazo, separa líneas y aplica cada regex a cada línea no vacía que no comienza por `#` ([`__main__.py:17`](../../nexa_scriptguard/__main__.py#L17)).
3. `correlated_findings` une algunas continuaciones y mantiene asignaciones textuales de variables en un diccionario; hace una sustitución textual por referencias y prueba dos combinaciones de patrones ([`contextual.py:11`](../../nexa_scriptguard/contextual.py#L11), [`contextual.py:24`](../../nexa_scriptguard/contextual.py#L24)).
4. Ordena por severidad, línea y columna; calcula SHA-256 sobre los bytes leídos y registra fecha UTC ([`__main__.py:35`](../../nexa_scriptguard/__main__.py#L35)).
5. Opcionalmente redacta una copia; luego imprime y escribe los formatos pedidos. `--fail-on` devuelve 2 si se alcanza el umbral ([`__main__.py:141`](../../nexa_scriptguard/__main__.py#L141)).

### Rust

`read_bounded` limita la lectura a 5 MiB + 1 y exige UTF-8 válido. `flags` busca dos combinaciones literales por línea; `run` imprime ruta, número, identificador y texto, más un resumen ([`main.rs:11`](../../rust/nexa-scriptguard-helper/src/main.rs#L11)). Hallazgos no alteran el código de salida; errores de lectura y uso incorrecto devuelven 2. No hay parser, hash, reportes estructurados, redacción, gravedad, confianza ni invocación desde Python. El README identifica correctamente la independencia de los motores.

## 4. Hallazgos técnicos priorizados

### A-01 — Alto: sobrescritura de entrada por alias de archivo

- **Evidencia:** se comparan rutas resueltas, no la identidad del archivo ([`__main__.py:130`](../../nexa_scriptguard/__main__.py#L130)); las salidas se abren con `write_text` ([`__main__.py:155`](../../nexa_scriptguard/__main__.py#L155)).
- **Reproducción observada:** en un directorio temporal se creó un enlace duro de la entrada como destino `--json`; la CLI devolvió 0 y la entrada pasó a contener JSON. No se ejecutó el contenido de entrada.
- **Impacto:** pérdida de datos si se elige o presenta como salida otro nombre del mismo archivo. También son relevantes colisiones entre salidas y carreras de reemplazo entre validación y apertura; estas últimas no fueron explotadas en la prueba.
- **Dirección:** comprobar identidad de archivos existentes, prevenir alias y diseñar apertura/escritura segura frente a enlaces y carreras en cada plataforma; definir política explícita para sobrescritura y fallos parciales. `resolve()` por sí solo no resuelve enlaces duros ni TOCTOU.

### A-02 — Alto: redacción no garantiza confidencialidad

- **Evidencia:** la regex de [`__main__.py:15`](../../nexa_scriptguard/__main__.py#L15) cubre nombres como `password`, `api_key`, `secret` y `token` seguidos de `=` o `:`; [`redact_report`](../../nexa_scriptguard/__main__.py#L43) actúa solo sobre instrucción, fragmento y contexto. La ruta y el hash permanecen, al igual que cualquier secreto en otros campos.
- **Reproducción observada:** `Authorization: Bearer synthetic_secret_123` en una línea con hallazgo sigue presente en el JSON serializado tras `redact_report`. El valor es sintético.
- **Impacto:** filtración por terminal o archivos al asumir que `--redact` sanitiza todo. El contexto en JSON también puede incorporar líneas vecinas sensibles. El hash del archivo original no es una redacción: puede permitir comprobar candidatos cuando la entrada es predecible.
- **Alcance:** README y SECURITY ya advierten que la redacción es limitada; no debe interpretarse esta observación como garantía previamente prometida. Rust imprime instrucciones completas y carece de opción de redacción ([`main.rs:41`](../../rust/nexa-scriptguard-helper/src/main.rs#L41)).

### A-03 — Alto: no existe parsing sintáctico ni análisis de flujo fiable

- **Evidencia:** reglas sobre líneas físicas ([`__main__.py:24`](../../nexa_scriptguard/__main__.py#L24)); sustitución textual sin AST, ámbitos ni grafo de control ([`contextual.py:24`](../../nexa_scriptguard/contextual.py#L24)).
- **Observado:** se detecta `SG-001` dentro de `echo "curl ... | bash"`, de un comentario en línea y del cuerpo de un heredoc. Una descarga seguida de `| bash` en otra línea con continuación no produce hallazgo. `curl ... | sudo bash` tampoco.
- **Observado:** `A="curl ..."; B=$A; $B | bash` distribuido en líneas no produce correlación; una reasignación dentro de `if false` puede borrar el valor útil; `echo "$A | bash"` produce `SG-FLOW-001` pese a ser texto citado. La sustitución no demuestra que datos de red lleguen realmente al intérprete.
- **Impacto:** falsos positivos y negativos, incluso en los escenarios principales del producto. La frase de flujo «termina ejecutándose» es más concluyente que la evidencia aportada.

### A-04 — Alto: amplificación de memoria y salida

- **Evidencia:** por cada coincidencia se conserva la línea y contexto; la serialización repite texto por hallazgo, la redacción usa copia profunda y HTML construye tarjetas completas en memoria ([`__main__.py:27`](../../nexa_scriptguard/__main__.py#L27), [`__main__.py:43`](../../nexa_scriptguard/__main__.py#L43), [`__main__.py:64`](../../nexa_scriptguard/__main__.py#L64)).
- **Reproducción observada:** una línea de 100 fragmentos `eval x; `, 802 bytes en el archivo temporal, generó 100 hallazgos y 123.305 bytes con `json.dumps` predeterminado. Esto demuestra amplificación, no establece un máximo de memoria ni un tiempo de ejecución.
- **Impacto:** una entrada pequeña o dentro del límite puede provocar consumo excesivo de memoria, CPU o disco. No hay límite de hallazgos, longitud de evidencia, tiempo, tamaño de salida ni cancelación. Las regex y sustituciones repetidas también requieren pruebas adversariales; no se midió un umbral de ReDoS.

### A-05 — Medio: evidencia incompleta y salidas inconsistentes

- **Evidencia:** hallazgos regex guardan columna, instrucción, fragmento y dos líneas vecinas a cada lado; hallazgos de flujo agregan `end_line`, pero asignan columna 1 y no registran sitio de asignación, valor, secuencia ni motivo de correlación ([`contextual.py:44`](../../nexa_scriptguard/contextual.py#L44)).
- JSON conserva los campos del objeto; HTML y terminal muestran subconjuntos distintos, y SARIF conserva ubicación inicial, explicación, instrucción y confianza, pero omite contexto, recomendaciones, fin de rango y hash ([`__main__.py:52`](../../nexa_scriptguard/__main__.py#L52)). El formato plain no muestra SHA-256, confianza ni pasos de verificación.
- En la prueba de `SG-FLOW-001`, `results[].ruleId` existe pero el catálogo `driver.rules` contiene solo las cinco reglas JSON. Esto dificulta la resolución de metadatos; **no se realizó una validación de esquema ni se afirma que la ausencia del descriptor por sí sola invalide SARIF**. `render_sarif` requiere ruta absoluta para `as_uri`; la CLI la suministra, pero llamadas directas con rutas relativas pueden fallar.
- No existe modelo documentado de evidencias, identificador estable de hallazgo, deduplicación semántica, versión de reglas ni trazabilidad de transformación/redacción.
- La versión emitida en el reporte es `0.4.0-alpha`, mientras que paquete y módulo declaran `0.4.0a1`; conviene usar una fuente única de versión para evitar ambigüedades ([`__main__.py:37`](../../nexa_scriptguard/__main__.py#L37), [`pyproject.toml`](../../pyproject.toml)).

### A-06 — Medio: severidad y confianza no están calibradas

- `SG-001`, `SG-002` y ambas reglas de flujo son `CRITICAL`; las otras tres, `HIGH`, definidos estáticamente ([`bash.json`](../../nexa_scriptguard/bash.json), [`contextual.py:40`](../../nexa_scriptguard/contextual.py#L40)). No hay evaluación del alcance, control de datos, probabilidad, contexto de ejecución ni impacto real.
- La confianza es `heuristic` para regex y `medium` para correlación, sin escala común, explicación, métricas o calibración ([`__main__.py:32`](../../nexa_scriptguard/__main__.py#L32)). Una correlación incierta puede describirse como hecho confirmado.
- `--fail-on` usa solamente severidad; devuelve 2 tanto para umbral alcanzado como para diversos errores de CLI, lo que dificulta distinguirlos en automatización. Sin `--fail-on`, incluso hallazgos críticos devuelven 0.

### A-07 — Medio: diferencias entre motores y entradas

- Python decodifica bytes inválidos con `errors=\"replace\"`; Rust los rechaza ([`__main__.py:22`](../../nexa_scriptguard/__main__.py#L22), [`main.rs:37`](../../rust/nexa-scriptguard-helper/src/main.rs#L37)). Se comprobó que Python acepta `echo` seguido de byte `0xff` y calcula correctamente el hash de los bytes originales.
- Rust compara con `contains` sensible a mayúsculas y requiere espacios literales para la primera regla; su segunda regla no exige que `--data-binary` esté en una instrucción `curl`/`wget` ni que el archivo sensible sea realmente el contenido transmitido. Los IDs y reglas no son equivalentes a Python. No hay contrato común ni pruebas diferenciales.
- Una salida positiva de un motor no predice la del otro; las comparaciones de cobertura requieren especificar explícitamente qué casos comparten.

### A-08 — Medio: escritura, terminal y concurrencia no endurecidas

- Los reportes se escriben directamente y en secuencia, sin transacción entre formatos, exclusión mutua, creación exclusiva ni escritura atómica; un fallo posterior puede dejar archivos parciales o solo algunas salidas. Las excepciones de escritura quedan fuera del bloque de errores de lectura ([`__main__.py:136`](../../nexa_scriptguard/__main__.py#L136), [`__main__.py:155`](../../nexa_scriptguard/__main__.py#L155)).
- Validación de salidas usa rutas con `expanduser().resolve()`, pero la escritura utiliza las rutas originales; `~` puede validarse para una ubicación y escribirse o fallar en otra. Salidas preexistentes se sobrescriben.
- No hay coordinación para procesos concurrentes que escriban el mismo destino. La entrada puede cambiar durante el análisis o entre comprobación y apertura; el hash identifica los bytes efectivamente leídos, no garantiza una instantánea coherente ni la identidad posterior del archivo.
- En terminal se insertan rutas y texto no confiables; la ruta neon se interpola en markup Rich y ambos motores pueden emitir caracteres de control presentes en entrada o ruta. Se requiere evaluar escape de markup, secuencias de control y seguridad de logs. No se verificó explotación de terminal.
- El límite por bytes no establece límite temporal de E/S ni una política completa de archivos especiales, enlaces o condiciones de carrera. No se sometieron FIFOs ni dispositivos a pruebas en esta auditoría.

## 5. Revisión detallada de capacidades

### 5.1 Parser Bash, contexto y correlación

No existe gramática, AST, tokenizador de shell ni validación sintáctica. Las regex desconocen comillas, sustitución de comandos, expansiones, heredocs, pipes y redirecciones como entidades semánticas. `logical_lines` maneja algunas barras invertidas finales, no las reglas completas de Bash; solo se aplica a correlación, no a las cinco reglas directas.

El diccionario de asignaciones es textual y global al recorrido: no modela flujo de control, alcance de funciones/subshell, reasignaciones condicionales, exportaciones a procesos, arrays, transformaciones ni aliases. Solo sustituye referencias capturadas inicialmente; no hay propagación recursiva ni resolución de valores. El orden de iteración de un conjunto de referencias no define una semántica estable para sustituciones dependientes. Su condición de exclusión de coincidencias directas puede dejar variantes sin regla de respaldo; `elif` limita a una clase de correlación por línea lógica.

La correlación detecta coexistencia de patrones, no un enlace fuente → transformación → sumidero probado. No modela si la misma salida de red llega efectivamente al intérprete o si el archivo referenciado se envía al destino.

### 5.2 Inventario de reglas

| ID | Señal actual | Limitación representativa |
|---|---|---|
| SG-001 | `curl`/`wget` y pipe directo a `bash`, `sh` o `zsh`, misma línea | Cadenas/comentarios son interpretados como código; pierde continuaciones y `sudo` interpuesto. |
| SG-002 | `curl`/`wget`, `--data-binary @` o `--upload-file`, ruta de clave SSH RSA/Ed25519 | No cubre todas las formas de subida, rutas o claves; coincidencia textual no prueba transferencia. |
| SG-003 | `chmod 777`, con `-R` opcional en posición específica | Omite modos simbólicos y otras combinaciones de opciones; no evalúa destino. |
| SG-004 | `rm` con opción corta que contiene `r` antes de `f` | `rm -fr` no coincide; no modela opciones separadas, rutas o expansión. |
| SG-005 | `eval` seguido de espacio | No determina confiabilidad del argumento y puede detectar texto no ejecutable. |
| SG-FLOW-001 | Expansión textual de variable hace coexistir red y sink shell | Sin origen, camino ni certeza de ejecución; no resuelve múltiples saltos. |
| SG-FLOW-002 | Expansión textual hace coexistir ruta sensible y patrón de subida | Sin resolución de archivos ni flujo real; limitado a patrones de [`contextual.py:8`](../../nexa_scriptguard/contextual.py#L8). |

Rust tiene dos etiquetas distintas: `REMOTE_EXECUTION_REVIEW` y `SENSITIVE_FILE_UPLOAD_REVIEW`. No representa las otras familias ni los mismos predicados. Los checks Python son textos estáticos; algunos son instrucciones generales y `stat ruta_objetivo` requiere sustitución manual. El analizador no los ejecuta. Son útiles como guía inicial, pero no constituyen un procedimiento reproducible con precondiciones, identificación de evidencia, autorización o manejo seguro de secretos.

### 5.3 SHA-256 y evidencia

Python calcula `hashlib.sha256(data).hexdigest()` sobre los bytes originales, antes de decodificar o redactar; se contrastó con `hashlib` en la prueba de UTF-8 inválido. Esto permite identificar el contenido leído, no demuestra procedencia, integridad frente a una referencia confiable, firma, fecha de adquisición ni ausencia de cambios durante la lectura. El hash se incluye en JSON y HTML, y terminal neon, pero no en terminal plain o SARIF; Rust no lo calcula. No se verificó contra una herramienta externa ni con vectores estándar en la suite.

Se recomienda conservar procedencia y rangos verificables sin afirmar que una coincidencia es prueba de ejecución. Distinguir bytes originales, texto decodificado y evidencia redactada, así como qué hash se distribuye y sus implicaciones de privacidad.

### 5.4 Reportes y protección de secretos

| Superficie | Estado observado | Brecha |
|---|---|---|
| JSON | Objeto con metadatos, SHA-256 y hallazgos completos; Unicode legible. | Sin esquema/versionado de contrato; contexto y ruta pueden filtrar datos; redactado parcial. |
| HTML | Autocontenido; datos dinámicos textuales escapados con `html.escape`; existe prueba básica de `<script>`. | No muestra contexto o rango final; redacción opcional; faltan pruebas sistemáticas de inyección y controles. |
| SARIF | `2.1.0`, ubicación, nivel y resultados; rutas absolutas convertidas a URI en CLI. | Catálogo no incluye flujo; campos omitidos; no se validó esquema ni ingestión real; ruta absoluta puede revelar información. |
| Terminal neon | Rich muestra hash y detalles; instrucciones se agregan como `Text`. | Ruta interpolada como markup; salida contiene evidencia; no se verificó neutralización integral de controles. |
| Terminal plain | Hallazgos e instrucción resumidos. | Sin hash ni indicación explícita de confianza o verificaciones; posible exposición de controles y secretos. |
| Rust | Texto con ruta y línea original. | Sin redacción ni hash, sin formato estructurado o paridad de campos. |

La prueba HTML existente verifica un solo payload, no cubre todos los campos. Los reportes no son seguros para compartir automáticamente, incluso con `--redact`; aplicar revisión humana y controles de acceso.

## 6. Seguridad del analizador, recursos y calidad

- **Entrada no confiable:** el contenido se lee como datos y no se llama a shell ni se ejecutan verificaciones en el código revisado. Esto no elimina los riesgos de agotamiento, fuga, terminal o sobrescritura ya descritos.
- **Presupuesto:** ambos motores limitan bytes de entrada a 5 MiB; no se comprobaron en esta ejecución los bordes 5 MiB exactos y +1. Python puede amplificar salida y Rust puede generar gran salida en terminal; no hay cuotas globales ni control de tiempo.
- **Fuzzing:** no se encontraron harnesses o corpus de fuzzing en los archivos versionados. No se ejecutó fuzzing ni medición sistemática de complejidad.
- **Concurrencia:** no hay procesamiento paralelo interno en los caminos revisados. La ausencia de paralelismo interno no evita carreras entre procesos o frente al sistema de archivos. No se ejecutó una prueba de estrés concurrente.
- **Errores y contratos:** lectura Python convierte errores previstos en error de argparse; errores de salida pueden producir traceback. Rust informa errores de lectura, pero no ofrece formato estructurado. La política de entrada inválida, salidas parciales y códigos debe unificarse explícitamente.
- **Dependencias:** Python depende de Rich y setuptools; Rust no declara dependencias directas ([`pyproject.toml`](../../pyproject.toml), [`Cargo.toml`](../../rust/nexa-scriptguard-helper/Cargo.toml)). No se realizó auditoría de cadena de suministro, vulnerabilidades de dependencias ni revisión de dependencias transitivas.

## 7. Matriz de funcionalidades

| Funcionalidad solicitada o relevante | Estado | Evidencia y brecha |
|---|---|---|
| Lectura sin ejecutar scripts | Implementado con salvedad | No hay ejecución en los caminos revisados; A-01 permite sobrescribir entrada mediante salida aliased. |
| Límite de entrada 5 MiB | Implementado | Ambos leen como máximo límite + 1; distinto tratamiento de UTF-8. No limita CPU, salida ni tiempo. |
| Parser real de Bash | Pendiente | Análisis textual en ambos motores; no AST ni gramática. |
| Contexto sintáctico y control de flujo | Pendiente | Sin scopes, ramas ni semántica de quoting/heredoc. |
| Flujo de datos | Parcial | Dos heurísticas de sustitución en un solo nivel, sin grafo ni trazabilidad. |
| Correlación de instrucciones | Parcial | Referencias a asignaciones textuales anteriores; sin correlación general ni evidencia de origen. |
| Reglas de riesgo | Parcial | Cinco reglas Python, dos correlaciones y dos etiquetas Rust; no hay cobertura integral ni paridad. |
| Evidencia local y posición | Parcial | Python conserva línea, fragmento y contexto; sin cadena de flujo ni rangos completos homogéneos. Rust imprime línea. |
| SHA-256 | Parcial | Python sobre bytes leídos; no en todos los formatos; ausente en Rust. |
| Severidad y confianza | Parcial | Severidades fijas y dos etiquetas de confianza sin calibración; ausentes en Rust. |
| Procedimientos de investigación | Parcial | Recomendaciones y checks estáticos, no ejecutados; sin playbooks ni cadena de custodia. |
| Redacción de secretos | Parcial | Opcional y limitada en Python; ausente en Rust, rutas y hash conservados. |
| JSON / HTML / SARIF | Parcial | Solo Python; campos dispares, SARIF sin catálogo de flujo ni validación integral. |
| Terminal | Parcial | Python neon/plain y Rust; distinta información y tratamiento de datos no confiables. |
| Integración de motores / contrato común | Pendiente | Ejecutables independientes; no protocolo ni pruebas de paridad. |
| Concurrencia segura | Pendiente | Sin política de salidas concurrentes o TOCTOU; no probada. |
| Límites de memoria, tiempo y salida | Parcial | Solo límite de bytes de entrada; amplificación demostrada. |
| Fuzzing y corpus adversarial | Pendiente | No encontrados en el repositorio; no ejecutados. |
| CI multiplataforma | Parcial | Python configura Windows/Linux/macOS y 3.10/3.12; Rust configura Ubuntu ([workflows](../../.github/workflows/)). Su presencia no prueba ejecuciones exitosas. |

## 8. Roadmap propuesto y criterios de aceptación

Las prioridades y umbrales siguientes son **propuestas para acordar**, no garantías actuales. Todo cambio de detección debe incluir regresiones positivas y negativas; no ejecutar nunca el código analizado.

### P0 — Integridad, confidencialidad y disponibilidad

1. **Salidas seguras:** rechazar identidad compartida entrada/salida y entre salidas, incluidos enlaces duros; definir política de archivos existentes; usar apertura y publicación resistentes a carreras según capacidades de cada plataforma. Informar fallos sin éxito parcial aparente.
   - Aceptación: pruebas temporales en Windows/Linux/macOS para misma ruta, ruta relativa/absoluta, symlink donde sea compatible, hardlink, salidas duplicadas y errores de escritura; bytes originales intactos en todos los casos. Pruebas concurrentes demuestran que un fallo no deja reporte final truncado. Documentar explícitamente límites residuales por plataforma.
2. **Política de privacidad:** definir modo compartible y campos permitidos, rutas y huellas; centralizar sanitización antes de todos los serializadores, incluidos logs y Rust si corresponde. Mantener claro que la detección de secretos no puede garantizar exhaustividad.
   - Aceptación: fixtures sintéticos de asignaciones, Bearer, URLs con credenciales, claves multilínea y secretos en contexto/ruta; validar cada salida y errores, sin coincidencias de los valores de prueba. Documentar restricciones y comportamiento cuando un campo no puede sanearse.
3. **Presupuestos:** límites configurables y seguros para hallazgos, evidencia, bytes de salida y tiempo; truncamiento explícito con estado de análisis incompleto y código diferenciado de éxito limpio.
   - Aceptación propuesta: para una configuración de prueba de 1.000 hallazgos y 2 MiB de salida, ninguno supera el límite; entradas de muchas coincidencias, líneas largas y continuaciones terminan dentro del tiempo configurado o informan cancelación. Medir memoria pico, CPU y disco en CI; fijar umbrales de producción tras establecer baseline.
4. **Salida segura en terminal:** escapar markup en rutas y neutralizar/representar controles en texto y logs.
   - Aceptación: pruebas con ESC, OSC, retornos de carro y markup Rich en rutas e instrucciones; los bytes de control no confiables no se emiten como secuencias activas.

### P1 — Contrato de evidencia y reportes

1. Definir modelo versionado común: ID de regla, versión, ubicación/rango, severidad, confianza explicada, evidencia y sus transformaciones, origen de datos, limitaciones, estado y metadatos de análisis. Separar evidencia observada de hipótesis.
   - Aceptación: pruebas de esquema y round-trip JSON; IDs únicos; rangos correctos con UTF-8, CRLF y multilínea; SHA-256 contrastado con vectores conocidos y bytes del archivo, también tras redacción; pruebas de cada formato.
2. Registrar las reglas contextuales y mapear la evidencia al contrato SARIF; declarar política de rutas y columnas.
   - Aceptación: validar el documento contra el esquema SARIF 2.1.0 y ejecutar una ingestión real en al menos un consumidor soportado con reglas directas y de flujo, rutas con espacios y caracteres Unicode. Registrar cualquier diferencia específica del consumidor.
3. Definir códigos de salida separados para hallazgos según umbral, entrada inválida, análisis incompleto y errores de E/S, con migración compatible y documentación.
   - Aceptación: pruebas CLI de cada código, de combinaciones de formato y de fallos; no reportar análisis incompleto como limpio.

### P2 — Parser y semántica Bash

1. Seleccionar y evaluar un parser con soporte y licencia compatibles; documentar versión de Bash, plataformas, precisión de rangos, política de errores y sintaxis no soportada. Un AST parcial no debe presentarse como parser completo.
   - Aceptación: corpus versionado con comillas simples/dobles, escapes, comentarios, heredocs, continuaciones, funciones, subshells, redirecciones, pipes, sustituciones, sintaxis inválida y UTF-8; verificar nodos y posiciones esperadas. Todo error o nodo no soportado debe marcar el análisis incompleto.
2. Migrar reglas a nodos de comandos y argumentos conservando un modo heurístico identificado hasta completar migración.
   - Aceptación: las reproducciones de A-03 dejan de producir los falsos positivos/negativos especificados para sintaxis soportada; conservar regresiones actuales y medir precisión/recall sobre corpus etiquetado, publicando denominadores y casos excluidos.

### P3 — Flujo de datos y correlación

1. Definir IR, grafo de control, ámbitos, fuentes, transformaciones, sumideros y manejo conservador de valores desconocidos, ciclos y ramificaciones. Evitar ejecutar expansiones o resolver recursos remotos.
   - Aceptación: fixtures de múltiples saltos, reasignaciones condicionales, funciones, subshells y quoting; cada correlación informa origen, pasos, sink, rangos y grado de incertidumbre. No declarar ejecución demostrada por coincidencia textual.
2. Revisar catálogo y taxonomía de severidad/confianza; documentar amenazas, precondiciones y verificaciones manuales seguras por regla.
   - Aceptación: por regla, al menos casos positivos, negativos y ambiguos, justificación de severidad, incertidumbre y pruebas de umbral; informe de precisión/recall sobre corpus etiquetado, sin prometer cobertura universal.

### P4 — Convergencia de motores y robustez continua

1. Decidir si Rust es prototipo independiente o motor integrado; especificar protocolo, IDs, límites, errores, comportamiento UTF-8 y compatibilidad antes de prometer paridad.
   - Aceptación: suite contractual compartida para las capacidades declaradas equivalentes, con diferencias intencionales documentadas y prueba de integración extremo a extremo si se integran.
2. Añadir fuzzing continuo de parser, correlación y serializadores, más pruebas diferenciales y de concurrencia.
   - Aceptación propuesta: harness reproducible por semilla, corpus y minimización; al menos 10 minutos por harness en una tarea programada, sin crashes ni ejecuciones de entrada; cada incidente minimizado genera regresión. Pruebas de límites y escrituras concurrentes en los sistemas soportados.
3. Ampliar CI a las plataformas y versiones efectivamente declaradas para ambos motores; publicar resultados y presupuestos medidos, no inferir éxito por existencia de workflow.

## 9. Validación realizada y pendientes

| Comprobación | Resultado |
|---|---|
| Python: `.venv\Scripts\python.exe -m unittest discover -s tests -v` | **8/8 pasaron** en esta sesión. |
| Rust: `cargo fmt`, `cargo clippy`, `cargo test` | El usuario informó que finalizaron correctamente antes de esta auditoría; **no se reejecutaron ni se inspeccionaron sus logs** aquí. Cuatro tests Rust se identificaron en el código fuente. |
| Casos sintéticos de parsing/correlación | Confirmados: falsos positivos por literal, comentario y heredoc; falsos negativos por continuación, `sudo`, dos saltos y rama; falso positivo de variable en texto citado. |
| Protección de entrada | Confirmada sobrescritura por hardlink en directorio temporal; archivo temporal eliminado por su gestor al finalizar. |
| Redacción y SARIF | Confirmado valor Bearer sintético no redactado y ausencia de descriptor de `SG-FLOW-001` en `driver.rules`. |
| Hash | Confirmada igualdad con `hashlib.sha256` sobre bytes inválidos UTF-8 de prueba. |
| Amplificación | 802 bytes de archivo, 100 hallazgos, 123.305 bytes de JSON en serialización de prueba. |
| No realizados | Fuzzing, benchmarks exhaustivos, validación de esquema SARIF/ingestión, pruebas de carreras, límites exactos, análisis de dependencias y CI remota. |

## 10. Estado Git y cambios de esta auditoría

Al comenzar: `main...origin/main`; `rust/nexa-scriptguard-helper/src/main.rs` modificado, y `.vscode/`, `rust/nexa-scriptguard-helper/Cargo.lock` y `rust/nexa-scriptguard-helper/target/` sin seguimiento. La diferencia Rust observada es de formato; se conservó íntegramente. Este informe agrega `docs/audits/NEXA_SCRIPTGUARD_TECHNICAL_AUDIT.md` sin seguimiento. No se hicieron commits ni push. El estado final debe confirmarse con `git status --short --branch`.
