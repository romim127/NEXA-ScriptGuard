# Política de seguridad

NEXA ScriptGuard es un analizador estático experimental. No constituye una frontera de seguridad, sandbox ni certificación; ningún hallazgo o resultado limpio demuestra por sí solo intención o ausencia de riesgo. El analizador no ejecuta scripts examinados ni comandos de investigación.

## Protección de datos

- Los bytes de entrada se leen bajo un límite y el SHA-256 identifica el contenido leído. No se garantiza una instantánea coherente si otro proceso modifica el archivo concurrentemente.
- Terminal y archivos de reporte aplican redacción best-effort por defecto, pero no pueden reconocer todos los formatos de credenciales. `--include-sensitive-evidence` desactiva la redacción de secretos/rutas; requiere autorización del usuario.
- El SHA-256 permanece disponible en salidas redactadas y puede correlacionarse con un archivo conocido. Las rutas pueden revelar información. Revise permisos y contenido antes de compartir.
- No sobrescriba reportes previos automáticamente: los destinos existentes son rechazados. La publicación de varios formatos no es una transacción global frente a una caída abrupta.

## Reporte de problemas

No publiques credenciales, datos privados, instaladores o scripts de terceros. Usa GitHub Private Vulnerability Reporting si está habilitado; si no, solicita un canal privado al mantenedor.

## Alcance

Python usa Tree-sitter Bash para sintaxis y heurísticas, no una evaluación completa del runtime. El helper Rust es un proceso separado de alcance lineal reducido. `--compat-heuristics`, errores de parseo, límite alcanzado o falta de parser se informan como análisis incompleto. Véase [arquitectura](docs/ARCHITECTURE.md) y [roadmap](docs/ROADMAP.md).
