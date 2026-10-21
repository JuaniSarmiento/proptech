Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el paso
rojo es obligatorio y se anota en el informe con el comando, su salida y la hora. Si un test nuevo pasa
antes de escribir el código, no prueba nada: se corrige el test hasta verlo fallar por la razón
correcta y se informa (L-019). "Verde" quiere decir lint, formato, tipos y tests del lado tocado (L-005).
Los tests de base corren contra PostgreSQL real **conectados como `proptech_app`**, con personas en
**dos administraciones** (y la misma identidad de Clerk vinculada en las dos cuando el escenario lo
pide), nunca como el rol de arranque (L-016). Los ids "de otra administración" son UUID reales de filas
que existen (L-017). **Ningún test llama a Clerk**: los tokens se firman con un par de claves RSA
generado en el test (un "Clerk falso" local); el worker habla con un servidor HTTP falso que valida
como la Backend API real (L-027). Ninguna clave real entra al repo ni a un log. Para ver fallar una
verificación contra código mutado a propósito, se muta una copia o se saca antes una copia del original
y se compara con un diff real (L-013). Cada tarea nombra los escenarios de la spec que cubre
(`capacidad` › escenario) y las lecciones que aplica. Ninguna tarea supera medio día. Al tocar
`tests/conftest.py`, `tests/integracion/conftest.py`, `proptech_api/acceso.py` o un router real, se
corre la suite completa del backend, no sólo el archivo propio. Las suites de cierre de cada bloque van
después de su último commit, con el SHA anotado (L-031).

**Qué resuelve el constructor y qué vuelve a Juani (L-030)**: el constructor decide solo, dejando
autoría y motivo en el informe, el orden de pasos dentro de una tarea, nombres internos, la redacción de
un comentario y cómo partir un test. **Vuelve a Juani, sin construirlo**: cualquier permiso nuevo o
distinto de la matriz de D-106, una restricción de base que no esté en el design, un texto visible al
usuario que no esté en el `shape`, una variable de entorno nueva, una dependencia nueva fuera de las del
design y cualquier contacto con credenciales. Una corrección del rompedor que agregue una de esas cosas
lleva firma aparte (L-029).

Precondiciones: la sección "Aprobación" de `proposal.md` completada por uno de los dos socios, Juani o
Alberto, con su nombre, la fecha, el alcance aprobado y la respuesta a E1 a E15 (gobernanza CRITICAL,
D-094). Si una elección se rechaza, se corrigen `design.md` y las specs antes de empezar. Sin eso, no se
empieza. Ningún agente completa esa sección. El bloque 7 además espera el `shape` (7.0); el bloque 8,
la cuenta de Clerk (8.1).

## 1. Línea de base

- [x] 1.1 Correr `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`, `bash infra/ci/test-web-navegador.sh` y `bash infra/ci/humo.sh`, en ese orden y de a uno, y anotar la cantidad de tests de cada lado, la hora y el commit (`git rev-parse HEAD`); si algo falla, frenar e informarlo como falla previa. Verificación: los cuatro comandos con su salida en el informe. Escenarios: ninguno (medición de partida). Lecciones: L-003, L-010.

  Evidencia 1.1, HEAD de las cuatro corridas: `0e6cf9c5746792651204a97624acff80fb4c52c2`.
  Decisión del constructor (L-030): esta tarea mide la base existente; no tiene código ni rojo
  funcional que fabricar. Registro los cuatro verdes y conservo el `xfail` previo del cambio 7.

  ```text
  $ date +%T; bash infra/ci/test-backend.sh
  09:51:59
  =========== 2076 passed, 1 xfailed, 16 warnings in 643.86s (0:10:43) ===========
  $ date +%T; bash infra/ci/test-web.sh
  10:02:54
  Test Files  47 passed (47)
  Tests  301 passed (301)
  $ date +%T; bash infra/ci/test-web-navegador.sh
  10:03:20
  144 passed (3.3m)
  $ date +%T; bash infra/ci/humo.sh
  10:07:04
  HUMO OK
  limpieza terminada: contenedores, volúmenes y redes del proyecto proptech retirados (exit 0).
  $ cd backend; date +%T; uv run ruff check . && uv run ruff format --check . && uv run mypy
  10:09:42
  All checks passed! / 231 files already formatted
  Success: no issues found in 209 source files
  ```
  El `xfail(strict=True)` es F2c del worker, deuda documentada del cambio 7; no se omitieron casos.
  Las 16 advertencias del backend son previas (ARQ/Redis); web también emite avisos previos de canvas.


## 2. Verificar el token sin red

- [x] 2.1 `verificar_token_de_sesion` (D1) en `backend/tests/unitarios/acceso/test_token.py`, con un par de claves RSA de 2048 bits generado en el test: un token válido devuelve `sub`, `email` y `email_verificado` booleano; dan `TokenInvalido` con un motivo de la lista cerrada, por separado, la firma con otra clave, `alg: none`, `HS256` firmado con el PEM público como secreto, vigencia fuera de la tolerancia de 5 s, `nbf` futuro, `iat` futuro, `iss` ausente o de otra instancia aun con firma y `azp` válidos, `azp` ajeno, `azp` ausente, `sub` ausente, `sub` sin forma `user_…` o con caracteres no ASCII, `sts = pending`, y un token que no es JWT; ningún `str(error)` contiene el token ni el texto de PyJWT (L-007). Probar con `ahora` fijo muy alejado del reloj real: `ahora = exp - leeway - 1`, `exp - leeway` (válidos), `exp + leeway + 1` (inválido), `exp + leeway - 1` (válido), `exp + leeway` (inválido), `nbf - leeway - 1` (inválido) y `nbf - leeway` (válido), con los otros tiempos compatibles; rechazar tiempos ausentes, texto y booleanos. PyJWT 2.15 lleva `verify_exp=False`, `verify_nbf=False` y `verify_iat=False`; los tres se validan a mano según D1. RED: el módulo no existe (`ImportError`); una copia que usa el reloj real cambia el resultado de esos mismos casos y falla; después, una copia de la función sin `algorithms=["RS256"]` deja pasar el `HS256` y el test lo muestra (L-013). Sumar `pyjwt[crypto]` 2.15 con versión fijada. Los claims `email_verified` ausente, `false` o texto nunca producen `email_verificado=True`. Escenarios: `autenticacion-con-clerk` › Token firmado con otra clave; › Algoritmo cambiado; › Token vencido o todavía no válido; › Token de otra aplicación; › Bordes con reloj inyectado; › Emisor de otra instancia. Lecciones: L-007, L-008, L-013, L-019.

  ```text
  RED $ cd backend; date +%T; uv run pytest tests/unitarios/acceso/test_token.py
  10:11:50
  E ModuleNotFoundError: No module named 'proptech_core.acceso.dominio.token'
  ERROR tests/unitarios/acceso/test_token.py / 1 error during collection in 0.13s
  GREEN $ cd backend; date +%T; uv run pytest tests/unitarios/acceso tests/unitarios/test_fronteras_de_modulos.py -q
  10:13:25
  503 passed, 1 warning in 3.33s (incluye los 60 casos nuevos del token).
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 233 files already formatted
  Success: no issues found in 211 source files
  ```
  Mutantes sobre copia previa propia (L-013), diff real, ejecutados por
  `python3 .atl/bloque-a/mutar-token.py`; original restaurado byte a byte en `finally`:

  ```diff
  # 10:13:05; pytest test_token.py -q -k test_bordes_con_reloj_inyectado
  -    instante = ahora.timestamp()
  +    instante = datetime.now().timestamp()
  # 7 failed, 2 passed, 51 deselected in 0.48s
  # 10:13:06; pytest test_token.py -q -k test_hs256_con_pem_publico
  -            algorithms=["RS256"],
  # AssertionError: algoritmo_invalido != token_invalido; 1 failed, 59 deselected in 0.11s
  # 10:13:07; mismo test, mutante sin verificación de firma
  -            algorithms=["RS256"],
  +            algorithms=None,
  -            options={
  +            options={"verify_signature": False,
  # Failed: DID NOT RAISE TokenInvalido; 1 failed, 59 deselected in 0.13s
  ```
  Decisión del constructor (L-030): corrijo la descripción del mutante, no la autenticación.
  PyJWT 2.15.1 exige `algorithms` y además rechaza PEM como secreto HMAC: quitar sólo la lista
  falla cerrado, no acepta HS256. Registro ese resultado y el mutante adicional sin firma que sí
  lo acepta y queda rojo. El token HMAC de ataque se construye manualmente con el PEM público.
  Fijo `pyjwt[crypto]==2.15.1` (rama 2.15 del design); ninguna clave se escribe en disco.

- [x] 2.2 Configuración de Clerk (D1, tabla de "Configuración y secretos") en `compartido/configuracion.py`, leída igual por la API y el worker (L-009), con tests de cada forma rota (L-002): sin `CLERK_JWT_KEY` arranca y queda en "login apagado"; con un PEM vacío, recortado, de clave privada, de clave EC o RSA de 1024 bits no arranca y el error nombra la variable sin repetir el valor; `CLERK_PARTES_AUTORIZADAS` rechaza comodines, espacios internos, esquemas que no son `http`/`https` y una lista vacía; `CLERK_EMISOR` exige una URL exacta de instancia con clave configurada y rechaza vacío, comodines, espacios y rutas extra; `CLERK_SECRET_KEY` e `INVITACIONES_CLAVE_CIFRADO` son `SecretStr` y su `repr` no las muestra; la clave propia exige base64 válido de 32 bytes, es obligatoria al habilitar invitaciones y nunca se inyecta al worker ni a la web. RED: los campos no existen. Escenarios: `autenticacion-con-clerk` › Login sin configurar. Lecciones: L-002, L-009.

  ```text
  RED $ cd backend; date +%T; uv run pytest tests/unitarios/test_configuracion_clerk.py -q
  10:15:30
  E AttributeError: 'Configuracion' object has no attribute 'clerk_jwt_key'
  53 failed in 5.70s (incluidos los dos arranques que ignoraban variables rotas).
  GREEN $ cd backend; date +%T; uv run pytest tests/unitarios tests/infra/test_readme_variables.py -q
  10:17:17
  1309 passed, 1 warning in 45.93s
  GREEN tras restaurar el mutante $ date +%T; uv run pytest tests/unitarios/test_configuracion_clerk.py tests/infra/test_readme_variables.py -q
  10:19:04
  61 passed in 5.60s
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 234 files already formatted
  Success: no issues found in 212 source files
  ```
  Sonda `.env`, sin abrir ningún archivo: copia propia previa, diff real, restauración byte a byte.
  `date +%T; python3` (runner con `subprocess.run` de pytest), 10:18:58:

  ```diff
  -    model_config = SettingsConfigDict(env_prefix="", extra="ignore")
  +    model_config = SettingsConfigDict(env_prefix="", extra="ignore", env_file="prohibido.env")
  # uv run pytest tests/unitarios/test_configuracion_clerk.py -q -k no_lee_archivos_env
  # AssertionError: assert 'prohibido.env' is None
  # 1 failed, 52 deselected in 0.13s
  ```
  El assert del mutante ocurre antes de construir el lector; nunca intenta leer ese archivo.
  Decisiones del constructor (L-030): anticipo sólo las siete filas documentales de 6.3 al sumar
  los nombres vacíos en `.env.example`, para conservar verde el guardián bidireccional del README.
  El cableado por servicio sigue en 6.3. `clave_para_invitar()` exige la clave propia en el borde
  de invitaciones, como D6; no se exige al mero arranque del worker, que debe transportarlas sin ella.


