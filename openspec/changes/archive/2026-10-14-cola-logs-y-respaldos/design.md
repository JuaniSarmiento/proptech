## Context

Ver `proposal.md` (Why). Este cambio es la segunda mitad del `arranque-del-sistema` original, que se
partió en dos (ver `design.md` de `arranque-del-sistema`, "División del cambio"), y que la auditoría
de Alberto del 13/10 volvió a partir (D-087): **este diseño (1c) conserva D1 a D4, D7, D8 y D12**;
**D9 (respaldos) se mudó sin cambios de fondo a `respaldos-y-restauracion` (1d)**, que además define
el humo ampliado y el README. Los números se conservan para que se puedan rastrear; D5, D6, D10 y D11
viven en `arranque-del-sistema`. D13 es nueva (los errores de terceros, L-007). D16 a D18 son nuevas y
salen de la tercera auditoría del socio (13/10): `Dinero` copiable y serializable (A1), la API detrás
del proxy (B6) y las contraseñas como secreto con un único engine por proceso (M12 a M14). Esa misma
auditoría sumó a D1, D2 y D7 la confirmación de Redis (M19), la red de salida del worker (M18), los
logs de error de Caddy (M26), Alembic sin pisar los logs (M16) y ARQ sin argumentos ni resultados en
el log (M25), y a las tareas la subida de PyYAML (M11), el rechazo de `float` y `Decimal` al encolar
(M24) y la línea de base sobre un clon con historial (M27, B14).

Estado de partida, con `arranque-del-sistema` archivado (11/10/2026):

- `infra/compose.yaml` (proyecto `proptech`): `db` (healthcheck entrecomillado), `migraciones`, `api`,
  `web`, `caddy`; redes `borde` e `interna` (`internal: true`). `api` ya recibe `REDIS_HOST`,
  `REDIS_PORT`, `REDIS_PASSWORD` y `PROPTECH_PARAMETROS`, con `../config` montado de sólo lectura.
- `backend/`: `Configuracion` con Redis y `PROPTECH_PARAMETROS` (D11 de 1b), con la parte de
  PostgreSQL separada para Alembic; `leer_parametros` llamado en `crear_app()`; `Dinero`, `TipoDinero`,
  `leer_semilla` y su comando. Migración `0001` vacía. `/api/salud` con verificador de base inyectable
  y `connect_timeout=2`. Cuatro tests de arranque de la API como proceso aparte
  (`tests/unitarios/test_arranque_api*.py`), que el worker replica (L-009).
- Tests: fixture de PostgreSQL que deriva la imagen de Compose y test de integración que compara la
  imagen del contenedor real (D12 de 1b). Nada de Redis.
- La web es un esqueleto de Next.js 16 sin llamadas a la API. CI: jobs `backend`, `web`, `humo` y
  `secretos`. `infra/ci/humo.sh` levanta con `docker compose up --build -d --wait`.

**Si `arranque-del-sistema` no está archivado** cuando arranque el constructor, este cambio no empieza.

## Cómo aplica cada lección

| Lección | Dónde se aplica en este cambio |
|---|---|
| L-001 (apagada, que no responde y lenta, con cota de tiempo) | Redis en los tres estados contra contenedor real (D4, tarea 4.5); salud con Redis detenido y pausado (4.7); la base pausada con una conexión ya abierta en el pool del engine único (D18, 3.6); base pausada durante un trabajo (5.8); `/salud-web` con la API colgada y con la conexión rechazada (6.3). Cada test afirma su cota. |
| L-002 (faltante, vacía, en blanco, tipo, rango; nombra la variable sin el valor) | Contraseñas como `SecretStr` sin perder los rechazos de vacía y en blanco (3.5); parámetros del pool (3.6); arranque del worker (5.9). |
| L-003 (contar tests contra la línea de base) | 1.1 anotó la línea de base sobre un árbol sin historial; 1.2 la repite sobre un clon con `.git` y es la que compara 7.1. |
| L-004 (dos revisores por el mismo camino no son dos) | Para el rompedor: los tests cubren el `request_id` por el middleware con `TestClient`, por la ruta de la web con `fetch` simulado y por el worker en proceso; el de punta a punta por el proxy es del humo del 1d. Atacar por un camino que no sea esos (por ejemplo, un endpoint `def` que abre su propia sesión, o dos pedidos concurrentes que comparten conexión del pool). |
| L-005 (verde es todo el workflow) | Cada tarea cierra con lint, formato, tipos y tests del lado tocado; 7.1 corre el workflow entero, humo incluido. |
| L-006 (lo destructivo apunta a `proptech`) | Los tests que detienen o pausan Redis o PostgreSQL lo hacen sobre contenedores propios del test, nunca sobre el de sesión ni sobre el stack de Compose (D12; 3.6, 4.5, 5.8). |
| L-007 (el error de una librería también es una salida) | D7 y D13: el formatter no copia mensajes de excepción (2.2); el 500 inesperado (3.3); las contraseñas fuera de la representación de la configuración (3.5); el log de la salud degradada sin el mensaje de psycopg (3.6); `ArgumentoNoPermitido` nombra el campo sin el valor (4.4); `ColaNoDisponible` tiene mensaje propio (4.5); la salud no repite el error (4.6); los eventos de reintento (5.3); el trabajo `pickle` rechazado (5.6); los argumentos y el resultado de un trabajo fuera de los logs de ARQ (5.7); el arranque del worker (5.9); `/salud-web` (6.3); los logs de error de Caddy sin URI ni encabezados (6.4). Cada uno con un test de marcador. |
| L-008 (fullmatch y sólo ASCII) | Validación del `request_id` en Python y TypeScript (D8; 3.1, 6.1), `fallar_veces` entero estricto (5.4) y `Dinero` reconstruido desde su texto, que vuelve a pasar por la validación (D16, 4.3). |
| L-009 (un arreglo en un módulo se prueba en su gemelo) | Gemelos de este cambio: el validador del `request_id` en Python y en TypeScript (una sola tabla de casos, 3.1 y 6.1); el verificador de base y el de cola de `/api/salud` (4.6); el arranque de la API y el del worker (5.9 replica los cuatro tests); `/api/salud` y `/salud-web` (los dos sin texto de error en el cuerpo, 4.6 y 6.3); el engine del worker y el de la API (los dos con los parámetros del pool de la configuración, D18). |

