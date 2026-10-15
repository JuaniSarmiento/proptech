## Purpose

Registra cada acción sensible con quién la hizo, sobre qué y cuándo, en la misma transacción que la
acción, de forma que no se pueda saltear, editar ni borrar (D-016).

## ADDED Requirements

### Requirement: La acción y su registro se confirman juntos

Cada acción sensible SHALL dejar exactamente una fila de auditoría en la misma transacción que la
acción: si la acción se revierte, la fila no queda; si la fila no se puede escribir, la acción se
revierte. La fila MUST llevar la administración, la persona que actuó, la acción, la entidad afectada,
el `request_id` del pedido y la marca de tiempo de la base.

#### Scenario: Acción confirmada

- **WHEN** el titular asigna un edificio
- **THEN** queda exactamente una fila de auditoría con su persona, la acción
  `asignar_edificio`, el complejo y el `request_id` del pedido

#### Scenario: Acción revertida

- **WHEN** la acción falla después de haber escrito su fila de auditoría
- **THEN** no queda ni la acción ni la fila

#### Scenario: Registro que no se puede escribir

- **WHEN** la fila de auditoría es rechazada por la base
- **THEN** la acción tampoco queda

#### Scenario: Toda acción sensible registrada

- **WHEN** se ejecuta cada caso de uso marcado como sensible
- **THEN** cada uno deja exactamente una fila, y un caso de uso sensible sin registro hace fallar la
  suite

### Requirement: Vocabulario cerrado y detalle sin datos sensibles

La acción SHALL ser una de una lista cerrada, controlada también por la base. El detalle MUST aceptar
sólo las claves permitidas para esa acción y MUST NOT contener contraseñas, tokens, emails ni el texto
de un error de terceros.

#### Scenario: Acción fuera de la lista

- **WHEN** se intenta registrar una acción que no está en la lista
- **THEN** la base la rechaza

#### Scenario: Clave no permitida en el detalle

- **WHEN** el detalle trae una clave fuera de las permitidas para esa acción
- **THEN** el registro se rechaza antes de escribir, sin repetir el valor en el error

### Requirement: La auditoría sólo se agrega

Nadie SHALL poder modificar, borrar ni vaciar filas de auditoría: ni `proptech_app` ni el dueño de la
tabla. Cada administración MUST ver sólo su propia auditoría.

#### Scenario: Editar o borrar como la app

- **WHEN** `proptech_app` intenta `UPDATE`, `DELETE` o `TRUNCATE` sobre la auditoría
- **THEN** la base lo rechaza y las filas siguen iguales

#### Scenario: Editar o borrar como el dueño

- **WHEN** `proptech_migrador` intenta `UPDATE`, `DELETE` o `TRUNCATE` sobre la auditoría
- **THEN** la base lo rechaza y las filas siguen iguales

#### Scenario: Auditoría de otra administración

- **WHEN** con el tenant de A se lee la auditoría
- **THEN** no aparece ninguna fila de B
