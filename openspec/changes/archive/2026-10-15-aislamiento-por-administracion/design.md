## Context

Ver `proposal.md` (Why) y el explore `openspec/exploraciones/2026-10-15-acceso-y-aislamiento.md`.
Estado del código al 15/10/2026 (commit `b77babf`):

- **Un solo rol de base** (`POSTGRES_USER` de `infra/.env`), que la imagen oficial crea como
  superusuario y que comparten `migraciones`, `api`, `worker` y `respaldos` en `infra/compose.yaml`.
  Hoy nada hace de candado: todo corre con permiso para saltearse cualquier política.
- **`configuracion.py`**: `_ConfiguracionBaseDeDatosBase` y `_ConfiguracionBase` leen el mismo par
  `POSTGRES_USER`/`POSTGRES_PASSWORD`; `url_sqlalchemy()` arma un `URL` y lo devuelve renderizado como
  `str` con la contraseña (M12 a medias, D-091).
- **`base_de_datos.py::registrar_application_name`** ya registra un `after_begin` sobre la
  `sessionmaker` que corre `set_config(..., true)`. Es el molde de D4.
- **Worker**: `tareas.py` valida sus argumentos con Pydantic estricto antes de encolar (D2 del 1c); la
  base se toca con `asyncio.to_thread` (L-015).
- **Migraciones**: `0001_inicial` (vacía) y `0002_trabajos_hechos`, las dos creadas por el rol de
  arranque.
- **Redes**: `interna` (sin salida: base, Redis, API, worker, web y Caddy con IP fija `172.28.0.254`),
  `borde` (Caddy) y `salida_worker`. La web está hoy en la misma red que la base.
- **Restauración** (`infra/respaldos/restaurar.sh`, 1d): `pg_restore --no-owner -U <rol de arranque>`
  en una base aparte.

**Lo que probó el arquitecto** el 15/10/2026 en un contenedor `postgres:18.6-trixie` descartable, y
que este design toma como hecho (EVIDENCIA de su revisión, no de este propose):

1. El migrador no puede crear tablas en `public` sin `GRANT CREATE` o sin ser dueño del esquema.
2. `ALTER DEFAULT PRIVILEGES` no cubre tablas que ya existían.
3. El dueño de una tabla, aun sin `BYPASSRLS`, puede `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` y
   leer todo, y puede `DISABLE TRIGGER`.
