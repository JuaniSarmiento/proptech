## ADDED Requirements

### Requirement: Cabeceras de seguridad en el proxy

Toda respuesta servida por el proxy SHALL llevar `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` y una `Permissions-Policy` restrictiva, y MUST
NOT llevar `Server`, `Via` ni `X-Powered-By`, venga de Caddy, de la web o de la API. Una respuesta a HEAD
MUST llevar las mismas cabeceras que la respuesta a GET y ningún cuerpo.

#### Scenario: Respuesta de la web y de la API

- **WHEN** se pide `/` y `/api/salud` a través del proxy, con GET y con HEAD
- **THEN** las cuatro respuestas traen las cabeceras de seguridad, ninguna trae `Server`, `Via` ni
  `X-Powered-By`, y las de HEAD no traen cuerpo

#### Scenario: Respuesta de error de la API

- **WHEN** se pide por el proxy una ruta de la API que no existe
- **THEN** el 404 trae las mismas cabeceras de seguridad

### Requirement: Contenedores endurecidos

Ningún servicio SHALL poder ganar privilegios nuevos (`no-new-privileges`) y cada uno MUST correr con
sólo las capacidades del kernel que necesita, cada una justificada. El PID 1 de la API, el worker, la
web, las migraciones y los respaldos MUST no ser root, verificado en cada servicio. Los datos de Caddy
MUST persistir en volúmenes propios.

#### Scenario: PID 1 de cada servicio

- **WHEN** se lee el usuario del PID 1 en la API, el worker, la web, las migraciones y los respaldos
- **THEN** ninguno es root, y el chequeo da rojo en cada servicio si se lo configura como root

#### Scenario: Privilegios y capacidades

- **WHEN** se inspecciona la configuración de cada servicio
- **THEN** todos tienen `no-new-privileges`, todos descartan todas las capacidades, y sólo `db`, `redis`
  y `caddy` vuelven a agregar las de su lista justificada

#### Scenario: Caddy reinicia sin perder certificados

- **WHEN** se recrea el contenedor de Caddy
- **THEN** sus datos siguen en el volumen
