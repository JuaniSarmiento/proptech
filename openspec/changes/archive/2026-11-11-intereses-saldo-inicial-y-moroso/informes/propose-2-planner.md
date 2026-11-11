# Planner · propose · intento 2

- Rol: planner (role-planner nativo, Claude). Corrige el plan del intento 1 según
  `informes/propose-1-plan-reviewer.md` (Codex, VUELVE AL PLANNER).
- Revisión: `main` en `533a440`, más los artefactos sin commitear del change. Sin commit.
- Fecha: 30/10/2026, Argentina (UTC-03).
- No se tocaron `informes/propose-1-*.md`, `informes/LEEME.md` ni la sección `## Estado del orquestador`
  de `tasks.md` (verificado con `diff` de las 12 primeras líneas antes de reemplazar el cuerpo: sin
  diferencias). Copia del intento 1 en el scratchpad de la sesión, fuera del repo.

## Disposición por hallazgo

| PR | Disposición | Qué cambió y dónde |
|---|---|---|
| PR-01 (CORREGIR) | Aceptado | `design.md:39-46` (Context: `configuracion_vigente` lanza `NoEncontrado` si el edificio no es visible y devuelve `None` sin versión, verificado en `complejos/aplicacion/lectura.py:213-227`); `design.md` D1 (`:109-136`, `None` → `Conflicto("configuracion")`, `NoEncontrado` se propaga) y D6 (`:279-298`); spec intereses-por-mora requisito nuevo "Sin configuración vigente al corte la emisión se rechaza" (`:166-188`) con escenarios "Sólo una versión futura" y "Edificio de otra administración"; spec situacion-de-cobranza `:144-150`; tarea 5.2 (`tasks.md:193-203`) con `contar_escrituras` y el mutante de traducir `NoEncontrado` asignado a la 7.2 (`tasks.md:289-307`), porque en la emisión la FK de `emision` rechaza antes de leer la configuración (declarado en la tarea) |
| PR-02 (BLOQUEANTE) | Aceptado | Concepto nuevo "cuentas alcanzadas" en `design.md` D0 (`:88-108`): unión de cuentas con obligación y con movimiento de la emisión, un solo `bloquear_cuentas` ordenado en anulación, replay y foto final. Verificado que ningún otro caso de uso escribe `movimiento.emision_id` (`rg` en `correcciones.py`, `creditos.py`). Spec libro-de-movimientos reescrita (`:5-70`): RF-01 sobre cuentas alcanzadas con escenario de U2, requisito nuevo "La anulación bloquea todas las cuentas alcanzadas", escenario "Anulación durante el contra-asiento de un interés de una cuenta sin obligación". Tarea nueva 5.4 (`tasks.md:213-225`) con RED real (el código de hoy, `emisiones.py:257-265`, bloquea sólo U1), espía de `bloquear_cuentas` y tres mutantes; D8 (`design.md:304-320`). E10 anota la consecuencia técnica (`design.md:361`) |
| PR-03 (BLOQUEANTE) | Aceptado; elección humana E13 | `design.md` D2 (`:137-175`) reemplaza "inicio natural / último corte" por **cubierto hasta** (vencimiento o migración, o el fin del último tramo de un interés que cuenta) y ancla los bloques de "mes entero" en el inicio del tramo. Resuelve la obligación migrada y el cambio de forma sin hueco ni doble cobro. D3 suma `cubierto_hasta` a la foto en la misma sentencia (`:176-191`). E13 nueva (`design.md:364`) con tres alternativas y su consecuencia. Spec intereses-por-mora: requisito "Cada corte calcula desde lo ya cubierto" (`:86-99`), "Forma de cálculo" reescrito con escenarios "De proporcional a mes entero" y "De mes entero a proporcional" (`:100-139`), "El interés se corta al cierre" ajustado a mes entero (`:140-152`). Spec saldo-inicial: escenarios "Mes entero después de migrar", con y sin interés importado, y "Segundo bloque después de migrar" (`:114-131`). Tareas 3.2, 4.3 y 6.3 con mutantes |
| PR-04 (CORREGIR) | Aceptado; elección humana E14 | Opción por defecto: fecha de **clasificación** sobre el libro actual, sin historia (`design.md` D6 `:279-298`, E14 `:365`). Spec situacion-de-cobranza: requisito nuevo "La fecha de la situación clasifica, no reconstruye historia" con escenario "Un pago posterior cuenta aunque la fecha sea anterior" (`:131-143`). Tarea 7.2 con mutante que filtra por `fecha_valor <= fecha`. Non-Goals de `design.md` (`:83-84`) |
| PR-05 (BLOQUEANTE) | Aceptado; elección humana E15 | Opción por defecto: separar intereses estables de saldo recalculado, coherente con RB4B-05 (`emisiones.py:113-115`). `design.md` D1 (`:127-131`), E15 (`:366`). Spec intereses-por-mora: requisito nuevo "Repetir la emisión devuelve los mismos intereses y recalcula el saldo" (`:275-301`) con replay inmediato, después de un pago ($72.000,00) y después de anular ($100.000,00). Tarea 5.3 (`tasks.md:204-212`) con tres mutantes |
| PR-06 (CORREGIR) | Aceptado | Matriz de mutantes por defensa y por tabla en la tarea 2.1 (`tasks.md:69-98`): `FORCE` lo detectan el catálogo (`test_catalogo_rls.py`, `revisar_catalogo` `:264-275` llama a `_rls_forzada` `:111-118`) y el chequeo de arranque (`roles.py:788-800`), no el aislamiento de la app; `ENABLE`+política, el aislamiento como app con precondición de rol; `REVOKE`, el SQLSTATE `42501` contra `P0001`; FK con cuenta. Filtro SQL de cobranza separado de RLS con conexión privilegiada, precondición afirmada y transacción revertida (tarea 7.2). `design.md` Context (`:47-54`) y D10 (`:328-343`). Además, por la nota del revisor sobre D4: `tramo_de_interes` pierde `obligacion_id` y su FK a `movimiento` pasa por `uq_mov_sentido` (`0023:131-132`) que fija la cuenta; origen con FK que fija la cuenta; FK a `complejo` que exige el catálogo; `configuracion_id` sin FK porque `configuracion_versionada` no da `REFERENCES` (`roles.py:920-935`) (`design.md` D4 `:192-218`, D5 `:256-271`) |
| PR-07 (CORREGIR) | Aceptado; elección humana E16 | Opción por defecto: el 4c recibe filas del archivo y agrupa por unidad y período; vencimientos distintos en un período y fila repetida se rechazan; cada fila se liga a lo que formó (`design.md` D5 `:219-278`, E16 `:367`). El signo del crédito queda como responsabilidad del 5. Spec saldo-inicial: requisito "Las filas con detalle se agrupan en una obligación por período" con "Dos conceptos del mismo período" y "Mismo período con vencimientos distintos" (`:38-64`), "Fila de sólo interés junto a otra con capital" (`:94-99`), "Origen de dos conceptos del mismo período" (`:161-165`), rechazos partidos en dos requisitos (`:177-209`) con "Fila repetida". Tareas 6.1 y 6.2 |
| PR-08 (CORREGIR) | Aceptado | Escenario "Redondeo único sobre dos tramos" con el ejemplo del revisor llevado a fechas e imputación concretas: $64,00 que vence 28/09, pago $1,00 con fecha valor 29/09, tramos 29/09 ($0,064) y 30/09 ($0,063), $0,13 contra $0,12 por tramo (spec intereses-por-mora `:201-206`). El de $62,50 queda renombrado "Medio centavo hacia arriba" y mata el mutante de modo de redondeo, no el de momento (`:195-199`). Tarea 4.1 (`tasks.md:131-142`) nombra qué escenario mata cada mutante; 4.5 aclara que el escenario fijo es el que garantiza el rojo; 5.1 lo repite contra la base |
| PR-09 (MENOR) | Aceptado | E6 como ratificación de D-143 sin alternativa (`design.md:357`; `proposal.md:75-80`; spec situacion-de-cobranza `:39-44`). Referencias: `proposal.md:139` (2.1, 5.5, 8.1); `design.md` Risks (`:369-397`) a 2.2, 5.5, 2.1 y 8.1; tarea 1.2 con el mutante del replay en `emisiones.py:117` (la `:116` es el bloqueo), también en D8 |