4. `pg_dump` como `proptech_app` falla ruidoso (`exit=1`, "query would be affected by row-level
   security policy"); con `--enable-row-security` sale vacío y en silencio; un rol sin superusuario
   con `BYPASSRLS` y `pg_read_all_data` vuelca todo.
5. Con FastAPI 0.143, una dependencia sincrónica que hace set/reset de una `ContextVar` falla con
   `ValueError` o el endpoint no ve el valor; con `async def` funciona.

## Deuda que recibe este cambio, y el reparto con el 2b y el 2c

Criterio (L-012, revisado por el arquitecto): va al 2a sólo lo que el candado necesita; al 2b lo que
necesita el login; al 2c (`endurecimiento-de-infraestructura`, MEDIUM) el endurecimiento que no hace al
candado.

| Ítem (origen) | Va a | Por qué |
|---|---|---|
| Roles de PostgreSQL para RLS, migrador y aplicación (auditorías 13/10) | 2a | Es el candado mismo (D1) |
| Separar la red de la web de la de la base (D-051) | 2a | Es aislamiento de datos: la web nunca tiene que alcanzar la base (D10) |
| M12 a medias, URL como `str` (1c) | 2a | El 2a reescribe `configuracion.py` y `env.py` para las credenciales por rol (D3) |
| `trabajos_hechos` y el tenant del worker (1c) | 2a | El worker con tenant es parte del candado (D8) |
| El orden de la 8.1 (1d) | 2a y 2c | Cada uno dice el orden de su corrida de cierre y por qué (D13) |
| Cabeceras en Caddy, `Via`, `X-Powered-By`, HEAD, volúmenes de Caddy | 2c | Infra del proxy; no cambia quién ve qué dato |
| CI con `pull_request`, límites de tiempo y gitleaks por digest | 2c | Pipeline; no cambia quién ve qué dato |
| Endurecimiento de contenedores y PID 1 no root servicio por servicio (13/10, 1d) | 2c | Reduce lo que puede hacer un proceso comprometido; el candado de datos no depende de eso |
| F7 resto y la doble congelada del humo (1d) | 2c | Calidad del humo y de la salud; no tocan el candado |
| Tabla de variables del README (13/10) | 2c | Documentación; el 2a sólo suma sus variables nuevas en el texto existente |
| CSP en Next, límite de intentos, auditoría de ingresos | 2b | Necesitan el login |
| Dependabot (13/10) | 15 (E4) | No lo necesita ni el candado ni el login; va con las imágenes por digest |

## Cómo aplica cada lección

La tabla del proposal dice qué tarea cubre cada lección. Lo que cambia el diseño:

- **L-004**: los tests de integración entran por la sesión de SQLAlchemy contra PostgreSQL real; el
  catálogo (`pg_class`, `pg_policies`, `pg_roles`, `pg_constraint`) se mira con SQL crudo; el humo entra
  por el proxy y por `psql`. El rompedor ataca por un tercer camino: el pool, los hilos, las migraciones
  futuras.
- **L-015**: el tenant viaja como dato en `session.info`, no como `ContextVar` ambiente (D4): no
  depende de qué hilo abre la transacción.
- **L-016**: todo test de aislamiento conecta como `proptech_app`; uno que conecta como superusuario
  pasa siempre. El volcado con el rol equivocado se ve fallar, no se supone.
- **L-017**: los ids de otra administración que usan los tests son UUID válidos y existentes, nunca un
  texto que FastAPI ya rechaza con 422.

## Fronteras

| Frontera | Dirección | Con qué rol o por dónde | Qué no puede cruzar |
|---|---|---|---|
| API → base | API depende de la base | `proptech_app`, tenant por transacción | nada sin tenant; nunca el rol de arranque, migrador ni respaldo |
| worker → base | worker depende de la base | `proptech_app`, tenant por tarea | ídem |
| migraciones → base | migraciones dependen de la base | rol de arranque (paso de roles) y `proptech_migrador` (Alembic) | el migrador no toca la auditoría |
| respaldos → base (volcado) | respaldos dependen de la base | `proptech_respaldo` | nunca `--enable-row-security`; nunca el rol de arranque |
| restauración → base | `restaurar.sh` depende de la base | rol de arranque, `--no-owner`, sólo bases `proptech_*` distintas de la en uso | los roles no viajan en el volcado (ver "Frontera de la restauración") |
| Caddy → web y API | Caddy depende de las dos | red `aplicacion` | Caddy y la web no alcanzan `db` ni `redis` |
| `complejos` → `acceso` | `complejos` (y 7, 8, 10b) dependen de `acceso.aplicacion`; `acceso` **no** importa `complejos` | por la capa `aplicacion` (D-021) | `acceso` trabaja sólo con ids de complejo y unidad; la API compone los dos |
| `acceso` → `compartido` | `acceso` depende de `compartido`; `compartido` **no** importa `acceso` | import directo de código común | la auditoría vive en `acceso`, no en `compartido` (D9) |

La dirección `complejos` → `acceso` se elige porque `complejos` (cambio 3) va a necesitar auditar y
autorizar, y la auditoría vive en `acceso`: si `acceso` además leyera `complejos` habría un ciclo. Para
eso, `asignacion_rol` guarda el `complejo_id` también en las filas de vecino (además de la unidad), y la
API, que compone los dos módulos, carga la unidad con `complejos.aplicacion` y le pasa a `acceso` los
ids. Un test de imports lo fija (5.1).

## Goals / Non-Goals

**Goals:**

- Que ningún camino de la API ni del worker pueda leer o escribir datos de otra administración aunque
  el código se equivoque, y que la base lo sostenga sola.
- Que 404 y 403 sigan D-037 y D-096 sin filtrar existencia.
- Dejar la auditoría lista para los cambios 7, 8 y 10b.

**Non-Goals:**

- Ningún mecanismo de sesión, contraseña, mail ni token (2b).
- Ninguna política de base por edificio (E2, D6).
- Ningún endpoint para leer la auditoría.
- El endurecimiento que no hace al candado (2c).

## Decisions

### D1 · Cuatro roles, y quién usa cada uno (E5)

- **Rol de arranque** (`POSTGRES_USER`, superusuario de la imagen): corre el paso de roles (D2), es
  dueño de `auditoria` y lo usa `restaurar.sh` desde el host. Lo recibe sólo `migraciones`, que es de
  una sola corrida (`restart: "no"`). Ningún servicio permanente lo tiene.
- **`proptech_migrador`**: `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB`, con `CREATE` sobre
  `public`, dueño de todas las tablas de dominio. Corre `alembic upgrade head`. **Es de confianza
  equivalente al superusuario sobre sus tablas**: como dueño puede `ALTER TABLE ... NO FORCE ROW LEVEL
  SECURITY` y leer todo (lo probó el arquitecto). Por eso su contraseña la tiene sólo `migraciones`.
- **`proptech_app`**: `LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB`, sin ser dueño de nada,
  con `SELECT, INSERT, UPDATE, DELETE` sobre las tablas de dominio y `trabajos_hechos`, `SELECT,
  INSERT` sobre `auditoria`, `SELECT` sobre `accion_de_auditoria` y `USAGE` sobre las secuencias.
- **`proptech_respaldo`**: `LOGIN NOSUPERUSER BYPASSRLS NOCREATEROLE NOCREATEDB`, miembro de
  `pg_read_all_data`. Sólo lo usa el servicio `respaldos` para `pg_dump`. Lee todo y no escribe nada.

Las contraseñas vienen de `POSTGRES_MIGRADOR_PASSWORD`, `POSTGRES_APP_PASSWORD` y
`POSTGRES_RESPALDO_PASSWORD`; los nombres, de `POSTGRES_*_USER`, validados contra
`^proptech_[a-z_]{1,40}$` (L-008).

**E5, apartamiento de D-087** (que hablaba de dos roles): se suman el rol de arranque con un trabajo
propio (dueño de la auditoría, B3) y `proptech_respaldo`, para que `respaldos`, que corre siempre,
deje de tener la contraseña del superusuario. **Descartado**: `respaldos` con el rol de arranque (como
en el 1d): un servicio permanente con la llave de todo; y `respaldos` con `proptech_app`: el volcado
falla (o sale vacío con `--enable-row-security`).

### D2 · El paso de roles corre en `migraciones`, antes y después de Alembic (E1)

Un script de `docker-entrypoint-initdb.d` corre sólo con el volumen vacío: no sirve para las máquinas
que ya tienen la base del 1d. Por eso el servicio `migraciones` corre:

```
python -m proptech_core.compartido.roles antes
alembic upgrade head            # como proptech_migrador
python -m proptech_core.compartido.roles despues
```

**`antes`**, con el rol de arranque, en una sola transacción:

1. crea cada rol si no existe (`DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_roles ...)`, porque
   `CREATE ROLE IF NOT EXISTS` no existe);
2. fija los atributos de D1 con `ALTER ROLE` cada vez (así una corrida arregla un rol que alguien
   tocó a mano), la membresía en `pg_read_all_data` y la contraseña con `psycopg.sql.Literal`, nunca
   interpolada a mano ni logueada (L-007);
3. `GRANT CREATE, USAGE ON SCHEMA public TO proptech_migrador` y `GRANT USAGE ON SCHEMA public TO
   proptech_app` (sin el primero el migrador no puede crear tablas: punto 1 del arquitecto);
4. transfiere al migrador cada tabla y secuencia de `public` cuyo dueño sea el rol de arranque, salvo
   `auditoria` (que es del rol de arranque a propósito, D9). Es una lista que
   sale del catálogo de ese esquema, nunca `REASSIGN OWNED` (que se llevaría objetos fuera del
   proyecto, L-006). Sobre un volumen del 1d eso es `alembic_version` y `trabajos_hechos`; sobre una
   base restaurada (dueño: el rol de arranque, por `--no-owner`) son todas las de dominio;
5. otorga **explícitamente** a `proptech_app` los permisos de D1 sobre cada tabla existente, incluida
   `trabajos_hechos` (los `DEFAULT PRIVILEGES` no cubren lo que ya existía: punto 2 del arquitecto);
6. fija `ALTER DEFAULT PRIVILEGES FOR ROLE proptech_migrador` para las tablas futuras.

**`despues`**, con el rol de arranque: transfiere `auditoria` al rol de arranque (la crea la migración
0004 como migrador), vuelve a otorgar los permisos de D1 sobre ella y verifica que el trigger y el
`FORCE` sigan activos. Así el migrador nunca queda como dueño de la
auditoría (B3).

**E1, sin `BYPASSRLS` para el migrador**: el migrador ya puede saltear la política de sus tablas
(quitando el `FORCE`), así que no darle `BYPASSRLS` **no** es una barrera contra él. La razón es otra:
obligar a que una migración que siembre filas de una administración fije su tenant **a propósito**
(`set_config('app.administracion_id', ..., true)`), igual que la app, en vez de escribir sin pensar en
qué administración cae cada fila. Quitarle el `FORCE` a una tabla en una migración es visible en el
diff y lo detecta el guardián (D5).

### D3 · Configuración por rol y la URL como objeto (M12)

- Un lector común (host, puerto, base) y un par de credenciales por clase: `ConfiguracionDeArranque`,
  `ConfiguracionDelMigrador`, `ConfiguracionDeRespaldo` (sólo para validar en tests; `respaldos` es un
  script de Bash que usa las variables de libpq) y `Configuracion` (API y worker, con las de la app).
  Cada una lee sólo sus variables.
- `url_sqlalchemy()` pasa a devolver `sqlalchemy.engine.URL`; `create_engine` lo acepta tal cual y
  `env.py` arma su engine con `create_engine(url)` en vez de `config.set_main_option(...)`. Un test
  verifica que `str()` y `repr()` del objeto ocultan la contraseña.
- **Decisión de implementación (construida en la tarea 2.1)**: el patrón `^proptech_[a-z_]{1,40}$`
  (D1, L-008) se exige al usuario de los **tres roles nuevos** (`ConfiguracionDelMigrador`,
  `ConfiguracionDeRespaldo`, `Configuracion`), no al de `ConfiguracionDeArranque`. Razón: D1 dice "los
  nombres, de `POSTGRES_*_USER`, validados contra ese patrón" — una forma que la variable del rol de
  arranque (`POSTGRES_USER`, sin segmento intermedio) no tiene — y su nombre lo elige quien despliega
  (hoy `proptech` en `infra/.env.example`, sin el guion bajo que pide el patrón): exigírselo hubiera
  invalidado configuraciones existentes sin que ninguna decisión lo pidiera. Verificado en
  `tests/unitarios/test_configuracion.py` (tabla `ROLES`, campo `exige_patron`).

### D4 · El tenant viaja en `session.info` (N4)

- `abrir_sesion(fabrica, administracion_id: UUID | None) -> Session` crea la sesión con
  `info={"administracion_id": administracion_id}`. Es la única forma de abrir una sesión de dominio en
  la API y en el worker (gemelos, L-009).
- Un `after_begin` registrado en la `sessionmaker` lee `session.info.get("administracion_id")`; si es un
  `UUID`, corre `SELECT set_config('app.administracion_id', :v, true)` con el valor como parámetro
  ligado; si falta, **no fija nada** y la política devuelve cero filas (D5). Nunca inventa un valor.
  Si es algo que no es `UUID` (un `str`, por error de programación), levanta antes de tocar la base.
- `after_begin` corre en cada transacción, así un `commit` a mitad de pedido abre la siguiente con el
  mismo tenant: `session.info` dura lo que la sesión.
- `set_config(..., true)` muere con la transacción; se descarta `SET` de sesión con `RESET` al devolver
  la conexión, porque depende de que alguien limpie aunque haya un error.

**Descartado: una `ContextVar` fijada por una dependencia `async def`.** Funciona con FastAPI 0.143 si
la dependencia es `async def` (punto 5 del arquitecto), pero deja la seguridad atada a un detalle del
framework (una dependencia sincrónica rompe en silencio o con `ValueError`) y a que cada hilo copie el
contexto (L-015, el mismo problema en el worker). En `session.info` el tenant es un dato explícito de
la sesión que lo usa: no hay contexto que perder ni que resetear, y una sesión abierta sin pasar por
`abrir_sesion` falla cerrada (cero filas).

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
cadena vacía después de la transacción). Un helper de migraciones `aislar_por_administracion(tabla)`
emite las sentencias y el `GRANT` a la app.

