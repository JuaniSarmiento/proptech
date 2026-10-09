## Purpose

Define cómo arranca PropTech completo con un solo comando, qué piezas quedan expuestas a Internet
(sólo el proxy) y cuáles no, cómo se aplican las migraciones de la base y qué informa el endpoint de
salud a través de la única puerta pública.

## ADDED Requirements

### Requirement: Arranque completo con un comando

El sistema SHALL levantarse entero (proxy, web, API, base de datos y migraciones) con
`docker compose up` ejecutado en `infra/`, desde un clon limpio del repositorio, siguiendo sólo los
pasos del README, sin instalar en el host nada más que Docker con Compose.

#### Scenario: Clon limpio siguiendo el README

- **WHEN** una persona clona el repositorio en una máquina con Docker, copia `infra/.env.example` a
  `infra/.env` y ejecuta `docker compose up --build` en `infra/`
- **THEN** todos los servicios de larga vida quedan en estado saludable y el trabajo de migraciones
  termina con código de salida 0

#### Scenario: Falta el archivo de entorno

- **WHEN** se ejecuta `docker compose up` en `infra/` sin `infra/.env` o sin una variable obligatoria
  como la contraseña de la base
- **THEN** Compose se niega a arrancar y el mensaje nombra la variable que falta, en lugar de
  arrancar con un valor por defecto

### Requirement: El proxy es la única puerta pública

Sólo el proxy SHALL publicar puertos hacia el host, y sólo el 80 y el 443. La base de datos, la API
y la web MUST NOT publicar ningún puerto y MUST ser alcanzables únicamente desde la red interna de
Compose. La base de datos MUST estar en una red sin salida a Internet.

#### Scenario: Puertos publicados del stack levantado

- **WHEN** el stack está levantado y se listan los puertos publicados de cada servicio
- **THEN** el único servicio con puertos publicados es el proxy, con los puertos 80 y 443, y la
  base, la API y la web no tienen ninguno

#### Scenario: Intento de conexión directa a la base desde el host

- **WHEN** con el stack levantado se consulta, para el servicio de base de datos, el mapeo de
  puerto publicado hacia el host (`docker compose port db 5432`)
- **THEN** no hay ningún mapeo: el puerto 5432 no está publicado y no existe forma de abrir una
  conexión directa desde el host a la base

### Requirement: Ruteo por prefijo en el proxy

El proxy SHALL enviar a la API todo pedido cuya ruta empiece con `/api/` y a la web todo lo demás.

#### Scenario: Pedido a la API a través del proxy

- **WHEN** se hace `GET /api/salud` contra el proxy
- **THEN** responde la API

#### Scenario: Pedido a la web a través del proxy

- **WHEN** se hace `GET /` contra el proxy
- **THEN** responde la web con una página HTML y código 200

### Requirement: Endpoint de salud

La API SHALL exponer `GET /api/salud`, sin autenticación, que responde JSON. Cuando la API funciona y
la base responde, MUST contestar 200 con `{"estado": "ok", "base": "ok"}`. Cuando la base no
responde, MUST contestar 503 con `{"estado": "degradado", "base": "sin_conexion"}`. La respuesta
MUST NOT incluir la cadena de conexión, el usuario, el host de la base, trazas de error ni versiones
de componentes.

#### Scenario: Todo funciona

- **WHEN** el stack está levantado y se hace `GET /api/salud` a través del proxy
- **THEN** la respuesta es 200 con cuerpo `{"estado": "ok", "base": "ok"}`

#### Scenario: La base no responde

- **WHEN** la API está corriendo, la base está detenida y se hace `GET /api/salud`
- **THEN** la respuesta es 503 con cuerpo `{"estado": "degradado", "base": "sin_conexion"}` y el
  cuerpo no contiene la cadena de conexión ni el texto de la excepción

#### Scenario: La base está congelada, no caída

- **WHEN** la API está corriendo, el proceso de la base está pausado (congelado, no detenido: el
  socket sigue existiendo pero nadie responde el handshake) y se hace `GET /api/salud`
- **THEN** la respuesta es 503 con cuerpo `{"estado": "degradado", "base": "sin_conexion"}` y llega
  en un tiempo acotado (menor al límite de conexión configurado, no indefinido)

### Requirement: Migraciones como trabajo aparte

Las migraciones de la base SHALL aplicarse con un trabajo separado que corre antes de que arranque la
API, y no en cada arranque de la API. La API MUST NOT arrancar si el trabajo de migraciones falla. La
primera migración MUST existir, no crear ninguna tabla de dominio y poder aplicarse y revertirse
sobre una base vacía.

#### Scenario: Instalación limpia

- **WHEN** se aplican las migraciones sobre una base PostgreSQL vacía
- **THEN** la base queda en la última revisión y la tabla de versiones de Alembic registra la primera
  migración

#### Scenario: Ida y vuelta

- **WHEN** sobre una base vacía se aplican todas las migraciones y después se revierten todas
- **THEN** ambos comandos terminan sin error y la base queda sin revisión aplicada

#### Scenario: Falla el trabajo de migraciones

- **WHEN** el trabajo de migraciones termina con error al levantar el stack
- **THEN** la API no arranca

### Requirement: Configuración sólo por variables de entorno y sin secretos en el repositorio

Toda configuración que varía entre entornos (cadena de conexión, contraseñas, dirección del sitio)
SHALL leerse de variables de entorno. El repositorio MUST incluir sólo `.env.example` con valores de
ejemplo no válidos como credencial real, y MUST NOT versionar ningún archivo `.env` real. Las imágenes
construidas MUST NOT contener archivos `.env`.

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

### Requirement: Contenedores sin privilegios de root

Los procesos de la API y de la web SHALL correr dentro de sus contenedores con un usuario sin
privilegios de root.

#### Scenario: Usuario del proceso

- **WHEN** se consulta el usuario efectivo del proceso principal de los contenedores de la API y de
  la web
- **THEN** no es root (uid distinto de 0)
