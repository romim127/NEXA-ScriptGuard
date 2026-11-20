# Changelog

## 0.5.0a1 — implementación modular inicial

- Consolida el contrato JSON con un esquema propio, valida SARIF contra el esquema oficial OASIS en la suite y declara sus columnas Unicode.
- Corrige la omisión del título en el modelo serializado que impedía mostrar hallazgos en HTML y terminal Rich; amplía pruebas de redacción y seguridad de publicación.
- Introduce parser Bash basado en Tree-sitter, IR con rangos, reglas AST y correlación de variables de alcance conservador.
- Añade modelo de hallazgos común, hash de origen, redacción compartible, límites configurables y estado explícito incompleto.
- Endurece publicación de reportes: no sobrescribe destinos existentes, rechaza symlink y detecta hardlinks existentes al input.
- Añade reportes JSON/HTML/SARIF/terminal desde un modelo compartido y helper Rust opcional por proceso JSON versionado.
- Añade corpus sintético, fuzz smoke determinista y pruebas de seguridad/CLI.
- Las funciones Python antiguas `inspect`, `render_html` y `render_sarif` se conservan temporalmente como compatibilidad de API interna; el CLI usa la ruta modular.

La versión es alpha. El roadmap y el reporte de implementación enumeran capacidades, pruebas y límites no terminados.