**El guardián** (`tests/integracion/test_catalogo_rls.py`) recorre el catálogo después de
`upgrade head` y falla, nombrando la tabla, si alguna tabla de `public`:

- con `administracion_id` no tiene `relrowsecurity` y `relforcerowsecurity`, no tiene política, tiene
  una política que usa `current_setting` sin el segundo argumento, o no tiene los permisos de D1 para
  `proptech_app`;
- con `complejo_id` lo admite nulo o no tiene la FK compuesta `(administracion_id, complejo_id) →
  complejo (administracion_id, id)`, salvo las excepciones listadas (hoy sólo `asignacion_rol`, donde el
  titular no tiene complejo);
- sin `administracion_id`, no está en la lista explícita de tablas técnicas (`alembic_version`,
  `trabajos_hechos`, `accion_de_auditoria`; `administracion` se aísla por su propio `id`).

Es la red contra el `GRANT` olvidado y contra una tabla de edificio sin `complejo_id`.

### D6 · Tablas mínimas y el alcance por edificio en la aplicación (E2)

Migración `0003_acceso_minimo`:

- `administracion (id uuid PK, nombre text)`, con política sobre `id`.
- `complejo (id, administracion_id, nombre)`, `UNIQUE (administracion_id, id)`.
- `unidad (id, administracion_id, complejo_id NOT NULL, nombre)`, `UNIQUE (administracion_id,
  complejo_id, id)`, FK compuesta `(administracion_id, complejo_id) → complejo`.
