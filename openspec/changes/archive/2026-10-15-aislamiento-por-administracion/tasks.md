Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el paso
rojo es obligatorio y se anota en el informe con el comando y su salida. Si un test nuevo pasa antes de
escribir el código, no prueba nada: se corrige el test hasta verlo fallar por la razón correcta y se
informa. "Verde" quiere decir lint, formato, tipos y tests del lado tocado (L-005), más `shellcheck`
sobre todo script de Bash tocado. Los tests de aislamiento corren contra PostgreSQL real **conectados
como `proptech_app`**, nunca como el rol de arranque (que es superusuario y saltea toda política: un
test así pasaría sin probar nada, L-016). Los ids "de otra administración" son UUID válidos de filas
que existen (L-017). Ninguna contraseña ni valor rechazado aparece en un error o un log sin un test con
un marcador que pruebe que no se repite (L-007). Para ver fallar una verificación contra código o
configuración mutados a propósito, se muta una copia o se saca antes una copia del original
(`git stash` o un commit local que se descarta) y se compara con un diff real (L-013). Cada tarea
nombra los escenarios de la spec que cubre (`capacidad` › escenario) y las lecciones que aplica.
Ninguna tarea supera medio día.

Precondiciones: el cambio 1d archivado (lo está desde el 14/10) y la sección "Aprobación" de
`proposal.md` completada por uno de los dos socios, Juani o Alberto, con su nombre, la fecha, el
alcance aprobado y la respuesta a E1 a E5 (gobernanza CRITICAL, D-094). Si una elección se rechaza, se
corrige `design.md` antes de empezar. Sin eso, no se empieza. Ningún agente completa esa sección.

## 1. Línea de base

- [x] 1.1 Correr la suite completa antes de tocar nada (`bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`, `bash infra/ci/humo.sh`, en ese orden y de a uno, D13) y anotar la cantidad de tests de cada lado, con la hora y el commit (`git rev-parse HEAD`); si algo falla, frenar e informarlo como falla previa. Escenarios: ninguno (medición de partida). Lecciones: L-003.
  - Hecho 15/10/2026 10:27-10:31, commit `bc4ca9f`: backend 606 passed + 1 xfailed (165s); web 16 passed; humo.sh → HUMO OK.

## 2. Roles y credenciales

- [x] 2.1 Configuración por rol (D3) en `tests/unitarios/test_configuracion.py`: `ConfiguracionDeArranque`, `ConfiguracionDelMigrador`, `ConfiguracionDeRespaldo` y `Configuracion` leen cada una sólo su par de credenciales; para cada par, la variable faltante, vacía, en blanco, con espacios alrededor y (para el usuario) con un nombre fuera de `^proptech_[a-z_]{1,40}$` o con dígitos no ASCII termina en `ConfiguracionInvalida` nombrando la variable y sin el marcador de la contraseña en el mensaje; `Configuracion` no arranca aunque el entorno tenga sólo `POSTGRES_USER`/`POSTGRES_PASSWORD`; `url_sqlalchemy()` devuelve un `sqlalchemy.engine.URL` cuyo `str()` y `repr()` no traen el marcador, y `env.py` arma el engine con ese objeto (M12). Verlos fallar, implementar, verlos pasar. Escenarios: `entorno-de-ejecucion` › Credencial de la app vacía. Lecciones: L-002, L-007, L-008, L-009.
- [x] 2.2 Paso de roles `antes` (D1, D2) en `tests/integracion/test_roles.py` contra PostgreSQL real: sobre una base con `alembic_version` y `trabajos_hechos` creadas por el rol de arranque, `python -m proptech_core.compartido.roles antes` crea los tres roles con los atributos de D1 (`proptech_respaldo` con `BYPASSRLS` y miembro de `pg_read_all_data`, los otros dos sin), da `CREATE` sobre `public` al migrador, le transfiere las dos tablas y otorga a `proptech_app` permisos explícitos sobre `trabajos_hechos`. Ver en rojo, cada uno por separado sobre una copia del módulo (L-013): sin el paso 3, `proptech_migrador` no puede `CREATE TABLE` en `public`; sin el paso 5, `proptech_app` recibe "permission denied" sobre `trabajos_hechos` aunque estén los `DEFAULT PRIVILEGES`. Además: una segunda corrida termina sin error y con los mismos atributos; un rol tocado a mano (`ALTER ROLE proptech_app BYPASSRLS`) vuelve a quedar sin `BYPASSRLS`; una contraseña con comilla simple funciona; ninguna salida trae el marcador; ningún objeto fuera de `public` cambia de dueño. Escenarios: `aislamiento-por-administracion` › Los atributos de cada rol; › Arranque repetido; › Volumen anterior a este cambio. Lecciones: L-006, L-007, L-013.
  - Hecho 15/10/2026: `backend/src/proptech_core/compartido/roles.py` (`antes`/`despues`, CLI). 9 tests en
    `tests/integracion/test_roles.py` (incluye los dos rojos con copia mutada del módulo, L-013, y los
    escenarios de la tarea). Al cerrar, los fixtures de `tests/conftest.py` (`roles_reales`,
    `ajustes_del_worker`, `esquema_migrado`) y 7 archivos de tests de integración del 2.1 se actualizaron
    para usar los roles reales que crea `roles.antes()` en vez del superusuario del contenedor como alias
    (pedido de Juani al cerrar). `despues` queda como no-op documentado hasta la tarea 6.1 (D9): antes de
    la migración de auditoría no tiene nada que hacer; el CLI ya expone el subcomando para 2.3.
- [x] 2.3 Compose y credenciales (D1, D10) en `tests/infra/test_compose.py`: `migraciones` corre `roles antes`, `alembic` con el migrador y `roles despues`, con `restart: "no"`; `api` y `worker` tienen las variables de la app y **no** `POSTGRES_PASSWORD`, `POSTGRES_MIGRADOR_PASSWORD` ni `POSTGRES_RESPALDO_PASSWORD`; `respaldos` usa `POSTGRES_RESPALDO_USER`/`_PASSWORD` y no tiene `POSTGRES_PASSWORD`; ningún servicio con `restart` distinto de `"no"` tiene `POSTGRES_PASSWORD`; ningún archivo de `infra/` contiene `--enable-row-security` (visto en rojo con una copia de `respaldar.sh` que lo agrega, L-013); la web no está en ninguna red con `db` ni `redis`, Caddy tiene su IP fija en `aplicacion` y `FORWARDED_ALLOW_IPS` coincide. Actualizar `infra/.env.example` y sumar las variables nuevas al README en el texto que ya existe (la tabla completa es del 2c). Escenarios: `respaldos-de-la-base` › Credenciales y opciones del servicio; `entorno-de-ejecucion` › La API conecta como la app (la parte de Compose); › La web intenta conectar a la base (la parte estática). Lecciones: L-007, L-013.
  - Hecho 15/10/2026: `interna` partida en `datos` (db, redis, migraciones, api, worker, respaldos) y
    `aplicacion` (api, web, caddy con IP fija); `migraciones` corre `roles antes && alembic upgrade head
    && roles despues`; `api`/`worker` con `POSTGRES_APP_*`; `respaldos` con `PGUSER`/`PGPASSWORD` desde
    `POSTGRES_RESPALDO_*`. `infra/.env.example` y una línea del README actualizados. 18 tests nuevos/
    modificados en `tests/infra/test_compose.py` (incluye el rojo L-013 con una copia de `respaldar.sh`)
    y 3 en `tests/infra/test_logs_y_proxy.py` (red `aplicacion` en vez de `interna`, hallados al correr
    la suite completa, no sólo el archivo nombrado en la tarea). `ningún servicio permanente tiene
    POSTGRES_PASSWORD` se verificó excluyendo `db` (el rol de arranque mismo, lo crea la imagen) y
    `migraciones` (restart "no"): no está escrito así en D1 pero es la lectura consistente con la
    realidad, anotado como juicio en el informe. `docker compose config --quiet` validado con un entorno
    completo (real, no sólo el parser YAML). `humo.sh` corrido el 15/10/2026 tras que Juani completara
    `infra/.env`: falló primero (`alembic current` dentro de `api`, que ya no tiene las credenciales del
    migrador); arreglado leyendo `alembic_version` por `psql` como el rol de arranque, igual que ya se
    hacía para la base restaurada; `shellcheck` (vía Docker, como el CI) en verde; segunda corrida: HUMO
    OK, los 14 pasos, exit 0.

## 3. Tablas mínimas y Row-Level Security

- [x] 3.1 Migración `0003_acceso_minimo` (D5, D6) con el helper `aislar_por_administracion`, en `tests/integracion/test_rls_acceso_minimo.py`, conectados como `proptech_app` con dos administraciones sembradas por el migrador con su propio `set_config` (E1): sin tenant, cero filas de cada tabla y sin error; con tenant `''`, lo mismo; con el tenant de A, el complejo de B por su id da cero filas; `INSERT` y `UPDATE` con `administracion_id` de B fallan y no dejan nada; una unidad de A colgada de un complejo de B falla por la FK compuesta; una asignación de vecino con una unidad de otro complejo de A falla por la FK `(administracion_id, complejo_id, unidad_id)`; una asignación de vecino sin unidad o de colaborador sin nivel falla por el `CHECK`; dos personas con el mismo email en A fallan y en A y B pasan; `downgrade` a 0002 deja el esquema como estaba y `upgrade` vuelve. Verlos fallar con la base de hoy, implementar, verlos pasar. Escenarios: `aislamiento-por-administracion` › Otra administración no ve nada; › Escritura cruzada rechazada; › Referencia cruzada rechazada; › Referencia a otro edificio rechazada; › Tenant ausente; › Tenant vacío. Lecciones: L-016, L-017.
  - Hecho 15/10/2026: `migraciones/ayudas_rls.py` (`aislar_por_administracion`) y `migraciones/versions/
    0003_acceso_minimo.py` (5 tablas). 19 tests en `tests/integracion/test_rls_acceso_minimo.py`, con
    contenedor propio y los roles reales (no el placeholder). Rojos reales encontrados y corregidos:
    faltaba `UNIQUE(administracion_id, id)` en `persona` (sin eso, Postgres no podía crear la FK
    compuesta de `asignacion_rol`, error `InvalidForeignKey`); la escritura cruzada la rechaza RLS con
    `InsufficientPrivilege`, no un `CHECK` (corregido en el test); el test de email único usaba una
    conexión en `autocommit=True`, así que su `rollback()` no deshacía nada (corregido con conexiones
    separadas y `autocommit=False`). Suite completa: 694 passed + 1 xfailed (sin regresión). `humo.sh`
    corrido de nuevo con la migración 0003 ya en el stack real: HUMO OK.
