## ADDED Requirements

### Requirement: Acciones de configuración auditadas

Crear un edificio, crear una versión de configuración de intereses y fondo de reserva, y confirmar
"sin saldos previos" SHALL registrarse en la auditoría, en la misma transacción que la acción, con su
acción del vocabulario cerrado (sumada por migración) y un detalle con claves permitidas: el id del
edificio y, para una versión, su fecha de vigencia. El detalle MUST NOT contener los valores de la
tasa ni del porcentaje. Si la acción se revierte, MUST NOT quedar su fila de auditoría.

#### Scenario: Crear un edificio queda auditado

- **WHEN** el titular crea un edificio
- **THEN** hay una fila de auditoría con la acción de crear edificio, el id del edificio, la persona y
  el `request_id`

#### Scenario: La versión que falla no deja auditoría

- **WHEN** la creación de una versión de configuración falla por la fecha repetida
- **THEN** no queda ninguna fila de auditoría de esa acción

#### Scenario: El detalle no trae la tasa

- **WHEN** se registra la creación de una versión con tasa "4.00"
- **THEN** el detalle tiene sólo el id del edificio y la fecha de vigencia
