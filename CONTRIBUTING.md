# Contribuir a NEXA ScriptGuard

Este proyecto es experimental y defensivo. Toda detección debe presentarse como una señal para revisión, no como prueba de malicia.

1. Abra un issue describiendo el comportamiento esperado y los límites.
2. Añada casos sintéticos positivos, negativos y ambiguos al corpus.
3. Mantenga el análisis en modo estático: nunca ejecute el script analizado ni recomendaciones como parte de una prueba.
4. Mantenga IDs/versiones de reglas estables, ubicaciones exactas, explicación y procedimiento de verificación.
5. Ejecute:

   ```powershell
   python -m pip install ".[test]"
   python -m unittest discover -s tests -v
   cargo fmt --manifest-path rust\nexa-scriptguard-helper\Cargo.toml -- --check
   cargo test --manifest-path rust\nexa-scriptguard-helper\Cargo.toml --all-targets
   cargo clippy --manifest-path rust\nexa-scriptguard-helper\Cargo.toml --all-targets -- -D warnings
   ```

   La suite valida JSON con `tests/schemas/nexa-report-1.0.schema.json` (contrato propio, no estándar externo) y SARIF 2.1.0 con el esquema oficial OASIS. Para SARIF descarga el esquema público por HTTPS y verifica su SHA-256; no envía reportes ni contenido del usuario. Sin conexión, establezca `NEXA_SARIF_SCHEMA_PATH` a una copia local del mismo esquema oficial, cuyo hash también se verifica. La falta de la dependencia, conexión o coincidencia de hash hace fallar las pruebas; no se omite la validación.

6. Documente qué pruebas locales y plataformas sí se ejecutaron. No infiera éxito de CI a partir de la definición del workflow.
7. No incluya credenciales, datos privados, instaladores o scripts de usuarios. No hagas commits o push que incluyan artefactos `.venv/`, `target/` u outputs locales.

## Compatibility

Please open an issue before changing the JSON/SARIF/Rust protocol or rule identifiers. Do not silently treat parser errors or resource exhaustion as a clean analysis. Keep all investigation checks non-executing and document false positives, false negatives, parser limitations, and platform-specific file guarantees.
