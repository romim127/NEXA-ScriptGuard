# Fase 5.1 · Revisión visual

Capturas de los builds de producción en Edge, con zoom al 100 %. La demo
usa el fixture sintético. La aplicación local muestra el dashboard al
abrir y después de analizar el ejemplo Bash del repositorio.

| Vista | Viewport | Captura |
|---|---:|---|
| Escritorio | 1440 × 1000 | [escritorio.png](escritorio.png) |
| Tablet | 820 × 1060 | [tablet.png](tablet.png) |
| Móvil | 390 × 844 | [movil.png](movil.png) |
| Aplicación local al abrir | 1440 × 900 | [local-inicio.png](local-inicio.png) |
| Aplicación local con reporte Bash | 1440 × 900 | [local-reporte.png](local-reporte.png) |

Los paneles y tarjetas usan dos columnas en escritorio y tablet y una en
móvil. Los detalles técnicos y la evidencia se abren con controles nativos.
Las métricas provienen del reporte y los formatos descargan el fixture
completo. Bash, Python y el helper Rust se presentan como capacidades de
la aplicación local.

Playwright verifica además un viewport de 320 px, foco y navegación por
teclado, contraste de controles y métricas, aviso visible al desplazar y
descargas con los encabezados definidos en `vercel.json`.
