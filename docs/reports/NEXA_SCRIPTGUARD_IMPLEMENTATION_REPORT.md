# Informe de implementación de NEXA ScriptGuard

**Versión documentada:** 0.5.0a1<br>
**Plataforma validada localmente:** Windows, Python 3.14.3, Rust/Cargo disponible<br>
**Base técnica:** auditoría existente en [`../audits/NEXA_SCRIPTGUARD_TECHNICAL_AUDIT.md`](../audits/NEXA_SCRIPTGUARD_TECHNICAL_AUDIT.md)<br>
**Estado:** implementación alfa; no constituye una versión final ni una certificación de seguridad.

## 1. Componentes implementados

La ruta modular Python reemplaza el flujo de regex como implementación principal. Los módulos tienen responsabilidades diferenciadas y se ejercitan desde la CLI o las pruebas:

| Responsabilidad | Implementación |
|---|---|
| Ingesta y publicación segura | `nexa_scriptguard/ingestion.py` |
| Parser y nodos de sintaxis Bash | `nexa_scriptguard/parser.py` |
| Representación común de ubicaciones, hallazgos y análisis | `nexa_scriptguard/model.py` |
| Reglas AST y catálogo | `nexa_scriptguard/rules.py`, `nexa_scriptguard/bash.json` |
| Correlación contextual y flujo conservador | `nexa_scriptguard/dataflow.py` |
| Clasificación, deduplicación, IDs y presupuestos de evidencia | `nexa_scriptguard/classification.py`, `nexa_scriptguard/limits.py` |
| Redacción y saneamiento para compartir | `nexa_scriptguard/redaction.py` |
| JSON, HTML, SARIF y terminal Rich | `nexa_scriptguard/reports.py` |
| Orquestación, estado incompleto y helper Rust | `nexa_scriptguard/analysis.py`, `nexa_scriptguard/rust_bridge.py` |
| CLI y compatibilidad histórica explícita | `nexa_scriptguard/cli.py`, `nexa_scriptguard/compat.py`, `nexa_scriptguard/legacy.py`, `nexa_scriptguard/__main__.py` |

El analizador procesa contenido como datos. Ni Python ni el helper Rust ejecutan el script inspeccionado o los comandos de investigación; estos últimos son recomendaciones.

## 2. Archivos creados y modificados

**Creados para la implementación**

- `nexa_scriptguard/analysis.py`, `classification.py`, `cli.py`, `compat.py`, `dataflow.py`, `ingestion.py`, `legacy.py`, `limits.py`, `model.py`, `parser.py`, `redaction.py`, `reports.py`, `rules.py`, `rust_bridge.py`.
- `tests/test_analysis_core.py`, `tests/test_cli.py`, `tests/test_ingestion.py`, `tests/test_parser.py`, `tests/test_redaction.py`, `tests/test_report_schemas.py`, `tests/test_rust_bridge.py`, `tests/corpus/bash_cases.json` y `tests/schemas/nexa-report-1.0.schema.json`.
- `README.en.md`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `docs/RULES.md`, `docs/ROADMAP.md`, `docs/Ollama-analysis.md` y este informe.
- `rust/nexa-scriptguard-helper/Cargo.lock`, generado por Cargo para el ejecutable Rust. Se conserva aunque el crate todavía no tenga dependencias externas.

**Modificados**

- `.github/workflows/tests.yml`, `.github/workflows/rust.yml`, `.gitignore`.
- `README.md`, `SECURITY.md`, `CONTRIBUTING.md`.
- `pyproject.toml`, `nexa_scriptguard/__init__.py`, `nexa_scriptguard/__main__.py`, `nexa_scriptguard/bash.json`.
- `rust/nexa-scriptguard-helper/src/main.rs`.

La auditoría inicial se conserva como línea base; no se repitió ni se reemplazó. La carpeta local `.vscode/` queda ignorada y no se eliminó ni se modificó. Los directorios `.venv/`, `target/` y las cachés quedan excluidos por `.gitignore`.

## 3. Correcciones de seguridad

