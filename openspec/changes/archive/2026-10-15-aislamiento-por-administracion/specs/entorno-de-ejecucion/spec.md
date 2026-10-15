## ADDED Requirements

### Requirement: Credenciales de la base por rol

Cada servicio SHALL recibir sólo las credenciales del rol que le toca: la API y el worker, las de
`proptech_app`; las migraciones, las de `proptech_migrador` y las del rol de arranque (sólo para crear
y reparar los roles, en un servicio de una sola corrida); los respaldos, las de `proptech_respaldo`.
Ningún servicio permanente MUST recibir la contraseña del rol de arranque, y la API y el worker MUST
NOT recibir la del migrador ni la de respaldo. Cada par de credenciales MUST validarse al arrancar (faltante,
vacío o en blanco) nombrando la variable sin mostrar su valor.

#### Scenario: La API conecta como la app

- **WHEN** el stack está levantado y la API consulta `current_user`
- **THEN** obtiene `proptech_app`, y el entorno de su contenedor no tiene la contraseña del rol de
  arranque, ni la del migrador, ni la de respaldo

#### Scenario: Credencial de la app vacía

- **WHEN** `POSTGRES_APP_PASSWORD` está vacía o en blanco
- **THEN** la API y el worker no arrancan y el error nombra la variable sin mostrar ningún valor

### Requirement: La web no alcanza la base

La web SHALL estar en una red sin acceso a PostgreSQL ni a Redis; sólo la API, el worker, las
migraciones y los respaldos alcanzan la base.

#### Scenario: La web intenta conectar a la base

- **WHEN** desde el contenedor de la web se intenta abrir una conexión a `db:5432`
- **THEN** la conexión no se establece
