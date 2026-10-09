Orden estricto. En cada par, la tarea de test (o de chequeo que falla) va primero y hay que **ver la
falla** antes de pasar a la siguiente. Versiones, nombres de archivos y estructura salen de
`design.md` (D1 a D11); no se elige nada nuevo sin anotarlo como desvío. Ninguna regla de negocio
(R01 a R16) se toca en este cambio.

## 1. Andamiaje del backend

- [x] 1.1 Escribir `backend/tests/unitarios/test_paquetes.py`, que importa `proptech_core`, `proptech_api` y `proptech_worker`. Verificación: `uv run pytest` (o `python -m pytest` si todavía no hay proyecto) falla por import.
- [x] 1.2 Crear `backend/pyproject.toml` (hatchling, tres paquetes, `requires-python = ">=3.14,<3.15"`, dependencias y versiones de D4), `.python-version`, los tres paquetes con `__init__.py` y `py.typed`, y `uv.lock`. Verificación: `uv sync --locked` termina bien y el test de 1.1 pasa.
- [x] 1.3 Configurar Ruff (reglas y largo de D2), mypy estricto y pytest (`--strict-markers`, `xfail_strict = true`, marcador `integracion` declarado) en `pyproject.toml`. Verificación: `ruff check`, `ruff format --check` y `mypy` pasan; un archivo temporal mal formateado hace fallar `ruff format --check` (se muestra la salida y se borra el archivo).

## 2. Configuración y conexión a la base

- [x] 2.1 Tests unitarios de `Configuracion`: sin `POSTGRES_PASSWORD` falla con un error que nombra la variable y no imprime ningún valor; la URL armada escapa una contraseña con `@`, `:` y `/` y se puede volver a parsear con los mismos datos. Verificación: fallan porque el módulo no existe.
- [x] 2.2 Implementar `proptech_core/compartido/configuracion.py` (pydantic-settings, variables `POSTGRES_*`) y `base_de_datos.py` (`URL.create`, engine, Base declarativa). Verificación: tests de 2.1 en verde, `mypy` y `ruff` limpios.

## 3. Endpoint de salud (unitario)

- [x] 3.1 Tests unitarios de `GET /api/salud` con el verificador reemplazado por `dependency_overrides`: base ok responde 200 `{"estado":"ok","base":"ok"}`; base caída responde 503 `{"estado":"degradado","base":"sin_conexion"}`; un verificador que lanza una excepción con el texto `postgresql://usuario:secreto@host/db` responde 503 y el cuerpo no contiene `secreto` ni `postgresql://`; `GET /salud` sin prefijo responde 404. Verificación: fallan porque la app no existe.
- [x] 3.2 Implementar `proptech_api/app.py` (router bajo `/api`) y `proptech_api/salud.py` según D11. Verificación: tests de 3.1 en verde.

## 4. PostgreSQL real y migraciones

- [x] 4.1 Tests en `backend/tests/infra/`: (a) toda imagen de `infra/compose.yaml` y de los `FROM` de los Dockerfiles tiene etiqueta con versión de parche y ninguna es `latest` ni va sin etiqueta; (b) la imagen que usa el fixture de testcontainers es la del servicio `db` de Compose, y si difieren el test nombra las dos. Verificación: fallan porque `infra/compose.yaml` no existe.
- [x] 4.2 Crear `infra/compose.yaml` con sólo el servicio `db` (`postgres:18.6-trixie`, volumen en `/var/lib/postgresql`, red `interna` con `internal: true`, sin `ports:`, healthcheck `pg_isready`, variables con `${VAR:?}`), `infra/.env.example` con las variables `POSTGRES_*` y valores de ejemplo, y el fixture de `backend/tests/conftest.py` que lee la imagen de Compose y levanta el contenedor con testcontainers. Verificación: tests de 4.1 en verde.
- [x] 4.3 Tests de integración (marcador `integracion`): `alembic upgrade head` sobre la base vacía deja registrada la revisión `0001`; `alembic downgrade base` después deja la base sin revisión; el verificador real de salud devuelve ok contra el contenedor y "sin conexión" contra un puerto donde no escucha nadie, en menos de 5 segundos. Verificación: fallan porque Alembic no está configurado.
- [x] 4.4 Crear `alembic.ini` (sin URL adentro), `migraciones/env.py` (URL desde `Configuracion`), `script.py.mako` y `versions/0001_inicial.py` con `upgrade` y `downgrade` vacíos. Verificación: tests de 4.3 en verde; `uv run pytest` completo en verde.

