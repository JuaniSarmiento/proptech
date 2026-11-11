# Plan-reviewer · propose · intento 2

- Rol: plan-reviewer. Ejecutor: Codex, ejecución directa de esta sesión, sin `codex exec` anidado. El identificador exacto del modelo y el effort no están expuestos en la sesión; no los infiero del nombre del producto ni del informe previo.
- Fecha: 30/10/2026, Argentina (UTC-03). Chequeos principales entre 18:34:31 y 18:35:43.
- Revisión: rama `main`, SHA `533a44027d16819fd774c404372b5e5dbd39917d`, más el directorio del change sin commitear. `git status --short`: únicamente `?? openspec/changes/intereses-saldo-inicial-y-moroso/` al empezar.
- Alcance: correcciones PR-01 a PR-09 y sus consecuencias nuevas, elecciones E1 a E16 y PA-1. Única escritura: este informe. Sin suite, build, commit ni cambios al plan. No se evalúa como faltante la firma humana, que viene después de esta revisión.

## Fuentes leídas

En las citas siguientes, `proposal.md`, `design.md`, `tasks.md`, `specs/` e `informes/` son relativos a `openspec/changes/intereses-saldo-inicial-y-moroso/`.

- `informes/propose-1-plan-reviewer.md`, incluidos PR-01 a PR-09 y las precisiones de esquema y consumidores; `informes/propose-2-planner.md` completo. La primera salida extensa se truncó parcialmente; se completaron las precisiones y elecciones mediante lectura focalizada de las líneas 145-190.
- `proposal.md:1-171`, `design.md:1-416`, `tasks.md:1-328`. Lectura inicial y focalizadas posteriores, especialmente D0-D6, D8-D10, elecciones y matriz de mutantes.
- `specs/intereses-por-mora/spec.md:1-299`, `specs/saldo-inicial/spec.md:1-240`, `specs/situacion-de-cobranza/spec.md:1-166`, `specs/libro-de-movimientos/spec.md:1-69`, `specs/reparto-de-montos/spec.md:1-26`.
- `CLAUDE.md`, instrucciones AGENTS del encargo y `obsidian.md` (nota existente, sólo lectura).
- `CHANGES.md:574-618`; `knowledge-base/12_fichas_de_changes.md:677-740`.
- `knowledge-base/05_reglas_de_negocio.md:173-217,340-409,792-825` (R03, R04, R09, R30 y R20).
- `knowledge-base/09_decisiones_y_supuestos.md:2020-2046,2551-2598,2926-2953` (D-113, D-130, D-143).
- `knowledge-base/15_lecciones.md:461-480,505-520,959-968` (defensas que se tapan y evidencia); búsqueda de títulos pertinentes. No se declara lectura completa de las lecciones en este intento.
- `backend/src/proptech_core/cuenta_corriente/aplicacion/emisiones.py:85-121,232-285`; `lecturas.py:30-75,140-188`; `correcciones.py:160-194`; `dominio/estado.py:85-125`.
- `backend/src/proptech_core/complejos/aplicacion/lectura.py:213-227`.
- `backend/migraciones/versions/0023_libro_de_movimientos.py:78-90,120-145,190-210`.
- `backend/src/proptech_core/compartido/roles.py:775-805,895-938`.
- `backend/tests/integracion/test_catalogo_rls.py:100-120,260-280`.

## EVIDENCIA

Todo es evidencia estática sobre la revisión del encabezado. Los intervalos financieros son oráculos independientes, sin importar producción. Las transcripciones de herramientas contienen las lecturas; no se creó un archivo adicional de logs.

