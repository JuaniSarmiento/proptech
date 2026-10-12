## Context

Ver `proposal.md` (Why). Este cambio es la segunda mitad del `arranque-del-sistema` original, que se
partió en dos (ver `design.md` de `arranque-del-sistema`, "División del cambio"). Las decisiones se
mudaron sin cambios de contenido y **conservan sus números (D1 a D4, D7 a D9, D12)** para que se
puedan rastrear; D5, D6, D10 y D11 viven en `arranque-del-sistema`.

Estado de partida esperado, con `arranque-del-sistema` archivado:

- `infra/compose.yaml` (proyecto `proptech`): `db` (healthcheck entrecomillado), `migraciones`, `api`,
  `web`, `caddy`; redes `borde` e `interna` (`internal: true`). `api` ya recibe `REDIS_HOST`,
  `REDIS_PORT`, `REDIS_PASSWORD` y `PROPTECH_PARAMETROS`, con `../config` montado de sólo lectura.
- `backend/`: `Configuracion` con Redis y `PROPTECH_PARAMETROS` (D11 de 1b), con la parte de
  PostgreSQL separada para Alembic; `leer_parametros` llamado en `crear_app()`; `Dinero`, `TipoDinero`,
  `leer_semilla` y su comando. Migración `0001` vacía. `/api/salud` con verificador de base inyectable
  y `connect_timeout=2`.
- Tests: fixture de PostgreSQL que deriva la imagen de Compose y test de integración que compara la
  imagen del contenedor real (D12 de 1b). Nada de Redis.
- La web es un esqueleto de Next.js 16 sin llamadas a la API. CI: jobs `backend`, `web`, `humo` y
  `secretos`.

**Si `arranque-del-sistema` no está archivado** cuando arranque el constructor, este cambio no empieza:
depende de su tarea 6.2 (Compose ya pasa la configuración a la API).

## Cómo aplica cada lección

| Lección | Dónde se aplica en este cambio |
|---|---|
| L-001 (apagada, que no responde y lenta, con cota de tiempo) | Redis en los tres estados contra contenedor real (D4, tareas 3.3 y 3.4); base pausada durante un trabajo (4.5); `/salud-web` con la API colgada (5.2); humo con Redis pausado (7.3). Cada test afirma su cota. |
| L-002 (faltante, vacía, en blanco, tipo, rango; nombra la variable sin el valor) | Arranque del worker (4.6) y configuración de respaldos (6.1). |
| L-003 (contar tests contra la línea de base) | Tarea 1.1 anota la línea de base; 8.1 compara. |
| L-004 (dos revisores por el mismo camino no son dos) | Para el rompedor: el humo y los tests de integración cubren el `request_id` por caminos distintos (pedido directo, por la web, por el worker); atacar por uno que no sea esos. |
| L-005 (verde es todo el workflow) | Cada tarea cierra con lint, formato, tipos y tests del lado tocado; 8.1 corre el workflow entero, humo incluido. |
| L-006 (lo destructivo apunta a `proptech`) | `restaurar.sh` rechaza destinos sin prefijo `proptech_` o iguales a la base en uso (D9); el humo usa `-p proptech`. |

## Goals / Non-Goals

**Goals:**

- Que los cambios 2 a 15 encuentren resueltas, probadas y con una sola forma: la cola con reintentos e
  idempotencia, el log, el `request_id` y el backup.
- Que cada pieza falle cerrada y rápido ante sus dependencias rotas, con un error que diga qué pasó.

**Non-Goals:**

- Diseñar el modelo de tenant del worker (cambio 2).
- Monitoreo, métricas o alertas externas; página de estado pública.
- Copia de backups fuera del servidor y su cifrado (con el despliegue).
- Logs estructurados de la web y de Caddy (ver D7).

## Decisions

### D1 · Versiones de Redis, ARQ y el cliente de Redis