- **Entrada:** se lee un archivo regular mediante descriptor, se limita su tamaño, se compara la identidad del descriptor con los metadatos iniciales y se comprueba si el tamaño/fecha cambiaron durante la lectura. El SHA-256 identifica exactamente los bytes leídos. No se garantiza una instantánea coherente si un escritor altera el contenido simultáneamente.
- **Salida:** se rechazan destinos existentes, enlaces simbólicos, rutas duplicadas y hardlinks ya existentes al archivo analizado. Los reportes se preparan en temporales del directorio destino, se sincroniza el contenido y se publican mediante creación exclusiva de hardlink, que no reemplaza una entrada concurrente.
- **Errores parciales:** ante fallo de una publicación posterior se intenta retirar los destinos publicados, solo si aún identifican los temporales. Se informan fallos de rollback o limpieza. No hay transacción atómica entre varios formatos/volúmenes ni garantía ante caída abrupta o pérdida eléctrica; en Windows no se sincroniza el directorio.
- **Secretos y terminal:** una rutina común recorre todos los campos de salida, escapa caracteres de control y aplica redacción best-effort de patrones de credenciales, rutas de usuario y ubicaciones sensibles. La redacción es predeterminada; `--include-sensitive-evidence` es una exclusión explícita. SHA-256 y metadatos de ubicación siguen disponibles.
- **Presupuestos:** se limitan bytes de entrada, AST, hallazgos, evidencia por hallazgo y total, expansión intermedia del flujo, tiempo, tamaño de cada artefacto de salida y una estimación de memoria. El estado pasa a `incomplete` al detectar un límite o evidencia truncada; la CLI devuelve `3`, no una señal de éxito limpio.

El límite de memoria no es una cuota dura del proceso. Tree-sitter no se puede interrumpir desde Python mientras ejecuta `parse`; el presupuesto se estima tras convertir el AST y, si se excede, se detiene el análisis de reglas. La serialización se realiza antes de publicar y el límite de salida se comprueba por artefacto, no como suma de todos los formatos.

## 4. Parser Bash seleccionado y cobertura real

Se seleccionó `tree-sitter-bash==0.25.1` con `tree-sitter>=0.25,<0.26`, dependencias MIT. Se eligió por su gramática Bash, nodos estructurados, recuperación de errores y rangos de origen precisos; el binding Python publica wheels para los sistemas declarados por el proyecto. El ritmo de mantenimiento del upstream no se verificó independientemente durante esta tarea.

El adaptador convierte el árbol a nodos con clase sintáctica, rangos byte, posiciones 1-based en caracteres Unicode, errores y relaciones padre/hijo. Comparte los bytes originales y obtiene el texto de cada nodo por corte diferido, sin duplicar en cada nodo todo su segmento. La suite comprueba comandos, pipelines multilínea, quoting/comentarios, heredocs, asignaciones, funciones, condicionales, bucles, subshells, UTF-8 y sintaxis inválida. El catálogo principal ya consulta nodos `command` y `pipeline`, no líneas físicas.

La gramática aceptada no equivale a semántica completa: no se evalúan expansiones, valores de entorno, comandos externos, `source`, comportamiento del shell, ejecución condicional ni efectos del sistema. Los errores sintácticos y límites son explícitos; el inventario de soporte semántico nodo-por-nodo sigue pendiente. `--compat-heuristics` conserva las heurísticas regex anteriores bajo el identificador `legacy-regex-compatibility` y siempre informa análisis incompleto.

## 5. Reglas implementadas

El catálogo mantiene IDs estables, versión de regla, severidad, explicación, recomendación y verificaciones manuales:

- **SG-001 a SG-012:** pipeline de descarga/intérprete; posible subida de rutas sensibles; permisos mundialmente escribibles; borrado recursivo/forzado; `eval`; shell dinámico; desactivación de controles; persistencia en cron/servicios; cambios de configuración sensible; setuid; valores que parecen credenciales; y escrituras a destinos críticos acotados.
- **SG-FLOW-001 y SG-FLOW-002:** texto de red en una variable relacionada con intérprete y ruta sensible relacionada con opción de carga.

