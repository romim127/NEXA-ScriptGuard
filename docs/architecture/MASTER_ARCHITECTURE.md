# Arquitectura maestra

| Estado | Componentes |
|---|---|
| Implementado | GUI de loopback y CLI, ingestión acotada, despacho por extensión, motores independientes Bash y Python, helper Rust opcional para Bash, catálogos, evidencias, clasificación, redacción y exportaciones JSON/HTML/SARIF. |
| Parcial | Correlación contextual y flujo de datos conservadores, redacción heurística y presupuestos cooperativos. El soporte de Python depende de la gramática del intérprete local. |
| Planificado | Incorporación de otros lenguajes mediante despacho explícito, parser, catálogo y corpus propios sobre el contrato común. Modelos locales pequeños como ayuda opcional y revisable. |
| Bloqueado para publicación real | Procesamiento web pendiente de equivalencia de motores, pruebas en runtime objetivo y controles de privacidad y aislamiento. |

La [arquitectura existente](../ARCHITECTURE.md) detalla presupuestos y contratos. El [flujo](DATA_FLOW.md) identifica los límites de confianza y [pruebas y CI](../development/TESTING.md) registra los procedimientos de verificación. La [evaluación web](../decisions/ADR-0003-VERCEL-EVALUATION.md) mantiene separada la evolución de despliegue.

Los lanzadores del repositorio delegan en `python -m nexa_scriptguard.gui`.
El comando instalado `RUN` invoca la misma función. La GUI valida el motor
Bash, abre el navegador y conserva loopback, puerto dinámico y token por sesión.
El punto de entrada es estable para la futura evolución del frontend.
[NGI-STD-002](../governance/NGI-STD-002_LOCAL_APPLICATION_LAUNCH_STANDARD.md)

La Fase 4 sirve el frontend React desde los recursos de la distribución
Python. TypeScript valida el contrato consumido y NextGenAI UI presenta
controles y resultados. Vite se usa durante la compilación. La referencia
anterior queda disponible en `/legacy`. [ADR 0004](../decisions/ADR-0004-REACT-LOOPBACK.md)

La Fase 5 agrega exploración de hallazgos en la GUI local y un consumidor independiente con fixtures estáticos. El análisis WASM integral continúa experimental. [ADR 0005](../decisions/ADR-0005-STATIC-DEMO-WASM-PROBE.md)

SITA agrega una etapa local y acotada de interpretación de hallazgos clasificados. [Arquitectura y matriz](SITA.md).
