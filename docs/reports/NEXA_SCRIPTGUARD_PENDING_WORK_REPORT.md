# NEXA ScriptGuard — Informe de trabajo pendiente

Fecha de corte inicial: 20 de noviembre de 2026; actualización vigente:
25 de noviembre de 2026. Para la evolución Bash/Python,
véase también [NEXA_SCRIPTGUARD_PYTHON_EVOLUTION_REPORT.md](NEXA_SCRIPTGUARD_PYTHON_EVOLUTION_REPORT.md).

Las secciones históricas que siguen al estado vigente conservan el snapshot
original del 20 de noviembre. En caso de contradicción, prevalecen el estado
vigente de este informe y el
[informe de consolidación](NEXA_SCRIPTGUARD_CONSOLIDATION_REPORT.md).

## Estado vigente al 25 de noviembre

La matriz de CI del head `950fc352bc58fe412897b302c4043710b161d886` tiene
nueve jobs únicos aprobados (seis Python y tres Rust); no cubre cambios
posteriores. La repetición local dio 85 pruebas Python (84 aprobadas, una
omitida por falta de privilegio local para crear symlinks) y seis pruebas Rust,
con `fmt`, Clippy y build aprobados.

La prueba visual local seleccionó `demo_example.sh` y mostró dos hallazgos
HIGH sin ejecutar el script. Persisten dos verificaciones distintas: el
navegador integrado no guardó físicamente JSON/HTML/SARIF, y no hay un
consumidor SARIF instalado. La descarga y la interoperabilidad real siguen
pendientes; no se instalaron extensiones.

Se agregaron 15 documentos de arquitectura/gobernanza/requisitos/decisiones/
desarrollo y se evaluó Vercel sin desplegar. La decisión es conservar el modo
local. Para matriz, resultados exactos y próximos pasos prevalece el
[informe de consolidación](NEXA_SCRIPTGUARD_CONSOLIDATION_REPORT.md).

## Alcance y estado

La interfaz local consume el analizador existente, permite cargar archivos Bash
sin ejecutarlos, presenta resultados y exporta JSON, HTML y SARIF. Incorpora
una recreación vectorial del escudo basada en la imagen aportada. La corrección
de timeout y sus pruebas deterministas forman parte de los cambios preparados.
La ausencia de hallazgos no demuestra que un script sea seguro.

Este informe registra pendientes y riesgos, no certifica que las capacidades
parciales estén terminadas. Los detalles de implementación y la matriz completa
están en el [informe de implementación](NEXA_SCRIPTGUARD_IMPLEMENTATION_REPORT.md).

## Prioridades para publicación

| Prioridad | Pendiente | Criterio de aceptación |
|---|---|---|
| P0 | CI de la evolución Bash/Python: los seis jobs Python y tres Rust aprobaron para `dcd0615`; ver enlaces en el informe de evolución. El usuario informó también aprobación para `725986e`. | Verificar los resultados reales de cualquier commit posterior antes de merge. |
| P0 | Symlink de destino existente: la prueba omitida localmente pasó en el job Windows/Python 3.12 de CI de `dcd0615`, preservando el archivo objetivo. | Confirmar escenarios adicionales o el equipo local solo si se necesitan; no modificar configuración sin autorización. |
| P0 | Comprobar la descarga física desde un navegador de usuario. | Guardar JSON, HTML y SARIF, abrirlos, comprobar contenido y estado, y verificar el comportamiento del navegador frente a un nombre existente. |
| P0 | Conservar el escudo aprobado visualmente por la persona responsable del diseño. | Mantener intacto el SVG aprobado y comprobar su presentación al ampliar la interfaz, sin volver a solicitar aprobación del diseño. |
| P1 | Validar redacción y seguridad de las salidas compartidas. | Ampliar corpus sintético de secretos y rutas, controles, casos negativos y revisar resultados antes de compartir. La redacción actual es heurística. |
| P1 | Validar SARIF con consumidores reales. | Importar reportes completos e incompletos en al menos un consumidor y comprobar ubicaciones, reglas y mensajes. La validación actual de esquema no garantiza interoperabilidad. |
| P1 | Ampliar análisis y corpus Bash. | Cubrir por regla casos positivos, negativos y ambiguos; definir semántica y limitaciones de ámbitos, funciones, subshells, ramas, expansiones y `source`. |
| P1 | Ampliar paridad y contrato del helper Rust. | Negociar límites y verificar diferencialmente las capacidades compartidas sin afirmar paridad total; hoy Rust cubre solo señales SG-001/SG-002. |
| P2 | Fortalecer límites de recursos y fuzzing. | Evaluar aislamiento del parser con cuotas medibles por plataforma y fuzzing guiado por cobertura; hoy el timeout es cooperativo y la memoria estimada. |
| P2 | Revisar concurrencia y publicación de archivos entre plataformas. | Repetir pruebas de hardlinks, carreras, rollback y fallo abrupto en los tres sistemas; documentar garantías realmente observadas. |
| Bloqueado | Análisis del instalador oficial de Ollama. | Obtener autorización y artefacto verificable, aplicar el procedimiento documentado y no ejecutarlo; no descargarlo sin autorización. |

## Validación local de esta preparación

- Windows, Python 3.14.3: `python -m unittest discover -s tests -v`,
  **74 pruebas: 73 aprobadas y una omitida** en 20,980 s. La omisión se debe a
  `WinError 1314` al crear un symlink.
- Rust: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`,
  `cargo test` (**6 aprobadas**) y `cargo build`, usando
  `--manifest-path rust\nexa-scriptguard-helper\Cargo.toml`: aprobados.
- Interfaz en navegador: selección y análisis de `demo_example.sh` como datos,
  dos hallazgos, visualización de incompletitud y de HTML no confiable como
  texto; las exportaciones respondieron HTTP 200. No se verificó guardado
  físico mediante el navegador automatizado.
- El escudo SVG se comprobó visualmente en navegador; las nueve pruebas de GUI
  pasaron y el SVG se parseó como XML.

No se ejecutaron localmente los cambios en Linux, macOS ni Python 3.10/3.12.
La CI posterior a la publicación y el estado remoto deben comprobarse por
separado; una configuración de workflow no equivale a una ejecución aprobada.

## Riesgos operativos

El servidor escucha solo en loopback y usa una URL privada; no protege frente
a procesos locales o extensiones maliciosas. El navegador decide el destino y
las colisiones de las descargas, por lo que la garantía de no sobrescritura de
la CLI no se aplica a ellas. El parser nativo no es preemptible, el límite de
memoria es estimado y el tiempo de socket es por operación. La redacción puede
omitir secretos, y los hashes aún permiten correlacionar archivos. Un análisis
incompleto debe tratarse como desconocido.
