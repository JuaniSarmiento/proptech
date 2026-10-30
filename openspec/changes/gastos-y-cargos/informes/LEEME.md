# Informes de `gastos-y-cargos` (6): revisión independiente e integración con `main`

| Informe | Fase | Intento | Rol | Autor / ejecutor declarado | Familia | Revisión revisada |
|---|---|---|---|---|---|---|
| `apply-1-constructor.md` | apply | 1 | constructor de integración | role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador | Claude | `2f81682` + `origin/main` `60b3dd5` → entrega `838a0b3` (código y specs) más un commit sólo de documentación |
| `verify-1-breaker.md` | verify | 1 | rompedor | Codex como rompedor, subagente nativo Codex; sustitución registrada del plugin codex no disponible, CLI no pudo iniciar por filesystem de sólo lectura | OpenAI/GPT; modelo no verificado | `40af1a1` (código `838a0b3`) |
| `apply-2-constructor.md` | apply | 2 | constructor (correcciones F1-F4, S1, S2 del rompedor) | role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador | Claude | `6ec260e` + reproducciones sin commitear del rompedor → entrega `58f2d76` (código) más un commit sólo de documentación |
| `verify-2-breaker.md` | verify | 2 | rompedor | Codex rompedor, subagente nativo Codex; sustitución explícita del plugin solicitado `codex:codex-rescue`, sin atribuirle ejecución | OpenAI/GPT; modelo no verificado | `63582e4` (código `58f2d76`) |
| `apply-3-constructor.md` | apply | 3 | constructor (F2-1 y S4 del rompedor 2) | role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador | Claude | `a6029cf` + reproducciones sin commitear del rompedor 2 → entrega `f432055` (código) más un commit sólo de documentación |

| `verify-3-breaker.md` | verify | 3 | rompedor | Codex vía plugin `codex:codex-rescue`, según dispatch explícito; sin Codex anidado | OpenAI/GPT; modelo no verificado | `8e6e13e` (código `f432055`) |
| `verify-1-auditor.md` | verify | 1 | auditor | role-auditor, subagente nativo de Claude (Claude Code), despachado por el orquestador | Claude (misma familia que los constructores) | `51a7ff3` (código `f432055`) |
| `verify-2-auditor.md` | verify | 2 | auditor | role-auditor, subagente nativo de Claude (Claude Code), mismo contexto que el intento 1 | Claude | `25011bf` (código idéntico a `51a7ff3`) |

Intento 3: ninguna falla reproducida; 68 casos unitarios verdes y un test PostgreSQL sólo recolectado. Falta ejecutar ese test y resolver la deuda anterior con auditoría.

Auditor, intento 1 (`verify-1-auditor.md`, 30/10/2026): **BLOQUEANTES** B1 (falta el revisor del plan y el RED original es por setup) y B2 (P36/P37 respondidas por Emiliano, el plan pedía a Juani o Alberto), los dos de decisión humana; suite completa propia sobre `51a7ff3`: 4736 passed, 1 xfailed. Antes: F2-1 y S4 del rompedor 2 se corrigieron en `apply-3-constructor.md`; S3 queda como deuda candidata para el auditor. El rompedor del intento 1 no quedó limpio; sus hallazgos se corrigieron en `apply-2-constructor.md`.

No hay informes originales del apply de Emiliano en esta carpeta: su evidencia TDD está en `tasks.md`, tareas 1.1 a 9.5.

Auditor, intento 2 (`verify-2-auditor.md`, 30/10/2026): **APROBADO**. Juani aceptó B1 como deuda (D13) y ratificó B2 (D-141) por escrito en `tasks.md` (`25011bf`); el código no cambió desde `51a7ff3`, así que se reusa la suite del intento 1 (4736 passed, 1 xfailed).