- `persona (id, administracion_id, nombre, email text null)`, con `CHECK (email = lower(email))` y
  `UNIQUE (administracion_id, email)` (D-096; sin la extensión `citext`).
- `asignacion_rol (id, administracion_id, persona_id, rol, complejo_id null, unidad_id null, nivel
  null)`, con `CHECK` por rol: titular sin complejo ni unidad; colaborador con complejo y nivel `ver` o
  `editar`; consejo con complejo; vecino con complejo **y** unidad. FKs compuestas a persona, a complejo
  `(administracion_id, complejo_id)` y a unidad `(administracion_id, complejo_id, unidad_id)`, así la
  unidad del vecino tiene que ser de ese complejo.

**Convención nueva** (B2): toda tabla que cuelga de un edificio lleva `complejo_id NOT NULL` con FK
compuesta `(administracion_id, complejo_id)`, y el guardián (D5) lo exige. Deja preparada la reversión
de E2 sin rellenos.

**E2, alcance por edificio en la aplicación**: la base asegura la administración; el edificio lo filtra
el dominio `acceso` leyendo `asignacion_rol` (ya filtrada por RLS).

- **Riesgo explícito**: el filtro de aplicación no sólo separa edificios del personal: también protege
  al **vecino frente a la unidad de otro vecino** y al **consejo frente a otro edificio**. Si falla, un
  vecino ve la deuda y los datos de un tercero de su misma administración. La base no lo frena. Se
  cubre con un test por rol y por endpoint (5.2) y es un blanco explícito del rompedor.
