## MODIFIED Requirements

### Requirement: Arranque completo con un comando

El sistema SHALL levantarse entero (proxy, web, API, worker, base de datos, Redis, respaldos y
migraciones) con `docker compose up` ejecutado en `infra/`, desde un clon limpio del repositorio,
siguiendo sólo los pasos del README, sin instalar en el host nada más que Docker con Compose.

#### Scenario: Clon limpio siguiendo el README

- **WHEN** una persona clona el repositorio en una máquina con Docker, copia `infra/.env.example` a
  `infra/.env`, crea la carpeta de respaldos como indica el README y ejecuta
  `docker compose up --build` en `infra/`
- **THEN** todos los servicios de larga vida (proxy, web, API, worker, base, Redis y respaldos) quedan
  en estado saludable y el trabajo de migraciones termina con código de salida 0

#### Scenario: Falta el archivo de entorno

- **WHEN** se ejecuta `docker compose up` en `infra/` sin `infra/.env` o sin una variable obligatoria
  como la contraseña de la base, la de Redis, la carpeta de respaldos o el usuario del host
  (`PROPTECH_UID`, `PROPTECH_GID`)
- **THEN** Compose se niega a arrancar y el mensaje nombra la variable que falta, en lugar de
  arrancar con un valor por defecto

### Requirement: El proxy es la única puerta pública

Sólo el proxy SHALL publicar puertos hacia el host, y sólo el 80 y el 443. La base de datos, Redis, la
API, el worker, la web y el servicio de respaldos MUST NOT publicar ningún puerto y MUST ser
alcanzables únicamente desde la red interna de Compose. La base de datos, Redis y el servicio de
respaldos MUST estar en una red sin salida a Internet. El worker MAY tener salida a Internet sólo por
una red propia, en la que no está ningún otro servicio.

#### Scenario: Red de salida del worker

- **WHEN** se lee la configuración de Compose
- **THEN** el worker está en la red interna y en una red de salida sin `internal`, ningún otro servicio
  (ni la base, ni Redis, ni la API, ni el servicio de respaldos) está en esa red de salida, y la base,
  Redis y el servicio de respaldos están sólo en la red interna

#### Scenario: Puertos publicados del stack levantado

- **WHEN** el stack está levantado y se listan los puertos publicados de cada servicio
- **THEN** el único servicio con puertos publicados es el proxy, con los puertos 80 y 443, y ningún
  otro servicio tiene alguno

#### Scenario: Intento de conexión directa a la base desde el host

- **WHEN** con el stack levantado se consulta, para el servicio de base de datos, el mapeo de
  puerto publicado hacia el host (`docker compose port db 5432`)
- **THEN** no hay ningún mapeo: el puerto 5432 no está publicado y no existe forma de abrir una
  conexión directa desde el host a la base

#### Scenario: Intento de conexión directa a Redis desde el host

- **WHEN** con el stack levantado se consulta `docker compose port redis 6379`
- **THEN** no hay ningún mapeo

#### Scenario: Redis sin contraseña

- **WHEN** desde la red interna se intenta un comando contra Redis sin la contraseña
- **THEN** Redis lo rechaza por falta de autenticación

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

### Requirement: Configuración sólo por variables de entorno y sin secretos en el repositorio

Toda configuración que varía entre entornos (cadena de conexión, contraseñas de la base y de Redis,
dirección del sitio, ruta del archivo de parámetros, carpeta, usuario, frecuencia, límite y retención
de los respaldos) SHALL leerse de variables de entorno. El repositorio MUST incluir sólo
`.env.example` con valores de ejemplo no válidos como credencial real, y MUST NOT versionar ningún
archivo `.env` real ni la carpeta de respaldos. Las imágenes construidas MUST NOT contener archivos
`.env`. Toda variable obligatoria que falte, esté vacía, en blanco, tenga un tipo equivocado o esté
fuera de rango MUST hacer terminar al proceso con un error que nombre cada variable con problema sin
mostrar nunca su valor. El trabajo de migraciones MUST necesitar sólo las variables de la base. Las
contraseñas MUST guardarse en la configuración como valores secretos, que no aparecen en su
representación, y la cadena de conexión con contraseña MUST armarse sólo al crear la conexión.

#### Scenario: Contraseñas fuera de la representación de la configuración

- **WHEN** se imprime, se representa o se vuelca a un diccionario o a JSON la configuración cargada con
  contraseñas de la base y de Redis
- **THEN** ninguna de las dos contraseñas aparece, y el único código que lee su valor es el que crea la
  conexión a la base o a Redis

#### Scenario: Archivo de entorno ignorado

- **WHEN** existe `infra/.env` en la copia local y se consulta el estado de git
- **THEN** git no lo lista como archivo a versionar

#### Scenario: Imagen sin archivo de entorno

- **WHEN** se construyen las imágenes de la API y de la web con un `.env` presente en su carpeta
- **THEN** ninguna imagen contiene un archivo `.env`

#### Scenario: API sin cadena de conexión

- **WHEN** la API arranca sin la variable de la cadena de conexión
- **THEN** el proceso termina con un error que nombra la variable faltante y no muestra ningún valor
  secreto

#### Scenario: Variables de Redis rotas

- **WHEN** la API o el worker arrancan con `REDIS_HOST` o `REDIS_PASSWORD` faltante, vacía o en
  blanco, o con `REDIS_PORT` igual a `abc`, `0` o `70000`
- **THEN** el proceso termina con un error que nombra cada variable con problema y no contiene el
  valor de ninguna contraseña

#### Scenario: Archivo de parámetros inexistente

- **WHEN** la API o el worker arrancan con `PROPTECH_PARAMETROS` apuntando a un archivo que no existe
- **THEN** el proceso termina con un error que nombra `PROPTECH_PARAMETROS`

#### Scenario: Migraciones sólo con las variables de la base

- **WHEN** el trabajo de migraciones corre con las variables de PostgreSQL y sin ninguna variable de
  Redis ni `PROPTECH_PARAMETROS`
- **THEN** las migraciones se aplican sin error de configuración

#### Scenario: El stack pasa la configuración nueva a la API

- **WHEN** se lee la configuración de Compose
- **THEN** la API y el worker reciben las variables de Redis (la contraseña desde el archivo de
  entorno, obligatoria) y la ruta del archivo de parámetros, con la carpeta `config/` montada de sólo
  lectura, y `.env.example` incluye valores de ejemplo para la contraseña de Redis y las variables de
  respaldos

#### Scenario: Carpeta de respaldos ignorada

- **WHEN** existe la carpeta local de respaldos con archivos y se consulta el estado de git
- **THEN** git no lista ningún backup como archivo a versionar

### Requirement: Contenedores sin privilegios de root

Los procesos de la API, la web, el worker, Redis y el servicio de respaldos SHALL correr dentro de sus
contenedores con un usuario sin privilegios de root.

#### Scenario: Usuario del proceso

- **WHEN** se consulta el usuario efectivo del proceso principal de los contenedores de la API, la
  web, el worker, Redis y respaldos
- **THEN** no es root (uid distinto de 0)
