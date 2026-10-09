## Why

Al 09/10/2026 el repositorio no tiene código: no hay forma de levantar el sistema ni de saber si un
cambio rompe algo. Antes del primer módulo con reglas de negocio hace falta el piso donde todo lo
demás se apoya: que el proyecto arranque entero con un comando y que los tests corran solos en cada
push (ficha `1a · infraestructura-base` de `conocimiento/roadmap.md`). Es el cambio que habilita a
`arranque-del-sistema` (1b) y, por la cadena, a todo M1.

## What Changes

- Estructura de carpetas de D-040: `config/`, `web/`, `backend/` con los paquetes `proptech_core`,
  `proptech_api` y `proptech_worker` bajo `backend/src/`, e `infra/`.
- Docker Compose en `infra/` con cuatro servicios de larga vida (PostgreSQL, Caddy, la API y la web)
  y un trabajo de migraciones que corre aparte, antes de que arranque la API.
- **Caddy es el único servicio con puertos publicados** (80 y 443). PostgreSQL, la API y la web
  viven en una red interna sin puertos hacia el host (D-043, arquitectura de Alberto).
- Alembic configurado con una primera migración vacía, aplicable y reversible sobre una base limpia
  (cierra la parte de "migraciones ordenadas con instalación limpia comprobada" de H01).
- Esqueleto de FastAPI con un endpoint de salud (`GET /api/salud`) que informa también si la base
  responde.
- Esqueleto de Next.js (App Router, TypeScript) con una página técnica mínima, servido detrás de
  Caddy (D-036).
- Lint, formato y chequeo de tipos para Python y TypeScript, y tests de los dos lados.
- CI en GitHub Actions que en cada push corre lint, tipos, tests (incluidos los de integración contra
  PostgreSQL real), una prueba de humo del stack completo detrás de Caddy y una búsqueda de secretos.
- `.env.example` sin secretos; la configuración entra sólo por variables de entorno (H45).
- README con la sección "cómo levantarlo" desde un clon limpio.

## Capabilities

### New Capabilities

- `entorno-de-ejecucion`: cómo arranca el sistema completo con un comando, qué servicios quedan
  expuestos a Internet y cuáles no, cómo se aplican las migraciones y qué responde el endpoint de
  salud a través de la única puerta pública.
- `integracion-continua`: qué verifica el CI en cada push (lint, tipos, tests unitarios y de
  integración con PostgreSQL real, humo del stack, secretos) y que falla cuando algo de eso falla.

### Modified Capabilities

Ninguna: `openspec/specs/` está vacío, éste es el primer cambio.

## Cobertura

- **Historias (HU)**: ninguna directamente. Es infraestructura que habilitan todas las historias de M1.
- **Reglas (R)**: ninguna regla de negocio se implementa acá. Se prepara el terreno para R07 y D-046
  (PostgreSQL real en los tests de integración) y para R10 (base en red interna, sin puerto público),
  sin implementar ninguna de las dos.
- **Decisiones**: D-020 (stack), D-036 (Next.js), D-038 (sólo para dejar `proptech_worker` como
  paquete vacío; Redis y el worker son de 1b), D-040 (estructura), D-043 (Caddy como única puerta,
  criterio de costo cero), D-046 (preparar PostgreSQL real para tests futuros con `NUMERIC`),
  D-047 punto 4 y D-049 (partición en 1a y 1b).
- **Observaciones del análisis**: H01 (migraciones ordenadas, instalación limpia) y H45 (entorno
  unificado: una sola fuente de configuración por variables de entorno, sin contraseñas literales).

## Fuera del cambio

- Redis, el worker ARQ y su tarea de prueba (1b). `proptech_worker` queda como paquete vacío.
- `config/parametros.yaml` y su lector (1b). `config/` se crea vacía.
- Logs estructurados en JSON y `request_id` de punta a punta (1b).
- Backups de PostgreSQL (1b) y su restauración probada (M3).
- Datos semilla (1b) y cualquier tabla de dominio: la primera migración es vacía.
- Login, usuarios, roles, Row-Level Security y el usuario de base sin privilegios de dueño (2).
- Las carpetas de los módulos de `proptech_core` (`complejos`, `acceso`, etc.): las crea el cambio
  que las llena. Sólo se crea `compartido/` con lo mínimo para la configuración y la base.
- Cualquier diseño de interfaz: la página de Next.js es un marcador técnico, no una pantalla. La
  skill impeccable entra cuando arranque la primera pantalla real (2).
- Despliegue al VPS, dominio real y certificados de producción: el Caddyfile queda listo para
  recibir un dominio por variable, pero nada se publica en este cambio.
- Generación del cliente TypeScript desde OpenAPI.

## Knowledge Base Impact

- `conocimiento/decisiones.md`: **APPEND**. Una decisión nueva (D-050) con las herramientas y
  versiones elegidas en el design (gestor de dependencias, lint y formato, versiones de imágenes,
  PostgreSQL en el CI) y lo descartado.
- `conocimiento/roadmap.md`: none. La ficha 1a sigue describiendo el plan; el cambio no altera el
  orden ni el alcance de 1b en adelante.
- `conocimiento/mvp.md`, `reglas-de-negocio.md`, `glosario.md`, `proyecto-final.md`,
  `forma-de-trabajo.md`: none. No se toca dominio, reglas, nombres ni proceso.

Fuera de `conocimiento/`, al archivar: el `README.md` raíz deja de decir "próximamente" en `web/`,
`backend/` e `infra/` (lo hace una tarea de este cambio), y la sección "Estado" del `CLAUDE.md` del
proyecto deja de decir que no hay código (lo actualiza el orquestador al archivar).

## Impact

- Código nuevo en `web/`, `backend/`, `infra/`, `config/` y `.github/workflows/`.
- Dependencias nuevas: FastAPI, SQLAlchemy, Alembic, psycopg, pydantic-settings, Next.js, React, y
  herramientas de desarrollo (ver design.md).
- Sistemas externos: GitHub Actions (gratuito para repositorios públicos) e imágenes públicas de
  Docker Hub. Ningún servicio pago (D-043).
- El repositorio es público: ningún secreto ni dato personal entra en el código, los tests, las
  imágenes ni los logs del CI.
