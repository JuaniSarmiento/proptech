## ADDED Requirements

### Requirement: El humo verifica el candado en el stack vivo

La prueba de humo SHALL verificar en el stack levantado que la API y el worker conectan como un rol sin
superusuario ni `BYPASSRLS`, que la web no alcanza la base, y que un backup restaurado trae las dos
administraciones sembradas con sus políticas.

#### Scenario: Rol de la app en el stack vivo

- **WHEN** el humo consulta el rol con el que conectan la API y el worker
- **THEN** es `proptech_app`, sin superusuario ni `BYPASSRLS`

#### Scenario: Backup completo en el humo

- **WHEN** el humo siembra dos administraciones, espera un backup y lo restaura en
  `proptech_restauracion`
- **THEN** cuenta los complejos de cada administración en la base restaurada y coinciden con los
  sembrados
