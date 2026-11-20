# ♾ NEXA ScriptGuard

**NextGenAI Infinity** · *AI assists. Human verifies. Human decides.*

NEXA ScriptGuard es un analizador estático experimental de scripts Bash. No ejecuta el archivo inspeccionado ni los comandos que recomienda para investigarlo. Un análisis limpio **no** demuestra que el script sea seguro.

## Instalación

Requiere Python 3.10 o posterior. El paquete instala el runtime Tree-sitter y la gramática Bash oficial:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

En Linux/macOS, activar el entorno con `source .venv/bin/activate`. La gramática [`tree-sitter-bash`](https://github.com/tree-sitter/tree-sitter-bash) está bajo MIT; su binding publica wheels para Windows, Linux y macOS. El parser ofrece árbol sintáctico y posiciones de origen, pero no interpreta toda la semántica de Bash ni ejecuta expansiones.

## Uso

### Interfaz gráfica local en Windows

Desde la raíz del repositorio y con las dependencias instaladas:

```powershell
.\.venv\Scripts\python.exe -m nexa_scriptguard.gui
```

Se abre el navegador; si no ocurre, copie la URL privada que aparece en la consola. Seleccione un `.sh`, pulse **Analizar archivo** y revise el estado, las evidencias redactadas y las recomendaciones. Los botones exportan JSON, HTML y SARIF mediante descargas del navegador. La interfaz usa el motor existente, no ejecuta el script y conserva su estado incompleto. Mantenga la consola abierta; `Ctrl+C` detiene el servicio.

El servidor escucha solo en `127.0.0.1`, en un puerto aleatorio, y utiliza un token de sesión: no comparta la URL ni la consola. Se conserva solo el último resultado; si otra pestaña inicia un análisis, la exportación anterior exige analizar de nuevo. El navegador decide el destino y cómo resolver colisiones al descargar; la garantía de no sobrescritura de la CLI no se aplica a estas descargas. La redacción es heurística, no garantiza eliminar todos los secretos. Los límites de la GUI usan los valores predeterminados descritos abajo y el tiempo/memoria no son cuotas duras. El helper opcional puede habilitarse con `--rust-helper` seguido de la ruta a un ejecutable Rust de confianza.

### Línea de comandos

```text
python -m nexa_scriptguard script.sh --view plain --json report.json
python -m nexa_scriptguard script.sh --html report.html --sarif report.sarif
python -m nexa_scriptguard script.sh --fail-on high
```

Los destinos de reporte deben ser nuevos. NEXA no reemplaza archivos existentes; la publicación crea cada destino atómicamente sin sobrescritura, pero un conjunto de varios formatos no es una transacción atómica frente a una caída abrupta. Cree el directorio de reportes antes de iniciar el análisis.

La redacción de secretos y rutas sensibles es best-effort y está activa por defecto en terminal y archivos. `--include-sensitive-evidence` es una opción explícita para incluir evidencia sin redacción; los controles de terminal se siguen escapando. Aun redactado, un hash SHA-256 puede permitir correlación con un archivo conocido. Revise los reportes antes de compartirlos.

Los límites pueden ajustarse con `--max-input-bytes`, `--max-findings`, `--max-evidence-chars`, `--max-total-evidence-chars`, `--max-output-bytes`, `--max-memory-bytes`, `--max-ast-nodes` y `--timeout-seconds`. El parser Tree-sitter no es preemptible; el límite de memoria es una estimación, no una cuota dura de memoria nativa. Si se alcanza un límite, un error de parseo o falta el parser, el reporte indica `analysis_status: incomplete` y la CLI devuelve `3`; nunca equivale a un resultado limpio.

### Compatibilidad y Rust

`--compat-heuristics` habilita expresamente las heurísticas de regex previas; el resultado se etiqueta `legacy-regex-compatibility` y siempre es incompleto. El helper Rust es un proceso independiente, opcional:

```powershell
cargo build --manifest-path rust\nexa-scriptguard-helper\Cargo.toml
python -m nexa_scriptguard script.sh --rust-helper rust\nexa-scriptguard-helper\target\debug\nexa-scriptguard-helper.exe
```

Python envía por `stdin` los bytes ya acotados de la entrada y Rust devuelve resultados por el protocolo JSON `1.0` / `json-v1-stdin`; así ambos usan el mismo snapshot y hash sin crear una copia temporal de usuario. Rust cubre solo las señales SG-001 y SG-002 en una misma línea; no comparte el parser ni el análisis de flujo Python.

### Códigos de salida

- `0`: análisis completo sin alcanzar el umbral `--fail-on`.
- `2`: análisis completo con hallazgos que alcanzan `--fail-on`.
- `3`: análisis incompleto, compatibilidad heurística, timeout o límite alcanzado.
- `4`: error operativo de entrada, reporte o integración.

## Alcance actual

Se reconocen comandos Bash mediante la gramática Tree-sitter; se detectan las reglas del [catálogo](docs/RULES.md) y se correlacionan algunas asignaciones literales y múltiples saltos de variables con pipes/intérpretes y cargas de archivos. El flujo se marca como posible o indeterminado, no como prueba de ejecución.

No se modelan por completo expansiones, valores de entorno, `source`, todos los ámbitos, todas las ramas, comandos externos, comportamiento del sistema operativo ni sintaxis dinámica. Los errores sintácticos de Tree-sitter y los constructs que no se puedan analizar dejan constancia de análisis incompleto; los constructs aceptados por la gramática aún pueden requerir revisión humana.

## Seguridad, arquitectura y contribución

- [Arquitectura y límites](docs/ARCHITECTURE.md)
- [Catálogo de reglas](docs/RULES.md)
- [Procedimiento para el instalador de Ollama](docs/Ollama-analysis.md)
- [Roadmap](docs/ROADMAP.md)
- [Política de seguridad](SECURITY.md)
- [Contribuciones](CONTRIBUTING.md)
- [Cambios](CHANGELOG.md)
- [English README](README.en.md)

No ejecute `demo_example.sh`: contiene instrucciones deliberadamente sospechosas. Solo analícelo como texto.

## Calidad

En el repositorio, ejecute:

```powershell
python -m pip install ".[test]"
python -m unittest discover -s tests -v
cargo test --manifest-path rust\nexa-scriptguard-helper\Cargo.toml
cargo clippy --manifest-path rust\nexa-scriptguard-helper\Cargo.toml --all-targets -- -D warnings
```

CI declara trabajos para Windows, Linux y macOS. Su configuración no demuestra por sí sola que cada ejecución remota haya pasado.
La suite obtiene el esquema SARIF oficial por HTTPS y verifica su hash; para validación sin conexión se puede definir `NEXA_SARIF_SCHEMA_PATH` a una copia idéntica. JSON se valida contra un esquema versionado propio, no contra un estándar externo. Véase [Contribuciones](CONTRIBUTING.md).

**THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.**
