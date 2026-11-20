# Procedimiento seguro: instalador oficial de Ollama

**No se descargó ni ejecutó ningún instalador de Ollama durante esta implementación.** NEXA ScriptGuard analiza scripts Bash; no inspecciona el contenido de un instalador Windows `.exe` ni valida firmas de binarios.

## Cuando exista un archivo autorizado

1. Obtener la versión y artefacto desde la página/canal oficial de Ollama mediante el proceso aprobado por la organización. Registrar URL, fecha, versión y persona/proceso que autorizó su adquisición. No usar mirrors no aprobados.
2. Si el proveedor publica hash o firma para esa versión/plataforma, verificarlo con la clave/procedimiento oficial y conservar el resultado. Si no publica evidencia verificable, dejar constancia: un SHA-256 local identifica el archivo, pero no prueba autenticidad.
3. Conservar el original en un directorio restringido, registrar tamaño y SHA-256 y trabajar sobre una copia de solo lectura. No abrir, montar ni lanzar el instalador durante una revisión estática.
4. Para un artefacto `.sh`, analizarlo como texto con NEXA en una máquina de revisión; registrar versión de NEXA, hash del script, estado completo/incompleto, reglas, contexto y limitaciones. Compartir solo reportes redactados y aprobados.
5. Para un `.exe`/`.msi`, utilizar herramientas de análisis estático de formatos Windows y verificación de Authenticode en un entorno aprobado. NEXA no cubre ese formato; no inferir ausencia de riesgo a partir de este escáner.
6. Revisar manualmente las instrucciones detectadas. Los procedimientos de verificación del reporte no son para ejecutar automáticamente sobre el instalador.
7. Si la revisión requiere instalación dinámica, detener este flujo y obtener autorización explícita, usar un entorno aislado/destruible con controles aprobados y plan de observación. Esa actividad queda fuera de esta herramienta.

## Resultado y evidencia

El entregable debe separar: procedencia declarada, verificación de firma/hash, observaciones estáticas, limitaciones, decisiones humanas y actividades no realizadas. No describir el instalador como “seguro” por un escaneo limpio.
