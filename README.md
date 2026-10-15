# PropTech

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados) en
Mendoza: liquidación de expensas, cuenta corriente de cada unidad, registro de pagos y portal del
vecino. Proyecto de Alberto Cortez (también conocido como **koris**) y Juan Ignacio Sarmiento.

## Estado

Base de conocimiento cerrada y congelada para el primer hito (octubre de 2026), con preguntas abiertas
que se responden antes de cada cambio. El MVP arranca por **edificios**. Construidos y
archivados: **1a `infraestructura-base`** (el sistema completo arranca con un comando y el CI corre en
cada push), **1b `arranque-del-sistema`** (configuración, tipo `Dinero` exacto, parámetros y
edificio de ejemplo validados) y **1c `cola-logs-y-respaldos`** (Redis, worker con reintentos e
idempotencia, logs en JSON y número de seguimiento de punta a punta; cerrado con OK con deuda
anotada). Propuesto: **1d `respaldos-y-restauracion`** (el próximo, espera la aprobación escrita de
uno de los dos socios). Todavía no hay
liquidación ni cuenta corriente: llegan en los cambios 4 a 7 del roadmap
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

Sólo Caddy publica puertos (80 y 443); la base, Redis, la API, el worker y el servicio de respaldos
viven en redes internas sin salida (la web nunca alcanza la base ni Redis, D-051).

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
