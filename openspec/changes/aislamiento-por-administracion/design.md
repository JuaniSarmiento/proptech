## Context

Ver `proposal.md` (Why) y el explore `openspec/exploraciones/2026-10-15-acceso-y-aislamiento.md`.
Estado del código al 15/10/2026 (commit `b77babf`):

- **Un solo rol de base** (`POSTGRES_USER` de `infra/.env`), que la imagen oficial crea como
  superusuario y que comparten `migraciones`, `api`, `worker` y `respaldos` en `infra/compose.yaml`.
  Hoy nada hace de candado: todo corre con permiso para saltearse cualquier política.
- **`configuracion.py`**: `_ConfiguracionBaseDeDatosBase` y `_ConfiguracionBase` leen el mismo par
  `POSTGRES_USER`/`POSTGRES_PASSWORD`; `url_sqlalchemy()` arma un `URL` y lo devuelve renderizado como
  `str` con la contraseña (M12 a medias, D-091).
- **`base_de_datos.py::registrar_application_name`** ya hace, para `application_name`, lo que el plan
  de D-087 pide para el tenant: un `after_begin` sobre la `sessionmaker` que corre
  `set_config(..., true)` leyendo una `ContextVar`. Es el molde de D4, con dos diferencias: un tenant
  ausente nunca se inventa, y el tenant tiene que estar fijado antes de la primera consulta.
- **Worker**: `tareas.py` valida sus argumentos con Pydantic estricto antes de encolar (D2 del 1c) y
  `con_seguimiento_de_tarea` fija el `request_id` por tarea; la base se toca con `asyncio.to_thread`,
  que copia el contexto (L-015).
- **Migraciones**: `0001_inicial` (vacía) y `0002_trabajos_hechos`, las dos creadas por el rol de
  arranque.
- **Redes**: `interna` (sin salida, con la base, Redis, la API, el worker, la web y Caddy con IP fija
  `172.28.0.254`), `borde` (Caddy) y `salida_worker`. La web está hoy en la misma red que la base.
- **CI** (`.github/workflows/ci.yml`): sólo `on: push`, sin `timeout-minutes`, gitleaks
  `zricethezav/gitleaks:v8.30.1` por tag.

## Deuda que recibe este cambio, y el reparto con el 2b

Criterio (L-012): va al 2a lo que necesita el candado o el endurecimiento de infraestructura; va al 2b
lo que necesita el login. Lo que no necesita ninguno de los dos se dice.

| Ítem (origen) | Va a | Por qué |
|---|---|---|
| Roles de PostgreSQL para RLS, migrador y aplicación (auditorías 13/10) | 2a | Es el candado mismo (D1) |
| Endurecimiento de contenedores (13/10) | 2a | Infra; el rol de la app sin privilegios pierde valor si el contenedor puede escalar (D11) |
| PID 1 no root visto sólo en `redis` (1d) | 2a | Es parte del endurecimiento de contenedores, mismo test (D11) |
| Cabeceras de seguridad en Caddy (13/10) y `Via`, `X-Powered-By`, HEAD (D-051) | 2a | Infra del proxy; se prueban sin pantallas (D10) |
| Volúmenes de Caddy (13/10) | 2a | Infra del proxy, mismo archivo (D10) |
| Separar la red de la web de la de la base (D-051) | 2a | Es parte del aislamiento: la web nunca tiene que alcanzar la base (D11) |
| CI con `pull_request`, límites de tiempo y gitleaks por digest (13/10) | 2a | Endurecimiento del pipeline que corre los tests del candado; con dos desarrolladores (D-093) los PR ya existen (D12) |
| Tabla de variables del README (13/10) | 2a | Las credenciales por rol son las primeras variables que cambian el contrato de `.env` |
| M12 a medias, URL como `str` (1c) | 2a | El 2a reescribe `configuracion.py` y `env.py` para las credenciales por rol (D3) |
| `trabajos_hechos` y el tenant del worker (1c) | 2a | El worker con tenant es parte del candado (D8) |
| F7 resto: "aparece uno solo" y pasos 11 y 13 sin nombre (1d) | 2a | El 2a amplía el humo con roles y backup completo; se arregla el mismo archivo (D13) |
| El humo nunca congela las dos dependencias (1d) | 2a | Mismo archivo, misma tarea de humo (D13) |
| El orden de la 8.1 (1d) | 2a | La tarea de cierre del 2a (11.1) dice el orden y por qué (D14) |
| CSP en Next (13/10) | 2b | Una CSP sin pantallas no prueba nada; la primera pantalla con formulario es la de login |
| Límite de intentos en el login (ficha 2) | 2b | No existe login que limitar |
| Auditoría de login exitoso y fallido (explore §3) | 2b | Usa la tabla y el helper del 2a |
| Dependabot (13/10) | ninguno | No lo necesita ni el candado ni el login. Se propone moverlo al cambio 15, junto a las imágenes por digest que mantendría (E4 en "Aprobación") |

