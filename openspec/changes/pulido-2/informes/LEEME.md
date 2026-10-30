# Informes del change pulido-2 (3d)

Índice armado por el orquestador el 30/10/2026. Los informes originales mandan; este índice no los reemplaza.

| Informe | Rol | Autor / ejecutor | Familia | Revisión |
|---|---|---|---|---|
| `verify-1-breaker.md` | rompedor, intento 1 | subagente nativo role-breaker | Claude | `b1ec660` |
| `propose-2-plan-reviewer.md` | revisor del plan corregido, vueltas 1 y 2 | subagente nativo role-plan-reviewer | Claude | plan sin commit sobre `b1ec660` |
| `apply-1-constructor.md` | constructor, intentos 1 y 2 (4.3, 11.1 a 11.6) | subagente nativo role-constructor | Claude | `a4b4e53`, `d15c610` |
| `verify-2-breaker.md` | rompedor, intento 2 (F7) | subagente nativo role-breaker | Claude | `a4b4e53` |
| `verify-3-breaker.md` | rompedor, intento 3 (ninguna falla) | subagente nativo role-breaker | Claude | `d15c610` |
| `verify-1-auditor.md` | auditor, intento 1 (BLOQUEANTES) | subagente nativo role-auditor | Claude | `decf692` |

La corrección del plan (F4, PR2-1 a PR2-3) la hizo un subagente nativo role-planner sin informe propio: su trabajo está en el diff de `spec.md`, `proposal.md` y `tasks.md` del commit `a4b4e53`.

## Faltan (BJ-1 del auditor)

- El informe del planner del plan original (commit `302fef4`).
- El informe del revisor del plan original.
- El informe del constructor original, con el rojo y el verde de las tareas 1 a 10. El rojo no se puede reconstruir, porque los commits llevan el test y el código juntos.
- El informe de la 10.2 ("rompe y audita" en un solo agente, sin independencia).

Lo que los reemplaza como evidencia: los mutantes del rompedor (13 muertos en el intento 1; el que sobrevivía, muerto en el intento 2) y el vitest completo sobre `decf692`. La decisión sobre estos faltantes la toma Juani (BJ-1).