El catálogo contiene **14 reglas: 10 HIGH y 4 MEDIUM**; no hay reglas asignadas actualmente a CRITICAL o LOW, aunque el clasificador puede ordenar esos niveles. La cobertura de privilegios, persistencia, configuración, redirecciones y exposición es parcial y basada en patrones. No se declara intención maliciosa: comandos administrativos pueden ser legítimos y requieren contexto. El corpus agrupa casos positivos, negativos y ambiguos, pero la cobertura individual por regla no es exhaustiva.

## 6. Correlación y flujo de datos

La implementación registra asignaciones sintácticas y correlaciona referencias con sinks acotados (intérpretes y opciones de subida). Soporta varios saltos de variables, reasignaciones y orden por línea/columna; los registros contienen variable, cadena de asignaciones y ubicaciones de origen/destino. La expansión recursiva tiene profundidad máxima y tope de caracteres; alcanzarlos deja constancia de análisis incompleto. El análisis contextual marca ámbitos con incertidumbre.

Las relaciones se etiquetan `possible` o `indeterminate`; la presencia de comandos en un mismo pipeline es estructuralmente demostrable, pero no demuestra que los datos lleguen al intérprete ni que el comando se ejecute. No hay análisis completo de transformaciones, arrays, ámbitos de funciones, subshells, ramas, merges, puntos de entrada, fuentes externas o flujo interprocedimental. Sources y sinks no conforman todavía un grafo semántico exhaustivo.

## 7. Estado del motor Rust

Rust conserva su rol de helper opcional y no se presenta como paridad del motor Python. El ejecutable identifica dos señales compartidas, SG-001 y SG-002, mediante análisis lineal de líneas físicas; no tiene parser Bash, flujo de variables, contexto de control ni redacción propia. El protocolo JSON devuelve metadatos de versión, estado, hash y hallazgos; errores operativos en ese modo también son JSON.

Rust impone límites internos fijos de entrada, hallazgos, evidencia y salida. Aunque Python controla el timeout del proceso y valida la respuesta, esos límites todavía no se negocian en el contrato. Las pruebas actuales cubren las dos señales, citas/comentarios y errores UTF-8.

## 8. Integración Python-Rust

La integración utiliza proceso independiente, argumentos fijos y `stdin`; Python envía los bytes del snapshot ya leído y calculado, junto con ruta y SHA-256. Rust no vuelve a abrir la ruta de usuario ni crea una copia temporal de la entrada. El puente aplica timeout, limita la respuesta, valida schema/rules version, motor, ruta/hash y metadatos de cada hallazgo; los errores no se convierten silenciosamente en resultados limpios. La combinación deduplica señales compartidas por regla y línea.

El contrato `json-v1-stdin` está versionado como JSON `1.0`, pero aún no es un esquema JSON publicado/validado externamente y no unifica todos los presupuestos ni todas las propiedades del hallazgo. La paridad diferencial se limita a las señales declaradas comunes; Rust no comparte análisis contextual ni datos de flujo.

## 9. Resultados de pruebas

Validación local en Windows con Python 3.14.3:

- `python -m unittest discover -s tests -v` desde `.venv`: **64 tests, 63 aprobados y 1 omitido** (5,341 s). El omitido es la creación de symlink de salida, bloqueada por `WinError 1314` (privilegio de Windows no disponible).
- Incluye pruebas de parser, reglas/corpus, flujo y regresiones, redacción, límites, CLI, reportes, UTF-8, publicación sin sobrescritura, hardlinks, concurrencia, rollback e integración con el ejecutable Rust.
- `cargo fmt -- --check`: aprobado.
- `cargo test --all-targets`: **6 aprobados**.
- `cargo clippy --all-targets -- -D warnings`: aprobado.
- `cargo build`: aprobado.
- `python -m compileall -q nexa_scriptguard tests` y `git diff --check`: aprobados. Pylance no informó diagnósticos del workspace.

