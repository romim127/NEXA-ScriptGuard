# Contratos de módulos

| Módulo | Entrada y salida | Dependencias, errores y límites |
|---|---|---|
| `gui.py` y `gui_assets/` | Archivo seleccionado y token local → informe y descargas | Loopback, tamaño y concurrencia acotados. Rechaza solicitudes inválidas y exportaciones con ID obsoleto. |
| `cli.py` y `__main__.py` | Ruta, opciones y destinos → terminal, archivos y código de salida | Ingestión y reportes compartidos. Falla explícitamente ante colisión y error de publicación. |
| `ingestion.py`, `limits.py` | Ruta o bytes → snapshot con hash y presupuestos | Valida lectura regular y bytes. Rechaza entradas fuera de los límites. |
| `analysis.py` | Snapshot y extensión → resultado común | Despacha `.sh` y `.py`. Gramática, plazo cooperativo y límites de evidencia pueden producir un resultado incompleto. |
| `parser.py`, `rules.py`, `bash.json`, `contextual.py`, `dataflow.py`, `compat.py`, `legacy.py` | Bash → nodos, hallazgos y correlaciones | Tree-sitter y catálogo Bash. La compatibilidad heurística se identifica como incompleta. |
| `python_analysis.py`, `python_rules.json` | Python → hallazgos PY-001 a PY-008 | AST estándar, resolución conservadora y límite de nodos. La versión del intérprete determina la gramática. |
| `rust_bridge.py`, helper Rust | Snapshot Bash → JSON auxiliar versionado | Ejecutable de confianza, stdin acotado, timeout y validación de protocolo. |
| `model.py`, `classification.py`, `redaction.py` | Hallazgos → informe ordenado y evidencia compartible | Identificadores estables, límites de evidencia y redacción heurística. |
| `reports.py` | Informe → JSON, HTML, SARIF o terminal | Validación estructural, escape de contenido y límite de salida según el punto de entrada. |

Consultar [contratos de reportes](REPORTING_CONTRACTS.md) y [garantías de archivos y límites](../ARCHITECTURE.md).
