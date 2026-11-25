# NEXA ScriptGuard · Informe de consolidación

Verificación del 25 de noviembre de 2026. Candidato del [PR #1](https://github.com/romim127/NEXA-ScriptGuard/pull/1): `950fc352bc58fe412897b302c4043710b161d886`.

GitHub registró el merge del PR #1 en `74a1c3cc959950c2061d48855b7f69921d7e5ace`. La gobernanza y la demostración sintética se tramitan en un cambio independiente.

| Control | Resultado |
|---|---|
| Suite local Windows | 85 pruebas para Bash, Python, CLI, GUI y reportes. 84 aprobadas y una omitida porque el entorno local no permite crear symlinks. |
| Helper Rust | Seis pruebas aprobadas con `cargo test --locked --all-targets`. |
| GitHub Actions del candidato | Seis jobs Python y tres Rust aprobados. El runner Windows verificó el caso de symlinks. |
| Descargas físicas | Edge guardó JSON, HTML y SARIF para Bash completo, Python completo y Bash incompleto en directorios aislados. Los conteos de JSON y SARIF coincidieron. |
| Colisiones del navegador | Edge visible, con la política normal y descargas automáticas en un perfil nuevo, conservó un JSON preexistente y creó `nexa-scriptguard-report (1).json`. El modo de automatización CDP `allow` reemplazó el archivo sintético, por lo que la política depende del navegador y su configuración. |
| Herramienta SARIF | Microsoft SARIF Multitool 5.9.0 aceptó los tres archivos con código 0 en .NET 10 mediante `DOTNET_ROLL_FORWARD=Major`. Emitió SARIF2005 por el metadato opcional `informationUri`. |
| Compatibilidad y redacción | Bash registró SG-001/SG-002, Python PY-001/PY-003/PY-004/PY-005 y Bash incompleto conservó SG-001 y el diagnóstico de gramática. Las exportaciones omitieron la credencial sintética y el HTML escapó el fragmento de prueba. |

La prueba usó `demo_example.sh`, `tests/corpus/python_gui_example.py` y `tests/corpus/gui_incomplete.sh` como datos por loopback. Se verificaron las reglas, ubicaciones y mensajes del SARIF. El navegador controló sus descargas. Las garantías de escritura exclusiva de la CLI se cubrieron en la suite local.

Los resultados de CI corresponden al SHA del candidato. [Workflow Python](https://github.com/romim127/NEXA-ScriptGuard/actions/runs/44791992557) · [Workflow Rust](https://github.com/romim127/NEXA-ScriptGuard/actions/runs/44791992431).

## Gobernanza y despliegue

El [árbol del proyecto](../architecture/PROJECT_TREE.md) incluye la arquitectura, gobernanza, requisitos, trazabilidad, ADR y seguimiento del desarrollo. La evaluación de [Vercel](../decisions/ADR-0003-VERCEL-EVALUATION.md) prioriza procesamiento en el navegador sujeto a paridad de los motores. Un adaptador remoto requeriría pruebas de dependencias nativas, procesamiento sin estado y controles de privacidad y abuso. La demostración sintética tiene un alcance separado de un servicio de análisis.

## Inicio local en Windows

```powershell
.\.venv\Scripts\python.exe -m nexa_scriptguard.gui
```