- [x] 3.2 Guardián del catálogo (D5) en `tests/integracion/test_catalogo_rls.py`: después de `upgrade head`, se cumplen las tres reglas de D5 (RLS forzada, política con `missing_ok` y permisos para la app; `complejo_id NOT NULL` con FK compuesta salvo las excepciones; tablas sin `administracion_id` sólo en la lista técnica). Ver el rojo cinco veces, cada una con una migración de prueba sobre una copia (L-013): una tabla sin `FORCE`, una sin política, una política con `current_setting` de un solo argumento, una sin `GRANT`, una con `complejo_id` nulo o sin la FK compuesta; cada rojo nombra la tabla. Escenarios: `aislamiento-por-administracion` › Una tabla nueva sin candado. Lecciones: L-013, L-016.
  - Hecho 15/10/2026: el guardián (`revisar_catalogo`) vive directo en `tests/integracion/test_catalogo_rls.py`
    (así lo describe design.md), recorriendo `pg_tables`/`pg_class`/`pg_policies`/`pg_constraint` con el
    rol de arranque. 6 tests (el esquema real sin problemas + los 5 rojos, cada uno con una tabla `zz_*`
    creada a mano y borrada al final, nunca una migración real). Rojo real encontrado en el camino: una
    política `CREATE POLICY ... USING (...)` sin `WITH CHECK` explícito queda con `with_check = NULL`
    en el catálogo (Postgres no copia `USING` a `WITH CHECK`), lo que hacía que los cinco escenarios
    reportaran "sin política" además de su defecto propio; se corrigió agregando `WITH CHECK` igual a
    `USING` en los cuatro escenarios que no prueban el formato de la política, y se agregaron
    aserciones negativas para que cada rojo aísle un solo defecto. Suite completa: 700 passed + 1
    xfailed. No se tocó ninguna migración ni `compose.yaml`; no se repitió `humo.sh`.

## 4. El tenant en la sesión

- [x] 4.1 `abrir_sesion` y `after_begin` (D4) en `tests/integracion/test_tenant_por_transaccion.py`, con un engine de `pool_size=1` como `proptech_app`: una sesión con el tenant de A confirma y la siguiente, abierta sin tenant, lee cero filas de A; lo mismo después de revertir y después de una excepción; dentro de una sesión con el tenant de A, un `commit` y una segunda transacción siguen viendo A; una sesión abierta con `fabrica()` directo (sin `abrir_sesion`) lee cero filas; un tenant que no es `UUID` (un `str`) levanta antes de ejecutar SQL; la misma batería corre con la sesión usada desde `asyncio.to_thread` y desde un `threading.Thread`, y en los dos casos ve A (el tenant no depende del hilo, L-015). Escenarios: `aislamiento-por-administracion` › El pedido siguiente no hereda; › Una segunda transacción en el mismo pedido. Lecciones: L-009, L-015.
  - Hecho 15/10/2026: `abrir_sesion` y `registrar_tenant_por_administracion` en `base_de_datos.py`, gemelas
    de `registrar_application_name` (mismo patrón de `after_begin`). 8 tests en
    `tests/integracion/test_tenant_por_transaccion.py`. RED real confirmado (`git stash` sobre
    `base_de_datos.py`, `ImportError`, L-013) y restaurado. Al principio reusaba el contenedor de sesión
    (`roles_reales`/`esquema_migrado`); corriendo la SUITE COMPLETA (no sólo el archivo) salió un orden
    roto real: este archivo y `test_identidad_api.py` (4.2) disparaban `esquema_migrado` por primera vez
    antes, en el orden alfabético, que archivos preexistentes (`test_idempotencia.py`,
    `test_migracion_trabajos_hechos.py`, `test_migraciones_y_salud_real.py`) que corren su propio
    `upgrade head`/`downgrade base` sobre el MISMO contenedor asumiendo que corren primero; su
    `downgrade base`, al correr después, le borraba el esquema a este archivo a mitad de sesión
    (`UndefinedTable: relation "administracion" does not exist`). Arreglado dándole a este archivo (y a
    4.2) su propio contenedor, como ya hacían 3.1 y 3.2. Suite completa, dos corridas: 716
    passed + 1 xfailed, en dos corridas (sin flaky). Al tocar `tests/conftest.py` o un router real, no
    alcanza con correr el archivo propio: hay que correr la suite completa, L-013/L-016.
- [x] 4.2 Identidad y orden de dependencias (D7) en `tests/integracion/test_identidad_api.py`: sin `dependency_overrides`, los tres endpoints responden 401 y un contador de `before_cursor_execute` registra cero sentencias; con la identidad de A inyectada, un `X-Administracion-Id`, un `?administracion_id=` y un campo `administracion_id` en el cuerpo con el id de B no cambian el tenant (la respuesta no trae datos de B y `current_setting` dentro del pedido es A); dos pedidos seguidos con identidades distintas no se contagian; la batería pasa con la dependencia de sesión sincrónica y con una versión `async def` (D4: el tenant no depende de eso). Escenarios: `autorizacion-por-rol` › Pedido sin identidad; `aislamiento-por-administracion` › Encabezado o parámetro con otra administración. Lecciones: L-017.
  - Hecho 15/10/2026: `proptech_core/acceso/dominio/identidad.py` (`Identidad`, frozen); `proptech_api/
    acceso.py` (`identidad_actual` siempre 401, `sesion_con_tenant` depende de ella explícitamente);
    `proptech_api/complejos.py` con los tres endpoints mínimos de D7 (sin `alcanza`/`puede` todavía: eso
    es la tarea 5.x, que va a envolver estos mismos handlers). `app.py` registra
    `registrar_tenant_por_administracion` y el nuevo router. 8 tests en
    `tests/integracion/test_identidad_api.py` (contenedor propio, mismo motivo que 4.1). RED real
    confirmado (archivos movidos, `ImportError`/`ModuleNotFoundError`, L-013) y restaurado. Suite
    completa: 716 passed + 1 xfailed (dos corridas). Web: 16 passed. `humo.sh` corrido de nuevo por tocar
    código real de la API: HUMO OK.
  - **SUPUESTO**: el 404 de estos endpoints hoy sólo cubre "no existe o es de otra administración" (ya
    lo filtra RLS); "existe pero no alcanza" (D6, el alcance por edificio) todavía no está — lo agrega
    5.2 envolviendo estos handlers. No se escribió `complejos.aplicacion` (que nombra design.md): estos
    endpoints consultan la base directo dentro de la sesión con tenant, sin esa capa, porque 4.2 no la
    ejercita todavía. Juicio del constructor, confianza media: si el rompedor o el auditor prefieren que
    esa capa exista desde ahora, es un cambio menor en 5.x, no acá.

## 5. Autorización

- [x] 5.1 Matriz de D-096 y fronteras (D7, Fronteras) en `tests/unitarios/acceso/test_permisos.py` y `tests/unitarios/test_fronteras_de_modulos.py`: una tabla de casos escrita a mano desde D-096 (no generada desde el código) con cada acción por titular, colaborador "editar", colaborador "ver", consejo y vecino; una acción de `Accion` sin fila en la matriz se niega para todos; `alcanza` por rol (titular todo; colaborador sólo complejos asignados; consejo el suyo; vecino sus unidades y su complejo). El test de fronteras recorre los imports con `ast` y falla si `proptech_core.compartido` importa `acceso`, o si `acceso` importa `complejos` (visto en rojo con un import agregado a una copia, L-013). Verlos fallar, implementar, verlos pasar. Escenarios: `autorizacion-por-rol` › La matriz completa. Lecciones: L-013.
  - Hecho 15/10/2026: `proptech_core/acceso/dominio/permisos.py` (`Rol`, `Nivel`, `Accion`, `Asignacion`,
    `puede`, `alcanza`, la matriz de D-096 escrita a mano). 51 tests en `tests/unitarios/acceso/
    test_permisos.py` (cada celda de la matriz, colaborador "ver" sin ninguna fila en Sí, una `Accion`
    sin fila se niega para todos, `alcanza` por rol) y 3 en `test_fronteras_de_modulos.py` (`compartido`
    no importa `acceso`, `acceso` no importa `complejos`, más el rojo L-013 sobre una copia). RED real
    confirmado dos veces: módulo movido (`ImportError`) y, para el checker de fronteras, un import
    agregado a mano al `base_de_datos.py` REAL (no sólo a la copia), visto fallar nombrando el archivo,
    restaurado con `diff` limpio contra el original. Suite completa: 770 passed + 1 xfailed. No se tocó
    ninguna migración, `compose.yaml` ni la API real; no se repitió `humo.sh`.
