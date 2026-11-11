# Informe del planner · propose · intento 1

- **Change**: 4c `intereses-saldo-inicial-y-moroso` (C-07c), CRITICAL.
- **Rol**: planner (role-planner nativo, Claude Opus 5.5). Despachado por el orquestador el 30/10/2026.
- **Revisión base**: `main` en `533a440`, árbol con `openspec/changes/intereses-saldo-inicial-y-moroso/`
  sin trackear. Sin commit.
- **Artefactos entregados**: `proposal.md`, `design.md`, `tasks.md` (debajo de "Estado del
  orquestador", intacta), `specs/intereses-por-mora/spec.md`, `specs/saldo-inicial/spec.md`,
  `specs/situacion-de-cobranza/spec.md`, `specs/libro-de-movimientos/spec.md` (ADDED),
  `specs/reparto-de-montos/spec.md` (MODIFIED).

## EVIDENCIA

| Comando | Hora | Salida relevante |
|---|---|---|
| `openspec status --change intereses-saldo-inicial-y-moroso --json` (inicio) | 30/10/2026, antes de escribir | proposal `ready`, specs/design `blocked`, tasks `done` (sólo la sección del orquestador) |
| `openspec instructions {proposal,specs,design,tasks} --change ... --json` | idem | plantillas seguidas; reglas del proyecto: KB Impact, qué queda fuera, gobernanza, lecciones; tareas con test antes, ~20 tareas máximo, cada tarea cita su escenario |
| `openspec show <spec> --type spec --json --no-scenarios` para `libro-de-movimientos`, `reparto-de-montos`, `imputacion-de-creditos`, `fronteras-de-modulos` | idem | ningún requisito existente cubre interés, saldo inicial ni cobranza; "Un monto suelto se redondea medio hacia arriba" es el que modifica RB-6 |
| `rg` de imports entre módulos en `backend/src/proptech_core` | idem | `cuenta_corriente -> acceso, compartido`; `complejos -> acceso, compartido`; `gastos -> acceso, compartido, complejos`. `cuenta_corriente -> complejos.aplicacion` no crea ciclo |
| lectura de `backend/migraciones/versions/0023_libro_de_movimientos.py:20-240` | idem | `movimiento` no tiene columnas de días, tasa ni base; `uq_mov_interes(administracion_id,obligacion_id,corte) WHERE tipo='interes'`; `ck_mov_operacion` (interés puede ir sin `operacion_id`); `uq_mov_operacion` único por administración; `('saldo_inicial','credito')` sembrado |
| `eza backend/migraciones/versions` | idem | cabeza `0033_categoria_obligatoria_mensual.py`; la próxima es `0034` |
| `rg -no 'date\(2026, ?N, ?1\)' backend/tests` | idem | 74 períodos de octubre, 21 de noviembre, 7 de diciembre de 2026 en tests (motivo de no agregar un chequeo "corte <= hoy") |
| `openspec validate intereses-saldo-inicial-y-moroso --strict` | 2026-10-30T18:09:47-03:00 | `Change 'intereses-saldo-inicial-y-moroso' is valid` |
| `openspec status --change intereses-saldo-inicial-y-moroso --json` (final) | 2026-10-30T18:09:47-03:00 | `isPlanningComplete: true`; proposal, specs, design y tasks `done`; `nextSteps` sugiere apply, que **no** corresponde: la construcción espera la firma CRITICAL |
| `rg -c '^- \[ \]' tasks.md` | idem | 23 tareas |

Código leído para nombrar archivos ciertos: `cuenta_corriente/aplicacion/emisiones.py` (entero),
`compartido/reparto.py` (entero), `cuenta_corriente/dominio/estado.py` e `imputacion.py` (enteros),
`cuenta_corriente/aplicacion/lecturas.py:30-75`, `cuentas.py:44-155`, `creditos.py:59-125`,
`correcciones.py:83-235`, `complejos/aplicacion/lectura.py:178-230`,
`complejos/dominio/configuracion.py:1-80`, `tests/integracion/test_cc_anulacion_candado.py:1-60,110-230`,
`test_cc_correcciones.py:39-153`, `_cuenta_corriente.py:1-90`,
`tests/unitarios/test_fronteras_de_modulos.py` (reglas y `_DUENO_DE_TABLA`).

## JUICIO

Autor: planner. Comparación: reglas R03, R09, R17, R20, R30 y D-109, D-113, D-130, D-143 contra el
esquema de `0023` y el código de `emisiones.py`, `estado.py` y `lecturas.py`.

1. **Contradicción encontrada (confianza alta)**: D-143 dice que el 4c "no necesita otro contrato" que
   `uq_mov_interes(obligacion_id, corte)`. Pero R17 (vigente) exige excluir los intereses que registró
   una emisión anulada y permitir volver a emitir el período; la re-emisión necesita registrar el
   interés del **mismo** corte sobre la misma obligación vieja, y el único lo impide (23505). P53 ya lo
   advertía para el contra-asiento. No la resolví inventando: el plan lleva la propuesta E1 (el tramo
   pasa al corte siguiente, sin préstamo D-115.3), con dos alternativas, para firma.
2. **Ambigüedad de texto (confianza alta)**: R20 dice que el total vencido debe "superar" el umbral; el
   test mínimo de R30 y D-143 dicen "igual o por encima" / "$500 o más". El plan usa `>=` (E6) y propone
   corregir la palabra de R20 al archivar.
3. **Hueco de regla (confianza media)**: R09 manda corregir un saldo inicial mal cargado con R08, pero
   R08 no admite débito libre: un saldo cargado de menos no tiene corrección. No afecta al 4c; queda
   como PA-1 para el 5.
4. **Hueco de modelo (confianza media)**: `ck_obligacion_importes` no admite una obligación sin capital,
   así que un renglón viejo con sólo interés no entra. E11 propone rechazarlo; afecta al 5 y a Alberto.
5. **Cambio de contrato del 4b (confianza alta)**: meter el interés en `registrar_emision` cambia su
   resultado y exige configuración; la semilla `sembrar` no crea ninguna versión, así que la tarea 2.2 le
   suma una con tasa 0 y la 5.4 revisa la regresión una por una.
6. **RF-01 (confianza alta)**: concuerdo con D-138: la carrera con la anulación no puede matar el
   mutante porque ambas toman candados. La aserción nueva mira la última sentencia de foto y su `:ids`.
7. **Tamaño**: 23 tareas, sobre las ~20 de `openspec/config.yaml`. Lo justifico en `tasks.md`; lo
   evalúa el revisor del plan.

## SUPOSICIÓN

- **E2 · Corte = último día del mes anterior al período emitido.** Lo infiero del ejemplo de P53 ("la
  mora de agosto que aparece en la expensa de septiembre") y de los tests del 4b (vencimiento el día 10
  del mismo mes del período). Ninguna decisión lo dice con esas palabras. Pregunta 2 para Juani.
- **E3 · Tasa mensual / 30.** Ningún documento de la KB fija la convención diaria (`rg` sin resultados
  para 30/365 en la KB). A validar con P58/P42.
- **E4, E5, E7, E8, E10** son elecciones de diseño mías, no decisiones existentes; van a firma.
- No corrí ningún test ni migración: no existe código del 4c y el brief no pide factibilidad en
  ejecución. Los montos de los escenarios los calculé a mano (por ejemplo, 20 días × 0,1% × $100.000 =
  $2.000); los verifica el constructor con el oráculo de la tarea 4.5.
- No verifiqué que los planes de `EXPLAIN` de la foto sigan sin Seq Scan con el `LEFT JOIN` nuevo: queda
  en la tarea 3.2.
- No leí `knowledge-base/10_preguntas_abiertas.md` entera: sólo P53 a P60 (líneas 159-190).

## Fuentes leídas

- `CHANGES.md:574-610` (C-07c, C-07d, C-08).
- `knowledge-base/12_fichas_de_changes.md:677-745, 795-799, 851-856`.
- `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md` §4.5 (200-219), §8 (373-397), §9
  (399-440).
- `knowledge-base/05_reglas_de_negocio.md`: R03 (173-201), R04 (203-225), R05 (227-267), R06 (269-283),
  R07 (285-312), R08 (314-338), R09 (340-370), R30 (381-400), R17 (548-573), R20 (792-818).
- `knowledge-base/09_decisiones_y_supuestos.md`: D-109 (1876-1915), D-113 (2020-2043), D-115
  (2094-2120), D-129 (2507-2530, parcial), D-130 (2551-2600), D-143 (2926-2952).
- `knowledge-base/10_preguntas_abiertas.md:159-190` (P53 a P60).
- `knowledge-base/15_lecciones.md`: títulos completos; L-016, L-019, L-035, L-048, L-049, L-061, L-064
  enteras.
- `openspec/specs/libro-de-movimientos/spec.md:1-60, 88-180, 266-290`,
  `openspec/specs/reparto-de-montos/spec.md:124-138`, `openspec/config.yaml`.
- `openspec/changes/archive/2026-10-27-libro-de-movimientos/proposal.md` (sección Aprobación, formato).
- Código listado en EVIDENCIA.

## Contaminación por informes ajenos

Ninguna. No leí informes de otros roles de este change (no existen) ni de la regresión en
`.git/informes-regresion/`; lo que sé de RF-01, RF-02 y RB-6 sale de la ficha 4 y de D-130/D-138, que
citan esos informes.

## Preguntas abiertas para Juani

Cada una cambia lo que se construye; el plan está escrito con la propuesta y vuelve al planner si elegís
otra.

1. **E1 · Re-emisión.** Si anulás octubre y lo volvés a emitir, el interés de septiembre con corte 30/09
   no se puede registrar dos veces (único de `0023`). ¿Aceptás que ese tramo se cobre en la emisión de
   noviembre (misma plata, un mes después), o preferís construir el préstamo D-115.3 para cambiar el
   único?
2. **E2 · Corte.** ¿La emisión de octubre corta el interés el 30/09 (fin del mes anterior), como en el
   ejemplo de P53?
3. **E3 · Convención.** ¿Interés diario = tasa mensual / 30, y "mes entero" por bloques de 30 días?
4. **E6 · Umbral.** ¿$500 justos pasan el umbral (`>=`), como dicen R30 y D-143, aunque R20 diga
   "supera"?
5. **E7 · Período con sólo interés.** Si una unidad pagó el capital de agosto y le queda sólo el interés,
   ¿agosto deja de contar como liquidación vencida para el moroso crítico?
6. **E11 · Renglón viejo con sólo interés** en el Excel de migración: ¿se rechaza, como propone el plan?
7. **PA-1 (para antes del 5)**: un saldo inicial cargado de menos y ya confirmado, ¿cómo se corrige si
   R08 no admite débito libre?
