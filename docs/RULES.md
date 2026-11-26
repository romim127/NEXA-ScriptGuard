# Catálogo de reglas NEXA ScriptGuard

Las reglas describen señales que requieren revisión; no determinan intención maliciosa ni ejecución. Los catálogos se encuentran en `nexa_scriptguard/bash.json` y `nexa_scriptguard/python_rules.json`; sus IDs se consideran estables. Las reglas Bash usan nodos de comando excepto SG-001, que usa pipelines. Rust comparte únicamente SG-001 y SG-002 con su detector lineal y limitado.

| ID | Severidad | Señal | Límites principales |
|---|---|---|---|
| <a name="sg-001"></a>SG-001 | High | Downloader y shell en el mismo pipeline | No prueba entrega/ejecución; Rust solo en una línea. |
| <a name="sg-002"></a>SG-002 | High | Opción de carga junto a ruta sensible | Heurística de opciones/ruta; no resuelve el archivo ni prueba transferencia. |
| <a name="sg-003"></a>SG-003 | High | `chmod 777`/modo mundialmente escribible | Cobertura parcial de modos y opciones. |
| <a name="sg-004"></a>SG-004 | High | `rm` con opción corta recursiva/forzada | Requiere resolver variables, glob y directorio de trabajo. |
| <a name="sg-005"></a>SG-005 | High | `eval` | Puede ser legítimo; no clasifica la confiabilidad del argumento. |
| <a name="sg-006"></a>SG-006 | High | `bash`/`sh`/`zsh -c` con expansión | No prueba que la expansión sea no confiable. |
| <a name="sg-007"></a>SG-007 | High | Desactivación o detención de controles específicos | Lista acotada; administración autorizada puede ser legítima. |
| <a name="sg-008"></a>SG-008 | Medium | Edición de cron o habilitación de servicio | Persistencia potencial; no implica autorización ausente. |
| <a name="sg-009"></a>SG-009 | Medium | Edición/copia de configuración sensible | No calcula diff ni estado final. |
| <a name="sg-010"></a>SG-010 | High | Asignación de setuid | No resuelve propietario o necesidad. |
| <a name="sg-011"></a>SG-011 | Medium | Asignación con valor parecido a credencial | Puede ser placeholder; redacción best-effort. |
| <a name="sg-012"></a>SG-012 | High | Escritura a dispositivo/archivo crítico acotado | No cubre todos los alias ni efectos indirectos. |
| <a name="sg-flow-001"></a>SG-FLOW-001 | High | Variable con texto de red conectada a intérprete | Flujo posible/indeterminado; control de flujo y split quedan incompletos. |
| <a name="sg-flow-002"></a>SG-FLOW-002 | Medium | Variable con ruta sensible en opción de carga | No resuelve filesystem, ámbito ni transferencia real. |

Cada entrada del catálogo incluye explicación, recomendación y checks manuales. Las recomendaciones no se ejecutan. Los checks son puntos de revisión, no comandos garantizados ni universalmente seguros.

## Reglas Python

| ID | Severidad | Señal | Límites principales |
|---|---|---|---|
| <a name="py-001"></a>PY-001 | High | `eval` o `exec` | No demuestra ejecución ni entrada no confiable; nombres ambiguos se omiten. |
| <a name="py-002"></a>PY-002 | High | `subprocess` con `shell=True` | Funciones y argumentos reconocidos de forma limitada. |
| <a name="py-003"></a>PY-003 | High | `pickle.load`/`loads` | La procedencia de los datos no está demostrada. |
| <a name="py-004"></a>PY-004 | High | Respuesta de red vinculada a `eval`/`exec` | Expresión directa o asignación simple; no prueba ejecución ni transferencia. |
| <a name="py-005"></a>PY-005 | Medium | Nombre de credencial asignado a literal | Puede ser ejemplo; redacción heurística, no exhaustiva. |
| <a name="py-006"></a>PY-006 | High | `os.system`, `os.popen` o `subprocess.getoutput`/`getstatusoutput` | No resuelve argumentos ni todas las funciones equivalentes. |
| <a name="py-007"></a>PY-007 | High | `execute`/`executemany` con SQL interpolado | No identifica el tipo del receptor ni demuestra inyección. |
| <a name="py-008"></a>PY-008 | High | Verificación TLS `verify=False` en llamadas HTTP reconocidas | No cubre sesiones, clientes ni todas las bibliotecas. |

Los alias resueltos se invalidan cuando existen asignaciones conflictivas en el mismo ámbito. No se simulan imports, funciones ni comportamiento de ejecución. Las reglas pueden omitir casos o generar falsos positivos.

## Severidad y confianza

La severidad prioriza impacto potencial si la señal corresponde al comportamiento previsto. La confianza refleja certeza limitada del patrón, no probabilidad de malicia. Una regla que requiere inspección no debe tratarse como bloqueo automático o veredicto. Los flujos incluyen relaciones `possible` o `indeterminate`; no hay relaciones interprocedurales demostradas.

## Pruebas

`tests/corpus/bash_cases.json` contiene casos sintéticos positivos, negativos y ambiguos. `tests/test_parser.py` cubre esa tabla, quoting, comentarios, heredocs, pipes y asignaciones; revisar la suite antes de cambiar severidad o semántica.