## Goals / Non-Goals

**Goals:**

- Que los cambios 1d a 15 encuentren resueltas, probadas y con una sola forma: la cola con reintentos
  e idempotencia, el log y el `request_id`.
- Que cada pieza falle cerrada y rápido ante sus dependencias rotas, con un error que diga qué pasó.

**Non-Goals:**

- Diseñar el modelo de tenant del worker (cambio 2).
- Monitoreo, métricas o alertas externas; página de estado pública.
- Respaldos, restauración, humo ampliado y README (1d, D-087).
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
- **Confirmado en la tercera auditoría (M19)**: el servicio `redis` lleva `requirepass`, `appendonly`,
  el volumen `datos_redis` y ningún puerto publicado. La tarea 4.1 exige los cuatro y la spec lo fija
  en "Redis protegido y persistente".

### D2 · El worker: misma imagen, otro comando, trabajos en JSON

- Servicio `worker` con `image: proptech-backend:local` (la misma que construye `api`) y
  `command: ["arq", "proptech_worker.ajustes.AjustesDelWorker"]`. Depende de `db` y `redis`
  saludables y de `migraciones` completado. Redes: `interna` y `salida_worker` (ver abajo, M18). Healthcheck:
  `["CMD", "arq", "--check", "proptech_worker.ajustes.AjustesDelWorker"]` con
  `health_check_interval = 30` (el default de ARQ es una hora y el chequeo nunca fallaría a tiempo).
  `stop_grace_period: 30s`.
- **Red de salida del worker (M18)**: la red `interna` es `internal: true` y no tiene salida a
  Internet; los proveedores de email e IA (cambios 13 y 14) la necesitan. El worker suma una red
  propia, `salida_worker`, sin `internal`, en la que no está ningún otro servicio: la base y Redis
  siguen sólo en `interna` y no quedan alcanzables desde esa red. Se declara ahora, con su test (5.10),
  para que el cambio 13 no tenga que tocar la topología de red junto con su lógica de envío.
  **Descartado** poner al worker en `borde`: comparte red con Caddy y queda a un salto de lo público.
- **Serialización JSON**: `job_serializer=lambda d: json.dumps(d).encode()` y
  `job_deserializer=json.loads`, en el pool que encola y en el worker. El default de ARQ es `pickle`:
  quien escriba en Redis ejecutaría código en el worker. Un trabajo que no es JSON falla en la
  deserialización y ARQ lo descarta; el log registra la plantilla del evento, nunca el contenido (D7).
- **Contrato de toda tarea**: `async def tarea(ctx, *, request_id: str, clave: str, **datos)`, datos
  sólo `str`/`int`/`bool`/listas y mapas de esos tipos; los montos van como texto (`Dinero.a_texto()`).
- **Dominio síncrono**: SQLAlchemy sigue sincrónico (1a). El worker abre un `Engine` al arrancar
  (`on_startup`, guardado en `ctx`) con los parámetros del pool de la configuración (D18) y
  `application_name=proptech-worker`, y ejecuta el trabajo de base con `asyncio.to_thread`, que copia
  el contexto (así el `request_id` de la `ContextVar` llega al hilo).
