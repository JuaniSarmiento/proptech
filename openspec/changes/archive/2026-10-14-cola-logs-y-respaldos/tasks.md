Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el paso
rojo es obligatorio. Si un test nuevo pasa antes de escribir el código, no prueba nada: se corrige el
test hasta verlo fallar por la razón correcta y se informa. "Verde" quiere decir lint, formato, tipos y
tests del lado tocado (L-005). Los tests de dependencias usan los tres estados de L-001 con su cota de
tiempo afirmada; los de configuración, las cinco formas de L-002; todo texto externo se valida con
coincidencia completa y sólo ASCII (L-008); ningún mensaje de error de Redis, ARQ, psycopg o
SQLAlchemy llega a un log, a un error propio o a una respuesta sin un test con un marcador que pruebe
que no se repite (L-007). Cada tarea nombra los escenarios de la spec que cubre
(`capacidad` › escenario) y las lecciones que aplica. Ninguna tarea supera medio día.
Precondición: `arranque-del-sistema` archivado (ver design.md, Context). El apply corre sobre un clon
del repositorio **con su historial** (`.git` presente), nunca sobre una copia de los archivos: gitleaks,
`git check-ignore` y el clon limpio de 7.1 lo necesitan.

## 1. Línea de base y dependencias

- [x] 1.1 Correr la suite completa antes de tocar nada (`bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`) y anotar en el informe la cantidad de tests de cada lado como línea de base (L-003); si algo falla, frenar e informarlo como falla previa. Escenarios: ninguno (medición de partida). **Línea de base: backend 259 passed, web 1 passed (2026-10-12T12:58-12:59Z).**
- [x] 1.2 Repetir la línea de base sobre un clon del repositorio con su historial (`git clone` del remoto, no una copia sin `.git`; la de 1.1 no lo tenía): `git rev-parse HEAD`, `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`, `git check-ignore -v infra/.env` sobre un `.env` de prueba y gitleaks con la imagen y la configuración del CI. Pegar en esta tarea cada comando con su salida y la hora; ésta pasa a ser la línea de base contra la que compara 7.1. Si la cantidad de tests difiere de 1.1, explicar la diferencia antes de seguir; si algo falla, frenar e informarlo como falla previa. Escenarios: ninguno (medición de partida). Lecciones: L-003.

  **Evidencia (clon limpio en `/tmp/.../proptech-clon-1.2`, 2026-10-14):**

  ```
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:29:26Z
  $ git clone https://github.com/JuaniSarmiento/proptech.git proptech-clon-1.2
  Clonando en 'proptech-clon-1.2'...
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:29:28Z
  $ git rev-parse HEAD
  539d00572e45582f998007ecbcd8fb4b7d621834
  ```

  Nota: el HEAD del remoto (`539d005`) es un commit atrás del local (`1886b75`), que todavía no
  estaba pusheado al arrancar esta tarea. Diferencia: `git show --stat 1886b75` toca sólo
  `openspec/changes/cola-logs-y-respaldos/{design,proposal,tasks}.md` (docs), ningún archivo de
  `backend/` ni `web/`. El código y los tests del clon son equivalentes a los de 1.1.

  ```
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:29:44Z
  $ bash infra/ci/test-backend.sh
  ...
  ======================= 259 passed, 1 warning in 14.93s ========================
  ```

  259 passed: igual a la línea de base de 1.1 (backend 259 passed). Sin diferencia.

  ```
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:30:06Z
  $ bash infra/ci/test-web.sh
  ...
   Test Files  1 passed (1)
        Tests  1 passed (1)
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:30:07Z
  ```

  1 passed: igual a la línea de base de 1.1 (web 1 passed). Sin diferencia.

  ```
  $ echo "POSTGRES_PASSWORD=prueba-no-real-123" > infra/.env
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:30:29Z
  $ git check-ignore -v infra/.env
  .gitignore:16:.env	infra/.env
  exit: 0
  ```

  `.env` de prueba (valor inventado, sin secretos reales) correctamente ignorado por la regla
  `.gitignore:16:.env`. Se borró después de la verificación.

  ```
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:30:38Z
  $ docker run --rm -v "$PWD":/repo -w /repo zricethezav/gitleaks:v8.30.1 git --config /repo/.gitleaks.toml -v .
  1:30PM INF 42 commits scanned.
  1:30PM INF scanned ~1329333 bytes (1.33 MB) in 297ms
  1:30PM INF no leaks found
  exit: 0
  $ date -u +"%Y-%m-%dT%H:%M:%SZ"
  2026-10-14T13:30:39Z
  ```

  **Línea de base de 1.2 (contra la que compara 7.1): backend 259 passed, web 1 passed, HEAD del
  clon `539d00572e45582f998007ecbcd8fb4b7d621834` (2026-10-14T13:29:26Z a 13:30:39Z).**
- [x] 1.3 Test en `tests/infra/` que exige en `pyproject.toml` `pyyaml>=6.0.3,<7` y que `uv.lock` resuelva PyYAML 6.0.3 o posterior. Verlo fallar (hoy dice `>=6.0.2`), subir la dependencia, regenerar el lock con `uv lock`, correr `uv sync --locked` y verlo pasar. Por qué: no hay wheel de PyYAML 6.0.2 para Python 3.14 en Windows y la instalación cae a compilar. Escenarios: `integracion-continua` › PyYAML con wheel para Python 3.14. Lecciones: L-005.

## 2. Logs estructurados