La suite descargó el esquema público oficial SARIF 2.1.0 Errata 01 desde `https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json`, verificó SHA-256 `c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e` y validó reportes reales con `jsonschema` 4.26.0/Draft 4, sin enviar los reportes. Los reportes JSON NEXA se validaron con el esquema propio `tests/schemas/nexa-report-1.0.schema.json`/Draft 2020-12; no hay un esquema externo oficial para este formato. Se comprobaron casos completos, incompletos, compatibilidad, flujo, evidencia sin redacción y reportes inválidos. También se verificó la opción de copia local mediante `NEXA_SARIF_SCHEMA_PATH`.

La consolidación corrigió un defecto reproducido: `Finding.to_dict` omitía `title`, lo que causaba `KeyError` al generar HTML o terminal Rich con hallazgos. El campo se incorporó al modelo y al contrato. SARIF ahora declara `columnKind: unicodeCodePoints`, con una prueba de columna precedida por un carácter Unicode suplementario. La validación de esquemas ocurre en pruebas, no en la CLI de producción.

Las pruebas de archivos verificaron hardlinks al input, destinos equivalentes, destino preexistente, dos escritores simultáneos, aparición del destino durante la publicación, rollback ante fallo del segundo enlace y conservación de un destino reemplazado antes del rollback. La prueba de symlink real se omitió por falta de privilegios; no se simuló su éxito. La redacción se ejercitó con credenciales, Bearer, rutas Windows/Unix y controles sintéticos en JSON, HTML, SARIF y ambas vistas de terminal.

El test suite utilizó `unittest`, que es el runner declarado en CI. No se afirma que las pruebas hayan pasado en Linux o macOS; tampoco se ejecutó el workflow remoto.

## 10. Fuzzing y límites de recursos

Existe un fuzz smoke determinista con semilla fija que analiza 250 entradas sintéticas con gramática variable; es reproducible, pero no es fuzzing guiado por cobertura ni mide cobertura del parser. No se ejecutó fuzzing continuo ni sanitizer.

Los límites configurables se prueban para entrada, nodos, hallazgos, memoria estimada, tiempo, evidencia individual/total, expansión de flujo y salida. El parser nativo no es preemptible, el cálculo de memoria no limita asignaciones nativas y se valida cada salida por separado. La ejecución aislada con cuotas duras, medición por sistema operativo y fuzzing coverage-guided quedan pendientes.

## 11. Compatibilidad multiplataforma

La CI declara Windows, Linux y macOS. El workflow Python prueba Python 3.10 y 3.12, instala el extra `test`, compila Rust y ejecuta `unittest`, incluidas las validaciones de esquema; el workflow Rust ejecuta tests y Clippy en los tres sistemas. La compatibilidad declarada de dependencias no sustituye resultados reales: solo se ejecutó localmente en Windows/Python 3.14.3; Python 3.10 y 3.12 no estaban instalados. La prueba de symlink se omitió por permisos; debe confirmarse en un runner Windows configurado para ello.

## 12. Capacidades incompletas

- Semántica completa de Bash, alcance por funciones/subshells, ramas, arrays, entorno, `source`, transformaciones y resolución del filesystem.
- Cobertura de reglas y triadas positiva/negativa/ambigua exhaustivas para cada regla.
- Redacción exhaustiva, protección de metadatos y validación de interoperabilidad con consumidores SARIF reales.
- Paridad Python-Rust, negociación de límites y resultados diferenciales amplios.
- Memoria/tiempo con cuotas duras y timeout que interrumpa parsing nativo.
- Verificación de symlink en Windows con privilegios, CI remoto, fuzzing guiado por cobertura.
- Análisis del instalador de Ollama: existe procedimiento, no artefacto inspeccionado.

## 13. Bloqueos técnicos

1. El parser Tree-sitter no es interrumpible desde el proceso Python y no ofrece por sí solo una cuota de memoria nativa.
2. El runner Windows local no permite crear el symlink de prueba. Linux/macOS no estaban disponibles para validación local y no se consultaron resultados de CI remota.
3. Las pruebas SARIF requieren acceso al esquema oficial o una copia local con el hash fijado; no se probó ningún consumidor externo. El esquema por sí solo no certifica semántica ni interoperabilidad completa.
4. No se proporcionó un instalador oficial de Ollama ni autorización para descargarlo o ejecutarlo; ninguno fue descargado ni ejecutado.

