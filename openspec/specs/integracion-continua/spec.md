# integracion-continua Specification

## Purpose
Define qué verifica la integración continua en cada push a `main` y garantiza que falle cuando falla
cualquiera de esas verificaciones, para que "el CI está en verde" sea una afirmación con valor.

## Requirements

### Requirement: Verificaciones en cada push

El CI SHALL correr en cada push a `main`, en cada pull request y a pedido manual, y MUST ejecutar: lint
y formato de Python, chequeo de tipos de Python, tests de Python (unitarios y de integración contra
PostgreSQL real), lint y formato de TypeScript, chequeo de tipos de TypeScript, tests de la web, una
prueba de humo del stack completo y una búsqueda de secretos en el historial del repositorio. Cada
trabajo MUST tener un límite de tiempo respaldado por una medición de su duración real, y las imágenes
de la búsqueda de secretos y de `shellcheck` MUST estar fijadas por digest, no sólo por tag.

#### Scenario: Push con todo correcto

- **WHEN** se pushea a `main` un commit donde todas las verificaciones pasan
- **THEN** el workflow termina en verde y cada una de las verificaciones listadas aparece como paso
  ejecutado

#### Scenario: Workflow revisado

- **WHEN** se lee el workflow del CI
- **THEN** se dispara con `push` a `main`, con `workflow_dispatch` y con `pull_request`; cada trabajo
  tiene `timeout-minutes`; y las imágenes de gitleaks y de `shellcheck` llevan `@sha256:`

#### Scenario: Un test que se cuelga

- **WHEN** corre `tests/integracion/test_tenant_por_transaccion.py` con el arreglo de R7 sacado en una
  copia (sin `registrar_reset_del_tenant_al_devolver`)
- **THEN** falla en rojo en menos de un minuto nombrando el test, en vez de quedar colgado; y si
  cualquier otro test se cuelga, el log del trabajo trae su traza antes de que lo corte el límite de
  tiempo

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

### Requirement: El humo verifica el candado en el stack vivo

La prueba de humo SHALL verificar en el stack levantado que la API y el worker conectan como un rol sin
superusuario ni `BYPASSRLS`, que la web no alcanza la base, y que un backup restaurado trae las dos
administraciones sembradas con sus políticas.

#### Scenario: Rol de la app en el stack vivo

- **WHEN** el humo consulta el rol con el que conectan la API y el worker
- **THEN** es `proptech_app`, sin superusuario ni `BYPASSRLS`

#### Scenario: Backup completo en el humo

- **WHEN** el humo siembra dos administraciones, espera un backup y lo restaura en
  `proptech_restauracion`
- **THEN** cuenta los complejos de cada administración en la base restaurada y coinciden con los
  sembrados

### Requirement: Cada paso del humo dice cuál es y deja su evidencia

Cada paso de la prueba de humo que falla SHALL nombrar su número, su descripción, la línea y el
comando que falló, también cuando falla un chequeo suelto (`[ ]` o `grep -q`), un `if ! ...; then` o un
`exit 1` explícito, y cuando falla algo dentro de `compose()` MUST nombrar la línea del llamado y no la
de la función. Cuando el humo falla, MUST volcar el estado y los logs de los contenedores antes de bajar
el stack. Cada arranque del servicio de respaldos MUST dejar exactamente un backup nuevo, y el conteo
de los `.dump` MUST esperar a que el volcado termine de aparecer, con un plazo acotado, en vez de
asumir que ya está.

#### Scenario: Un paso que falla

- **WHEN** un script mínimo que usa los helpers del humo fuerza a fallar un paso, una vez con un `[ ]`
  suelto, otra con un `grep -q` suelto, otra con un `if !` y otra con un `exit 1` explícito
- **THEN** en los cuatro casos la salida nombra el número y la descripción del paso, la línea y el
  comando que falló

#### Scenario: Ningún camino de falla queda anónimo

- **WHEN** se lee `infra/ci/humo.sh`
- **THEN** ningún `exit 1` ni `if !` termina el script sin pasar por el formateador del paso, y un
  test da rojo con una copia que reintroduce un `exit 1` pelado

#### Scenario: Falla dentro de compose

- **WHEN** un comando de `compose()` falla durante el paso N
- **THEN** la salida nombra la línea desde donde se llamó, no la de la función `compose`

#### Scenario: Un respaldo por arranque