- [x] 2.1 Tests del formatter de `proptech_core/compartido/logs.py`: una sola línea JSON aunque un valor tenga saltos de línea; `ts` UTC con milisegundos; campos base presentes y en el orden de D7; niveles en minúscula; un `extra` fuera de la lista cerrada se descarta y `campos_descartados` lo cuenta; `logger.info("pago de %s", dato)` deja la plantilla y no el dato. Verlos fallar e implementar el formatter (D7). Escenarios: `trazabilidad-y-logs` › Campo no permitido; › Mensaje con argumentos; › Línea de un pedido atendido (formato de la línea). Lecciones: L-005.
- [x] 2.2 Tests de excepciones y de `configurar_logs(servicio)`: con una excepción, `tipo_error` (nombre calificado) y `traza` (hasta 10 cuadros `modulo:línea:función`) sin el mensaje ni las líneas de código; con un error real de `psycopg.OperationalError` armado con un marcador en el mensaje, el marcador no aparece en la salida (los errores de redis-py y de ARQ se prueban en 4.4 y 5.6, cuando sus dependencias ya existen); `configurar_logs` reemplaza los handlers de la raíz, `uvicorn`, `uvicorn.error` y `arq`, llamarla dos veces no duplica líneas y un log de `arq` con argumentos sale como plantilla. Verlos fallar, implementar, verlos pasar. Escenarios: `trazabilidad-y-logs` › Error de un tercero con datos en su mensaje; › Mensaje con argumentos. Lecciones: L-007.
- [x] 2.3 Tests en `tests/infra/` que exigen el `CMD` del `backend/Dockerfile` con `--no-access-log` y `--proxy-headers`, y `FORWARDED_ALLOW_IPS` en el servicio `api` igual a la dirección fija de `caddy` en la red `interna` (nunca `*` ni una subred entera); la red `interna` con subred declarada y `caddy` con esa dirección; `log_line_prefix=%m [%p] %q%a ` en el servicio `db`; y el ancla de rotación `x-logs` (`json-file`, `max-size`, `max-file`) aplicada a todos los servicios de `compose.yaml`. Verlos fallar, cambiar los archivos (D7, D17), verlos pasar. Escenarios: `entorno-de-ejecucion` › Rotación declarada; › La API confía sólo en el proxy; `trazabilidad-y-logs` › Query string con un dato personal (sin log de acceso de uvicorn). Lecciones: L-005.

## 3. Número de seguimiento y conexión a la base en la API

- [x] 3.1 Escribir la tabla de casos `config/contratos/request-id.json` (válidos con su forma normalizada; inválidos con su motivo): UUID en minúsculas, en mayúsculas (se normaliza), vacío, 35 y 37 caracteres, sin guiones, con llaves, espacio y tabulación alrededor, salto de línea al principio y al final, un dígito reemplazado por un dígito árabe-índico, una letra de ancho completo, `<script>`, comillas y `' OR 1=1 --`. Test de pytest que exige que la tabla tenga al menos un caso de cada motivo de esa lista (así no se puede vaciar) y recorre todos los casos contra `validar_request_id` de `proptech_core/compartido/seguimiento.py`. Verlos fallar e implementar con `re.fullmatch(..., flags=re.ASCII)` validando antes de pasar a minúsculas (D8). Escenarios: `trazabilidad-y-logs` › UUID con espacios, tabulaciones, saltos de línea o dígitos no ASCII; › UUID en mayúsculas; › Número de seguimiento malicioso; › Mismos casos en la web y en la API (lado Python). Lecciones: L-008, L-009.
- [x] 3.2 Tests del middleware con `TestClient`: sin encabezado, la respuesta trae un UUID en `X-Request-ID` y la línea `pedido_atendido` lo lleva junto con método, ruta (plantilla), estado y duración; con uno de la tabla de inválidos, la respuesta trae otro y ningún log contiene el valor recibido; `GET /api/salud?email=vecino@ejemplo.invalid` no deja ni el email ni `email=` en los logs; una ruta sin coincidencia loguea el path truncado a 200 sin query string; un endpoint `def` de prueba ve el `request_id` en sus logs (la `ContextVar` llega al hilo). Verlos fallar, implementar el middleware ASGI puro y llamar a `configurar_logs` en `crear_app()` (D8), verlos pasar. Escenarios: `trazabilidad-y-logs` › Pedido sin número de seguimiento; › Número de seguimiento malicioso; › Línea de un pedido atendido; › Query string con un dato personal.
- [x] 3.3 Test de error inesperado: un endpoint de prueba que lanza una excepción con un dato personal en el mensaje responde 500 `{"error": "interno", "request_id": ...}` y ni la respuesta ni los logs contienen el dato; lo mismo con un `sqlalchemy.exc.IntegrityError` cuyo mensaje trae un parámetro de SQL marcado. Verlo fallar, implementar, verlo pasar. Escenarios: `trazabilidad-y-logs` › Error inesperado; › Error de un tercero con datos en su mensaje. Lecciones: L-007.
- [x] 3.4 Tests de integración del `application_name` contra PostgreSQL real (contenedor de test con el `log_line_prefix` de D7): dentro de una transacción con `request_id` R, `current_setting('application_name')` contiene R; en la transacción siguiente de la misma conexión, no; un error provocado (`SELECT 1/0`) deja en los logs del contenedor una línea con R. Verlos fallar, implementar el evento `after_begin` con parámetro ligado y el nombre base en `connect_args`, verlos pasar. Escenarios: `trazabilidad-y-logs` › En la sesión de la base.
- [x] 3.5 Tests de `Configuracion` con contraseñas marcadas: `postgres_password` y `redis_password` son `SecretStr`; `repr()`, `str()`, `vars()` y `json.dumps(vars(...), default=str)` de la configuración no contienen ninguna de las dos (`Configuracion` es una clase común, no un modelo pydantic); la URL con contraseña sólo la arma `url_sqlalchemy()` al crear el engine; un test recorre el código fuente y exige que `get_secret_value` aparezca sólo en `proptech_core/compartido/configuracion.py` (`url_sqlalchemy`) y en `proptech_core/compartido/conexion_redis.py` (que crea 4.4 y del que toman la conexión el adaptador de cola, el verificador de salud de 4.6 y los `RedisSettings` del worker de 5.5). Las contraseñas vacías o en blanco se siguen rechazando nombrando la variable y los cuatro tests de arranque de la API siguen pasando. Verlos fallar, implementar (D18), verlos pasar. Escenarios: `entorno-de-ejecucion` › Contraseñas fuera de la representación de la configuración; › API sin cadena de conexión (regresión). Lecciones: L-002, L-007.
- [x] 3.6 Tests del engine único y de su pool: `crear_app()` crea un solo engine en el lifespan, lo guarda en `app.state` y lo descarta al cerrar; diez pedidos a `/api/salud` no crean engines nuevos (espía sobre `crear_engine`); el engine toma de la configuración `pool_pre_ping`, `pool_size`, `pool_recycle`, `pool_timeout` y `connect_timeout` (opcionales con default, y con las cinco formas de L-002 cuando vienen: faltante usa el default; vacía, en blanco, `abc` y fuera de rango terminan nombrando la variable); con la base caída, `/api/salud` responde 503 y loguea `salud_degradada` con `dependencia: base` y `tipo_error`, sin el mensaje de psycopg (marcador en el error); contra un PostgreSQL propio del test (L-006), con una conexión ya abierta en el pool y la base pausada **después**, `/api/salud` responde 503 en menos de 3 s (cota afirmada; `connect_timeout` no cubre una conexión ya abierta, D18) y, despausada, el siguiente pedido responde 200. Verlos fallar, implementar, verlos pasar. Escenarios: `entorno-de-ejecucion` › Un solo engine por proceso; › La base se congela con una conexión abierta; › La base no responde; › La base está congelada, no caída (regresión). Lecciones: L-001, L-002, L-006, L-007.