| Comando | Hora local | Salida relevante |
|---|---|---|
| `pwd`; `git status --short`; `git rev-parse HEAD` | Antes de 18:34:31, sin reloj capturado | Repo esperado, SHA completo del encabezado, sólo el directorio del change sin rastrear |
| `date -Iseconds`; `openspec list --json` | 18:34:31 | Change `in-progress`, 0/24 tareas |
| `openspec status --change intereses-saldo-inicial-y-moroso --json` | 18:34:31 | `isPlanningComplete: true`, cuatro artefactos `done`. Es estado de artefactos, no aprobación ni implementación |
| `openspec instructions proposal --change intereses-saldo-inicial-y-moroso --json` | 18:34:31 | Esquema `spec-driven`, rutas locales, contexto y reglas de KB/TDD/CRITICAL recuperados; no se ejecutó propose |
| `bat`, `rg --files`, `rg -n` y `python3` con `Path.read_text().splitlines()` numerado | Entre 18:34:31 y 18:35:43; no se capturó reloj por lectura | Artefactos y código citados en las secciones siguientes; búsqueda explícita de índices, únicos, replay y huellas en design/tasks |
| `date -Iseconds`; `openspec validate intereses-saldo-inicial-y-moroso --strict` | 18:35:17 | Salida exacta debajo; exit 0 |
| `openspec --version` | 18:35:17 | `1.14.3`. Se informa la discrepancia con la versión fijada por el proyecto, sin instalar ni modificar herramientas |
| `python3` con `Decimal` desde texto, `ROUND_HALF_UP` y `datetime` | 18:35:17 | Dos tramos: `0.064 + 0.063`, único `0.13`, por tramo `0.12`. Bloques desde 01/10 al corte 31/10: 01/10-30/10 y 31/10-29/11; total `6000.00`. Migrados: proporcional `1280.00`/`1360.00`, mes entero `2400.00`/`2550.00`. Replay `72000`, anulado `100000`; 51 días al 6% `10200.00` |
| `date -Iseconds`; `python3` con intervalos y `Decimal` | 18:35:43 | Con interés de octubre vigente hasta 31/10 y el de septiembre contra-asentado, el máximo sigue siendo 31/10 y el próximo inicio 01/11: no recupera 11/09-30/09 (`2000`). Dos entradas por fila `85000+20000` y `84000+21000`, mismo componente, suman ambas `105000` y tienen las mismas referencias de origen |

Salida de validación:

```text
Change 'intereses-saldo-inicial-y-moroso' is valid
```

La validación estructural no detecta las contradicciones semánticas de PR-10 a PR-12. No se corrió suite ni mutante.

## Tabla de cierre PR-01 a PR-09

| Número | Descripción corta | Estado | Evidencia |
|---|---|---|---|
| PR-01 | Ausencia de versión frente a edificio invisible | CERRADO | `design.md:118-120,285-296`, `specs/intereses-por-mora/spec.md:166-188`, tarea 5.2 y tarea 7.2. Coincide con `complejos/aplicacion/lectura.py:213-227`: `None` se traduce, `NoEncontrado` se propaga. El caso de emisión ajena queda como regresión, y el mutante de traducción se asigna a cobranza, donde puede discriminar |
| PR-02 | Anulación de cuentas con sólo interés | CERRADO | `design.md:88-103`, `specs/libro-de-movimientos/spec.md:25-41,63-69`, tarea 5.4 (`tasks.md:213-225`): unión obligación/movimiento, bloqueo único ordenado, carrera y replay de U2. Contrasta correctamente con la selección restringida actual de `emisiones.py:257-265` y con el candado previo al chequeo de `correcciones.py:180-189` |
| PR-03 | Anclaje de mes entero tras migrar | PARCIAL | El caso migrado original está resuelto: `design.md:143-168`, E13, `specs/saldo-inicial/spec.md:114-130`, tareas 4.3/6.3. La generalización al cambio de forma introduce el resultado incompatible de PR-10 y la garantía de continuidad no se sostiene en PR-12 |
| PR-04 | Semántica de consulta a fecha | CERRADO | `design.md:279-296`, E14, `specs/situacion-de-cobranza/spec.md:131-142`, tarea 7.2. Fecha sólo selecciona vencimiento/configuración; libro actual sin filtro histórico. Es compatible con `lecturas.py:44-64,145-150` |
| PR-05 | Replay y saldo estable inexistente | CERRADO | `design.md:123-130`, E15, `specs/intereses-por-mora/spec.md:275-299`, tarea 5.3: intereses originales estables y saldo recalculado, incluidos pago y anulación. Respeta la limitación real de `emisiones.py:113-121` y `estado.py:91-97` |
| PR-06 | Mutantes tapados por otras defensas | CERRADO | Matriz de tarea 2.1 (`tasks.md:69-98`) y ensayo privilegiado de tarea 7.2 (`:298-304`). FORCE se observa por catálogo/arranque, no por app: soporte real en `test_catalogo_rls.py:111-118,268-274` y `roles.py:792-798`. SQL se separa de RLS con precondición explícita. Las FK nuevas fijan cuenta (`design.md:198-211,264-267`). Cierre del diseño de pruebas, sin afirmar ejecución |
| PR-07 | Agrupación de filas por período | PARCIAL | Responsable, agrupación, vencimientos y referencias múltiples ahora existen en `design.md:227-267`, E16, `specs/saldo-inicial/spec.md:38-64,149-165`, tareas 6.1/6.2. Resuelven el choque con el único de `0023:199-200`. Falta que la nueva granularidad sea preservable para cumplir el replay por filas: PR-11 |
| PR-08 | Redondeo por tramo sin ejemplo discriminante | CERRADO | `specs/intereses-por-mora/spec.md:195-206`, tareas 4.1/4.5/5.1. Pago de $1 con fecha 29/09, efecto desde 30/09, produce bases $64/$63 y `0.13` contra `0.12`. El ejemplo de $62,50 queda correctamente dedicado al modo HALF_UP |
| PR-09 | E6 y referencias obsoletas | CERRADO | E6 en `design.md:357`, `proposal.md:75-80`, spec cobranza `:39-44`: ratificación sin alternativa. Referencias corregidas en `proposal.md:133-141`, `design.md:309-310,371-396`, tareas 1.2/5.5/8.1. La lectura de replay está efectivamente en `emisiones.py:117` |