- `max_tries = 5`, `job_timeout = 120`, `keep_result = 3600`, `log_results = False` (D7).
- **Tipos que acepta `encolar` (M24)**: lista blanca, igual que los campos del log: `str`, `int`,
  `bool`, `None`, listas y mapas con claves `str`, recorridos en profundidad. Cualquier otro valor
  (`float`, `Decimal`, un `Dinero` sin pasar a texto, una fecha) se rechaza antes de tocar Redis con
  `ArgumentoNoPermitido`, cuyo mensaje nombra la ruta del campo (`montos[1]`, `detalle.total`) y nunca
  el valor. **Por qué**: con el serializador JSON un `float` viaja sin error y llega al worker como
  número binario (el defecto que R07 y D-046 prohíben); un `Decimal` haría fallar `json.dumps` con un
  `TypeError` cuyo mensaje repite el valor (L-007).
- **Blindaje del CLI de ARQ (D7, D13, F12, vuelta 3)**: `arq/cli.py` siempre corre
  `logging.config.dictConfig(default_log_config(...))` al arrancar, después de importar
  `proptech_worker.ajustes` y antes de `Worker.main()` (antes de `on_startup`). Con la config por
  default de ARQ eso reemplaza el handler del logger `arq` por uno de texto plano que interpola los
  argumentos del trabajo; si Redis es inalcanzable, ahí se logea el error de conexión de redis-py
  (host, puerto, mensaje) varias veces, sin pasar por `FormateadorJSON`. **En vez de tocar el
  `command` del servicio `worker` en Compose** (que un test exige literal, sin `--custom-log-dict`),
  se pisa `arq.cli.default_log_config` al importar `ajustes.py` para que devuelva una config
  `dictConfig` propia, con el mismo formatter JSON que usa el resto del worker. El `import` de
  `proptech_worker.ajustes` corre siempre antes de ese `dictConfig` (el CLI primero importa
  `worker_settings`, después configura logging), así que el pisado ya está en su lugar a tiempo.
- **`sys.excepthook` acotado a cuatro paquetes (D13, F12, vuelta 3)**: el CLI de ARQ no atrapa el
  error de `create_pool` cuando los reintentos de conexión a Redis se agotan, y ese traceback (que el
  `excepthook` default de Python imprime directo a `stderr`) lleva el mensaje de redis-py con host y
  puerto. `ajustes.py` reemplaza `sys.excepthook` por una función que, si el tipo de la excepción es
  de uno de los cuatro paquetes de D13 (`redis`, `arq`, `psycopg`, `sqlalchemy`, por el nombre del
  módulo) y no es `KeyboardInterrupt`, la logea como cualquier otra (vía el formatter, pasando la
  excepción misma como `msg`): sólo `tipo_error` y `traza`, nunca su mensaje. Cualquier otra
  excepción (en particular las propias, que ya nombran la variable o el campo sin su valor) sigue el
  camino normal a `stderr` sin pasar por acá. **Límite declarado (F12b)**: esto cubre la excepción tal
  como la lanza el paquete; una excepción de terceros envuelta por otra capa (encadenada con `from`,
  un `ExceptionGroup`, o un `OSError` genérico que no pertenece a ninguno de los cuatro módulos) no
  entra en el chequeo por nombre de módulo y sigue el camino normal. Sin un camino real hoy que
  produzca ese envoltorio; deuda para el cambio 7 si aparece uno.

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
- **Otro límite declarado (F2c, vuelta 3)**: `asyncio.wait_for` (D18, `COTA_OPERACION_S`) corta la
  espera del event loop, nunca el hilo que corre la operación de base; si la base queda congelada más
  tiempo que todos los reintentos juntos (ARQ ya marcó el trabajo `tarea_agotada`), el hilo del
  primer intento, que sigue vivo en segundo plano, puede confirmar su `INSERT` en `trabajos_hechos`
  después de ese agotamiento (ver la spec de `cola-de-trabajos`, "Límite conocido"). Acá no importa
  porque el efecto de `tarea_de_prueba` es vacío. **Este patrón no se copia para una tarea con efecto
  real** (un email, un movimiento de plata, una reserva confirmada): ahí una confirmación tardía
  después de `tarea_agotada` es un efecto que nadie espera y que nadie va a reintentar ni revisar. El
  cambio 7, antes de registrar la primera tarea real del worker, tiene que resolverlo del lado de la
  base (un corte de servidor: `statement_timeout`/`lock_timeout` de PostgreSQL o el `connect_args` de
  libpq que corresponda) más una cota propia por tarea; acotar sólo la espera del lado del cliente no
  alcanza.

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
- **Conexión a Redis en un solo módulo**: `proptech_core/compartido/conexion_redis.py` es el único que lee
  `redis_password` con `get_secret_value()` (D18). De ahí toman su conexión el adaptador ARQ, el
  verificador de cola de `/api/salud` y los `RedisSettings` del worker.
