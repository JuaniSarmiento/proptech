# propose · intento 4 · planner

- Autor: planner (subagente Claude, Opus 5.5), por despacho del orquestador del 30/10/2026.
- Alcance: sólo PR-13 y PR-14 de `informes/propose-3-plan-reviewer.md:59-69`, por decisión de Juani
  (opción 1, `tasks.md:5`). Nada más del plan tocado; `## Estado del orquestador` sin tocar.
- Revisión: árbol de trabajo sin commit sobre `533a440` (el change está sin seguimiento en git).

## Cambios

### PR-13 · cobertura exacta acotada

- `tasks.md:192-197` (4.5): la propiedad universal pasa a llamarse **cobertura de lo cobrable**: la unión
  de lo cubierto por los intereses que cuentan es exactamente el conjunto de días entre el inicio natural
  y el corte que el oráculo, con la configuración de cada corte, asigna a un tramo con base positiva; los
  días de base cero quedan sin cubrir. El generador suma pagos parciales y totales; el pago total va
  también como `@example` fijo.
- `tasks.md:191-192`: **no solapamiento** queda como propiedad aparte, sin cambios de fondo.
- `tasks.md:201-202`: el mutante de control de cobertura por máximo apunta a la propiedad renombrada y
  al escenario fijo "Un hueco anterior se recupera..." de 4.4 (el hueco de $5.000,00 se conserva tal cual).
- `tasks.md:141-142` (4.1): escenario fijo nuevo "Detalle de un pago total"; `tasks.md:149-150`: mutante
  "estirar el último tramo con base positiva hasta el corte" → rojo por fechas.
- `specs/intereses-por-mora/spec.md:251-256`: escenario nuevo "Detalle de un pago total" bajo "Cada
  interés guarda su detalle por tramo": $100.000, vence 10/09/2026, gracia 0, 3% proporcional, pago
  total con fecha valor 20/09/2026 → $1.000,00, un solo tramo 11/09-20/09 sobre $100.000, ningún tramo
  21/09-30/09.
- `design.md` y el requisito de cobertura de la spec (`spec.md:86-92`) no afirmaban la cobertura
  exacta universal; no se tocaron.

### PR-14 · negativos discriminantes del CHECK de mes entero

- `tasks.md:95` (matriz de 2.1): un mutante por condición. Quitar sólo la de mismo mes → entra
  30/09-31/10 con `dias = 32`; quitar sólo la de fin de mes → entra 01/10-30/10. Ambos rechazados con
  el CHECK completo. 30/09-29/10 queda como negativo extra, declarado no discriminante.
- `design.md:239-241`: misma precisión junto a la fórmula del CHECK.

## EVIDENCIA

- `openspec validate intereses-saldo-inicial-y-moroso --strict` → `Change 'intereses-saldo-inicial-y-moroso' is valid` (2026-10-30T20:43:51-03:00).
- Recalculo con `Decimal` (python3, en este turno): suma diaria `base * 3 / 100 / 30` del 11/09 al
  30/09/2026, base $100.000 hasta el 20/09 y 0 después → `1000.00`, días con base positiva 11/09 a
  20/09 (10). `date(2026,10,31) - date(2026,9,30)` = 31 días → `dias = 32` para 30/09-31/10.
- Fórmula del CHECK evaluada a mano: 30/09-31/10 pasa `extract(day FROM hasta + 1) = 1` y falla
  `desde > hasta - 31` (30/09 > 30/09 falso); 01/10-30/10 falla fin de mes y pasa mismo mes
  (01/10 > 30/09).

## JUICIO

- Planner: las dos correcciones son precisiones de criterio de prueba, sin cambio de decisión
  financiera ni de código previsto. Confianza alta.

## SUPOSICIÓN

- La evaluación del CHECK no se corrió en PostgreSQL (no hay migración todavía); es análisis.
- Se asume que la base del día t descuenta imputaciones con fecha efectiva `< t` (design D2), igual
  que en "Pago parcial reduce la base"; de ahí que el 20/09 todavía devengue.

## Fuentes y contaminación

- Leídos: `informes/propose-3-plan-reviewer.md:59-69`, `tasks.md:85-205`, `design.md:144-195,230-242`,
  `specs/intereses-por-mora/spec.md:30-100,232-262`.
- Contaminación: el informe del revisor del intento 3 (es el insumo de esta corrección). `tasks.md`
  cambió en disco durante el turno por otra mano; no se revirtió.