## Hallazgos nuevos

### PR-10 · El cambio de proporcional a mes entero exige $3.000 donde su regla calcula $6.000

- **Fuente:** `design.md:158-168`, E13 (`:364`); `specs/intereses-por-mora/spec.md:102-106,126-131`; tarea 4.3 (`tasks.md:149-159`).
- **Observación:** tras el corte proporcional 30/09, lo cubierto termina el 30/09 y el nuevo tramo comienza el 01/10. La regla cobra cada bloque cuyo inicio es menor o igual al corte. Al 31/10 empiezan dos bloques: 01/10-30/10 y 31/10-29/11. Con $100.000 al 3%, cada uno vale $3.000, por lo que el resultado es $6.000. El escenario y la tarea sólo esperan $3.000 y un tramo hasta 30/10. No es un problema de redondeo: son dos bloques frente a uno.
- **Disposición: BLOQUEANTE.** Alinear algoritmo, escenario, E13 y mutantes antes de firma. Si la intención es cobrar únicamente un bloque en este caso, hace falta explicar qué regla impide cobrar el que empieza el 31/10 y cómo se concilia con cobrar un mes completo por un día de atraso. No elijo esa convención por el humano.

### PR-11 · Agrupar pierde los datos por fila necesarios para el replay prometido

- **Fuente:** E16 (`design.md:367`), contrato y persistencia D5 (`:227-267`), `specs/saldo-inicial/spec.md:5-7,149-165,210-224`, tareas 6.2/6.4 (`tasks.md:252-276`).
- **Observación:** el contrato recibe importes e interés por fila; el replay exige mismos datos y rechaza cambiar el importe de una fila. La obligación conserva sumas por componente; el interés conserva la suma del período; origen sólo guarda referencias y número de fila, sin aporte de capital/interés por fila ni firma canónica del pedido en la carga. Dos filas de septiembre del mismo componente, mismo vencimiento, filas 12/13, por $85.000/$20.000 frente a $84.000/$21.000 dejan exactamente el mismo capital de $105.000, mismo interés (por ejemplo $3.000 sólo en fila 12) y las mismas relaciones de origen. Son pedidos distintos indistinguibles en el esquema descrito. El nombre del archivo no recupera su contenido. Lo mismo ocurre al redistribuir interés entre filas que ya tenían interés positivo. La alternativa de E16 atribuye pérdida del aporte por fila sólo al agrupamiento en el 5, pero el diseño recomendado también lo pierde.
- **Disposición: CORREGIR.** Definir persistencia suficiente para comparar el pedido original, por ejemplo los aportes originales o una firma canónica del pedido validado guardada en la carga, con semántica explícita sobre orden/normalización. Agregar replay con sumas iguales y aportes por fila diferentes, y su mutante. Alinear también la afirmación de trazabilidad y la comparación de alternativas en E16. No alcanza el escenario actual que cambia un importe alterando el total.

### PR-12 · El máximo de cobertura no recupera un hueco anterior a un interés posterior vigente