### Elecciones para el humano (tabla del revisor, líneas 172-185)

- **E1** (`design.md:352`): ya no promete "la plata no se pierde"; dice que los días diferidos se cobran
  cuando exista una emisión siguiente, con la configuración de ese corte, y que el importe puede
  diferir. Escenario nuevo "El tramo recuperado usa la tasa del corte siguiente" ($10.200,00 contra
  $8.200,00 sin anular). Aclara que PR-02 y PR-05 se resuelven aparte.
- **E3** (`:354`): presentada como elección explícita que D-113 no fija; el anclaje pasa a E13.
- **E7** (`:358`): elección adicional al texto amplio de R20, no deducción de D-143; el caso mixto
  explícito con la alternativa y su consecuencia.
- **E11** (`:362`): dice que excluye una entrada plausible del Excel y pide aceptar la limitación para el
  contrato del 5; con E16 por defecto, la exclusión se acota al período sin capital.
- **PA-1** (`design.md:408-411`, `proposal.md:81-82`): el 4c no declara cumplida la corrección
  posconfirmación de R09; queda bloqueante del 5 (también en el impacto en la KB y en 6.4).

### Lo que no se reabrió

D-143, P53, P54, P57 a P60, la cantidad de tareas (el revisor no recomendó partir; ahora son 24 por la
5.4 nueva), D9, D7, E2, E4, E5, E8, E9 y E12 salvo referencias. `specs/reparto-de-montos/spec.md` sin
cambios.