## Cómo aplica cada lección

La tabla del proposal dice qué tarea cubre cada lección. Lo que cambia el diseño:

- **L-004**: los tests de integración entran por la sesión de SQLAlchemy contra PostgreSQL real; el
  catálogo (`pg_class`, `pg_policies`, `pg_roles`) se mira con SQL crudo; el humo entra por el proxy y
  por `psql`. El rompedor ataca por un tercer camino: el pool, los hilos y las migraciones futuras.
- **L-015**: la `ContextVar` del tenant se lee en el `after_begin`, que corre en el hilo donde se abre
  la transacción; todo acceso a la base del worker sigue por `asyncio.to_thread`.
- **L-016**: PID 1 no root se ve en rojo **en cada** servicio, no en uno; el conteo de filas del backup
  se hace con dos administraciones sembradas, así "las dos" puede dar "una".
- **L-017**: los ids de otra administración que usan los tests son UUID válidos y existentes, nunca un
  texto que FastAPI ya rechaza con 422.

## Goals / Non-Goals

**Goals:**

- Que ningún camino de la API ni del worker pueda leer o escribir datos de otra administración aunque
  el código se equivoque, y que la base lo sostenga sola.
- Que 404 y 403 sigan D-037 y D-096 sin filtrar existencia.
- Dejar el helper de auditoría listo para los cambios 7, 8 y 10b.

**Non-Goals:**

- Ningún mecanismo de sesión, contraseña, mail ni token (2b).
- Ninguna política de base por edificio (E2, D6).
- Ningún endpoint para leer la auditoría.

## Decisions

### D1 · Tres roles, y quién usa cada uno

- **Rol de arranque** (`POSTGRES_USER`, superusuario de la imagen): crea los otros dos y hace los
  backups. Lo reciben sólo `migraciones` (para el paso de roles) y `respaldos`.
- **`proptech_migrador`**: `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB`, dueño del esquema
  `public` de la aplicación y de todas las tablas. Corre `alembic upgrade head`.
- **`proptech_app`**: `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB`, sin ser dueño de nada,
  con `SELECT, INSERT, UPDATE, DELETE` sobre las tablas de dominio (`SELECT, INSERT` sobre
  `auditoria`) y `USAGE` sobre las secuencias, otorgados por `ALTER DEFAULT PRIVILEGES FOR ROLE
  proptech_migrador` más el `GRANT` explícito en cada migración, y verificados por el guardián de D5.

Los nombres de los dos roles son fijos (`proptech_migrador`, `proptech_app`); las contraseñas vienen de
`POSTGRES_MIGRADOR_PASSWORD` y `POSTGRES_APP_PASSWORD`. Las variables `POSTGRES_MIGRADOR_USER` y
`POSTGRES_APP_USER` existen sólo para que la configuración no tenga el nombre escrito en dos lugares, y
se validan contra `^proptech_[a-z_]{1,40}$` (L-008).

**Descartado**: dos roles como dice D-087, con el rol de arranque reasignado a uno de ellos. El rol de
arranque es superusuario por la imagen y no se puede degradar sin perder la forma de crear los otros;
dejarlo existir sólo para eso y para los respaldos es más simple que quitarle el superusuario.

### D2 · El arranque de roles corre en `migraciones`, no en `docker-entrypoint-initdb.d` (E1)

