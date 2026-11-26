# Fase 5 · Paridad funcional de las GUI

La prueba Playwright abre `/` y `/legacy` por separado con la misma sesión
local. Ejecuta cada fixture con Enter y compara JSON y SARIF por contenido,
HTML por bytes y las tarjetas por los campos visibles. Se excluye la fecha
UTC del JSON. La prueba conserva IDs de reglas, IDs deterministas de
hallazgos, hash, nombre y campos semánticos.

| Criterio | Comparación |
|---|---|
| Carga, detección y análisis Bash | Mismo archivo, lenguaje, estado, hash y reporte con `demo_example.sh`. |
| Carga, detección y análisis Python | Mismo fixture, lenguaje, estado, hash y reporte con `python_gui_example.py`. |
| Criticidad y categorías | Niveles y reglas de cada tarjeta frente al JSON. |
| Evidencias, líneas y columnas | Texto compartible y ubicación de cada tarjeta. En React se expande la evidencia con el control nativo. |
| Explicaciones y recomendaciones | Texto de cada tarjeta frente al resultado del motor. |
| Incompletos y errores | `gui_incomplete.sh` conserva hallazgos y diagnóstico más estado incompleto. Ambas rutas rechazan un archivo con extensión inválida. |
| Límites | Ambas rutas deshabilitan el envío por encima de 5 MiB con la configuración estándar y muestran el motivo. Python conserva la comprobación 413 independiente del cliente. |
| Exportaciones | Descargas físicas de los tres formatos en ambas rutas y comparación semántica. |
| Identidad visual | Mismo SVG canónico y CSS de base. Las pruebas de Python comparan bytes del escudo. |
| Scroll, responsive y accesibilidad básica | Ambas rutas desplazan el documento en viewport estrecho, sin ancho excedente. Se comprueban etiqueta de archivo, activación por teclado y estado anunciado. |
| Mejoras exclusivas de React | Filtros combinables, búsqueda, ordenamiento, navegación por ubicación, evidencia expandible y resumen del parser y motores. |

La comparación cubre fixtures sintéticos seleccionados. La prueba de
accesibilidad cubre navegación y estados básicos, con una auditoría WCAG
integral pendiente. `/legacy` sigue disponible como referencia.

La validación local de Playwright en Edge pasó desde `RUN` instalado con
pipx. Microsoft SARIF Multitool 5.9.0 aceptó los reportes Bash, Python e
incompleto con código 0. El aviso previo por `informationUri` dejó de aparecer.