| Pieza | Versión | Por qué |
|---|---|---|
| Imagen de Redis | `redis:8.10.2-trixie` | Última estable de la rama 8 al 09/10/2026 (Docker Hub). Debian trixie, igual que PostgreSQL y Python. |
| `arq` | `==0.28.0` | Última publicada (PyPI, 16/04/2026), declara Python 3.14. |
| `redis[hiredis]` (Python) | `>=5.3.1,<6` | ARQ 0.28 exige `redis<6`. 5.3.1 es la última de la rama 5. `hiredis` 3.4.2 tiene wheels para 3.14. |

- **Descartado `testcontainers[redis]`**: ese extra exige `redis>=7` (Python) y choca con el `<6` de
  ARQ; `uv lock` no resuelve. Redis en los tests se levanta con `DockerContainer` genérico de
  `testcontainers.core` (D12), que no importa el cliente.
- **Descartado Celery** (más pesado, sin asyncio; Alberto propone ARQ, D-038) y **Redis en Alpine**
  (misma razón que PostgreSQL en 1a: musl y diferencias con trixie).
- Redis arranca con `redis-server --appendonly yes --maxmemory-policy noeviction --requirepass
  "${REDIS_PASSWORD:?falta REDIS_PASSWORD}"`. `appendonly`: los trabajos encolados sobreviven a un
  reinicio (Alberto: "Redis guarda su estado en disco"). `noeviction`: Redis nunca descarta trabajos
  para hacer lugar. **Contraseña** aunque esté en la red interna: la web comparte esa red hasta que el
  cambio 2 la separe (riesgo anotado en 1a). El primer argumento es `redis-server` para que el
  entrypoint de la imagen baje a usuario `redis` (uid 999) con `gosu`; con `sh -c` correría como root.
- Volumen `datos_redis:/data`, red `interna`, sin `ports`. Healthcheck:
  `["CMD-SHELL", "REDISCLI_AUTH=\"$${REDIS_PASSWORD}\" redis-cli ping | grep -q PONG"]` con
  `REDIS_PASSWORD` en el entorno del servicio (el `$$` evita que Compose lo interpole y lo deje en
  `docker inspect` del healthcheck).

### D2 · El worker: misma imagen, otro comando, trabajos en JSON

- Servicio `worker` con `image: proptech-backend:local` (la misma que construye `api`) y
  `command: ["arq", "proptech_worker.ajustes.AjustesDelWorker"]`. Depende de `db` y `redis`
  saludables y de `migraciones` completado. Redes: sólo `interna`. Healthcheck:
  `["CMD", "arq", "--check", "proptech_worker.ajustes.AjustesDelWorker"]` con
  `health_check_interval = 30` (el default de ARQ es una hora y el chequeo nunca fallaría a tiempo).
  `stop_grace_period: 30s`.
- **Serialización JSON**: `job_serializer=lambda d: json.dumps(d).encode()` y
  `job_deserializer=json.loads`, en el pool que encola y en el worker. El default de ARQ es `pickle`:
  quien escriba en Redis ejecutaría código en el worker. Un trabajo que no es JSON falla en la
  deserialización y ARQ lo descarta; el log registra la plantilla del evento, nunca el contenido (D7).
- **Contrato de toda tarea**: `async def tarea(ctx, *, request_id: str, clave: str, **datos)`, datos
  sólo `str`/`int`/`bool`/listas y mapas de esos tipos; los montos van como texto (`Dinero.a_texto()`).
- **Dominio síncrono**: SQLAlchemy sigue sincrónico (1a). El worker abre un `Engine` al arrancar
  (`on_startup`, guardado en `ctx`) con `connect_timeout=2`, `pool_pre_ping=True` y
  `application_name=proptech-worker`, y ejecuta el trabajo de base con `asyncio.to_thread`, que copia
  el contexto (así el `request_id` de la `ContextVar` llega al hilo).
- `max_tries = 5`, `job_timeout = 120`, `keep_result = 3600`.

### D3 · Reintentos e idempotencia

**Reintentos.** Un decorador `reintentable(politica)` envuelve cada tarea:

- Se reintenta **sólo** un error pasajero: `ErrorPasajero` (propio) y los que lo son por naturaleza:
  `sqlalchemy.exc.OperationalError`, `redis.exceptions.ConnectionError`/`TimeoutError`,
  `TimeoutError`, `ConnectionError`.
