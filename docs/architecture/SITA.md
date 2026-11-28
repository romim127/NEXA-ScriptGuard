# SITA · System Impact & Trust Analysis

SITA consume hallazgos clasificados de Bash y Python. El enriquecimiento en
`nexa_scriptguard/impact.py` utiliza la regla, procedencia, ubicación y relaciones
existentes. No abre archivos adicionales ni efectúa verificaciones dinámicas.
Compatibilidad Bash y Rust devuelven cobertura no evaluada. El helper Rust
mantiene su protocolo y sigue aportando señales suplementarias.

## Contrato

El objeto opcional `impact_analysis` por hallazgo tiene versión propia 1.0.
Contiene cobertura, confianza, procedencia, recursos, límites, CIA, flujos,
referencias y limitaciones. Cada conclusión enlaza referencias mediante IDs
locales al hallazgo. `direct` indica que el recurso surge del patrón de la
instrucción. `correlated` indica que surge del enlace entre señales.

| Estado | Interpretación |
| --- | --- |
| `potential` | La evidencia identifica una posibilidad presente en el código. |
| `conditional` | El efecto exige condiciones explícitas en tiempo de ejecución. |
| `indeterminate` | Hay una señal pertinente con semántica insuficiente para precisar el efecto. |
| `not_established` | La señal evaluada carece de respaldo para la dimensión. |
| `not_evaluated` | La regla o procedencia carece de evaluación disponible. |

La correlación normaliza `destination` de Bash y `sink` de Python. El
contrato SITA conserva roles, coordenadas, incertidumbre y cantidad de pasos
de asignación. La evidencia base conserva la cadena y relación originales
sujetas a su política de redacción. No se infieren validaciones ni
transformaciones de una cadena de nombres.

Las coordenadas de código usan línea y columna desde 1, en puntos de código
Unicode y con fin exclusivo. Los offsets visuales usan puntos de código desde
0 y fin exclusivo sobre `evidence.shared`. Los tokens obtenidos de AST y
subfragmentos de una línea pueden resaltarse si caben en el fragmento.
El rango queda ausente si la evidencia está truncada, cambió al prepararla,
está fuera del fragmento o requiere una correspondencia multilínea.
Un rango se activa por vez, de modo que referencias superpuestas siguen
siendo seleccionables por separado. React segmenta por puntos de código.
La pestaña `/legacy` mantiene su presentación de referencia y exporta los
reportes enriquecidos a través del mismo backend.

## Taxonomía de recursos

| ID | Recurso | Aplicabilidad inicial |
| --- | --- | --- |
| SYS-01 | Sistema de archivos | Bash, rutas y borrado |
| SYS-02 | Procesos y subprocesos | Python, API de ejecución |
| SYS-03 | Registro de Windows | Windows, reservado |
| SYS-04 | Servicios del sistema | Dependiente de plataforma, reservado |
| SYS-05 | Variables de entorno | Multiplataforma, reservado |
| SYS-06 | Credenciales y secretos | Bash y Python, literales |
| SYS-07 | Comunicaciones de red | Bash y Python, transferencia u origen correlacionado |
| SYS-08 | Usuarios, permisos y privilegios | Bash, comandos POSIX de modo |
| SYS-09 | Configuración del SO | Bash, convenciones de rutas Unix |
| SYS-10 | Persistencia | Bash, cron y systemd donde estén disponibles |
| SYS-11 | Controles de seguridad | Bash para controles Linux, Python para TLS |
| SYS-12 | Bases de datos | Python, señal indeterminada del método |
| SYS-13 | Memoria y ejecución dinámica | Bash y Python, ejecución |
| SYS-14 | Registros y evidencias de auditoría | Multiplataforma, reservado |
| SYS-15 | Dependencias y cadena de suministro | Multiplataforma, reservado |

## Límites de confianza

| ID | Dirección | Evidencia mínima |
| --- | --- | --- |
| TB-01 | Entrada externa → aplicación | Origen externo y entrada identificables. Reservado. |
| TB-02 | Datos → intérprete de código | Instrucción intérprete y entrada de datos identificada por el patrón o la correlación. |
| TB-03 | Aplicación → sistema operativo | API reconocida de invocación de comandos del SO. |
| TB-04 | Usuario → contexto privilegiado | Contextos de origen y destino y operación que los conecta. Reservado. |
| TB-05 | Entorno local → red externa | Origen local, operación de envío y destino externo respaldados. Reservado. |
| TB-06 | Aplicación → almacenamiento sensible | Operación sobre un destino de almacenamiento sensible identificado. Reservado. |
| TB-07 | Proceso → otro proceso | Procesos identificables y canal entre ambos. Reservado. |
| TB-08 | Aplicación → servicio externo | Servicio externo y operación que alcanza ese dominio. Reservado. |
| TB-09 | Dependencia externa → entorno local | Procedencia externa y mecanismo de incorporación verificables. Reservado. |
| TB-10 | Aplicación → controles de seguridad | Control identificado y operación que solicita degradarlo. |

## Matriz de reglas

Las asociaciones de cada fila requieren la evidencia del patrón que generó el
hallazgo. Condiciones y justificaciones completas se serializan desde
`SIGNALS` y se muestran en el panel y exportaciones.