- Código síncrono de la API (endpoints `def`) encola con `anyio.from_thread.run(cola.encolar, ...)`.
- `/api/salud` suma un verificador de cola inyectable: cliente síncrono de redis-py con
  `socket_connect_timeout=2` y `socket_timeout=2`, `PING`, y cualquier excepción es `sin_conexion`.
  **El verificador crea un cliente de Redis nuevo por pedido** (`obtener_verificador_de_cola`), a
  diferencia del engine único de base de D18: un cliente sincrónico de redis-py no mantiene un pool
  caro de conexiones como SQLAlchemy, así que no hace falta guardarlo en el lifespan; cada pedido abre
  y cierra el suyo.
- Los tres estados se prueban contra el contenedor real (D12): **apagado** (contenedor detenido),
  **que no responde** (contenedor pausado con la API de Docker) y **lento** (`DEBUG SLEEP` con
  `--enable-debug-command yes`, sólo en el contenedor de test: por debajo del límite completa, por
  encima falla dentro de la cota). Cada test lleva su cota de tiempo afirmada.

### D7 · Formato del log

- **Biblioteca estándar `logging`** con un `Formatter` propio en `proptech_core/compartido/logs.py`,
  sin dependencias. `configurar_logs(servicio)` reemplaza los handlers de la raíz, `uvicorn`,
  `uvicorn.error` y `arq` por uno a `stdout` con ese formatter. Se llama en `crear_app()` (uvicorn ya
  configuró los suyos antes de importar la app; se pisan) y al importar `proptech_worker.ajustes`;
  además, el `on_startup` del worker la vuelve a llamar, pero **condicional**: sólo si el logger `arq`
  ya no tiene el handler JSON propio. **Por qué puede perderlo**: el CLI de ARQ (`arq
  proptech_worker.ajustes.AjustesDelWorker`, el comando del servicio `worker`) llama siempre
  `logging.config.dictConfig(default_log_config(...))` al arrancar, después de importar este módulo y
  antes de que `Worker.main()` corra `on_startup`; con la config por default de ARQ eso pisaría el
  handler JSON por uno de texto plano. D2 ya blinda ese camino pisando
  `arq.cli.default_log_config` para que devuelva la misma config JSON (ver abajo), así que en el CLI
  real el handler nunca se pierde; `on_startup` reconfigura igual, por si algo más (un test en proceso
  que no pasa por el CLI, u otra reconfiguración) lo hubiera pisado antes. Reconfigurar siempre, sin la
  condición, rompería a los tests que capturan los logs redirigiendo el `.stream` del handler ya
  puesto, porque `configurar_logs` nunca reutiliza el objeto del handler viejo. Uvicorn corre con
  `--no-access-log`: su log de acceso incluye la query string.
  **Dos líneas fijas de ARQ sin pasar por este diseño**: `Worker.main()` loguea "Starting worker for %d
  functions: %s" y las estadísticas de la conexión a Redis (versión, memoria, clientes, claves) **antes**
  de llamar a `on_startup`; ninguna de las dos lleva datos de un trabajo ni de un pedido, sólo el
  conteo de funciones registradas y el estado de Redis, así que se aceptan tal cual (spec de
  `trazabilidad-y-logs`, "Excepción conocida").
  **Evento fijo `excepcion_como_mensaje`**: cuando `record.msg` es la excepción misma, no una
  plantilla (lo hacen `uvicorn/server.py` y `config.py` con `logger.error(exc)`, F7b), el formatter no
  puede usarla como `evento` porque su `str()` es el mensaje de la excepción; en vez de eso usa el
  evento fijo `excepcion_como_mensaje` y saca `tipo_error`/`traza` de la excepción misma, nunca de su
  texto (D13). **Traceback crudo**: cuando el mensaje ya es un traceback formateado como texto (lo hace
  Starlette en `lifespan.startup.failed`, que uvicorn logea sin `exc_info`), el formatter lo reconoce
  por la marca `"Traceback (most recent call last):"`, descarta el mensaje entero (evento fijo
  `traceback_crudo_descartado`) y reconstruye `tipo_error` buscando, de atrás para adelante, la primera
  línea que `fullmatch`ea un nombre de excepción (`[A-Za-z_][\w.]*` terminado en `Error`, `Exception`,
  `Warning`, `Exit` o `Interrupt`, con `re.ASCII`): una línea de continuación del mensaje (con espacios,
  guiones, sin forma de identificador) nunca matchea esa expresión, aunque tenga dos puntos.
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
- **Alembic no pisa los logs (M16)**: `migraciones/env.py` llama a
  `fileConfig(config.config_file_name, disable_existing_loggers=False)`. Con el default (`True`), correr
  las migraciones en un proceso que ya configuró sus logs (los tests de integración, o la API si algún
  día migra al arrancar) apaga en silencio todos los loggers creados antes, incluidos los de
  `proptech_core`. **Descartado** sacar `fileConfig`: el trabajo de migraciones en Compose sigue
  queriendo ver la salida de Alembic.
