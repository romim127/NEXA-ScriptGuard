# NEXA ScriptGuard — Evolución del análisis Python

Fecha de corte: 20 de noviembre de 2026. Rama de trabajo:
`feat/python-static-analysis`, creada desde `725986e`. Implementación:
`dcd0615`. [Pull request #1](https://github.com/romim127/NEXA-ScriptGuard/pull/1),
abierto como borrador; no fusionado.

## Implementación

- `.sh` utiliza el motor Bash existente; `.py` se analiza con `ast` de la
  biblioteca estándar. Otras extensiones se rechazan. El archivo analizado no
  se ejecuta ni importa. `--compat-heuristics` es exclusivo de Bash.
- El escudo aprobado `gui_assets/infinity-shield.svg` permanece idéntico al
  de `725986e`. La interfaz acepta `.sh` y `.py`, muestra el lenguaje y utiliza
  el modelo, la redacción y los renderizadores JSON, HTML y SARIF existentes.
- Las reglas PY-001 a PY-008 cubren evaluación dinámica, shell en subprocess,
  pickle, evaluación de contenido de red, posibles secretos literales,
  funciones de ejecución de comandos, construcción dinámica de SQL y
  `verify=False` en clientes HTTP seleccionados. Las coincidencias no prueban
  que se ejecuten ni que sean maliciosas. El catálogo y sus límites están en
  [RULES.md](../RULES.md).
- El motor reconoce alias de importación sin conflictos y una correlación
  limitada entre fuente de red y evaluación, marcada `possible`. No realiza
  resolución completa de ámbitos, tipos, flujo de control ni llamadas
  indirectas. La sintaxis soportada depende de la versión de Python anfitriona.
- La redacción identifica también nombres con prefijos, anotaciones sencillas
  y valores entrecomillados; sigue siendo heurística y no garantiza protección
  completa. El helper Rust no analiza `.py`; no se afirma paridad.

## Validación local

- Windows/Python 3.14.3: `python -m unittest discover -s tests -v`: **84
  pruebas, 83 aprobadas y 1 omitida**, 23,563 s. La omisión es la creación de
  symlink por `WinError 1314`; no se modificaron permisos ni configuración.
- Pruebas positivas y negativas para las ocho reglas, alias, shadowing,
  reasignación, sintaxis inválida, archivo vacío, límites, redacción, no
  ejecución, selección, corpus Bash y reportes. JSON se valida contra el
  esquema NEXA y SARIF contra el esquema oficial OASIS para casos Python
  completos e incompletos.
- Rust: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`,
  `cargo test` (**6 aprobadas**) y `cargo build`, con
  `--manifest-path rust\nexa-scriptguard-helper\Cargo.toml`: aprobados.
- GitHub Actions verificó el commit de implementación `dcd0615`: los seis
  jobs Python (Windows, Ubuntu y macOS con 3.10 y 3.12) y los tres jobs Rust
  aprobaron tanto para el push como para el pull request. Consultar los
  [jobs Python del PR](https://github.com/romim127/NEXA-ScriptGuard/actions/runs/44789980406)
  y [jobs Rust del PR](https://github.com/romim127/NEXA-ScriptGuard/actions/runs/44789980214).
  Los checks de cualquier commit posterior deben verificarse por separado.
- En navegador local, el archivo sintético Python produjo cuatro hallazgos y
  la credencial de ejemplo apareció redactada. El escudo cargó en una vista
  de 375 píxeles sin desbordamiento horizontal. Se verificó por hash que el
  SVG coincide con el de la base. No se ejecutó el archivo de ejemplo.
- El navegador automatizado no emitió el evento de descarga; sigue sin
  comprobarse el guardado físico, las colisiones y la ausencia de
  sobrescrituras silenciosas desde un navegador de usuario. Las respuestas
  HTTP y los contratos no sustituyen esa prueba.

## Verificaciones pendientes y bloqueos

1. Verificar los checks de cualquier commit posterior al `dcd0615` y las
   protecciones de rama antes del merge. El usuario comunicó que en `725986e`
   también aprobaron los workflows Python y Rust. `gh` no estaba autenticado;
   los resultados de `dcd0615` se consultaron mediante integración GitHub.
2. Ejecutar la prueba real de symlink con permisos apropiados sin cambiar
   ajustes del sistema sin autorización adicional.
3. Confirmar descargas físicas JSON, HTML y SARIF y comportamiento ante nombres
   existentes. El navegador controla la ruta y las colisiones, y no hereda la
   garantía no-clobber de la CLI.
4. Probar reportes SARIF completos e incompletos en un consumidor real; el
   esquema validado no demuestra interoperabilidad. No se identificó un
   consumidor instalado durante esta intervención.
5. Mantener como posteriores fuzzing guiado por cobertura, aislamiento del
   parser, cuotas duras y ensayos multiplataforma de concurrencia y rollback.
   El parseo AST y Tree-sitter no es preemptible; la memoria es estimada.
6. El instalador de Ollama permanece fuera de alcance y no fue descargado ni
   ejecutado.

Inicio en Windows desde la raíz con dependencias instaladas:

```powershell
.\.venv\Scripts\python.exe -m nexa_scriptguard.gui
```

La publicación requiere revisar los checks y permisos reales. No se declara
merge ni CI exitosa sin evidencia posterior.
