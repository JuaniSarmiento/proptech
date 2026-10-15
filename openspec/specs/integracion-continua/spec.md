# integracion-continua Specification

## Purpose
Define qué verifica la integración continua en cada push a `main` y garantiza que falle cuando falla
cualquiera de esas verificaciones, para que "el CI está en verde" sea una afirmación con valor.

## Requirements

### Requirement: Verificaciones en cada push

El CI SHALL correr en cada push a `main` y a pedido manual, y MUST ejecutar: lint y formato de
Python, chequeo de tipos de Python, tests de Python (unitarios y de integración contra PostgreSQL
real), lint y formato de TypeScript, chequeo de tipos de TypeScript, tests de la web, una prueba de
humo del stack completo y una búsqueda de secretos en el historial del repositorio.

#### Scenario: Push con todo correcto

- **WHEN** se pushea a `main` un commit donde todas las verificaciones pasan
- **THEN** el workflow termina en verde y cada una de las verificaciones listadas aparece como paso
  ejecutado

### Requirement: El CI falla cuando falla una verificación

Cada verificación SHALL hacer fallar el workflow si falla. Ningún paso MUST ignorar su código de
salida, y una suite que no recolecta ningún test MUST contar como falla.

#### Scenario: Test roto de Python

- **WHEN** un test de Python falla
- **THEN** el workflow termina en rojo

#### Scenario: Test roto de la web

- **WHEN** un test de la web falla
- **THEN** el workflow termina en rojo

#### Scenario: Error de lint o de formato

- **WHEN** un archivo de Python o de TypeScript no cumple el lint o el formato
- **THEN** el workflow termina en rojo

#### Scenario: Suite vacía

- **WHEN** la suite de Python o la de la web no encuentra ningún test
- **THEN** el workflow termina en rojo

### Requirement: Canario de test roto

En cada corrida, el CI SHALL demostrar que sus comandos de test fallan ante un test roto: agrega en
una copia de trabajo descartable un test que falla a propósito, en Python y en la web, corre el mismo
comando de test que usa el paso normal y MUST exigir que ese comando termine con código distinto de 0.
Si el comando termina en 0 con el test roto, el workflow MUST terminar en rojo. El test roto MUST NOT
quedar commiteado.

#### Scenario: Comando de test que traga fallas

- **WHEN** el comando de test de Python o de la web se configura de forma que termina en 0 aunque un
  test falle (por ejemplo, con `|| true`)
- **THEN** el canario detecta el código 0 con el test roto y el workflow termina en rojo

#### Scenario: Corrida normal

- **WHEN** los comandos de test están bien configurados
- **THEN** el canario ve código distinto de 0 con el test roto, el paso del canario pasa y el árbol
  de trabajo commiteado no contiene el test roto

### Requirement: Tests de integración contra PostgreSQL real

Los tests de integración SHALL correr contra un PostgreSQL real y un Redis real de la misma versión
que usa Compose, y MUST NOT reemplazarlos por otro motor ni por dobles en memoria. El mismo mecanismo
MUST funcionar en la máquina del desarrollador y en el CI. La verificación de que las versiones
coinciden MUST mirar la imagen del contenedor que efectivamente corrió en los tests, no una constante
derivada del propio archivo de Compose.

#### Scenario: Migraciones en el CI

- **WHEN** corre la suite de integración en el CI
- **THEN** las migraciones se aplican y se revierten contra un PostgreSQL real levantado para la
  corrida

#### Scenario: Worker contra Redis real

- **WHEN** corre la suite de integración de la cola
- **THEN** los trabajos se encolan y se ejecutan contra un Redis real levantado para la corrida, y los
  casos de Redis caído, congelado y lento se prueban sobre un contenedor real

#### Scenario: Versión de PostgreSQL desalineada

- **WHEN** la imagen del contenedor de PostgreSQL o de Redis que corrió en los tests difiere de la
  declarada en Compose
- **THEN** un test falla y nombra las dos imágenes

#### Scenario: La imagen de los tests no está escrita a mano