- **ARQ no escribe argumentos ni resultados (M25)**: ARQ loguea por defecto cada trabajo con sus
  argumentos y su resultado truncados. El formatter ya descarta `record.args` y por eso esos valores no
  salen; además `AjustesDelWorker` fija `log_results = False`, para no depender de un solo candado. La
  tarea 5.7 lo prueba con dos marcadores (uno en un argumento, otro en el resultado) y se ve fallar
  primero con el handler por defecto de ARQ.
- **Rotación**: ancla `x-logs` en Compose con `driver: json-file`, `max-size: "10m"`, `max-file: "5"`,
  aplicada a todos los servicios.
- **Caddy (M26)**: sigue sin log de acceso (su formato incluye la URI con query string), pero Caddy
  escribe igual **logs de error** (por ejemplo, un `reverse_proxy` que no llega a la API o a la web),
  y esos registros incluyen el pedido: la URI con su query string y los encabezados. Se filtran en el
  logger por defecto, en las opciones globales del `Caddyfile`, con `format filter` borrando
  `request>uri` y `request>headers`. **Descartado** registrar el riesgo como aceptado: la query string
  puede traer un email o un token (es el mismo motivo por el que uvicorn corre sin log de acceso) y el
  filtro es configuración de Caddy, sin código. Se verifica con `caddy adapt --validate` y el JSON
  resultante (6.4); la verificación de punta a punta (un 502 con un email en la query) queda propuesta
  para el humo del 1d. La sintaxis exacta del filtro se confirma en el apply contra la documentación
  de la versión de Caddy fijada en Compose.
- **Fuera**: la web sin log estructurado. El primer registro de un pedido es el de la API. Se revisa
  cuando haya producción.
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
- **Cómo se valida (L-008)**: en Python, `re.fullmatch` con `flags=re.ASCII` y la expresión
  `[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}`; en TypeScript, la
  misma expresión anclada con `^...$` y sin la bandera `m`. **Se valida antes de normalizar**: nunca
  se recorta ni se pasa a minúsculas un valor para después aceptarlo, porque `strip()` se come el salto
  de línea final y `lower()` de Unicode puede convertir un carácter ajeno. Clases `[0-9a-fA-F]`
  explícitas en vez de `\d` o de `re.IGNORECASE`.
- **Una sola tabla de casos (L-009)**: `config/contratos/request-id.json`, con los válidos (y su forma
  normalizada) y los inválidos (con su motivo). La leen el test de pytest y el de Vitest, y cada uno
  exige que haya al menos un caso de cada motivo obligatorio (vacío, largo, sin guiones, llaves,
  espacio, tabulación, salto de línea al principio y al final, dígito no ASCII, ancho completo,
  `<script>`, comillas, inyección SQL, mayúsculas), así nadie la vacía sin que falle un test. Vive en
  `config/` porque los dos scripts de test (`test-backend.sh` y `test-web.sh`) corren en el host con el
  repositorio entero; no es configuración de ejecución y ningún proceso la lee en producción.
  **Descartado**: duplicar los casos en cada lado (el defecto que L-009 describe).
- **Caddy**: `request_header X-Request-ID {http.request.uuid}` en el sitio (pisa siempre lo que mande
  el cliente) y `header X-Request-ID {http.request.uuid}` para devolverlo. **Por qué pisar**: un
  valor elegido por el cliente sirve para ensuciar los logs o hacerse pasar por otro pedido; el que
  necesite correlacionar del lado del cliente lee el de la respuesta.
- **Web**: `web/src/lib/seguimiento.ts` exporta `validarRequestId(valor: string): string | null`
  (la misma expresión de más arriba, anclada) y `requestIdDe(cabeceras: Headers): string` (devuelve
  el `x-request-id` entrante si `validarRequestId` lo acepta, si no `crypto.randomUUID()`) y
  `cabecerasHaciaLaApi(cabeceras)`. **`validarRequestId` queda exportado** (no sólo usado adentro de
  `requestIdDe`) porque el test de la tabla de casos compartida (3.1, 6.1) necesita probar el
  validador solo, con cada caso de `request-id.json`, sin pasar por `requestIdDe` ni por sus efectos
  (generar un UUID nuevo). La ruta `web/src/app/salud-web/route.ts`
  (`export const dynamic = "force-dynamic"`) hace `fetch` a `${PROPTECH_URL_API_INTERNA}/api/salud`
  con esa cabecera y un límite de 2 segundos (`LIMITE_MS`) implementado con `AbortController` propio y
  `setTimeout(() => controlador.abort(), LIMITE_MS)`, **no** `AbortSignal.timeout(2000)`: Vitest usa
  temporizadores falsos en los tests de esta ruta y `AbortSignal.timeout` arma su propio temporizador
  interno por fuera de los que Vitest controla, así que nunca dispara bajo `vi.useFakeTimers()` y el
  test quedaría esperando un abort real. Con `setTimeout` propio, el test avanza el reloj falso y lo
  ve disparar. Responde
  `{"web": "ok", "api": "ok" | "degradado" | "sin_conexion" | "sin_configurar"}` con 200 si la API dio
  200 y 503 si no. **Contrato** (spec "Contrato de respuesta de /salud-web"): exactamente esos dos
  campos, `Content-Type: application/json`, `api` derivado sólo del código de estado (200 es `ok`,
  cualquier otro es `degradado`, sin leer el cuerpo de la API); `sin_conexion` ante timeout o conexión
  rechazada; `sin_configurar` sin la variable, sin llamar a `fetch`; el mismo `X-Request-ID` que se
  reenvió va en la respuesta; nunca el texto del error ni la dirección interna (L-007). Variable
  `PROPTECH_URL_API_INTERNA=http://api:8000`, fija en Compose (no es
  secreto). Es la única llamada de la web a la API en este cambio; la usan las páginas reales desde el
  cambio 2. **Descartado** mostrar el estado en la página: es interfaz y pediría pasar por impeccable
  por una línea de texto.