## 5. Imagen de la API

- [x] 5.1 Tests en `backend/tests/infra/` para cada Dockerfile del repo: la última etapa declara un `USER` distinto de root, y el `.dockerignore` de su contexto excluye `.env` y `.env.*`. Verificación: fallan porque no hay Dockerfile.
- [x] 5.2 Escribir `backend/Dockerfile` (multi-etapa, uv `0.12.24` copiado sólo en el build, final `python:3.14.8-slim-trixie` sin uv, usuario no root, comando `uvicorn proptech_api.app:app --host 0.0.0.0 --port 8000` sin `--forwarded-allow-ips="*"`) y `backend/.dockerignore`. Verificación: tests de 5.1 en verde para el backend; `docker build` termina bien y `docker run --rm --entrypoint id <imagen> -u` no imprime 0.

## 6. Web

- [x] 6.1 Crear `web/package.json` (versiones exactas de D2 a D4, `packageManager: pnpm@12.10.1`), `pnpm-lock.yaml`, `.node-version`, `tsconfig.json` estricto, `biome.json`, `vitest.config.ts` (entorno node), `src/app/layout.tsx`, y escribir `src/app/page.test.tsx`, que renderiza la página con `react-dom/server` y espera el texto "PropTech". Verificación: `pnpm vitest run` falla porque la página no existe.
- [x] 6.2 Escribir `src/app/page.tsx` como marcador técnico sin diseño. Verificación: el test de 6.1 pasa; `pnpm biome ci` y `pnpm tsc --noEmit` pasan; un archivo temporal mal formateado hace fallar `biome ci` (se muestra la salida y se borra).
- [x] 6.3 Escribir `web/next.config.ts` (`output: "standalone"`), `web/Dockerfile` (multi-etapa, `node:24.21.0-alpine`, pnpm con `--frozen-lockfile`, usuario no root) y `web/.dockerignore`. Verificación: los tests de 5.1 pasan también para la web; `docker build` termina bien y `docker run --rm --entrypoint id <imagen> -u` no imprime 0.

## 7. Compose completo y Caddy

- [x] 7.1 Tests estáticos en `backend/tests/infra/` sobre `infra/compose.yaml`: el único servicio con `ports:` es `caddy`, con 80 y 443; `db`, `api`, `web` y `migraciones` no tienen `ports:`; `db` está sólo en la red `interna` y esa red tiene `internal: true`; `migraciones` usa la misma imagen que `api` con comando `alembic upgrade head` y `restart: "no"`; `api` depende de `migraciones` con `service_completed_successfully`; `POSTGRES_PASSWORD` se interpola con `:?`. Verificación: fallan porque Compose sólo tiene `db`.
- [x] 7.2 Escribir `infra/ci/humo.sh` según D9 (levanta con `--wait`; verifica salud 200 por Caddy, puertos publicados sólo de Caddy, conexión a `localhost:5432` rechazada, `id -u` distinto de 0 en `api` y `web`, imágenes sin `.env` con señuelos creados antes del build, `GET /` 200 con HTML; después detiene `db` y verifica 503 con `{"estado":"degradado","base":"sin_conexion"}`; `trap` con `docker compose down -v` y borrado de señuelos). Verificación: correrlo falla porque el stack no está completo.
- [x] 7.3 Completar `infra/compose.yaml` (servicios `migraciones`, `api`, `web`, `caddy`, redes `borde` e `interna`, healthchecks de D9), `infra/Caddyfile` (sitio desde `PROPTECH_SITIO`, `/api/*` a la API sin quitar el prefijo, resto a la web, sin encabezado `Server`) y `infra/.env.example` completo. Verificación: tests de 7.1 en verde; `infra/ci/humo.sh` termina en 0; en `infra/` sin `.env`, `docker compose config` falla y el mensaje nombra la variable faltante.
- [x] 7.4 Verificar que si `migraciones` falla la API no arranca: con una revisión rota temporal (o una contraseña errónea sólo para ese servicio), `docker compose up` deja a `api` sin arrancar. Se muestra la salida y se deshace el cambio temporal. Verificación: la salida de `docker compose ps -a` lo muestra.

