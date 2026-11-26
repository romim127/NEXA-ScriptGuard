# ADR 0004 · GUI React sobre el servidor local

**Estado:** Implementado para verificación de la Fase 4.

El frontend React, TypeScript y Vite se compila como HTML, JavaScript, CSS y
el SVG Infinity emitido desde el recurso aprobado. Python sirve un conjunto
explícito de rutas bajo la CSP existente. Se versiona el bundle junto con su
licencia de terceros para que una instalación desde Git o desde una rueda
pueda arrancar sin Node.js. CI recompila desde el lockfile y compara el
resultado con el bundle versionado.

`/` usa el bundle cuando está disponible. `/legacy` conserva la interfaz
anterior como referencia para la paridad y como alternativa local. Ambas
usan la misma sesión de loopback y los mismos motores y reportes. El paquete
`@nextgenai/ui` define componentes y tokens independientes de los motores.
`InfinityShield` recibe el recurso original desde el consumidor.

El cliente TypeScript valida los campos de reporte que presenta y el ID de
resultado. Los errores HTTP se muestran con mensajes locales y las
evidencias se renderizan como texto. El fragmento de sesión se retira de la
URL y se usa solo para peticiones al mismo origen de loopback. La autoridad del
contrato de reporte, del límite de recursos y del análisis sigue en Python.

Se consideró un servidor de desarrollo obligatorio y un API remoto. El
primero añadiría Node al procedimiento de arranque y el segundo ampliaría
la frontera de confianza. Se eligió servir los recursos compilados con el
servidor existente. El despliegue remoto conserva los criterios de
[ADR 0003](ADR-0003-VERCEL-EVALUATION.md).
