## ADDED Requirements

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

### Requirement: El humo corre sólo en un proyecto de Compose aislado

`infra/ci/humo.sh` SHALL tomar el nombre del proyecto de Compose de `PROPTECH_COMPOSE_PROYECTO`, MUST
NOT llevar un nombre de proyecto fijo en el script, y MUST exportar esa variable para que todo script
que invoca (la restauración incluida) opere sobre el mismo proyecto y nunca sobre otro. Antes de
ejecutar ningún `up` ni ningún `down`, el humo MUST negarse a empezar, con un mensaje que nombre la
causa y cómo correrlo, en tres casos: (a) la variable no está definida; (b) vale `proptech` (el
proyecto del stack de uso real) y ese proyecto tiene contenedores corriendo; (c) el puerto 80 o el 443
del host ya están ocupados, porque el proxy los publica fijos y el humo no puede correr en paralelo con
otro stack. En el CI, el job define la variable.

#### Scenario: Sin variable

- **WHEN** se corre el humo sin `PROPTECH_COMPOSE_PROYECTO`
- **THEN** el humo termina distinto de 0 antes de ejecutar ningún `up` ni `down`, y el mensaje dice que
  falta la variable y da un ejemplo de cómo correrlo

#### Scenario: Proyecto `proptech` con contenedores

- **WHEN** se corre el humo con `PROPTECH_COMPOSE_PROYECTO=proptech` y ese proyecto tiene contenedores
  corriendo
- **THEN** el humo termina distinto de 0 antes de tocar nada, nombra el proyecto, y el stack real sigue
  levantado y con sus volúmenes

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
`docker` (los Dockerfile y `infra/compose.yaml`), `uv` (el backend) y `npm` (la web, con pnpm). Cada
ecosistema MUST apuntar a un directorio que exista y tener un límite de PR abiertos.

#### Scenario: El archivo es válido

- **WHEN** se lee `.github/dependabot.yml`
- **THEN** declara los cuatro ecosistemas, cada `directory` existe en el repositorio y
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

#### Scenario: Un test no tolera el paralelo

- **WHEN** un test sólo es correcto en serie
- **THEN** está marcado con un motivo escrito y corre aparte, nunca se lo saca de la suite

## MODIFIED Requirements

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