## EVIDENCIA

| Comando | Hora (UTC-03) | Salida relevante |
|---|---|---|
| Lectura de `propose-1-plan-reviewer.md:1-215` y de los artefactos del intento 1 | 18:20 aprox., sin reloj capturado | Base de las correcciones |
| `bat` y `rg -n` sobre `emisiones.py` (`:85-121`, `:116-117`, `:193`, `:221`, `:224`, `:232-285`, `:257-265`), `correcciones.py:150-200`, `lecturas.py:30-80,140-188`, `estado.py:60-110`, `lectura.py:200-245`, `ayudas_rls.py:35-50`, `roles.py:780-800,890-945`, `tablas_protegidas.py`, `0023:78-90,120-210`, `test_catalogo_rls.py:95-135,230-300`, `conftest.py:95-160`, `test_libro_rollback.py` | 18:20-18:29 | Citas verificadas; corregidas en el acto tres que había escrito mal (`roles.py:920-935`, `0023:82-83` para `ck_obligacion_importes`, `test_catalogo_rls.py:111-118`) |
| `date -Iseconds; openspec validate intereses-saldo-inicial-y-moroso --strict` (primera) | 18:30:09 | exit 1: cuatro WARNING de requisitos de más de 500 caracteres. Se partieron en dos cada uno |
| `date -Iseconds; openspec validate intereses-saldo-inicial-y-moroso --strict` (segunda) | 18:30:45 | `Change 'intereses-saldo-inicial-y-moroso' is valid`, exit 0 |
| `openspec status --change intereses-saldo-inicial-y-moroso --json` | 18:30:45 | `isPlanningComplete: true`; proposal, specs, design y tasks `done`. Es estado de artefactos, no aprobación |
| `openspec show ... --json --deltas-only` | 18:30:45 | 36 requisitos, 92 escenarios en los deltas |
| `rg -c '^- \[ \]' tasks.md`; búsqueda de em dash en todos los artefactos | 18:30:45 | 24 tareas; ningún em dash |
| `python3` con `Decimal` y `datetime`, sin importar producción | 18:30:54 | Dos tramos: 0.13 único, 0.12 por tramo; $62,50: 0.13 HALF_UP, 0.12 HALF_EVEN; migrado mes entero 2400.00 y 2550.00, bloque hasta 14/11, siguiente 15/11; mes entero → proporcional 200, mutante 3100; proporcional → mes entero 2000, bloque hasta 30/10; recuperado al 6%: 51 días, 10200.00 contra 8200.00; replay después del pago 72000; mutante interés sobre interés 3162 |
| `git status --short`; `git diff --name-only` | 18:30:45 | Sólo `?? openspec/changes/intereses-saldo-inicial-y-moroso/`; ningún archivo rastreado cambiado |

