# Estado de implementación

Bash, Python, CLI, GUI, escudo, exportaciones y helper Rust opcional quedaron integrados en `main` mediante el PR #1, con merge en `74a1c3cc959950c2061d48855b7f69921d7e5ace`. La suite Windows del 25 de noviembre de 2026 ejecutó 85 pruebas, con 84 aprobadas y una omitida por permisos de symlink. Rust aprobó seis pruebas. Los workflows de Python y Rust del PR #1 aprobaron en `950fc352bc58fe412897b302c4043710b161d886`.

El [informe de consolidación](../reports/NEXA_SCRIPTGUARD_CONSOLIDATION_REPORT.md) conserva el historial y las evidencias. Los trabajos abiertos y sus dependencias figuran en [tareas pendientes](PENDING_TASKS.md).

El arranque local dispone de `run-windows.bat`, `run-linux.sh` y `RUN`. Los
tres inician la GUI existente. La suite verifica el lanzador desde un
directorio externo y el manejo de apertura y cierre en Windows, Linux y macOS.
En Linux también verifica dos procesos simultáneos, el traspaso a un navegador
de prueba y el cierre de ambos puertos por señal.
[NGI-STD-002](../governance/NGI-STD-002_LOCAL_APPLICATION_LAUNCH_STANDARD.md)

Fase 4 aporta React y NextGenAI UI, cliente TypeScript y comprobación de la
rueda mediante pipx. El servidor y los motores mantienen los contratos
existentes. La referencia anterior se sirve en `/legacy`.
[ADR 0004](../decisions/ADR-0004-REACT-LOOPBACK.md)

Fase 5 implementa filtros, búsqueda, orden, evidencia expandible, navegación por línea, metadatos reales del archivo, enlaces SARIF y demo estática. La suite compara React y legacy. El experimento WASM solo mide muestras acotadas de Python y Bash e inspecciona el helper Rust compilado. [Matriz](PHASE_5_PARITY.md) · [ADR 0005](../decisions/ADR-0005-STATIC-DEMO-WASM-PROBE.md)
