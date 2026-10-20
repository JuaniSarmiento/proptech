# Descripción General

## Stack tecnológico

Verificado contra `backend/pyproject.toml`, `backend/Dockerfile`, `web/package.json`, `web/Dockerfile`
e `infra/compose.yaml` al 20/10/2026 (cambios 1a a 1d, 3a y 3b archivados).

| Capa | Tecnología | Versión mínima | Fuente |
|---|---|---|---|
| Backend · lenguaje | Python | 3.14 (`>=3.14,<3.15`) | `backend/pyproject.toml` |
| Backend · imagen de runtime | `python:3.14.8-slim-trixie` | 3.14.8 | `backend/Dockerfile` |
| Backend · gestor de paquetes | uv | 0.12.24 | `backend/Dockerfile` (`ghcr.io/astral-sh/uv:0.12.24`) |
| Backend · framework web | FastAPI | 0.143 (`>=0.143.0,<0.144.0`, fijado `<0.144`: `_ruta_de` usa un atributo interno de esta versión, D-091) | `backend/pyproject.toml` |
| Backend · servidor ASGI | uvicorn | 0.54 (`>=0.54.0,<0.55.0`) | `backend/pyproject.toml` |
| Backend · ORM | SQLAlchemy | 2.1 (`>=2.1.4,<2.2.0`) | `backend/pyproject.toml` |
| Backend · migraciones | Alembic | 1.20 (`>=1.20.0,<1.21.0`) | `backend/pyproject.toml` |
| Backend · driver de PostgreSQL | psycopg[binary] | 3.3.6 (`>=3.3.6,<3.4.0`) | `backend/pyproject.toml` |
| Backend · configuración | pydantic-settings | 2.15 (`>=2.15.0,<2.16.0`) | `backend/pyproject.toml` |
| Backend · lectura de YAML | pyyaml | 6.0.3 (`>=6.0.3,<7`; versión fijada por la deuda técnica del 1c, D-090) | `backend/pyproject.toml` |
| Backend · cola del worker | arq | 0.28.0 (exacta) | `backend/pyproject.toml` |
| Backend · cliente de Redis | redis[hiredis] | 5.3.1 (`>=5.3.1,<6`; `<6` porque lo exige arq) | `backend/pyproject.toml` |
| Backend · lint y formato | Ruff | 0.16.10 | `backend/pyproject.toml` (`dependency-groups.dev`) |
| Backend · tipado estático | mypy | 2.4.0 (modo `strict`, plugin de pydantic) | `backend/pyproject.toml` |
| Backend · tests | pytest | 9.1.1 | `backend/pyproject.toml` |
| Backend · tests de integración | testcontainers[postgres] | 4.15.0 (PostgreSQL real en Docker) | `backend/pyproject.toml` |
| Base de datos (imagen) | PostgreSQL | `postgres:18.6-trixie` | `infra/compose.yaml` |
| Cola/caché (imagen) | Redis | `redis:8.10.2-trixie` | `infra/compose.yaml` (D-091) |
| Proxy (imagen) | Caddy | `caddy:2.11.7-alpine` | `infra/compose.yaml` |
| Frontend · framework | Next.js (App Router) | 16.4.0 | `web/package.json` |
| Frontend · librería de UI | React / react-dom | 19.3.0 | `web/package.json` |
| Frontend · lenguaje | TypeScript | 6.0.3 (no 7, por compatibilidad con Next, D-051) | `web/package.json` |
| Frontend · imagen de runtime | `node:24.21.0-alpine` | 24.21.0 | `web/Dockerfile` |
| Frontend · gestor de paquetes | pnpm | 12.10.1 | `web/package.json` (`packageManager`) |
| Frontend · lint y formato | Biome | 2.5.15 | `web/package.json` |
| Frontend · tests | Vitest | 5.0.3 (con Vite fijado en 7.3.7, D-051) | `web/package.json` |
| Frontend · tests de componentes | @testing-library/react + @testing-library/user-event | 16.3.3 / 14.6.8, con `jsdom` 30.1.3 como entorno | `web/package.json` |
| Frontend · accesibilidad automática | axe-core | 4.14.0 (jsdom para estructura y nombres; el navegador real para contraste) | `web/package.json` |
| Frontend · navegador real (e2e) | Playwright (`@playwright/test`) | 1.64.1, sólo Chromium | `web/package.json` |
| Frontend · tipografía | Source Sans 3 (`@fontsource/source-sans-3`) | 5.3.1, servida desde la propia web (D10 del design del 3b) | `web/package.json` |
| Infraestructura · orquestación | Docker Compose, proyecto `proptech` | sin versión (CLI del host) | `infra/compose.yaml` |

Las piezas con su versión ya fijada en la tabla (como arq 0.28.0) pero pendientes de los cambios que
vienen, porque lo que falta es la funcionalidad, no la versión: **Backend** worker ARQ ya anda (cambio
1c) pero las tareas reales de PDFs, emails e IA llegan con los cambios 7, 8, 13 y 14 (D-038).
**Frontend** PWA instalable, sin app nativa (D-020, D-036); desde el 3b, `web/src/app/edificios/`
tiene las siete pantallas del administrador (D-105: todo el ancho, menú lateral agrupado con íconos,
barra superior fija y ayuda "?" acoplada); las pantallas del vecino y del consejo, y el login,
todavía no existen (2b en adelante). **Infraestructura** Caddy como único proxy con HTTPS automático
ya anda (D-043);
el servicio de respaldos (`pg_dump` con la imagen `postgres:18.6-trixie`, D-087) está construido y
archivado desde el cambio 1d (D-095; ver `08_arquitectura_propuesta.md` §Variables de entorno).

