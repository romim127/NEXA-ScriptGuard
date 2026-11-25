# Arquitectura actual

## Flujo de datos

1. `ingestion.py` resuelve y abre una entrada regular, comprueba identidad del descriptor, límite de bytes y cambios detectables durante lectura. Los bytes se hashean antes de decodificar.
2. `analysis.py` selecciona por extensión `.sh` o `.py`; rechaza otras extensiones. Para Bash, `parser.py` usa `tree-sitter` y `tree-sitter-bash`. Para Python, `python_analysis.py` utiliza `ast` de la biblioteca estándar sin importar ni ejecutar el archivo, y aplica las reglas de `python_rules.json`. Errores de gramática y límites se informan como incompletos.
3. `analysis.py` coordina parsing, reglas, correlación y análisis de variables; no ejecuta Bash.
4. `rules.py` aplica identificadores estables a nodos `command` y `pipeline`; `dataflow.py` conserva los sitios de asignación y consumo para unas pocas correlaciones.
5. `model.py` unifica metadatos de archivo, hash, ubicación, clasificación, evidencia, recomendación y estado.
6. `classification.py` ordena/deduplica hallazgos y limita evidencia. `redaction.py` sanitiza controles y aplica redacción best-effort antes de todas las salidas compartibles.
7. `reports.py` serializa JSON, HTML, SARIF y terminal Rich desde el mismo modelo; `cli.py` aplica límites y códigos de salida.
8. `rust_bridge.py` puede invocar el helper Rust como proceso separado con argumentos fijos, timeout, bytes acotados por `stdin` y contrato JSON `1.0` / `json-v1-stdin`. Rust analiza exactamente el snapshot y hash calculados por Python, no vuelve a abrir la ruta de usuario. No se usa shell ni se ejecuta el contenido.

## Contrato de hallazgo

Cada hallazgo contiene un ID determinista derivado de regla, archivo/hash y rango; regla/versión; ruta y SHA-256; rango 1-based; instrucción; contexto; severidad; confianza y razón; estado; correlación; explicación; recomendación; verificaciones no ejecutadas; limitaciones y motor.

JSON preserva la evidencia original sin redacción solamente cuando se opta explícitamente por `--include-sensitive-evidence`. En modo predeterminado, la evidencia se transforma a `shared`, el original se omite del reporte y `redaction_applied` / `original_available_in_this_report` lo indican. La redacción es una defensa de exposición común, no detector exhaustivo de secretos.

La suite valida JSON contra el contrato propio `tests/schemas/nexa-report-1.0.schema.json`, escrito en JSON Schema 2020-12; no existe un esquema externo oficial para este formato NEXA. Para SARIF 2.1.0 valida con JSON Schema Draft 4 contra el esquema oficial OASIS Errata 01, obtenido por HTTPS y fijado por SHA-256. `NEXA_SARIF_SCHEMA_PATH` permite utilizar una copia idéntica local para pruebas sin conexión. SARIF declara `columnKind: unicodeCodePoints`, coherente con las columnas del parser. Estas validaciones automatizadas no se ejecutan en la CLI de producción, que conserva validaciones estructurales internas; tampoco sustituyen pruebas con consumidores reales.

## Garantías de archivos

- La entrada se lee desde un descriptor y su tamaño/hash identifican los bytes leídos; no se garantiza una instantánea coherente frente a escritores concurrentes que puedan alterar contenido y metadatos.
- Salidas existentes, symlinks y rutas de salida duplicadas se rechazan. La identidad `(device, inode)` detecta hardlinks existentes al input. Se escriben temporales en el directorio de destino, se sincroniza su contenido y se publica cada nombre mediante creación exclusiva de hardlink.
- La creación del destino no reemplaza una entrada que aparezca concurrentemente. Si publicar un formato posterior falla, se intenta retirar los nombres previos solo cuando siguen apuntando a los temporales; el rollback entre varios volúmenes no es global ni resistente a caída abrupta.
- En Windows se depende de permisos/ACL y soporte del filesystem para hardlinks; la sincronización de directorio no está disponible en este código. En filesystems que no soporten hardlinks, el reporte falla explícitamente. No hay promesa de durabilidad ante pérdida eléctrica.
- El puente Rust transporta el snapshot por una tubería de proceso; stdout se limita al contrato JSON del helper. El helper no crea archivos con datos de entrada.

## Presupuestos

Los límites configurables cubren bytes de entrada, hallazgos, caracteres de evidencia por hallazgo y en total, expansión intermedia del flujo, nodos AST, tamaño de salida, tiempo y una estimación de memoria. Al superar la estimación tras construir el AST se detiene el análisis de reglas y se emite un resultado incompleto. El runtime Tree-sitter no permite interrumpir una llamada `parse` desde Python; el presupuesto de memoria no limita asignaciones nativas. La salida completa se serializa antes de publicar y el límite de bytes se verifica antes de escribir.

El presupuesto temporal de `analyze` usa el reloj monotónico y considera agotado el plazo cuando el reloj alcanza o supera el deadline. Se comprueba nuevamente después de clasificar y construir el informe, antes de devolverlo. Es cooperativo: no interrumpe el parser ni operaciones bloqueantes. En la CLI, la lectura inicial del archivo ocurre antes de llamar a `analyze`, y la redacción, serialización y publicación ocurren después; estas etapas no están comprendidas en ese presupuesto.

## Parser y límites semánticos

La dependencia es `tree-sitter>=0.25,<0.26` y `tree-sitter-bash==0.25.1` (MIT). Tree-sitter ofrece gramática Bash, recuperación de errores y rangos de origen byte precisos, convertidos aquí a columnas de caracteres Unicode. La gramática representa comandos, pipelines, redirecciones, palabras, asignaciones, sustituciones, heredocs y estructuras compuestas para las construcciones aceptadas. No resuelve funciones llamadas dinámicamente, `source`, entorno real, comandos externos ni comportamiento de runtime. El soporte efectivo queda limitado a la gramática y fixtures de `tests/test_parser.py`.

El modo `--compat-heuristics` conserva regex históricas, pero nunca comparte la etiqueta de parsing AST y siempre produce un estado incompleto.

El AST de Python está limitado por la gramática del intérprete que ejecuta NEXA. Su resolución de nombres es conservadora: alias importados con asignaciones conflictivas se consideran ambiguos. La correlación PY-004 relaciona únicamente expresiones de red directas o asignaciones simples con llamadas de evaluación; no construye un grafo de control y puede producir falsos positivos y negativos. El límite temporal es cooperativo y no interrumpe `ast.parse`; el presupuesto de memoria es estimado. El helper Rust no analiza archivos Python.

## Dependencias

`Cargo.lock` corresponde a un ejecutable Rust y debe mantenerse versionado; actualmente el crate no añade dependencias Rust. El `.gitignore` excluye `.vscode/`, `.venv/`, `target/`, caches Python y artefactos de cobertura; la configuración local ya existente no se elimina.