- Espera: `espera_base * 2 ** (intento - 1)` con `espera_base = 2.0` s → 2, 4, 8, 16. Se reintenta
  levantando `arq.Retry(defer=espera)` y se loguea `reintento_programado` (`tarea`, `intento`,
  `intentos_maximos`, `espera_s`, `tipo_error`).
- En el intento 5, en vez de `Retry`, se loguea `tarea_agotada` con nivel `error` y se relanza: ARQ la
  marca fallida. Eso cumple el papel de la "cola de mensajes muertos" de Alberto: queda en el log con
  su clave para que la mire una persona.
- Cualquier otro error: `tarea_fallida` con `tipo_error`, nivel `error`, sin reintento.
- `politica` (espera base e intentos) se arma en `on_startup` y viaja en `ctx`; los tests usan una
  espera base de 0,05 s. **Sin jitter**: con un solo worker no hay estampida y la espera
  determinista se puede afirmar en un test.

**Idempotencia, dos capas:**

1. **Cola**: `encolar` pasa `_job_id=clave`. ARQ no crea un segundo trabajo con ese id mientras el
   primero está en cola, corriendo o con resultado guardado (`keep_result`), y devuelve `None`:
   `encolar` informa `ya_encolado`.
2. **Base** (la que garantiza): tabla técnica `trabajos_hechos`, migración `0002`:

   | Columna | Tipo | |
   |---|---|---|
   | `clave` | `text` PK | `CHECK (length(clave) BETWEEN 1 AND 200)` |
   | `tarea` | `text NOT NULL` | |
   | `request_id` | `uuid NOT NULL` | |
   | `hecho_en` | `timestamptz NOT NULL DEFAULT now()` | |

   `ejecutar_una_vez(sesion, *, clave, tarea, request_id, efecto) -> bool` hace, en **una**
   transacción: `INSERT ... ON CONFLICT (clave) DO NOTHING RETURNING clave`; si no devolvió fila,
   devuelve `False` sin correr el efecto (`ya_hecha`); si devolvió, corre `efecto(sesion)` y confirma.
   Si el efecto falla, el rollback se lleva también la clave y el reintento puede completar. Dos
   ejecuciones simultáneas: la segunda queda bloqueada en el `INSERT` hasta que la primera confirma y
   después no obtiene fila. **Límite declarado**: un efecto externo (mandar un email) no entra en la
   transacción; para esos casos (cambio 13) la clave se reserva antes y el proveedor recibe la misma
   clave. No se resuelve acá.
- La clave la arma quien encola, a partir de datos estables de la operación (nunca la hora).
- `trabajos_hechos` no lleva `tenant_id`: el cambio 2 decide (está en "Fuera del cambio").

**Tarea de prueba** `tarea_de_prueba(ctx, *, request_id, clave, fallar_veces)`: valida
`0 <= fallar_veces <= 10` al encolar (en el modelo de argumentos) y otra vez al ejecutar; si
`ctx["job_try"] <= fallar_veces` levanta `ErrorPasajero`; si no, `ejecutar_una_vez` con efecto vacío
(la fila de `trabajos_hechos` es el efecto observable). Registrada en el worker; sólo se encola desde
código o desde `python -m proptech_worker.prueba encolar` dentro del contenedor (lo usa el humo).

### D4 · Encolar sin colgarse (L-001)

- Puerto `Cola` en `proptech_core/compartido/cola.py`: `async def encolar(tarea, *, clave, request_id,
  **datos) -> ResultadoEncolado` (`encolado` | `ya_encolado`); error `ColaNoDisponible`.
- Adaptador ARQ: crea el pool **perezosamente** en el primer uso, con `conn_timeout=2`,
  `conn_retries=0` en la API (en el worker, 5) y envuelve cada `enqueue_job` en
  `asyncio.timeout(2.5)`. Ante timeout o error de conexión descarta el pool (el siguiente intento
  reconecta) y levanta `ColaNoDisponible`. Así la API **arranca aunque Redis esté caído**, como ya
  arrancaba con la base caída, y `/api/salud` lo informa.
