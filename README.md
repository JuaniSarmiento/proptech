# PropTech

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados) en
Mendoza: liquidación de expensas, cuenta corriente de cada unidad, registro de pagos y portal del
vecino. Proyecto de Alberto Cortez (también conocido como **koris**) y Juan Ignacio Sarmiento.

## Estado

Base de conocimiento cerrada y congelada para el primer hito (octubre de 2026), con preguntas abiertas
que se responden antes de cada cambio. El MVP arranca por **edificios**. Construidos y
archivados: **1a `infraestructura-base`** (el sistema completo arranca con un comando y el CI corre en
cada push), **1b `arranque-del-sistema`** (configuración, tipo `Dinero` exacto, parámetros y
edificio de ejemplo validados), **1c `cola-logs-y-respaldos`** (Redis, worker con reintentos e
idempotencia, logs en JSON y número de seguimiento de punta a punta; cerrado con OK con deuda
anotada), **1d `respaldos-y-restauracion`** (`pg_dump` automático y a diario, restauración probada
contra una base aparte), **2a `aislamiento-por-administracion`** (roles de PostgreSQL separados,
Row-Level Security por administración y auditoría de acciones sensibles; el candado, D-097), **2c
`endurecimiento-de-infraestructura`** (cabeceras, contenedores y CI más duros) y **3a
`configuracion-del-edificio`** (el modelo del edificio completo: unidades, grupos de reparto,
categorías de gasto y la configuración de intereses y vencimiento, versionada y de sólo agregar). En
construcción: **2b `login`** y **3b `pantallas-del-edificio`** (las siete pantallas del administrador).
Todavía no hay liquidación ni cuenta corriente: llegan en los cambios 4 a 7 del roadmap
([`CHANGES.md`](CHANGES.md), con el detalle de cada cambio en
[`knowledge-base/12_fichas_de_changes.md`](knowledge-base/12_fichas_de_changes.md)).

## Estructura

| Carpeta | Qué tiene |
|---|---|
| [`knowledge-base/`](knowledge-base/) | **La base de conocimiento del MVP**: visión, actores, reglas de negocio, decisiones, glosario y fases. Es la fuente de verdad: empezá por su [README](knowledge-base/README.md) |
| `config/` | `parametros.yaml` (valores con que arranca cada edificio) y `semilla/` (edificio de ejemplo) |
| `openspec/` | Cambios del ciclo OPSX |
| `web/` | Frontend en Next.js |
| `backend/` | API en FastAPI, worker y dominio compartido (`proptech_core`, `proptech_api`, `proptech_worker`) |
| `infra/` | Docker Compose, Caddy y los scripts de CI |

La estructura completa y su porqué están en la decisión D-040 de
[`knowledge-base/09_decisiones_y_supuestos.md`](knowledge-base/09_decisiones_y_supuestos.md).

## Cómo levantarlo

Requisitos: Docker con Compose (`docker compose version`).

```bash
cp infra/.env.example infra/.env   # completar las cuatro POSTGRES_*_PASSWORD con valores propios
mkdir -p infra/datos-respaldos     # carpeta de los backups, fuera de git (D9)
cd infra
PROPTECH_UID=$(id -u) PROPTECH_GID=$(id -g) docker compose up --build
```

