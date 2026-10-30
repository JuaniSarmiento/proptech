# verify · intento 3 · ROMPEDOR · gastos-y-cargos (MEDIUM)

Autor: **Codex rompedor**. Ejecutor declarado por el dispatch: **Codex vía plugin `codex:codex-rescue`**, familia OpenAI/GPT; modelo concreto no verificado. No lancé otro Codex. Fecha: 30/10/2026. Revisión `8e6e13e285604e4bb5759cef85d86b4dcaec2c37`, código indicado `f432055`; árbol inicial limpio. Diff acotado `a6029cf..500a8fd`, sin reabrir hallazgos cerrados salvo regresión.

Recibí del usuario objetivo, diff, consumidores, tres lentes, restricciones, evidencia anterior y destinos. Este encabezado registra el dispatch y el intento; no incrementé el contador ni alteré tasks. No hubo delegación ni sustitución. Próxima acción: ejecutar integración pendiente y pasar al auditor con los originales. Este informe no es aprobación del auditor.

## EVIDENCIA

### Estado y ejecución

Todo se ejecutó exclusivamente en el worktree indicado. `openspec list --json`, `status --change gastos-y-cargos --json` e `instructions apply --change gastos-y-cargos --json` confirman artefactos done y 67/67 tareas. Ese estado no prueba aprobación del gate.

Ventana de checks finales observada: **2026-10-30T19:17:22Z a 19:17:38Z**. Revisión de producción intacta `8e6e13e`. Prefijo de comandos Python: `UV_CACHE_DIR=/tmp/uv-rompedor-6 uv run --no-sync --directory backend`.

| Comando tras el prefijo | Resultado observado |
|---|---|
| `pytest tests/unitarios/test_rompedor_gastos_intento_3.py tests/unitarios/test_gastos_aplicacion.py -q -p no:cacheprovider` | **68 passed**, 0.59 s |
| `ruff check --fix tests/unitarios/test_rompedor_gastos_intento_3.py tests/integracion/test_rompedor_gastos_intento_3.py` | Dos bloques de imports corregidos; cero errores restantes |
| `ruff format --check` sobre esos dos archivos | **2 files already formatted** |
| `mypy` sobre esos dos archivos, `--cache-dir /tmp/mypy-rompedor-6-v3` | **Success: no issues found in 2 source files** |
| `pytest tests/integracion/test_rompedor_gastos_intento_3.py --collect-only -q -p no:cacheprovider` | **1 test collected**, no se ejecutó su cuerpo |

Conteo propio sin sumar corridas repetidas: **32 casos nuevos verdes** (14 subconjuntos parciales de factura, 12 combinaciones estado/importe, 2 ediciones legítimas, 4 rechazos de null del cuerpo HTTP) y **36 existentes verdes**. Un test de integración solamente recolectado. Los verdes son ataques de regresión sobre código existente, no evidencia RED/GREEN de construcción. No hubo rojo de producto. El primer comando usó `python`, ausente; no creó archivos y pytest no encontró tests. Se corrigió a `python3`; ese error de entorno no cuenta como falla. Ruff inicial detectó imports; corregidos sólo en tests.

### Correctitud

- Quitar uno, dos o tres campos: los 14 subconjuntos propios rechazan con EntradaInvalida y no emiten UPDATE. El dominio exige cuatro o ninguno antes del nuevo guardia.
- Quitar los cuatro y cambiar importe simultáneamente: 59.99, 60.00 y 150.00 contra 60.00 acreditados, en borrador/sin_ia/en_revision/aprobado. Todos rechazan sin UPDATE; campo factura en editables y estado en aprobado. El aumento no elude el guardia.
- Sin notas: el caso existente `test_quitar_la_factura_sin_notas_se_permite` pasa. Con notas: los tres casos existentes que originaron F2-1 pasan. Las ediciones propias de concepto con y sin notas emiten un UPDATE y conservan la factura.
- No hay estado de anulación ni operación de anular nota en la migración 0032 ni en router/casos de uso examinados. No inventé una nota anulada alcanzable. El SUM incluye todas las notas actuales, cuyos importes son positivos por CHECK.
- El JOIN de lectura toma `g.periodo` actual, no una copia histórica. Entregué `test_periodo_factura_editada` marcado integracion: crea nota en noviembre, cambia factura borrador a septiembre y exige ambos períodos separados. Sólo recolectado. La spec dice período de su factura, sin exigir instantánea histórica: no presento la lectura actual como defecto.
- El guardia y el alta de notas bloquean la fila de gasto con FOR UPDATE por inspección. No ejecuté concurrencia real ni PostgreSQL con dobles.

### Cableado y consumidores

