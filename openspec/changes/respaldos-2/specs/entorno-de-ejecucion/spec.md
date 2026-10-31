## MODIFIED Requirements

### Requirement: Endpoint de salud

La API SHALL exponer `GET /api/salud`, sin autenticación, que responde JSON. Cuando la API funciona,
la base responde y la cola responde, MUST contestar 200 con
`{"estado": "ok", "base": "ok", "cola": "ok"}`. Cuando la base o la cola no responden, MUST contestar
503 con `"estado": "degradado"` y `"sin_conexion"` en el componente que falla (`base`, `cola` o
ambos). Las verificaciones de la base y de la cola MUST correr en paralelo y compartir un plazo total
de 1,5 segundos, de modo que la respuesta llegue dentro de ese plazo aunque las dos dependencias estén
congeladas, por debajo del límite de 2 segundos con el que `/salud-web` consulta a la API; una
verificación que no termina dentro del plazo cuenta como `sin_conexion`. La respuesta MUST NOT
incluir la cadena de conexión, el usuario, el host de la base o de Redis, trazas de error ni versiones
de componentes. La API MUST usar un único engine de base por proceso, creado al arrancar la aplicación
y con los parámetros de su pool tomados de la configuración, y cada verificación MUST quedar acotada
aunque la conexión ya esté abierta en el pool. Una verificación fallida MUST registrar en el log
exactamente una línea `salud_degradada` con la dependencia y el tipo de error, nunca el mensaje del
driver, aunque el hilo que corría la verificación termine con un error después de vencido el plazo.
Ninguna respuesta 503 MUST salir sin su línea `salud_degradada` ya registrada: por cada dependencia
que la respuesta informa como `sin_conexion` tiene que haber en el log exactamente una línea para esa
dependencia y ese pedido, ni cero ni dos, sin importar cómo compitan el vencimiento del plazo y el
hilo que termina tarde.

#### Scenario: Un solo engine por proceso

- **WHEN** la API atiende varios pedidos a `GET /api/salud`
- **THEN** todos usan el engine creado al arrancar la aplicación, sin crear uno nuevo por pedido, y ese
  engine toma de la configuración `pool_pre_ping`, el tamaño del pool, el reciclado, la espera del pool
  y el límite de conexión

#### Scenario: La base se congela con una conexión abierta

- **WHEN** el pool ya tiene una conexión abierta, el proceso de la base se pausa y se hace
  `GET /api/salud`
- **THEN** la respuesta es 503 con `"base": "sin_conexion"` en menos de 3 segundos, el log registra la
  dependencia y el tipo de error sin el mensaje del driver, y cuando la base vuelve el siguiente pedido
  responde 200

#### Scenario: Todo funciona

- **WHEN** el stack está levantado y se hace `GET /api/salud` a través del proxy
- **THEN** la respuesta es 200 con cuerpo `{"estado": "ok", "base": "ok", "cola": "ok"}`

#### Scenario: La base no responde

- **WHEN** la API está corriendo, la base está detenida y se hace `GET /api/salud`
- **THEN** la respuesta es 503 con cuerpo `{"estado": "degradado", "base": "sin_conexion", "cola": "ok"}`
  y el cuerpo no contiene la cadena de conexión ni el texto de la excepción

#### Scenario: La base está congelada, no caída

- **WHEN** la API está corriendo, el proceso de la base está pausado (congelado, no detenido: el
  socket sigue existiendo pero nadie responde el handshake) y se hace `GET /api/salud`
- **THEN** la respuesta es 503 con `"base": "sin_conexion"` y llega en un tiempo acotado (menor al
  límite de conexión configurado, no indefinido)

#### Scenario: La cola no responde

- **WHEN** Redis está detenido o pausado y se hace `GET /api/salud`
- **THEN** la respuesta es 503 con cuerpo `{"estado": "degradado", "base": "ok", "cola": "sin_conexion"}`
  en menos de 4 segundos

#### Scenario: La base y la cola no responden

- **WHEN** la base y Redis están detenidos y se hace `GET /api/salud`
- **THEN** la respuesta es 503 con cuerpo
  `{"estado": "degradado", "base": "sin_conexion", "cola": "sin_conexion"}`

#### Scenario: Las dos dependencias congeladas

- **WHEN** la verificación de la base y la de la cola no terminan nunca (las dos dependencias
  congeladas) y se hace `GET /api/salud`
- **THEN** la respuesta es 503 con `"base": "sin_conexion"` y `"cola": "sin_conexion"` en menos de 1,8
  segundos: el plazo es uno solo para las dos, no la suma de los dos

#### Scenario: Una dependencia lenta dentro del plazo

- **WHEN** la verificación de la base o la de la cola tarda 1 segundo y responde bien
- **THEN** la respuesta es 200 con las dos dependencias en `"ok"`

#### Scenario: Una sola línea por verificación fallida

- **WHEN** la verificación de la base o la de la cola vence el plazo y el hilo que la corría termina
  después con un error
- **THEN** el log tiene exactamente una línea `salud_degradada` para esa dependencia en ese pedido, esa
  línea lleva el `request_id` del pedido, y ninguna línea contiene el mensaje del error tardío

#### Scenario: Ráfaga de pedidos con una dependencia congelada

- **WHEN** se hacen muchos pedidos seguidos a `GET /api/salud` con una dependencia congelada, de modo
  que el vencimiento del plazo y el final del hilo de la verificación caigan en el mismo instante en
  algunos de ellos
- **THEN** cada respuesta 503 tiene en el log su línea `salud_degradada` para la dependencia que
  informa como `sin_conexion`, con el `request_id` de ese pedido: no hay ninguna respuesta 503 sin
  línea, ni ninguna dependencia con dos líneas en el mismo pedido