Un script de `initdb.d` corre sólo con el volumen vacío: no sirve para las máquinas que ya tienen la
base del 1d. Por eso el servicio `migraciones` corre primero un comando Python
(`python -m proptech_core.compartido.roles`) con el rol de arranque, que en una sola transacción:

1. crea cada rol si no existe (`DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_roles ...)`, porque
   `CREATE ROLE IF NOT EXISTS` no existe);
2. fija los atributos de D1 con `ALTER ROLE` cada vez (así una corrida arregla un rol que alguien
   tocó a mano) y la contraseña con `psycopg.sql.Literal`, nunca interpolada a mano ni logueada (L-007);
3. transfiere al migrador las tablas y secuencias de `public` que sean del rol de arranque
   (`alembic_version`, `trabajos_hechos`), una por una por nombre, nunca `REASSIGN OWNED` (que se
   llevaría objetos que no son del proyecto, L-006);
4. fija los `DEFAULT PRIVILEGES`.

Después corre `alembic upgrade head` con las credenciales del migrador.

**E1, sin `BYPASSRLS` para el migrador**: las migraciones del 2a no siembran datos. Una migración
futura que necesite escribir filas de una administración fija su propio
`set_config('app.administracion_id', ..., true)` antes de insertar, igual que la app. Darle
`BYPASSRLS` sería más simple, pero dejaría un rol con contraseña en el `.env` que saltea todas las
políticas; sin él, el único que las saltea es el superusuario de arranque, que la API y el worker
nunca reciben.

### D3 · Configuración por rol y la URL como objeto (M12)

- `_ConfiguracionBaseDeDatosBase` se parte en un lector común (host, puerto, base) y un par de
  credenciales por clase: `ConfiguracionDeArranque` (rol de arranque), `ConfiguracionDelMigrador` y
  `Configuracion` (API y worker, con las credenciales de la app). Cada una lee sólo sus variables, así
  la API no levanta aunque alguien le pase la contraseña de arranque por error y la use (y un test lo
  verifica leyendo el entorno del contenedor en Compose).
- `url_sqlalchemy()` pasa a devolver `sqlalchemy.engine.URL`; `create_engine` lo acepta tal cual y el
  único lugar que lo renderiza a texto es ninguno: `env.py` arma su engine con
  `create_engine(url)` en vez de `config.set_main_option("sqlalchemy.url", ...)`. Un test verifica que
  `repr()` y `str()` del objeto ocultan la contraseña.

### D4 · El tenant: `ContextVar` + `after_begin` + `SET LOCAL`

- `administracion_id_actual: ContextVar[UUID | None]` en `proptech_core/compartido/tenant.py`.
- Un `after_begin` registrado en la `sessionmaker` de la API y del worker (gemelos, L-009) que, si la
  variable tiene valor, corre `SELECT set_config('app.administracion_id', :v, true)` con el UUID como
  parámetro ligado. Si no tiene valor, **no fija nada**: la política devuelve cero filas (D5). Nunca
  inventa un valor, a diferencia del `request_id`.
- `after_begin` corre en cada transacción, así un `commit` a mitad de pedido abre la siguiente con el
  mismo tenant (escenario "Una segunda transacción en el mismo pedido").
- Se descarta `SET` sin `LOCAL` y `RESET` al devolver la conexión: un `SET` de sesión que no se
  resetea por un error contagia al pedido siguiente, y `set_config(..., true)` muere con la
  transacción sin depender de que alguien lo limpie.

### D5 · La política, y el guardián del catálogo

Cada tabla de una administración:

```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <t> FORCE ROW LEVEL SECURITY;
CREATE POLICY <t>_por_administracion ON <t>
  USING (administracion_id = nullif(current_setting('app.administracion_id', true), '')::uuid)
  WITH CHECK (administracion_id = nullif(current_setting('app.administracion_id', true), '')::uuid);
```

El `true` de `current_setting` (`missing_ok`) evita el error cuando la variable nunca se fijó; el
`nullif` evita el error de castear `''` a `uuid` (una variable fijada una vez en la sesión queda como
cadena vacía después de la transacción). Con `NULL`, la igualdad no es verdadera y no pasa ninguna
fila. Para no repetir el texto en cada migración, un helper de migraciones
`aislar_por_administracion(nombre_de_tabla)` emite las cuatro sentencias y el `GRANT` a la app.