## Arquitectura general

**Monolito modular, hexagonal por módulo, en español** (D-021, corregida en parte por D-040 y
D-046):

- Una sola aplicación dividida en módulos por dominio: `complejos` (antes `barrios`, D-040),
  `acceso`, `gastos`, `liquidacion`, `cuenta_corriente`, `pagos`, `avisos`, `politicas` (el motor de
  reglas, `13_motor_de_reglas.md`), más `compartido` (`Dinero` sobre `Decimal`, R07, D-046; sesión de base, tenancy,
  auditoría).
- Cada módulo con capas `dominio` (reglas puras), `aplicacion` (casos de uso), `puertos.py` e
  `adaptadores/`. Las dependencias apuntan hacia adentro.
- Los módulos se comunican sólo por su capa `aplicacion`; nunca tocan tablas ajenas.
- Muchos edificios en una sola base, cada fila con su administración, y Row-Level Security de
  PostgreSQL como segundo candado de R10. **Vigente desde el cierre del cambio 2a** (15/10/2026,
  D-098): RLS forzada en `administracion`, `complejo`, `unidad`, `persona`, `asignacion_rol` y
  `auditoria`, con `SET LOCAL` por transacción y `current_setting(..., missing_ok=true)` + `nullif`
  (una conexión sin tenant fijado falla cerrada); cuatro roles de PostgreSQL por responsabilidad (el de
  arranque, `proptech_migrador`, `proptech_app`, `proptech_respaldo`), ninguno con la contraseña del
  superusuario salvo el rol de arranque mismo; sin login todavía (2b), la identidad se inyecta en los
  tests. Detalle completo en `08_arquitectura_propuesta.md` §Seguridad y `04_modelo_de_datos.md`.
- La cuenta corriente es un libro de sólo agregar movimientos (R08).
- Tests en tres niveles: unitarios (reglas, sin base), integración (PostgreSQL real en Docker) y
  aceptación (la liquidación del piloto al centavo).

**Puerto de políticas** (D-064): las reglas propias de cada edificio (recargos, multas,
bonificaciones, cargos por estado, criterios de morosidad, alertas antes de emitir) entran por un
puerto en `proptech_core` que recibe hechos y devuelve acciones propuestas con montos como texto
`Dinero`; el núcleo valida todo lo que sale y corta en seco si algo no cierra. En el MVP el puerto se
implementa con GoRules ZEN y su editor visual jdm-editor, con un validador propio que bloquea la
emisión ante cualquier respuesta fuera de contrato (D-066, D-067). Detalle completo en
`13_motor_de_reglas.md`.

**Estructura del repositorio** (D-040): un solo repositorio con `knowledge-base/`, `openspec/`,
`web/` (Next.js, con áreas `(admin)`, `(consejo)` y `(vecino)`), `backend/` e `infra/` (docker-compose,
Caddyfile, backups). En `backend/src/`, tres paquetes: `proptech_core` (dominio compartido),
`proptech_api` (routers FastAPI) y `proptech_worker` (tareas). El árbol completo de directorios está en
`08_arquitectura_propuesta.md` §Estructura de directorios.

## Integraciones externas

| Servicio | Propósito | Tipo | Estado |
|---|---|---|---|
| QR de ARCA | Leer monto, CUIT, punto de venta, tipo y número de cada factura electrónica (R12) | Lectura de un código, sin API | Decidido (D-019) |
| Proveedor de IA para facturas | Completar concepto, período, categoría y grupo sugeridos cuando el QR no alcanza (R12) | API (proveedor a elegir) | Pendiente, se decide en el *design* del cambio 14 |
| Proveedor de IA para comprobantes de pago | Precargar monto, fecha y número de operación de un comprobante (R11) | API (proveedor a elegir) | Pendiente, se decide en el *design* del cambio 8 |
| Proveedor de email transaccional | Avisos de vencimiento y de mora (HU-V6), envío del PDF de la expensa | API/SMTP (proveedor a elegir, sin costo o el más barato, D-043) | Pendiente, se decide en el *design* del cambio 13 |
| GoRules ZEN (`zen-engine`) + jdm-editor | Motor y editor visual de las reglas propias de cada edificio | Librería embebida en el proceso de Python (sin servicio aparte) + componente React | Decidido (D-066), cambio 6b |
| Login (contraseña + link mágico) | Autenticación del personal (contraseña) y del vecino (link mágico por mail), método ya decidido (D-097); Clerk descartado (D-043) | Contraseña propia para el personal; envío de mail para el vecino, proveedor a elegir | Decidido el método (D-097); el *design* del cambio 2b define el envío del mail y la sesión |

Mercado Pago, recaudadores (Red Link, SIRO, Rapipago) y WhatsApp Business quedan fuera del MVP (ver
`01_vision_y_objetivos.md` §Fuera de alcance y `16_proyecto_final.md`).

## API REST (si aplica)

Todavía no hay endpoints construidos más allá del esqueleto de salud (`/api/salud`, `/salud-web` del
cambio 1a/1c). La API se construye módulo por módulo a partir del cambio 2 (`acceso-y-aislamiento`);
cada cambio del roadmap declara los endpoints que agrega en su `design.md`. No se documenta acá un
resumen que todavía no existe, para no inventarlo: ver `12_fichas_de_changes.md` y `CHANGES.md` para
qué construye cada cambio.