- **La plantilla de la ruta (`_ruta_de`, `proptech_api/seguimiento.py`)**: `scope["route"].path_format`
  sólo trae la ruta relativa al router que la declara; con `include_router(prefix=...)` (el patrón de
  "routers por dominio") FastAPI 0.143 resuelve el prefijo de forma perezosa y no lo funde ahí. La ruta
  ya fundida con el prefijo vive en
  `scope["fastapi"]["effective_route_context"].path_format`, que FastAPI calcula una vez por
  combinación de router y cachea en esa clave; si no está (una ruta declarada directo en `app`, sin
  router con prefijo), `path_format` del route ya trae el camino completo y alcanza como respaldo.
  **Es un atributo interno de FastAPI**, no de su API pública: el test que lo ejerce queda documentado
  como riesgo de romperse al subir de versión (ver Risks); por eso FastAPI está fijado `<0.144` y un
  test dedicado lo detecta si cambia. **El prefijo `/api` se movió a `salud.router`**
  (`APIRouter(prefix="/api")`, en vez de pasarlo en `app.include_router(salud.router, prefix="/api")`
  como antes, y sin el `router_api` intermedio que existía para agrupar el prefijo): fijado en el
  router mismo, `path_format` ya lo trae desde que la ruta se define, sin depender de en qué nivel de
  `include_router` quedó el prefijo.
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

### D13 · Los errores de terceros no salen (L-007)

- Regla: ningún `str(error)` de redis-py, ARQ, psycopg o SQLAlchemy se copia a un log, a un error
  propio o a una respuesta. Lo que sale es el tipo (`tipo_error`), la ubicación (`traza`, D7) y una
  descripción propia.
- Dónde podría colarse y cómo se cierra:
  - **Formatter** (D7): usa `record.msg`, descarta `record.args` y no incluye el mensaje de la
    excepción. Cubre también los logs de ARQ y uvicorn, que pasan por los handlers que reemplaza
    `configurar_logs`.
  - **`ColaNoDisponible`**: se levanta con un mensaje fijo (`"cola no disponible"`) y `from None`
    para que el traceback no encadene el error de redis-py.
  - **Verificadores de salud**: devuelven sólo `ok` o `sin_conexion`.
  - **Arranque del worker**: reutiliza los mensajes de `Configuracion` y `leer_parametros`, que ya
    nombran la variable o el campo sin el valor (1b); nunca reenvía el error de pydantic o de PyYAML.
  - **Trabajo rechazado** (`pickle` u otro formato): el evento se loguea por plantilla, sin el
    contenido crudo del trabajo.
  - **`/salud-web`**: el `catch` mapea a un estado fijo, nunca a `error.message`.
- Cada punto tiene un test con un marcador en el mensaje del error de terceros que afirma que el
  marcador no aparece en la salida.

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

### D16 · `Dinero` copiable y serializable (A1)

- `Dinero` (1b) es inmutable: usa `__slots__` y un `__setattr__` que bloquea toda asignación. Por eso
  `copy.copy`, `copy.deepcopy` y `pickle` fallan hoy con `AttributeError`: los tres reconstruyen el
  objeto vacío y le asignan el estado con `setattr`. `model_copy(deep=True)` de pydantic usa
  `deepcopy` y falla igual con cualquier modelo que tenga un monto.
- Se agregan `__reduce__`, que devuelve `(Dinero, (self.a_texto(),))`, y `__copy__`/`__deepcopy__`,
  que devuelven `self` (un objeto inmutable no necesita copia). Reconstruir desde el texto hace que la
  carga pase por la misma validación que la construcción: un pickle armado a mano con `"1e3"` falla
  con `MontoInvalido` (L-008).
