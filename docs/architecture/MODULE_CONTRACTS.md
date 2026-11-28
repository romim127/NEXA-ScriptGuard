# Contratos de módulos

| Módulo | Entrada y salida | Dependencias, errores y límites |
|---|---|---|
| `gui.py` y `gui_assets/` | Archivo seleccionado y token local → informe y descargas | Loopback, tamaño y concurrencia acotados. Rechaza solicitudes inválidas y exportaciones con ID obsoleto. |
| `frontend/src/services/api.ts` | `POST /analyze` envía bytes del archivo con `Content-Type: application/octet-stream`, `X-Nexa-Filename` codificado y token. Devuelve reporte JSON e ID en `X-Nexa-Result`. | Valida contenido, campos y estado de respuesta. Usa el mismo origen y rechaza redirecciones. |
| Cliente de exportación | `GET /export/{json,html,sarif}` envía token e ID del resultado. Recibe bytes y MIME del formato. | Python verifica sesión, resultado vigente y tamaño. El navegador gestiona nombre y destino. |
| `packages/nextgenai-ui` | Props tipadas, nodos React y eventos de usuario → componentes accesibles. | Presentación reutilizable sin acceso directo a archivos, red ni motores. |
| `cli.py` y `__main__.py` | Ruta, opciones y destinos → terminal, archivos y código de salida | Ingestión y reportes compartidos. Falla explícitamente ante colisión y error de publicación. |
| `ingestion.py`, `limits.py` | Ruta o bytes → snapshot con hash y presupuestos | Valida lectura regular y bytes. Rechaza entradas fuera de los límites. |
| `analysis.py` | Snapshot y extensión → resultado común | Despacha `.sh` y `.py`. Gramática, plazo cooperativo y límites de evidencia pueden producir un resultado incompleto. |
| `parser.py`, `rules.py`, `bash.json`, `contextual.py`, `dataflow.py`, `compat.py`, `legacy.py` | Bash → nodos, hallazgos y correlaciones | Tree-sitter y catálogo Bash. La compatibilidad heurística se identifica como incompleta. |
| `python_analysis.py`, `python_rules.json` | Python → hallazgos PY-001 a PY-008 | AST estándar, resolución conservadora y límite de nodos. La versión del intérprete determina la gramática. |
| `rust_bridge.py`, helper Rust | Snapshot Bash → JSON auxiliar versionado | Ejecutable de confianza, stdin acotado, timeout y validación de protocolo. |
| `model.py`, `classification.py`, `redaction.py` | Hallazgos → informe ordenado y evidencia compartible | Identificadores estables, límites de evidencia y redacción heurística. |
| `reports.py` | Informe → JSON, HTML, SARIF o terminal | Validación estructural, escape de contenido y límite de salida según el punto de entrada. |

Consultar [contratos de reportes](REPORTING_CONTRACTS.md) y [garantías de archivos y límites](../ARCHITECTURE.md).

El explorador React usa campos existentes de reporte (`file`, `lines`) y hallazgo (`engine`). Filtra y ordena en memoria sin modificar el reporte exportado. El consumidor estático usa props públicas de `@nextgenai/ui` y reportes precomputados, sin invocar el servicio local.

El atributo `data-max-input-bytes` del HTML local anuncia el límite vigente
para validar la selección en ambas GUI. El límite sigue bajo control de
Python y se comprueba también en `POST /analyze`.

El contrato opcional de impacto 1.0 por hallazgo y sus límites se especifican en [SITA](SITA.md).
