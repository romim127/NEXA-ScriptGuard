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

## Evaluación de hosting

El estándar de arranque local conserva los lanzadores y el comando `RUN`
durante la evolución del frontend. [NGI-STD-002](governance/NGI-STD-002_LOCAL_APPLICATION_LAUNCH_STANDARD.md)

La Fase 4 empaqueta la interfaz compilada en la distribución Python.
[ADR 0004](decisions/ADR-0004-REACT-LOOPBACK.md)

La decisión actual es conservar el producto local-first. No se añadió
configuración ni se desplegó NEXA en Vercel. El análisis del runtime Python,
los límites de payload/filesystem, los costos publicados, la condición de uso
del plan Hobby y los controles pendientes están en
[`decisions/ADR-0003-VERCEL-EVALUATION.md`](decisions/ADR-0003-VERCEL-EVALUATION.md).
Un futuro servicio requeriría aprobación separada para transferir scripts,
revisar privacidad/abuso/retención y probar el parser nativo en el runtime
objetivo; no se debe inferir compatibilidad por la mera disponibilidad de una
función Python.