## 4. Redis y la cola

- [x] 4.1 Tests en `tests/infra/test_compose.py`: servicio `redis` con imagen `redis:8.10.2-trixie`, sólo en la red `interna`, sin `ports`, con el volumen con nombre `datos_redis` en `/data`, `--appendonly yes`, `--maxmemory-policy noeviction`, `--requirepass` desde `REDIS_PASSWORD` con `:?`, primer argumento `redis-server` (baja a usuario `redis`) y healthcheck con `REDISCLI_AUTH` y `$$`. Verlos fallar, agregar el servicio (D1), verlos pasar. Escenarios: `cola-de-trabajos` › Declaración del servicio Redis; `entorno-de-ejecucion` › Intento de conexión directa a Redis desde el host; › Redis sin contraseña; › Usuario del proceso (Redis); › Falta el archivo de entorno (contraseña de Redis).
- [x] 4.2 Test en `tests/infra/` que exige en `pyproject.toml` `arq==0.28.0` y `redis[hiredis]>=5.3.1,<6` y prohíbe `testcontainers[redis]`; verlo fallar, agregar las dependencias y correr `uv lock` (D1). Agregar el fixture `redis_contenedor` con `DockerContainer` genérico (D12) y extender a Redis el test de imagen real contra Compose y el que prohíbe imágenes escritas a mano; verlo fallar forzando otra imagen en el fixture y verificar que el error nombra las dos. Escenarios: `integracion-continua` › Versión de PostgreSQL desalineada (Redis); › La imagen de los tests no está escrita a mano; › Worker contra Redis real (infraestructura del test).
- [x] 4.3 Tests de `Dinero` copiable y serializable: ida y vuelta por `pickle` en todos los protocolos (0 a `pickle.HIGHEST_PROTOCOL`) da un monto igual con el mismo texto; `copy.copy` y `copy.deepcopy` devuelven el mismo objeto (`is`); un modelo pydantic con un campo `Dinero` sobrevive a `model_copy(deep=True)` y a la ida y vuelta por `pickle`; un pickle armado a mano con un texto de monto inválido levanta `MontoInvalido` al cargarse (la reconstrucción pasa por la validación). Verlos fallar (hoy `copy.copy`, `copy.deepcopy` y `pickle` levantan `AttributeError` contra el `__setattr__` que bloquea la mutación), implementar `__reduce__` (reconstruye desde `a_texto()`), `__copy__` y `__deepcopy__` (devuelven `self`) (D16), verlos pasar. Va antes de la primera tarea de la cola que recibe montos (4.4). Escenarios: `representacion-de-montos` › Ida y vuelta por pickle; › Copia superficial y profunda; › Copia profunda de un modelo con montos; › Pickle con un monto inválido. Lecciones: L-008.
- [x] 4.4 Tests de integración del adaptador de cola contra Redis real: encola y devuelve `encolado`; la misma clave dos veces devuelve `ya_encolado`; el trabajo crudo en Redis es JSON con los argumentos por nombre; un argumento `float` o `Decimal`, suelto o anidado en una lista o un mapa (y un `Dinero` sin pasar a texto), se rechaza antes de tocar Redis con `ArgumentoNoPermitido`, cuyo mensaje nombra el campo (`monto`, `montos[1]`, `detalle.total`) sin su valor, y no queda nada encolado; un `redis.exceptions.ConnectionError` real con un marcador en el mensaje, pasado por `configurar_logs`, no deja el marcador en la salida (caso de redis-py que no entra en 2.2). Verlos fallar, implementar el puerto `Cola`, la validación de tipos de `encolar`, `proptech_core/compartido/conexion_redis.py` (único lugar que lee la contraseña de Redis, D4, D18) y el adaptador ARQ con serializador JSON (D2, D4), verlos pasar. Escenarios: `cola-de-trabajos` › Mismo trabajo encolado dos veces; › Trabajo encolado inspeccionado en Redis; › Monto como número al encolar. Lecciones: L-007.
- [x] 4.5 Tests de los tres estados del adaptador, cada uno con su cota afirmada y sobre un contenedor de Redis propio del test (nunca el de sesión ni el de Compose, despausado en un `finally`): detenido, pausado y con `DEBUG SLEEP` por encima del límite dan `ColaNoDisponible` en menos de 3 s; con `DEBUG SLEEP` por debajo del límite, encola; después de despausar, el siguiente encolado funciona (el pool se recrea); el mensaje de `ColaNoDisponible` y los logs no contienen el host, el puerto ni el texto del error de redis-py. Verlos fallar, implementar el pool perezoso, el `asyncio.timeout` y el descarte del pool (D4), verlos pasar. Escenarios: `cola-de-trabajos` › Redis caído; › Redis congelado; › Redis lento. Lecciones: L-001, L-006, L-007.
- [x] 4.6 Tests unitarios de `/api/salud` con verificador de cola inyectado: todo ok da 200 con `cola: ok`; cola caída da 503 `{"estado":"degradado","base":"ok","cola":"sin_conexion"}`; base caída da `base: sin_conexion` y `cola: ok`; las dos caídas; los mismos tests de "el cuerpo nunca trae host, usuario ni texto de excepción" que ya tiene el verificador de base, aplicados al de cola con un marcador en el mensaje de la excepción. Verlos fallar, implementar el verificador de cola (D4), verlos pasar. Escenarios: `entorno-de-ejecucion` › Todo funciona; › La base no responde; › La cola no responde; › La base y la cola no responden. Lecciones: L-007, L-009.
- [x] 4.7 Tests de integración de la salud y del arranque: con Redis pausado y con Redis detenido (contenedor propio), `/api/salud` responde 503 `cola: sin_conexion` en menos de 4 s; la app creada con `crear_app()` expone la cola cableada y, con Redis inalcanzable, arranca sin intentar conectar y responde `/api/salud`. Verlos fallar (la cola todavía no está cableada en `crear_app()`), cablearla, verlos pasar. Escenarios: `entorno-de-ejecucion` › La cola no responde; `cola-de-trabajos` › La API arranca sin Redis. Lecciones: L-001.

