## Context

El repositorio tiene `conocimiento/`, `openspec/` y `especificacion/` (ignorada por git), y ningún
código. El motivo está en `proposal.md` (Why) y los requisitos en `specs/entorno-de-ejecucion` y
`specs/integracion-continua`. Este documento resuelve el "Decidir en el design" de la ficha 1a y todo
lo que el constructor necesita para no tener que elegir nada por su cuenta.

Restricciones que condicionan todo:

- Repositorio **público**: nada de secretos en código, tests, imágenes ni logs del CI.
- Criterio de costo cero (D-043): GitHub Actions gratis para repos públicos, imágenes públicas.
- Arquitectura de Alberto como referencia: Caddy única puerta, base en red interna, Compose en un VPS,
  migraciones como trabajo aparte. El `request_id` es de 1b, no de acá.
- Entorno de Juani (verificado el 09/10/2026): uv 0.11.8, Node 22.22.2, pnpm 12.6.0, Docker 29.1.3,
  Compose 2.40.3. Python del sistema 3.12.3 (uv instala el que pida el proyecto).

Las versiones de abajo se consultaron el 09/10/2026 contra Docker Hub, PyPI, npm y la API de
releases de GitHub. Son las vigentes ese día.

## Goals / Non-Goals

**Goals:**

- Que cada elección de herramienta y versión quede tomada acá, con su alternativa descartada.
- Que el mismo comando de test corra igual en la máquina de Juani y en el CI.
- Que el "Terminado cuando" de la ficha sea verificable por comandos, no por inspección.

**Non-Goals:**

- Diseñar el despliegue al VPS (dominio, certificados reales, actualización sin corte).
- Elegir la librería de logs o el formato del `request_id` (1b).
- Fijar el modelo de usuarios de base para RLS (2). En 1a la API se conecta con el usuario que crea
  la imagen de PostgreSQL; el cambio 2 introduce el usuario de aplicación sin privilegios de dueño.

## Decisions

### D1 · Versiones fijadas de cada imagen

| Servicio | Imagen | Por qué esta variante |
|---|---|---|
| Base | `postgres:18.6-trixie` | PostgreSQL 18 es la versión mayor vigente. Debian (trixie) en vez de Alpine: musl ordena texto distinto que glibc y no queremos que el orden de un `ORDER BY` cambie entre la imagen y un servicio administrado futuro |
| Proxy | `caddy:2.11.7-alpine` | Última de la línea 2.11 |
| API y migraciones | `python:3.14.8-slim-trixie` | Ver D3. La API y el trabajo de migraciones son la **misma imagen** con distinto comando (igual que en el ejemplo de Alberto) |
| Web | `node:24.21.0-alpine` | Node 24 es la LTS activa. Next.js en modo `standalone` no necesita glibc |
| uv dentro de la imagen | `ghcr.io/astral-sh/uv:0.12.24` | Se copia sólo el binario (`COPY --from=`) en la etapa de build; no queda en la imagen final |