**El guardián** (`tests/integracion/test_catalogo_rls.py`) recorre el catálogo después de
`upgrade head` y falla, nombrando la tabla, si alguna tabla de `public` con columna
`administracion_id` no tiene `relrowsecurity` y `relforcerowsecurity`, no tiene política, tiene una
política cuyo texto en `pg_policies` usa `current_setting` sin el segundo argumento, o no tiene los
permisos de D1 para `proptech_app`. Las tablas sin `administracion_id` tienen que estar en una lista
explícita de tablas técnicas (hoy `alembic_version` y `trabajos_hechos`, más `administracion`, que se
aísla por su propio `id`). Una tabla nueva sin estar en ninguna de las dos categorías hace fallar el
test: es la red contra el `GRANT` olvidado.

### D6 · Tablas mínimas y el alcance por edificio en la aplicación (E2)

Migración `0003_acceso_minimo`:

- `administracion (id uuid PK, nombre text)`, con política sobre `id` en vez de `administracion_id`.
- `complejo (id, administracion_id, nombre)`, `UNIQUE (administracion_id, id)`.
- `unidad (id, administracion_id, complejo_id, nombre)`, FK compuesta
  `(administracion_id, complejo_id) → complejo (administracion_id, id)`.
- `persona (id, administracion_id, nombre, email text null)`, con `CHECK (email = lower(email))` y
  `UNIQUE (administracion_id, email)` (D-096: único por administración, no global; sin la extensión
  `citext`, para no sumar una dependencia de la base).
- `asignacion_rol (id, administracion_id, persona_id, rol, complejo_id null, unidad_id null, nivel null)`,
  con `CHECK` por rol: titular sin complejo ni unidad; colaborador con complejo y nivel `ver` o
  `editar`; consejo con complejo; vecino con unidad. FKs compuestas a persona, complejo y unidad.

Las FK compuestas son el candado de "Referencia cruzada rechazada": aunque la política deja escribir
la fila propia, la FK no deja colgarla de una fila ajena.

**E2, alcance por edificio en la aplicación**: la base asegura la administración; el edificio lo
filtra el dominio `acceso` leyendo `asignacion_rol` (ya filtrada por RLS). Una segunda política por
persona exigiría fijar también la identidad de la persona en la transacción y escribir, por tabla, el
camino hasta sus asignaciones: más caro, y cada tabla nueva de los cambios 3 a 10 tendría que
repetirlo. El riesgo es el que dice el explore (§2.5): un error de código en el filtro por edificio
muestra un edificio no asignado **de la misma administración**, nunca de otra. Se cubre con un test por
rol y por endpoint (5.2) y queda en la lista del rompedor.

### D7 · Identidad, sesión y autorización

- `proptech_core/acceso/dominio/`: `Identidad(administracion_id, persona_id)` (frozen), los enums
  `Rol`, `Nivel` y `Accion`, la matriz de D-096 como un dict literal `{Accion: {(Rol, Nivel|None)}}`
  y dos funciones puras: `puede(asignaciones, accion, complejo_id) -> bool` y
  `alcanza(asignaciones, complejo_id | unidad) -> bool`. Las asignaciones salen de la base, nunca del
  pedido.
- `proptech_api/acceso.py`: `identidad_actual()` levanta `HTTPException(401)` siempre (hasta el 2b);
  `sesion_con_tenant(identidad = Depends(identidad_actual))` fija la `ContextVar`, abre la sesión, y la
  resetea con el token en el `finally`. Al depender explícitamente de la identidad, FastAPI no puede
  abrir la sesión antes. Los tests usan `app.dependency_overrides[identidad_actual]`.
- Orden de chequeo en cada endpoint: cargar el recurso con la sesión filtrada → si no está o no
  `alcanza`, 404 → si no `puede`, 403 `{"detalle": "sin_permiso", "permiso_faltante": "<accion>"}`.
  El 404 sale de una sola función que arma la respuesta, así "no existe", "de otra administración" y
  "fuera de alcance" son el mismo objeto.