- **Costo de revertir** (pasar a una política de base por persona): hoy, unas 3 o 4 tareas: un segundo
  `set_config` con `app.persona_id` en el mismo `after_begin`; una función `SECURITY DEFINER` que lea
  `asignacion_rol` sin recursión de políticas; las políticas por tabla contra esa función; y ampliar el
  guardián. Después del cambio 10, cada tabla con datos tiene que pasar por una migración con relleno
  y su política: el costo crece con cada cambio.
- **Por qué igual en la aplicación**: la política por persona exige escribir, por tabla, el camino hasta
  las asignaciones, y cada tabla nueva de los cambios 3 a 10 tendría que repetirlo; con la convención de
  `complejo_id` y el costo de revertir acotado, se puede decidir de nuevo antes del cambio 10.

### D7 · Identidad, sesión y autorización

- `proptech_core/acceso/dominio/`: `Identidad(administracion_id, persona_id)` (frozen), los enums
  `Rol`, `Nivel` y `Accion`, la matriz de D-096 como un dict literal `{Accion: {(Rol, Nivel|None)}}` y
  dos funciones puras: `puede(asignaciones, accion, complejo_id) -> bool` y `alcanza(asignaciones,
  complejo_id, unidad_id | None) -> bool`. Las asignaciones salen de la base, nunca del pedido.