- [x] 5.2 Alcance por edificio con 404 (D6, D7) en `tests/integracion/test_alcance_api.py`, con `GET /api/complejos/{id}` y `GET /api/unidades/{id}` como `proptech_app` y la identidad inyectada: colaborador en complejo no asignado, vecino en la unidad de otro vecino del mismo complejo y consejo en otro complejo reciben 404; el titular recibe 200 en todos los de su administración; un complejo de B (UUID existente) y un UUID que no existe dan respuestas idénticas en código, cuerpo y encabezados salvo `X-Request-ID`. Escenarios: `autorizacion-por-rol` › Colaborador en un edificio no asignado; › Vecino en la unidad de otro vecino; › Consejo en otro edificio; › Titular; › Id de otra administración contra id inexistente. Lecciones: L-017.
  - Hecho 15/10/2026: nace `proptech_core/complejos/aplicacion/lectura.py` (`cargar_complejo`,
    `cargar_unidad`, sólo lectura; nunca importa `acceso`) y `proptech_core/acceso/aplicacion/
    autorizacion.py` (`cargar_asignaciones`). `proptech_api/complejos.py` compone los dos + `alcanza`,
    con una sola función `_no_encontrado()` para "no existe" y "no alcanza" (mismo cuerpo siempre,
    L-017). 5 tests en `test_alcance_api.py`. RED real confirmado revirtiendo `complejos.py` a su
    versión de la 4.2 (3 failed, código real en vez de esperado). Colateral: los fixtures de 4.2
    (`test_identidad_api.py`) no tenían ninguna `asignacion_rol`, así que `alcanza` les daba 404 donde
    antes daba 200 — se les agregó una asignación de titular (4.2 prueba el cableado de identidad, no
    el alcance; eso es esta tarea). Suite completa: 775 passed + 1 xfailed. `humo.sh` corrido de nuevo
    por tocar código real de la API: HUMO OK. El test que recorre las rutas registradas pidiendo que
    ninguna quede sin envolver (pedido de Juani) lo sumo al cerrar la 5.3, cuando también esté el
    permiso (403): recorrer las rutas antes de que el 403 exista cubriría la mitad de lo pedido.
- [x] 5.3 Permiso por acción con 403 (D7) en `tests/integracion/test_asignar_edificio_api.py`, con `POST /api/complejos/{id}/asignaciones`: el titular asigna un complejo a un colaborador de su administración (201, y el colaborador pasa a verlo por 5.2); un colaborador "editar" en un complejo asignado recibe 403 con `permiso_faltante` igual a `invitar_usuarios_y_asignar_edificios`; el mismo colaborador en un complejo no asignado recibe 404; consejo y vecino, 403 dentro de su alcance; el titular de A asignando a una persona de B (UUID existente) recibe 404 y no queda nada escrito. Escenarios: `autorizacion-por-rol` › Colaborador asigna un edificio; › Sin permiso y fuera de alcance; › Titular asigna un edificio; › Asignar a una persona de otra administración. Lecciones: L-017.
  - Hecho 15/10/2026: `complejos.py` compone `puede()` (403, cuerpo `{"detalle": "sin_permiso",
    "permiso_faltante": "invitar_usuarios_y_asignar_edificios"}`) y suma `existe_persona` (D-096,
    `acceso.aplicacion.autorizacion`) para que el destinatario del cuerpo también pase por RLS antes
    del `INSERT`. 6 tests en `test_asignar_edificio_api.py`. RED real: sin la 5.3, el titular de A
    asignando a una persona de B no daba 404 — daba **500** (`IntegrityError` de la FK, visto en la
    salida real), confirmando que el chequeo explícito hace falta y no alcanza con dejarlo en manos de
    la base. Orden elegido: `existe_persona` se mira DESPUÉS de `puede()`, para no revelar nada del
    cuerpo antes de confirmar que quien pide puede hacer esta acción en este complejo.
  - **Sumado (pedido de Juani, "apuesta 2" del informe de la 4.2)**: `tests/integracion/
    test_rutas_protegidas.py`, con dos chequeos. Estructural: la lista de rutas que el archivo cubre
    tiene que coincidir EXACTO con las que la app registra bajo `/api` (salvo `/api/salud`, pública);
    si alguien agrega una ruta sin pasar por este archivo, el conjunto ya no coincide y el test falla
    nombrándola — confirmado agregando a mano una ruta sin identidad y viéndola fallar, después
    restaurada con `diff` limpio. De comportamiento: cada ruta del candado, sin identidad, da 401 sin
    tocar la base (repetido sobre el conjunto completo); con una identidad real pero sin ninguna fila
    en `asignacion_rol`, nunca da 200/201 contra un recurso real (403 o 404, nunca éxito). 10 tests.
  - Suite completa: 791 passed + 1 xfailed (sin regresión). `humo.sh` corrido de nuevo: HUMO OK.

## 6. Auditoría

