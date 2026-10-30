# Informes de `gastos-y-cargos` (6): revisión independiente e integración con `main`

| Informe | Fase | Intento | Rol | Autor / ejecutor declarado | Familia | Revisión revisada |
|---|---|---|---|---|---|---|
| `apply-1-constructor.md` | apply | 1 | constructor de integración | role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador | Claude | `2f81682` + `origin/main` `60b3dd5` → entrega `838a0b3` (código y specs) más un commit sólo de documentación |

| `verify-1-breaker.md` | verify | 1 | rompedor | Codex como rompedor, subagente nativo Codex; sustitución registrada del plugin codex no disponible, CLI no pudo iniciar por filesystem de sólo lectura | OpenAI/GPT; modelo no verificado | `40af1a1` (código `838a0b3`) |
| `apply-2-constructor.md` | apply | 2 | constructor (correcciones F1-F4, S1, S2 del rompedor) | role-constructor, subagente nativo de Claude (Claude Code), despachado por el orquestador | Claude | `6ec260e` + reproducciones sin commitear del rompedor → entrega `58f2d76` (código) más un commit sólo de documentación |

Faltan, todavía no producidos: `verify-2-breaker.md` (rompedor sobre las correcciones) y el informe del auditor. El rompedor del intento 1 no quedó limpio; sus hallazgos se corrigieron en `apply-2-constructor.md`.

No hay informes originales del apply de Emiliano en esta carpeta: su evidencia TDD está en `tasks.md`, tareas 1.1 a 9.5.