- **Fuente:** `design.md:145-150,158-168`, E1 (`:352`), E13 (`:364`), PA-2 (`:412-414`); `specs/intereses-por-mora/spec.md:86-98,236-242`; propiedad de tarea 4.5 (`tasks.md:170-173`). Viabilidad del contra-asiento: `correcciones.py:167-194`, exclusión de pares en `estado.py:112-124`.
- **Observación:** para la obligación de septiembre por $100.000 vencida el 10/09, octubre registra $2.000 hasta 30/09 y noviembre registra $3.100 desde 01/10 hasta 31/10. Después se contra-asienta sólo el interés registrado en octubre. El interés de noviembre sigue contando. D2 toma como cubierto hasta el máximo 31/10 y el corte siguiente empieza el 01/11: los días 11/09-30/09 nunca se recuperan. El caso no requiere borrar ni modificar filas. La API actual admite corregir un interés no corregido de emisión vigente; no impone que sea el último interés de esa obligación (`correcciones.py:185-194`). Por lo tanto, un máximo no demuestra cobertura continua. Contradice tanto la recuperación declarada de PA-2/E1 como la propiedad nueva de no dejar días sin cubrir con anulaciones generadas. Es una incompatibilidad deducida, no una falla runtime reproducida.
- **Disposición: BLOQUEANTE.** Definir el tratamiento de huecos: recuperación por intervalos, restricción explícita de las correcciones admitidas u otra decisión visible con su alcance. Agregar escenario de corrección de un interés anterior cuando hay otro posterior vigente y el mutante correspondiente. Si se acepta que esos días no se recuperan, exponer esa limitación al humano y corregir las promesas y la propiedad; no presentar el máximo como garantía general de continuidad.

## Evaluación de E1 a E16 y PA-1

Evaluación de planteo y coherencia, sin resolver elecciones humanas. Fuentes canónicas: R03 (`knowledge-base/05_reglas_de_negocio.md:173-201`), R09 (`:340-370`), R30 (`:381-398`), R20 (`:792-818`); D-113 (`knowledge-base/09_decisiones_y_supuestos.md:2020-2043`), D-130 (`:2551-2569`) y D-143 (`:2926-2953`). Las opciones están en `design.md:352-367`; PA-1 en `:408-411`.