- [x] 6.1 Migración `0004_auditoria` y paso de roles `despues` (D2, D9) en `tests/integracion/test_auditoria_tabla.py`: después del arranque completo, el dueño de `auditoria` es el rol de arranque; como `proptech_app`, `UPDATE`, `DELETE` y `TRUNCATE` fallan; como `proptech_migrador`, `UPDATE`, `DELETE`, `TRUNCATE`, `ALTER TABLE auditoria DISABLE TRIGGER ALL` y `ALTER TABLE auditoria NO FORCE ROW LEVEL SECURITY` fallan por no ser dueño, y el trigger y el `FORCE` siguen activos (visto en rojo sin el paso `despues`, con el migrador como dueño, sobre una copia, L-013); como el rol de arranque, `UPDATE`, `DELETE` y `TRUNCATE` fallan por el trigger; una acción que no está en `accion_de_auditoria` falla por la FK; `accion_de_auditoria` coincide con `Accion`; con el tenant de A no aparece ninguna fila de B; `downgrade` (con el rol de arranque) y `upgrade` vuelven. Escenarios: `auditoria-de-acciones` › Editar o borrar como la app; › Editar, borrar o desactivar el bloqueo como el migrador; › Editar o borrar como el dueño; › Dueño de la tabla después de las migraciones; › Acción fuera de la lista; › Auditoría de otra administración. Lecciones: L-013, L-016.
  - Hecho 15/10/2026: migración `0004_auditoria.py` (`accion_de_auditoria`, una fila por `Accion`;
    `auditoria` aislada con `aislar_por_administracion("auditoria", permisos="SELECT, INSERT")`, FK de
    `accion`, trigger `BEFORE UPDATE OR DELETE`/`BEFORE TRUNCATE` que levanta para cualquier rol).
    `ayudas_rls.aislar_por_administracion` suma el parámetro `permisos` (antes siempre
    `SELECT, INSERT, UPDATE, DELETE`), documentando que por sí solo no alcanza: el
    `ALTER DEFAULT PRIVILEGES` de `antes()` de todos modos le regala a la app `UPDATE`/`DELETE` sobre
    cualquier tabla nueva del migrador. `roles.despues()` deja de ser no-op: transfiere `auditoria` al
    rol de arranque y hace el `REVOKE UPDATE, DELETE, TRUNCATE` + `GRANT SELECT, INSERT` explícito
    (pedido de Juani: "que haya un test que demuestre que `proptech_app` NO tiene UPDATE, DELETE ni
    TRUNCATE... aunque las DEFAULT PRIVILEGES se los den por default").
  - **El rojo pedido, real**: `test_rojo_sin_despues_el_migrador_desarma_la_auditoria_y_la_app_tiene_de_mas`
    corre el ciclo completo SIN `despues()` (contenedor propio, L-013) y muestra, por catálogo
    (`has_table_privilege`, no por DML — ver hallazgo abajo): `proptech_app` con `UPDATE`/`DELETE` en
    `True` (el sobre-otorgamiento real) y `TRUNCATE` en `False` (nunca estuvo en la lista de
    `ALTER DEFAULT PRIVILEGES`, así que no hacía falta revocarlo para eso, aunque `despues()` lo revoca
    igual por prolijidad). Con el `REVOKE` de `despues()` puesto, `test_la_app_tiene_exactamente_select_e_insert_sobre_auditoria`
    confirma `{SELECT: True, INSERT: True, UPDATE: False, DELETE: False, TRUNCATE: False}`.
  - **Hallazgo real (no estaba anotado)**: un DML real (`UPDATE`/`DELETE` de prueba) no sirve para ver
    este rojo, porque el trigger de auditoría sigue bloqueando aunque el privilegio esté de más —
    enmascara el sobre-otorgamiento. Hubo que verificar por `has_table_privilege` directamente (L-016).
    Relacionado: `ALTER TABLE auditoria DISABLE TRIGGER ALL` falla con "is a system trigger" (exige
    superusuario por el trigger interno de la FK de `accion`) incluso siendo dueño — así que el rojo que
    prueba "el dueño SÍ puede desactivar el trigger" nombra el trigger propio, nunca `ALL`; el test
    verde ("el migrador NO puede, por no ser dueño") sí usa `ALL` porque ahí "must be owner" llega
    antes de que Postgres mire qué triggers hay, y falla por la razón correcta.
  - `downgrade` de 0004 confirmado que el migrador solo no puede (intento real, falla) y que con el rol
    de arranque devolviéndole la tabla primero, sí (D9/D11, Migration Plan del design.md). 18 tests en
    `test_auditoria_tabla.py`. Suite completa: 809 passed + 1 xfailed; web: 16 passed; `humo.sh` (toca
    migraciones y `roles.py`): HUMO OK, con `revisión en uso=0004 revisión restaurada=0004` en el stack
    real.
- [x] 6.2 Helper en `acceso.aplicacion` y misma transacción (D9) en `tests/integracion/test_auditoria_transaccion.py` y `tests/unitarios/test_auditoria_detalle.py`: asignar un edificio deja exactamente una fila con la persona, `invitar_usuarios_y_asignar_edificios`, el complejo y el `request_id` del pedido; una falla forzada después del `registrar` revierte la asignación y la fila; una fila rechazada por la base revierte la asignación; `registrar` fuera de una transacción es un error; un detalle con una clave no permitida se rechaza antes de escribir y el valor (un marcador) no aparece en el error; el test del registro de `@accion_sensible` recorre todos los casos de uso marcados y exige una fila por cada uno, y se lo ve en rojo con un caso de uso marcado que no registra (sobre una copia, L-013). Escenarios: `auditoria-de-acciones` › Acción confirmada; › Acción revertida; › Registro que no se puede escribir; › Toda acción sensible registrada; › Clave no permitida en el detalle. Lecciones: L-007, L-011, L-013.
  - Hecho 15/10/2026: `proptech_core/acceso/aplicacion/auditoria.py` (`registrar`, exige
    `sesion.in_transaction()`; `_detalle_validado` contra un modelo Pydantic por `Accion`,
    `extra="forbid"`, nunca el valor en el mensaje de error — L-007; `accion_sensible`/
    `casos_sensibles_registrados`, el registro de casos de uso auditados). `complejos/aplicacion/
    escritura.py` nace con el único caso marcado hoy, `asignar_complejo_a_persona`: usa
    `sesion.begin_nested()` si la sesión ya estaba en una transacción (el caso real de la API, que ya
    leyó antes) o `sesion.begin()` si no (una sesión recién abierta, como en el test). `complejos.py`
    deja de insertar `asignacion_rol` a mano: llama al caso de uso y sigue committeando una sola vez.
  - **Hallazgo real**: `:detalle::jsonb` en un `text()` de SQLAlchemy no sustituye el bind — SQLAlchemy
    deja `:nombre::tipo` sin tocar (para no confundirlo con el operador de cast de Postgres) y el `:`
    crudo le llega al driver como `SyntaxError`. Se resolvió con `CAST(:detalle AS jsonb)`. El error de
    `CheckViolation` de `asignacion_rol` también llega envuelto en `sqlalchemy.exc.IntegrityError`
    (`.orig` es el de psycopg) al pasar por `sesion.execute()` del ORM, no suelto como en los tests de
    la 6.1 que usan psycopg directo.
  - 5 tests en `test_auditoria_detalle.py` (unitario, puro, sin base) + 6 en
    `test_auditoria_transaccion.py` (contenedor propio, L-006), incluido el rojo de la 6.2 (L-013: una
    copia del registro con un caso falso que nunca llama a `registrar()`, visto fallar la misma
    aserción que usa el sweep real). Suite completa: 820 passed + 1 xfailed (809 + 11); web: 16 passed;
    `humo.sh` (toca `complejos.py` real): HUMO OK.

## 7. El worker con tenant

- [x] 7.1 `con_administracion_de_tarea` (D8) en `tests/integracion/test_worker_tenant.py` y `tests/unitarios/test_worker_tenant.py`, con `tarea_de_prueba_con_administracion`: un trabajo sin `administracion_id`, con `""`, `"  "`, `123`, `"no-es-uuid"` y un UUID con dígitos no ASCII falla una sola vez, sin reintentos, sin efecto, con el evento fijo `tarea_sin_administracion` y sin el valor en el log; con el tenant de A cuenta sólo complejos de A, también desde el hilo de `asyncio.to_thread`; dos tareas seguidas en el mismo worker (A y después B) ven cada una lo suyo; la clave de idempotencia lleva el `administracion_id` adentro. Escenarios: `cola-de-trabajos` › Trabajo sin administración; › Administración malformada; › Dos tareas seguidas; › El tenant llega al hilo. Lecciones: L-007, L-008, L-009, L-015.
  - Hecho 15/10/2026: `proptech_core/compartido/tenant_de_tarea.py` (`con_administracion_de_tarea`):
    regex ASCII canónica (gemela de `validar_request_id`, L-008) antes que nada, después el modelo
    Pydantic estricto que pide D8 — sólo la regex corta un UUID con dígitos no ASCII, Pydantic estricto
    por sí solo no alcanza (ver hallazgo). Va POR FUERA de `reintentable` en la pila: un
    `administracion_id` inválido ni siquiera llama a la función reintentable, cero reintentos reales.
    Si la tarea recibe `clave`, el decorador le antepone el `administracion_id` (E3: `trabajos_hechos`
    tiene una sola clave global). `tarea_de_prueba_con_administracion` (cuenta complejos) nace en
    `proptech_worker/prueba.py`, sin ruta pública, igual que `tarea_de_prueba`.
  - **Hallazgo real (el más caro de la tarea)**: `proptech_worker/ajustes.py` nunca llamaba
    `registrar_tenant_por_administracion(fabrica)` en `on_startup` — `abrir_sesion` dejaba el tenant en
    `session.info` sin que nada lo convirtiera en `set_config`, así que la política de D5 veía el
    tenant vacío y daba **cero filas siempre, nunca un error** (el mismo tipo de agujero silencioso que
    D5 ya previene del lado de la API desde la 4.1). Se agregó la llamada, gemela de
    `registrar_application_name`; `tarea_de_prueba` (D2, sin `abrir_sesion`) queda igual porque
    `session.info` nunca tiene esa clave para ella.
  - Collateral real (no un rojo buscado): `test_on_startup_usa_crear_engine_con_la_configuracion_del_pool`
    rompió porque parchea `crear_engine`/`crear_fabrica_de_sesiones` con `MagicMock()` y
    `registrar_tenant_por_administracion` intentaba colgar un evento `after_begin` real de un mock
    (`InvalidRequestError`). Se agregó el `patch.object` que faltaba.
  - Rojo visto con pydantic estricto solo (sin la regex ASCII primero): un UUID armado con dígitos
    arábigo-índicos (U+0660 y siguientes) en la forma canónica pasaba `UUID(valor)` de la stdlib sin
    reclamar — el mismo tipo de gotcha de L-008 que ya mordió en `_entero_ascii_estricto`, ahora
    confirmado también en `uuid.UUID()`.
  - Contenedor propio para el archivo de integración (L-006): mismo hallazgo de la 4.1 (`administracion`/
    `complejo` no existen si el contenedor compartido corrió el ciclo de otro archivo primero), y además
    `proptech_worker.ajustes` fija su `Configuracion` una sola vez al importarse — no se puede reapuntar
    a otro contenedor en el mismo proceso, así que el `ctx` de este archivo arma su propio engine a mano.
    10 tests unitarios (puro, sin base) + 3 de integración. Suite completa: 833 passed + 1 xfailed
    (820 + 13); web: 16 passed; `humo.sh` (toca `ajustes.py` real): HUMO OK.

## 8. Redes

- [x] 8.1 La web fuera de la red de la base (D10): partir `interna` en `datos` y `aplicacion` según D10 (los tests estáticos están en 2.3). En el stack levantado, desde `web` una conexión a `db:5432` y a `redis:6379` no se establece, y desde `api` sí; el `request_id` de punta a punta del humo sigue pasando con la IP nueva de Caddy. Verlo fallar antes del cambio de redes (hoy la web alcanza la base). Escenarios: `entorno-de-ejecucion` › La web intenta conectar a la base. Lecciones: L-016.
  - Hecho 15/10/2026: la partición de redes (`datos`/`aplicacion`) ya existía desde la 2.3 — lo único
    que faltaba era el chequeo EN VIVO. Se sumó el paso `(3d)` a `humo.sh`: conexión TCP cruda (nunca un
    ping de aplicación, D10 pide que la red no llegue, no que el otro lado responda bien) desde `web`
    (Node, `net.createConnection`) y desde `api` (Python, `socket`) hacia `db:5432` y `redis:6379`.
    `web` no conecta a ninguna de las dos; `api` conecta a las dos.
  - **Rojo real (L-013)**: sobre una COPIA de `compose.yaml` en `/tmp` (nunca el archivo real) con `web`
    agregada a la red `datos` además de `aplicacion`, se levantó un stack parcial (`db`, `redis`, `web`,
    proyecto Compose separado `proptech-rojo81`) y el mismo chequeo de conexión cruda dio `CONECTO`
    desde la web hacia `db:5432` — confirmando que el paso agregado SÍ detecta el problema que D10
    quiere prevenir. Stack parcial destruido (`down -v`) y archivo temporal borrado; `diff` contra
    `git show HEAD:infra/compose.yaml` confirmó el archivo real intacto, sin tocar.
  - `shellcheck` (vía Docker) sobre `humo.sh` modificado: limpio. Corrida real: `HUMO OK`, con
    `web->db=NO_CONECTO web->redis=NO_CONECTO api->db=CONECTO api->redis=CONECTO` en la salida, y el
    `request_id` de punta a punta (pasos 7, 7b, 8) siguió pasando igual que antes.

## 9. Humo

- [x] 9.1 Sumar al humo (D11, D12), cada paso con su chequeo explícito: `current_user`, `rolsuper` y `rolbypassrls` de la conexión de `api` y de `worker` (`proptech_app`, falso, falso); dos administraciones sembradas con `psql` como rol de arranque, un backup de `respaldos` con `proptech_respaldo`, la restauración en `proptech_restauracion` con `restaurar.sh` y el conteo por administración (2 y 2), más `relforcerowsecurity` y las políticas presentes en la base restaurada. El rojo con el rol equivocado: con una copia de Compose donde `respaldos` usa `proptech_app`, el volcado **falla** (no aparece ningún `.dump` nuevo y el servicio queda no saludable), no da un conteo menor (L-013, L-016). Escenarios: `integracion-continua` › Rol de la app en el stack vivo; › Backup completo en el humo; `entorno-de-ejecucion` › La API conecta como la app; `respaldos-de-la-base` › Backup con dos administraciones; › Volcado con el rol equivocado. Lecciones: L-004, L-006, L-013, L-016.
  - Hecho 15/10/2026: cuatro pasos nuevos en `humo.sh`. `(9b)`: `current_user`/`rolsuper`/`rolbypassrls`
    de la conexión real de `api` y de `worker`, vía `pg_stat_activity` filtrado por `application_name`
    (`proptech-api%`/`proptech-worker%`, D8: dentro de una transacción queda `prefijo:request_id`, el
    `LIKE` alcanza las dos formas) unido a `pg_roles`; los dos dan `proptech_app,false,false`. Siembra
    de dos administraciones con dos complejos cada una (rol de arranque, bypassea RLS) justo después del
    `up --wait`, ANTES de que el healthcheck de `respaldos` ya haya exigido su primer backup automático
    (D9: ese backup corre DENTRO de `start_period`, antes de que el humo llegue a sembrar nada si se
    sembrara después). Backup manual (`respaldar.sh --una-vez`, ya pensado para esto) después de
    sembrar, y el resto de las verificaciones de la 9.1 usan ESE dump (el más nuevo, no
    necesariamente el único) para no depender de si el automático alcanzó a llevarse los datos.
    Verificado en la base restaurada: conteo por administración (2, 2), `relforcerowsecurity` y
    `pg_policies` presentes en `administracion`/`complejo` (el volcado se lleva el esquema, no sólo los
    datos).
  - **Hallazgo real**: concatenar un booleano con `||` en SQL lo castea a `"true"`/`"false"` (el literal
    SQL), NO al `"t"`/`"f"` que psql muestra para una columna booleana sola — la primera versión del
    chequeo `(9b)` comparaba contra `"proptech_app,f,f"` y el script cortaba en seco ahí (los pasos
    10 en adelante ni se veían en la salida, `set -e` se llevó todo a la limpieza) hasta corregir la
    comparación.
  - **Rojo real (L-013)**: sobre una copia de `compose.yaml` en `/tmp` con `respaldos` usando
    `POSTGRES_APP_USER`/`_PASSWORD` en vez de los de `proptech_respaldo`, un stack parcial (`db`,
    `migraciones`, `respaldos`, proyecto separado `proptech-rojo91`) mostró el log
    `{"evento":"respaldo_fallido","etapa":"pg_dump"}`, cero archivos `.dump` nuevos y el servicio
    `unhealthy` a los ~150s — nunca un conteo menor, falla de punta a punta. Stack destruido, carpeta
    temporal y archivo de Compose mutado borrados; `diff` contra `git show HEAD:infra/compose.yaml`
    confirmó el archivo real intacto.
  - `shellcheck` sobre `humo.sh`: limpio. Corrida real completa: `HUMO OK`. Suite completa (no cambió
    código Python, sólo `infra/`): backend 833 passed + 1 xfailed, web 16 passed, sin regresiones.

## 10. Cierre

- [x] 10.1 **Después de la última vuelta de correcciones** (L-010), y como lo último del cambio: correr `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh` y `bash infra/ci/humo.sh` **en ese orden y de a uno** (D13); anotar la cantidad de tests de cada lado contra la línea de base de 1.1, con hora y commit; si el código cambia después, repetirla. Escenarios: todos (corrida final). Lecciones: L-003, L-005, L-010.
  - Hecho 15/10/2026 15:14-15:19, commit `7faadce` (el último antes de esta misma entrada; nada de
    código cambió después de esta corrida, sólo esta línea de tasks.md): `test-backend.sh` → 833
    passed + 1 xfailed (209s); `test-web.sh` → 16 passed; `humo.sh` → HUMO OK (confirmado dos veces, la
    segunda con `tee` + `rg "HUMO OK"` + `${PIPESTATUS[0]}` = 0, para no depender de un `tail` que
    pudiera cortar la línea).
  - Contra la línea de base de la 1.1 (606 passed + 1 xfailed, commit `bc4ca9f`): **+227 tests** de
    backend a lo largo de las tareas 2.1 a 9.1; web sin cambios (16, no era parte de este cambio);
    humo.sh pasó de 1 paso nuevo (nombrado en 2.3) a HUMO OK con los pasos de las tareas 3.1 a 9.1
    sumados (3d, 9b, el backup manual de dos administraciones, el chequeo de rol de la conexión).
  - **El cambio queda acá, sin archivar y sin pushear** (pedido explícito del orquestador): lo que sigue
    es el rompedor. No hay archivos sin commitear (`git status` limpio salvo esta misma edición).

## 11. Vuelta 2 (rompedor + auditor, 15/10/2026)

Convención: igual que el resto — el test se ve fallar HOY antes del código, y el rojo queda pegado
en el "Hecho" de cada una. Siete bloqueantes de la auditoría (`auditoria-vuelta-1.md`):
R1, R2, R3, R4, R7, R8, R10. Las deudas R5, R6, R9 y R11 NO se tocan (quedan con dueño: 2b o 3).

- [x] 11.1 R1 · `roles antes` falla en un segundo ciclo sobre el mismo volumen: `_secuencias_de_public_del_rol` intentaba reasignar `auditoria_id_seq` (IDENTITY, ligada a la tabla), y Postgres lo rechaza. Rojo: ciclo completo `antes → upgrade head → despues → antes → despues` sobre la misma base. Corrección: excluir con `pg_depend` (`deptype IN ('a','i')`) las secuencias ligadas a una columna. Arreglar el test de la línea 231 (no podía dar rojo: nunca pasaba por la 0004) y sumar al humo un segundo `up` sobre el mismo volumen.
  - Hecho 15/10/2026: rojo real confirmado sobre el código sin parchear (revertido con `git checkout`
    momentáneo, L-013): `cannot change owner of sequence "auditoria_id_seq"`, mismo mensaje exacto
    que el rompedor. `_secuencias_de_public_del_rol` ahora excluye con `pg_depend`
    (`deptype IN ('a','i')`) cualquier secuencia ligada a una columna, no sólo la de `auditoria`
    (pedido explícito del auditor: "no alcanza con excluir sólo la de auditoria"). Test nuevo
    `test_un_segundo_ciclo_completo_sobre_el_mismo_volumen_no_falla` en `test_roles.py`, con el ciclo
    exacto que pidió el auditor. El test viejo de la línea 231 queda con un docstring que aclara su
    alcance real (volumen 1d, sin la 0004 de por medio — nunca iba a ver esto) en vez de dar a entender
    que cubría el reinicio real. Humo: paso `(1b)`, `compose down` (sin `-v`, conserva volúmenes) +
    `compose up -d --wait` de nuevo; shellcheck limpio; `HUMO OK` con la línea
    "el segundo up terminó con exit 0" confirmada en la salida real.
- [x] 11.2 R2 · `fn_auditoria_bloqueada` queda del migrador: puede reemplazarla, borrarla (`DROP ... CASCADE`) o escalar a superusuario. Rojo: test de catálogo, `proowner` de toda función usada por un trigger de `auditoria` tiene que ser el rol de arranque. Corrección: `despues()` también transfiere la función (`ALTER FUNCTION ... OWNER TO`) y le fija `SET search_path`.
  - Hecho 15/10/2026: rojo confirmado (dueño = `proptech_migrador`; `CREATE OR REPLACE` y
    `DROP ... CASCADE` como migrador, ambos pasaban). `despues()` ahora recorre por catálogo
    (`pg_trigger` + `pg_proc`, nunca un nombre fijo) las funciones de los triggers de `auditoria` y les
    hace `ALTER FUNCTION ... OWNER TO <arranque>` + `SET search_path = ''`. 2 tests nuevos en
    `test_auditoria_tabla.py`. **Collateral real**: el `downgrade` de la 0004 (que corre como migrador)
    dejó de poder `DROP FUNCTION` por la misma razón que ya no puede tocar la tabla — `_devolver_auditoria_al_migrador`
    del test ahora también le devuelve la función antes de bajar, igual que ya hacía con la tabla (D11).
    20/20 tests de `test_auditoria_tabla.py` y 10/10 de `test_roles.py`.

- [x] 11.3 R3 · La app tiene `INSERT`/`UPDATE`/`DELETE` sobre `accion_de_auditoria` (sólo debería `SELECT`, D1): puede ampliar o vaciar el vocabulario de acciones sensibles. Rojo: como `proptech_app`, los tres se niegan (hoy pasan). Corrección: `REVOKE` explícito en `despues()` (no alcanza con excluirla del grant de `antes()`: los `DEFAULT PRIVILEGES` se los dan igual).
  - Hecho 15/10/2026: rojo confirmado (4 tests, los 4 en rojo: SELECT/INSERT/UPDATE/DELETE daban todos
    `True`, y los tres DML como app pasaban sin error). Fix de dos partes, como pedía el auditor:
    `accion_de_auditoria` sumada a `_TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP` (no alcanza sola, documentado
    en el propio código) + `REVOKE INSERT, UPDATE, DELETE` / `GRANT SELECT` explícito en `despues()`,
    mismo patrón que ya existía para `auditoria`. 34/34 tests entre `test_auditoria_tabla.py` y
    `test_roles.py`; guardián de catálogo (`test_catalogo_rls.py`) sin regresión, 6/6.

- [x] 11.4 R4 · `despues()` no verifica que el trigger y el `FORCE` sigan activos, como promete D2. Rojo: borrar un trigger (o `NO FORCE`) como arranque y correr `despues()` — hoy sale 0. Corrección: verificar al final (incluido el dueño de la función, R2) y salir con 1 nombrando qué falta si algo no está.
  - Hecho 15/10/2026: rojo confirmado (borrar `trg_auditoria_sin_truncate` como arranque y correr
    `despues()` de nuevo: salía 0, sin mirar nada). `_verificar_auditoria_protegida` nueva en
    `roles.py`: `FORCE`, los dos triggers (nombrados, habilitados) y el dueño de sus funciones (R2),
    corrida al final de `despues()` dentro de la MISMA transacción — si algo falta, `despues()` no
    confirma nada (rollback) y sale 1 nombrando qué, vía la excepción propia `AuditoriaNoProtegida`
    (nueva rama en `_main`). No recrea lo que falta: D9/D11 ya dicen que tocar `auditoria` es cosa del
    paso de roles, no un arreglo silencioso dentro de él. **Collateral real**: el teardown de
    `test_auditoria_transaccion.py` tenía su propia copia de `_devolver_auditoria_al_migrador` sin el
    fix de R2 (la función también, no sólo la tabla) — mismo síntoma que ya se había arreglado en
    `test_auditoria_tabla.py`, acá duplicado porque cada archivo de integración es autocontenido
    (L-006). Suite completa: 841 passed + 1 xfailed (833 + 8 de R1 a R4); `humo.sh`: HUMO OK.

- [x] 11.5 R7 · Un `SET` de sesión (sin `LOCAL`) del tenant contagia al pedido siguiente que abre sin tenant. Rojo: pool de 1 conexión, `SET` de sesión con el tenant de A, después una sesión sin tenant — hoy ve las filas de A. Corrección: un evento de reset/checkin del pool que limpie `app.administracion_id` como cinturón, además del `SET LOCAL`.
  - Hecho 15/10/2026: rojo confirmado con un script standalone (fuera de pytest, para no depender de
    fixtures compartidos): sin el fix, una sesión sin tenant después de un `SET` de sesión crudo ve
    `['Complejo A']`; con el fix, `[]`. `registrar_reset_del_tenant_al_devolver(engine)` nueva en
    `base_de_datos.py`: evento `checkin` del ENGINE (no de la fábrica de sesiones — es un evento de
    pool, no de sesión) que corre `RESET app.administracion_id` sobre la conexión cruda cada vez que
    vuelve al pool, después del `ROLLBACK` que SQLAlchemy ya hace por default. `RESET` sobre un
    parámetro nunca fijado en esa sesión no es error (verificado). Cableado en `proptech_api/app.py` y
    `proptech_worker/ajustes.py`, gemelo de `registrar_tenant_por_administracion`. Test nuevo en
    `test_tenant_por_transaccion.py` (pool de 1 conexión, mismo patrón que el resto del archivo).
  - **Collateral real (el mismo patrón que ya había mordido en la 7.1)**: tres tests que mockean
    `crear_engine`/`crear_fabrica_de_sesiones` con `MagicMock()` (`test_motor_unico.py` x2,
    `test_worker_tarea_de_prueba.py` x1) rompieron porque el nuevo evento "checkin" intenta colgarse
    de un `MagicMock()`, que no es un target de evento válido de SQLAlchemy — mismo `InvalidRequestError`
    que ya se vio con `registrar_tenant_por_administracion` en la 7.1. Se sumó el `patch.object`
    correspondiente en los tres. Suite completa: 842 passed + 1 xfailed; `humo.sh`: HUMO OK.

- [x] 11.6 R8 · Nada impide que `proptech_app` quede con el mismo nombre o contraseña que otro rol (incluido el de arranque): la API podría arrancar con `BYPASSRLS` o con la contraseña del superusuario sin que nadie lo note. Rojo: `antes()` con dos `*_USER` iguales, o dos contraseñas iguales de las cuatro — hoy sale 0. Corrección: `antes()` rechaza nombres o contraseñas repetidas (sin mostrar valores); la API y el worker no arrancan si su propia conexión tiene `rolsuper`, `rolbypassrls` o es dueña de alguna tabla. `infra/.env.example` con placeholders distintos.
  - Hecho 15/10/2026: dos frentes, dos rojos reales. (1) `antes()`: rojo confirmado con
    `git checkout` momentáneo (L-013) — con dos `*_USER` o dos `*_PASSWORD` iguales, salía 0 sin
    mirar nada. `_verificar_los_cuatro_roles_son_distintos` nueva, corre ANTES de tocar la base (puro
    Python, sin ida y vuelta a Postgres): nombra las DOS VARIABLES que colisionan, nunca el valor.
    (2) `verificar_rol_de_aplicacion_seguro` nueva en `base_de_datos.py`: la API (`app.py`, dentro del
    `try` del lifespan, para que el `finally` siga limpiando el engine si levanta) y el worker
    (`ajustes.py.on_startup`) no arrancan si su propia conexión es superusuario, tiene `BYPASSRLS`, o
    es dueña de alguna tabla. 4 tests de integración nuevos (`test_rol_de_aplicacion_seguro.py`): la
    app pasa limpia; respaldo (`BYPASSRLS`), migrador (dueño de tablas) y el rol de arranque
    (superusuario) levantan, cada uno nombrando la razón real.
  - `infra/.env.example` traía las cuatro contraseñas iguales (el propio hallazgo del rompedor): ahora
    cada una lleva el nombre del rol al final (`...-arranque`, `...-migrador`, `...-app`,
    `...-respaldo`), y un test estático nuevo en `test_compose.py` exige que sigan siendo distintas.
  - **Collateral real (tercera vez, mismo patrón)**: los tres tests que mockean `crear_engine` con
    `MagicMock()` volvieron a romper — ahora porque `verificar_rol_de_aplicacion_seguro` desempaqueta
    una fila de 3 columnas real, y un mock no la da (`ValueError: not enough values to unpack`). Mismo
    `patch.object` de siempre, sumado a los dos anteriores (R7 ya había dejado uno ahí).
  - Verificado contra el `.env` REAL de Juani (nunca leído directo, D18): `humo.sh` corrido entero dio
    `HUMO OK`, confirmando que esas contraseñas ya eran distintas (las generó él al azar, no copió el
    ejemplo). Suite completa: 849 passed + 1 xfailed (842 + 7); web: 16 passed.

- [x] 11.7 R10 · Con el rol equivocado, `respaldos --salud` sigue dando 0 hasta 1,5 intervalos después del último backup bueno (36h con el default): esconde la falla salvo que se arranque sin backups previos. **Opción A** (la que corresponde: la opción B es cambiar el escenario y es de Juani, D-094): una marca `.ultimo-fallo` que `--salud` mire. Rojo: `.ultimo-ok` bueno previo + credenciales de la app + un ciclo fallido — hoy `--salud` sigue en 0.
  - Hecho 15/10/2026 (opción A, nunca la B): rojo confirmado con `git checkout` momentáneo
    (L-013) sobre `respaldar.sh` — con un `.ultimo-ok` bueno y un ciclo fallido después,
    `--salud` seguía dando 0. `.ultimo-fallo` nueva: `ciclo_backup` la escribe en cada uno de sus
    cinco puntos de falla (`pg_dump`, `pg_restore_list`, `mv`, `marca_ultimo_ok`, `retencion`) y la
    borra al final, sólo si el ciclo completo salió bien. `verificar_salud` ahora, además de lo que ya
    tenía, da no saludable si `.ultimo-fallo` es MÁS NUEVA que `.ultimo-ok` — exactamente el caso real
    que el escenario pide y que el humo (que arranca sin backups previos, L-016) no alcanzaba a probar.
    2 tests nuevos en `tests/infra/test_respaldos.py` (el harness sin Docker, con `pg_dump` falso):
    salud cae después de un ciclo fallido con un éxito previo, y un éxito posterior vuelve a limpiarla.
    `shellcheck`: limpio. Suite completa: 851 passed + 1 xfailed (849 + 2).

- [x] 11.8 Corrida de cierre de la vuelta 2 (D13, L-010): `test-backend.sh`, `test-web.sh`, `humo.sh` (con los dos `up`), en ese orden y de a uno, contra el commit final de la vuelta 2.
  - Hecho 15/10/2026 16:38-16:44, commit `d1e2a6c` (último antes de esta entrada): `test-backend.sh`
    → 851 passed + 1 xfailed (229s); `test-web.sh` → 16 passed; `humo.sh` → HUMO OK, con el paso `(1b)`
    (segundo `up` sobre el mismo volumen, R1) confirmado en la salida real.
  - Contra la base de la vuelta 1 (833 passed + 1 xfailed, commit `7faadce`): **+18 tests** a lo largo
    de R1, R2, R3, R4, R7, R8 y R10 (1 + 2 + 2 + 1 + 1 + 7 + 2 — más el corregido de la línea 231 de
    `test_roles.py`, que no suma tests nuevos pero deja de ser engañoso). Las deudas R5, R6, R9 y R11
    no se tocaron: siguen con dueño (2b, 3).
  - **El cambio queda acá, sin archivar y sin pushear**: lo que sigue es la vuelta 2 del rompedor y el
    auditor, sobre estas siete correcciones. `git status` limpio salvo esta misma edición.

## 12. Vuelta 3 (rompedor + auditor, 15/10/2026, sobre `7313564`)

Tres bloqueantes: V2-1 (regresión de R7), V2-2 (R4 verificaba forma, no bloqueo) y V2-4 (R10 no
cubre el disco lleno). Las deudas (R5, R6, R9, R11, V2-3, V2-5, V2-7) y notas (V2-6, V2-8, V2-9)
NO se tocan: quedan con dueño o archivadas tal como las dejó el auditor.

- [x] 12.1 V2-1 · `registrar_reset_del_tenant_al_devolver` (R7) rompe el pool cuando una conexión se corta a mitad de pedido o de tarea: el evento `checkin` hacía `dbapi_connection.cursor()` sin mirar si es `None` (SQLAlchemy lo deja así cuando ya invalidó la conexión sola), y un `AttributeError` sin atrapar dentro de `checkin` aborta el "devolver al pool" de SQLAlchemy a mitad de camino — el lugar queda `checked out` para siempre. Con el pool por default, 15 cortes dejan la API en 500 permanente; en el worker, el error deja de ser pasajero (`AttributeError` no reintenta). Rojo: `pg_terminate_backend` real a mitad de consulta (sesión y tarea del worker) — hoy `AttributeError`, `checkedout=1` y después `TimeoutError`/sin reintento. Corrección: `if dbapi_connection is None: return`, y cualquier error real del `RESET` invalida la conexión (`connection_record.invalidate`) en vez de propagar.
  - Hecho 15/10/2026: rojo real confirmado (`AttributeError: 'NoneType' object has no attribute
    'cursor'` en `base_de_datos.py:148`, idéntico al informe) con dos tests nuevos en
    `tests/integracion/test_reset_de_pool_tras_corte.py` (contenedor propio, L-006; evento REAL
    cableado, nunca un mock, L-017): uno a nivel sesión (pool de 1, overflow 0, `pg_terminate_backend`
    desde una conexión de superusuario aparte) y uno en el worker (`@con_administracion_de_tarea
    @reintentable`, el corte durante un `pg_sleep(2)`). `_checkin` ahora: `dbapi_connection is None`
    se ignora sin más; cualquier error real del `RESET` invalida la conexión en vez de propagar.
    Verde: `OperationalError` (no `AttributeError`), `pool.checkedout() == 0`, la sesión siguiente
    responde, y la tarea termina en `arq.Retry` con `reintento_programado` (ya no necesitó tocar
    `reintentos.py`: `OperationalError` ya estaba en `_ERRORES_PASAJEROS_POR_NATURALEZA`). El test de
    R7 de la vuelta 2 (`test_un_set_de_sesion_sin_local_no_contagia...`) sigue en verde, sin cambios.

- [x] 12.2 V2-2 · `despues()` (R4) verificaba la FORMA del bloqueo de `auditoria`, no que bloqueara de verdad, y el rompedor lo reprodujo como rol de arranque FUERA de cualquier ventana de migración (el auditor subió la severidad por esto: el informe la había acotado, de forma falsa, a "la tanda de la 0004"). (a) `ALTER TABLE auditoria DISABLE ROW LEVEL SECURITY` (con `FORCE` intacto) pasaba `despues()` con exit 0 — sin RLS encendida, la política no se aplica a NADIE. (b) Reemplazar el cuerpo de `fn_auditoria_bloqueada()` (mismo nombre, mismo dueño, mismos triggers habilitados) también pasaba con exit 0 — igual que recrear el trigger sobre otro evento con `WHEN (false)`. Rojo: los tres, hoy exit 0. Corrección: sumar `relrowsecurity` al catálogo (a), y probar el BLOQUEO DE VERDAD dentro de un `SAVEPOINT` (b): insertar una fila de prueba, exigir que `UPDATE`/`DELETE`/`TRUNCATE` fallen, y revertir todo.
  - Hecho 15/10/2026: los tres rojos confirmados sobre `7313564` sin tocar, exit 0 en los tres (idéntico
    al informe). `_verificar_auditoria_protegida` ahora también exige `relrowsecurity=true` (antes sólo
    miraba `relforcerowsecurity`: con RLS apagada el `FORCE` da igual). Nueva
    `_verificar_bloqueo_de_escritura_de_verdad`: dentro de un `SAVEPOINT`, fija un tenant de prueba
    (`set_config(..., true)`; el rol de arranque ES superusuario y bypassea RLS siempre, sin importar
    `BYPASSRLS` ni `FORCE` — se fija de todos modos por prolijidad, no porque haga falta sortear nada),
    inserta una fila con ese tenant, intenta `UPDATE`, `DELETE` y `TRUNCATE` de verdad y exige que los
    tres levanten, y revierte todo con `ROLLBACK TO SAVEPOINT`; que nunca quede la fila de prueba lo
    prueba `test_despues_no_deja_la_fila_de_prueba_en_auditoria` (13.3, vuelta 4). Esto agarra la variante (a), la (b) y la variante 2
    del rompedor (trigger recreado sobre otro evento) con el MISMO mecanismo, sin necesitar comparar
    `tgtype`/`tgqual`/un hash de `prosrc` (la otra opción que daba el auditor). 3 tests nuevos en
    `test_auditoria_tabla.py`, cada uno con su propio contenedor (rompen el estado a propósito).

- [x] 12.3 V2-4 · `respaldar.sh --salud` (R10) seguía en 0 cuando el ciclo falla con el disco lleno: `date +%s > .ultimo-fallo` crea el archivo pero la escritura falla con el disco lleno, y queda VACÍO — un contenido vacío no pasa el `fullmatch` de `verificar_salud` y la marca se ignoraba en silencio, la misma falla que R10 ya había cerrado para el rol equivocado. Rojo: harness (`.ultimo-fallo` vacío y más nuevo que `.ultimo-ok`, hoy `--salud` da 0) y el script real `v2_r10_disco_lleno.sh` del rompedor (hoy "salud tras ciclo fallido exit=0"). Corrección: comparar por mtime (`-nt`) cuando el contenido no se puede leer como número — nunca depende de poder ESCRIBIR con el disco lleno, sólo lee archivos que ya existen.
  - Hecho 15/10/2026: rojo del harness confirmado (`test_salud_falla_con_un_ultimo_fallo_vacio_mas_nuevo_que_el_ultimo_ok`,
    `assert 0 != 0`). Rojo real pegado tal cual, corriendo `levantar.sh` + `v2_r10_disco_lleno.sh` del
    rompedor sobre `7313564` (antes del fix):
    ```
    ciclo 1 exit=0 ; salud tras ciclo bueno exit=0
    tmpfs 512K 512K 0 100% /respaldos
    date: write error: No space left on device
    ciclo 2 (disco lleno) exit=1
    .ultimo-fallo existe (0 bytes)
    salud tras ciclo fallido exit=0
    ```
    `verificar_salud` ahora: si `.ultimo-fallo` no tiene contenido numérico válido, compara por `-nt`
    contra `.ultimo-ok` en vez de ignorar la marca. 2 tests nuevos en `test_respaldos.py` (uno "sano",
    confirmado con dientes: mutado a mano a "cualquier `.ultimo-fallo` = no saludable", dio rojo). Mismo
    script del rompedor, re-corrido con el fix: `salud tras ciclo fallido exit=1`. `shellcheck`: limpio.


- [x] 12.4 Corrida de cierre de la vuelta 3 (D13, L-010): `test-backend.sh`, `test-web.sh`, `humo.sh` (con los dos `up`), en ese orden y de a uno, contra el commit final de la vuelta 3.
  - Hecho 15/10/2026 17:41-17:47, commit `9228e64` (último antes de esta entrada): `test-backend.sh` →
    858 passed + 1 xfailed (276s), limpio; `test-web.sh` → 16 passed; `humo.sh` → HUMO OK, con el paso
    `(1b)` (segundo `up`, R1) confirmado en la salida real. (Una corrida intermedia, antes de commitear,
    tuvo 1 fallo aislado en `test_worker_tenant.py::test_administracion_invalida_falla_una_sola_vez_sin_efecto[entero]`
    por una coincidencia de substring ("123" dentro del dict de un `LogRecord` no relacionado, nada que
    ver con esta vuelta); no reprodujo ni aislado ni en esta corrida final — flake pre-existente, no
    tocado.)
  - Contra la base de la vuelta 2 (851 passed + 1 xfailed, commit `d1e2a6c`): **+7 tests** (2 de V2-1,
    3 de V2-2, 2 de V2-4). Las deudas y notas de la vuelta 2 (R5, R6, R9, R11, V2-3, V2-5, V2-6, V2-7,
    V2-8, V2-9) no se tocaron.
  - **El cambio queda acá, sin archivar y sin pushear**: lo que sigue es la vuelta 3 del rompedor y el
    auditor, o la tabla directo a Juani si no hay más bloqueantes.

## 13. Vuelta 4 (decisión de Juani: opción B, 15/10/2026)

Juani eligió la opción (B) del dictamen de la vuelta 3 (`auditoria-vuelta-3.md`, sección "Las
opciones") el 15/10/2026: cerrar los 4 puntos que quedaban abiertos — V3-1, V3-2, V3-4 (sólo M8 y
M5) y V3-10 — y no tocar ninguna otra deuda (R5, R6, R9, R11, V2-3, V2-5, V2-7, V3-5 a V3-9, V3-11
a V3-15 siguen iguales).

- [x] 13.1 V3-1 · `_verificar_politica_de_auditoria` (`despues()`) comparaba contra una lista de
  cosas prohibidas, nunca contra el CONJUNTO ENTERO de políticas esperado sobre `auditoria`: una
  política PERMISIVA extra agregada a mano (se combina con OR con la original, abriendo la tabla
  igual aunque la original siga intacta) pasaba con exit 0, e `ALTER POLICY ... USING (true)`
  (deja el nombre y la forma intactos, sólo cambia la condición) también. Rojo, contra `ac688b2`
  (vía `git stash` sobre el fix, L-013):
    ```
    $ uv run pytest tests/integracion/test_auditoria_tabla.py::test_rojo_despues_no_notaba_una_politica_permisiva_extra tests/integracion/test_auditoria_tabla.py::test_rojo_despues_no_notaba_la_politica_alterada -v -m integracion
    FAILED ...test_rojo_despues_no_notaba_una_politica_permisiva_extra - AssertionError: assert 0 == 1
    FAILED ...test_rojo_despues_no_notaba_la_politica_alterada - AssertionError: assert 0 == 1
    2 failed in 6.84s
    ```
  Corrección: `_verificar_politica_de_auditoria` exige EXACTAMENTE una política sobre `auditoria`,
  con su nombre, PERMISSIVE, para todos los comandos (`polcmd = '*'`), PUBLIC (`polroles` en
  `(None, [0])`), y `qual`/`with_check` iguales al string exacto que `pg_get_expr` devuelve para lo
  que genera `ayudas_rls.aislar_por_administracion` (confirmado contra Postgres 18.6 real con un
  script de diagnóstico aparte, nunca adivinado — Postgres normaliza los casts `::text`/`::uuid`
  que el SQL original no escribe explícitos). 2 tests nuevos.
  - Hecho 15/10/2026: verde confirmado (ver 13.5, corrida de cierre).

- [x] 13.2 V3-2 · Las tres sondas de `_verificar_bloqueo_de_escritura_de_verdad` (UPDATE/DELETE/
  TRUNCATE) usaban `except psycopg.Error: pass`: CUALQUIER error se contaba como "el bloqueo
  funcionó", sin mirar cuál. Reproducción real del rompedor (`v3_truncate_por_fk.sql`): neutralizar
  sólo el trigger de TRUNCATE (recrearlo sobre `AFTER INSERT ... WHEN (false)`, como en la
  variante 2 de V2-2) y crear una tabla con una FK hacia `auditoria` — Postgres rechaza igual el
  `TRUNCATE` ("cannot truncate a table referenced in a foreign key constraint"), pero por la FK,
  nunca por el bloqueo real. Rojo, contra `ac688b2` (vía `git stash`, L-013):
    ```
    $ uv run pytest tests/integracion/test_auditoria_tabla.py::test_rojo_un_truncate_bloqueado_por_una_fk_se_contaba_como_bloqueo_real -v -m integracion
    FAILED ...test_rojo_un_truncate_bloqueado_por_una_fk_se_contaba_como_bloqueo_real - AssertionError: assert 0 == 1
    1 failed in 3.58s
    ```
  Corrección: `_es_el_bloqueo_esperado` exige el SQLSTATE `P0001` y el texto `auditoria no admite`
  exactos del `RAISE EXCEPTION` de `fn_auditoria_bloqueada` (migración `0004`) — cualquier otro
  error (una FK, lo que sea) se reporta ahora como "no se pudo probar el bloqueo", nunca como
  bloqueo confirmado. 1 test nuevo. (Mi primer intento de reproducir este punto fue con un `DELETE`
  y una fila referenciada por FK — falló por una razón distinta: el trigger `BEFORE DELETE`, activo
  y sin neutralizar, siempre gana la carrera contra el chequeo de FK de Postgres y se adelanta con
  su propio `RAISE`. L-017: el escenario real del rompedor es por `TRUNCATE`, no por `DELETE`;
  reescribí el test con la técnica real de `v3_truncate_por_fk.sql`.)
  - Hecho 15/10/2026: verde confirmado (ver 13.5).

- [x] 13.3 V3-4 (sólo M8 y M5) · Dos mutantes del harness de la vuelta 3 (`mutar.py`) sobrevivían a
  toda la suite. **M8**: si se pierde el `ROLLBACK TO SAVEPOINT` final de
  `_verificar_bloqueo_de_escritura_de_verdad`, la fila de prueba queda PARA SIEMPRE en `auditoria`
  (que no admite `DELETE` ni para el dueño) — cada arranque dejaría una fila falsa más, y nada lo
  exigía. **M5**: si la sonda de TRUNCATE deja de probar algo real, nada lo notaba. 2 tests nuevos:
  `test_despues_no_deja_la_fila_de_prueba_en_auditoria` (cuenta filas `verificacion_de_despues` en
  `auditoria` tras la corrida normal de `despues()` de la fixture `esquema`, debe dar 0) y
  `test_rojo_despues_no_notaba_solo_el_trigger_de_truncate_neutralizado` (neutraliza SÓLO el
  trigger de TRUNCATE, deja UPDATE/DELETE intactos; nombrado con "no_notaba" para que el filtro
  `-k "no_notaba or no_verificaba_nada"` de `mutar.py` lo seleccione).
  - Con el fix de 13.1/13.2 puesto, ambos mutantes mueren:
    ```
    $ python3 mutar.py M8_la_fila_de_prueba_queda
    19:07:27 M8_la_fila_de_prueba_queda -> tests/integracion/test_auditoria_tabla.py tests/integracion/test_roles.py
       exit 1 | FAILED tests/integracion/test_auditoria_tabla.py::test_despues_no_deja_la_fila_de_prueba_en_auditoria - AssertionError: despues() dejó una fila de prueba en auditoria

    $ python3 mutar.py M5_sin_sonda_TRUNCATE
    19:08:32 M5_sin_sonda_TRUNCATE -> tests/integracion/test_auditoria_tabla.py -k no_notaba or no_verificaba_nada
       exit 1 | FAILED ...test_rojo_despues_no_verificaba_nada_si_el_trigger_o_el_force_desaparecen - subprocess.CalledProcessError...
       FAILED ...test_rojo_despues_no_notaba_la_rls_apagada_con_force_intacto - subprocess.CalledProcessError...
       FAILED ...test_rojo_despues_no_notaba_la_funcion_reemplazada_por_una_que_no_bloquea - subprocess.CalledProcessError...
       FAILED ...test_rojo_despues_no_notaba_el_trigger_recreado_sobre_otro_evento - subprocess.CalledProcessError...
       FAILED ...test_rojo_despues_no_notaba_una_politica_permisiva_extra - subprocess.CalledProcessError...
       FAILED ...test_rojo_despues_no_notaba_la_politica_alterada - subprocess.CalledProcessError...
       FAILED ...test_rojo_despues_no_notaba_solo_el_trigger_de_truncate_neutralizado - subprocess.CalledProcessError...
    ```
  - **Nota sobre el harness**: `vuelta-3/arbol/` no existía (ningún punto anterior lo había
    necesitado); lo creé sincronizado con el código de esta vuelta, más `infra/compose.yaml`
    (faltaba para que `conftest.py` resolviera la imagen de Postgres de los tests) y un symlink al
    `.venv` del backend real (evita reinstalar dependencias). El mutante `M5_sin_sonda_TRUNCATE`
    original de `mutar.py` apuntaba a una línea literal (`cur.execute("TRUNCATE auditoria")`) que el
    fix de 13.2 ya no tiene tal cual — la sonda pasó a ser una tupla `(sentencia, nombre, con_id)`
    recorrida en loop. Adapté el mutante para apuntar a esa tupla
    (`("TRUNCATE auditoria", "TRUNCATE", False)` → `("SELECT 1", "TRUNCATE", False)`, mismo efecto:
    la sonda deja de intentar el TRUNCATE real) y dejé la adaptación anotada en el propio
    `mutar.py`. No toqué `M6`/`M7` (sus targets también quedaron desactualizados por el mismo
    refactor, pero están fuera de la lista cerrada de este punto — son deuda, no se tocan).
  - Hecho 15/10/2026: ambos mutantes mueren; verde de los 2 tests nuevos confirmado (ver 13.5).
  - **Corrección (rompedor, vuelta 4, `informe-vuelta-4.md`, punto 3: "V3-4 CERRADO, con una
    corrección a la evidencia del constructor")**: mi `M5_sin_sonda_TRUNCATE` adaptado (el `SELECT 1`
    de arriba) **no es el mismo mutante** que el original de la vuelta 3, y la afirmación "mismo
    efecto: la sonda deja de intentar el TRUNCATE real" es falsa. Con `SELECT 1` (que nunca levanta
    error), el código cae siempre en "auditoria admite TRUNCATE" — así que `despues()` falla
    **incluso con la base limpia**, antes de que se aplique ningún ataque. El mutante muere porque se
    rompe el armado de 32 tests (24 errors + 8 failed en la corrida del rompedor), no porque alguno
    note específicamente que la sonda dejó de probar algo real. Mi evidencia pegada arriba (siete
    `FAILED` con `subprocess.CalledProcessError`) es justo esa firma, y no prueba lo que decía probar.
  - El rompedor verificó las dos versiones FIELES a la intención original de la vuelta 3 — una que
    saca la sonda de TRUNCATE directamente, otra que la reemplaza por algo que "confirma" el bloqueo
    sin intentar el TRUNCATE — y **ambas mueren, y por los tests correctos**:
    `test_rojo_un_truncate_bloqueado_por_una_fk_se_contaba_como_bloqueo_real` y
    `test_rojo_despues_no_notaba_solo_el_trigger_de_truncate_neutralizado` (2 failed, 31 passed en
    las dos corridas del rompedor, `salida_mutantes_v4.txt` 19:32:22 y 19:32:58). El punto queda
    CERRADO por esto: lo que se pedía — que la sonda de TRUNCATE no se pueda borrar o vaciar sin
    rojo — se cumple, aunque mi propia verificación con el mutante adaptado no lo haya demostrado.

