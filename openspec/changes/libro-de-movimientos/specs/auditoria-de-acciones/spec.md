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

- **WHEN** el registro en la auditoría falla durante una corrección
- **THEN** ni la corrección ni sus imputaciones quedan en el libro

#### Scenario: El vocabulario nuevo

- **WHEN** se lista `accion_de_auditoria` después de `0024`
- **THEN** contiene `corregir_movimiento`, y bajar `0024` con una corrección auditada falla con `23503`
