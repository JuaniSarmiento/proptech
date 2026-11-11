# propose-5 · planner · PR-15

Autor: planner (subagente nativo Claude, Opus 5.5). Revisión base: `533a440` + árbol sin commitear de
`openspec/changes/intereses-saldo-inicial-y-moroso/`. Alcance acotado por Juani: sólo PR-15.

## Cambios

- `specs/intereses-por-mora/spec.md:258-264`: escenario nuevo "Detalle de un pago total con mes entero"
  (requisito "Cada interés guarda su detalle por tramo"), junto a "Detalle de un pago total" (251-256, sin
  tocar): $100.000, vence 10/09/2026, 3% mes entero, gracia 0, pago total fecha valor 20/09, corte
  30/09 → $3.000,00, un tramo 11/09-30/09 con base $100.000.
- `tasks.md:171-174` (4.3): mutante "aplicar a mes entero la exclusión de días con base diaria cero" →
  rojo por fechas en el escenario nuevo (11/09-20/09 en vez de 11/09-30/09); el escenario va en 4.3 con
  importe y fechas.
- `tasks.md:195-205` (4.5, propiedad de cobertura): la exclusión de días con base diaria cero vale sólo
  en proporcional; en mes entero la cobertura es el tramo mensual completo con la base de su primer día a
  cobrar aunque después haya pago total. Dos `@example` fijos: el proporcional ($1.000,00) y el
  discriminante de mes entero ($3.000,00). Se conservan no solapamiento (línea 193-194) y el hueco de
  $5.000,00 (4.4, sin tocar).
- Sin cambios en `design.md` (163-177 ya define mes entero con la base del primer día a cobrar), ni en
  `## Estado del orquestador`, ni en otros informes.

## EVIDENCIA

- `2026-10-30T20:49:11-03:00`, `python3` con `Decimal` y `ROUND_HALF_UP`: mes entero 100000*3/100 =
  3000.00; proporcional 10 días = 1000.00; hueco 20+30 días = 5000.00.
- Mismo momento: `openspec validate intereses-saldo-inicial-y-moroso --strict` → "Change
  'intereses-saldo-inicial-y-moroso' is valid".

## SUPOSICIÓN

- Que el escenario nuevo, de dominio puro, corresponde a 4.3 y no a 5.x (integración); no se agregó
  versión de integración por el alcance acotado.
- No se releyó el resto del plan buscando otras frases que mezclen base diaria y base de tramo.

## Fuentes y contaminación

Leí `informes/propose-4-plan-reviewer.md:78-93`, `tasks.md:136-214`, `spec.md:110-124,236-265`,
`design.md:160-177`. Contaminación: el caso y la disposición vienen del informe de Codex (PR-15); los
importes los recalculé de forma independiente.
