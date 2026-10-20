## MODIFIED Requirements

### Requirement: Cada cambio es una versión nueva y las anteriores no se tocan

Cambiar la configuración SHALL crear una versión nueva con su fecha de vigencia, la persona que la
creó y el momento de alta; la versión anterior MUST quedar igual. Ningún rol de la aplicación MUST
poder modificar ni borrar una versión: ni por la API ni por SQL como `proptech_app`, tampoco después
de que el sistema vuelva a arrancar y el paso de roles corra otra vez. Sólo el super admin y los
administradores con alcance sobre el edificio (principal o por ese edificio) MUST poder crear una
versión (E3 de `roles-de-la-empresa`), y la creación MUST quedar auditada.

#### Scenario: Cambiar la tasa

- **WHEN** el super admin crea una versión con tasa "4.00" vigente desde mañana
- **THEN** hay dos versiones, la de 3.00 sigue intacta, y la nueva tiene autor, fecha de alta y una
  fila de auditoría

#### Scenario: Un administrador del edificio cambia la tasa

- **WHEN** un administrador por edificio crea una versión en su edificio
- **THEN** la versión queda creada, con él como autor y una fila de auditoría

#### Scenario: Editar una versión por SQL

- **WHEN** `proptech_app` intenta `UPDATE` o `DELETE` sobre una versión existente
- **THEN** la base lo rechaza y la versión sigue igual

#### Scenario: Editar una versión después de otro arranque

- **WHEN** el paso de roles y las migraciones corrieron dos veces seguidas y, con el trigger de la
  tabla deshabilitado sobre una copia, `proptech_app` intenta `UPDATE` o `DELETE` sobre una versión
- **THEN** la base lo rechaza por permisos y la versión sigue igual

#### Scenario: Un colaborador cambia la tasa

- **WHEN** un auxiliar del edificio (antes, colaborador "ver"), o un contador con cualquier alcance, intenta crear una versión
- **THEN** la respuesta es 403 con el permiso faltante
