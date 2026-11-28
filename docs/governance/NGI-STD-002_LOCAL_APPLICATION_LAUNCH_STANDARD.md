# NGI-STD-002 — LOCAL APPLICATION LAUNCH STANDARD

NextGenAI Infinity mantiene un procedimiento estable de arranque local. Este
estándar complementa [NGI-STD-001](NGI-STD-001_SOFTWARE_DEVELOPMENT.md).

- Distribuir `run-windows.bat` para CMD y PowerShell y `run-linux.sh` para Bash.
  Cada lanzador resuelve la raíz del proyecto y selecciona `.venv` o un
  entorno virtual activo compatible. Los errores de preparación indican cómo
  recuperar el arranque.
- Ofrecer `RUN` mediante instalación explícita en el ámbito del usuario.
  Cualquier cambio persistente del PATH requiere una acción explícita.
- Ejecutar la GUI existente en primer plano, comprobar dependencias y verificar
  la aplicación y su sesión antes de abrir el navegador predeterminado.
  Mostrar solo la dirección base. Permitir cierre con Ctrl+C.
- Escuchar exclusivamente en loopback con token por sesión y puerto dinámico
  asignado por el sistema. Evitar privilegios administrativos y mantener los
  archivos analizados en el equipo.
- Preservar los puntos de entrada cuando cambie el frontend. React, TypeScript,
  Vite y `nextgenai-ui` podrán evolucionar detrás del mismo arranque, con los
  motores Bash y Python y el helper Rust opcional. Cualquier despliegue en
  Vercel tiene un procedimiento independiente.

ScriptGuard conserva `python -m nexa_scriptguard.gui`. Se consultaron en modo
de lectura el árbol raíz, README y empaquetado de HexForge como referencia.
La rama pública consultada carecía de los dos lanzadores en la raíz; el
puerto de ScriptGuard continúa asignándose dinámicamente.
[NEXA HexForge](https://github.com/romim127/NEXA-HexForge)

Ver [instalación y arranque](../development/SETUP.md).
