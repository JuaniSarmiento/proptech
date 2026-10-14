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
Juani). Todavía no hay
liquidación ni cuenta corriente: llegan en los cambios 4 a 7 del roadmap
([`conocimiento/roadmap.md`](conocimiento/roadmap.md)).

## Estructura

| Carpeta | Qué tiene |
|---|---|
| [`conocimiento/`](conocimiento/) | **La base de conocimiento del MVP**: objetivo, historias de usuario, reglas de negocio, decisiones, glosario y fases. Es la fuente de verdad: empezá por su [README](conocimiento/README.md) |
| `config/` | `parametros.yaml` (valores con que arranca cada edificio) y `semilla/` (edificio de ejemplo) |
| `openspec/` | Cambios del ciclo OPSX |
| `web/` | Frontend en Next.js |
| `backend/` | API en FastAPI, worker y dominio compartido (`proptech_core`, `proptech_api`, `proptech_worker`) |
| `infra/` | Docker Compose, Caddy y los scripts de CI |

La estructura completa y su porqué están en la decisión D-040 de
[`conocimiento/decisiones.md`](conocimiento/decisiones.md).

## Cómo levantarlo

Requisitos: Docker con Compose (`docker compose version`).

```bash
cp infra/.env.example infra/.env   # completar POSTGRES_PASSWORD con un valor propio
cd infra
docker compose up --build
```

Después de que los servicios queden sanos:

- `http://localhost`: la web (marcador técnico, todavía sin pantallas reales).
- `http://localhost/api/salud`: `{"estado":"ok","base":"ok"}` si la base responde.

Sólo Caddy publica puertos (80 y 443); la base, la API y la web viven en una red interna.

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

1. Nada se programa sin estar escrito antes en `conocimiento/` y en un cambio de OPSX.
2. El núcleo financiero se construye con TDD: cada regla de
   [`reglas-de-negocio.md`](conocimiento/reglas-de-negocio.md) tiene sus tests antes que el código.
3. Si algo contradice la base de conocimiento, se para y se decide: una decisión nueva en
   `decisiones.md`, nunca una edición de una vieja.

## Stack

Next.js · FastAPI · PostgreSQL con Row-Level Security · Redis con worker · Caddy · Docker en un VPS.