- Endpoints: `GET /api/complejos/{complejo_id}`, `GET /api/unidades/{unidad_id}` y
  `POST /api/complejos/{complejo_id}/asignaciones` (cuerpo: `persona_id`, `rol`, `nivel`).

### D8 · El worker: el tenant como argumento validado (E3)

- Decorador `con_administracion_de_tarea` (molde: `con_seguimiento_de_tarea`): valida
  `administracion_id` con un modelo Pydantic estricto (`UUID`, `strict=True`) antes de tocar nada;
  si falla, levanta una excepción de tipo permanente que el worker no reintenta (el mismo camino que
  ya tienen los argumentos inválidos de la tarea de prueba) y loguea un evento fijo
  `tarea_sin_administracion` sin el valor (L-007). Si valida, fija la `ContextVar` y la resetea al
  terminar con el token, también si la tarea falla.
- Una tarea de prueba nueva (`tarea_de_prueba_con_administracion`, cuenta complejos) en
  `proptech_worker/prueba.py` para los tests y el humo.
- **E3**: `trabajos_hechos` queda **sin** `administracion_id` y fuera de RLS: guarda la clave de
  idempotencia, el nombre de la tarea, el `request_id` y la hora, ningún dato de una administración.
  Las claves de idempotencia de las tareas con tenant incluyen el `administracion_id`, para que dos
  administraciones no se pisen la misma clave. Va a la lista de tablas técnicas del guardián (D5).

### D9 · Auditoría

- Migración `0004_auditoria`: `auditoria (id bigint identity, administracion_id, persona_id, accion
  text, entidad text, entidad_id uuid, detalle jsonb, request_id uuid, creado_en timestamptz default
  now())`, aislada con D5 pero con `GRANT SELECT, INSERT` a la app (ni `UPDATE` ni `DELETE`), un
  `CHECK (accion IN (...))` con el vocabulario y un trigger `BEFORE UPDATE OR DELETE` por fila más
  uno `BEFORE TRUNCATE` por sentencia que levantan una excepción para cualquier rol, dueño incluido.
  El superusuario de arranque podría desactivar el trigger: es el mismo rol que ya puede todo, y la app
  nunca lo tiene.
- `proptech_core/compartido/auditoria.py`: `registrar(sesion, identidad, accion, entidad, entidad_id,
  detalle)` exige `sesion.in_transaction()` (si no, error de programación), valida el detalle contra
  el modelo Pydantic de esa acción (`extra="forbid"`, sólo tipos simples) y hace el `INSERT` en la
  misma sesión. El caso de uso abre `with sesion.begin():`, hace el efecto y llama a `registrar`;
  cualquier excepción revierte las dos.
- Un decorador `@accion_sensible(Accion.X)` marca el caso de uso; un registro en memoria lista los
  marcados y un test los recorre y exige una fila por cada uno.
- Vocabulario inicial: `asignar_edificio`. El 2b suma `ingreso_exitoso` e `ingreso_fallido`.

### D10 · Proxy y web

- `Caddyfile`: `header` con `X-Content-Type-Options nosniff`, `Referrer-Policy no-referrer`,
  `X-Frame-Options DENY`, `Permissions-Policy "camera=(), microphone=(), geolocation=()"`, y
  `-Server`, `-Via`, `-X-Powered-By`; `reverse_proxy` con `header_down -Via` y
  `header_down -X-Powered-By` para lo que viene de atrás. HSTS queda para el despliegue con dominio
  (cambio 15): en el CI el sitio es HTTP.
- `web/next.config.*`: `poweredByHeader: false`.
- Volúmenes `datos_caddy:/data` y `config_caddy:/config`.

### D11 · Redes y contenedores

- `interna` se parte en `datos` (interna, sin salida: `db`, `redis`, `migraciones`, `api`, `worker`,
  `respaldos`) y `aplicacion` (interna, sin salida: `api`, `web`, `caddy`), con la IP fija de Caddy
  en `aplicacion` y `FORWARDED_ALLOW_IPS` apuntando a esa. La web llega a la API por `aplicacion` y no
  ve `db` ni `redis`.
