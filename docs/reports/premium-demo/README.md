# Fase 5.1 · Revisión visual

Capturas del build de producción de la demo en Edge, con zoom al 100 %.
El aviso, los contadores y las tarjetas se muestran con el fixture sintético
del repositorio.

| Vista | Viewport | Captura |
|---|---:|---|
| Escritorio | 1440 × 1000 | [escritorio.png](escritorio.png) |
| Tablet | 820 × 1060 | [tablet.png](tablet.png) |
| Móvil | 390 × 844 | [movil.png](movil.png) |

Los paneles y tarjetas usan dos columnas en escritorio y tablet y una en
móvil. Los detalles técnicos y la evidencia se abren con controles nativos.
Las métricas provienen del reporte y los formatos descargan el fixture
completo. Bash, Python y el helper Rust se presentan como capacidades de
la aplicación local.

Playwright verifica además un viewport de 320 px, foco y navegación por
teclado, contraste de controles y métricas, aviso visible al desplazar y
descargas con los encabezados definidos en `vercel.json`.