- **WHEN** se lee la configuración de los tests de integración
- **THEN** las imágenes de PostgreSQL y de Redis se derivan del archivo de Compose y no aparecen
  escritas como literal

### Requirement: Prueba de humo del stack detrás del proxy

El CI SHALL levantar el stack completo con Compose y verificar que `GET /api/salud` a través del
proxy responde 200 con la base y la cola conectadas, que el único servicio con puertos publicados es
el proxy, que el worker está saludable y completa un trabajo con un reintento, que el `request_id`
asignado por el proxy aparece en el log de la API tanto en un pedido directo como en uno que pasa por
la web, que con Redis pausado `/salud-web` informa la API como degradada y no como sin conexión, que
un backup se generó solo, que ese backup se restaura en una base aparte y que sobrevive a
`docker compose down -v`. Todo comando destructivo del humo MUST apuntar al proyecto de Compose
`proptech` o a bases con el prefijo `proptech_`.

#### Scenario: Humo en el CI

- **WHEN** corre el paso de humo
- **THEN** el stack se levanta, el endpoint de salud responde 200 a través del proxy, la verificación
  de puertos publicados pasa, el `request_id` se sigue de punta a punta, el backup automático aparece
  y se restaura, y el stack se baja al terminar, aun si el paso falló

#### Scenario: Request id malicioso en el humo

- **WHEN** el humo manda un pedido con un `X-Request-ID` malicioso a través del proxy
- **THEN** la respuesta trae un UUID distinto y el valor malicioso no aparece en los logs de ningún
  servicio

#### Scenario: Redis pausado en el humo

- **WHEN** el humo pausa Redis y consulta `GET /api/salud` y `GET /salud-web` a través del proxy
- **THEN** `/api/salud` responde 503 con `"cola": "sin_conexion"` en menos de 4 segundos,
  `/salud-web` responde 503 con `{"web": "ok", "api": "degradado"}` (la API contestó dentro del límite
  de la web, no `"sin_conexion"`), y Redis se despausa aunque la verificación falle

### Requirement: Búsqueda de secretos

El CI SHALL buscar secretos en todo el historial de git del repositorio y MUST fallar si encuentra
alguno. Los valores de `.env.example` MUST NOT disparar la búsqueda.

#### Scenario: Secreto commiteado

- **WHEN** un commit contiene algo con forma de credencial real (por ejemplo una clave privada o un
  token de un proveedor conocido)
- **THEN** el workflow termina en rojo y señala el archivo y el commit

### Requirement: Versiones de herramientas fijadas

Las acciones del workflow, las imágenes de Docker y las herramientas de lint y test SHALL estar
fijadas a una versión exacta. Ninguna imagen de Compose ni del CI MUST usar la etiqueta `latest` ni
una etiqueta sin versión de parche.

#### Scenario: Imagen sin versión fija

- **WHEN** un archivo de Compose o un Dockerfile referencia una imagen con `latest`, sin etiqueta, o
  con una etiqueta sin versión de parche
- **THEN** un test falla y nombra la imagen

### Requirement: Dependencias con wheels para la versión de Python del proyecto

Las dependencias del backend SHALL declararse en versiones que publican wheels para la versión de
Python del proyecto en Linux, macOS y Windows, para que `uv sync --locked` no tenga que compilar nada.
PyYAML MUST declararse como `pyyaml>=6.0.3,<7` y el lock MUST resolverla en 6.0.3 o posterior.

#### Scenario: PyYAML con wheel para Python 3.14

- **WHEN** se leen `pyproject.toml` y `uv.lock` del backend
- **THEN** PyYAML está declarada como `>=6.0.3,<7` y el lock la resuelve en 6.0.3 o posterior

### Requirement: Análisis estático de los scripts de Bash

El CI SHALL correr `shellcheck`, en una versión fijada, sobre todos los scripts de Bash de `infra/`, y
MUST fallar ante cualquier hallazgo.

#### Scenario: Script de Bash con un hallazgo de shellcheck

- **WHEN** un script de `infra/` tiene un hallazgo de `shellcheck` (por ejemplo, una variable sin
  comillas)
- **THEN** el paso de `shellcheck` del CI falla y nombra el archivo