- Todos los servicios: `security_opt: [no-new-privileges:true]`. `cap_drop: [ALL]` en `api`, `worker`,
  `web`, `migraciones` y `respaldos`; `db` y `redis` con `cap_drop: [ALL]` y sólo las capacidades que
  su entrypoint necesita para bajar de usuario (`CHOWN`, `SETUID`, `SETGID`, `DAC_OVERRIDE`,
  `FOWNER`); `caddy` con `NET_BIND_SERVICE`. El constructor confirma la lista mínima viendo fallar el
  arranque sin cada una (se anota en el informe).
- PID 1 no root: el test existente de `/proc/1/status` se parametriza por servicio, y el rojo se ve en
  cada uno con una copia de Compose mutada (L-013, L-016).

### D12 · CI

`on: [push, pull_request]`, `timeout-minutes` en cada trabajo (10 los rápidos, 30 el humo) y gitleaks
como `zricethezav/gitleaks:v8.30.1@sha256:<digest>`, con el digest tomado de la imagen que hoy corre
el CI (el constructor lo anota con el comando que lo obtuvo).

### D13 · Humo

- Pasos nuevos: `current_user`, `rolsuper` y `rolbypassrls` de la conexión de la API y del worker;
  cabeceras con GET y HEAD por el proxy; dos administraciones sembradas con `psql` como rol de
  arranque, backup, restauración en `proptech_restauracion` y conteo por administración (2 y 2).
- F7 resto: una función `paso N "descripción"` que imprime el número y la descripción al fallar, y un
  helper `exactamente_uno` para cada "aparece uno solo". Cada paso con su `if ! ...; then` (L-014).
- Doble congelada: `docker compose -p proptech pause db redis`, los dos pedidos y un `trap` que
  despausa siempre.

### D14 · La corrida de cierre, en orden

La 11.1 corre `test-backend.sh`, `test-web.sh` y `humo.sh` **en este orden y de a uno**: los tests de
integración y el humo usan contenedores de PostgreSQL con nombres del proyecto `proptech`, y en
paralelo se pisan. Si el orden no importara para un paso, la tarea lo diría; acá importa.

## Risks / Trade-offs

- [Alcance por edificio sólo en la aplicación] → tests por rol y por endpoint, y el rompedor lo ataca;
  la base sigue asegurando la administración (E2).
- [El rol de arranque sigue siendo superusuario y está en el `.env`] → sólo lo reciben `migraciones`
  y `respaldos`; un test de Compose verifica que `api` y `worker` no lo tienen.
- [Una migración futura escribe una política a mano sin `missing_ok`] → el guardián del catálogo lee
  `pg_policies` y falla.
- [Cambiar de red rompe `FORWARDED_ALLOW_IPS`] → el humo ya verifica el `request_id` de punta a punta
  y la IP de origen; si la IP fija no coincide, falla ahí.
- [Las capacidades mínimas de `db` y `redis` dependen de la imagen] → se prueban arrancando el stack;
  si una actualización de imagen necesita otra, el humo falla al levantar.
- [El paso de roles necesita la contraseña de arranque en `migraciones`] → es un servicio de una sola
  corrida (`restart: "no"`), y su log no repite ningún valor (L-007).
- [E3: `trabajos_hechos` global] → no guarda datos de una administración; si un cambio futuro le
  agrega uno, el guardián lo obliga a aislarla.

## Migration Plan

1. `git pull`, completar `infra/.env` con `POSTGRES_MIGRADOR_PASSWORD` y `POSTGRES_APP_PASSWORD`
   (el README lo dice).
2. `docker compose up --build`: `migraciones` crea los roles, transfiere `alembic_version` y
   `trabajos_hechos` al migrador y corre 0003 y 0004; la API y el worker arrancan como `proptech_app`.
3. Rollback: `alembic downgrade 0002` como migrador (0004 y 0003 tienen `downgrade` que deja el
   esquema como estaba) y volver la imagen anterior. Los roles quedan creados: no molestan, y el paso
   de roles es idempotente si se vuelve a subir. El backup del 1d sigue siendo completo en las dos
   direcciones porque lo hace el rol de arranque.

## Open Questions

- Quién lee la auditoría (sólo el titular, o también el consejo): no cambia el mecanismo; se decide
  cuando exista una pantalla que la muestre.