Búsqueda de `cargar_nota_de_credito`, `FROM nota_de_credito`, `listar_notas` y `periodo_de_la_factura` en backend y web. La lectura modificada llega al GET `/notas-de-credito/{nota_id}` y se devuelve sin modelo de respuesta que elimine el campo. No encontré endpoint/listador de notas ni exportación Excel de notas: el Excel del módulo importa cargos particulares; no consume esta lectura. El cálculo de aprobados usa otra consulta, intacta, y no depende del nuevo campo.

No cambia id, complejo_id ni gasto_id, que usa el router para alcance y autorización. Los tests existentes de matriz de detalle en test_gastos_aplicacion pasaron. El nuevo JOIN usa id y administracion_id; las FK compuestas existentes vinculan gasto y nota al edificio. Aislamiento real no ejecutado.

Los cuatro tests propios del cuerpo CuerpoEdicionGasto confirman que null se rechaza antes del caso de uso. Esto es validación del cuerpo, no transporte HTTP ejecutado. El guardia sigue siendo pertinente para consumidores internos/futuros del caso de uso.

### Contratos y comentarios

La spec notas exige asociación a gasto con factura y ambos períodos separados; no fija nombre JSON. `periodo_de_la_factura` cumple ese significado y `periodo` conserva el de la nota. Design D5 requiere bloqueo sobre factura y tope acumulado; el diff conserva ambos. No encontré contradicción en esas secciones. Ni design ni spec documentan literalmente el nuevo nombre: el contrato observable queda fijado por el código y el test de integración añadido por el constructor. No modifiqué contratos.

El comentario nuevo sobre asociación, tope y serialización corresponde a las consultas observadas. El rechazo parcial ocurre antes del any del guardia, coherente con el dominio. No reabrí S3 de Excel, que este diff no toca; sigue requiriendo disposición del auditor según informe previo.

## JUICIO

Autor: **Codex rompedor**. Confianza **alta** en los rechazos y UPDATE observados con dobles, **media** en cableado/contratos inspeccionados y limitada para SQL real por entorno.

**Intento 3 sin fallas reproducidas en el alcance examinado.** F2-1 queda cubierto por pruebas enfocadas ejecutadas. S4 tiene implementación coherente y evidencia PostgreSQL ajena del constructor, que no cuento como ejecución propia. Antes de cerrar, el orquestador debe ejecutar el test pendiente y el auditor resolver la suficiencia de evidencia y deuda existente. No habilito archivo ni afirmo suite completa.

## SUPOSICIÓN

- PostgreSQL, JOIN real, RLS y carreras no ejecutados: Docker no disponible según brief. El test nuevo de período editado está listo, marcado integracion y sólo recolectado.
- No hay lista de notas en la superficie buscada; si otro consumidor externo no versionado existe, no fue examinado.
- No corrí build, suite completa, CI remoto, migraciones ni ensayo de roles. No hice commits ni push. Engram no disponible; obsidian.md ausente en este worktree. No actualicé memoria externa por el alcance exclusivo del worktree.

## Fuentes leídas

Instrucciones heredadas y CLAUDE local; KB15 lecciones (salida extensa parcialmente truncada, sin afirmar lectura íntegra); skill local `.claude/skills/openspec-verify-change/SKILL.md` como guía subordinada al rol; CLI list/status/instructions; diff indicado; informes verify-1 y verify-2 (lecturas acotadas, con truncamiento declarado) e índice; tasks vía CLI y encabezado; spec notas completa; secciones pertinentes de design mediante búsquedas; gastos/aplicacion/gastos.py y notas_de_credito.py; dominio/gasto.py; router gastos y cuerpo de edición; migración 0032 por búsquedas; test_gastos_aplicacion completo y secciones nuevas/helpers de test_notas_de_credito; búsquedas de consumidores en backend/web. No leí ni expuse secretos. No hice auditoría de vigencia de toda la KB, fuera del diff de esta corrección.

## Contaminación

El brief contiene las afirmaciones del constructor. `instructions apply` muestra tasks y sus afirmaciones antes del análisis: contaminación declarada. Leí **apply-3-constructor.md después del análisis propio, de los 68 verdes iniciales y de escribir ambos archivos de ataque**. Sus resultados de integración/mutantes son evidencia ajena, no reproducida aquí. Reutilicé helpers de fixtures/dobles del test existente, por lo que no reclamo independencia de esa infraestructura ni acuerdo por mera diferencia de nombres. No busqué otros revisores para fabricar consenso.

## FALLAS REPRODUCIDAS

**ninguna**.

Producción intacta. Entrega: este original, entrada en LEEME y dos archivos de pruebas, uno de ellos pendiente PostgreSQL. No iniciar una cuarta ronda automática si la integración pendiente reproduce una falla: corresponde al orquestador aplicar el límite del gate y consultar la disposición humana.