Las cuatro `POSTGRES_*_PASSWORD` (arranque, migrador, app y respaldo) tienen que ser **distintas entre
sí**: `roles antes` rechaza el arranque si dos coinciden, sin mostrar ningún valor (R8, vuelta 2 del
2a). El detalle completo de cada variable está en [Variables de entorno](#variables-de-entorno), más
abajo.

La carpeta de respaldos (`PROPTECH_DIR_RESPALDOS` en `.env`, por defecto
`./datos-respaldos` relativo a `infra/`) hay que crearla **antes** del primer
`docker compose up`: es una carpeta del host (bind mount, no un volumen de
Docker), así sobrevive a un `docker compose down -v`. `PROPTECH_UID` y
`PROPTECH_GID` son el usuario del host (`id -u` / `id -g`), para que esos
archivos queden del dueño real y no de un uid que el host no conoce; sin
ellos, Compose se niega a arrancar nombrando la variable que falta. Las demás
variables de respaldos (`RESPALDO_INTERVALO_SEGUNDOS`, `RESPALDO_CONSERVAR`,
`RESPALDO_LIMITE_SEGUNDOS`) ya traen un valor por defecto en `.env.example`.

Después de que los servicios queden sanos:

- `http://localhost`: la web (marcador técnico, todavía sin pantallas reales).
- `http://localhost/api/salud`: `{"estado":"ok","base":"ok","cola":"ok"}` si la base y la cola
  responden.

Sólo Caddy publica puertos (80 y 443); la base, Redis, la API, la web y el servicio de respaldos
viven en redes internas sin salida a Internet (la web nunca alcanza la base ni Redis, D-051). El
worker es la única excepción: además de esas redes, tiene salida a Internet por la red
`salida_worker` (sin `internal`, sin uso todavía) para los proveedores de email e IA de cambios
posteriores (M18).

**En Windows**: los scripts de `infra/` (incluidos `respaldar.sh`, `restaurar.sh` y los de
`infra/ci/`) son de Bash. Corren en **WSL2** o en **Git Bash**, nunca en PowerShell ni en `cmd`.

### Cómo restaurar un backup

El servicio `respaldos` genera un backup completo al arrancar y después cada
`RESPALDO_INTERVALO_SEGUNDOS` (un día por defecto), en `infra/datos-respaldos/` (o la carpeta que
indique `PROPTECH_DIR_RESPALDOS`), con nombre `proptech-<fecha y hora UTC>.dump`. Para cargar uno en
una base aparte (nunca sobre la base en uso):

```bash
infra/respaldos/restaurar.sh infra/datos-respaldos/proptech-20261014T120000Z.dump
```

Funciona desde cualquier carpeta del repositorio. Sin un segundo argumento, el destino es
`proptech_restauracion`; para usar otro nombre (siempre con el prefijo `proptech_`, nunca la base en
uso):

```bash
infra/respaldos/restaurar.sh infra/datos-respaldos/proptech-20261014T120000Z.dump proptech_mi_prueba
```

### Correr los tests

Backend (requiere [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync --locked
uv run pytest                 # todo, incluida la integración con PostgreSQL real (Docker)
uv run pytest -m "not integracion"   # sin Docker
```

Web (requiere [pnpm](https://pnpm.io/) 12.10.1, `corepack enable` lo resuelve solo):

```bash
cd web
pnpm install --frozen-lockfile
pnpm test
```

Los mismos comandos de test que usa el CI están en `infra/ci/test-backend.sh` y
`infra/ci/test-web.sh`.

## Variables de entorno

Tabla única (D8, tarea 2c): antes vivía (incompleta, y con una fila que ya mentía) en
`knowledge-base/08_arquitectura_propuesta.md`, que ahora enlaza acá. Verificada en los dos sentidos
contra `infra/.env.example` y `infra/compose.yaml` por un test (`tests/infra/test_readme_variables.py`):
falla si falta una fila o si una fila nombra una variable que ya no existe. Nunca un valor real: el
repositorio es público (`.env` y la carpeta de respaldos están en `.gitignore`;
`infra/.env.example` sólo trae placeholders).

| Variable | La usan | Obligatoria/opcional | Default | Propósito |
|---|---|---|---|---|
| `POSTGRES_HOST` | `db` (implícito), API, worker, migraciones | Obligatoria | Compose la fija en `db` | Host de PostgreSQL |
| `POSTGRES_PORT` | API, worker, migraciones | Opcional | 5432 | Puerto de PostgreSQL |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `db`, migraciones (`roles.py antes`/`despues`) | Obligatoria | sin default | El rol de arranque: superusuario de la imagen oficial. Crea y repara los otros tres roles, único dueño de `auditoria`; ningún servicio PERMANENTE lo recibe (R8). **No** es el que usan la API ni el worker (ver `POSTGRES_APP_*`, abajo) |
| `POSTGRES_DB` | `db`, API, worker, migraciones | Obligatoria | sin default | Nombre de la base |
| `POSTGRES_MIGRADOR_USER` / `POSTGRES_MIGRADOR_PASSWORD` | Alembic (migraciones) | Obligatoria | sin default | `proptech_migrador`, dueño de las tablas de dominio; sin `BYPASSRLS` |
| `POSTGRES_APP_USER` / `POSTGRES_APP_PASSWORD` | API, worker | Obligatoria; `POSTGRES_APP_USER` tiene que ser exactamente `proptech_app` (`roles antes` lo rechaza si no, V3-14) | sin default | `proptech_app`, sin superusuario ni `BYPASSRLS`; sujeta a Row-Level Security igual que cualquier cliente. Las migraciones (`ayudas_rls.py`) tienen ese nombre escrito a mano en sus `GRANT`: un nombre distinto crearía un rol sin esos permisos |
| `POSTGRES_RESPALDO_USER` / `POSTGRES_RESPALDO_PASSWORD` | `respaldos`, `restaurar.sh` | Obligatoria | sin default | `proptech_respaldo`, con `BYPASSRLS` y `pg_read_all_data`, sin superusuario; sólo para `pg_dump`/`pg_restore` |
| `REDIS_HOST` | API, worker | Fijada por Compose | `redis` | Host de Redis |
| `REDIS_PORT` | API, worker | Opcional | 6379 | Puerto de Redis |
| `REDIS_PASSWORD` | `redis`, API, worker | Obligatoria | sin default | Contraseña de Redis (`SecretStr`; `redis-server` arranca con `--requirepass`) |
| `PROPTECH_PARAMETROS` | API, worker | Obligatoria (el archivo tiene que existir y ser legible) | Compose la fija en `/app/config/parametros.yaml` | Ruta al archivo de parámetros del sistema |
| `FORWARDED_ALLOW_IPS` | API (uvicorn, `--proxy-headers`) | Fijada por Compose, no por `.env` | `172.28.0.254` (la IP fija de `caddy` en la red `aplicacion`, D17) | Única IP de la que la API acepta encabezados `X-Forwarded-*` |
| `PROPTECH_SITIO` | `caddy` | Obligatoria | sin default | Dominio o URL que sirve Caddy (`http://localhost` en local; el dominio real en producción) |
| `PROPTECH_URL_API_INTERNA` | `web` | Fijada por Compose | `http://api:8000` | URL interna con la que el servidor de Next llama a la API; nunca la ve el navegador |
| `DB_POOL_PRE_PING` | API, worker | Opcional | `true` | Verifica la conexión del pool antes de usarla |
| `DB_POOL_SIZE` | API, worker | Opcional (1 a 50) | 5 | Tamaño del pool del engine de SQLAlchemy |
| `DB_POOL_RECYCLE_S` | API, worker | Opcional (60 a 86400) | 1800 | Segundos antes de reciclar una conexión del pool |
| `DB_POOL_TIMEOUT_S` | API, worker | Opcional (1 a 60) | 5 | Segundos de espera por una conexión libre del pool |
| `DB_CONNECT_TIMEOUT_S` | API, worker | Opcional (1 a 30) | 2 | Segundos de espera al establecer la conexión a PostgreSQL |
| `PGHOST` | `respaldos` | Fijada por Compose, no configurable | `db` | Convención de libpq que usan `pg_dump`/`pg_restore`; misma información que `POSTGRES_HOST` |
| `PGPORT` | `respaldos` | Fijada por Compose, no configurable | 5432 | Convención de libpq; misma información que `POSTGRES_PORT` |
| `HOME` | `respaldos` | Fijada por Compose, no configurable | `/tmp` | `HOME` dentro del contenedor, para que `pg_dump`/`pg_restore` tengan dónde escribir su configuración |
| `PROPTECH_DIR_RESPALDOS` | `respaldos` | Obligatoria | `./datos-respaldos` en `.env.example` (relativo a `infra/`) | Carpeta del host (bind mount) donde se guardan los `.dump`; sobrevive a `docker compose down -v` |
| `PROPTECH_UID` | `respaldos` | Obligatoria | sin default | UID del usuario del host, para que los backups no queden de un uid que el host no conoce |
| `PROPTECH_GID` | `respaldos` | Obligatoria | sin default | GID del usuario del host, gemelo de `PROPTECH_UID` |
| `RESPALDO_INTERVALO_SEGUNDOS` | `respaldos` | Opcional (60 a 604800) | 86400 (diario) | Cada cuánto corre un backup, además del de arranque |
| `RESPALDO_CONSERVAR` | `respaldos` | Opcional (1 a 365) | 14 | Cuántos backups se retienen antes de borrar los más viejos |
| `RESPALDO_LIMITE_SEGUNDOS` | `respaldos` | Opcional (5 a 86400, menor que el intervalo) | 1800 | Corta el volcado (`pg_dump`) si tarda más que este límite |

Las cuatro `POSTGRES_*_PASSWORD` (arranque, migrador, app y respaldo) tienen que ser **distintas
entre sí** (R8, vuelta 2 del 2a): `roles antes` rechaza el arranque si dos coinciden, sin mostrar
ningún valor.

Todas las que llegan como texto desde el entorno (enteros incluidos) se validan con coincidencia
completa y sólo dígitos ASCII, sin ceros a la izquierda ni signo (L-002, L-008): un valor con
espacios, una coma de miles o una parte decimal exacta se rechaza en vez de truncarse en silencio.

## Cómo se trabaja

1. Nada se programa sin estar escrito antes en `knowledge-base/` y en un cambio de OPSX.
2. El núcleo financiero se construye con TDD: cada regla de
   [`05_reglas_de_negocio.md`](knowledge-base/05_reglas_de_negocio.md) tiene sus tests antes que el código.
3. Si algo contradice la base de conocimiento, se para y se decide: una decisión nueva en
   `09_decisiones_y_supuestos.md`, nunca una edición de una vieja.

## Trabajar con Active Stack

Este repositorio ya tiene su base de conocimiento, su roadmap y sus reglas escritos a mano. Si vas a
trabajar acá con Active Stack v1 (Alberto) o con el método propio del proyecto (Juani), empezá por
[`AGENTS.md`](AGENTS.md): tiene el stack, qué leer antes de codear, las reglas duras (incluido qué
herramientas de fundación **no correr nunca** en este repo) y el flujo de trabajo de los dos ciclos.

El instalador de Active Stack v1 deja la última versión de OpenSpec. Este repo usa la 1.13.0 (las
skills de `.claude/skills/` se generaron con ella): después de instalar, fijala con
`npm install -g @fission-ai/openspec@1.13.0` y no corras `openspec update`.

## Stack

Next.js · FastAPI · PostgreSQL con Row-Level Security · Redis con worker · Caddy · Docker en un VPS.