- `proptech_api/acceso.py`: `identidad_actual()` levanta `HTTPException(401)` siempre (hasta el 2b);
  `sesion_con_tenant(identidad = Depends(identidad_actual))` llama a `abrir_sesion(fabrica,
  identidad.administracion_id)` y la cierra en el `finally`. Al depender explícitamente de la
  identidad, FastAPI no abre la sesión antes. Como el tenant viaja en la sesión (D4), da igual si la
  dependencia es sincrónica o `async def`. Los tests usan `app.dependency_overrides[identidad_actual]`.
- Orden de chequeo en cada endpoint: cargar el recurso con la sesión filtrada → si no está o no
  `alcanza`, 404 → si no `puede`, 403 `{"detalle": "sin_permiso", "permiso_faltante": "<accion>"}`. El
  404 sale de una sola función, así "no existe", "de otra administración" y "fuera de alcance" son el
  mismo objeto.
- Endpoints: `GET /api/complejos/{complejo_id}`, `GET /api/unidades/{unidad_id}` y
  `POST /api/complejos/{complejo_id}/asignaciones` (cuerpo: `persona_id`, `rol`, `nivel`). Los tres viven
  en `proptech_api`, que compone `complejos.aplicacion` (cargar) y `acceso.aplicacion` (autorizar y
  auditar).

### D8 · El worker: el tenant como argumento validado (E3)

- Decorador `con_administracion_de_tarea`: valida `administracion_id` con un modelo Pydantic estricto
  (`UUID`, `strict=True`) antes de tocar nada; si falla, levanta una excepción permanente que el worker
  no reintenta y loguea un evento fijo `tarea_sin_administracion` sin el valor (L-007). Si valida, le
  pasa el `UUID` a la tarea, que abre sus sesiones con `abrir_sesion(fabrica, administracion_id)`
  (D4), también dentro de `asyncio.to_thread`. No hay estado ambiente que pase a la tarea siguiente.
- `tarea_de_prueba_con_administracion` (cuenta complejos) en `proptech_worker/prueba.py`.
- **E3**: `trabajos_hechos` queda **sin** `administracion_id` y fuera de RLS: guarda la clave de
  idempotencia, el nombre de la tarea, el `request_id` y la hora. **Con D8, las claves de idempotencia
  de las tareas con tenant llevan el `administracion_id` adentro**, así dos administraciones no se pisan
  la misma clave; la clave no se puede leer como dato de negocio. Va a la lista de tablas técnicas del
  guardián.

### D9 · Auditoría en `acceso.aplicacion` (B1, B3)

**Dónde vive y hacia dónde apunta la dependencia**: `proptech_core/acceso/aplicacion/auditoria.py`.
Los módulos que auditan (`complejos` desde el 3; `liquidacion`, `pagos`, `cuenta_corriente` desde 7, 8
y 10b) la usan vía `acceso.aplicacion` (D-021: los módulos se hablan sólo por `aplicacion`). La
dirección es `<módulo> → acceso → compartido`; `compartido` no importa a nadie del dominio.
**Descartado**: la auditoría en `compartido` (como la listaba D-021): necesita `Identidad` y `Accion`,
que son de `acceso`, y eso es un ciclo `compartido` ↔ `acceso`; definir en `compartido` un actor y un
vocabulario genéricos obligaría a `compartido` a conocer las acciones de todos los módulos.

