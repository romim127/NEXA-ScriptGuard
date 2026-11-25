# Estado de implementación

Bash, Python, CLI, GUI, escudo, exportaciones y helper Rust opcional quedaron integrados en `main` mediante el PR #1, con merge en `74a1c3cc959950c2061d48855b7f69921d7e5ace`. La suite Windows del 25 de noviembre de 2026 ejecutó 85 pruebas, con 84 aprobadas y una omitida por permisos de symlink. Rust aprobó seis pruebas. Los workflows de Python y Rust del PR #1 aprobaron en `950fc352bc58fe412897b302c4043710b161d886`.

El [informe de consolidación](../reports/NEXA_SCRIPTGUARD_CONSOLIDATION_REPORT.md) conserva el historial y las evidencias. Los trabajos abiertos y sus dependencias figuran en [tareas pendientes](PENDING_TASKS.md).

El arranque local dispone de `run-windows.bat`, `run-linux.sh` y `RUN`. Los
tres inician la GUI existente. La suite comprueba el traspaso al navegador,
puertos independientes, cierre y ejecución desde un directorio externo.
[NGI-STD-002](../governance/NGI-STD-002_LOCAL_APPLICATION_LAUNCH_STANDARD.md)