## 5. Worker e idempotencia

- [x] 5.1 Test de integración de la migración `0002`: ida y vuelta sobre base vacía, la tabla `trabajos_hechos` con sus columnas, PK y `CHECK` del largo de la clave (vacía y de 201 caracteres rechazadas). Además, en el mismo proceso: llamar a `configurar_logs`, correr `alembic upgrade head` y afirmar que un logger de `proptech_core` creado antes sigue escribiendo su línea JSON (hoy `fileConfig` de `migraciones/env.py` corre con `disable_existing_loggers=True` y lo apaga). Verlo fallar, escribir la migración (D3) y llamar a `fileConfig(..., disable_existing_loggers=False)` (D7), verlo pasar. Escenarios: `cola-de-trabajos` › Trabajo ejecutado dos veces (la unicidad que lo sostiene); `integracion-continua` › Migraciones en el CI; `trazabilidad-y-logs` › Las migraciones no apagan los logs.
- [x] 5.2 Tests de integración de `ejecutar_una_vez` contra PostgreSQL real: la primera ejecución corre el efecto y registra la clave con su `request_id`; la segunda devuelve `False` sin correr el efecto; si el efecto lanza, no queda la clave y un segundo intento completa; dos hilos simultáneos con la misma clave: el efecto corre una sola vez y el otro devuelve `False`. Verlos fallar, implementar en `proptech_core/compartido/idempotencia.py`, verlos pasar. Escenarios: `cola-de-trabajos` › Trabajo ejecutado dos veces; › Dos ejecuciones simultáneas; › El efecto falla después de reservar la clave.
- [x] 5.3 Tests unitarios de la política de reintentos: esperas 2, 4, 8, 16 con base 2; un error pasajero levanta `Retry` con esa espera y loguea `reintento_programado`; en el intento 5 loguea `tarea_agotada` con nivel `error` y relanza; un error no pasajero loguea `tarea_fallida` y no levanta `Retry`; `OperationalError` y `ConnectionError` cuentan como pasajeros; ninguno de esos eventos contiene el mensaje de la excepción (marcador). Verlos fallar, implementar `reintentable` (D3), verlos pasar. Escenarios: `cola-de-trabajos` › Falla pasajera y después éxito (esperas); › Intentos agotados (evento); › Error que no es pasajero. Lecciones: L-007.
- [x] 5.4 Tests unitarios de la tarea de prueba y su modelo de argumentos: `fallar_veces` -1, 11, `"3"`, `True` y `2.5` se rechazan al encolar con un error que nombra el campo y sin encolar nada; 0 y 10 se aceptan; ninguna ruta de `crear_app()` encola la tarea de prueba. Verlos fallar, implementar el modelo (entero estricto) y `tarea_de_prueba` (D3), verlos pasar. Escenarios: `cola-de-trabajos` › Cantidad de fallas fuera de rango; › Sin ruta pública para la tarea de prueba. Lecciones: L-008.
- [x] 5.5 Tests de integración del worker en proceso (`burst=True`, espera base 0,05 s) con Redis y PostgreSQL reales: con 0 fallas registra la clave en un intento; con 2 fallas, 3 intentos y una sola fila; las líneas del worker y la fila llevan el `request_id` con que se encoló; un `request_id` inválido en el trabajo se reemplaza y se loguea `request_id_reemplazado`; el engine del worker toma de la configuración los mismos parámetros de pool que el de la API (gemelo de 3.6, L-009, D18). Verlos fallar, implementar `proptech_worker/ajustes.py` (D2, D3, D8), verlos pasar. Escenarios: `cola-de-trabajos` › Tarea de prueba exitosa; › Falla pasajera y después éxito; `trazabilidad-y-logs` › Hasta el worker.
- [x] 5.6 Tests de integración del worker en proceso, caminos de falla: con 5 fallas, 5 intentos, último evento `tarea_agotada` y ninguna fila; un trabajo serializado con `pickle`, con un marcador en su contenido, metido a mano en la cola no se ejecuta y ninguna línea de log (incluidas las de ARQ) contiene el marcador; un error real de ARQ armado con un marcador en el mensaje, pasado por `configurar_logs`, tampoco lo deja en la salida (caso de ARQ que no entra en 2.2). Verlos fallar, ajustar, verlos pasar. Escenarios: `cola-de-trabajos` › Intentos agotados; › Trabajo con formato ajeno; `trazabilidad-y-logs` › Error de un tercero con datos en su mensaje. Lecciones: L-007.

  **B2 (cierre de la vuelta 3, veredicto del auditor): rojo de mutación sobre el código de producción que cubre esta tarea.**
  No hay `git diff` posible porque estos archivos todavía no están commiteados en
  ningún lado (todo el cambio 1c sigue sin commit): la comparación "antes/después
  de la mutación" se hizo con `diff` contra una copia en `/tmp` sacada ANTES de
  mutar, no contra el working tree de git.

  *Mutación 1 — `tarea_agotada` (`proptech_core/compartido/reintentos.py`):*
  ```
  $ cp src/proptech_core/compartido/reintentos.py /tmp/reintentos.py.bak5.6
  $ sed -i 's/if intento >= politica.intentos_maximos:/if intento >= politica.intentos_maximos + 999:  # MUTACION B2/' \
      src/proptech_core/compartido/reintentos.py

  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && uv run pytest tests/integracion/test_worker_caminos_de_falla.py::test_cinco_fallas_cinco_intentos_tarea_agotada_y_ninguna_fila -v
  2026-10-14T18:32:39Z
  ...
  >       assert len(reintentos) == 4, lineas  # 4 reintentos + el 5to intento agotado = 5
  E       AssertionError: [...]
  E       assert 5 == 4
  (nunca loguea "tarea_agotada": con la condición rota, el 5to intento también
  cuenta como "reintento_programado" en vez de agotarse)
  FAILED ... 1 failed in 5.63s

  $ cp /tmp/reintentos.py.bak5.6 src/proptech_core/compartido/reintentos.py
  $ diff /tmp/reintentos.py.bak5.6 src/proptech_core/compartido/reintentos.py && echo "IDENTICO reintentos.py"
  IDENTICO reintentos.py

  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && uv run pytest tests/integracion/test_worker_caminos_de_falla.py -v
  2026-10-14T18:33:05Z
  ======================== 3 passed, 2 warnings in 4.78s =========================
  ```

  *Mutación 2 — rechazo de `pickle` (`proptech_core/compartido/cola.py`,
  `deserializar_job`):*
  ```
  $ cp src/proptech_core/compartido/cola.py /tmp/cola.py.bak5.6
  # deserializar_job pasa de json.loads(datos) a pickle.loads(datos) (MUTACION B2)

  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && uv run pytest tests/integracion/test_worker_caminos_de_falla.py::test_trabajo_con_pickle_no_se_ejecuta_y_no_deja_el_marcador -v
  2026-10-14T18:33:25Z
  >           assert _fila(ajustes_del_worker, job_id) is None
  E           AssertionError: assert ('worker-pickle-2662f406-...',) is None
  (el pickle armado a mano SÍ se deserializa y la tarea corre: queda fila)
  FAILED ... 1 failed in ...s

  $ cp /tmp/cola.py.bak5.6 src/proptech_core/compartido/cola.py
  $ diff /tmp/cola.py.bak5.6 src/proptech_core/compartido/cola.py && echo "IDENTICO cola.py"
  IDENTICO cola.py

  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && uv run pytest tests/integracion/test_worker_caminos_de_falla.py -v
  2026-10-14T18:33:37Z
  ======================== 3 passed, 2 warnings in 4.77s =========================
  ```