- **Por qué en este cambio y antes de la cola** (tarea 4.3, antes de 4.4): la auditoría lo pidió porque
  ARQ serializa los argumentos con `pickle` por defecto. En este cambio la cola usa JSON (D2) y los
  montos viajan como texto, así que por la cola nunca viaja un `Dinero`; lo que sí lo necesita es
  cualquier camino que copie o serialice un modelo con montos (`model_copy(deep=True)`, `deepcopy` de
  una estructura, un `ProcessPoolExecutor` en la generación de PDFs del cambio 7). Es la primera vez
  que el código sale del dominio puro y conviene que el tipo base no falle en esos caminos.
- **Descartado** quitar el `__setattr__` que bloquea la mutación: la inmutabilidad es la garantía de
  R07 y D-046.

### D17 · La API detrás del proxy (B6)

- `CMD` del backend: `uvicorn ... --no-access-log --proxy-headers`. Sin `--proxy-headers`, la API ve
  como cliente la dirección de Caddy y el esquema `http` aunque el pedido haya llegado por `https`.
- Uvicorn sólo confía en las cabeceras de reenvío que vienen de las direcciones de
  `FORWARDED_ALLOW_IPS` (por defecto `127.0.0.1`, que en un contenedor aparte nunca es Caddy). La red
  `interna` declara su subred y `caddy` recibe una dirección fija en ella; `api` recibe
  `FORWARDED_ALLOW_IPS` con **sólo esa dirección**.
- **Descartado** `FORWARDED_ALLOW_IPS=*` o la subred entera: la web y el worker comparten la red
  `interna` y podrían mandar a la API un `X-Forwarded-For` falso; cuando el cambio 2 sume el límite de
  intentos de login por dirección, ese valor decide a quién se bloquea.

### D18 · Contraseñas como secreto y un único engine por proceso (M12, M13, M14)

- **`SecretStr` (M12)**: `postgres_password` y `redis_password` pasan a `SecretStr` en
  `Configuracion`. `repr` y `str` muestran `**********`. El valor se lee con
  `get_secret_value()` sólo en el borde: `url_sqlalchemy()` en `configuracion.py` (que usan el engine y
  `env.py` de Alembic) y `conexion_redis.py` (D4). `Configuracion` es una clase común: el test cubre
  `repr`, `str` y `vars()`. Un test recorre el código fuente y exige que no aparezca en otro
  lado. Los validadores de vacía y en blanco se mantienen sobre el valor secreto.
  **M12 a medias**: `url_sqlalchemy()` devuelve un `str` con la contraseña ya interpolada (lo que
  usan el engine y `env.py` de Alembic para construirlo), no el objeto `sqlalchemy.engine.URL`
  renderizado sólo al convertirlo a texto en el borde, que era el pedido original de Alberto.
  **Alternativa elegida y qué se descartó**: se eligió el `str` porque Alembic (`env.py`) espera
  ese tipo en `config.set_main_option("sqlalchemy.url", ...)` y cambiar a un objeto `URL` ahí exige
  tocar también cómo Alembic arma su engine; se descartó por ahora armar el objeto `URL` y
  renderizarlo recién en el borde (lo que cerraría el pedido entero) porque el impacto de dejarlo así
  es bajo (la contraseña ya no vive en el `repr`/`str` de `Configuracion`, que era el riesgo que M12
  buscaba cerrar) y tocar Alembic no estaba en el alcance de este cambio. Deuda para el cambio 2.
- **`COTA_OPERACION_S = 1.5` (D3, F2b y F2c)**: cota propia de la operación de base que corre en el
  hilo de `tarea_de_prueba` (`asyncio.wait_for(asyncio.to_thread(...), timeout=COTA_OPERACION_S)`),
  menor que cualquier `job_timeout` configurado (120 s en producción, D2) con margen; nace **adentro**
  de `reintentable` para que un `TimeoutError` acá se reintente o agote con su propio evento, en vez
  de que ARQ dé el trabajo por fallado desde afuera cuando vence `job_timeout`.
  **Advertencia declarada**: esta cota, fija y genérica, no sirve para una tarea larga (un PDF, una
  llamada a un proveedor externo): el cambio 7, o quien agregue la primera tarea cuya operación de
  base sea más lenta que un `INSERT` simple, tiene que definir una cota propia por tarea, no reusar
  esta constante. Además, `asyncio.wait_for` corta la espera del event loop, nunca el hilo que sigue
  corriendo en segundo plano (F2c, ver la spec de `cola-de-trabajos`, "Límite conocido"): por sí sola
  no alcanza para una tarea con efecto real, que necesita además un corte del lado de la base.
- **Un único engine por proceso (M13)**: hoy `/api/salud` crea y descarta un engine en cada pedido. Se
  crea uno solo en el lifespan de `crear_app()`, se guarda en `app.state` y se descarta al cerrar; el
  verificador de base lo recibe inyectado. Una verificación fallida loguea `salud_degradada` con
  `dependencia` y `tipo_error`, nunca el mensaje de psycopg (L-007).
