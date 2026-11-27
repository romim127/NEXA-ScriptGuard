# Testing and validation

## Local commands

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cargo fmt --manifest-path rust\nexa-scriptguard-helper\Cargo.toml -- --check
cargo clippy --manifest-path rust\nexa-scriptguard-helper\Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path rust\nexa-scriptguard-helper\Cargo.toml --all-targets
cargo build --manifest-path rust\nexa-scriptguard-helper\Cargo.toml
```

Tests use synthetic data. They must not execute a script under inspection or
any investigation command from a finding. The Python suite includes parser,
rules, data flow, GUI HTTP integration, redaction, report schemas, ingestion,
and Rust bridge tests. The Rust suite exercises the helper's declared subset.

## CI

`../../.github/workflows/tests.yml` declares six Python jobs (Windows, Ubuntu, and
macOS × Python 3.10 and 3.12). `.github/workflows/rust.yml` declares three
Rust jobs (Windows, Ubuntu, and macOS). A successful workflow definition is
not evidence of a successful run; record exact commit checks in the release
report.

`../../tests/test_report_schemas.py` validates NEXA JSON against the project schema
and SARIF against the official OASIS schema. This does not substitute for
testing a real SARIF consumer. Fuzz testing is not a sustained, coverage-guided
campaign; current smoke tests must not be described as such.

## Frontend de Fase 4

Desde la raíz, `npm ci` instala el lockfile y `npm run typecheck`,
`npm run lint`, `npm test` y `npm run build` verifican fuentes y bundle.
`npm audit --audit-level=moderate` comprueba las dependencias.
`npx playwright install chromium` prepara el navegador de prueba y
`npm run e2e` ejecuta los casos de navegador. Usá `NEXA_PYTHON` para
seleccionar el intérprete y `NEXA_RUN` con la ruta absoluta al lanzador
instalado por pipx para verificar la distribución.

El caso operativo intercepta y rechaza tráfico fuera de loopback. El
caso estático comprueba que el shell de Vite carga bajo un subdirectorio
y que analizar sin sesión local no transmite el archivo.

## SG-UI-001 · Desplazamiento de código y evidencia

Las reglas `pre-wrap` y `overflow-wrap: anywhere` partían las instrucciones
y la evidencia. `CodeBlock` usa `white-space: pre` y scroll horizontal
propio en un bloque enfocable. `EvidenceViewer` lo usa para contenido de
código y conserva el flujo responsive para el texto descriptivo.

Playwright verifica la aplicación local y la demo en 360, 390, 768, 1366 y
1920 px. Los casos miden `clientWidth`, `scrollWidth` y el cambio de
`scrollLeft` por teclado. En 390 px también emulan un gesto táctil de
Chromium. Se compara el texto completo, se comprueba que una línea larga
ocupa un único renglón y se verifica el scroll vertical del documento.

El caso local analiza archivos sintéticos con un marcador que permanecerá
ausente si se inspeccionan como datos. La demo usa una variante de su
fixture solo en el build de prueba. `NEXA_SCROLL_VISUAL_DIR` permite
guardar capturas de ambos casos en 390 y 1366 px.
[Capturas de la corrección](../reports/sg-ui-001)
