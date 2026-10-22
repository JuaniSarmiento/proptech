# auditoria-de-acciones Specification

## Purpose
Registra cada acción sensible con quién la hizo, sobre qué y cuándo, en la misma transacción que la
acción, de forma que no se pueda saltear, editar ni borrar (D-016).

## Requirements

### Requirement: La acción y su registro se confirman juntos

Cada acción sensible SHALL dejar exactamente una fila de auditoría en la misma transacción que la
acción: si la acción se revierte, la fila no queda; si la fila no se puede escribir, la acción se
revierte. La fila MUST llevar la administración, la persona que actuó, la acción, la entidad afectada,
el `request_id` del pedido y la marca de tiempo de la base.

#### Scenario: Acción confirmada

- **WHEN** el titular asigna un edificio
- **THEN** queda exactamente una fila de auditoría con su persona, la acción
  `invitar_usuarios_y_asignar_edificios`, el complejo y el `request_id` del pedido

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

La acción SHALL ser una de una lista cerrada, formada por los permisos de la matriz de D-106 más los
eventos de acceso que no son permisos (`ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`,
`invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion`,
`quitar_asignacion`), controlada también por la base: sumar una acción o un evento exige una migración.
El detalle MUST aceptar sólo las claves permitidas para esa acción y MUST NOT contener contraseñas,
tokens, emails, ids de Clerk en claro ni el texto de un error de terceros. Un mismo caso de uso sensible
MUST registrarse con una sola acción y una acción MUST NOT quedar registrada por dos casos de uso que se
pisen sin que la suite lo note.

#### Scenario: Acción fuera de la lista

- **WHEN** se intenta registrar una acción que no está en la lista
- **THEN** la base la rechaza

#### Scenario: Clave no permitida en el detalle

- **WHEN** el detalle trae una clave fuera de las permitidas para esa acción
- **THEN** el registro se rechaza antes de escribir, sin repetir el valor en el error

#### Scenario: Evento de acceso

- **WHEN** se registra `ingreso_exitoso` con el detalle permitido
- **THEN** la base lo acepta, y el detalle no tiene email, token ni id de Clerk

#### Scenario: Dos casos de uso con la misma acción

- **WHEN** dos casos de uso distintos se marcan como sensibles con la misma acción
- **THEN** la suite falla nombrando la acción y los dos casos de uso

### Requirement: La auditoría sólo se agrega

Ningún rol de la aplicación SHALL poder modificar, borrar ni vaciar filas de auditoría, ni desactivar
lo que lo impide: ni `proptech_app` ni `proptech_migrador`. La tabla MUST pertenecer al rol de arranque,
de modo que el migrador no sea su dueño. Incluso el dueño MUST ver rechazados `UPDATE`, `DELETE` y
`TRUNCATE` mientras el bloqueo esté activo; el único que puede desactivarlo es el superusuario de
arranque, que ningún servicio permanente tiene. Cada administración MUST ver sólo su propia auditoría.

#### Scenario: Editar o borrar como la app

- **WHEN** `proptech_app` intenta `UPDATE`, `DELETE` o `TRUNCATE` sobre la auditoría
- **THEN** la base lo rechaza y las filas siguen iguales

#### Scenario: Editar, borrar o desactivar el bloqueo como el migrador

- **WHEN** `proptech_migrador` intenta `UPDATE`, `DELETE`, `TRUNCATE`, `ALTER TABLE ... DISABLE
  TRIGGER` o `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` sobre la auditoría
- **THEN** la base lo rechaza por no ser dueño ni tener el permiso, y las filas y el bloqueo siguen
  iguales

#### Scenario: Editar o borrar como el dueño

- **WHEN** el rol de arranque, dueño de la tabla, intenta `UPDATE`, `DELETE` o `TRUNCATE` sin
  desactivar antes el bloqueo
- **THEN** la base lo rechaza y las filas siguen iguales

#### Scenario: Dueño de la tabla después de las migraciones

- **WHEN** termina el arranque del stack
- **THEN** el dueño de la auditoría es el rol de arranque, no `proptech_migrador`

#### Scenario: Auditoría de otra administración

- **WHEN** con el tenant de A se lee la auditoría
- **THEN** no aparece ninguna fila de B

### Requirement: Acciones de configuración auditadas

Crear un edificio, crear una versión de configuración de intereses, vencimiento y fondo de reserva, y
confirmar "sin saldos previos" SHALL registrarse en la auditoría, en la misma transacción que la
acción, con su acción del vocabulario cerrado (sumada por migración) y un detalle con claves
permitidas: el id del edificio y, para una versión, su fecha de vigencia. El detalle MUST NOT contener
los valores de la tasa, del porcentaje ni del recargo. Si la acción se revierte, MUST NOT quedar su
fila de auditoría.

#### Scenario: Crear un edificio queda auditado

- **WHEN** el titular crea un edificio
- **THEN** hay una fila de auditoría con la acción de crear edificio, el id del edificio, la persona y
  el `request_id`

#### Scenario: La versión que falla no deja auditoría

- **WHEN** la creación de una versión de configuración falla por la fecha repetida
- **THEN** no queda ninguna fila de auditoría de esa acción

#### Scenario: El detalle no trae la tasa

- **WHEN** se registra la creación de una versión con tasa "4.00" y recargo del segundo vencimiento
  "5.00"
- **THEN** el detalle tiene sólo el id del edificio y la fecha de vigencia