- Código síncrono de la API (endpoints `def`) encola con `anyio.from_thread.run(cola.encolar, ...)`.
- `/api/salud` suma un verificador de cola inyectable: cliente síncrono de redis-py con
  `socket_connect_timeout=2` y `socket_timeout=2`, `PING`, y cualquier excepción es `sin_conexion`.
- Los tres estados se prueban contra el contenedor real (D12): **apagado** (contenedor detenido),
  **que no responde** (contenedor pausado con la API de Docker) y **lento** (`DEBUG SLEEP` con
  `--enable-debug-command yes`, sólo en el contenedor de test: por debajo del límite completa, por
  encima falla dentro de la cota). Cada test lleva su cota de tiempo afirmada.

### D7 · Formato del log

- **Biblioteca estándar `logging`** con un `Formatter` propio en `proptech_core/compartido/logs.py`,
  sin dependencias. `configurar_logs(servicio)` reemplaza los handlers de la raíz, `uvicorn`,
  `uvicorn.error` y `arq` por uno a `stdout` con ese formatter. Se llama en `crear_app()` (uvicorn ya
  configuró los suyos antes de importar la app; se pisan) y en el `on_startup` del worker. Uvicorn
  corre con `--no-access-log`: su log de acceso incluye la query string.
- **Una línea JSON por evento** (`json.dumps(..., ensure_ascii=False)`; los saltos de línea quedan
  escapados), claves en este orden:

  ```json
  {"ts":"2026-10-09T18:04:05.123Z","nivel":"info","servicio":"api","logger":"proptech_api.seguimiento",
   "evento":"pedido_atendido","request_id":"3f2c...","metodo":"GET","ruta":"/api/salud","estado":200,
   "duracion_ms":3}
  ```

- **Campos permitidos** (lista cerrada): `ts`, `nivel`, `servicio`, `logger`, `evento`, `request_id`,
  `metodo`, `ruta`, `estado`, `duracion_ms`, `tarea`, `clave`, `intento`, `intentos_maximos`,
  `espera_s`, `resultado`, `tipo_error`, `traza`, `dependencia`, `componente`, `campos_descartados`.
  Un `extra` fuera de la lista se descarta y se cuenta. **Por qué lista blanca y no lista negra**:
  una lista negra de "campos sensibles" falla con el primer nombre que nadie previó (`mail`,
  `contacto`); la blanca falla cerrada.
- **`evento` es la plantilla, nunca el mensaje interpolado**: el formatter usa `record.msg` y descarta
  `record.args`. `logger.info("pago de %s", email)` deja `"evento":"pago de %s"`. Los logs de
  terceros pierden detalle; es el precio de que ningún dato se cuele por un argumento.
- **Excepciones**: `tipo_error` = nombre calificado de la clase; `traza` = hasta 10 cuadros
  `modulo:línea:función` de `traceback.extract_tb`, **sin** el mensaje de la excepción ni las líneas de
  código. El mensaje puede traer parámetros de SQL o datos del usuario (`IntegrityError` los incluye).
- **`ruta`** = la plantilla de la ruta de FastAPI (`/api/unidades/{id}`) cuando hay una coincidencia,
  si no el path crudo truncado a 200 caracteres, sin query string.
- Niveles: `debug`, `info`, `warning`, `error`, `critical`, en minúscula.
- **Rotación**: ancla `x-logs` en Compose con `driver: json-file`, `max-size: "10m"`, `max-file: "5"`,
  aplicada a todos los servicios.
- **Fuera**: Caddy queda sin log de acceso (su formato incluye la URI con query string; filtrarla es
  configuración propia que no se justifica todavía) y la web sin log estructurado. El primer registro
  de un pedido es el de la API. Se revisa cuando haya producción.
- PostgreSQL: `command: ["postgres", "-c", "log_line_prefix=%m [%p] %q%a "]`, así cada línea de log
  de la base (errores, avisos) lleva el `application_name`, que trae el `request_id` (D8).