## 8. Comandos de test únicos y canario

- [x] 8.1 Escribir `infra/ci/test-backend.sh` (pytest completo, sin tragar el código de salida) y `infra/ci/test-web.sh` (`vitest run`), con `set -euo pipefail`. Verificación: los dos terminan en 0 en el árbol actual; con un test roto temporal terminan distinto de 0.
- [x] 8.2 Escribir `infra/ci/canario.sh <backend|web>` según D7. Verificación: (a) corrido normal termina en 0 y `git status --porcelain` no muestra el test roto; (b) con `|| true` agregado temporalmente al script de test correspondiente, el canario termina distinto de 0; se deshace el cambio temporal. Las dos salidas se muestran.

## 9. Búsqueda de secretos

- [x] 9.1 Crear `.gitleaks.toml` mínimo y correr gitleaks 8.30.1 por Docker sobre el historial y sobre el árbol de trabajo. Verificación: 0 hallazgos en el repo; un archivo temporal sin versionar con una clave privada inventada es detectado por `gitleaks dir` (se muestra la salida y se borra el archivo sin commitearlo); `infra/.env.example` no genera hallazgos.

## 10. Workflow de CI

- [x] 10.1 Tests en `backend/tests/infra/` sobre `.github/workflows/ci.yml`: existen los jobs `backend`, `web`, `humo` y `secretos`; cada `uses:` está fijado a un SHA de 40 caracteres; no aparece `continue-on-error` ni `|| true`; el disparador incluye `push` a `main` y `workflow_dispatch`; `permissions` es `contents: read`; los pasos de test llaman a `infra/ci/test-*.sh` y existen los pasos del canario. Verificación: fallan porque el workflow no existe.
- [x] 10.2 Escribir `.github/workflows/ci.yml` según D6, con los SHA de las etiquetas de D6 resueltos y la etiqueta en un comentario. Verificación: tests de 10.1 en verde y `actionlint` (por su imagen de Docker, versión fija) sin errores.

## 11. README y verificación final

- [x] 11.1 Escribir en el `README.md` raíz la sección "Cómo levantarlo" (requisitos: Docker con Compose; `cp infra/.env.example infra/.env`; `cd infra && docker compose up --build`; abrir `http://localhost` y `http://localhost/api/salud`; cómo correr los tests con uv y pnpm, y cómo saltear los de integración sin Docker) y actualizar la tabla de estructura (sacar "próximamente" de `web/`, `backend/` e `infra/`). Verificación: en una copia limpia del árbol (`git ls-files -co --exclude-standard` copiado a un directorio temporal, sin `.env` ni `node_modules`), siguiendo sólo el README, `docker compose up --build -d --wait` levanta todo y `curl -fsS http://localhost/api/salud` devuelve `{"estado":"ok","base":"ok"}`.
- [x] 11.2 Corrida completa con evidencia, en este orden y mostrando comando y salida de cada uno: `ruff check`, `ruff format --check`, `mypy`, `infra/ci/test-backend.sh`, `infra/ci/canario.sh backend`, `pnpm biome ci`, `pnpm tsc --noEmit`, `infra/ci/test-web.sh`, `infra/ci/canario.sh web`, `infra/ci/humo.sh`, gitleaks. Todo en 0 salvo lo que el canario espera que falle. El verde real de GitHub Actions lo confirma el orquestador después del push al archivar; si sale rojo, el cambio se reabre.