Todas con versión de parche exacta; ninguna con `latest` (requisito "Versiones de herramientas
fijadas", con su test). No se fija además el digest `@sha256:`: con Juani solo y sin despliegue
todavía, actualizar a mano un digest por cada parche de seguridad cuesta más de lo que protege.
Se reconsidera cuando haya producción.

**Gotcha de PostgreSQL 18 que hay que respetar**: desde la 18 la imagen oficial guarda los datos en
`/var/lib/postgresql/18/docker` y espera el volumen montado en `/var/lib/postgresql`, no en
`/var/lib/postgresql/data` como hasta la 17. Montarlo en el lugar viejo hace que los datos queden
fuera del volumen y se pierdan al recrear el contenedor.

*Descartado*: `postgres:18-alpine` (colaciones de musl, ver arriba); etiquetas flotantes como
`postgres:18` o `caddy:2` (un rebuild trae otra versión sin que nadie lo decida).

### D2 · Lint, formato y tipos

| Lado | Lint y formato | Tipos |
|---|---|---|
| Python | **Ruff 0.16.10** (`ruff check` y `ruff format --check`), reglas `E, W, F, I, B, UP, S, RUF`, largo de línea 100, `target-version = "py314"` | **mypy 2.4.0** en modo `strict` sobre `src/` y `tests/` |
| TypeScript | **Biome 2.5.15** (`biome ci`), reglas recomendadas más los dominios `react` y `next` | **TypeScript 6.0.3**, `tsc --noEmit` con `strict` y `noUncheckedIndexedAccess` |

*Por qué*: una sola herramienta rápida por lado para lint y formato, sin plugins que se desalineen.
mypy en estricto ahora, con el código vacío, cuesta cero; agregarlo con diez módulos escritos cuesta
una semana (y Juani pide tipado estricto).

*Descartado*:
- Black + isort + flake8: tres herramientas para lo que Ruff hace en una.
- Pyright: necesita Node en el lado de Python; mypy es el estándar de la línea de comandos.
- ESLint + Prettier con `eslint-config-next`: es lo que trae Next por defecto y tiene más reglas
  propias de Next, pero son dos herramientas y dos configuraciones. Costo aceptado: Biome cubre menos
  reglas específicas de Next que `eslint-config-next`.
- TypeScript 7.0.2: es la reescritura nativa y no expone todavía la misma API programática que usan
  las herramientas del ecosistema (Next la usa para su chequeo de tipos). 6.0 es la última línea
  sobre la API conocida. Se revisa cuando Next declare soporte.

### D3 · Versiones de lenguaje y gestores de paquetes

- **Python 3.14** (`.python-version` en `backend/`), gestionado por **uv** con `uv.lock` versionado.
  `requires-python = ">=3.14,<3.15"`.
- **Node 24.21.0** (`web/.node-version`), gestor **pnpm 12.10.1** fijado en el campo
  `packageManager` de `web/package.json`, con `pnpm-lock.yaml` versionado e instalación
  `--frozen-lockfile` en CI e imagen.

*Descartado*:
- Python 3.13: su ventana de correcciones de bugs se cierra en octubre de 2026, el mismo mes en que
  arranca el proyecto. 3.14 ya va por el parche 8.
- Node 22: pasa a mantenimiento; 24 es la LTS activa hasta 2028. Juani tiene 22 instalado: el README
  indica cómo tener 24 (no hace falta para `docker compose up`, sólo para correr los tests de la web
  fuera de Docker).
- Poetry o pip-tools: uv es lo que Juani ya usa, resuelve más rápido y además instala Python.
- npm o bun: pnpm es lo que Juani tiene instalado y su instalación estricta evita depender de
  paquetes no declarados.

### D4 · Dependencias de ejecución

| Paquete | Versión |
|---|---|
| fastapi | 0.143.0 |
| uvicorn | 0.54.0 |
| sqlalchemy | 2.1.4 |
| alembic | 1.20.0 |
| psycopg[binary] | 3.3.6 |
| pydantic-settings | 2.15.0 |
| next | 16.4.0 |
| react, react-dom | 19.3.0 |

De desarrollo: pytest 9.1.1, httpx 0.28.1 (para el `TestClient`), testcontainers[postgres] 4.15.0,
pyyaml (para los tests que leen `compose.yaml`), vitest 5.0.3, @types/react y @types/node acordes.

En `pyproject.toml` se fijan con `==` las herramientas de lint y test (para que el CI no cambie solo)
y con `>=x,<x+1` de mayor las de ejecución, con el `uv.lock` como fuente exacta. En `package.json`,
todas con versión exacta (sin `^`).

SQLAlchemy **sincrónico** con psycopg 3: alcanza para el volumen del MVP (un edificio de 40 unidades),
el `SET LOCAL` de RLS funciona igual y los tests son más simples. *Descartado*: SQLAlchemy async con
asyncpg, que suma complejidad sin una carga que lo justifique. Si el cambio 2 o el 4 lo necesitan, lo
deciden ellos.

### D5 · Cómo corre PostgreSQL real en los tests de integración (y en el CI)

**Testcontainers** levanta un PostgreSQL efímero por sesión de pytest, con la **misma imagen** que
declara `infra/compose.yaml`. La imagen no se escribe dos veces: el fixture la lee de
`infra/compose.yaml`, y un test aparte verifica que las dos coincidan (requisito "Versión de
PostgreSQL desalineada").

El mecanismo es idéntico en la máquina de Juani y en el runner `ubuntu-24.04` de GitHub Actions, que
ya trae Docker. Los tests de integración llevan el marcador `integracion`; sin Docker se pueden
saltear con `-m "not integracion"`, pero el CI corre todo.

*Descartado*:
- `services: postgres` de GitHub Actions: funciona sólo en el CI; en local habría que levantar la
  base de otra forma y publicar su puerto, que es justo lo que este cambio prohíbe.
- Correr los tests dentro de Compose contra el servicio `db`: acopla la suite al stack entero y la
  hace lenta para el ciclo de TDD.
- SQLite en memoria: no es PostgreSQL; RLS, `NUMERIC(14,2)` y los bloqueos no existen ahí. Contradice
  "integración (PostgreSQL real en Docker)" de D-021.

### D6 · Proveedor de CI y forma del workflow

**GitHub Actions**, un solo workflow `.github/workflows/ci.yml`, disparado por `push` a `main` y por
`workflow_dispatch`. Cuatro jobs en paralelo sobre `ubuntu-24.04`:

| Job | Qué corre |
|---|---|
| `backend` | `uv sync --locked`, `ruff check`, `ruff format --check`, `mypy`, `infra/ci/test-backend.sh` (pytest con integración), canario de backend |
| `web` | `pnpm install --frozen-lockfile`, `biome ci`, `tsc --noEmit`, `infra/ci/test-web.sh` (vitest), canario de web |
| `humo` | `infra/ci/humo.sh` (ver D9) |
| `secretos` | gitleaks 8.30.1 por su imagen de Docker, con `fetch-depth: 0` para ver todo el historial |

Acciones fijadas **por SHA de commit**, con la etiqueta en un comentario: `actions/checkout` v7.0.1,
`actions/setup-node` v7.1.0, `astral-sh/setup-uv` v10.2.0, `pnpm/action-setup` v6.1.0. El
constructor resuelve los SHA de esas etiquetas. Permisos del workflow: `contents: read` y nada más.

*Descartado*: GitLab CI o CircleCI (el repo vive en GitHub); fijar acciones por etiqueta (una
etiqueta se puede mover, un SHA no); `gitleaks-action` (pide licencia para organizaciones y agrega
una dependencia más; la imagen oficial hace lo mismo); trufflehog (más pesado para el mismo fin).

### D7 · El canario: cómo se prueba que el CI falla con un test roto

La ficha pide "el CI falla a propósito con un test roto". Como se trabaja sin ramas y sobre `main`,
pushear un test roto ensuciaría el historial y dejaría `main` en rojo. En su lugar:

- Los comandos de test viven en un solo lugar: `infra/ci/test-backend.sh` y `infra/ci/test-web.sh`.
  Los usan el paso normal, el canario y Juani en su máquina.
- `infra/ci/canario.sh <backend|web>` escribe un test que falla a propósito
  (`backend/tests/unitarios/test_canario_roto.py` o `web/src/canario-roto.test.ts`), corre el mismo
  script de test, **exige código de salida distinto de 0**, y borra el archivo con un `trap` aunque
  algo falle. Si el script de test devuelve 0 con el test roto, el canario sale con error y el job se
  pone rojo.

Así cada corrida del CI demuestra que un test roto lo pone en rojo, y alguien que agregue
`|| true` o un `continue-on-error` al paso de tests rompe el canario. Pytest ya devuelve 5 cuando no
recolecta tests y vitest devuelve 1 cuando no encuentra ninguno: los dos cuentan como falla sin
configuración extra (requisito "Suite vacía"). Pytest corre con `--strict-markers` y
`xfail_strict = true`.

*Descartado*: pushear un commit con un test roto y revertirlo (ensucia `main`, que es la única rama);
confiar en la configuración sin una prueba que corra cada vez.

### D8 · Red, puertos y Caddy

```
Internet ──► :80/:443 ──► caddy ──┬── /api/* ──► api:8000 ──► db:5432
            (red borde)           └── resto ───► web:3000
                                  (red interna, internal: true)
```

- Dos redes: `borde` (puente normal, sólo Caddy, para que sus puertos publicados funcionen) e
  `interna` con `internal: true` (Caddy, web, api, migraciones y db). Ningún servicio salvo Caddy
  tiene `ports:`; los demás sólo `expose:`.
- Consecuencia buscada: la base, la API y la web no tienen salida a Internet. Cuando el worker
  necesite hablar con el proveedor de email o de IA (cambios 13 y 14), se le agrega a él solo una red
  con salida. Se anota como riesgo abajo.
- Caddyfile en `infra/Caddyfile`: la dirección del sitio sale de la variable `PROPTECH_SITIO`
  (`http://localhost` en `.env.example`, para que en local no haya certificados autofirmados que
  aceptar; en producción será el dominio y Caddy saca el certificado solo). `handle /api/*` hace
  `reverse_proxy api:8000` **sin quitar el prefijo**: la API monta sus rutas bajo `/api`. Todo lo
  demás va a `web:3000`. Se quita el encabezado `Server`.
- Uvicorn corre sin `--forwarded-allow-ips="*"`: confiar a ciegas en `X-Forwarded-For` es uno de los
  errores que nombra el documento de Alberto. Hoy nada lee la IP del cliente; cuando algo la
  necesite (límite de pedidos), se configura con la IP de Caddy.

*Descartado*: Nginx (D-043); una sola red con puertos sin publicar (la base quedaría con salida a
Internet); quitar el prefijo `/api` en Caddy (la API tendría que saber que vive detrás de un prefijo
vía `root_path`, otra cosa más que configurar y que el OpenAPI muestre bien).

### D9 · Compose, migraciones y la prueba de humo

- Archivo `infra/compose.yaml`; se corre **desde `infra/`** con `docker compose up --build`, y lee
  `infra/.env`. Así se respeta D-040 (todo el despliegue en `infra/`) y el comando sigue siendo
  `docker compose up`. *Descartado*: un `compose.yaml` en la raíz con `include:` (la resolución del
  `.env` entre el archivo raíz y el incluido es confusa y es un lugar más donde equivocarse).
- Variables obligatorias con `${VAR:?mensaje}`, para que Compose se niegue a arrancar si faltan
  (requisito "Falta el archivo de entorno"). La configuración de la base entra **por partes**
  (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`), las mismas
  variables que usa la imagen de PostgreSQL, y la API arma la URL con `sqlalchemy.URL.create`, que
  escapa caracteres especiales de la contraseña. Una sola fuente de configuración (H45).
- Servicio `migraciones`: misma imagen que `api`, comando `alembic upgrade head`, `restart: "no"`,
  `depends_on: db: condition: service_healthy`. La `api` depende de
  `migraciones: condition: service_completed_successfully` y de `db` saludable. *Descartado*: correr
  `alembic upgrade` al arrancar la API (con dos réplicas compiten, y una migración fallida deja la API
  reiniciando en bucle).
- Healthchecks: `db` con `pg_isready`; `api` con un `python -c` que pide `/api/salud` con urllib (sin
  instalar curl en la imagen); `web` con `node -e` y `fetch`; `caddy` depende de `api` y `web`
  saludables.
- Volumen `datos_postgres` montado en `/var/lib/postgresql` (gotcha de D1).
- `infra/ci/humo.sh`: `docker compose up -d --build --wait`, luego verifica (1) `GET
  http://localhost/api/salud` responde 200 con `{"estado":"ok","base":"ok"}`, (2) que en
  `docker compose ps --format json` el único servicio con puertos publicados es `caddy` con 80 y 443,
  (3) que una conexión TCP a `localhost:5432` es rechazada, (4) que `id -u` dentro de `api` y de
  `web` no es 0, (5) que las imágenes construidas no contienen ningún `.env` (el script crea un
  `.env` señuelo en `backend/` y `web/` antes de construir para probar el `.dockerignore`), y (6)
  que `GET /` responde 200 con HTML. Siempre termina con `docker compose down -v` en un `trap`.
  En el CI genera su propio `infra/.env` desde `.env.example`.

### D10 · Estructura de carpetas que crea el cambio

```
.
├── .github/workflows/ci.yml
├── .gitleaks.toml                     # vacío salvo lo necesario; sin allowlists amplias
├── config/.gitkeep                    # parametros.yaml llega en 1b
├── backend/
│   ├── .dockerignore                  # excluye .env*, .venv, tests, cachés
│   ├── .python-version                # 3.14
│   ├── Dockerfile                     # multi-etapa: build con uv, final slim sin uv, usuario no root
│   ├── alembic.ini
│   ├── pyproject.toml                 # un solo proyecto, hatchling, tres paquetes
│   ├── uv.lock
│   ├── migraciones/
│   │   ├── env.py                     # URL desde Configuracion, nunca desde alembic.ini
│   │   ├── script.py.mako
│   │   └── versions/0001_inicial.py   # upgrade y downgrade vacíos
│   ├── src/
│   │   ├── proptech_core/
│   │   │   ├── __init__.py
│   │   │   ├── py.typed
│   │   │   └── compartido/
│   │   │       ├── __init__.py
│   │   │       ├── configuracion.py   # pydantic-settings, variables POSTGRES_*
│   │   │       └── base_de_datos.py   # engine, URL.create, Base declarativa para Alembic
│   │   ├── proptech_api/
│   │   │   ├── __init__.py
│   │   │   ├── py.typed
│   │   │   ├── app.py                 # crea la app FastAPI, router bajo /api
│   │   │   └── salud.py               # GET /api/salud, verificador de base inyectable
│   │   └── proptech_worker/
│   │       ├── __init__.py            # vacío hasta 1b
│   │       └── py.typed
│   └── tests/
│       ├── conftest.py                # fixture de PostgreSQL con testcontainers
│       ├── unitarios/                 # sin base, sin Docker
│       ├── integracion/               # marcador `integracion`, PostgreSQL real
│       └── infra/                     # leen infra/compose.yaml y los Dockerfiles
├── infra/
│   ├── .env.example
│   ├── Caddyfile
│   ├── compose.yaml
│   └── ci/
│       ├── test-backend.sh
│       ├── test-web.sh
│       ├── canario.sh
│       └── humo.sh
└── web/
    ├── .dockerignore
    ├── .node-version                  # 24.21.0
    ├── Dockerfile                     # multi-etapa, output standalone, usuario no root
    ├── biome.json
    ├── next.config.ts                 # output: "standalone"
    ├── package.json                   # packageManager: pnpm@12.10.1, versiones exactas
    ├── pnpm-lock.yaml
    ├── tsconfig.json
    ├── vitest.config.ts
    └── src/app/
        ├── layout.tsx
        ├── page.tsx                   # marcador técnico: "PropTech", sin diseño
        └── page.test.tsx              # renderiza con react-dom/server, sin jsdom
```

Un solo `pyproject.toml` con los tres paquetes (`hatchling`, `packages = ["src/proptech_core",
"src/proptech_api", "src/proptech_worker"]`): API y worker comparten imagen y dependencias.
*Descartado*: un workspace de uv con tres proyectos (tres `pyproject.toml` para paquetes que se
despliegan juntos).

Las carpetas de los módulos de `proptech_core` (`complejos`, `acceso`, `gastos`, etc.) **no se crean**:
una carpeta vacía afirma una estructura que nadie validó todavía. Cada cambio crea la suya con
`dominio/`, `aplicacion/`, `puertos.py` y `adaptadores/` según D-040. *Descartado*: crear los ocho
módulos vacíos ahora.

La página de la web no es una interfaz: muestra el nombre del sistema y nada más. Por eso no pasa por
impeccable en este cambio; la primera pantalla real (login, cambio 2) sí.

### D11 · El endpoint de salud por dentro

`salud.py` define un verificador de base como dependencia de FastAPI (una función que devuelve si la
base contesta un `SELECT 1` con timeout de conexión de 2 segundos). En los tests unitarios se
reemplaza con `app.dependency_overrides` por uno que devuelve verdadero o falso, sin base. En los de
integración se usa el real contra el PostgreSQL de testcontainers. Cualquier excepción del verificador
se traduce a "sin conexión" y **no se propaga su texto** a la respuesta (requisito: el cuerpo no
contiene la cadena de conexión).

## Risks / Trade-offs

- [Biome cubre menos reglas propias de Next que `eslint-config-next`] → Se acepta para el esqueleto.
  Si en el cambio 2 aparece un error que esas reglas habrían atrapado, se suma ESLint sólo con
  `eslint-config-next` y se registra como decisión.
- [La red `interna` sin salida va a molestar cuando el worker necesite Internet (13 y 14)] → Se le da
  una red con salida sólo al worker en ese cambio; la base nunca.
- [Versiones fijadas sin digest: una etiqueta de parche de Docker Hub se puede re-publicar] → Riesgo
  bajo con imágenes oficiales; se fija el digest cuando haya producción.
- [Testcontainers necesita Docker en la máquina de quien corre los tests] → Ya es requisito para
  `docker compose up`. Los unitarios corren sin Docker con `-m "not integracion"`.
- [El job de humo construye las imágenes en cada push y tarda varios minutos] → Corre en paralelo con
  los demás; con un solo desarrollador el costo es tiempo de espera, no plata.
- [TypeScript 6 puede quedar viejo rápido si Next adopta 7] → Se revisa al actualizar Next.
- [La API se conecta como el usuario que crea la imagen de PostgreSQL, que es dueño de la base] →
  Aceptable sin datos ni RLS. El cambio 2 crea el usuario de aplicación sin privilegios de dueño; está
  en "Fuera del cambio".
- [El "CI en verde" sólo se puede ver después del push, y el push lo hace el orquestador al archivar]
  → El constructor deja la evidencia local (los scripts de `infra/ci/` corridos, con su salida,
  incluido el canario). El orquestador confirma la corrida real de GitHub Actions después del push; si
  sale roja, el cambio se reabre.
- [`web` puede alcanzar a `db` en la red `interna`: ambos comparten esa red aunque `web` nunca
  necesita hablarle a la base] → Pendiente para el cambio 2 (acceso-y-aislamiento): separar `interna`
  en sub-redes por quién necesita hablar con quién, no sólo "con o sin salida a Internet".
- [Encabezados `Via` y `X-Powered-By`, y `HEAD` devolviendo 405 en vez de replicar la respuesta de
  `GET`] → Agregar a la lista de ataques del cambio 2 (acceso-y-aislamiento): son fuga de información
  de la pila y un verbo HTTP mal manejado, ninguno de los dos cubierto por este cambio.
- [El test de la imagen de fixture es tautológico: compara el archivo contra sí mismo, no prueba nada
  del comportamiento real] → Reescribir o borrar en 1b.
- [`10.255.255.1` puede quedar "inalcanzable" al instante en los runners de GitHub, en vez de no
  responder, por lo que el test unitario podría pasar sin probar realmente el timeout] → No se
  endurece el test unitario por esto: el paso 7 de `humo.sh` (`docker compose pause db`) sí prueba el
  timeout contra una base que no responde de verdad, dentro de Docker.
- [`pg_isready -U "${POSTGRES_USER}"` sin comillas en el healthcheck] → Entrecomillar en 1b.

## Migration Plan

No hay nada que migrar: es el primer código. Para volver atrás alcanza con revertir el commit del
cambio; `docker compose down -v` borra el volumen local de la base, que en este cambio no tiene datos.

## Open Questions

Ninguna que cambie las tareas. El dominio de producción y la estrategia de despliegue al VPS se
deciden cuando haya algo que publicar.

## Desvíos durante la construcción

- **Vite fijado en `7.3.7` vía `pnpm-workspace.yaml` (`overrides`)**: `vitest 5.0.3` (D4) resuelve por
  defecto `vite@8.3.4`, cuya transformación SSR (usada por el entorno `node` de Vitest) pasa por
  Rolldown/oxc y falla con `Unexpected JSX expression` al importar un componente `.tsx` desde el
  test (reproducido el 09/10/2026 con `page.test.tsx`). `vite@7.3.7` sigue en el rango de peer
  dependency de vitest (`^6.4.0 || ^7.0.0 || ^8.0.0`) y usa esbuild para esa transformación, sin el
  problema. Se revisa cuando Vite estabilice la ruta SSR de Rolldown.
- **`pnpm-workspace.yaml` con `allowBuilds: esbuild: true`**: pnpm 12.10 bloquea scripts de
  postinstalación por política de cadena de suministro (`ERR_PNPM_IGNORED_BUILDS`); esbuild necesita
  su postinstall para bajar el binario nativo. Se aprobó sólo ese paquete, no `--all` global.
- **Mypy con el plugin `pydantic.mypy`** (`[tool.mypy] plugins`): sin él, `mypy --strict` exige los
  cinco argumentos de `Configuracion()` aunque en runtime se completan desde el entorno
  (`BaseSettings`), y habría que silenciar `call-arg` en cada instanciación. Con el plugin, mypy
  entiende el patrón y no hace falta ningún `type: ignore`.
- **Reglas extra de Ruff**: `S105` y `S607` ignoradas en `tests/**` (contraseñas de prueba literales
  y `subprocess` con ejecutables conocidos como `uv`/`alembic`); `extend-immutable-calls` para
  `fastapi.Depends` (si no, `B008` marca el patrón estándar de FastAPI como error).
- **`testcontainers.community.postgres` en vez de `testcontainers.postgres`**: el segundo emite
  `DeprecationWarning` en la versión 4.15.0 pinneada; el módulo `community` ya existe en esa misma
  versión y es la forma soportada.
- **`ENV HOSTNAME=0.0.0.0` en `web/Dockerfile`**: Docker fija la variable de entorno `HOSTNAME` al
  ID corto del contenedor para todo proceso que arranca dentro. El `server.js` standalone de Next
  usa `process.env.HOSTNAME || '0.0.0.0'`, así que sin este `ENV` el servidor queda escuchando sólo
  en la IP del contenedor y nunca en `127.0.0.1`: el healthcheck con `fetch('http://localhost:3000')`
  fallaba siempre con `ECONNREFUSED` (reproducido el 09/10/2026). No está en D9 ni D10.
- **`infra/ci/humo.sh`, verificación (3), no usa una conexión TCP cruda a `127.0.0.1:5432`**: en la
  máquina de Juani hay *otro* PostgreSQL de otro proyecto publicado en ese puerto del host (no
  relacionado con este cambio), así que esa conexión da un falso "accesible" aunque este `compose`
  no publique nada. Se cambió a `docker compose port db 5432`, que pregunta por el mapeo de *este*
  stack (vacío/`:0` cuando no hay `ports:`), y es lo que D9 pedía comprobar en espíritu. Sin
  secuestrar el puerto de otro proyecto para liberarlo primero.
- **Tag de gitleaks `v8.30.1`, no `8.30.1`**: Docker Hub publica `zricethezav/gitleaks` con el
  prefijo `v` en sus tags (`v8.30.1` existe, `8.30.1` no). Mismo parche que fijó D6, sólo el
  prefijo.
- **`openspec/config.yaml`, la guía de `apply` entre comillas**: `- TDD estricto: ver el test
  fallar antes de escribir el código que lo hace pasar.` es un ítem de lista que empieza con
  texto seguido de `:`, así que YAML lo interpreta como un mapeo (`TDD estricto` como clave) en
  vez de una cadena de un solo ítem. Se corrigió a `- "TDD estricto: ..."` entre comillas. No
  cambia el contenido de la guía, sólo evita que `openspec` la lea como un objeto.
- **Spec "Intento de conexión directa a la base desde el host" reescrita, no el script**: el
  escenario pedía que una conexión TCP cruda a `localhost:5432` fuera rechazada, pero `humo.sh`
  (ver el desvío de arriba) no hace esa conexión porque en la máquina de Juani puede haber *otro*
  PostgreSQL publicado en ese puerto, lo que daría un falso "accesible". Entre reescribir el
  script para ramificar por `CI=true` (dos caminos de verificación, uno que nunca corre en la
  máquina de desarrollo) o reescribir el escenario para que describa lo que realmente se mide, se
  eligió lo segundo: el escenario ahora pide que `docker compose port db 5432` no tenga ningún
  mapeo, que es la propiedad real que importa (nadie puede abrir una conexión directa porque no
  hay puerto publicado) y es verificable igual en cualquier máquina, con o sin otro PostgreSQL
  corriendo.
- **`Configuracion.__init__` nombraba sólo las variables `missing`, no las mal formadas ni las
  vacías (ronda 3 del Rompedor)**: el filtro original (`e["type"] == "missing"`) dejaba pasar
  `POSTGRES_PORT="abc"` (tipo `int_parsing`) y `POSTGRES_PASSWORD=""` (presente pero vacía, no
  "falta" para pydantic) hacia el mensaje genérico "Configuración inválida", que no nombra la
  variable — exactamente la confusión "config rota disfrazada de base caída" que D11 dice evitar.
  Se agregó un `field_validator` que rechaza string vacío o sólo-espacios en las 4 variables sin
  default, y `Field(ge=1, le=65535)` en el puerto; `__init__` ahora junta TODOS los errores de
  `ValidationError.errors()` (no sólo `missing`) y nombra cada variable ofensora sin nunca incluir
  el valor recibido. En esa vuelta se agregaron tests parametrizados en `tests/unitarios/`: cada
  variable faltante, cada variable vacía, cada variable string en blanco, puerto no numérico,
  puerto 0 y 70000, y un test que verifica que un valor con pinta de secreto real nunca aparece en
  el mensaje de error aunque la variable que falle sea otra.
  **Corrección (vuelta 4)**: la ronda 3 del Rompedor había quedado en `backend/tests/rompedor/
  test_configuracion_ronda3.py`, no movida ni borrada como decía esta nota antes — 10 tests sin
  anotar que rompían `ruff format --check` y daban 26 errores de `mypy` (tuplas `tuple[str, int]`
  recibiendo `tuple[str, str]`), lo que ponía el CI en rojo. Se migraron sus 10 casos a
  `backend/tests/unitarios/test_configuracion.py` (tipados, con las ramas "aceptado/rechazado"
  antes exploratorias convertidas en aserciones firmes contra el comportamiento real observado:
  pydantic acepta `" 5432 "`, `"+5432"`, `"05432"` y `"5432.0"` como puerto 5432, y rechaza el
  puerto vacío sin caer al default), y se borró `backend/tests/rompedor/` (la carpeta, no sólo su
  contenido).
- **`infra/ci/humo.sh`, nuevo escenario (7), `docker compose pause db`**: el escenario (8, antes
  7) ya cubría "base detenida" (`stop`), que cierra el socket y el cliente ve el rechazo de
  conexión al instante. Pausar congela el proceso con el cgroup freezer sin cerrar el socket: el
  kernel acepta el SYN pero nadie atiende el handshake de la aplicación, que es el caso real que
  justifica `connect_timeout=2` en `salud.py` (sin ese timeout, este escenario colgaría en vez de
  responder). Se verifica que `/api/salud` conteste 503 en menos de 4000ms y se hace `unpause`
  antes de seguir. Esto corresponde al escenario nuevo "La base está congelada, no caída" en
  `specs/entorno-de-ejecucion/spec.md`.
