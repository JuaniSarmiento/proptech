# Spec Delta

## Purpose

Revertir un pago confirmado que el banco devuelve y reimputar uno confirmado en la unidad equivocada, sin
borrar nada, con el interés de los días ya cobrados bien calculado (R18, R25, R20, P29, D-083, D-163, E8 a
E10).

## ADDED Requirements

### Requirement: Revertir un pago confirmado

`POST .../pagos/{id}/reversion` SHALL exigir motivo y un pago `confirmado` (si no, 409 `motivo` `estado`), y
registrar por cada parte un `reversion_de_pago` con `corrige_a` el movimiento vigente de la parte, revertir
sus ajustes enlazados y dejar el evento `revertido`, auditado, en una transacción. El pago original sigue
visible con su estado nuevo. Requiere `revertir_o_reimputar_pago`.

#### Scenario: Cheque rechazado

- **WHEN** se revierte un pago confirmado de $43.350,00 de `1A` con "cheque rechazado"
- **THEN** la deuda de `1A` vuelve a la de antes del pago y el pago se ve `revertido`

#### Scenario: Revertir pasa a moroso crítico

- **WHEN** después de revertir, `1A` tiene dos liquidaciones vencidas con capital impago
- **THEN** `situacion_de_cuenta` la da como moroso crítico

#### Scenario: Revertir uno no confirmado

- **WHEN** el pago está `informado` o `rechazado`
- **THEN** responde 409 y no se registra nada

### Requirement: El interés corre desde el vencimiento original (P29)

Al sacar un pago de una unidad (por reversión o reimputación), cada interés que cuenta y que se calculó con
ese pago adentro SHALL recalcularse sin él sobre sus mismos tramos, y la diferencia se registra como
`interes_por_reversion` (débito, componente interés, `enlazado_a` ese interés). Sigue siendo interés
simple: no genera interés.

#### Scenario: Revertir después de una emisión

- **WHEN** el pago de `1A` del 05/11 se confirmó el 05/11, la emisión de diciembre cobró interés con el pago
  adentro, y el 10/12 se revierte
- **THEN** se registra `interes_por_reversion` por la diferencia, y el interés de `1A` queda igual al de una
  cuenta que nunca recibió ese pago

### Requirement: Reimputar entre dos unidades en una sola transacción

`POST .../pagos/{id}/reimputacion` con `desde_unidad_id`, `hacia_unidad_id` y motivo SHALL mover esa parte en
una transacción: en la de origen, un `reimputacion` débito con `corrige_a` el movimiento vigente, la
reversión de sus ajustes y el interés de la reversión; en la de destino, un `reimputacion` crédito con la
fecha de la transferencia, imputado con R04 a esa fecha, con su ajuste, y `enlazado_a` el débito. Si falla
un paso no queda ninguno. La misma unidad: 422; una de otro edificio: 404.

#### Scenario: De 7B a 7A

- **WHEN** el pago de $43.350,00 confirmado en `1B` se reimputa a `1A`
- **THEN** `1B` vuelve a deber lo de antes, `1A` queda con el pago imputado con su fecha de transferencia, y
  `situacion_de_cuenta` da bien a las dos

#### Scenario: Falla a mitad de camino

- **WHEN** el paso de la unidad de destino falla
- **THEN** ninguna de las dos cuentas tiene un movimiento nuevo