## 14. Riesgos residuales

Falsos positivos y negativos son esperables: reglas y flujo son indicadores heurísticos. Redacción best-effort puede dejar secretos no reconocidos; SHA-256 y rutas pueden facilitar correlación. La lectura no garantiza consistencia si otro proceso modifica el archivo concurrentemente. El rollback de múltiples reportes es mejor esfuerzo y no sobrevive necesariamente una caída. El helper Rust tiene menor alcance y límites fijos. Un análisis incompleto debe tratarse como desconocido, nunca como limpio.

## 15. Próximas tareas concretas

1. **P0:** validar publicación y symlinks en Windows con permisos, además de hardlinks, carreras, rollback y fallo abrupto en los tres sistemas; fijar criterios de seguridad de archivos por plataforma.
2. **P0:** ampliar el corpus de redacción y validar interoperabilidad con consumidores SARIF reales; la validación automatizada contra el esquema OASIS y el contrato JSON propio ya está incorporada.
3. **P1:** formalizar el contrato del proceso Rust, compartir límites Rust/Python y añadir pruebas diferenciales de todas las reglas que declaren paridad.
4. **P1:** definir soporte semántico explícito por nodo Bash; ampliar corpus etiquetado y completar casos positivos, negativos y ambiguos para cada regla.
5. **P1:** diseñar análisis de ámbitos/ramificaciones/funciones conservador, con transferencias de estado verificables y limitación de complejidad.
6. **P2:** evaluar aislamiento del parser para cuotas duras, medir memoria/tiempo por plataforma y añadir fuzzing guiado por cobertura con minimización de casos.
7. **P2:** ejecutar y revisar los workflows remotos Windows/Linux/macOS; actualizar compatibilidad solo con evidencia de ejecuciones reales.
8. **Bloqueado por autorización:** adquirir/analizar un artefacto oficial de Ollama solo con autorización y procedimiento de procedencia; no instalar ni ejecutar el instalador.

## 16. Matriz de cumplimiento actualizada

