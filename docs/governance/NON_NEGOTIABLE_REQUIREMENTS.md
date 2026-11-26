# Requisitos no negociables

- Tratar los scripts como datos. Nunca ejecutarlos, importar el Python analizado ni ejecutar recomendaciones automáticamente.
- Proteger secretos y credenciales. Comunicar análisis incompletos y aclarar el alcance de la ausencia de hallazgos.
- Preservar módulos previos, identidad y diseños aprobados. Los cambios de identidad requieren autorización.
- Entregar por GitHub sin ZIP y publicar implementaciones terminadas mediante el proceso de integración.
- Registrar resultados reales de pruebas. Conservar los controles de seguridad en cualquier despliegue.
- Mantener un arranque local estable, sin privilegios administrativos,
  con loopback, puerto dinámico y token. El PATH de usuario solo cambia
  mediante acción explícita. [NGI-STD-002](NGI-STD-002_LOCAL_APPLICATION_LAUNCH_STANDARD.md)
- Mantener la distribución local operativa sin Node.js ni servicios de red
  después de instalarla. Tratar evidencias como texto y conservar la CSP.

La demostración muestra su condición sintética de forma persistente y no acepta archivos. Los experimentos web requieren paridad y verificación antes de habilitar análisis real.