### D8 · Cómo viaja el `request_id`

```
navegador ──► Caddy ─────────────► API ──► PostgreSQL (application_name, por transacción)
              │ pisa X-Request-ID   │ valida, ContextVar, logs, respuesta
              │ con {http.request.uuid}       └──► Redis (argumento del trabajo) ──► worker
              └──► web (Next) ──► API (reenvía X-Request-ID, red interna)
```

- **Formato**: UUID canónico (36 caracteres, `8-4-4-4-12` hexadecimal), normalizado a minúsculas.
  Todo productor genera UUID (Caddy, `crypto.randomUUID()`, `uuid.uuid4()`), así que validar contra
  ese patrón exacto descarta cualquier valor malicioso y además cabe en `application_name` (63
  caracteres) con el prefijo.
- **Caddy**: `request_header X-Request-ID {http.request.uuid}` en el sitio (pisa siempre lo que mande
  el cliente) y `header X-Request-ID {http.request.uuid}` para devolverlo. **Por qué pisar**: un
  valor elegido por el cliente sirve para ensuciar los logs o hacerse pasar por otro pedido; el que
  necesite correlacionar del lado del cliente lee el de la respuesta.
- **Web**: `web/src/lib/seguimiento.ts` exporta `requestIdDe(cabeceras: Headers): string` (devuelve
  el `x-request-id` entrante si es UUID válido, si no `crypto.randomUUID()`) y
  `cabecerasHaciaLaApi(cabeceras)`. La ruta `web/src/app/salud-web/route.ts`
  (`export const dynamic = "force-dynamic"`) hace `fetch` a `${PROPTECH_URL_API_INTERNA}/api/salud`
  con esa cabecera y `AbortSignal.timeout(2000)`, y responde
  `{"web": "ok", "api": "ok" | "degradado" | "sin_conexion" | "sin_configurar"}` con 200 si la API dio
  200 y 503 si no. Variable `PROPTECH_URL_API_INTERNA=http://api:8000`, fija en Compose (no es
  secreto). Es la única llamada de la web a la API en este cambio; la usan las páginas reales desde el
  cambio 2. **Descartado** mostrar el estado en la página: es interfaz y pediría pasar por impeccable
  por una línea de texto.
- **API**: middleware **ASGI puro** (no `BaseHTTPMiddleware`) en `proptech_api/seguimiento.py`: lee
  `X-Request-ID`, valida o genera, fija la `ContextVar` `request_id_actual` (en
  `proptech_core/compartido/seguimiento.py`), agrega el encabezado a la respuesta, loguea
  `pedido_atendido` al final y, ante una excepción no atrapada, loguea `error_inesperado` (D7) y
  responde 500 `{"error": "interno", "request_id": "..."}`. Un test con endpoint `def` (corre en el
  pool de hilos) verifica que la `ContextVar` llega al hilo.
- **Base**: evento `after_begin` de la `Session` que ejecuta
  `SELECT set_config('application_name', :nombre, true)` con `:nombre = "proptech-api:<request_id>"`
  (o `proptech-worker:<request_id>`). `true` = local a la transacción: al confirmar o revertir vuelve
  al nombre base de la conexión (`application_name=proptech-api` en `connect_args`), así no se pega
  al pedido siguiente del pool. Parámetro ligado, nunca interpolado. Se prueba contra PostgreSQL real:
  dentro de la transacción, en la siguiente, y con un error provocado cuyo log de la base lleva el
  `request_id` (el contenedor de test arranca con el mismo `log_line_prefix`).
- **Worker**: `encolar` exige `request_id`; el decorador de la tarea fija la `ContextVar` con el
  argumento antes de correr y la limpia al terminar; los logs y el `application_name` lo toman de ahí.
  Si el argumento falta o es inválido, se genera uno y se loguea `request_id_reemplazado`.

### D9 · Backups: dónde, cada cuánto y cómo salen del contenedor