- [x] 5.7 Test de integración del worker en proceso sobre los logs de ARQ: encolar la tarea de prueba con un argumento extra marcado (que la tarea recibe en `**datos`) y registrar en el worker de test una tarea que devuelve un resultado marcado; correr el worker en `burst` capturando la salida estándar, la de error y todos los loggers (incluidos `arq.worker` y `arq.jobs`, que por defecto escriben los argumentos y el resultado de cada trabajo) y afirmar que ninguno de los dos marcadores aparece en ninguna línea. Verlo fallar con el handler por defecto de ARQ (sin `configurar_logs`), que sí los escribe, para probar que el test detecta la fuga; después correrlo con la configuración real del worker (`configurar_logs` y `log_results = False` en `AjustesDelWorker`, D7) y verlo pasar. Escenarios: `trazabilidad-y-logs` › Argumentos y resultado de un trabajo. Lecciones: L-007.
- [x] 5.8 Test de integración de base caída durante el trabajo: con un PostgreSQL propio del test pausado en el primer intento y despausado antes del segundo (en un `finally`), la tarea se reintenta como pasajera y registra la clave una vez, con la cota afirmada. Verlo fallar, ajustar, verlo pasar. Escenarios: `cola-de-trabajos` › Base caída durante el trabajo. Lecciones: L-001, L-006.
- [x] 5.9 Tests de arranque del worker que replican, uno por uno y como proceso aparte, los cuatro que ya tiene la API: `test_arranque_api.py` (falta `POSTGRES_PASSWORD`), `test_arranque_api_variable_malformada.py` (`REDIS_PORT=abc`, y además `70000`), `test_arranque_api_password_vacio.py` (`REDIS_PASSWORD` vacía, y además en blanco) y `test_arranque_api_parametros.py` (tasa negativa nombrando `intereses.tasa_mensual`, `PROPTECH_PARAMETROS` faltante, vacía e inexistente); en cada uno el proceso termina, nombra la variable o el campo y su salida no contiene ninguna contraseña ni el texto del error de pydantic o de PyYAML. Verlos fallar, implementar el `on_startup` con `Configuracion`, `leer_parametros` y `configurar_logs`, verlos pasar. Escenarios: `cola-de-trabajos` › Worker sin una variable obligatoria; › Worker con variables de Redis rotas; › Worker con parámetros inválidos; `entorno-de-ejecucion` › Variables de Redis rotas; › Archivo de parámetros inexistente. Lecciones: L-002, L-007, L-009.

  **B2 (cierre de la vuelta 3, veredicto del auditor): rojo de mutación sobre
  el fail-fast de `proptech_worker/ajustes.py`.** Mismo aviso que en 5.6: sin
  `git diff` posible (archivo sin commitear); comparación contra copia en
  `/tmp` tomada antes de mutar.
  ```
  $ cp src/proptech_worker/ajustes.py /tmp/ajustes.py.bak5.9
  $ sed -i 's/^_configuracion = Configuracion()$/_configuracion = None  # MUTACION B2 (deshabilita el fail-fast)/' \
      src/proptech_worker/ajustes.py

  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && uv run pytest tests/unitarios/test_arranque_worker.py \
      tests/unitarios/test_arranque_worker_variable_malformada.py \
      tests/unitarios/test_arranque_worker_password_vacio.py \
      tests/unitarios/test_arranque_worker_parametros.py -v
  2026-10-14T18:34:08Z
  >       assert "POSTGRES_PASSWORD" in resultado.stderr, (...)
  E       AssertionError: el error no nombra la variable faltante: 'Traceback ...
  AttributeError: \'NoneType\' object has no attribute \'proptech_parametros\'
  (con `_configuracion = None`, `leer_parametros(_configuracion.proptech_parametros)`
  explota con un `AttributeError` genérico en vez del fail-fast que nombra la
  variable rota: cambia la EXCEPCIÓN, no sólo el texto)
  10 failed, 1 passed in 4.54s

  $ cp /tmp/ajustes.py.bak5.9 src/proptech_worker/ajustes.py
  $ diff /tmp/ajustes.py.bak5.9 src/proptech_worker/ajustes.py && echo "IDENTICO ajustes.py"
  IDENTICO ajustes.py

  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && uv run pytest tests/unitarios/test_arranque_worker.py \
      tests/unitarios/test_arranque_worker_variable_malformada.py \
      tests/unitarios/test_arranque_worker_password_vacio.py \
      tests/unitarios/test_arranque_worker_parametros.py -v
  2026-10-14T18:34:24Z
  ============================== 11 passed in 4.53s ==============================
  ```