**Un solo vocabulario**: `Accion` (en `acceso.dominio`) es a la vez el nombre del permiso de la matriz
y la acción registrada en la auditoría. La asignación de un edificio se audita como
`invitar_usuarios_y_asignar_edificios`, igual que su permiso. Las acciones que no se autorizan con la
matriz (el 2b suma `ingreso_exitoso` e `ingreso_fallido`) son miembros de `Accion` sin fila en la
matriz, y `puede` las niega: se registran, no se autorizan.

**La tabla** (migración `0004_auditoria`):

- `accion_de_auditoria (nombre text PK)`, técnica y del migrador, con una fila por miembro de `Accion`;
  `auditoria (id bigint identity, administracion_id, persona_id, accion text REFERENCES
  accion_de_auditoria, entidad text, entidad_id uuid, detalle jsonb, request_id uuid, creado_en
  timestamptz default now())`, aislada con D5. **Cada acción nueva exige una migración** que inserte
  su fila en `accion_de_auditoria` (es el control de la base sobre el vocabulario; un test exige que la
  tabla y el enum coincidan). Se descarta el `CHECK (accion IN (...))` sobre `auditoria`: como la tabla
  es del rol de arranque, cada acción nueva obligaría a correr una migración como superusuario. El
  migrador, dueño del vocabulario, podría borrarlo con `CASCADE` y llevarse la FK: perdería el control
  del vocabulario, no la posibilidad de editar o borrar filas de auditoría.
- Un trigger `BEFORE UPDATE OR DELETE` por fila y uno `BEFORE TRUNCATE` por sentencia levantan una
  excepción para cualquier rol.
- **Dueño: el rol de arranque** (paso `despues` de D2). El migrador no es dueño, así que no puede
  `DISABLE TRIGGER` ni `NO FORCE` (punto 3 del arquitecto), y no tiene `UPDATE` ni `DELETE`. La app sólo
  tiene `SELECT, INSERT`. El único que puede desactivar el trigger es el superusuario de arranque, que
  ya puede todo y que ningún servicio permanente tiene. Consecuencia: una migración futura que cambie
  la estructura de `auditoria` corre en el paso de roles, no en Alembic (se anota como riesgo).

**El helper**: `registrar(sesion, identidad, accion, entidad, entidad_id, detalle)` exige
`sesion.in_transaction()`, valida el detalle contra el modelo Pydantic de esa acción
(`extra="forbid"`, sólo tipos simples) y hace el `INSERT` en la misma sesión. El caso de uso abre `with
sesion.begin():`, hace el efecto y llama a `registrar`; cualquier excepción revierte las dos. Un
decorador `@accion_sensible(Accion.X)` marca el caso de uso; un test recorre los marcados y exige una
fila por cada uno.

### D10 · La web fuera de la red de la base

`interna` se parte en `datos` (interna, sin salida: `db`, `redis`, `migraciones`, `api`, `worker`,
`respaldos`) y `aplicacion` (interna, sin salida: `api`, `web`, `caddy`), con la IP fija de Caddy en
`aplicacion` y `FORWARDED_ALLOW_IPS` apuntando a esa. La web llega a la API por `aplicacion` y no ve
`db` ni `redis`. El resto del endurecimiento de contenedores es del 2c.

### D11 · Frontera de la restauración (N2)

`restaurar.sh` (1d) corre `pg_restore --no-owner` con el rol de arranque. Lo que viaja en el volcado:
tablas, datos, `FORCE`, políticas, triggers y `GRANT` (que nombran a los roles por nombre). Lo que
**no** viaja: los roles mismos ni sus contraseñas (son del clúster), y los dueños (`--no-owner`: todo
queda del rol de arranque). En la base de verificación del humo (`proptech_restauracion`, mismo
clúster) los roles existen, así que los `GRANT` se aplican, y el humo verifica que la RLS forzada y las
políticas llegaron. Sobre una base restaurada para **reemplazar** la de producción, el paso `antes` de
D2 vuelve a pasarle las tablas de dominio al migrador y la auditoría queda del rol de arranque como
debe. **Riesgo con dueño, cambio 15**: el procedimiento de recuperación real (restaurar en otro
servidor, donde los roles no existen) necesita levantar primero `migraciones` para crear los roles y
recién después restaurar; se escribe y se prueba con el despliegue.