- **Servicio `respaldos`** en Compose con `image: postgres:18.6-trixie` (el `pg_dump` de la misma
  versión que el servidor), `entrypoint: ["/usr/local/bin/respaldar.sh"]` montado desde
  `infra/respaldos/respaldar.sh:ro`, red `interna` únicamente, sin `ports`, `user:
  "${PROPTECH_UID:?falta PROPTECH_UID}:${PROPTECH_GID:?falta PROPTECH_GID}"`, `HOME=/tmp`, y
  `${PROPTECH_DIR_RESPALDOS:?falta PROPTECH_DIR_RESPALDOS}:/respaldos` montado.
- **Cómo sale sin red**: la red `interna` no tiene salida y no la necesita. El dump viaja de `db` a
  `respaldos` por la red interna (libpq) y queda en `/respaldos`, que es una **carpeta del host**
  montada (bind mount). El archivo existe en el disco del host apenas se escribe; no hay copia por
  red ni puerto abierto. **Por qué bind mount y no un volumen con nombre**: `docker compose down -v`
  borra los volúmenes con nombre (lo hace el propio humo) y se llevaría los backups junto con la base;
  una carpeta del host no la toca.
- **Dónde**: `PROPTECH_DIR_RESPALDOS`. En `.env.example`, `./datos-respaldos` (relativo a `infra/`,
  agregado a `.gitignore`). En el VPS, una ruta fuera del repositorio. Corre con el uid/gid del
  usuario del host para que los archivos sean suyos y no de un uid 999 que el host no conoce.
- **Cada cuánto**: uno al arrancar el servicio y después cada `RESPALDO_INTERVALO_SEGUNDOS`
  (default 86400). Diario alcanza para el volumen del MVP; el de arranque hace que "el backup se
  genera solo" se pueda comprobar en el humo sin esperar un día. **Descartado** cron en el contenedor:
  la imagen de PostgreSQL no lo trae y sumar un paquete por un `sleep` no se justifica.
- **Formato y nombre**: `pg_dump --format=custom` a `proptech-AAAAMMDDTHHMMSSZ.dump.parcial`, luego
  `pg_restore --list` sobre el archivo (verifica que se puede leer) y `mv` atómico a `.dump`. `umask
  077`: sólo el dueño lee. Después escribe `.ultimo-ok` con la hora (epoch).
- **Retención**: `RESPALDO_CONSERVAR` (default 14, dos semanas). Se borra lo que excede, más viejo
  primero, **sólo** archivos que cumplen `proptech-*.dump`, y sólo después de un backup correcto.
  `.parcial` huérfanos de un ciclo anterior se borran al arrancar.
- **Fallas**: si `pg_dump` o la verificación fallan, se borra el `.parcial`, se loguea
  `respaldo_fallido` con nivel `error` y se espera al próximo ciclo sin terminar el proceso.
- **Validación de su configuración** (L-002) al arrancar: intervalo entero 60..604800, conservar
  entero 1..365, carpeta existente y escribible; el error nombra la variable, nunca la contraseña.
- **Salud**: `respaldar.sh --salud` falla si `.ultimo-ok` no existe o es más viejo que 1,5 intervalos;
  healthcheck con `start_period: 120s`.
- **Logs** del script: líneas JSON con los mismos campos base (`ts`, `nivel`, `servicio:"respaldos"`,
  `evento`, `componente`), escritas con `printf` y valores fijos (nombre de archivo, duración), nunca
  la salida de `pg_dump`.
- **Testeable sin Docker**: `respaldar.sh --una-vez` corre un ciclo y termina. Los tests de pytest lo
  ejecutan con `pg_dump`/`pg_restore` falsos en el `PATH` para cubrir nombre, atomicidad, retención,
  falla y configuración inválida.
- **Restauración** `infra/respaldos/restaurar.sh <archivo> [base_destino]`: corre en el host, usa
  `docker compose -p proptech exec -T db`, destino por defecto `proptech_restauracion`, **rechaza**
  un destino igual a `POSTGRES_DB` o sin el prefijo `proptech_` (L-006), hace `dropdb --if-exists` y
  `createdb` del destino y `pg_restore --no-owner` por la entrada estándar. El humo lo corre y
  compara la revisión de Alembic de la base restaurada con la de la base en uso.
