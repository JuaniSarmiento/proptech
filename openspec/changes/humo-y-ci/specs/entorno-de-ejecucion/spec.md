## ADDED Requirements

### Requirement: El sitio de respaldo del proxy responde 421 y lo dice un test

Un pedido que no matchea el sitio configurado (por IP, con un `Host` ajeno o sin `Host`) en el puerto
80 SHALL recibir `421` con cuerpo vacío para GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS y TRACE, con
las cuatro cabeceras de seguridad y sin `Server`, `Via` ni `X-Powered-By`.

#### Scenario: Ocho métodos

- **WHEN** se pide `/` con cada uno de los ocho métodos a un `Host` ajeno, con el stack levantado
- **THEN** las ocho respuestas son `421`, vacías y con las cabeceras de seguridad

#### Scenario: El respaldo cambia de código

- **WHEN** el `Caddyfile` del sitio de respaldo pasa a responder otro código
- **THEN** el humo y un test estático dan rojo nombrando el código esperado

### Requirement: Qué cubre y qué no el proxy con un sitio https está declarado

Con `PROPTECH_SITIO=https://...`, el estado actual del proxy (sin bloque propio para el puerto 443
fuera del sitio configurado, sin HSTS, redirección `308` de http a https generada por Caddy sin las
cabeceras de seguridad) SHALL estar escrito en el spec y fijado por un test estático del `Caddyfile`,
de modo que un cambio en esa conducta sin actualizar la declaración dé rojo. Cerrar esa brecha (HSTS y
respaldo del 443) MUST quedar para el cambio que pone el dominio real.

#### Scenario: El Caddyfile cambia sin declararlo

- **WHEN** se agrega un bloque `:443` o una directiva `Strict-Transport-Security` al `Caddyfile` sin
  actualizar la declaración
- **THEN** el test estático da rojo diciendo que la declaración quedó vieja

#### Scenario: La declaración existe

- **WHEN** se lee el spec `entorno-de-ejecucion`
- **THEN** nombra la 308 y el 443 con un `Host` ajeno como brechas conocidas, con su dueño

### Requirement: El proxy no cuelga si un servicio de atrás no responde

El proxy SHALL cortar con 502 o 504 a un pedido cuyo servicio de atrás no responde dentro de un plazo
configurado en el `Caddyfile` (conexión y respuesta), con las cabeceras de seguridad, y MUST NOT dejar
al cliente esperando más de ese plazo más un margen de 5 segundos.

#### Scenario: `api` pausada

- **WHEN** el servicio `api` está pausado (no detenido) y se pide `GET /api/salud` por el proxy
- **THEN** la respuesta llega como 502 o 504 dentro del plazo configurado más 5 segundos, con las
  cabeceras de seguridad y sin `Server`

#### Scenario: `web` pausada

- **WHEN** el servicio `web` está pausado y se pide `/`
- **THEN** ocurre lo mismo que con `api`

## MODIFIED Requirements

### Requirement: La causa de un arranque rechazado queda en el log

Cuando la API o el worker se niegan a arrancar por la configuración, por el rol con el que conectan a
la base, **porque la base no es alcanzable o porque el archivo de parámetros no se puede leer o está mal
formado**, el log del contenedor SHALL tener una línea JSON con un evento propio de arranque fallido y
la causa nombrada (la variable que falta, qué atributo del rol es inseguro, que la base no responde, o
qué campo del archivo de parámetros es inválido), y MUST NOT incluir ningún valor secreto ni la cadena de
conexión. El servicio MUST seguir sin arrancar.

#### Scenario: Arranque rechazado con causa nombrada

- **WHEN** una copia de Compose hace que `api` conecte con el rol de arranque (superusuario) y se mira
  `docker compose -p <proyecto> logs api`
- **THEN** el contenedor no arranca, el log tiene la línea del arranque fallido con la causa, y ninguna
  contraseña aparece en el log; lo mismo para `worker`

#### Scenario: Base inalcanzable

- **WHEN** la API arranca con `POSTGRES_HOST` apuntando a un host que no responde
- **THEN** el log tiene una línea `arranque_fallido` cuya causa dice que la base no es alcanzable, sin la
  contraseña ni la cadena de conexión, y el proceso termina distinto de 0

#### Scenario: Archivo de parámetros mal formado

- **WHEN** `parametros.yaml` tiene un YAML inválido o un campo con tipo equivocado
- **THEN** el log tiene una línea `arranque_fallido` que nombra el archivo y el campo, y el proceso
  termina distinto de 0
