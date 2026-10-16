## ADDED Requirements

### Requirement: Cada paso del humo dice cuál es y deja su evidencia

Cada paso de la prueba de humo que falla SHALL nombrar su número, su descripción, la línea y el
comando que falló, también cuando falla un chequeo suelto (`[ ]` o `grep -q`) y no sólo un
`if ! ...; then`. Cuando el humo falla, MUST volcar el estado y los logs de los contenedores antes de
bajar el stack. Cada arranque del servicio de respaldos MUST dejar exactamente un backup nuevo.

#### Scenario: Un paso que falla

- **WHEN** un script mínimo que usa los helpers del humo fuerza a fallar un paso, una vez con un `[ ]`
  suelto, otra con un `grep -q` suelto y otra con un `if !`
- **THEN** en los tres casos la salida nombra el número y la descripción del paso, la línea y el
  comando que falló

#### Scenario: Un respaldo por arranque

- **WHEN** el humo cuenta los `.dump` de la carpeta de respaldos antes y después de cada `up` y de la
  corrida `--una-vez`
- **THEN** cada uno deja exactamente un `.dump` nuevo, y si uno deja dos (o ninguno) el paso falla

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

En la base restaurada, la prueba de humo SHALL verificar `relrowsecurity = t` además de
`relforcerowsecurity = t` en las tablas con políticas.

#### Scenario: Restauración con RLS deshabilitada

- **WHEN** se restaura una copia del dump con `DISABLE ROW LEVEL SECURITY` sobre `complejo` (con el
  `FORCE` intacto)
- **THEN** el paso de la restauración falla nombrando la tabla

## MODIFIED Requirements

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