## JUICIO

Autor: planner (Claude). Comparé cada hallazgo con el código citado y con los artefactos del intento 1.
Confianza alta en PR-01, PR-02, PR-05, PR-08 y PR-09 (contrato y aritmética verificados). Confianza
media-alta en PR-03: "cubierto hasta" resuelve el caso migrado y el cambio de forma con una sola regla,
pero introduce una lectura nueva en la foto (`cubierto_hasta` desde `tramo_de_interes`) cuyo plan de
`EXPLAIN` no está medido. Confianza media-alta en PR-06: la matriz identifica qué defensa vigila cada
test, pero que el chequeo de arranque falle exactamente por `FORCE` en una tabla nueva es lectura de
`roles.py:788-800`, no ejecución. Confianza media en PR-07: el contrato de filas es técnicamente
coherente con `uq_obligacion_operacion`, pero no conozco el Excel real.

Recomendación por elección (detalle en `design.md`, "Elecciones a firmar"): E13 anclar en lo cubierto;
E14 fecha de clasificación; E15 separar intereses estables de saldo recalculado; E16 agrupar en el 4c.

## SUPOSICIÓN

- No se corrió ningún test, mutante, migración ni Docker: todo comportamiento futuro es análisis.
- Que una conexión privilegiada de los tests salte RLS (para el ensayo del filtro SQL de 7.2) se infiere
  de `test_catalogo_rls.py`, que hace `SET LOCAL ROLE` desde ella; la tarea exige afirmarlo como
  precondición en vez de suponerlo.
- Que la FK compuesta a `movimiento` por `uq_mov_sentido` sea creable por el migrador se apoya en el
  `GRANT REFERENCES` de `roles.py:920-935` sobre `movimiento`; no se probó.
- Que un contra-asiento pueda tomar como blanco un movimiento `interes` sale de leer
  `correcciones.py:167-189` (sólo rechaza un débito de corrección); no se ejecutó.
- No se inspeccionó un Excel real; E16 supone que el 5 puede traducir concepto a componente y el signo
  del saldo a fila de crédito.
- Engram no se consultó; la autoridad fue el repo y el encargo. No se actualizó `obsidian.md` ni la KB
  (son de la etapa de archivo).

## Fuentes leídas

`informes/propose-1-plan-reviewer.md:1-215`; `proposal.md`, `design.md`, `tasks.md` y las cinco specs del
intento 1; `knowledge-base/09_decisiones_y_supuestos.md:2926-2953` (D-143);
`knowledge-base/05_reglas_de_negocio.md:173-217,340-372` (R03, R04, R09); el código y los tests citados en
EVIDENCIA. No se releyó `informes/propose-1-planner.md` (es mío del intento 1).

## Contaminación

Este intento parte del informe de Codex por diseño: sus hallazgos y su tabla de elecciones fijaron qué
corregir. Usé su inventario de consumidores de `registrar_emision` (`:151-160`) y sus líneas de
`test_libro_rollback.py` sin rehacer la búsqueda completa; las líneas de `0033` sí las verifiqué. El
ejemplo numérico de PR-08 ($64 y $63) es suyo; las fechas, la imputación y los demás montos son míos y
están recalculados arriba. No leí informes de otros revisores.