- [x] 5.10 Tests en `tests/infra/test_compose.py` del servicio `worker`: imagen `proptech-backend:local`, comando `arq proptech_worker.ajustes.AjustesDelWorker`, healthcheck `arq --check`, redes `interna` y `salida_worker` (esta última sin `internal`, y ningún otro servicio en ella: ni `db`, ni `redis`, ni `api`), sin `ports`, dependencias de `db` y `redis` saludables y `migraciones` completado, `../config` montado de sólo lectura, `PROPTECH_PARAMETROS` y las variables de Redis con la contraseña obligatoria, ancla `x-logs`. Verlos fallar, agregar el servicio y la red (D2), verlos pasar. Escenarios: `cola-de-trabajos` › Worker saludable en el stack (declaración); `entorno-de-ejecucion` › El stack pasa la configuración nueva a la API; › Puertos publicados del stack levantado (declaración); › Red de salida del worker; › Usuario del proceso (worker).
- [x] 5.11 Test del comando `python -m proptech_worker.prueba encolar --fallar-veces N` contra Redis real: imprime la clave y el `request_id` generados y el trabajo queda en la cola; con `N` fuera de rango termina con código distinto de 0 nombrando el campo. Verlo fallar, implementar, verlo pasar. Escenarios: `cola-de-trabajos` › Tarea de prueba exitosa (forma de encolarla que usa el humo del 1d); › Cantidad de fallas fuera de rango.

## 6. Web y proxy

- [x] 6.1 Tests Vitest de `web/src/lib/seguimiento.ts` que leen la misma tabla `config/contratos/request-id.json` que pytest (con `fs` en tiempo de test, nunca con `import` del JSON: el contexto de build de la web es `web/` y no ve `config/`) y exigen los mismos motivos mínimos: cada válido se reenvía normalizado, cada inválido (incluidos los de espacios, tabulación, saltos de línea, dígito árabe-índico y letra de ancho completo) genera uno nuevo con forma de UUID; `cabecerasHaciaLaApi` arma `X-Request-ID`. Verlos fallar, implementar con una expresión anclada sin bandera `m` y con clases `[0-9a-fA-F]` explícitas, validando antes de pasar a minúsculas (D8), verlos pasar. Escenarios: `trazabilidad-y-logs` › Mismos casos en la web y en la API (lado TypeScript); › UUID con espacios, tabulaciones, saltos de línea o dígitos no ASCII; › De la web a la API (reenvío). Lecciones: L-008, L-009.
- [x] 6.2 Tests Vitest de `web/src/app/salud-web/route.ts` con `fetch` simulado, camino de respuesta: API 200 da 200 con exactamente `{"web":"ok","api":"ok"}`, `Content-Type` JSON y el mismo `X-Request-ID` en la llamada a la API y en la respuesta; API 503 da 503 `api: degradado`; API 500 con un cuerpo marcado da 503 `api: degradado` sin el cuerpo. Verlos fallar, implementar con `dynamic = "force-dynamic"` (D8), verlos pasar. Escenarios: `trazabilidad-y-logs` › API saludable; › API degradada; › API con un error inesperado.
- [x] 6.3 Tests Vitest de `/salud-web`, caminos de falla: API que no contesta corta a los 2 s con 503 `api: sin_conexion` (cota afirmada con temporizadores falsos); conexión rechazada da 503 `sin_conexion`; sin `PROPTECH_URL_API_INTERNA` da 503 `sin_configurar` sin llamar a `fetch`; un error de `fetch` con un marcador en el mensaje no aparece en la respuesta. Verlos fallar, implementar, verlos pasar. Escenarios: `trazabilidad-y-logs` › API caída o colgada; › API que no contesta; › Conexión rechazada; › Sin dirección de la API; › Error con datos en su mensaje. Lecciones: L-001, L-007.
- [x] 6.4 Tests en `tests/infra/` que exigen en el `Caddyfile` `request_header X-Request-ID {http.request.uuid}`, `header X-Request-ID {http.request.uuid}` y, en las opciones globales, el logger por defecto con `format filter` que borra `request>uri` y `request>headers` (D7); que `caddy adapt --validate` con la imagen de Caddy de Compose acepta el archivo y el JSON resultante lleva esos dos filtros; y en Compose `PROPTECH_URL_API_INTERNA=http://api:8000` en `web`. Verlos fallar, cambiar los archivos, verlos pasar. Escenarios: `trazabilidad-y-logs` › Cliente que manda su propio número (configuración del proxy; la verificación de punta a punta es del humo del 1d); › De la web a la API (configuración); › Error del proxy con un dato en la query (configuración). Lecciones: L-007.

