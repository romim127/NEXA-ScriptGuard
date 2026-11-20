# Catálogo de reglas NEXA ScriptGuard

Las reglas describen señales que requieren revisión; no determinan intención maliciosa ni ejecución. Los catálogos se encuentran en `nexa_scriptguard/bash.json` y `nexa_scriptguard/python_rules.json`; sus IDs se consideran estables. Las reglas Bash usan nodos de comando excepto SG-001, que usa pipelines. Rust comparte únicamente SG-001 y SG-002 con su detector lineal y limitado.

| ID | Severidad | Señal | Límites principales |
|---|---|---|---|
| SG-001 | High | Downloader y shell en el mismo pipeline | No prueba entrega/ejecución; Rust solo en una línea. |
| SG-002 | High | Opción de carga junto a ruta sensible | Heurística de opciones/ruta; no resuelve el archivo ni prueba transferencia. |
| SG-003 | High | `chmod 777`/modo mundialmente escribible | Cobertura parcial de modos y opciones. |
| SG-004 | High | `rm` con opción corta recursiva/forzada | Requiere resolver variables, glob y directorio de trabajo. |
| SG-005 | High | `eval` | Puede ser legítimo; no clasifica la confiabilidad del argumento. |
| SG-006 | High | `bash`/`sh`/`zsh -c` con expansión | No prueba que la expansión sea no confiable. |
| SG-007 | High | Desactivación o detención de controles específicos | Lista acotada; administración autorizada puede ser legítima. |
| SG-008 | Medium | Edición de cron o habilitación de servicio | Persistencia potencial; no implica autorización ausente. |
| SG-009 | Medium | Edición/copia de configuración sensible | No calcula diff ni estado final. |
| SG-010 | High | Asignación de setuid | No resuelve propietario o necesidad. |
| SG-011 | Medium | Asignación con valor parecido a credencial | Puede ser placeholder; redacción best-effort. |
| SG-012 | High | Escritura a dispositivo/archivo crítico acotado | No cubre todos los alias ni efectos indirectos. |
| SG-FLOW-001 | High | Variable con texto de red conectada a intérprete | Flujo posible/indeterminado; control de flujo y split quedan incompletos. |
| SG-FLOW-002 | Medium | Variable con ruta sensible en opción de carga | No resuelve filesystem, ámbito ni transferencia real. |

Cada entrada del catálogo incluye explicación, recomendación y checks manuales. Las recomendaciones no se ejecutan. Los checks son puntos de revisión, no comandos garantizados ni universalmente seguros.

## Reglas Python

| ID | Severidad | Señal | Límites principales |
|---|---|---|---|
| PY-001 | High | `eval` o `exec` | No demuestra ejecución ni entrada no confiable; nombres ambiguos se omiten. |
| PY-002 | High | `subprocess` con `shell=True` | Funciones y argumentos reconocidos de forma limitada. |
| PY-003 | High | `pickle.load`/`loads` | La procedencia de los datos no está demostrada. |
| PY-004 | High | Respuesta de red vinculada a `eval`/`exec` | Expresión directa o asignación simple; no prueba ejecución ni transferencia. |
| PY-005 | Medium | Nombre de credencial asignado a literal | Puede ser ejemplo; redacción heurística, no exhaustiva. |
| PY-006 | High | `os.system`, `os.popen` o `subprocess.getoutput`/`getstatusoutput` | No resuelve argumentos ni todas las funciones equivalentes. |
| PY-007 | High | `execute`/`executemany` con SQL interpolado | No identifica el tipo del receptor ni demuestra inyección. |
| PY-008 | High | Verificación TLS `verify=False` en llamadas HTTP reconocidas | No cubre sesiones, clientes ni todas las bibliotecas. |

Los alias resueltos se invalidan cuando existen asignaciones conflictivas en el mismo ámbito. No se simulan imports, funciones ni comportamiento de ejecución. Las reglas pueden omitir casos o generar falsos positivos.

## Severidad y confianza

La severidad prioriza impacto potencial si la señal corresponde al comportamiento previsto. La confianza refleja certeza limitada del patrón, no probabilidad de malicia. Una regla que requiere inspección no debe tratarse como bloqueo automático o veredicto. Los flujos incluyen relaciones `possible` o `indeterminate`; no hay relaciones interprocedurales demostradas.

## Pruebas

`tests/corpus/bash_cases.json` contiene casos sintéticos positivos, negativos y ambiguos. `tests/test_parser.py` cubre esa tabla, quoting, comentarios, heredocs, pipes y asignaciones; revisar la suite antes de cambiar severidad o semántica.