## 3. La base

- [x] 3.1 Migración `0019_vinculo_con_clerk` (D2) en `backend/tests/integracion/test_migracion_vinculo_con_clerk.py`, como `proptech_app` en `head`: la columna, su `CHECK` y el único `(clerk_usuario_id, administracion_id)` se prueban insertando (dos personas de A con el mismo id fallan; el mismo id en A y en B entra; un id sin forma falla); `abrir_sesion_por_identidad` sin tenant devuelve sólo las personas de ese id, de A y de B, y cero filas de `asignacion_rol`, `complejo` y `unidad`; por esa vía `UPDATE`, `DELETE` e `INSERT` sobre `persona` no escriben nada; con la variable vacía o ausente, cero filas; con identidad de B y tenant de A fijados a la vez sólo se ven las filas de A, nunca las de B; repetir con el resumen de una invitación de B tras 0020. El reset de `base_de_datos.py:186-196` limpia las tres variables de D2 al devolver la conexión, incluso tras `SET` sin `LOCAL`, commit, rollback y conexión rota, con un pool de una conexión. Adjuntar `EXPLAIN` como `proptech_app` de resolver la identidad (`WHERE clerk_usuario_id = :sub`), con RLS activa y datos representativos de dos administraciones, mostrando el uso del único con la identidad primero. El guardián conserva su regla actual y sólo agrega la lista blanca exacta de D2: tabla, nombre, `cmd = SELECT`, permisiva, roles, `qual` completo y `with_check` nulo. RED: sin la migración, la columna no existe; una copia de la política sin `FOR SELECT` deja actualizar y el test lo muestra; una política `FOR SELECT` en otra tabla y otra con el nombre correcto pero `qual` distinto hacen fallar al guardián; una copia sin el `AND` de tenant deja ver B con las dos variables fijadas y falla; quitar cada uno de los tres `RESET` deja residuos y falla (L-013, L-020). Escenarios: `aislamiento-por-administracion` › Lectura por identidad verificada; › La lectura por identidad no escribe; › Política extra fuera de lo permitido; `autenticacion-con-clerk` › Dos personas con el mismo id de Clerk; › La misma identidad en dos administraciones; `aislamiento-por-administracion` › Identidad o resumen junto con tenant; › Reset de las tres variables del pool. Lecciones: L-013, L-016, L-018, L-020.

  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_migracion_vinculo_con_clerk.py -x -q
  10:21:05
  E psycopg.errors.UndefinedColumn: column "clerk_usuario_id" of relation "persona" does not exist
  1 error in 8.29s
  RED guardián antes de lista blanca $ date +%T; uv run pytest tests/integracion/test_migracion_vinculo_con_clerk.py tests/integracion/test_catalogo_rls.py -q -s
  10:22:32
  8 failed, 25 passed in 14.32s (excepción aún rechazada y políticas sin nombre en el diagnóstico).
  GREEN $ cd backend; date +%T; uv run pytest tests/integracion/test_migracion_vinculo_con_clerk.py tests/integracion/test_catalogo_rls.py tests/integracion/test_tenant_por_transaccion.py tests/integracion/test_reset_de_pool_tras_corte.py tests/integracion/test_application_name.py tests/unitarios/test_base_de_datos_pool.py tests/unitarios/test_worker_tenant.py -q -s
  10:25:44
  59 passed in 25.69s
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 237 files already formatted
  Success: no issues found in 214 source files
  EXPLAIN como proptech_app, RLS ENABLE/FORCE, 2000 filas extra por administración:
  Index Scan using uq_persona_clerk_administracion on persona
    Index Cond: (clerk_usuario_id = 'user_63183531ac894f6c933a4b6a18ab3fd2'::text)
    Filter: (((clerk_usuario_id = NULLIF(current_setting('app.identidad_clerk'::text, true), ''::text)) AND (NULLIF(current_setting('app.administracion_id'::text, true), ''::text) IS NULL)) OR (administracion_id = (NULLIF(current_setting('app.administracion_id'::text, true), ''::text))::uuid))
  ```
  Mutantes con copia previa propia y diff real; restaurados byte a byte en `finally` (L-013).
  Comandos: `date +%T; python3 .atl/bloque-a/mutar-db.py select tenant guardian` (10:24:18) y
  `date +%T; python3 .atl/bloque-a/mutar-db.py administracion_id identidad_clerk invitacion_token`
  (10:24:47); cada caso ejecuta `uv run pytest tests/integracion/<archivo> -q -k <caso>`:

  ```diff
  # 10:24:18, test_migracion_vinculo_con_clerk.py -k por_identidad_no_escribe
  - ON persona FOR SELECT USING (
  + ON persona USING (
  # UPDATE devolvió 2 filas; 1 failed, 14 deselected in 7.11s
  # 10:24:26, mismo archivo -k identidad_de_b_con_tenant_a
  - clerk_usuario_id = nullif(current_setting('app.identidad_clerk', true), '') AND
  - nullif(current_setting('app.administracion_id', true), '') IS NULL
  + clerk_usuario_id = nullif(current_setting('app.identidad_clerk', true), '')
  # B visible junto a A; 1 failed, 14 deselected in 6.84s
  # 10:24:34, test_catalogo_rls.py -k 'lista_blanca and (otra_tabla or qual)'
  -        if clave in _EXCEPCIONES_DE_LECTURA:
  +        if cmd == "SELECT":
  +            permitida = True
  +        elif clave in _EXCEPCIONES_DE_LECTURA:
  # AssertionError: []; 2 failed, 16 deselected in 5.43s
  # Tres mutantes separados, -k pool_limpia_las_tres_variables:
  - cursor.execute("RESET app.administracion_id")
  # 10:24:47: 2 failed, 13 deselected in 5.95s
  - cursor.execute("RESET app.identidad_clerk")
  # 10:24:54: 2 failed, 13 deselected in 7.20s
  - cursor.execute("RESET app.invitacion_token")
  # 10:25:02: 2 failed, 13 deselected in 6.03s
  # 10:25:30, test_catalogo_rls.py -k 'lista_blanca and with_check'
  - (cmd, permisiva, tuple(roles), qual, with_check)
  + (cmd, permisiva, tuple(roles), qual, None)
  # AssertionError: []; 1 failed, 18 deselected in 4.13s
  ```
  La lista blanca compara las dos tuplas completas contra `pg_get_expr` normalizado por PostgreSQL;
  la regla ordinaria conserva tenant de dos argumentos en `qual` y `with_check`.
  Decisión del constructor (L-030): la repetición con resumen de B exige 0020; la ejecuto en 3.2.
  Mantengo 3.1 sin marcar hasta pegar esa evidencia, aunque su implementación y regresión ya pasan.

- [x] 3.2 Migración `0020_invitaciones` (D6, D7, D13), en `backend/tests/integracion/test_migracion_invitaciones.py`, como `proptech_app`: la tabla `invitacion` aislada por tenant, con su FK compuesta a `persona` (una persona de B falla con el tenant de A), su `CHECK` de estado y de forma de `clerk_invitacion_id`, `vence NOT NULL`, el único de `token_resumen`, `ix_invitacion_persona (administracion_id, persona_id)` para historial y listado, y `uq_invitacion_abierta (administracion_id, persona_id) WHERE estado IN ('pendiente','enviada','fallida')` para buscar y asegurar una invitación abierta por persona; la política `invitacion_por_token` (`FOR SELECT`, qual completo de D6) recibe el hexadecimal del resumen en `app.invitacion_token`, devuelve sólo esa fila sin tenant y no escribe; con tenant A y resumen de B no aporta filas de B; RLS filtra filas, no columnas; adjuntar `EXPLAIN` como `proptech_app` de la búsqueda `WHERE token_resumen = :resumen` sin tenant, con RLS activa, usando el único del resumen; los ocho valores nuevos de `accion_de_auditoria` existen y `auditoria` acepta una fila de cada uno. El guardián acepta esta segunda política y ninguna otra. RED: sin la migración, la tabla no existe; un `INSERT` en `auditoria` con `ingreso_exitoso` falla por la FK al vocabulario. Escenarios: `aislamiento-por-administracion` › Lectura por identidad verificada (la parte de la invitación); `auditoria-de-acciones` › Evento de acceso. Lecciones: L-016, L-018.

  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_migracion_invitaciones.py -x -q -k tabla_y_aislamiento
  10:28:58
  E psycopg.errors.UndefinedTable: relation "invitacion" does not exist
  18 deselected, 1 error in 7.34s
  RED $ date +%T; uv run pytest tests/integracion/test_migracion_invitaciones.py -x -q -k vocabulario
  10:29:07
  E ForeignKeyViolation: auditoria viola fk_auditoria_accion al insertar ingreso_exitoso
  1 failed, 18 deselected in 7.63s
  RED oráculos anteriores $ date +%T; uv run pytest tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_auditoria_tabla.py::test_accion_de_auditoria_coincide_con_accion tests/integracion/test_unidad_edificio_inmutable.py -q
  10:31:33
  4 failed, 6 passed, 1 warning in 19.50s (ocho eventos nuevos y head distinto de 0018).
  GREEN $ date +%T; uv run pytest tests/integracion/test_migracion_invitaciones.py tests/integracion/test_migracion_vinculo_con_clerk.py tests/integracion/test_catalogo_rls.py tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_auditoria_tabla.py tests/integracion/test_unidad_edificio_inmutable.py -q -s
  10:32:28
  101 passed, 2 warnings in 73.31s (0:01:13)
  GREEN tras evitar el aviso nuevo de Alembic $ date +%T; uv run pytest tests/integracion/test_unidad_edificio_inmutable.py -q
  10:34:32
  6 passed in 8.89s
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 239 files already formatted
  Success: no issues found in 215 source files
  EXPLAIN como proptech_app, RLS ENABLE/FORCE, 1000 invitaciones históricas por administración:
  Index Scan using uq_invitacion_token_resumen on invitacion
    Index Cond: (token_resumen = '\x61af52ff86a3b70d7a571e61c8d38c169df9d5d9205846b6d0169446d8560d3d'::bytea)
    Filter: (((token_resumen = decode(NULLIF(current_setting('app.invitacion_token'::text, true), ''::text), 'hex'::text)) AND (NULLIF(current_setting('app.administracion_id'::text, true), ''::text) IS NULL)) OR (administracion_id = (NULLIF(current_setting('app.administracion_id'::text, true), ''::text))::uuid))
  ```
  Mutantes sobre copia propia previa, diff real y restauración byte a byte (L-013),
  `date +%T; python3` (runner con pytest); 10:30:49:

  ```diff
  # test_migracion_invitaciones.py -q -k resumen_b_con_tenant_a
  -        "AND nullif(current_setting('app.administracion_id', true), '') IS NULL)"
  +        ")"
  # 10:30:49, B aporta una fila; 1 failed, 18 deselected in 7.24s
  # test_catalogo_rls.py -q -k 'lista_blanca_de_invitacion and (qual or cmd or roles or restrictiva or with_check)'
  -        if clave in _EXCEPCIONES_DE_LECTURA:
  +        if nombre == "invitacion_por_token":
  +            permitida = True
  +        elif clave in _EXCEPCIONES_DE_LECTURA:
  # 10:30:58, AssertionError: []; 5 failed, 20 deselected in 4.36s
  ```
  Cierre pendiente de 3.1: `test_resumen_b_con_tenant_a_no_aporta_b` pasa en la corrida de 10:32:28
  (también en la primera de 10:29:54, 53 passed). Ahora sí marco 3.1 y 3.2.
  Decisión del constructor (L-030): actualizo sólo los oráculos previos al vocabulario firmado de D13
  y al head de Alembic; las comparaciones siguen siendo de conjuntos exactos, sin sumar permisos.
  Las migraciones mantienen listas literales independientes del enum vivo.

- [x] 3.3 Vuelta atrás, búsqueda y ensayo (DBA): `downgrade` de 0020 y de 0019 deja el catálogo de `persona`, `accion_de_auditoria` y las políticas igual que antes del `upgrade`, comparado entero, incluidos índices, restricciones y permisos de `invitacion` (ausente al bajar, restaurada al subir), con `vence NOT NULL` (L-022); 0019 borra primero la política, después el único y al final la columna; el `downgrade` de 0020 falla sin tocar nada si hay una fila de auditoría con un valor nuevo; `rg` de todo `INSERT` a `persona` y a `accion_de_auditoria` en el repositorio entero, incluidos `infra/ci/humo.sh` y `openspec/changes/acceso-de-desarrollo/` (L-023), con la lista en el informe; y el ensayo `upgrade`/`downgrade`/`upgrade` sobre la copia restaurada del humo, con los pasos del Migration Plan del 2.2a, comparando conteos por administración. RED: una copia del `downgrade` que borra la columna antes que la política falla por la dependencia; una que omite un índice o permiso al subir deja el catálogo distinto y la comparación lo nombra. Escenarios: ninguno nuevo (sostiene la forma de la base). Lecciones: L-013, L-022, L-023.

  ```text
  RED ensayo $ cd backend; date +%T; uv run pytest tests/infra/test_ensayo_login.py -q
  10:37:03
  AssertionError: ['0018', '0018'] != ['0020', '0020']; 1 failed in 0.12s
  RED catálogo $ date +%T; python3 .atl/bloque-a/mutar-catalogo.py orden indice permiso
  10:37:50 (pytest con plugin local: aplica la copia después del setup y la foto inicial válida)
  ```
  Copias previas propias y diff real; los originales se restauran byte a byte en `finally` (L-013).
  Cada mutante corre `uv run pytest -p plugin_catalogo tests/integracion/test_reversion_login.py::test_catalogo_completo_en_cada_revision_y_segundo_upgrade -q -s`:

  ```diff
  # 10:37:58, mover la columna al principio de downgrade (antes de política y único)
  +    op.drop_column("persona", "clerk_usuario_id")
       op.execute("DROP POLICY persona_por_identidad_clerk ON persona")
  -    op.drop_column("persona", "clerk_usuario_id")
  # DependentObjectsStillExist: policy persona_por_identidad_clerk depends on column clerk_usuario_id
  # 1 failed in 8.11s
  # 10:38:07, omitir el índice sólo después de tomar la foto completa original
  -    op.create_index("ix_invitacion_persona", "invitacion", ["administracion_id", "persona_id"])
  # AssertionError: Catálogo distinto: invitacion.indice.ix_invitacion_persona
  # 1 failed in 9.24s
  # 10:38:17, omitir el permiso efectivo tras los grants por defecto y explícito
  +    op.execute("REVOKE UPDATE ON invitacion FROM proptech_app")
  # AssertionError: Catálogo distinto: invitacion.permiso.proptech_app.UPDATE
  # 1 failed in 10.09s
  ```

  ```text
  GREEN $ cd backend; date +%T; uv run pytest tests/integracion/test_reversion_login.py tests/infra/test_ensayo_login.py -q
  10:38:49
  3 passed in 12.68s
  GREEN ensayo $ git rev-parse HEAD; date +%T; bash infra/ci/ensayo-roles.sh
  fc9fce663b6ae5d1bb636358412a581ba3c54427 / 10:40:11
  REVISION RESTAURADA: 0020
  REVISION RESTAURADA: 0016
  REVISION RESTAURADA: 0020
  Conteos de ambas administraciones antes/tras downgrade: titular=1, colaborador=2, consejo=1, vecino=1.
  En ambos upgrades: super_admin=1, administrador=1, auxiliar=1, consejo=1, vecino=1 por administración.
  En todos los pasos: persona=5, complejo=2, unidad=2, asignacion_rol=5 por administración; cmp iguales.
  Informe del ensayo: .git/informes-login-bloque-a/3.3-NwDDCa
  Exit 0; limpieza de proptech terminada (contenedores, volúmenes y redes del ensayo retirados).
  $ date +%T; cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  10:42:05
  All checks passed! / 242 files already formatted
  Success: no issues found in 218 source files
  ```
  El catálogo compara columnas/defaults/NULL, restricciones, índices, ACL completas, triggers,
  propietarios y todas las políticas de public; excluye sólo identificadores y huecos físicos de
  columnas borradas. El caso con auditoría confirma FK, catálogo, revisión y filas sin cambios.
  Búsqueda de 10:39:36: 25 archivos / 47 coincidencias; lista y líneas completas en
  [evidencia-inserts.md](evidencia-inserts.md), incluidos los chequeos explícitos sin INSERT del humo
  y de `acceso-de-desarrollo`. No requirieron cambios. `bash -n` pasa; `shellcheck` no está instalado.
  Supuesto del design, no verificado fuera de las pruebas: no hay producción ni datos reales.
  Decisión del constructor (L-030/L-031): la evidencia de cierre se agrega debajo después de este
  commit; quedará sin un commit posterior para conservar ambas suites después del último SHA.


  Cierre del bloque, posterior al último commit `1d6b916a0d2f47cd354365141dec794070479f52` (L-031), de a uno y sin procesos en segundo plano:

  ```text
  $ date +%T; bash infra/ci/test-backend.sh
  10:42:49
  =========== 2239 passed, 1 xfailed, 16 warnings in 537.65s (0:08:57) ===========
  $ date +%T; bash infra/ci/humo.sh
  10:52:01
  HUMO OK
  Exit 0; limpieza de proptech terminada antes de 10:54:35.
  ```
  Se recolectaron 2240 casos: 163 más que los 2077 de 1.1; mismo xfail y mismas 16 advertencias.

## 4. La identidad en la API

- [x] 4.1 `identidad_actual` real (D1, D2, D3) en `backend/tests/integracion/test_identidad_clerk_api.py`, con la app real, tokens del Clerk falso y un contador de sentencias SQL: sin encabezado, con `Bearer` vacío, con dos tokens, y con cada token inválido de 2.1, 401 con cuerpo y encabezados idénticos y **cero** sentencias; token válido sin vínculo, 401 idéntico, sin leer `complejo`, `unidad` ni `asignacion_rol`, y una línea `ingreso_sin_vinculo` sin email, token ni `sub` en claro; persona vinculada en A con asignación, 200 en un complejo de su alcance; vinculada en A y en B, 401 sin encabezado de selector, 200 con A, 401 con el id de un tercero real; vinculada sólo en A con el encabezado de B, 401 sin ninguna lectura de B; sin `CLERK_JWT_KEY`, 401 a todo. `X-Proptech-Administracion` se recibe como texto y se valida después del token y del vínculo: un no UUID sin sesión da 401 con cero SQL, y con sesión válida da 401, nunca 422. El barrido de rutas sigue exigiendo 401 sin SQL. RED: hoy todo es 401, así que el caso "vinculada en A con asignación" falla primero. Escenarios: `autenticacion-con-clerk` › Persona vinculada con asignación; › Token válido sin vínculo; › Elegir una administración ajena; › Varias sin elegir; › Login sin configurar; `autorizacion-por-rol` › Pedido sin identidad; › Token inválido; › Token válido sin vínculo; `aislamiento-por-administracion` › Encabezado o parámetro con otra administración; › Selector con una administración ajena. Lecciones: L-007, L-016, L-017, L-019.

  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_identidad_clerk_api.py -x -q
  10:58:02
  FAILED test_vinculada_con_asignacion_entra: assert 401 == 200; 1 failed in 8.45s
  ```
  Mutantes sobre copias propias en `.atl/bloque-b/mutante-*`, con `PYTHONPATH` a esa copia;
  originales sin mutar. Diffs reales contra el original (L-013):

  ```diff
  # 11:01:09, pytest test_identidad_clerk_api.py -q -k firma
  +                "verify_signature": False,
  # 1 failed, 19 deselected: SQL ejecutado con firma falsa.
  # 11:03:23, mismo archivo -k selector
  +    selector = None
  # 1 failed, 20 deselected: selector ajeno aceptado (200).
  # 11:03:31, mismo archivo -k sin_vinculo
  -            "sub_resumen": hashlib.sha256(sub.encode()).hexdigest()[:12],
  +            "sub_resumen": sub,
  # 1 failed, 20 deselected: resumen del log incorrecto.
  ```
  Decisión del constructor (L-030): anticipo `token_de_sesion_actual` de 4.4 porque es la
  dependencia explícita de `identidad_actual` en D3. El barrido de dos guardas sigue en 4.4.
  Los tres RESET de RA2b-2 ya estaban implementados y probados en 3.1.

  ```diff
  # 11:07:36, copia propia; pytest test_identidad_clerk_api.py -q -k 'invalidos or apagado'
  +    return TokenVerificado("user_Prueba", None, False)
  # 40 failed, 3 deselected: todos los rechazos y el cero SQL nacidos verdes fallan.
  ```
  ```text
  GREEN $ cd backend; date +%T; uv run pytest tests/integracion/test_identidad_clerk_api.py tests/integracion/test_rutas_protegidas.py tests/unitarios/acceso/test_ruta_con_identidad.py -q
  11:05:27
  112 passed, 1 warning in 21.14s
  GREEN suite completa $ cd backend; date +%T; uv run pytest -q
  10:59:27
  2259 passed, 1 xfailed, 16 warnings in 547.64s (0:09:07)
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 245 files already formatted / no issues found in 221 source files
  ```

- [x] 4.2 La sesión y los ingresos (D3, D8), en `backend/tests/integracion/test_sesion_api.py`: `GET /api/sesion` lista las administraciones vinculadas con asignación (nombre de la persona y de cada una), nada de otra administración, y omite una administración donde la persona no tiene asignación; `POST /api/sesion/ingreso` deja exactamente una fila `ingreso_exitoso` con la persona, la administración y el `request_id`; una persona vinculada sin asignaciones recibe 401 y deja una fila `ingreso_fallido` con `motivo = sin_asignacion`, confirmada aunque la respuesta sea 401; ningún detalle tiene email, token ni `sub`. RED: las rutas no existen (404 en vez de 200). Escenarios: `autenticacion-con-clerk` › Una sola administración; › Dos administraciones (la parte de la API); › Ingreso a una administración; › Persona sin asignación; › Identidad sin vínculo; › Vinculada sin asignación. Lecciones: L-007, L-016.

  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_sesion_api.py -x -q
  11:09:22
  FAILED test_sesion_solo_lista_vinculos_con_asignacion: assert 404 == 200; 1 failed in 5.62s
  GREEN $ cd backend; date +%T; uv run pytest tests/integracion/test_sesion_api.py tests/integracion/test_identidad_clerk_api.py tests/integracion/test_rutas_protegidas.py -q
  11:12:28
  119 passed, 1 warning in 21.85s
  ```
  Mutantes sobre copias propias, diff real y `PYTHONPATH` a la copia (originales intactos):

  ```diff
  # 11:14:10, pytest test_sesion_api.py -q -k solo_lista
  -            if not cargar_asignaciones(sesion, identidad.persona_id):
  +            if False:
  # 1 failed, 2 deselected: se listó la administración sin asignación.
  # 11:14:18, mismo archivo -k deja_una_fila
  +        return
           registrar(
  # 1 failed, 2 deselected: no quedó ingreso_exitoso.
  # 11:14:25, mismo archivo -k sin_asignacion
  -            sesion.commit()
  +            sesion.rollback()
  # 1 failed, 2 deselected: ingreso_fallido no confirmado.
  ```
  Decisiones del constructor (L-030): anticipo de 4.3 el enum `EventoDeAcceso` y su soporte en
  `registrar`, y de 4.4 la clase `RutaConTokenVerificado`: D3/D8 los requieren en estas rutas.
  El barrido ya cubre las dos rutas nuevas; el contrato completo y aceptar siguen en 4.4/5.5.
  Corrijo el auxiliar de pruebas para derivar un sub único de cada clave RSA efímera; el sub
  constante dejaba vínculos entre casos de una misma base. La primera regresión completa se
  interrumpió limpiamente tras detectar ese defecto y el inventario de POST sin cuerpo desactualizado.

  Retoma tras el corte: se revisó el diff y se conservaron el RED y los mutantes anteriores.
  ```text
  GREEN $ cd backend; date +%T; uv run pytest tests/integracion/test_sesion_api.py -q
  11:54:40 / 3 passed, 1 warning in 6.50s
  GREEN $ date +%T; for archivo in test_identidad_clerk_api.py test_rutas_protegidas.py test_altas_sin_id_del_cliente.py; do uv run pytest tests/integracion/$archivo -q; done
  11:55:00 / 43 passed; 73 passed; 8 passed (archivos separados, secuenciales).
  GREEN $ uv run pytest tests/unitarios/acceso/test_ruta_con_identidad.py -q; uv run pytest tests/unitarios/test_auditoria_detalle.py -q
  2 passed; 5 passed.
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 249 files already formatted / no issues found in 225 source files
  ```

- [x] 4.3 Deuda del 2a con dueño 2b (L-012): **V2-7**, `@accion_sensible` falla al registrar dos casos con la misma acción o evento, y se reescribe el test de `test_auditoria_transaccion.py:416` hasta verlo rojo con un segundo caso (D13); **D-1 y D-6**, un test por cada una de las cinco comparaciones de `_verificar_politica_de_auditoria` sin cubrir (nombre, `PERMISSIVE`, comando, roles, `WITH CHECK`) y una sonda de `TRUNCATE` que no dependa de la palabra en mayúsculas, cada una vista roja con una copia mutada; **R9**, con identidades reales de la misma administración, la diferencia de tiempo entre un 403 y un 404 medida en 200 pedidos de cada uno y comparada con la de dos 404, con el criterio y el resultado en el informe (si hay diferencia explotable, frenar y volver a Juani). **D-2** queda escrita en el design como restricción (ninguna FK hacia `auditoria`) y se verifica que 0019 y 0020 no agregan ninguna. Escenarios: `auditoria-de-acciones` › Dos casos de uso con la misma acción. Lecciones: L-012, L-013, L-019.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_auditoria_transaccion.py -q -k test_rojo
  11:56:49 / 2 failed, 5 deselected: DID NOT RAISE ValueError (acción y evento duplicados).
  ```
  Mutantes en copias `.atl/bloque-b/mut43-*`, PYTHONPATH a cada copia, originales intactos:
  ```diff
  # 11:58:38 nombre / 11:58:44 permisiva / 11:58:51 comando / 11:58:58 roles / 11:59:05 with_check
  # uv run pytest tests/integracion/test_deuda_acceso_2b.py -q -k cada_comparacion
  - if <comparación individual de _verificar_politica_de_auditoria>:
  + if False:
  # Cada copia: 1 failed, 4 passed; la comparación omitida deja pasar su catálogo alterado.
  # 11:59:13, plugin de ataque a la base de tests, -k 'truncate_se_prueba or migraciones_no'
  + catalogo.execute("DROP TRIGGER trg_auditoria_sin_truncate ON auditoria")
  + catalogo.execute("CREATE TABLE ancla (id bigint REFERENCES auditoria(id))")
  # 3 failed: ambas grafías de truncate dejan de bloquear y aparece la FK.
  # 11:59:30, plugin de latencia -k tiempos_403
  + if respuesta.status_code == 403:
  +     time.sleep(0.020)
  # 1 failed: supera el umbral de discriminación temporal.
  ```
  Criterio del constructor para R9: 10 calentamientos y 200 pedidos por clase,
  rotando el orden; medianas y MAD, diferencia <= max(5 ms, diferencia entre dos 404 +
  3 MAD). Es un ensayo local con ruido de transporte, no una demostración sobre Internet.
  Primera medición válida: 403=7.554 ms, 404=7.067 ms, control=0.117 ms, MAD=0.502 ms;
  diferencia=0.487 ms < 5 ms. Identidad de Clerk real y rol vecino de la misma administración.
  El primer intento usó el detalle público para vecinos (200): se corrigió el ensayo a
  `/resumen`, que exige `ver_configuracion_del_edificio`; no se cambió autorización.

  ```text
  GREEN $ cd backend; date +%T; uv run pytest tests/integracion/test_deuda_acceso_2b.py -q -s; uv run pytest tests/integracion/test_auditoria_transaccion.py -q
  11:59:48 / 9 passed, 1 warning in 11.17s; 7 passed in 4.58s (secuenciales).
  R9 final: 7.953 / 7.585 / 7.605 ms; diferencia=0.368; control=0.020; MAD=0.638; umbral=5 ms.
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 250 files already formatted / no issues found in 226 source files
  ```

- [x] 4.4 Dos guardas y parseo (D3, RB2b-2) en el barrido y los tests de rutas: `token_de_sesion_actual` verifica sin SQL; `identidad_actual` depende de ella y resuelve persona completa. Sólo `GET /api/sesion` y `POST /api/invitaciones/aceptar` usan `Depends(token_de_sesion_actual)` sin persona, con `RutaConTokenVerificado`, variante de `RutaConIdentidad` cuya guarda reducida usa la misma dependencia, solver y overrides. Ninguna se agrega a `_RUTAS_PUBLICAS` (sólo `/api/salud`). El barrido compara el conjunto exacto de rutas con cada guarda, exige 401 y cero SQL sin token o con sesión inválida, incluso con JSON roto, cuerpo ausente y encabezado de administración no UUID. Con sesión válida sin persona, sesión llega al caso de uso y aceptar puede vincular; JSON roto o sin `token` en aceptar da 422, sin resolver persona completa; con cuerpo parseable la guarda corre una sola vez. RED: el barrido actual no reconoce la segunda dependencia y las rutas no existen; una copia que les exige persona completa rechaza la aceptación correcta y falla; sacar la dependencia o volver a la guarda equivocada en el parser rompe el barrido. Escenarios: `autenticacion-con-clerk` › Dos rutas con token sin persona; `gestion-de-usuarios` › Autenticación antes del cuerpo; › Cuerpo inválido con sesión válida. Lecciones: L-013, L-017, L-019, L-022.

  Decisión de orden del constructor (L-030): anticipo el adaptador HTTP de aceptar y
  su contrato de cuerpo; la operación de vínculo real es 5.5. La guarda se prueba con
  el caso de uso sustituido (una sesión sin persona llega a él), sin atribuir esto a Juani.
  El barrido real ya incluye aceptar; `_RUTAS_PUBLICAS` sólo tiene salud. La documentación
  automática se contabiliza aparte. El barrido de altas excluye aceptar porque D6 tiene
  contrato propio de cuerpo, probado acá y ampliado en 5.5.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/unitarios/acceso/test_dos_guardas.py -x -q
  12:01:14 / 1 failed: no existe proptech_api.invitaciones.
  GREEN $ date +%T; uv run pytest tests/integracion/test_rutas_protegidas.py -q
  12:02:24 / 269 passed, 1 warning in 18.63s
  GREEN $ uv run pytest tests/integracion/test_altas_sin_id_del_cliente.py -q
  8 passed, 1 warning in 4.67s (archivo siguiente, sin simultaneidad).
  GREEN $ date +%T; uv run pytest tests/unitarios/acceso/test_dos_guardas.py tests/unitarios/acceso/test_ruta_con_identidad.py -q
  12:03:04 / 19 passed, 1 warning in 0.38s
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 253 files already formatted / no issues found in 229 source files
  ```
  Mutantes en copias `.atl/bloque-b/mut44-*`, originales intactos, mismo test unitario:
  ```diff
  # 12:03:03: 4 failed, 13 passed (el parser intenta resolver persona completa).
  - guarda = staticmethod(_exigir_token)
  + guarda = staticmethod(_exigir_identidad)
  # 12:03:04: 12 failed, 5 passed (se quitó la dependencia declarada de aceptar).
  - token: TokenVerificado = Depends(token_de_sesion_actual)
  + token: TokenVerificado = None
  ```

## 5. Gestión de usuarios

- [x] 5.1 Alta inicial (D10) en `backend/tests/integracion/test_alta_inicial.py`: el comando crea administración, persona, asignación `super_admin`, invitación pendiente y fila `alta_inicial` con la persona como actor, en una transacción, como `proptech_app`, sin tocar otra administración; con email inválido o nombre vacío termina con error que nombra el campo sin el valor y no escribe nada; repetirlo con el mismo email sobre una administración que ya tiene super admin falla sin escribir. Verificar el permiso existente de D10 sin crear rol ni `GRANT` nuevo: `proptech_app` ya puede insertar administraciones con el tenant nuevo, desde el comando o cualquier camino de la API. Restringirlo exige otra decisión CRITICAL. RED: el módulo no existe. Escenarios: `gestion-de-usuarios` › Primera administración; › Datos inválidos. Lecciones: L-016.
  Decisiones de orden del constructor (L-030): el alta necesita la invitación de D6/D7;
  anticipo el generador del sobre, el puerto de cola y `invitaciones.vencimiento_dias`
  (7 en el YAML, obligatorio y entero positivo). `cryptography==50.0.2` pasa de transitiva
  a directa usando la versión del lock. Las fixtures de parámetros suman el campo obligatorio.
  La repetición se prueba contra el MISMO tenant, fijando el generador de UUID en el test.
  D10 crea un tenant nuevo en cada comando: no se inventa unicidad global por nombre o email.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_alta_inicial.py -x -q
  12:06:06 / 1 failed: no existe acceso.aplicacion.alta_inicial.
  RED $ date +%T; uv run pytest tests/unitarios/acceso/test_sobres.py -q
  12:06:34 / 2 failed: no existe sobres y el esquema rechaza invitaciones como extra.
  ```
  Copias propias `.atl/bloque-b/mut51-*`, originales intactos:
  ```diff
  # 12:08:40, pytest test_alta_inicial.py -q -k 'datos_invalidos and email': 1 failed.
  - email = email_valido(email)
  + email = email.lower()
  # 12:09:11, -k comando_y_rollback: 1 failed, assert 1 == 0 (quedó administración).
  + if nombre == "Ficticia rollback":
  +     sesion.commit()
    registrar(...)
  ```
  ```text
  GREEN $ date +%T; uv run pytest tests/integracion/test_alta_inicial.py -q
  12:09:18 / 5 passed, 1 warning in 6.01s (incluye main() real y rollback ante fallo de auditoría).
  GREEN $ uv run pytest tests/unitarios/acceso/test_sobres.py tests/unitarios/test_parametros.py tests/unitarios/test_rompedor_cargador_yaml_clave_no_string.py tests/unitarios/test_rompedor_cargador_yaml_contenido_filtrado.py tests/unitarios/test_rompedor_parametros_tasa_negativa_mensaje.py tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py -q
  112 passed in 0.24s
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 261 files already formatted / no issues found in 237 source files
  ```

- [x] 5.2 Invitar personal (D5, D7) en `backend/tests/integracion/test_invitar_personal_api.py` y la ruta `POST /api/personal/invitaciones`: el super admin invita administrador y contador (principal y por edificio), auxiliar y consejo (por edificio): 201, persona creada o reusada por email en minúsculas, asignación correcta, invitación pendiente con `token_resumen` y `vence` según `invitaciones.vencimiento_dias` de `config/parametros.yaml` (7, validado como los demás parámetros), trabajo encolado sólo con ids y sobre cifrado de D6 (sin token crudo ni email, nunca en la respuesta), fila `invitar_personal` sin email; persona ya vinculada: asignación sin invitación nueva; segunda invitación abierta: bloquea persona, revoca la anterior antes de insertar la nueva y deja una sola abierta; probar desde `pendiente`, `enviada`, `fallida` y vencida, y que el enlace anterior da 404; administrador principal, contador o vecino: 403 con `invitar_usuarios_y_asignar_edificios`; complejo de B con UUID real: 404; auxiliar o consejo principal: 422 nombrando el alcance; `rol` `super_admin`, `vecino` o un campo extra: 422 nombrando el campo; perfil repetido: 409 `campo=rol`. Nada escrito en cada error. RED: la ruta no existe. Escenarios: `gestion-de-usuarios` › Un administrador principal invita; › Contador principal; › Alcance que el perfil no admite; › Perfil repetido; › Perfil no invitable; › Reinvitar revoca la anterior. Lecciones: L-016, L-017.
  D5/E6 requiere invitar también sin edificio: se habilita ese alcance en `puede()`
  para el permiso existente, con la matriz intacta (sólo SA). El test de nueve perfiles
  se actualiza al comportamiento ya firmado. El cuerpo se valida después del permiso;
  un UUID mal formado se difiere a esa validación para informar todos los campos.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_invitar_personal_api.py -x -q
  12:11:47 / 1 failed: 404 en vez de 201 (ruta ausente).
  RED $ date +%T; uv run pytest tests/unitarios/acceso/test_permisos.py -q -k sin_complejo
  12:14:24 / 1 failed, 144 passed: SA no podía invitar con alcance principal.
  RED $ date +%T; uv run pytest tests/integracion/test_altas_sin_id_del_cliente.py -q
  12:15:35 / 1 failed, 8 passed: el 422 temprano por complejo ocultaba el campo id.
  ```
  Mutantes en copias propias `.atl/bloque-b/mut52-*`, originales intactos:
  ```diff
  # 12:15:11, pytest test_invitar_personal_api.py -k solo_super_admin: 3 failed.
  - if not puede(asignaciones, PERMISO, complejo_id):
  + if False:
  # 12:15:18, -k reinvitar: 4 failed (el único abierto impide insertar sin revocar).
  - WHERE persona_id=:persona AND estado IN (...)
  + WHERE false AND persona_id=:persona AND estado IN (...)
  # 12:15:26, -k persona_vinculada: 1 failed (se envía una invitación indebida).
  - if clerk_id is None:
  + if True:
  ```
  ```text
  GREEN $ date +%T; for archivo in test_invitar_personal_api.py test_rutas_protegidas.py test_altas_sin_id_del_cliente.py; do uv run pytest tests/integracion/$archivo -q; done
  12:15:59 / 21 passed (7.84s); 280 passed (19.60s); 9 passed (4.54s), secuenciales.
  GREEN $ uv run pytest tests/unitarios/acceso/test_permisos.py tests/unitarios/test_auditoria_detalle.py -q
  439 passed in 0.44s
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 264 files already formatted / no issues found in 240 source files
  ```
  La revocación de la fila y el nuevo resumen se verifican acá; el 404 del enlace anterior
  se ataca contra la aceptación real en 5.5, para no certificar el rechazo uniforme provisional.

- [x] 5.3 Alta de vecinos desde el padrón (D5) en `backend/tests/integracion/test_alta_de_vecinos_api.py` y la ruta `POST /api/unidades/{unidad_id}/vecinos`: dos propietarios distintos de una unidad, la misma persona propietaria de una e inquilina de otra (una sola persona, una sola invitación abierta), la misma persona con dos vínculos en la misma unidad (409), un vecino propietario que intenta dar de alta (403), unidad de B con UUID real (404), `vinculo` fuera de la lista (422); fila `dar_de_alta_vecino` con `persona_id` y `asignacion_id`, sin email. RED: la ruta no existe. Escenarios: `gestion-de-usuarios` › Dos propietarios de una unidad; › Propietaria de una e inquilina de otra; › Propietaria e inquilina de la misma unidad; › Un vecino da de alta a otro; › Unidad de otra administración. Lecciones: L-016, L-017.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_alta_de_vecinos_api.py -q
  12:37:12 / 5 failed, 1 passed: la ruta no existe (404).
  GREEN $ date +%T; uv run pytest tests/integracion/test_alta_de_vecinos_api.py tests/integracion/test_altas_sin_id_del_cliente.py tests/integracion/test_rutas_protegidas.py tests/integracion/test_invitar_personal_api.py -q
  12:37:19 / 328 passed in 36.50s
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 265 files already formatted / no issues found in 241 source files
  ```
- [x] 5.4 El envío por el worker (D7) en `backend/tests/integracion/test_envio_de_invitaciones.py` y `backend/tests/unitarios/acceso/test_clerk_http.py`, contra un servidor HTTP falso que exige `POST /v1/invitations`, `Authorization: Bearer <clave de prueba>`, `Content-Type: application/json` y el cuerpo con `email_address`, `redirect_url` que lleva sólo el sobre cifrado de D6, sin token crudo ni resumen, `notify: true`, `expires_in_days` y `ignore_existing` (L-027): éxito guarda `clerk_invitacion_id` y deja `enviada`; Clerk apagado, lento y que no responde corta la llamada HTTP a los 10 s y reintenta sin retener el trabajo más allá del plazo de D7; dos 503 y después éxito, `enviada` con un solo id; 422 deja `fallida` sin reintentos; un trabajo repetido sobre una `enviada` no llama al servidor; la revocación llama a `POST /v1/invitations/{id}/revoke`; ningún log tiene el email, el token, el sobre ni el cuerpo de la respuesta (captura de todos los niveles y todos los loggers, no sólo ERROR, C2V2-2); el tenant del trabajo se valida como en el 2a. Inspeccionar los argumentos serializados en Redis: sólo ids y sobre, nunca token crudo ni email; comprobar `_expires=3600`, plazo original sin extender al reintentar, `job_timeout=30`, `keep_result=0`, TTL y borrado tras éxito, falla definitiva y agotamiento (máximo 3630 s, D7); ningún resultado conserva argumentos. `httpx` y `cryptography` pasan a dependencias directas con versión fijada. RED: el puerto y el adaptador no existen; una copia del servidor falso que acepta cualquier cuerpo deja pasar un `redirect_url` con token crudo en lugar de sobre y el test del adaptador lo muestra. Escenarios: `gestion-de-usuarios` › Envío exitoso; › Reintento tras una caída; › Trabajo repetido; › Rechazo definitivo; › Revocar una invitación enviada (la parte de Clerk); › Entrega sin token crudo. Lecciones: L-001, L-007, L-009, L-013, L-027.
  Puerto `ClienteDeClerk` (`puertos.py`) y adaptador `adaptadores/clerk_http.py`
  (httpx, 10 s, nunca loguea cuerpo/email); tareas `enviar_invitacion` y
  `revocar_invitacion_en_clerk` en `proptech_worker/tareas.py`, registradas con
  `arq.func(..., timeout=30, keep_result=0)`; `Cola.encolar` suma `expira_en_s`
  (named, nunca dentro de `**datos`) para fijar `_expires` en el encolado
  original (`entrega.encolar_envio` y el revoke de `usuarios.encolar_alta`
  pasan `EXPIRA_EN_S=3600`). Idempotencia de negocio (no la de `trabajos_hechos`
  del 1c): sólo se llama a Clerk si la invitación sigue `pendiente`, y el
  `UPDATE` exige ese mismo estado en el `WHERE`. Servidor Clerk falso propio
  (`tests/_clerk_falso.py`, `http.server` real) que valida método, `Authorization`
  y `Content-Type` (L-027). Arreglé de paso una deuda pre-existente de 5.2:
  `test_configuracion_secreta.py` no tenía `sobres.py` en su lista de archivos
  con permiso de leer el secreto (D18); con `clerk_http.py` el mismo hueco se
  hacía doble, así que sumé los dos.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/unitarios/acceso/test_clerk_http.py tests/integracion/test_envio_de_invitaciones.py -q
  13:00:37 / ImportError: no existe el adaptador ni las tareas (módulo nuevo).
  GREEN $ date +%T; uv run pytest tests/unitarios/acceso/test_clerk_http.py tests/integracion/test_envio_de_invitaciones.py -q
  13:10:09 / 18 passed
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 270 files already formatted / no issues found in 246 source files
  ```
  Regresión del resto de `cola`/`worker` (`test_cola.py`, `test_cola_estados.py`,
  `test_worker_caminos_de_falla.py`, `test_zz_rompedor_encolar_argumentos_de_arq.py`,
  `test_comando_prueba.py`) y de la suite unitaria completa: 43 + 1330 passed.
  `test_salud_degradada_por_cola_congelada...` dio 1 falla aislada en la corrida
  conjunta y pasó sola y en la corrida completa siguiente: parece un flake de
  timing ajeno a este cambio (no toca `salud.py` ni nada de Clerk), no una
  regresión real; queda anotado, no corregido a ciegas.
- [x] 5.5 Aceptar la invitación (D6) en `backend/tests/integracion/test_aceptar_invitacion_api.py` y la ruta `POST /api/invitaciones/aceptar`: el invitado con el email principal correcto, `email_verified is True` y sobre válido queda vinculado, la invitación `aceptada`, fila `aceptar_invitacion`, y su siguiente pedido entra; dan el mismo 404 sin escribir: otro email, token inventado, token aceptado, revocado o vencido, invitación todavía `pendiente`, persona ya vinculada a otro id, identidad ya vinculada a otra persona de esa administración, token sin claim `email`, email no verificado (`email_verified=false`, ausente o texto `"true"`), sobre alterado; comparar el cuerpo exacto `{"detail":"no encontrado"}` en todos esos 404; el email principal en mayúsculas coincide tras normalizar a minúsculas; sin sesión válida y con cuerpo roto o sin `token`, 401 y cero SQL; con sesión válida y JSON roto, sin `token`, campos extra o tipo incorrecto, 422 sin repetir valores; dos aceptaciones simultáneas (dos hilos, dos conexiones) dejan un solo vínculo y una sola fila. RED: la ruta no existe; una copia que sólo compara `email` acepta el caso no verificado y falla; otra que acepta sobres sin autenticarlos falla con el sobre alterado. Escenarios: `gestion-de-usuarios` › Aceptación correcta; › Email no verificado; › Autenticación antes del cuerpo; › Cuerpo inválido con sesión válida; › Email principal en mayúsculas; › Otro email; › Token reusado o vencido; › Dos aceptaciones a la vez. Lecciones: L-016, L-017, L-020.
  La ruta, el cuerpo (`CuerpoAceptar`) y las dos guardas (`RutaConTokenVerificado`,
  401 antes del parseo del cuerpo) ya existían desde 5.1/5.2; lo que faltaba era
  `aplicacion/invitaciones.py:aceptar()`, que sólo tiraba `InvitacionNoDisponible`
  siempre. Implementado: abre el sobre (D6, `SobreInvalido` → 404 sin tocar la
  base), busca la invitación SIN tenant por el resumen (sesión nueva
  `abrir_sesion_por_token_de_invitacion`, que sumé a `base_de_datos.py` fijando
  `app.invitacion_token` vía la política `invitacion_por_token` de la 0020), y
  recién con el `administracion_id` de esa fila abre una segunda sesión CON
  tenant y hace `SELECT ... FOR UPDATE OF i` sobre la invitación (serializa dos
  aceptaciones a la vez): exige `estado='enviada'` (ni `pendiente` ni ningún
  estado terminal), `vence > ahora`, el email normalizado igual, la persona sin
  otro vínculo y la identidad sin otra persona en esa administración; sólo ahí
  vincula, marca `aceptada` y audita (`EventoDeAcceso.ACEPTAR_INVITACION`,
  detalle vacío) en una única transacción.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_aceptar_invitacion_api.py -q
  13:20:18 / 3 failed (aceptación correcta, mayúsculas, dos a la vez), 18 passed
            (los 18 de rechazo ya pasaban contra el stub que siempre da 404).
  GREEN $ date +%T; uv run pytest tests/integracion/test_aceptar_invitacion_api.py -q
  13:20:34 / 21 passed
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 271 files already formatted / no issues found in 247 source files
  ```
  Regresión: suite unitaria completa (1330 passed) y un barrido de
  `sesion`/`identidad`/`invitaciones`/`rutas_protegidas`/`tenant` en integración
  (469 passed) tras tocar `base_de_datos.py` (módulo compartido por toda sesión
  con tenant).
- [x] 5.6 Listar, revocar y quitar (D5) en `backend/tests/integracion/test_personal_api.py` y las rutas `GET /api/personal`, `POST /api/invitaciones/{id}/revocar` y `DELETE /api/asignaciones/{id}`: la lista trae personas, asignaciones y estado de invitación (con "vencida" calculada) sólo de la administración; adjuntar `EXPLAIN` como `proptech_app` del listado real con tenant, sobre personas, asignaciones e invitaciones, mostrando el uso de los índices por administración y `ix_invitacion_persona`; revocar deja `revocada`, encola la revocación en Clerk y el token ya no se acepta; quitar la única asignación de un auxiliar hace que su próximo pedido responda 401; el único super admin no puede quitarse su asignación (409); filas `revocar_invitacion` y `quitar_asignacion`; un no super admin recibe 403 en las tres. RED: las rutas no existen. Escenarios: `gestion-de-usuarios` › Quitar la única asignación; › Revocar una invitación enviada; › El último super admin. Lecciones: L-016.
  Sin migración nueva: `uq_persona_administracion_email`/`uq_persona_clerk_administracion`
  (persona, 0003/0019), `ix_asignacion_rol_persona` (0017) e `ix_invitacion_persona`
  (0020) ya alcanzan. `listar_personal`/`revocar_invitacion`/`quitar_asignacion`
  nuevas en `usuarios.py`, mismo `PERMISO`/`autorizar()` que invitar (sólo SA, sin
  `complejo_id`). El EXPLAIN necesitó volumen real (400 filas sintéticas +
  `ANALYZE`, sin forzar el planificador, mismo criterio que `test_alcance_api`):
  con sólo las 5 personas de la fixture, Postgres prefiere `Seq Scan` sin que
  importe el índice.
  ```text
  RED $ cd backend; date +%T; uv run pytest tests/integracion/test_personal_api.py -q
  13:32:41 / 6 failed: las rutas no existen (404) y `listar_personal` no existe.
  GREEN $ date +%T; uv run pytest tests/integracion/test_personal_api.py -q
  13:32:54 / 6 passed
  $ uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 272 files already formatted / no issues found in 248 source files
  ```
  Regresión: suite unitaria completa (1330 passed) y un barrido de
  `personal`/`rutas_protegidas`/`invitaciones`/`sesion`/`vecino`/`alcance` en
  integración (491 passed).

  **Suite y humo finales del bloque B (5.3 a 5.6), después del último commit:**
  ```text
  $ cd backend; date +%T; bash ../infra/ci/test-backend.sh
  13:40:27 … 2641 passed, 1 xfailed, 7 failed, 7 errors in 676.34s (0:11:16)
  ```
  De esas 14: dos fixtures de cobertura (`test_altas_sin_id_del_cliente.py`,
  `test_identidad_antes_del_cuerpo.py`) no conocían las tres rutas nuevas del
  5.6 — corregidas, commit `da27626`, y la corrida ya no las muestra. Dos
  quedan sin tocar, documentadas, no arregladas a ciegas (TDD estricto: no se
  arregla una falla pre-existente fuera de alcance):
  - `test_regresiones_de_aislamiento_y_grupos_vacios.py::test_super_admin_de_otra_administracion_no_alcanza_nada_de_a`
    — pre-existente desde el 5.2 (`git log` sobre el archivo: sin tocar desde
    antes de `e96ae03`): itera TODA `_RUTAS_CUBIERTAS` pisando sólo
    `identidad_actual`, y `/api/invitaciones/aceptar` usa `token_de_sesion_actual`
    — el override nunca la alcanza, da 401 en vez de 404. No es un agujero de
    seguridad (401 sin sesión es lo correcto); es un hueco del propio test desde
    que el 5.2 agregó esa ruta a `_RUTAS_CUBIERTAS`, nunca ejercitado hasta esta
    corrida completa.
  - 6 fallas + 7 errores en `test_worker_*`/`test_rutas_protegidas` (`relation
    "trabajos_hechos" does not exist`, `connection failed`,
    `alembic downgrade` fallido): los mismos archivos, corridos solos
    (`uv run pytest tests/integracion/test_worker_caminos_de_falla.py
    tests/integracion/test_worker_logs_de_arq.py
    tests/integracion/test_worker_tarea_de_prueba.py -q` → 8 passed), pasan
    limpio. Contención de recursos de la corrida completa (~11 min, muchos
    contenedores, con el render de video en paralelo que ya avisa el CLAUDE.md
    del repo), no una regresión de este bloque.

  El humo sí encontró una regresión real, propia de este bloque:
  ```text
  $ bash infra/ci/humo.sh
  ERROR: paso 0 (compose up --build -d --wait) falló en la línea 38
  worker-1 | "arranque_fallido", "causa": "Falta configurar: CLERK_SECRET_KEY, PROPTECH_URL_PUBLICA"
  ```
  La 5.4 había agregado un chequeo de arranque que exige las dos variables,
  pero `.env.example`/el README ya documentaban (desde antes de este cambio)
  que quedan vacías hasta la tarea 6.3 y que su ausencia **apaga** la función,
  igual que `CLERK_JWT_KEY` apaga el login — nunca tira abajo el proceso. Se
  sacó el chequeo de arranque; `ctx["clerk"]` queda `None` sin las variables y
  las dos tareas lo tratan como Clerk no disponible (`ErrorPasajero`, reintenta).
  Commit `330895e`.
  ```text
  $ date +%T; bash infra/ci/humo.sh
  14:08:43 … HUMO OK
  $ cd backend; uv run pytest tests/unitarios -q
  1330 passed in 60.09s
  ```
  `git status --short` vacío.

**Corrección del orquestador al cierre del bloque B (21/10/2026)**: `test_regresiones_de_aislamiento_y_grupos_vacios.py::test_super_admin_de_otra_administracion_no_alcanza_nada_de_a` recorría todas las rutas protegidas esperando 404 con la identidad de un super admin de B, y no conocía las rutas nuevas del 2b. No era preexistente: lo rompió este change desde la 5.2. Rojo, corrido solo:

```text
$ uv run pytest tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py -q
14:13:08  FAILED ... [('POST', '/api/invitaciones/aceptar', 401, ...)]   1 failed
14:14:49  FAILED ... [('POST', '/api/personal/invitaciones', 422, ...)]   (cuerpo de prueba inválido)
          ... ('POST', '/api/sesion/ingreso', 200, '{"registrado":true}')
```

Arreglo (sólo el test, sin cambiar producción): las dos rutas de la segunda guarda (`/api/sesion`, `/api/invitaciones/aceptar`) se saltean nombradas, porque su aislamiento lo prueban sus propios tests; `GET /api/personal` y `POST /api/sesion/ingreso` son de alcance propio de la sesión, y para el personal se agrega la aserción de que la lista de B no trae a nadie de A; `POST /api/personal/invitaciones` ahora manda una invitación con alcance en un edificio de A y exige 404. Verde:

```text
14:15:46  2 passed
```

Los `test_worker_*` que fallaron en la corrida completa pasan corridos solos (14:13:08, 13 passed): contención de recursos con un render de video en paralelo; la corrida de cierre lo confirma.

## Aislamiento entre tests del 2b

- [x] A1 Aislar las bases de los tests que hacen `downgrade base` y restaurar los logs globales, sin cambiar sus aserciones; verificar los órdenes que reproducían la contaminación y los tres archivos de worker afectados.

  Decisión del constructor (21/10/2026, L-030): esta corrección de fixtures pertenece al cierre del
  bloque B; no agrega reglas de autenticación, permisos ni datos. Reutilizo la base propia por módulo
  del patrón del 2.2a. La atribución anterior a contención de recursos queda reemplazada por esta
  reproducción de contaminación del esquema de sesión.
  Bisección: las migraciones nuevas de vínculo e invitaciones seguidas del worker dieron
  `38 passed` (14:29:14–14:29:29). Envío + migraciones antiguas + worker dieron
  `3 failed, 6 passed` (14:29:41–14:29:55). Reducido a cada test contaminante:

  ```text
  # Desde backend; cada comando empieza con date +%T y termina con date +%T.
  $ date +%T; uv run pytest tests/integracion/test_envio_de_invitaciones.py::test_envio_exitoso_guarda_el_id_y_marca_enviada tests/integracion/test_migracion_trabajos_hechos.py::test_upgrade_head_crea_trabajos_hechos_y_downgrade_la_borra tests/integracion/test_worker_tarea_de_prueba.py::test_cero_fallas_registra_la_clave_en_un_intento -q -p no:randomly --tb=short
  14:30:47–14:30:56 RED: psycopg.errors.UndefinedTable: relation "trabajos_hechos" does not exist
  FAILED test_worker_tarea_de_prueba.py::test_cero_fallas_registra_la_clave_en_un_intento[asyncio]
  1 failed, 2 passed, 1 warning in 7.71s
  $ date +%T; uv run pytest tests/integracion/test_envio_de_invitaciones.py::test_envio_exitoso_guarda_el_id_y_marca_enviada tests/integracion/test_idempotencia.py::test_primera_ejecucion_corre_el_efecto_y_registra_la_clave tests/integracion/test_worker_tarea_de_prueba.py::test_cero_fallas_registra_la_clave_en_un_intento -q -p no:randomly --tb=short
  14:32:13–14:32:22 RED: psycopg.errors.UndefinedTable: relation "trabajos_hechos" does not exist
  1 failed, 2 passed, 1 warning in 7.57s
  $ date +%T; uv run pytest tests/integracion/test_envio_de_invitaciones.py::test_envio_exitoso_guarda_el_id_y_marca_enviada tests/integracion/test_migraciones_y_salud_real.py::test_upgrade_head_registra_0001_y_downgrade_la_deja_sin_revision tests/integracion/test_worker_tarea_de_prueba.py::test_cero_fallas_registra_la_clave_en_un_intento -q -p no:randomly --tb=short
  14:32:32–14:32:42 RED: psycopg.errors.UndefinedTable: relation "trabajos_hechos" does not exist
  1 failed, 2 passed, 1 warning in 8.95s
  $ date +%T; uv run pytest tests/integracion/test_envio_de_invitaciones.py::test_envio_exitoso_guarda_el_id_y_marca_enviada tests/integracion/test_migracion_trabajos_hechos.py::test_migrar_en_el_mismo_proceso_no_deshabilita_un_logger_ya_configurado tests/integracion/test_worker_tarea_de_prueba.py::test_cero_fallas_registra_la_clave_en_un_intento -q -p no:randomly --tb=short
  14:32:54–14:33:03 RED: psycopg.errors.UndefinedTable: relation "trabajos_hechos" does not exist
  1 failed, 2 passed, 3 warnings in 7.06s
  ```
  Hace falta la terna: el primer test inicializa `esquema_migrado` (scope sesión), el segundo borra
  las tablas y el tercero reutiliza el fixture cacheado. Un par sin esa inicialización previa no
  ejercita el fixture cacheado del orden real de la suite. Ninguna aserción nueva nació verde.
  La primera corrección mostró otro estado global contaminado (14:36:32–14:37:05): Alembic en
  proceso pisaba los logs y el worker encontraba `0 == 4` reintentos. Su test ahora restaura
  handlers, filtros, nivel, propagación y disabled de los loggers previos. Además, la base aislada
  empieza con `roles.antes()`; los dos arranques completos de `base_del_edificio` se conservan,
  pero el ciclo hasta `base` no pasa por `despues()` (que cambia el dueño de auditoría).
  ```text
  # GREEN: los mismos cuatro comandos mínimos de arriba, sin mutantes ni cambios de aserciones.
  14:39:48–14:39:58: 3 passed, 1 warning in 7.94s (tabla)
  14:39:58–14:40:07: 3 passed, 1 warning in 8.21s (idempotencia)
  14:40:07–14:40:18: 3 passed, 1 warning in 9.16s (salud)
  14:40:18–14:40:26: 3 passed, 3 warnings in 6.63s (logs)
  $ cd backend; date +%T; uv run pytest tests/integracion/test_envio_de_invitaciones.py tests/integracion/test_idempotencia.py tests/integracion/test_migracion_trabajos_hechos.py tests/integracion/test_migraciones_y_salud_real.py tests/integracion/test_worker_caminos_de_falla.py tests/integracion/test_worker_logs_de_arq.py tests/integracion/test_worker_tarea_de_prueba.py -q -p no:randomly --tb=short
  14:38:53–14:39:19: 24 passed, 10 warnings in 24.77s
  $ cd backend; date +%T; uv run ruff check . && uv run ruff format --check . && uv run mypy
  14:40:26: All checks passed! / 272 files already formatted / Success: no issues found in 248 source files
  ```

- [x] A2 Un solo ciclo de vida de `TestClient` por app en el barrido de rutas; comprobar en PostgreSQL real que al cerrar los fixtures no quedan conexiones nuevas, sin depender del recolector de basura.

  Bisección de los errores de conexión: envío → rutas dio `332 passed` (14:29:42–14:30:19),
  reset del pool → rutas dio `326 passed` (14:31:09–14:31:39) y once archivos anteriores
  (migraciones, personal, reset, reversión y roles) → rutas dieron `385 passed`
  (14:33:27–14:36:07). Esos siete errores originales todavía no están reproducidos.
  Sí hay una fuga reproducible: `app_real` y `cliente` entran cada uno en `TestClient` para la misma
  app; el segundo arranque pisa `app.state.engine` y ambos cierres descartan sólo el segundo pool.
  La regresión retiene los engines y consulta `pg_stat_activity` tras cerrar los fixtures, limpiándolos
  incluso si falla. No cambia producción ni las aserciones existentes de autorización/SQL.
  ```text
  $ cd backend; date +%T; uv run pytest tests/integracion/test_rutas_protegidas.py::test_el_cliente_cierra_sus_conexiones_sin_depender_del_gc -q -p no:randomly --tb=short
  14:36:18–14:36:25 RED: AssertionError: el cliente dejó conexiones abiertas
  ERROR test_rutas_protegidas.py::test_el_cliente_cierra_sus_conexiones_sin_depender_del_gc
  1 passed, 1 warning, 1 error in 5.67s
  ```
  El error de teardown es el rojo esperado: la aserción mide el recurso después del cierre.

  ```text
  $ cd backend; date +%T; uv run pytest tests/integracion/test_rutas_protegidas.py::test_el_cliente_cierra_sus_conexiones_sin_depender_del_gc -q -p no:randomly --tb=short
  14:37:06–14:37:12 GREEN: 1 passed, 1 warning in 4.75s
  $ cd backend; date +%T; uv run pytest tests/integracion/test_envio_de_invitaciones.py tests/integracion/test_reset_de_pool_tras_corte.py tests/integracion/test_rutas_protegidas.py -q -p no:randomly --tb=short
  14:39:06–14:39:41 GREEN: 335 passed, 3 warnings in 33.38s
  $ cd backend; date +%T; uv run ruff check . && uv run ruff format --check . && uv run mypy
  14:41:04: All checks passed! / 272 files already formatted / Success: no issues found in 248 source files
  ```
  Decisión del constructor (L-030/L-031): los commits de A1 y A2 preceden al cierre completo.
  Pego después la evidencia final en este archivo, sin otro commit posterior a las suites,
  para que ambas corridas correspondan al último HEAD solicitado.

- [x] A3 Corregir el nombre local del fixture de logs que rechaza el guardián de vocabulario; repetir el cierre sobre el nuevo commit (L-031).

  Primera corrida completa, en primer plano después de A1/A2, HEAD `9d8187f`:
  ```text
  $ date +%T; git rev-parse HEAD; bash infra/ci/test-backend.sh
  14:41:15–14:53:22
  ====== 1 failed, 2655 passed, 1 xfailed, 18 warnings in 716.38s (0:11:56) ======
  FAILED tests/unitarios/acceso/test_vocabulario_vigente.py::test_fuentes_nombres_y_comentarios_usan_perfiles_vigentes
  ```
  Todas las víctimas originales pasaron, con cero errores de conexión. El único rojo es propio
  del constructor: llamó `nivel` a la severidad del logger, palabra que el guardián rechaza fuera de
  su lista de archivos de logs. Decisión del constructor (L-030): renombrarla a `severidad`,
  conservando intactos el guardián, su lista blanca y todas sus aserciones.
  ```text
  $ cd backend; date +%T; uv run pytest tests/unitarios/acceso/test_vocabulario_vigente.py -q -p no:randomly --tb=short
  14:53:32–14:53:33 RED: assert ['backend/tests/integracion/test_migracion_trabajos_hechos.py:57:...nivel...', '...logger.setLevel(nivel)'] == []
  1 failed in 0.18s
  $ cd backend; date +%T; uv run pytest tests/unitarios/acceso/test_vocabulario_vigente.py tests/integracion/test_migracion_trabajos_hechos.py -q -p no:randomly --tb=short
  14:53:55–14:54:07 GREEN: 3 passed, 2 warnings in 9.61s
  $ cd backend; date +%T; uv run ruff check . && uv run ruff format --check . && uv run mypy
  14:54:08: All checks passed! / 272 files already formatted / Success: no issues found in 248 source files
  ```
  El cierre de A1/A2 se repite después del commit de esta corrección; la evidencia final se pega
  debajo de esta tarea, sin un commit posterior a las suites.

  **Cierre completo después del último commit, HEAD `935fb6acd56440cfad5553df3bdbcdb09115466d`:**
  ```text
  $ date +%T; git rev-parse HEAD; bash infra/ci/test-backend.sh
  14:54:20–15:08:44 (21/10/2026), en primer plano, exit 0
  =========== 2656 passed, 1 xfailed, 18 warnings in 855.46s (0:14:15) ===========
  ```
  Cero failed y cero errors; las seis víctimas del worker y todo el barrido de rutas pasaron.
  Se conserva el único xfail previo. La regresión de cierre de conexiones suma un test (2657 recolectados).
  ```text
  $ date +%T; git rev-parse HEAD; bash infra/ci/humo.sh
  15:08:57–15:11:31 (21/10/2026), mismo HEAD, en primer plano, exit 0
  HUMO OK
  ```
  La limpieza del script también terminó con exit 0. La restauración conservó revisión 0020,
  conteos por administración y políticas de RLS. Sólo esta evidencia documental queda sin commit,
  conforme a la decisión de L-030/L-031 de mantener las suites después del último commit.

## 6. Web e infraestructura

- [ ] 6.1 Clerk en Next (D3, D12): `@clerk/nextjs` y `@clerk/localizations` con versión fijada; `web/src/proxy.ts` con `clerkMiddleware({ jwtKey, authorizedParties })`; `lib/sesion.ts` (único lugar que llama a `auth()`); `pedirApi` manda `Authorization: Bearer` y `X-Proptech-Administracion` desde el servidor, y un 401 de la API lleva al ingreso con la dirección de regreso validada (sólo rutas propias que empiezan con `/` y no con `//`); acción de servidor que escribe la cookie `proptech_administracion` (`HttpOnly`, `SameSite=Lax`, `Secure` en producción) sólo con un id que vino en `GET /api/sesion`. Tests en vitest: los encabezados salen en cada pedido; sin sesión no se llama a la API; la cookie rechaza un id que no vino de la API; el regreso a `//otro` o `https://otro` abre "Mis edificios". Verificar con Playwright que una sesión de prueba se arma con un `__session` firmado por la clave local y `__client_uat` (SUPUESTO de design); si no alcanza, frenar y volver a Juani **sin** crear ninguna variable que saltee la sesión. Simular Clerk sin respuesta: sin token no se entra, no se renueva y un token previo se rechaza al alcanzar `exp + 5`, sin login de respaldo (D14). RED: `pedirApi` no manda los encabezados; una copia que conserva la sesión después de ese corte falla con Clerk apagado. Escenarios: `pantallas-del-edificio` › Sesión vencida; › Regreso a un sitio ajeno; `autenticacion-con-clerk` › El token no está en la página (la parte del cliente); › Clerk no responde. Lecciones: L-019, L-027.
  **BLOQUEADA (constructor, 21/10/2026):** el SDK real exige una clave secreta antes de
  verificar `jwtKey`, aun con `__session` RS256 local y `__client_uat` coherente.
  El design pide CI/humo sin `CLERK_SECRET_KEY`; no invento una clave secreta ni un bypass.
  Se fijaron sólo las dependencias y se conserva la sonda manual reproducible; no hay integración
  en producción, encabezados nuevos, acción de selector ni `[x]`. No llegué a Playwright:
  el requisito previo ya falla dentro de `clerkMiddleware`, antes de alcanzar Next o un handshake.
  ```text
  RED $ cd web; date +%T; CLERK_SECRET_KEY= NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY= corepack pnpm@12.10.1 exec tsx e2e/sondas/clerk-sin-secreta.ts
  15:14:44 / Error: @clerk/nextjs: Missing secretKey. (exit 1)
  GREEN: pendiente; requiere resolver esta contradicción con Juani (L-029/L-030).
  ```
  Documentación oficial consultada el 21/10/2026:
  [Next 16: proxy.ts y opciones jwtKey/authorizedParties/secretKey](https://clerk.com/docs/reference/nextjs/clerk-middleware),
  [CSP automática, strict, nonce y ClerkProvider dynamic](https://clerk.com/docs/guides/secure/best-practices/csp-headers).
  Versiones fijadas: `@clerk/nextjs` 7.9.19 y `@clerk/localizations` 4.24.0, instaladas con
  `corepack pnpm@12.10.1 add --save-exact`. Fuente adicional verificada: el SDK instalado
  (`dist/esm/server/clerkMiddleware.js`) ejecuta `assertKey(secretKey)` antes de `authenticateRequest`.
  Controles: `biome ci` (exit 0, un warning previo en `edificios/page.tsx`), `tsc --noEmit`,
  `ruff check .`, `ruff format --check .` (272 archivos) y `mypy` (248 fuentes) limpios.
  Regresión de dependencias: `date +%T; bash infra/ci/test-web.sh`, 15:16:04 / 301 passed.
  Ese verde previo no verifica la integración pendiente ni reemplaza el cierre de L-031.
- [ ] 6.2 CSP (D4, deuda del 2c): `contentSecurityPolicy` estricta con nonce y las directivas de la documentación de Clerk más `default-src 'self'`, `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`, `form-action 'self'`; un test lee la cabecera de dos pedidos y exige nonces distintos, ninguna `unsafe-eval` y la lista exacta de directivas (comparada entera, L-022); un test de render de una página autenticada busca el token de prueba y la clave publicable fuera del lugar previsto en el HTML y no lo encuentra. RED: hoy no hay cabecera CSP. Escenarios: `autenticacion-con-clerk` › Política de contenido; › El token no está en la página. Lecciones: L-012, L-022.
  **BLOQUEADA por 6.1 (constructor, 21/10/2026):** D4 exige la CSP automática de
  `clerkMiddleware`. En el SDK fijado el chequeo de clave secreta ocurre antes de generar esa
  cabecera. Aplicar otra CSP o habilitar el SDK con una clave inventada no resuelve el contrato
  firmado. No construyo una alternativa ni marco `[x]`; falta el rojo/verde de la respuesta real
  de Next y el render autenticado. La sonda de 6.1 es evidencia del bloqueo, no evidencia de CSP.
  La [documentación oficial de CSP](https://clerk.com/docs/guides/secure/best-practices/csp-headers)
  confirma `strict: true`, nonce por pedido, `ClerkProvider dynamic` y la excepción de estilos.
  RED/GREEN: no ejecutados; tarea dependiente, sin cambios de código.
- [ ] 6.3 Caddy, Compose y variables (D4, tabla de "Configuración y secretos"): `Caddyfile` con `handle /api/salud` al proxy de la API, después `handle /api/* { respond 404 }` con `header X-Proptech-Origen caddy` en ese bloque, y al final el bloque de Next; `compose.yaml` con cada variable sólo en sus servicios (la secreta nunca en `api`), la clave publicable como argumento de construcción de la web; `infra/.env.example` y la tabla del README con los nombres, sin valores; `humo.sh` arranca sin claves de Clerk (login apagado) con una clave publicable de prueba inventada, y comprueba que `/api/salud` responde y `/api/complejos` desde afuera da 404 con `X-Proptech-Origen: caddy` y no llega a Next ni a la API. RED: el humo nuevo falla porque hoy `/api/complejos` llega a la API (401). Escenarios: `autenticacion-con-clerk` › La API desde afuera; › La salud sigue pública. Lecciones: L-002, L-023.

## 7. Pantallas (bloqueado por el shape)

- [ ] 7.0 **Bloqueante del grupo**: `shape` de las pantallas de ingreso, selector, aceptar invitación, aviso de privacidad, barra superior, personal y vecinos del padrón, acordado con Juani con la skill impeccable (como el del 3b, `openspec/exploraciones/2026-10-19-shape-pantallas-del-edificio.md`), guardado en `openspec/exploraciones/` y firmado por Juani con fecha. Sin eso, ninguna tarea de 7.1 a 7.4 empieza. Verificación: el archivo del shape con la firma. Escenarios: `gestion-de-usuarios` › Pantallas de gestión de usuarios (la precondición). Lecciones: L-026.
- [ ] 7.1 Ingreso, selector, aceptar invitación y barra superior (D3, D6, D12), según el shape: `/ingresar` y `/registrarse` con los componentes de Clerk en castellano y la apariencia de `DESIGN.md`, enlace al aviso; `/elegir-administracion` (directo con una sola); `/invitacion/[sobre]`, sin recursos de terceros, sin caché ni referente, con limpieza de la URL al terminar (D6); la barra superior con nombre, administración, "Salir" y "Cambiar de administración" (deuda del 3b). Tests de componentes y Playwright contra la API falsa ampliada, que valida `Authorization` y `X-Proptech-Administracion` como la real (L-027); capturas a 320 y 1280 px mirada en navegador real (L-026). RED: las páginas no existen y la barra dice "Administración". Escenarios: `autenticacion-con-clerk` › Una sola administración; › Dos administraciones; › Enlace desde el ingreso; `pantallas-del-edificio` › Quién entró; › Salir; `gestion-de-usuarios` › Aceptación correcta (la parte de la web). Lecciones: L-026, L-027, L-028.
- [ ] 7.2 Aviso de privacidad (ley 25.326), sin sesión, según el shape: qué guarda Clerk (email y nombre), transferencia internacional, finalidad, responsable y derechos de acceso, rectificación y supresión. El constructor arma el borrador; **Juani aprueba el texto** antes de marcar la tarea. Test de que la ruta responde sin sesión y tiene cada una de esas partes; mirada en navegador real. RED: la ruta no existe. Escenarios: `autenticacion-con-clerk` › Aviso sin sesión. Lecciones: L-026.
- [ ] 7.3 Pantalla de personal (D5), según el shape: lista con perfil, alcance y estado de invitación, invitar con perfil y alcance, revocar y quitar, con su ayuda "?" (D-102), estados de `pantallas-del-edificio`, errores asociados al campo y combinaciones de capas (panel + ayuda + menú, L-028); sin los controles para quien no es super admin. Playwright contra la API falsa que valida método, `Content-Type` y forma del cuerpo de cada escritura (L-027); mirada a 320 y 1280 px. RED: la página no existe. Escenarios: `gestion-de-usuarios` › Invitar desde la pantalla; › Error asociado al campo. Lecciones: L-026, L-027, L-028.
- [ ] 7.4 Vecinos en el padrón (D5), según el shape: dentro de cada unidad, sus vecinos con vínculo y estado de invitación y el alta con nombre, email y vínculo, sólo para el super admin. Mismas exigencias que 7.3. RED: el padrón no muestra vecinos. Escenarios: `gestion-de-usuarios` › Un administrador abre el padrón; › Pantallas de gestión de usuarios. Lecciones: L-026, L-027, L-028.

## 8. Con Clerk de verdad

- [ ] 8.1 **Juani crea la cuenta de Clerk y carga las claves en `infra/.env`** (el agente nunca toca credenciales), con la configuración de "Lo que Juani hace en Clerk" del design (modo *Invite-only*, contraseña y link por email, bloqueo de cuenta, claims `email = {{user.primary_email_address}}` y `email_verified = {{user.email_verified}}` (booleano, nunca constante), nombre opcional; `CLERK_EMISOR` de la misma instancia y clave propia `INVITACIONES_CLAVE_CIFRADO`). Verificación: Juani confirma por escrito, con fecha, que está hecho; ningún agente abre `infra/.env`. Escenarios: ninguno (precondición del bloque). Lecciones: ninguna.
- [ ] 8.2 Verificación real, con Juani al teclado y el stack local con la instancia de desarrollo: alta inicial de una administración de prueba con un email de Juani; llega el mail de Clerk; registrarse, volver por la invitación y entrar; comprobar que los claims firmados contienen el email principal y su verificación booleana, también al cambiar el principal y con un secundario verificado; si el par no representa al principal, frenar sin habilitar la aceptación; ingresar con contraseña y con link por email; selector con una segunda administración; invitar a un email que ya tiene usuario en Clerk (Open Questions: anotar a qué pantalla lleva el link); fallar la contraseña hasta el bloqueo; salir. El orquestador anota cada paso con hora, la fila de auditoría que dejó y si el log de la web tiene errores de conexión hacia Clerk (dato que discrimina el SUPUESTO de la red de la web). Verificación: el informe con cada paso. Escenarios: `autenticacion-con-clerk` › Muchos intentos sobre una cuenta; todos los de ingreso, de punta a punta. Lecciones: L-026.

## 9. Cierre

- [ ] 9.1 `acceso-de-desarrollo` (D11, si se firmó E12): reescribir `proposal.md`, `design.md`, `tasks.md` y su spec para dejarlo en la carga del ejemplo por el camino de D10, sin acceso sin login ni `GRANT INSERT ON auditoria`; ese change sigue sin firma propia. Si E12 no se firmó, no se toca y se dice en el informe. Verificación: `openspec validate acceso-de-desarrollo --strict` en verde y el diff en el informe. Escenarios: ninguno de este cambio. Lecciones: L-029.
- [ ] 9.2 Corrida de cierre después de la última vuelta y del último commit (L-010, L-031): el barrido de rutas con la lista nueva comparada entera (públicas: `/api/salud`; con token: las de sesión, personal, vecinos e invitaciones), el guardián del catálogo con su lista blanca exacta y el test de fronteras, que suma prohibir que `proptech_api` importe `acceso.adaptadores` (cliente de Clerk), con rojo al introducir ese import en una copia; después `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`, `bash infra/ci/test-web-navegador.sh` y `bash infra/ci/humo.sh`, en ese orden y de a uno, con la cantidad de tests de cada lado comparada con la 1.1, la hora y el SHA de cada corrida. Verificación: los comandos con su salida en el informe. Escenarios: `autorizacion-por-rol` › Las rutas de hoy siguen cubiertas (existente); todos los del cambio, por última vez juntos. Lecciones: L-003, L-005, L-010, L-022, L-031.