- **WHEN** el humo cuenta los `.dump` de la carpeta de respaldos antes y después de cada `up` y de la
  corrida `--una-vez`
- **THEN** cada uno deja exactamente un `.dump` nuevo, y si uno deja dos (o ninguno) el paso falla

#### Scenario: Volcado lento

- **WHEN** el volcado tarda 3 segundos en aparecer en la carpeta
- **THEN** el conteo espera y da uno, no cero

#### Scenario: La falla queda en el log

- **WHEN** el humo falla, por ejemplo porque una copia de Compose le saca a `redis` una capacidad que
  su entrypoint necesita
- **THEN** la salida del humo trae `docker compose ps -a` y los logs de los contenedores, con el error
  de `redis`, antes de que el stack se baje

#### Scenario: El script del humo es ejecutable

- **WHEN** se leen los modos de `infra/**/*.sh` con `git ls-files -s`
- **THEN** todos son `100755`

### Requirement: El humo congela las dos dependencias a la vez

La prueba de humo SHALL congelar la base y Redis al mismo tiempo y verificar que `/api/salud` responde
503 dentro de su plazo total, con una línea `salud_degradada` por dependencia, y que `/salud-web`
informa la API como degradada y no como sin conexión. La limpieza MUST despausar las dos dependencias
antes de bajar el stack, aunque el paso falle.

#### Scenario: Base y Redis congelados

- **WHEN** el humo pausa `db` y `redis` a la vez y pide `/api/salud` y `/salud-web`
- **THEN** `/api/salud` responde 503 en menos de 2,5 segundos, hay exactamente dos líneas
  `salud_degradada` con el `request_id` del pedido, y `/salud-web` no informa `sin_conexion`

#### Scenario: Despausar antes de bajar

- **WHEN** se lee la limpieza del humo
- **THEN** despausa `db` y `redis` antes del `down -v`, y el test da rojo con una copia que invierte
  ese orden

### Requirement: Las cabeceras de seguridad se verifican de punta a punta

La prueba de humo SHALL pedir por el proxy la web y la API con GET y con HEAD, una ruta inexistente de
la API, y `/api/salud` con `api` detenida, y verificar las cabeceras de seguridad y la ausencia de
`Server`, `Via` y `X-Powered-By`. También SHALL verificar que Caddy recreado conserva sus datos.

#### Scenario: Cabeceras en el stack vivo

- **WHEN** el humo pide `/` y `/api/salud` por el proxy con GET y con HEAD, una ruta inexistente de la
  API, y `/api/salud` con `api` detenida
- **THEN** todas las respuestas cumplen el requisito de cabeceras del entorno de ejecución, y la última
  es un 502 sin `Server`

### Requirement: El humo verifica que la base restaurada conserva RLS habilitada

En la base restaurada, la prueba de humo SHALL verificar `relrowsecurity = t` y `relforcerowsecurity =
t` en las tablas con políticas, y MUST comparar el contenido de cada política (tabla, nombre, comando,
roles, `qual` y `with_check`) con el de la base en uso, no sólo su cantidad.

#### Scenario: Restauración con RLS deshabilitada

- **WHEN** se restaura una copia del dump con `DISABLE ROW LEVEL SECURITY` sobre `complejo` (con el
  `FORCE` intacto)
- **THEN** el paso de la restauración falla nombrando la tabla

#### Scenario: Política debilitada con la misma cantidad

- **WHEN** la base restaurada tiene la misma cantidad de políticas en `complejo`, pero una con
  `USING (true)`
- **THEN** el paso falla nombrando la tabla y la política que difiere

#### Scenario: Política renombrada

- **WHEN** una política de la base restaurada tiene otro nombre
- **THEN** el paso falla nombrando la tabla y los dos nombres

### Requirement: El ensayo de roles corre en el CI con la cabeza derivada

El CI SHALL correr `infra/ci/ensayo-roles.sh` entero (respaldo, restauración, ida y vuelta de las
migraciones) en un job propio con límite de tiempo, en un proyecto de Compose descartable. La revisión
que el ensayo espera tras subir hasta la cabeza MUST salir de las migraciones reales (`alembic heads`),
nunca de un número escrito a mano en el script, y el texto que el ensayo imprime sobre el ciclo MUST
nombrar esa misma revisión.

#### Scenario: El ensayo corre en el CI

- **WHEN** se lee `.github/workflows/ci.yml`
- **THEN** hay un job que ejecuta `infra/ci/ensayo-roles.sh`, con `timeout-minutes`, sin
  `continue-on-error`

