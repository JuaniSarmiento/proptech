## Purpose

Define la configuración de intereses por mora (R03) y de fondo de reserva (R15) de cada edificio como
menús cerrados versionados (D-010, D-080): cada cambio es una versión nueva con fecha de vigencia,
autor y fecha de alta, y ninguna versión anterior se modifica ni se borra.

## ADDED Requirements

### Requirement: Menú cerrado con los rangos de los parámetros

Una versión de configuración SHALL tener tasa mensual (texto decimal de 0.00 a 10.00, hasta 2
decimales), días de gracia (entero de 0 a 31), forma de cálculo (`proporcional_por_dia` o
`mes_entero`) y porcentaje de fondo de reserva (texto decimal de 0.00 a 100.00, hasta 2 decimales). El
interés MUST ser siempre simple: no hay opción para capitalizar ni fórmula libre. Un valor fuera de
rango, un número JSON en lugar de texto, `NaN`, `Infinity` o un campo desconocido MUST rechazarse con
422 nombrando el campo, sin repetir el valor.

#### Scenario: Tasa como número

- **WHEN** la tasa llega como `3.5` (número JSON)
- **THEN** la respuesta es 422 nombrando la tasa

#### Scenario: Tasa fuera de rango

- **WHEN** la tasa es "10.01" o "-1.00"
- **THEN** la respuesta es 422 nombrando la tasa y el rango

#### Scenario: Pedido de capitalización

- **WHEN** el cuerpo trae un campo de capitalización o de fórmula
- **THEN** la respuesta es 422 por campo desconocido

### Requirement: Cada cambio es una versión nueva y las anteriores no se tocan

Cambiar la configuración SHALL crear una versión nueva con su fecha de vigencia, la persona que la
creó y el momento de alta; la versión anterior MUST quedar igual. Ningún rol de la aplicación MUST
poder modificar ni borrar una versión: ni por la API ni por SQL como `proptech_app`. Sólo el titular
MUST poder crear una versión, y la creación MUST quedar auditada.

#### Scenario: Cambiar la tasa

- **WHEN** el titular crea una versión con tasa "4.00" vigente desde mañana
- **THEN** hay dos versiones, la de 3.00 sigue intacta, y la nueva tiene autor, fecha de alta y una
  fila de auditoría

#### Scenario: Editar una versión por SQL

- **WHEN** `proptech_app` intenta `UPDATE` o `DELETE` sobre una versión existente
- **THEN** la base lo rechaza y la versión sigue igual

#### Scenario: Un colaborador cambia la tasa

- **WHEN** un colaborador "editar" del edificio intenta crear una versión
- **THEN** la respuesta es 403 con el permiso faltante

### Requirement: Vigencias sin superposición ni retroactividad

Un edificio SHALL tener a lo sumo una versión por fecha de vigencia, y la base MUST impedir una
segunda aunque lleguen dos pedidos a la vez. Una versión nueva MUST tener vigencia desde la fecha de hoy
o posterior, en hora de Mendoza; una vigencia pasada MUST rechazarse con 422. La configuración vigente
para una fecha MUST ser la versión con la mayor fecha de vigencia que no supere esa fecha; antes de la
primera versión no hay configuración vigente.

#### Scenario: Dos versiones para el mismo día

- **WHEN** se crea una versión vigente desde una fecha que ya tiene versión
- **THEN** la respuesta es 409 y queda una sola versión para ese día

#### Scenario: Dos pedidos simultáneos

- **WHEN** dos pedidos crean a la vez una versión para la misma fecha del mismo edificio
- **THEN** uno se guarda y el otro recibe 409

#### Scenario: Versión retroactiva

- **WHEN** se crea una versión vigente desde ayer
- **THEN** la respuesta es 422 y no se guarda nada

#### Scenario: Vigente para una fecha

- **WHEN** hay versiones vigentes desde el 1/11 y el 1/12 y se pide la vigente para el 15/11
- **THEN** la respuesta es la del 1/11

#### Scenario: Fecha anterior a la primera versión

- **WHEN** se pide la configuración vigente para una fecha anterior a la creación del edificio
- **THEN** la respuesta dice que no hay configuración vigente para esa fecha