| Requisito | Estado | Implementación verificada / brecha |
|---|---|---|
| Ingesta, hash y límites de entrada | Implementado con límites | Snapshot de bytes acotado y hash estable de lo leído; no hay snapshot coherente frente a escritores concurrentes. |
| Evitar sobrescritura de input por ruta/hardlink/symlink | Implementado con límites | Destinos existentes y symlinks rechazados; identidad del input detecta hardlinks existentes; carreras de creación no reemplazan el destino. |
| Escritura segura y errores parciales | Parcial | Temporales, publicación no-clobber, sync de contenido y rollback best-effort; no hay atomicidad multiarchivo/caída ni fsync de directorio Windows. |
| Protección central de secretos y terminal | Parcial | Una rutina compartida aplica redacción/control escaping a todos los formatos; patrones best-effort y hash/ruta pueden revelar correlaciones. |
| Límites configurables de hallazgos, memoria, tiempo, evidencia y salida | Parcial | Todos configurables; memoria es estimada, parsing no preemptible y salida acotada por artefacto. |
| Análisis incompleto no presentado como limpio | Implementado | Errores, límites, truncamientos y compatibilidad quedan incompletos; CLI retorna 3. |
| Arquitectura modular con interfaces, código y pruebas | Implementado | Ingesta, parser, modelo, reglas, contexto/flujo, evidencia/clasificación, reportes, orquestación/Rust en módulos separados. |
| Parser Bash multiplataforma, licencia y posiciones | Parcial | Tree-sitter Bash MIT, rangos byte/Unicode; dependencias declaran wheels, pero ejecución local verificada solo en Windows. |
| Comandos, quoting, variables, sustituciones, pipes, redirecciones, heredocs y estructuras | Parcial | La gramática crea nodos; fixtures verifican subconjunto. No hay semántica completa ni catálogo por constructo no modelado. |
| Migración de regex y modo compatibilidad identificado | Implementado | Reglas principales usan AST; regex histórica queda bajo flag/etiqueta propia y estado incompleto. |
| Familias de reglas críticas/altas/medias/bajas y IDs estables | Parcial | 14 reglas: 10 HIGH y 4 MEDIUM; todavía ninguna CRITICAL/LOW, y varias familias solo cubiertas por patrones acotados. |
| Positivos, negativos y ambiguos por regla | Parcial | Corpus sintético cubre clases; no hay triada exhaustiva por cada regla. |
| Sources/sinks, propagación, reasignaciones y múltiples saltos | Parcial | Asignaciones literales, cadena de variables, orden por ubicación y sinks limitados; no modela toda la semántica. |
| Funciones, ámbitos, subshells y ramificaciones | Parcial | Algunos ancestros generan incertidumbre; no hay análisis de flujo completo por ámbito/ramificación. |
| Evidencia verificable de origen/destino y relaciones de certeza | Parcial | Registros con ubicaciones y cadena; `possible`/`indeterminate`; pipeline estructural no prueba ejecución ni transferencia. |
| Modelo unificado de hallazgo con SHA-256, ubicaciones, clasificación y recomendación | Implementado | Modelo común versionado; metadatos e instrucciones de investigación se generan por regla. |
| Procedimientos específicos y no ejecución automática | Parcial | Cada regla incluye checks/recomendaciones; falta validar exhaustividad y seguridad contextual de cada procedimiento. |
| Diferenciar evidencia original y redactada | Implementado con límites | JSON compartible elimina `original` cuando redacta y conserva `shared`; los patrones no son exhaustivos. |
| Motor Rust revisado y contrato versionado | Parcial | Helper proceso JSON `1.0`, errores estructurados y snapshot stdin; solo SG-001/002 y límites no negociados. |
| Pruebas de integración y diferenciales Python-Rust | Parcial | Integración y dos señales comunes probadas; no existe paridad amplia. |
| Terminal, JSON, HTML y SARIF desde modelo común | Implementado con validación parcial | Renderers comparten reporte; tests locales cubren CLI JSON/SARIF, HTML escaping y sanitización. |
| Validación de JSON Schema y SARIF 2.1.0 oficial | Parcial | Pruebas contra esquema NEXA propio y esquema OASIS oficial con hash fijado; falta consumidor SARIF real y validación externa en tiempo de ejecución. |
| Parser/flujo/regresiones/UTF-8/archivos/concurrencia/límites/integración | Implementado con límites | Suite local pasa; symlink omitido por permisos y fallos externos/plataformas no ejecutados. |
| Fuzzing | Parcial | 250 casos deterministas de smoke; no coverage-guided. |
| Corpus sintético reproducible | Implementado | Casos positivos, negativos y ambiguos versionados en `tests/corpus/bash_cases.json`. |
| Procedimiento del instalador oficial Ollama | Parcial | Procedimiento está documentado; artefacto no disponible, no descargado ni ejecutado. |
| CI Windows/Linux/macOS | Parcial | Workflows declarados para las tres plataformas; solo Windows local ejecutado, no se afirma éxito remoto. |
| README ES/EN, arquitectura, reglas, límites, seguridad, contribución y roadmap | Implementado | Documentación sincronizada con capacidades y límites alfa. |
| `.gitignore` y `Cargo.lock` | Implementado | Excluye `.vscode`, `.venv`, `target` y cachés; se conserva lock del binario Rust sin dependencias externas. |
| No commits, push ni ejecución de scripts analizados | Cumplido | No se realizaron commits/push; tampoco se ejecutaron scripts analizados ni instalador de Ollama. |

## 17. Estado final de Git

El trabajo permanece local y sin commit ni push. Los archivos de la implementación, pruebas, corpus y documentación, incluido `rust/nexa-scriptguard-helper/Cargo.lock`, están preparados en el índice para revisión. `.vscode/`, `target/`, `.venv/` y las cachés están ignorados y no se eliminaron. La advertencia de Git sobre conversión LF/CRLF en archivos Rust no afectó las pruebas ni `git diff --check`.
