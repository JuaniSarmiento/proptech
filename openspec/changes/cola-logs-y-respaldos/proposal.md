## Why

Es la segunda mitad del `arranque-del-sistema` original, partido porque no entraba en una vuelta del
constructor. `arranque-del-sistema` dejó los parámetros, el monto y la semilla; faltan las piezas
transversales de operación que todos los cambios siguientes dan por existentes: una cola con worker
para lo lento (PDFs, emails, IA), un número de seguimiento por pedido para reconstruir cualquier
reclamo, logs que no filtren datos y backups que se generen solos. Si cada cambio de M1 las inventa a
su manera, el 7 (liquidación) y el 13 (emails) se construyen sobre convenciones distintas. Completa la
ficha `1b` de `conocimiento/roadmap.md` y habilita al cambio 2.

Decisiones que cubre: **D-038** (Redis y worker ARQ con reintentos espaciados e idempotencia) y
**D-047 punto 4** en su parte de logs estructurados con número de seguimiento y backups automáticos.
Avanza la observación **H46** (restauración de backup probada) de M3. Planifica sobre las lecciones
L-001 a L-006 (ver `design.md`, "Cómo aplica cada lección").

## What Changes

- **Redis** (`redis:8.10.2-trixie`) en la red `interna`, con contraseña, persistencia en disco y sin
  puertos publicados.
- **Worker ARQ** como servicio aparte que usa la misma imagen que la API con otro comando. Tiene una
  tarea de prueba, reintentos espaciados sólo para errores pasajeros, tope de intentos e
  idempotencia en dos capas (clave del trabajo en la cola y clave única en la base, en la misma
  transacción que el efecto). Los trabajos viajan serializados en JSON, nunca con `pickle`. No arranca
  con configuración o parámetros inválidos.
- **Migración `0002`** con la tabla técnica `trabajos_hechos` (clave de idempotencia). Es la primera
  tabla del sistema y no es de dominio.
- **Logs estructurados en JSON**, una línea por evento, con una lista cerrada de campos, sin cuerpos,
  sin query strings, sin mensajes de excepción y sin los argumentos de los mensajes.
- **Número de seguimiento (`request_id`)**: Caddy lo genera siempre y pisa el que venga de Internet;
  la web lo reenvía a la API; la API lo valida, lo pone en cada línea de log, lo devuelve en la
  respuesta y lo anota en la conexión a PostgreSQL (`application_name`); el worker lo adopta del
  trabajo encolado.
- **Ruta técnica de la web** `GET /salud-web` (sin interfaz) que consulta la salud de la API
  reenviando el `request_id`.
- **Endpoint de salud ampliado**: informa también si la cola responde. **BREAKING** para quien lea el
  cuerpo exacto: se agrega el campo `cola`.
- **Backups automáticos de PostgreSQL**: un servicio `respaldos` hace un `pg_dump` al arrancar y
  después una vez por día, lo deja en una carpeta del host (a salvo de `docker compose down -v`),
  conserva los últimos 14 y se prueba restaurándolo en una base aparte.
- **CI**: el humo verifica el worker, Redis sin puertos, el `request_id` de punta a punta, el backup
  generado solo y su restauración, y el comando de la semilla dentro de la imagen.

## Capabilities

### New Capabilities

- `cola-de-trabajos`: cómo se encola un trabajo, cómo lo ejecuta el worker, qué se reintenta y cuánto
  se espera, cuándo se abandona, por qué un trabajo repetido no duplica su efecto y qué valida el
  worker al arrancar.
- `trazabilidad-y-logs`: formato del log, campos permitidos, qué nunca se loguea y cómo viaja el
  `request_id` por cada salto.
- `respaldos-de-la-base`: cuándo se genera un backup, dónde queda, cuántos se conservan y cómo se
  prueba que se puede restaurar.

### Modified Capabilities

- `entorno-de-ejecucion`: el arranque incluye Redis, el worker y los respaldos; el endpoint de salud
  informa la cola; la configuración suma las variables de respaldos; Redis, el worker y los
  respaldos también sin root y sin puertos; rotación de logs.
- `integracion-continua`: los tests de integración corren también contra Redis real y el chequeo de
  imagen real cubre Redis; el humo cubre worker, `request_id` y respaldos.

## Fuera del cambio

- **Parámetros, `Dinero`, semilla y configuración de Redis en la API**: hechos en `arranque-del-sistema`.
- **Usuarios, login, roles, tenant y Row-Level Security**: cambio 2. `trabajos_hechos` nace sin
  `tenant_id`; el cambio 2 decide si lo lleva.
- **Copia de los backups fuera del servidor y cifrado**: se decide con el despliegue al VPS.
- **Tareas reales del worker** (PDF, email, IA): cambios 7, 13 y 14. Red con salida a Internet para el
  worker: cambio 13.
- **Pantallas**: la única pieza nueva de la web es una ruta técnica que devuelve JSON.
- **Rate limiting en Redis**: cambio 2 (login).

## Knowledge Base Impact

- `conocimiento/decisiones.md`: **APPEND**. Una decisión con las elecciones de este cambio (versiones
  de Redis, ARQ y redis-py; JSON en vez de `pickle`; formato del log y lista cerrada de campos;
  `request_id` como UUID pisado por Caddy; backups diarios en carpeta del host con 14 copias).
- `conocimiento/roadmap.md`: **REWRITE** de la ficha de este cambio (marcarla ✅) y de la ficha 2 para
  que decida si `trabajos_hechos` lleva `tenant_id` y cómo fija el tenant el worker sobre el
  `request_id` ya existente.
- `conocimiento/glosario.md`: **APPEND** de "número de seguimiento (`request_id`)", "clave de
  idempotencia", "trabajo / tarea del worker" y "respaldo", si no están.
- `conocimiento/lecciones.md`: lo propone el auditor al cerrar; este cambio no lo escribe.
- `conocimiento/reglas-de-negocio.md` y `conocimiento/mvp.md`: none. No cambia ninguna regla.

## Impact

- **Código**: `backend/src/proptech_core/compartido/` (logs, seguimiento, cola, idempotencia),
  `backend/src/proptech_api/` (middleware de seguimiento, salud, manejo de errores),
  `backend/src/proptech_worker/` (ajustes, tarea y comando de prueba),
  `backend/migraciones/versions/0002_*`, `web/src/lib/seguimiento.ts`, `web/src/app/salud-web/route.ts`.
- **Infra**: `infra/compose.yaml` (servicios `redis`, `worker`, `respaldos`; rotación de logs;
  `log_line_prefix` de PostgreSQL), `backend/Dockerfile` (`--no-access-log`), `infra/Caddyfile`,
  `infra/respaldos/`, `infra/.env.example`, `infra/ci/humo.sh`, `.gitignore`, README.
- **Dependencias nuevas**: `arq==0.28.0`, `redis[hiredis]` 5.3.x (ARQ exige `<6`). Sin dependencias
  nuevas en la web.
- **Configuración nueva**: `PROPTECH_DIR_RESPALDOS`, `PROPTECH_UID`/`PROPTECH_GID`,
  `RESPALDO_INTERVALO_SEGUNDOS`, `RESPALDO_CONSERVAR`, `PROPTECH_URL_API_INTERNA` (fija en Compose).
- **Contrato**: `GET /api/salud` agrega el campo `cola`; toda respuesta de la API lleva `X-Request-ID`.
