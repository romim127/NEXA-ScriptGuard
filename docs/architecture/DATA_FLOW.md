# Flujo y límites de confianza

1. La CLI abre y valida el archivo. La GUI recibe bytes acotados con token de sesión y validación del origen local.
2. La ingestión calcula el hash del snapshot. El despachador determina el lenguaje por extensión y rechaza los demás tipos.
3. Tree-sitter Bash o el AST estándar de Python analiza contenido no confiable como datos. El helper Rust de confianza puede recibir el mismo snapshot Bash por stdin.
4. Las reglas producen ubicaciones y evidencias. El análisis contextual añade correlaciones conservadoras y la clasificación ordena y aplica presupuestos. Se comunica cualquier estado incompleto.
5. La redacción prepara la versión compartible. La opción explícita de evidencia original pertenece a la CLI. Todo renderer aplica su escape correspondiente.
6. La GUI vincula exportaciones al informe vigente y el navegador administra el destino. La CLI publica de forma exclusiva en las rutas solicitadas.

El archivo, su nombre, los fragmentos y los diagnósticos cruzan la frontera como datos no confiables. El token y el informe activo se mantienen en memoria local. Cualquier servicio web introduciría una frontera de red y requeriría consentimiento explícito y los controles del [modelo de seguridad](SECURITY_MODEL.md).

La GUI React retira el fragmento de sesión de la barra de direcciones y
conserva el token en `sessionStorage` de la pestaña para recargas. Tras
recibir el reporte valida el esquema consumido antes de renderizarlo como
texto. Para exportar solicita los bytes al servidor y entrega un enlace Blob
temporal al navegador.

Las vistas de criticidad, regla, búsqueda y orden son proyecciones del reporte validado. Las exportaciones siguen leyendo el resultado vigente completo. La demo empaqueta fixtures y produce blobs locales sin recibir archivos de entrada.
