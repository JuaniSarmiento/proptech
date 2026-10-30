# Knowledge base report · 6 `gastos-y-cargos` (30/10/2026)

Union of the proposal's Knowledge Base Impact and the actual diff (`5c6d84c..92a6bb2`).

| Documento | Estado | Qué |
|---|---|---|
| `02_descripcion_general.md` | REWRITTEN (Emiliano, apply) | El módulo `gastos` deja de estar vacío |
| `04_modelo_de_datos.md` | REWRITTEN (Emiliano, apply) | `proveedor`, `gasto`, `nota_de_credito`, `cargo_particular` existentes, con ERD |
| `05_reglas_de_negocio.md` | REWRITTEN (Emiliano, apply) | R12, R13, R14, R16 y R22 con código |
| `06_funcionalidades.md` | REWRITTEN (Emiliano, apply) | HU-A3 y HU-A3b cubiertas por API |
| `09_decisiones_y_supuestos.md` | APPENDED | D-140, D-141 (Emiliano, renumeradas al integrar) y D-142 (cierre, 30/10/2026) |
| `10_preguntas_abiertas.md` | REWRITTEN | P36 y P37 resueltas (D-141), ratificadas por Juani (D-142) |
| `11_glosario.md` | REWRITTEN (Emiliano, apply) | proveedor, nota de crédito, cargo particular |
| `12_fichas_de_changes.md` | REWRITTEN | Ficha 6 archivada con la deuda de la revisión (D1 a D13); "Recibe del 6" en las fichas 5, 11, 2e (C-23), 3e (C-26) y R1 (C-28) |
| `15_lecciones.md` | APPENDED | L-063, L-064 (Emiliano) y L-065 a L-067 (revisión) |
| `CHANGES.md` | REWRITTEN | C-09 `[x]` |
| `CLAUDE.md` / `AGENTS.md` | REWRITTEN | Estado: 6 archivado, sin PRs en revisión |

**Sin cambios**: `01`, `03`, `07`, `08`, `13`, `14`, `16`. La corrección F1 usa el permiso existente
`ver_configuracion_del_edificio` sin tocar la matriz de `03`.

**PENDING**: D12 (nombre y lugar en el roadmap del change de pantallas de gastos, D-140), a cargo de
Juani. No hay pendientes heredados: el 3d no dejó `knowledge-base-report.md`.
