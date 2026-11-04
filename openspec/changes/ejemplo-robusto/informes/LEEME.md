# Informes del change ejemplo-robusto (C-27, 3f)

Índice armado por el orquestador el 30/10/2026. Los informes originales mandan; este índice no los reemplaza.

| Informe | Rol | Autor / ejecutor | Familia | Revisión |
|---|---|---|---|---|
| `propose-1-plan-reviewer.md` | plan y revisión juntos (LOW) | orquestador, Claude Opus 5.5, sesión de Giuliano | Claude | `9649471` con el plan sin commit |
| `apply-1-constructor.md` | constructor, intento 1 | subagente nativo `role-constructor`, Claude Opus 5.5 | Claude | `9649471` más el árbol sin commit, hash del diff `1946d4ce` |
| `propose-2-plan-reviewer.md` | corrección y revisión del plan juntas (LOW) | orquestador, Claude Opus 5.5, sesión de Giuliano | Claude | `9649471` más el mismo árbol, con el plan corregido |
| `apply-2-constructor.md` | constructor, intento 2 | subagente nativo `role-constructor`, Claude Opus 5.5 | Claude | `9649471` más el árbol sin commit, hash del diff `22bb0402` |
| `verify-1-breaker.md` | rompedor, intento 1 | subagente nativo `role-breaker`, Claude Opus 5.5 | Claude | hash del diff `22bb0402` |
| `propose-3-plan-reviewer.md` | disposición del rompedor, corrección y revisión del plan juntas (LOW) | orquestador, Claude Opus 5.5, sesión de Giuliano | Claude | hash del diff `22bb0402`, con el plan corregido |
| `apply-3-constructor.md` | constructor, intento 3 (segundo agente) | subagente nativo `role-constructor`, Claude Opus 5.5 | Claude | hash del diff `6dd4630f` |
| `verify-1-auditor.md` | auditor, verify 1: **BLOQUEANTES** (B1, B2) | subagente nativo `role-auditor`, Claude Opus 5.5 | Claude | hash del diff `6dd4630f` |

## Faltan

- Rompedor, intento 2: no corre, por decisión de Giuliano (03/11/2026). Hueco declarado para el auditor.

- Suite completa local: no se corre, por decisión de Giuliano. El juez es el CI del PR (8.1), que todavía no existe.
- Auditor: corrió el 03/11/2026 y dio BLOQUEANTES. Los dos huecos de arriba son sus B1 y B2; falta la decisión de Giuliano.

## Qué recibió cada rol

- Orquestador: la guía del equipo, la ficha 3f, `15_lecciones.md`, los specs y el código. El informe lista las fuentes.
- Constructor, intento 1 (subagente nativo `role-constructor`, familia Claude, sin sustitución): brief acotado con objetivo, artefactos del change, decisiones, consumidores fuera del área, límites y salida esperada. Sin acceso a `.git/informes-*` (máquina de Juani) ni a `infra/.env`.
- Constructor, intento 1, cierre: un mensaje del orquestador pidió cortar la corrida final y completar el informe sin ejecutar nada nuevo. Quedó detenido antes de devolver su resultado final: el informe está escrito, pero no hay mensaje de entrega.
- Constructor, intento 2 (subagente nativo `role-constructor`, familia Claude, sin sustitución): un agente nuevo, sin el contexto del intento 1, porque ése no se pudo retomar después del corte. Recibió las decisiones sobre H-1 y H-2, el plan corregido, el informe del intento 1, los archivos autorizados, los límites y el orden de cierre. Sin acceso a `.git/informes-*` ni a `infra/.env`.
- Rompedor, verify 1 (subagente nativo `role-breaker`, familia Claude, sin sustitución): revisión y hashes, el plan, los consumidores fuera del área, los chequeos vigentes con su hora y el límite de memoria. Se le pide atacar antes de leer los informes del constructor. Comparte familia con el constructor, así que su independencia es de contexto, no de proveedor. Sin acceso a `.git/informes-*` ni a `infra/.env`.
- Constructor, intento 3 (subagente nativo `role-constructor`, familia Claude, sin sustitución): el mismo agente del intento 2, retomado con su contexto. Recibió las tareas del grupo 9, el plan corregido, el informe del rompedor, los límites y el orden de cierre, sin la suite completa. Sin acceso a `.git/informes-*` ni a `infra/.env`.
- Constructor, intento 3, segundo agente (subagente nativo `role-constructor`, familia Claude, sin sustitución): agente nuevo, despachado el 03/11/2026 a pedido de Giuliano, porque el primero del intento 3 fue detenido y no se pudo retomar. Recibió el grupo 9, el plan corregido, los informes del rompedor y de la revisión 3, el estado del árbol (`bb902f98...`), la decisión de Giuliano sobre tests mínimos y sin segunda vuelta de rompedor, y los límites. Sin acceso a `.git/informes-*` ni a `infra/.env`.
- Auditor, verify 1 (subagente nativo `role-auditor`, familia Claude, sin sustitución): despachado el 03/11/2026 sobre `6dd4630f...`, con todos los informes originales, el plan, la decisión de Giuliano de no repetir el rompedor ni correr la suite, y los huecos declarados. Sin acceso a `.git/informes-*` ni a `infra/.env`.
