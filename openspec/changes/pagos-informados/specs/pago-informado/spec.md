# Spec Delta

## Purpose

El vecino (o el personal por él) informa un pago con su comprobante: banco, número de operación, fecha de
la transferencia, monto y a qué unidades corresponde. Informar no cambia la deuda (R11, R10, D-163, E2 a E4).

## ADDED Requirements

### Requirement: Informar un pago no cambia la deuda

`POST /api/complejos/{id}/pagos` SHALL crear un pago `informado` con su comprobante y sus partes, sin
escribir ningún movimiento en el libro, y responder 201 con el `pago_id` y el estado.

#### Scenario: Pago informado

- **WHEN** el propietario de `1A` informa $43.350,00 con fecha 05/11/2026 para `1A`
- **THEN** responde 201 con estado `informado` y la deuda de `1A` y su `situacion_de_cuenta` no cambian

### Requirement: El número de operación es único por edificio y banco

Entre los pagos no rechazados de un edificio, la combinación de banco y número de operación normalizados
(sin espacios, guiones ni puntos, en minúscula, sin tildes) MUST ser única; la repetida da 409 con `campo`
`numero_de_operacion` y `motivo` `repetido`.

#### Scenario: El mismo comprobante dos veces

- **WHEN** se informa un pago con banco `Banco Nación` y número `12-345.678`, y después otro con `banco
  nacion` y `12345678`
- **THEN** el segundo da 409 `repetido`, también si es para otra unidad

#### Scenario: Otro banco con el mismo número

- **WHEN** el segundo pago es de `Mercado Pago` con el número `12345678`
- **THEN** se informa (201)

#### Scenario: Un rechazado libera su número

- **WHEN** el primer pago se rechazó
- **THEN** el mismo banco y número se pueden informar de nuevo

### Requirement: Sólo para unidades propias, con partes que suman el monto

El vecino SHALL informar sólo para unidades del edificio donde tiene asignación de vecino (propietario o
inquilino); otra unidad da 404. Con varias unidades, una parte por unidad, sin repetir, que suman el
monto. El personal con `confirmar_pago_informado` puede informar por cualquier unidad del edificio. Sin
`informar_pago` ni `confirmar_pago_informado`, 403.

#### Scenario: Reparto entre departamento y cochera

- **WHEN** la persona es propietaria de `1A` y de `C1` e informa $50.000,00 repartido en $40.000,00 y
  $10.000,00
- **THEN** el pago queda con dos partes

#### Scenario: Una unidad ajena

- **WHEN** el propietario de `1A` informa un pago para `1B`
- **THEN** responde 404 y no se crea nada

#### Scenario: Partes que no suman

- **WHEN** las partes suman $49.999,99 y el monto es $50.000,00
- **THEN** responde 422 con `campo` `partes`

### Requirement: Los datos del pago se validan

El monto MUST ser mayor que cero con dos decimales; la fecha de la transferencia no futura ni anterior a
un año; banco y número no vacíos; el comprobante del mismo edificio, subido por quien informa (o por el
personal) y no usado por otro pago. Cada falla da 422 con su campo.

#### Scenario: Fecha futura

- **WHEN** la fecha de la transferencia es mañana
- **THEN** responde 422 con `campo` `fecha_de_transferencia`

### Requirement: Cada uno ve sólo sus pagos

El vecino SHALL ver los pagos con alguna parte en sus unidades, con su estado y el motivo de un rechazo; el
personal con `confirmar_pago_informado` ve los del edificio. Un pago de otra unidad u otra administración
da 404.

#### Scenario: El vecino ve el estado

- **WHEN** el propietario de `1A` lista sus pagos
- **THEN** ve los de `1A` con estado `informado`, `confirmado`, `rechazado` (con su motivo) o `revertido`,
  y ninguno de `1B`