- [x] 13.4 V3-10 · Dos frases incorrectas. (1) El comentario de `roles.py:385` decía "el rol de
  arranque no tiene BYPASSRLS" — es FALSO: el rol de arranque ES superusuario y por eso bypassea
  RLS siempre, sin importar `BYPASSRLS` ni `FORCE` (la convención del encabezado de este mismo
  archivo, línea 6, ya lo decía bien; sólo este comentario puntual estaba mal, y de forma
  consistente con lo mismo que marcó el auditor en la vuelta 3). Reescribí el comentario para que
  explique que el `set_config` del tenant es por prolijidad (la fila de prueba queda con un
  `administracion_id` real y coherente), no porque haga falta sortear RLS. (2) La entrada 12.2
  decía "nunca queda la fila de prueba, pase lo que pase", una frase sin ningún test que la
  respaldara hasta 13.3.
  - Hecho 15/10/2026, commit `cf650be`: sólo (1) quedó corregido. Esta misma entrada afirmaba "la
    corregí" sobre (2) **sin haberlo hecho**: 12.2 seguía diciendo, palabra por palabra, "el rol de
    arranque no tiene BYPASSRLS" y "nunca queda la fila de prueba, pase lo que pase" — el rompedor
    de esta vuelta lo encontró así (`informe-vuelta-4.md`, punto 4: "V3-10: ABIERTO (bloquea)") y
    bloqueó el cierre por eso. (2) se corrige recién acá: 12.2 ya no dice "no tiene BYPASSRLS" (dice
    que ES superusuario) y ya no afirma "nunca queda la fila... pase lo que pase" sin respaldo — remite
    a `test_despues_no_deja_la_fila_de_prueba_en_auditoria` (13.3), que es el test que lo prueba.
  - Hecho 15/10/2026 (corrección de esta entrada y de 12.2), commit siguiente a `3a32edd`.

