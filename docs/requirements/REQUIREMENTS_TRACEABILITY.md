# Trazabilidad de requisitos

| Requisito | Módulos o reglas | Evidencia y criterio |
|---|---|---|
| Analizar Bash y Python como datos | `analysis`, `parser`, `rules`, `python_analysis` y PY-001 a PY-008 | `test_parser.py`, `test_python_analysis.py`, `test_analysis_core.py`. Reglas y estado de análisis verificables. |
| Ingestión segura y límites | `ingestion`, `limits`, `gui` | `test_ingestion.py`, `test_gui.py`. Rechazo acotado y visibilidad de análisis incompleto. |
| Modelo, compatibilidad y privacidad | `model`, `classification`, `redaction`, `reports` | `test_report_schemas.py`, `test_redaction.py`. Formatos válidos, evidencia sensible redactada y HTML escapado. |
| Exportar desde GUI y CLI | `reports`, `cli`, `frontend/src/services/api.ts` | `test_cli.py`, `test_gui.py` y descargas físicas en Playwright. Los destinos CLI se publican sin reemplazo. |
| Helper opcional | `rust_bridge`, `src/main.rs` | `test_rust_bridge.py`, `cargo test` y matriz Rust. |
| Reproducibilidad y compatibilidad | `pyproject.toml`, `Cargo.lock`, `.github/workflows` | Suites de [CI y pruebas](../development/TESTING.md) asociadas al SHA evaluado. |
| Arranque local estable | Lanzadores, `RUN`, `gui.main` | `test_launch.py`. Inicio desde otro directorio, navegador, loopback, puertos independientes y cierre. |
| Interfaz tipada, reutilizable y offline | `frontend`, `packages/nextgenai-ui`, bundle Python | Typecheck, ESLint, Vitest, auditoría npm y Playwright con instalación pipx. Se prueba navegación, scroll, estados, evidencia no confiable, análisis y exportación. |

Ver [criterios de aceptación](ACCEPTANCE_CRITERIA.md), [requisitos funcionales](FUNCTIONAL_REQUIREMENTS.md) y [no funcionales](NONFUNCTIONAL_REQUIREMENTS.md).

Fase 5 verifica equivalencia de campos, límites, teclado y descargas en [la matriz de paridad](../development/PHASE_5_PARITY.md). Las anclas `helpUri` del catálogo se cubren en `test_report_schemas.py`. El consumidor independiente se valida con Playwright.
