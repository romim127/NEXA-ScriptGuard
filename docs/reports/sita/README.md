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

## SG-SITA-001

La regresión cubre reportes anteriores, cobertura disponible, procedencia
sin cobertura, omisión por plazo o presupuesto, y cobertura parcial con
escaneo base completo. Se verifica el mismo estado en el panel React y
en los contratos de CLI, JSON, HTML y SARIF. Las pruebas consumen
`impact_omission` o `impact_analysis.coverage` sin interpretar mensajes
de limitación.

La repetición local obtuvo 102 pruebas Python aprobadas y dos omitidas por
plataforma, seis pruebas Rust, nueve Vitest y siete Playwright aprobadas.
SG-UI-001 conservó los cinco anchos y el gesto táctil a 390 px desplazó
194 px en local y demo. Las capturas se regeneraron con la etiqueta de
cobertura visible.

## SG-RUN-001

Durante el diagnóstico, VS Code conservaba una pestaña de ScriptGuard en
`127.0.0.1:49497` sin un proceso escuchando. Otra instancia en el puerto
50365 seguía operativa, servía el bundle actual y rechazaba peticiones sin
sesión con HTTP 403. La pestaña sin servidor explica el fallo de conexión
en ese origen. La solicitud original no se conservó para inspección.

El entry point existente admite `RUN scriptguard` y `RUN`. Comprueba por
HTTP la interfaz, sus recursos y la sesión antes de entregar la URL al
navegador. El proceso permanece en primer plano y termina con Ctrl+C.
La terminal identifica el paquete y el intérprete y muestra solo la
dirección base.

En Windows se instaló la rueda del proyecto en `.venv` y se registró su
`RUN.exe` en una carpeta dedicada del PATH de usuario. Se probó desde la
raíz y desde TEMP en PowerShell integrado de VS Code. Ctrl+C devolvió el
control y cerró el puerto de la instancia de prueba. Playwright pasó los
once criterios funcionales y una comprobación local adicional con el
archivo de aceptación, que no se versionó. Las dos solicitudes de análisis
recibieron HTTP 200 en la misma sesión y se verificaron las referencias
SITA y las descargas JSON, HTML y SARIF.

## SG-SITA-UX-002

Capturas del panel compartido sobre informes de prueba. La versión local
usa un archivo sintético de la suite. La demo usa su reporte precomputado.

| Vista | Local | Demo |
| --- | --- | --- |
| Compacta, escritorio | [1366 px](local-1366-compact.png) | [1366 px](demo-1366-compact.png) |
| Expandida, escritorio | [1366 px](local-1366.png) | [1366 px](demo-1366.png) |
| Compacta, móvil | [390 px](local-390-compact.png) | [390 px](demo-390-compact.png) |
| Expandida, móvil | [390 px](local-390.png) | [390 px](demo-390.png) |

Se verificó con teclado que el destino exacto enfoca y resalta `eval`, y
que localizar la línea enfoca el bloque y retira el resaltado. Vitest
cubre las referencias externas sin botón y los rangos descartados cuando
el texto no coincide o está truncado. Las pruebas de SG-UI-001 recorren
360, 390, 768, 1366 y 1920 px en local y demo.