| Punto | Evaluación de la pregunta y de su opción por defecto |
|---|---|
| E1 | Pregunta pertinente por el único real `0023:205-206`. El diferimiento respeta el libro que sólo agrega y la pertenencia del interés a la obligación de D-143. Está corregida la advertencia sobre tasa futura e inexistencia de equivalencia monetaria. La recuperación general sigue incompleta: PR-12. R03 no decide este diferimiento por sí misma |
| E2 | Clara y coherente: mes anterior al que se emite, último día por D-113 y registro en la siguiente liquidación de R03. D-143:2932-2934 conserva el mes de origen aunque se muestre después |
| E3 | Bien presentada como convención propuesta. R03 admite ambas formas y exige el mes completo por un día; D-113 fija redondeo/cierre, no divisor ni bloques de 30 días. /30 es una elección plausible, no un hecho de KB; necesita coherencia con E13 y PR-10 |
| E4 | Pregunta válida. Usar versión vigente al corte y no cambiar intereses registrados respeta historia de R03:196-197 y cierre de D-113. Una sola versión para días recuperados es una decisión adicional, visible en E1 y en el ejemplo del 6%; no la certifica el Excel de Alberto |
| E5 | Coherente con base impaga, pago parcial y gracia de R03:177,198-200. Fecha valor y efecto desde el día siguiente son convenciones explícitas de `design.md:151-155`, verificables en los ejemplos, incluido PR-08. No se probó ejecución |
| E6 | Correctamente es ratificación, sin decisión reabierta. `>=` cumple D-143:2938-2940 y el borde de R30:397-398. La palabra rezagada de R20 no desplaza esa decisión |
| E7 | La pregunta ahora hace visible que excluir períodos de sólo interés en el caso mixto es una elección adicional al texto de R20:794-799 y D-143:2946-2948. La categoría sólo intereses tiene sentido, pero extender su exclusión al caso mixto requiere la elección explícita que se está presentando, no deducción automática de D-143 |
| E8 | Contar obligaciones con capital y no meses distintos está expuesto, pero requiere cuidado: R20:803-805 dice cada período para saldo inicial y D-143 impide duplicar una expensa por su interés. E16 resuelve varios conceptos de una importación; una carga y una emisión con el mismo período podrían ser dos obligaciones. La opción es firmable como elección adicional si se entiende esa consecuencia (alternativa E8), no como mandato inequívoco de R20 |
| E9 | Coherente con R09: detalle/total, interés traído tal cual, fecha de migración, origen, crédito y cierre del importador. La implementación propuesta de agrupación/replay requiere PR-11. No se declara resuelta la corrección posconfirmación, separada en PA-1 |
| E10 | Alcance razonable para R03: una deuda no deja de generar interés porque su unidad no reciba obligación nueva ese mes. El candado ampliado y la unión en anulación/replay están definidos por D0 y tarea 5.4. Compatible con la deuda de pruebas asignada al 4c por D-130:2558-2563 |
| E11 | Restricción técnicamente fundada en `ck_obligacion_importes` de `0023:82-83`. Se plantea claramente que excluye una entrada plausible admitida conceptualmente por R09; no es cumplimiento universal de la importación. Agrupar permite la fila de sólo interés cuando el mismo período sí tiene capital, con escenario concreto. Aceptar la limitación corresponde al humano |
| E12 | Delegar autorización y auditoría a los llamadores es coherente con una capa de aplicación interna, no una ruta pública (`proposal.md:63-68`, `design.md:321-326`, spec saldo `:226-230`). Las reglas consultadas no exigen duplicarlas dentro del 4c. La elección no permite omitir tenant/RLS ni que el 5/10a dejen de autorizar; éstos son consumidores expresamente nombrados |
| E13 | La pregunta es necesaria y el default migrado evita cobrar antes de migración (R09:344-349), con y sin interés importado. El mecanismo por tramos permite continuar después de un bloque que pasa el corte. No está listo para firma: cambio de forma tiene importe contradictorio (PR-10) y máximo no garantiza continuidad general (PR-12). No modifica la prohibición de capitalización de R03 |
| E14 | Bien delimitada como clasificación del libro actual. R20:800-802 pide derivar la situación, no historia; R30 requiere configuración con vigencia. Default coherente para consultas actuales. La fecha sí decide vencimiento y versión de gracia/umbral (`design.md:292-294`), y ninguna selección histórica de movimientos; no se confunde con certificado histórico R21 |
| E15 | Bien planteada y viable estáticamente: intereses leídos por emisión permanecen identificables aunque no cuenten; saldo actual recalculado respeta el contrato actual `emisiones.py:113-121`. Los ejemplos de $102.000, $72.000 y $100.000 cierran en las precondiciones separadas de la spec. R03 conserva el importe registrado, no obliga a congelar todas las respuestas del replay. No requiere cuarta tabla con este default |
| E16 | Agrupar en 4c resuelve el choque con `uq_obligacion_operacion` y se ajusta a filas con concepto de R09 y períodos de R20. Rechazar vencimientos distintos es una limitación explícita, no inferencia de los datos reales. La pregunta compara responsabilidades reales, pero su default necesita preservar el pedido para replay y corregir la pérdida de información atribuida sólo a la alternativa (PR-11) |
| PA-1 | Pregunta fundada por R09:363-364 y la ficha `12_fichas_de_changes.md:725-729`. No tiene default resolutivo: propone mantener la decisión como bloqueante del 5 y reconocer cumplimiento parcial, explicitado en `proposal.md:81-82`, `design.md:388-411`, tarea 6.4. Es honesto y coherente como límite propuesto; no habilita el 5 ni resuelve R09 por diferimiento. No elijo un débito nuevo ni reabro R08 |

### Consultas, restricciones y seguridad del esquema corregido

Eliminar `obligacion_id` de `tramo_de_interes` es viable para las consultas descritas: D3 obtiene `max(tr.hasta)` por `(administracion_id, movimiento_id)` (`design.md:181-188`), con índice previsto en D10 (`:334-335`), y el movimiento conserva la obligación requerida por `ck_mov_interes` (`0023:87-89`). La FK de D4 puede usar el único existente `uq_mov_sentido` (`0023:131-132`) y su permiso REFERENCES existe en `roles.py:920-933`. El único de interés por obligación/corte vive en **movimiento**, no en tramo (`0023:205-206`); eliminar la columna duplicada no lo elimina ni exige cambiarlo.

