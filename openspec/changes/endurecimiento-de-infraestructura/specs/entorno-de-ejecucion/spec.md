## ADDED Requirements

### Requirement: Cabeceras de seguridad en el proxy

Toda respuesta servida por el proxy SHALL llevar `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` y una `Permissions-Policy` restrictiva, y MUST
NOT llevar `Server`, `Via` ni `X-Powered-By`, venga de la web, de la API o del propio Caddy (incluidas
las respuestas de error que genera Caddy cuando un servicio de atrás no responde), **y sin importar si
el pedido matchea el sitio configurado** (`{$PROPTECH_SITIO}`): por IP, con un `Host` que no sea ese, o
sin `Host` (HTTP/1.0), el proxy SHALL servir esta misma respuesta en vez de la respuesta por defecto de
Caddy (C2-2, vuelta 2 del 2c). Una respuesta a HEAD MUST llevar las mismas cabeceras que la respuesta a
GET.

**Excepción, acotada:** lo que el servidor HTTP arma ANTES de elegir un sitio — una línea de pedido
malformada (400), un encabezado demasiado grande (431), una versión de HTTP no soportada (505) o un
`OPTIONS *` — no pasa por ningún sitio (ni el real ni el de respaldo) y sale sin estas cabeceras; es
inherente al servidor HTTP de Go que usa Caddy, no una falla de configuración (N1, rompedor vuelta 1).

#### Scenario: Respuesta de la web y de la API

- **WHEN** se pide `/` y `/api/salud` a través del proxy, con GET y con HEAD
- **THEN** las cuatro respuestas traen las cabeceras de seguridad, ninguna trae `Server`, `Via` ni
  `X-Powered-By`, y cada HEAD trae las mismas cabeceras de seguridad que su GET

#### Scenario: Respuesta de error de la API

- **WHEN** se pide por el proxy una ruta de la API que no existe
- **THEN** el 404 trae las mismas cabeceras de seguridad y ninguna de `Server`, `Via` ni `X-Powered-By`

#### Scenario: Error del proxy

- **WHEN** el servicio `api` está detenido y se pide `GET /api/salud` por el proxy
- **THEN** la respuesta es 502, trae las cabeceras de seguridad y no trae `Server`

#### Scenario: Pedido que no matchea el sitio configurado

- **WHEN** se pide por IP, con un `Host` que no es `{$PROPTECH_SITIO}`, o sin `Host` (HTTP/1.0)
- **THEN** la respuesta trae las cabeceras de seguridad y no trae `Server`, `Via` ni `X-Powered-By`
  (nunca la respuesta por defecto de Caddy)

### Requirement: Contenedores endurecidos

Ningún servicio SHALL poder ganar privilegios nuevos (`no-new-privileges`) y cada uno MUST correr con
sólo las capacidades del kernel que necesita, cada una justificada, verificado en el proceso que corre
y no sólo en la configuración. Los datos de Caddy MUST persistir en volúmenes propios.

Para un servicio cuyo entrypoint baja privilegios por su cuenta después de que el contenedor arranca
(hoy `redis`, con `setpriv`; mañana puede ser otro), el PID 1 MUST NOT ser la fuente de este chequeo:
su `CapBnd` puede quedar vacío sin importar qué haya puesto Compose, así que un `cap_drop` sacado
pasaría igual (C2-3, rompedor/auditor, vuelta 1 del 2c). El chequeo SHALL leer un proceso nuevo
(`compose exec`/`run`), que siempre refleja lo que Compose configuró.

#### Scenario: Privilegios y capacidades en el stack vivo

- **WHEN** con el stack levantado se lee `/proc/self/status` de un proceso nuevo en cada uno de los
  ocho servicios (`compose exec`, o `compose run --no-deps` en `migraciones`, que ya terminó)
- **THEN** todos traen `NoNewPrivs: 1`, el `CapBnd` de cada uno es exactamente su lista justificada
  (vacía salvo en `db`, `redis` y `caddy`), y el chequeo da rojo si una copia de Compose le saca el
  `cap_drop`/`security_opt` a cualquiera de los ocho, incluido `redis`

#### Scenario: Caddy recreado conserva sus datos

- **WHEN** se lee `/data/caddy/instance.uuid` de Caddy, se lo recrea con
  `docker compose -p proptech up -d --force-recreate caddy` y se lo lee de nuevo
- **THEN** el valor es el mismo, y con una copia de Compose sin el volumen de `/data` cambia

### Requirement: La causa de un arranque rechazado queda en el log

Cuando la API o el worker se niegan a arrancar por la configuración o por el rol con el que conectan a
la base, el log del contenedor SHALL tener una línea JSON con un evento propio de arranque fallido y la
causa nombrada (la variable que falta, o qué atributo del rol es inseguro), y MUST NOT incluir ningún
valor secreto. El servicio MUST seguir sin arrancar.

#### Scenario: Arranque rechazado con causa nombrada

- **WHEN** una copia de Compose hace que `api` conecte con el rol de arranque (superusuario) y se mira
  `docker compose -p proptech logs api`
- **THEN** el contenedor no arranca, el log tiene la línea del arranque fallido con la causa, y ninguna
  contraseña aparece en el log; lo mismo para `worker`

## MODIFIED Requirements

### Requirement: Contenedores sin privilegios de root

Los procesos de la API, la web, el worker, las migraciones, los respaldos, Redis y PostgreSQL SHALL
correr dentro de sus contenedores con un usuario sin privilegios de root, verificado sobre el PID 1 de
cada servicio (en Redis y PostgreSQL, el proceso que queda después de bajar de usuario). Caddy MUST ser
el único servicio que corre como root, declarado y sin capacidades salvo `NET_BIND_SERVICE`.

#### Scenario: Usuario del proceso

- **WHEN** se lee el usuario del PID 1 en `/proc/1/status` de los contenedores de la API, la web, el
  worker, las migraciones, los respaldos, Redis y PostgreSQL
- **THEN** ninguno es root (uid distinto de 0)

#### Scenario: Un servicio configurado como root

- **WHEN** una copia de Compose hace correr como root cualquiera de esos siete servicios (`user: "0:0"`;
  en `db` y `redis`, además, con el entrypoint salteado para que no baje de usuario con `gosu`) y se
  corre el chequeo
- **THEN** el chequeo da rojo nombrando ese servicio, para cada uno de los siete
