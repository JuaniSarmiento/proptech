# Spec Delta

## ADDED Requirements

### Requirement: La corrección de un movimiento queda auditada

Toda corrección SHALL registrar en la auditoría la acción `corregir_movimiento` en la misma transacción
que el movimiento de corrección, con el edificio, el id de lo corregido y la forma de la corrección,
nunca el motivo ni el importe. Si la auditoría falla, la corrección MUST no quedar escrita.

#### Scenario: Corrección auditada

- **WHEN** el super admin registra un contra-asiento
- **THEN** existe una fila de auditoría `corregir_movimiento` con el id del movimiento de corrección como
  entidad, y su detalle no contiene el motivo ni el importe

#### Scenario: Falla la auditoría

- **WHEN** el AP pide una corrección por la API real y el registro de auditoría falla
- **THEN** la API no confirma: otra conexión comprueba que ni la corrección ni sus imputaciones quedaron en el libro

#### Scenario: El vocabulario nuevo

- **WHEN** el ensayo del consumidor invoca la operación y se lista `accion_de_auditoria` después de `0024`
- **THEN** contiene `corregir_movimiento`, y bajar `0024` con una corrección auditada falla con `23503`

### Requirement: Emitir y anular se auditan en el llamador

El libro SHALL ser la autoridad del estado anulada para el saldo. El llamador del 7 MUST derivar la anulación del libro y auditar emisión y anulación en la misma transacción con sus acciones existentes; el libro no duplica esas auditorías. El estado distribuida pertenece al 7.

#### Scenario: Anulación y auditoría del llamador

- **WHEN** el llamador del 7 anula una liquidación mediante `anular_emision`
- **THEN** registra en la misma transacción el evento del libro y la auditoría `ANULAR_LIQUIDACION`; la lectura del estado anulada del 7 coincide con el libro