| Regla | Cobertura | Recurso, operación y límite | Condición o incertidumbre |
| --- | --- | --- | --- |
| SG-001 | Correlación indeterminada | SYS-13 ejecución | Red e intérprete en la misma tubería. Orden y entrega por verificar. |
| SG-002 | Sintáctica | SYS-07 transferencia | Herramienta, opción de carga y referencia sensible. Destino efectivo desconocido. |
| SG-003 | Sintáctica | SYS-08 modificación | chmod con modo amplio. Requiere objetivo y permisos. |
| SG-004 | Sintáctica | SYS-01 eliminación | rm con opción reconocida. Ruta, acceso y resultado desconocidos. |
| SG-005 | Sintáctica | SYS-13 ejecución, TB-02 | eval requiere texto interpretable. |
| SG-006 | Sintáctica | SYS-13 ejecución, TB-02 | Shell con opción y expansión. Valor resultante desconocido. |
| SG-007 | Sintáctica | SYS-11 desactivación, TB-10 | Control reconocido, existente y modificable. |
| SG-008 | Sintáctica | SYS-10 modificación | crontab o activación de servicio. Persistencia efectiva desconocida. |
| SG-009 | Indeterminada | SYS-09 acceso | Mención de ruta sensible. Operando y dirección por verificar. |
| SG-010 | Sintáctica | SYS-08 modificación | chmod con modo set-ID. No acredita un cambio de contexto. |
| SG-011 | Sintáctica | SYS-06 presencia potencial | Literal candidato. Validez y exposición desconocidas. |
| SG-012 | Indeterminada | SYS-01 acceso | Herramienta y ruta de alto impacto. Papel de la ruta por verificar. |
| SG-FLOW-001 | Correlacionada | SYS-13 ejecución, TB-02 | Asignación y comando intérprete. Depende de expansión, comillas y ramas. |
| SG-FLOW-002 | Correlacionada | SYS-07 transferencia | Asignación de ruta y opción de carga. Destino y acceso desconocidos. |
| PY-001 | Sintáctica | SYS-13 ejecución, TB-02 | eval o exec. Origen desconocido. |
| PY-002 | Sintáctica | SYS-02 ejecución, TB-03 | API de subprocesos con shell habilitado. |
| PY-003 | Sintáctica | SYS-13 ejecución | Requiere que pickle procese contenido pertinente. |
| PY-004 | Correlacionada | SYS-13 ejecución, SYS-07 acceso, TB-02 | AST enlaza un origen de red posible con evaluación. |
| PY-005 | Sintáctica | SYS-06 presencia potencial | Nombre sensible y literal. Sin evidencia de transferencia. |
| PY-006 | Sintáctica | SYS-02 ejecución, TB-03 | API reconocida de invocación de comandos. |
| PY-007 | Indeterminada | SYS-12 acceso | Método y forma del argumento. Tipo del receptor desconocido. |
| PY-008 | Sintáctica | SYS-11 desactivación, TB-10 | Opción TLS deshabilitada. Requiere una conexión donde se aplique. |

## Presupuestos y validación

SITA comparte el plazo monotónico del análisis. Cada hallazgo admite como
máximo cuatro flujos, diez referencias, dos recursos y un límite. La
estimación de salida del enriquecimiento se acota al menor de 1 MiB,
un octavo del presupuesto de salida y un treintaidosavo del presupuesto de
memoria. Se mide sobre JSON indentado de cada objeto por separado. Este
presupuesto es una estimación, y la serialización final mantiene sus límites
existentes. Al agotarse el presupuesto se omiten los objetos de análisis
restantes y se marca cada hallazgo con un motivo compacto en
`impact_omission`. Las limitaciones generales conservan el resumen.

Una carga artificial de 2000 hallazgos con cuatro flujos cada uno,
sin aplicar el tope, tomó 393 ms bajo tracemalloc, alcanzó 11 134 664 bytes
de memoria Python rastreada y generó 8 342 001 bytes de JSON compacto
en una ejecución local. La medición motivó el tope agregado. La latencia
depende de la máquina, parser y entrada.

La compatibilidad del esquema se comprueba con el validador anterior y el
nuevo. La interfaz moderna, la demo precomputada, el CLI y las tres
exportaciones se verifican de forma independiente. Las propiedades SARIF
conservan las conclusiones y la incertidumbre del motor.

## Trazabilidad de cobertura (SG-SITA-001)

| Contrato del hallazgo | Presentación |
| --- | --- |
| Sin `impact_analysis` ni `impact_omission` | Análisis de impacto no disponible en este reporte |
| `impact_analysis.coverage: not_evaluated` | No evaluado por el motor SITA |
| `impact_omission: resource_budget` o `deadline` | No evaluado por límite de recursos |
| `impact_analysis.coverage: partial` | Cobertura parcial, con las limitaciones del análisis conservado |

`impact_omission` es opcional, excluyente con `impact_analysis` y contiene
únicamente un valor del catálogo. SARIF conserva el motivo como
`result.properties.impactOmission`. CLI, HTML y GUI derivan las etiquetas
de estos campos. La completitud del escaneo, severidad, confianza y
conclusiones CIA conservan su significado. Los reportes previos a
esta corrección carecen de la marca explícita de omisión.

## Presentación y alcance de PY-004 (SG-SITA-UX-002)

El panel común resume recursos, límites, CIA, cobertura, confianza y
condiciones. Las justificaciones idénticas se agrupan y cada conclusión
conserva sus números de referencia. La referencia exacta puede resaltar
texto si el rango sigue siendo válido sobre la instrucción mostrada.
Una ubicación que coincide con la primera línea de esa instrucción puede
llevar el foco al bloque sin resaltar. Las demás ubicaciones se muestran
con su limitación y sin control de navegación.

PY-004 reconoce una llamada de red directa y una variable asignada desde
esa expresión. Con `response = requests.get(...)`, seguido de
`payload = response.text` y `eval(payload)`, el segundo valor se obtiene
de un nombre intermedio que la resolución de `network()` no sigue.
Con y sin importación explícita, el caso produce PY-001. Con la
importación y la asignación directa de `requests.get(...).text` a
`payload`, produce PY-001 y PY-004. El comportamiento coincide con
`462189b`. La resolución de cadenas de asignación y atributos en Python
queda como evolución separada del motor.