#### Scenario: Una migración nueva no deja viejo al ensayo

- **WHEN** se agrega una migración nueva y no se toca `ensayo-roles.sh`
- **THEN** el ensayo verifica la cabeza nueva y su texto la nombra, y ningún test da rojo por un número
  desfasado

#### Scenario: Una cabeza escrita a mano

- **WHEN** `ensayo-roles.sh` vuelve a tener un número de revisión literal en `verificar_revision`
- **THEN** un test da rojo nombrando la línea

### Requirement: El humo y el ensayo de roles corren sólo en un proyecto de Compose aislado

`infra/ci/humo.sh` e `infra/ci/ensayo-roles.sh` SHALL tomar el nombre del proyecto de Compose de
`PROPTECH_COMPOSE_PROYECTO`, MUST NOT llevar un nombre de proyecto fijo ni un valor por defecto en el
script, y MUST exportar esa variable para que todo script que invocan (la restauración incluida)
opere sobre el mismo proyecto y nunca sobre otro. Antes de ejecutar ningún `up` ni ningún `down`, los
dos MUST negarse a empezar, con un mensaje que nombre la causa y cómo correrlos, en tres casos: (a) la
variable no está definida; (b) vale `proptech` (el proyecto del stack de uso real), **siempre**, haya o
no contenedores corriendo; (c) el puerto 80 o el 443 del host ya están ocupados, porque el proxy los
publica fijos y no pueden correr en paralelo con otro stack. Cualquier otro nombre MUST seguir
permitido. La comprobación MUST vivir en un solo lugar compartido por los dos scripts. En el CI, cada
job define su propia variable, distinta de `proptech`.

*Cambia lo aprobado antes* (decisión D15 del diseño): el caso (b) sólo rechazaba `proptech` "con
contenedores corriendo".

#### Scenario: Sin variable

- **WHEN** se corre el humo sin `PROPTECH_COMPOSE_PROYECTO`
- **THEN** el humo termina distinto de 0 antes de ejecutar ningún `up` ni `down`, y el mensaje dice que
  falta la variable y da un ejemplo de cómo correrlo

#### Scenario: Proyecto `proptech`, con o sin contenedores

- **WHEN** se corre el humo o el ensayo con `PROPTECH_COMPOSE_PROYECTO=proptech`, con el stack real
  corriendo, detenido con sus volúmenes, o sin ningún contenedor
- **THEN** el script termina distinto de 0 antes de invocar `compose` (ni un `up` ni un `down -v`),
  nombra el proyecto, y el stack real conserva sus contenedores y sus volúmenes

#### Scenario: El ensayo de roles comparte los rechazos

- **WHEN** se corre `ensayo-roles.sh` sin la variable, con `proptech` o con el puerto 80 ocupado
- **THEN** termina distinto de 0 antes de invocar `compose`, con el mismo mensaje que el humo y la forma
  de correr el ensayo

#### Scenario: Puertos ocupados

- **WHEN** se corre el humo con un proyecto propio mientras otro stack tiene el puerto 80 o el 443
  publicados
- **THEN** el humo termina distinto de 0 antes de ejecutar ningún `up` ni `down`, el mensaje nombra el
  puerto ocupado, y el otro stack sigue intacto

#### Scenario: Con un proyecto propio y el host libre

- **WHEN** se corre el humo con `PROPTECH_COMPOSE_PROYECTO=proptech-humo-prueba` y nada ocupa el 80 ni
  el 443
- **THEN** el humo usa sólo ese proyecto, la restauración también, y al terminar no queda ningún
  contenedor ni volumen de ese proyecto

#### Scenario: La restauración sigue al proyecto del humo

- **WHEN** el humo corre con un proyecto propio y invoca `restaurar.sh`
- **THEN** la restauración opera sobre ese proyecto, nunca sobre `proptech`, y un test da rojo con una
  copia del humo que no exporta la variable

#### Scenario: Nombre fijo en el script

- **WHEN** se lee `humo.sh`
- **THEN** no aparece `-p proptech` ni ningún otro nombre de proyecto literal, y un test da rojo con
  una copia que lo reintroduce

### Requirement: El chequeo de capacidades cubre todos los servicios