## 7. Cierre: corrida equivalente al CI

- [x] 7.1 Desde un clon limpio del repositorio con su historial, siguiendo sólo el README (que este cambio no modifica), correr en este orden todos los pasos del workflow y adjuntar cada comando con su salida y la hora: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `bash infra/ci/test-backend.sh`, `bash infra/ci/canario.sh backend`, `pnpm install --frozen-lockfile`, `pnpm biome ci`, `pnpm tsc --noEmit`, `bash infra/ci/test-web.sh`, `bash infra/ci/canario.sh web`, `bash infra/ci/humo.sh` (el existente, que con `--wait` espera a Redis y al worker saludables y verifica que sigue habiendo un solo servicio con puertos) y gitleaks con la imagen y la configuración del CI. Informar la cantidad de tests de cada lado contra la línea de base de 1.2 y explicar todo test salteado o deseleccionado. Escenarios: `entorno-de-ejecucion` › Clon limpio siguiendo el README; › Puertos publicados del stack levantado; `cola-de-trabajos` › Worker saludable en el stack; y, como regresión de los requisitos que este cambio reescribe sin tocar su comportamiento (los cubren los tests y el humo existentes, que no pueden bajar): `entorno-de-ejecucion` › Intento de conexión directa a la base desde el host; › La base está congelada, no caída; › Archivo de entorno ignorado; › Imagen sin archivo de entorno; › API sin cadena de conexión; › Migraciones sólo con las variables de la base. Lecciones: L-003, L-005.

  **Cómo se resolvió el bloqueo de la primera vuelta** (no commitear/pushear
  impedía un `git clone` con el código terminado): se clonó el repositorio
  local con su historial a un directorio temporal fuera del repo (`git
  clone`, sin tocar `origin`), y encima se copiaron **sólo los archivos que
  git versionaría hoy** (`git ls-files -z -c -o --exclude-standard | rsync
  --from0 --files-from=-`), sin `.venv`, `node_modules`, `.env` ni artefactos
  locales. Se verificó que `git status --short` del clon coincide exactamente
  (mismas 65 rutas) con el del repo original antes de correr nada. Sigue sin
  haber ningún commit ni push: el clon vive en un directorio temporal, se usó
  y se borró al final.

  **B1 (cierre de la vuelta 3, veredicto del auditor): se repitió esta tarea
  completa con el código final**, después de las tres correcciones de esta
  vuelta (comentario de `tareas.py`, test de F2c como `xfail`, evidencia de
  mutación de 5.6/5.9). La evidencia de abajo **reemplaza** la de la corrida
  anterior (2026-10-14T16:01–16:08Z, backend 447 passed): ese número ya no
  describe el código actual. La diferencia no es sólo el test `xfail` de
  F2c (que suma 1): es casi toda de los tests de ataque de las vueltas 2 y 3
  del rompedor que quedaron en el repo (`test_ataque_*`, `test_zz_rompedor_*`);
  el detalle completo del conteo está más abajo, en la comparación contra la
  línea de base de 1.2.

  **Evidencia (clon limpio en un directorio temporal, 2026-10-14, vuelta 3):**

  ```
  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && git clone /home/juanisarmiento/Proyectos/PropTech <scratch>/proptech-limpio-v3
  2026-10-14T18:35:25Z
  hecho.
  $ git -C <scratch>/proptech-limpio-v3 rev-parse HEAD
  1886b75fc1102c27fe8271fef110651942dc526b   # mismo HEAD que el repo local (nada de este cambio está commiteado)

  $ git ls-files -z -c -o --exclude-standard | rsync -a --from0 --files-from=- ./ <scratch>/proptech-limpio-v3/
  2026-10-14T18:35:40Z  (sin salida, exit 0)

  $ git status --porcelain | sort > /tmp/orig_status_v3.txt
  $ git -C <scratch>/proptech-limpio-v3 status --short | sort > /tmp/clon_status_v3.txt
  $ diff /tmp/orig_status_v3.txt /tmp/clon_status_v3.txt; echo "exit: $?"
  exit: 0   # 78 archivos en cada lado, lista idéntica (más que las 65 de la
            # vuelta anterior: esta vuelta sumó, entre otros, los tests de
            # ataque copiados del rompedor y el nuevo test xfail de F2c)
  $ find <scratch>/proptech-limpio-v3 -maxdepth 3 -iname ".venv" -o -iname "node_modules" -o -iname ".env"
  (sin resultados: el clon no tiene nada ignorado)
  ```

  ```
  $ cd <scratch>/proptech-limpio-v3/backend && date -u +"%Y-%m-%dT%H:%M:%SZ" && uv sync --locked
  2026-10-14T18:35:51Z
  (instala paquetes desde cero, sin .venv previo)

  $ uv run ruff check .
  2026-10-14T18:35:58Z
  All checks passed!

  $ uv run ruff format --check .
  2026-10-14T18:35:58Z
  108 files already formatted

  $ uv run mypy
  2026-10-14T18:35:58Z
  Success: no issues found in 103 source files

  $ cd .. && bash infra/ci/test-backend.sh
  2026-10-14T18:36:12Z
  =========== 516 passed, 1 xfailed, 16 warnings in 111.20s (0:01:51) ============

  $ bash infra/ci/canario.sh backend
  2026-10-14T18:38:09Z
  FAILED tests/unitarios/test_canario_roto.py::test_canario_roto_a_proposito - ...
  1 failed, 516 passed, 1 xfailed, 16 warnings in 109.37s
  CANARIO OK (backend): el script de test terminó distinto de 0 con el test roto

  $ cd ../web && date -u +"%Y-%m-%dT%H:%M:%SZ" && corepack pnpm@12.10.1 install --frozen-lockfile
  2026-10-14T18:40:11Z
  Done in 307ms using pnpm v12.10.1 (instala desde cero, sin node_modules previo)

  $ corepack pnpm@12.10.1 biome ci
  2026-10-14T18:40:17Z
  Checked 10 files in 13ms. No fixes applied.

  $ corepack pnpm@12.10.1 tsc --noEmit
  2026-10-14T18:40:17Z
  (sin salida: sin errores)

  $ cd .. && bash infra/ci/test-web.sh
  2026-10-14T18:40:24Z
  Test Files  3 passed (3)
       Tests  16 passed (16)

  $ bash infra/ci/canario.sh web
  2026-10-14T18:40:24Z
  FAIL  src/canario-roto.test.ts > canario roto a propósito
  Test Files  1 failed | 3 passed (4)
       Tests  1 failed | 16 passed (17)
  CANARIO OK (web): el script de test terminó distinto de 0 con el test roto

  $ COMPOSE_PROJECT_NAME=proptech bash infra/ci/humo.sh
  2026-10-14T18:40:34Z
  (sin el error de buildkit de la corrida anterior: la caché estaba limpia.
  db, redis, migraciones, api, worker, web, caddy: todos Healthy en el primer
  intento)
  --- (1) GET /api/salud por Caddy ---
  {"estado":"ok","base":"ok","cola":"ok"}
  --- (2) sólo caddy publica puertos ---
  servicios con puertos publicados: caddy
  --- (3) el servicio db no tiene puerto publicado hacia el host ---
  ok: db no tiene ports publicados (docker compose port db 5432 = ':0')
  --- (4) api y web corren como no root ---
  uid api=999 uid web=100
  --- (5) las imágenes construidas no contienen .env ---
  --- (6) GET / responde 200 con HTML ---
  --- (7) base pausada (congelada, no caída) -> 503 degradado, dentro de un tiempo acotado ---
  {"estado":"degradado","base":"sin_conexion","cola":"ok"}código: 503, duración: 2015ms
  --- (8) base caída -> 503 degradado ---
  {"estado":"degradado","base":"sin_conexion","cola":"ok"}código: 503
  HUMO OK
  --- limpieza: docker compose down -v --- (stack bajado completo, volúmenes y redes removidos)

  $ docker ps -a --filter "name=proptech" --format "{{.Names}}"
  (sin salida: cero contenedores proptech después de la limpieza)

  $ date -u +"%Y-%m-%dT%H:%M:%SZ" && docker run --rm -v "$PWD":/repo -w /repo zricethezav/gitleaks:v8.30.1 git --config /repo/.gitleaks.toml -v .
  2026-10-14T18:41:12Z
  43 commits scanned. no leaks found

  $ docker run --rm -v "$PWD":/repo -w /repo zricethezav/gitleaks:v8.30.1 dir --config /repo/.gitleaks.toml -v .
  2026-10-14T18:41:18Z
  no leaks found
  ```

  **Nota sobre el modo `git` de gitleaks**: sólo escanea commits, y acá el
  HEAD del clon es el mismo del repo (nada de este cambio está commiteado),
  así que ese modo nunca mira el código nuevo. El `dir` (sobre el working
  tree copiado, que es lo que corresponde a "el código terminado") es el que
  de hecho lo cubre.

  **Comparación contra la línea de base de 1.2** (backend 259 passed, web 1
  passed, HEAD `539d005`): backend pasó de 259 a **516 passed + 1 xfailed**
  (+257 sobre la base de 1.2: los +188 de las secciones 2 a 6 de la primera
  corrida de 7.1, más los tests de ataque de las vueltas 2 y 3 del rompedor
  que viven en el repo (`test_ataque_*`, `test_zz_rompedor_*`) y el nuevo
  `test_zz_rompedor_v3_agotada_con_efecto.py`, marcado `xfail(strict=True)`
  a propósito por F2c); web pasó de 1 a **16** (sin cambios en esta vuelta,
  no se tocó `web/`). Ningún test salteado ni deseleccionado. **No** son "los
  mismos números que la corrida anterior sobre el working tree sin clonar":
  acá cambiaron a propósito respecto de la corrida de 7.1 de la vuelta
  anterior (447 → 516+1 xfailed) porque el código cambió; sí coinciden
  exactamente con la corrida hecha sobre el working tree sin clonar en esta
  misma vuelta (`516 passed, 1 xfailed` en ambos lados): la del clon corrió
  a las 18:35Z-18:38Z; la única corrida sobre el árbol sin clonar de esta
  vuelta es posterior (18:44:48Z, informe de cierre del constructor), hecha
  después de borrar el clon, no antes de crearlo como decía una versión
  anterior de este párrafo.

  Clon temporal borrado al terminar (`rm -rf` sobre el directorio
  `<scratch>/proptech-limpio-v3`, fuera de este repositorio). Sin commit ni
  push en ningún momento.