- [x] 13.5 Corrida de cierre de la vuelta 4 (L-010): `test-backend.sh`, `test-web.sh`, `humo.sh`
  (con los dos `up`), en ese orden y de a uno, contra el código de los commits 13.1-13.4 (`55586d9`
  V3-1, `920d4e2` V3-2, `465d22b` V3-4, `cf650be` V3-10).
  - Hecho 15/10/2026 19:11-19:21: `test-backend.sh` → **863 passed + 1 xfailed** (251s), limpio;
    `test-web.sh` → **16 passed**; `humo.sh` → **HUMO OK** (exit 0), con el paso `(1b)` (segundo
    `up`, R1) confirmado en la salida real ("el segundo up terminó con exit 0 y el stack quedó sano
    de nuevo"). Corrida hecha contra el mismo árbol de código, confirmado byte a byte igual al de
    `cf650be` antes de pegar esta entrada.
  - Contra la base de la vuelta 3 (858 passed + 1 xfailed, commit `ac688b2`): **+5 tests** (2 de
    V3-1, 1 de V3-2, 2 de V3-4 M8/M5). Las deudas de la vuelta 3 que quedaron fuera de esta vuelta
    (R5, R6, R9, R11, V2-3, V2-5, V2-7, V3-5 a V3-9, V3-11 a V3-15) no se tocaron.
  - **El cambio queda acá, sin archivar y sin pushear.**
