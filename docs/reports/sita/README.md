# Evidencia de aceptación SITA

Capturas de Playwright con Microsoft Edge sobre la aplicación instalada mediante
`RUN` y el build de la demo, con las conclusiones CIA desplegadas.

- Local [1366 px](local-1366.png) y [390 px](local-390.png).
- Demo [1366 px](demo-1366.png) y [390 px](demo-390.png).

Playwright verifica foco y resaltado de `eval` al activar una referencia con
Enter. El informe se recorre en vertical y la comprobación de SG-UI-001 mide el
scroll independiente a 360, 390, 768, 1366 y 1920 px.

## Once criterios locales

1. RUN abre con el selector vacío.
2. El SVG original se conserva y se carga.
3. El diálogo nativo selecciona el archivo.
4. Seleccionar el archivo no emite la solicitud de análisis.
5. Analizar envía la solicitud explícita.
6. El hallazgo muestra severidad, ubicación y evidencia.
7. Se puede recorrer el informe completo verticalmente.
8. La evidencia larga se desplaza horizontalmente sin ajuste de línea.
9. JSON, HTML y SARIF se descargan y conservan el contenido del reporte.
10. La sesión analiza otro archivo sin reiniciar.
11. Los marcadores de ejecución usados por la prueba siguen ausentes.

Las comprobaciones de regresión son automatizadas. La revisión visual humana
sigue pendiente.