- **El congelamiento con una conexión ya abierta**: `connect_timeout` acota sólo el establecimiento
  de la conexión. Con un engine único, el pool reutiliza una conexión abierta, y si la base se pausa
  después, el `SELECT 1` (o el `pool_pre_ping`) queda esperando una respuesta que no llega: el kernel
  del contenedor pausado sigue aceptando los paquetes TCP, así que el socket no da error. El
  escenario "La base está congelada, no caída" de 1a pasaba porque cada pedido abría una conexión
  nueva. Por eso la verificación corre en un hilo con un plazo propio de 2 s y, si vence, responde
  `sin_conexion` e invalida esa conexión del pool; `pool_timeout` acota la espera si varias
  verificaciones colgadas agotan el pool. La tarea 3.6 lo prueba contra un PostgreSQL propio del test.
- **Parámetros del pool desde la configuración (M14)**: `DB_POOL_PRE_PING` (default `true`),
  `DB_POOL_SIZE` (5, rango 1..50), `DB_POOL_RECYCLE_S` (1800, 60..86400), `DB_POOL_TIMEOUT_S` (5,
  1..60) y `DB_CONNECT_TIMEOUT_S` (2, 1..30). Opcionales con default, así no se suma ninguna variable
  obligatoria a `.env`; cuando vienen, se validan con las cinco formas de L-002. Los usan el engine de la
  API y el del worker (gemelos, L-009). **Descartado** ponerlos en `config/parametros.yaml`: ese
  archivo es de parámetros del negocio (D-042), no de conexión.
- **Rechazo estricto de puertos (L-008)**: `_entero_ascii_estricto` (`configuracion.py`) exige
  `fullmatch` contra `[0-9]+` con `re.ASCII` antes de que pydantic convierta el valor a entero. Se
  aplica a los `DB_POOL_*` nuevos de este punto y, de paso, a `POSTGRES_PORT` y `REDIS_PORT`, que ya
  existían desde 1b: pydantic en modo laxo aceptaba `'5\n'`, `' 5'`, `'5.0'` o `'5_0'` (el separador de
  miles de `int()`) y los convertía sin avisar a un entero distinto del que parecía. **Cambia el
  comportamiento del 1b**: un valor de puerto que antes pasaba laxo ahora se rechaza. Aceptado y
  anotado como tal, en línea con L-008 (toda entrada externa valida con coincidencia completa y sólo
  ASCII): es la misma regla que ya regía para el resto de los enteros de configuración, aplicada
  también a los dos puertos que quedaron afuera cuando se escribió 1b.

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
- [`trabajos_hechos` crece sin límite] → Una fila por trabajo; al volumen del MVP son miles por año.
  Se poda cuando moleste, nunca antes de que pase el `keep_result` de ARQ.

- [Tamaño del cambio] → 35 tareas, por encima de las "unas veinte" de `openspec/config.yaml` y de las
  29 que registró D-088 como excepción. Las 29 eran el corte de D-087 (secciones 1 a 5 del cambio
  original, 23 tareas) más el cierre, con las tareas partidas para que ninguna supere medio día y las
  lecciones L-007 a L-009 sumadas. La tercera auditoría del socio (13/10) sumó seis: la línea de base
  sobre un clon con historial (1.2), PyYAML (1.3), las contraseñas como secreto (3.5), el engine único
  (3.6), `Dinero` copiable (4.3) y los logs de ARQ (5.7); el resto de sus pedidos entró como casos de
  tareas existentes. La cifra quedó registrada en D-090 (14/10), que corrige a D-088. El próximo corte natural sigue siendo sacar la web y el proxy (sección 6) a otro cambio; no
  se hace sin decisión de Juani.
- [El 1c se archiva sin el humo ampliado] → Los escenarios de punta a punta por el proxy (el
  `request_id` elegido por el cliente, de la web a la API, el worker con un reintento dentro del stack,
  Redis pausado detrás de Caddy) se verifican acá por partes: tests de la configuración de Caddy y
  Compose, de la ruta de la web con `fetch` simulado, del middleware y del worker en proceso. El humo
  existente sí levanta Redis y el worker y espera que estén saludables. La verificación de punta a
  punta la hace el humo del 1d (D-087), que no empieza sin el 1c archivado.

## Migration Plan

- Migración `0002` crea `trabajos_hechos`; su `downgrade` la borra. Probada ida y vuelta sobre base
  vacía (como `0001`).
- Para volver atrás: revertir el commit y `docker compose -p proptech down -v`.
- Al actualizar una copia local existente no hace falta tocar `.env`: este cambio no suma variables
  obligatorias (`REDIS_PASSWORD` ya está desde 1b, `PROPTECH_URL_API_INTERNA` y `FORWARDED_ALLOW_IPS`
  son fijas en Compose y los `DB_POOL_*` son opcionales con default, D18).

## Open Questions

Ninguna que cambie las specs o las tareas. Pendiente de la etapa de despliegue: logs estructurados de
la web y de Caddy (los de error de Caddy ya se filtran, D7). La cifra de 35 tareas quedó registrada en D-090.
