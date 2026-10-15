## ADDED Requirements

### Requirement: Credenciales de la base por rol

Cada servicio SHALL recibir sólo las credenciales del rol que le toca: la API y el worker, las de
`proptech_app`; las migraciones, las de `proptech_migrador` y las del rol de arranque (sólo para crear
los roles); los respaldos, las del rol de arranque. La API y el worker MUST NOT recibir la contraseña
del rol de arranque ni la del migrador. Cada par de credenciales MUST validarse al arrancar (faltante,
vacío o en blanco) nombrando la variable sin mostrar su valor.

#### Scenario: La API conecta como la app

- **WHEN** el stack está levantado y la API consulta `current_user`
- **THEN** obtiene `proptech_app`, y el entorno de su contenedor no tiene la contraseña del rol de
  arranque

#### Scenario: Credencial de la app vacía

- **WHEN** `POSTGRES_APP_PASSWORD` está vacía o en blanco
- **THEN** la API y el worker no arrancan y el error nombra la variable sin mostrar ningún valor

### Requirement: La web no alcanza la base

La web SHALL estar en una red sin acceso a PostgreSQL ni a Redis; sólo la API, el worker, las
migraciones y los respaldos alcanzan la base.

#### Scenario: La web intenta conectar a la base

- **WHEN** desde el contenedor de la web se intenta abrir una conexión a `db:5432`
- **THEN** la conexión no se establece

### Requirement: Cabeceras de seguridad en el proxy

Toda respuesta servida por el proxy SHALL llevar `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` y `Permissions-Policy` restrictiva, y MUST NOT
llevar `Server`, `Via` ni `X-Powered-By`. Una respuesta a HEAD MUST llevar las mismas cabeceras que la
respuesta a GET y ningún cuerpo.

#### Scenario: Respuesta de la web y de la API

- **WHEN** se pide `/` y `/api/salud` a través del proxy, con GET y con HEAD
- **THEN** las cuatro respuestas traen las cabeceras de seguridad y ninguna trae `Server`, `Via` ni
  `X-Powered-By`, y las de HEAD no traen cuerpo

### Requirement: Contenedores endurecidos

Ningún servicio SHALL poder ganar privilegios nuevos (`no-new-privileges`) y cada uno MUST correr con
sólo las capacidades del kernel que necesita. El PID 1 de la API, el worker, la web, las migraciones y
los respaldos MUST no ser root, verificado en cada servicio. Los datos de Caddy (certificados y
configuración) MUST persistir en volúmenes propios.

#### Scenario: PID 1 de cada servicio

- **WHEN** se lee el usuario del PID 1 en la API, el worker, la web, las migraciones y los respaldos
- **THEN** ninguno es root, y el chequeo da rojo en cada servicio si se lo configura como root

#### Scenario: Caddy reinicia sin perder certificados

- **WHEN** se recrea el contenedor de Caddy
- **THEN** sus datos siguen en el volumen
