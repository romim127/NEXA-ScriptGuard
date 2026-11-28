# ADR 0006 — Impacto estático y límites de confianza

SITA enriquece hallazgos clasificados de Bash y Python dentro del plazo del análisis. Las heurísticas de compatibilidad y Rust conservan su procedencia y quedan sin cobertura inicial. La extensión opcional impact_analysis conserva schema_version 1.0 y usa version 1.0 propia. Los consumidores viejos pueden ignorar la extensión. Los consumidores nuevos indican ausencia de evaluación en reportes viejos.

El motor aporta taxonomías, conclusiones CIA, condiciones, referencias y correlaciones normalizadas. La preparación del reporte elimina rangos si la evidencia visible cambia. Los rangos locales usan puntos de código Unicode desde cero y fin exclusivo. Las ubicaciones del script usan línea y columna desde uno y fin exclusivo. La interfaz reutiliza CodeBlock y presenta referencias navegables. CLI, HTML y SARIF transportan las mismas conclusiones. SARIF usa propiedades de extensión.

La cobertura distingue evaluación sintáctica, correlación y ausencia de evaluación. CIA expresa potencial, condicional, indeterminado, no establecido y no evaluado. No establecido significa que la señal no sustenta esa dimensión. Indeterminado significa que hay una relación pertinente cuyo efecto no se puede precisar. La completitud base y la severidad permanecen independientes.

Presupuesto inicial para medir: 2000 hallazgos, hasta 4 relaciones y 10 referencias por hallazgo, con comprobación del plazo compartido por hallazgo. Se acota el tamaño mediante estructuras cerradas y referencias a evidencia existente. Al agotar el plazo la cobertura restante queda explícitamente sin evaluar. Las cifras definitivas se documentarán con mediciones.