D4 no declara un nuevo único por obligación/corte en la tabla de tramos (`design.md:194-214`); tampoco corresponde exigir uno que impida varios tramos legítimos. La suma y la ausencia de solapamiento quedan en el contrato de aplicación/tests (`spec intereses:210-219`, tarea 4.5), sin garantía adicional declarada en la base. Que el movimiento sea realmente tipo interés sigue siendo límite explícito de aplicación (`design.md:210-211`): la FK demuestra cuenta y sentido, no tipo. No se considera esa distinción una FK ya ejecutada.

La matriz PR-06 distingue correctamente catálogo FORCE, lectura con RLS y filtro SQL sin RLS. Los mutantes de FK y SQLSTATE tienen observadores discriminantes escritos en tarea 2.1; la exigencia de una corrida por defensa/tabla y precondición de rol está expresa (`tasks.md:77-90,298-304`). Quitar el helper de RLS apaga un conjunto (`ENABLE`, FORCE y política), tal como declara la fila: no debe reportarse después como demostración independiente de cada política. La evidencia que construya el constructor debe nombrar exactamente la defensa quitada y el rojo obtenido, conforme a las reglas comunes de `tasks.md:24-31`. No se certifica ahora un mutante ni una aserción runtime.

## JUICIO

Autor: Codex, plan-reviewer, intento 2. Comparé las respuestas del planner con los artefactos reales, los contratos y restricciones actuales del libro, y los pasajes canónicos indicados; recalculé con Decimal los casos nuevos. Siete hallazgos originales quedan cerrados en el plan; PR-03 y PR-07 quedan parciales por consecuencias introducidas por sus correcciones. El cierre es documental/estático, no implementación validada.

Confianza alta en PR-10 (contradicción entre algoritmo y número) y PR-11 (dos pedidos distintos producen el mismo estado persistido descrito). Confianza alta en la insuficiencia matemática del máximo de PR-12, y media-alta en su alcance operacional: la corrección es admitida por el código leído, pero no se ejecutó la secuencia contra base. Los tres requieren disposición explícita del planner; ningún informe leído sustituye la evidencia propia. D-143 se conserva y no se reabren P53/P54 ni se exigen P57-P60 antes de construir.

## SUPOSICIÓN

- No se ejecutaron suite, tests aislados, mutantes, Docker, PostgreSQL, migraciones, EXPLAIN ni código futuro del 4c. Los rojos nombrados siguen siendo objetivos de pruebas, no hechos observados.
- `openspec validate` pasó con la versión disponible 1.14.3; no certifico validación con la fijada 1.13.0. No alteré la instalación.
- Modelo exacto y effort no fueron suministrados por el entorno; no se inventa identidad para completar el encabezado.
- No se inspeccionó Excel real, no se investigó legislación ni se evaluó rendimiento. No se repitió el inventario completo del intento 1 ni su revisión general de migraciones/consumidores.
- No se recuperó Engram ni se consultaron revisiones hermanas para obtener acuerdo. No se actualizó memoria, Obsidian, tasks ni LEEME por la restricción de única escritura. Tampoco se hizo comparación histórica de fechas de autor de toda la KB; ninguna reescritura se autoriza desde este informe.
- La sección Estado del orquestador sigue mostrando informes del intento 1 como pendientes (`tasks.md:7`), aunque existen y fueron leídos. Es estado operativo heredado que el planner declara haber preservado, no ausencia material de los originales.
- El entorno permite escribir más rutas que la autorizada; se respeta el límite de manera operativa escribiendo únicamente este informe, sin afirmar sandbox por archivo.

## Contaminación

Leí explícitamente `informes/propose-2-planner.md` y mi propio `informes/propose-1-plan-reviewer.md` antes de este informe. Esta revisión está deliberadamente guiada por PR-01 a PR-09 y por las correcciones declaradas. No es una revisión ciega ni se reclama independencia por distinto nombre de rol. Verifiqué en los artefactos y en las líneas de código citadas las conclusiones usadas como evidencia; los recálculos nuevos son propios. No leí otros informes originales de revisores en este intento.

## Veredicto

VUELVE AL PLANNER

- PR-10, BLOQUEANTE: el escenario de cambio de forma contradice el algoritmo de bloques.
- PR-11, CORREGIR: la agrupación pierde la información necesaria para rechazar cambios por fila en replay.
- PR-12, BLOQUEANTE: el máximo de cobertura no recupera huecos anteriores a intereses posteriores vigentes.
