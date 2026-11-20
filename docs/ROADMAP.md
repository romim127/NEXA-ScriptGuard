# Roadmap técnico

Este roadmap registra trabajo incompleto, no capacidades anunciadas como terminadas.

## P0 — endurecimiento verificable

- Medir memoria real en Windows/Linux/macOS y evaluar límites nativos para parsing.
- Validar symlink outputs también en Windows CI con permisos disponibles; probar hardlinks, carreras, rollback parcial y caída durante publicación.
- Ampliar corpus sintético de secretos, rutas, controles, serialización y alias de archivos; documentar redacción no exhaustiva.

## P1 — contratos y compatibilidad

- Integrar un consumidor SARIF real y ampliar pruebas de interoperabilidad. La suite ya valida contra el contrato JSON versionado del proyecto y el esquema OASIS SARIF 2.1.0 oficial.
- Comprobar la interpretación de `columnKind: unicodeCodePoints` con consumidores SARIF reales, especialmente para caracteres Unicode supplementary.
- Medir y publicar presupuestos de tiempo/memoria; considerar cuotas duras por proceso si se adopta un mecanismo seguro multiplataforma.
- Fijar un schema/version policy para IDs, regla y compatibilidad del proceso Rust.

## P2 — análisis semántico

- Resolver alcances y valores al combinar ramas, funciones, subshells, arrays y reassignments.
- Ampliar sources/sinks y transformaciones con una IR de flujo explícita, sin ejecutar sustituciones.
- Evaluar parser/fixtures para versiones Bash declaradas y construir corpus etiquetado de falsos positivos/negativos.

## P3 — verificación y release

- Añadir fuzzing guiado por cobertura con presupuesto, minimización de casos y ejecución programada; el test actual es fuzz smoke determinista, no fuzzing continuo.
- Añadir compatibilidad efectiva de CI para Windows/Linux/macOS y comprobar los resultados remotos antes de anunciarlos.
- Decidir si Rust seguirá siendo helper opcional lineal o adoptará una gramática/parser compatible; actualmente no alcanza paridad semántica.

## Fuera de alcance de esta entrega

- Análisis de binarios ejecutables, PowerShell, red/descarga en tiempo de análisis y ejecución instrumentada.
- Descarga automática del instalador de Ollama o ejecución de instaladores/scripts.