- **Fuera**: copia fuera del servidor y cifrado (Alberto: "copias cifradas todos los días, guardadas
  fuera del servidor"). Se decide con el despliegue; queda en Riesgos.

### D12 · Tests de integración con Redis real

- `conftest.py` suma `redis_contenedor` (sesión): `DockerContainer(IMAGEN_REDIS_PARA_TESTS)` con la
  imagen leída de `compose.yaml`, `redis-server --requirepass <de prueba> --enable-debug-command yes`,
  puerto expuesto y espera por el log `Ready to accept connections`. Los tests que detienen o pausan
  Redis usan **su propio contenedor** (alcance de función o módulo), nunca el de sesión, y despausan
  en un `finally`.
- El test de integración que compara la imagen del contenedor que corrió con Compose (hecho en 1b
  para PostgreSQL) se extiende a Redis, y el test unitario que prohíbe imágenes escritas a mano en
  `conftest.py` también cubre la de Redis.
- El worker se prueba en proceso: `arq.worker.Worker(..., burst=True)` contra el Redis y el PostgreSQL
  de test, con la política de espera corta.

## Risks / Trade-offs

- [ARQ tiene pocos mantenedores y fija `redis<6`] → La cola está detrás del puerto `Cola` y las
  tareas no importan ARQ salvo el decorador; cambiar a otra cola toca el adaptador y `ajustes.py`.
  Se revisa si ARQ no publica soporte para redis-py 6.
- [Redis 8 cambió de licencia (AGPLv3 / RSALv2 / SSPLv1)] → Se usa sin modificar y sin ofrecerlo como
  servicio: no impone obligaciones al proyecto. Si molesta, Valkey es compatible y se cambia la imagen.
- [`DEBUG SLEEP` necesita `--enable-debug-command yes`] → Sólo en el contenedor de test; el de
  Compose no lo habilita y el humo no lo usa.
- [Descartar `record.args` deja pobres los logs de bibliotecas de terceros] → Se acepta: la garantía
  de "ningún dato por argumento" vale más que el detalle. Si un log de tercero hace falta, se agrega
  con un evento propio.
- [La contraseña de Redis queda visible en `docker inspect` del servicio] → Igual que la de PostgreSQL
  en el entorno; quien accede al daemon de Docker ya es dueño de la máquina.
- [Backups en el mismo disco que la base] → Protegen de un error humano o una migración rota, no de
  perder el servidor. La copia fuera del servidor y el cifrado se deciden con el despliegue; hasta
  entonces no hay datos reales (el piloto no empezó).
- [El uid/gid del host como usuario del servicio de respaldos] → En el CI el runner no es 1000; el
  humo exporta `PROPTECH_UID=$(id -u)` y `PROPTECH_GID=$(id -g)` antes de levantar.
- [`trabajos_hechos` crece sin límite] → Una fila por trabajo; al volumen del MVP son miles por año.
  Se poda cuando moleste, nunca antes de que pase el `keep_result` de ARQ.

- [Tamaño del cambio] → 32 tareas, con logs, cola, worker, web y respaldos en una sola vuelta. 1b
  mostró que una vuelta del constructor cubre unas 20. Si se quiere evitar otra división a mitad de
  camino, el corte natural es después de la sección 5 (`request_id` de punta a punta) y dejar
  respaldos, humo y README (secciones 6 y 7) en un cambio aparte.

## Migration Plan

- Migración `0002` crea `trabajos_hechos`; su `downgrade` la borra. Probada ida y vuelta sobre base
  vacía (como `0001`).
- Para volver atrás: revertir el commit y `docker compose -p proptech down -v`. La carpeta de respaldos
  del host queda; se borra a mano si se quiere.
- Al actualizar una copia local existente: copiar las variables nuevas de `.env.example` a `.env` y
  crear la carpeta de respaldos. Compose nombra la que falte.

## Open Questions

Ninguna que cambie las specs o las tareas. Pendientes de la etapa de despliegue: destino y cifrado de
la copia fuera del servidor; logs estructurados de Caddy y de la web.