El humo SHALL derivar la lista de servicios a los que les verifica `NoNewPrivs` y `CapBnd` de la
configuración efectiva de Compose, y MUST dar rojo si un servicio de esa lista no tiene sus
capacidades esperadas declaradas, nombrando el servicio.

#### Scenario: Un noveno servicio

- **WHEN** una copia de `compose.yaml` agrega un servicio sin declarar sus capacidades esperadas en el
  humo
- **THEN** el humo falla nombrando ese servicio, en vez de ignorarlo

#### Scenario: PID 1 de la base

- **WHEN** una copia de `compose.yaml` agrega `init: true` a `db` (el PID 1 pasa a ser `docker-init`,
  que corre como root)
- **THEN** el chequeo del PID 1 de `db` da rojo, y un test estático impide que `compose.yaml` lo
  declare; la nota del humo dice que el chequeo sólo se ve rojo con ese cambio

### Requirement: El verificador de cabeceras no acepta de más

El verificador de cabeceras de seguridad del humo SHALL rechazar una cabecera de seguridad repetida y
un valor que contenga la palabra esperada rodeada de otro texto (por ejemplo `no-referrer-when-downgrade`
en lugar de `no-referrer`).

#### Scenario: Cabecera duplicada

- **WHEN** el verificador recibe dos `X-Frame-Options: DENY`
- **THEN** falla nombrando la cabecera y la descripción de la respuesta

#### Scenario: Valor con texto de más

- **WHEN** el verificador recibe `Referrer-Policy: no-referrer-when-downgrade`
- **THEN** falla nombrando el valor obtenido y el esperado

### Requirement: Dependabot propone las actualizaciones

El repositorio SHALL tener `.github/dependabot.yml` con actualizaciones semanales para `github-actions`,
`docker` (los Dockerfile de `backend` y `web`), `docker-compose` (`infra/compose.yaml`), `uv` (el backend) y `npm` (la web, con pnpm). Cada
ecosistema MUST apuntar a un directorio que exista y tener un límite de PR abiertos.

#### Scenario: El archivo es válido

- **WHEN** se lee `.github/dependabot.yml`
- **THEN** declara los cinco ecosistemas (`docker` y `docker-compose` cuentan por separado), cada `directory` existe en el repositorio y
  `open-pull-requests-limit` está presente en todos

#### Scenario: Una acción nueva sin SHA

- **WHEN** Dependabot propone actualizar una acción
- **THEN** la actualización mantiene el SHA de 40 caracteres, y `test_ci_workflow.py` sigue exigiéndolo

### Requirement: Chromium se cachea en el job `web`

El job `web` del CI SHALL restaurar los navegadores de Playwright de una caché cuya clave incluya la
versión de Playwright resuelta por `pnpm-lock.yaml`, e instalar sólo lo que falte. Si la caché no
existe o no se restaura, el job MUST instalar Chromium y pasar igual.

#### Scenario: Corrida con caché

- **WHEN** corre el job `web` con la caché restaurada
- **THEN** el paso de instalación no descarga Chromium y los tests en el navegador pasan

#### Scenario: Cambia la versión de Playwright

- **WHEN** cambia la versión de Playwright en el lockfile
- **THEN** la clave de la caché cambia y Chromium se descarga de nuevo

### Requirement: El backend corre en paralelo sin compartir base

El CI SHALL correr los tests unitarios y los de integración del backend en paralelo con `pytest-xdist`,
y cada proceso trabajador MUST tener su propio PostgreSQL y su propio Redis, de modo que ningún test
vea datos de otro. La suite MUST dar el mismo conjunto de tests pasados que en serie, y el tiempo del
job completo MUST bajar respecto de la corrida en serie medida antes del cambio.

#### Scenario: Mismos tests, menos tiempo

- **WHEN** se corre la suite del backend en serie y en paralelo sobre el mismo commit, con Docker
- **THEN** pasan los mismos tests, y la duración en paralelo queda medida y escrita junto a la de serie

#### Scenario: Aislamiento entre trabajadores

- **WHEN** dos tests de integración que escriben en la misma tabla corren en trabajadores distintos
- **THEN** ninguno ve las filas del otro

*Se cumple por construcción, sin test propio*: cada módulo de test levanta su propio contenedor de
Postgres (`testcontainers`), así que dos trabajadores no comparten base.

#### Scenario: Un test no tolera el paralelo

- **WHEN** un test sólo es correcto en serie
- **THEN** está marcado con un motivo escrito y corre aparte, nunca se lo saca de la suite