### D12 · El humo

Pasos nuevos, cada uno con su `if ! ...; then` explícito: `current_user`, `rolsuper` y `rolbypassrls`
de la conexión de `api` y de `worker`; la web sin conexión a `db:5432`; dos administraciones sembradas
con `psql` como rol de arranque, un backup de `respaldos` (ya con `proptech_respaldo`), la restauración
en `proptech_restauracion` y el conteo por administración, más `relforcerowsecurity` y las políticas en
la base restaurada. El rojo se ve con una copia de Compose donde `respaldos` usa `proptech_app`: el
volcado tiene que **fallar** (no queda `.dump` nuevo y el servicio queda no saludable), no dar un
conteo menor. Un test estático exige que ningún script ni `compose.yaml` contenga
`--enable-row-security`. El resto del humo (F7, doble congelada) es del 2c.

### D13 · La corrida de cierre, en orden

La 10.1 corre `test-backend.sh`, `test-web.sh` y `humo.sh` **en este orden y de a uno**: los tests de
integración y el humo usan contenedores de PostgreSQL con nombres del proyecto `proptech`, y en
paralelo se pisan.

## Risks / Trade-offs

- [Alcance por edificio sólo en la aplicación: un error muestra la unidad de otro vecino o el edificio
  de otro consejo] → tests por rol y por endpoint, blanco del rompedor, convención de `complejo_id` y
  costo de revertir acotado (E2, D6).
- [El migrador puede quitar el `FORCE` de sus tablas] → es de confianza equivalente al superusuario;
  sólo `migraciones` tiene su contraseña; el guardián falla si una tabla queda sin `FORCE` (D5).
- [`migraciones` tiene la contraseña del rol de arranque, y un contenedor terminado conserva su entorno
  en `docker inspect`] → es de una sola corrida y no expone puertos; el 2c y el 15 revisan secretos de
  Compose con el despliegue.
- [Una migración futura escribe una política a mano sin `missing_ok`] → el guardián lee `pg_policies`.
- [Cambiar `auditoria` exige el rol de arranque] → se hace en el paso de roles; es raro y deliberado.
- [Cambiar de red rompe `FORWARDED_ALLOW_IPS`] → el humo ya verifica el `request_id` de punta a punta.
- [Restauración en otro servidor sin roles] → dueño, el cambio 15 (D11).
- [E3: `trabajos_hechos` global] → no guarda datos de una administración; si un cambio le agrega uno,
  el guardián lo obliga a aislarla.

## Migration Plan

1. `git pull`, completar `infra/.env` con `POSTGRES_MIGRADOR_*`, `POSTGRES_APP_*` y
   `POSTGRES_RESPALDO_*` (el README lo dice).
2. `docker compose up --build`: `migraciones` corre `roles antes`, `alembic upgrade head` como migrador
   (0003 y 0004) y `roles despues`; la API y el worker arrancan como `proptech_app`; `respaldos`, como
   `proptech_respaldo`.
3. **Rollback**: `alembic downgrade 0002` **borra las tablas**, incluida la auditoría. Hoy no hay datos
   reales y cuesta cero; **desde el cambio 3, con edificios cargados, ya no**: un rollback pasa a ser
   restaurar un backup, no un `downgrade`. Como `auditoria` es del rol de arranque, el `downgrade` de
   0004 corre con ese rol (el migrador no puede borrarla). Los roles quedan creados: no molestan, y el
   paso de roles es idempotente si se vuelve a subir. Volver la imagen anterior exige volver
   `respaldos` al rol de arranque del 1d.

## Open Questions

- Quién lee la auditoría (sólo el titular, o también el consejo): no cambia el mecanismo; se decide
  cuando exista una pantalla que la muestre.
