## ADDED Requirements

### Requirement: El backup trae todas las administraciones sin ser superusuario

El servicio de respaldos SHALL volcar la base con `proptech_respaldo`, un rol sin superusuario al que
Row-Level Security no le filtra filas y que puede leer todas las tablas, de modo que el backup tenga los
datos de todas las administraciones. MUST NOT usar las credenciales del rol de arranque, de
`proptech_app` ni de `proptech_migrador`, y ningún volcado MUST usar `--enable-row-security`, que con
un rol filtrado produce un backup vacío sin error.

#### Scenario: Backup con dos administraciones

- **WHEN** la base tiene complejos de dos administraciones, se genera un backup y se restaura en una
  base aparte
- **THEN** la base restaurada tiene los complejos de las dos, en la misma cantidad que la original, y
  conserva la RLS forzada y las políticas de cada tabla

#### Scenario: Volcado con el rol equivocado

- **WHEN** el servicio de respaldos se configura con las credenciales de `proptech_app`
- **THEN** el volcado falla, no queda ningún `.dump` nuevo y el servicio queda no saludable

#### Scenario: Credenciales y opciones del servicio

- **WHEN** se inspecciona la configuración del servicio de respaldos y sus scripts
- **THEN** su usuario es `proptech_respaldo`, no tiene la contraseña del rol de arranque y ningún
  script usa `--enable-row-security`
