Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el paso
rojo es obligatorio y se anota en el informe con el comando, su salida y la hora. Cada escenario tiene
al menos un caso que **falla hoy**, contra el código del commit de la línea de base; si un test nuevo
pasa antes de escribir el código, no prueba nada: se corrige hasta verlo fallar por la razón correcta
y se informa (L-019). Los escenarios que son guardas de regresión por construcción están nombrados en
`design.md` ("Cómo aplica cada lección") con cómo se ve su rojo. "Verde" quiere decir lint, formato,
tipos y tests del lado tocado (L-005). Los tests de aislamiento y de base corren contra PostgreSQL real
**conectados como `proptech_app`**, nunca como el rol de arranque (L-016); los ids "de otro edificio"
o "de otra administración" son UUID de filas que existen (L-017). Ningún valor rechazado aparece en un
error, una respuesta o un log sin un test con un marcador que pruebe que no se repite (L-007). Montos
y proporciones se construyen siempre desde texto; un `float` en cualquier punto es un rojo. Para ver
fallar una verificación contra código mutado a propósito, se muta una copia o se saca antes una copia
(`git stash` o un commit local que se descarta) y se compara con un diff real (L-013). Cada tarea
nombra los escenarios que cubre (`capacidad` › escenario) y las lecciones que aplica. Ninguna tarea
supera medio día.

Precondiciones, sin las cuales no se empieza:

- La sección "Aprobación" de `proposal.md` completada por Juani o Alberto, con nombre, fecha, alcance y
  la respuesta a E1 a E10 (gobernanza HIGH, D-094). Si una elección se rechaza, se corrige `design.md`
  antes de empezar. Ningún agente completa esa sección.
- Si E1 se firma con la recomendación de mover la 7.2 al 3b, se saca de este archivo antes de empezar.
- P19, P24 y P33 están resueltas (D-100): ninguna tarea está bloqueada por una pregunta abierta.
  PR1 a PR4 (`design.md`, Open Questions) no bloquean; si se responden antes de construir, se ajusta
  la tarea que nombran.

## 1. Línea de base

- [x] 1.1 Correr la suite completa antes de tocar nada (`bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`, `bash infra/ci/humo.sh`, en ese orden y de a uno) y anotar la cantidad de tests de cada lado, la hora y el commit (`git rev-parse HEAD`); anotar también cuántos tests del 2a insertan en `unidad` con la columna `nombre` (los toca 3.1). Si algo falla, frenar e informarlo como falla previa. Escenarios: ninguno (medición de partida). Lecciones: L-003.

  Commit de la línea de base: `379ffa666e4850f44c1aeb4b17c1ecf6abf577b2` (HEAD al arrancar).

  **DESVIACIÓN DE PROCESO, anotada sin tapar**: `bash infra/ci/test-backend.sh` se lanzó en segundo plano a las 08:58:10 y, mientras corría, ya se empezó a leer y editar `test_rutas_protegidas.py` para la tarea 2.1 (primer `pytest -k` propio de 2.1 a las 09:01:40), antes de que la 1.1 terminara (09:04:29). No es la secuencia que pide la convención ("correr todo antes de tocar nada"). Mitigación real, no sólo intención: pytest importa cada módulo de test una sola vez al recolectar (los primeros segundos de la corrida); un edit posterior en disco no cambia el bytecode ya cargado en ESE proceso, y las corridas de 2.1 fueron procesos `pytest` nuevos y separados — por eso el número de abajo no está mezclado con el código de 2.1. Pero no hay captura de log de la fase de recolección que lo pruebe con certeza (no se usó `--collect-only` con marca de hora antes de editar), así que el conteo de 900/1 queda como EVIDENCIA de lo que corrió, con esta ASUNCIÓN declarada sobre por qué no está contaminado.

  **EVIDENCIA** — `bash infra/ci/test-backend.sh` (equivalente a `uv run pytest`, que es lo que ese script invoca):
  ```
  $ cd backend && uv run pytest -q    # lanzado 08:58:10, terminó ~09:04:29 (379.08s)
  900 passed, 1 xfailed, 16 warnings in 379.08s (0:06:19)
  ```

  **EVIDENCIA** — `bash infra/ci/test-web.sh`:
  ```
  $ bash infra/ci/test-web.sh    # 2026-10-19 09:05:54
  Test Files  3 passed (3)
  Tests  16 passed (16)
  Duration  367ms
  ```

  **EVIDENCIA** — `bash infra/ci/humo.sh`:
  ```
  $ bash infra/ci/humo.sh    # 2026-10-19 09:05:59, terminó 09:08:27
  ...
  HUMO OK
  exit=0
  ```

  **Tests del 2a que insertan en `unidad` con la columna `nombre`** (los toca 3.1, que la renombra a `identificador`): 6 inserts `INSERT INTO unidad (..., nombre)` en 5 archivos —
  `tests/integracion/test_alcance_api.py` (1), `tests/integracion/test_asignar_edificio_api.py` (1),
  `tests/integracion/test_rutas_protegidas.py` (1, ya actualizado por 2.1 al archivo compartido pero
  la fila de `INSERT` sigue igual), `tests/integracion/test_rls_acceso_minimo.py` (2),
  `tests/integracion/test_identidad_api.py` (1). Comando: `rg -c "INTO unidad.*nombre" tests/`, 2026-10-19
  09:03. Ningún uso ORM (`Unidad(nombre=...)`) encontrado, sólo SQL crudo.

## 2. Deuda heredada, antes de cualquier ruta nueva

- [x] 2.1 **R6** (bloqueante antes de la primera ruta nueva, D-098) en `tests/integracion/test_rutas_protegidas.py`: el barrido toma la ruta efectiva de toda `APIRoute` de la app (incluida con `include_router(prefix=...)`, agregada con `add_api_route` sobre la app, anidada). **Rojo**, sobre una copia del test (L-013): una app de prueba con un router sin prefijo montado con `include_router(prefix="/api")` y otra con `add_api_route("/api/x")`, cada una con una ruta fuera de `_RUTAS_CUBIERTAS`: el barrido de hoy pasa en verde (es el defecto). Arreglarlo y verlo fallar nombrando cada ruta; sobre la app real, la lista sale idéntica a la de hoy (tres rutas del 2a más `/api/salud` pública). Escenarios: `autorizacion-por-rol` › Ruta montada con prefijo de inclusión; › Ruta agregada directo a la app; › Las rutas de hoy siguen cubiertas. Lecciones: L-013, L-019, L-020.

  **RED** — 2026-10-19 09:01:40 (los dos tests nuevos, agregados ANTES del arreglo, corriendo contra el `_api_routes` viejo — no hizo falta copia aparte, L-013: agregar el test ya alcanza para ver el defecto sin tocar el código de producción):
  ```
  $ uv run pytest tests/integracion/test_rutas_protegidas.py -k "sin_cubrir_se_detecta" -v
  FAILED ...::test_ruta_montada_con_prefijo_de_inclusion_sin_cubrir_se_detecta
    AssertionError: el barrido no vio la ruta montada con include_router(prefix=...): rutas detectadas: set()
  FAILED ...::test_ruta_agregada_directo_a_la_app_sin_cubrir_se_detecta
    AssertionError: el barrido no vio la ruta agregada con add_api_route directo a la app: rutas detectadas: set()
  2 failed, 10 deselected, 1 warning in 0.73s
  ```
  Confirma el defecto exacto de D8: el barrido viejo no fallaba nombrando la ruta nueva (lo que se esperaría de un barrido "ciego pero detectado"); la perdía del todo (`set()`), porque filtraba por `sub.path.startswith("/api")` sobre `original_router.routes`, cuyo `.path` nunca lleva el prefijo de inclusión, y porque ignoraba toda ruta que no viniera envuelta en `_IncludedRouter`.

  **GREEN** — 2026-10-19 09:02:06, arreglo de `_api_routes` (recorre `_IncludedRouter.effective_candidates()`, recursivo, más `APIRoute` directa):
  ```
  $ uv run pytest tests/integracion/test_rutas_protegidas.py -k "sin_cubrir_se_detecta" -v
  PASSED ...::test_ruta_montada_con_prefijo_de_inclusion_sin_cubrir_se_detecta
  PASSED ...::test_ruta_agregada_directo_a_la_app_sin_cubrir_se_detecta
  2 passed, 10 deselected, 1 warning in 0.79s
  ```
  Suite completa del archivo, sin regresión (L-020 — las tres rutas del 2a + `/api/salud` siguen siendo exactamente lo que ve el barrido, escenario "Las rutas de hoy siguen cubiertas"):
  ```
  $ uv run pytest tests/integracion/test_rutas_protegidas.py -q    # 09:02:53
  12 passed, 1 warning in 6.70s
  ```
  Lint/formato/tipos (L-005): `uv run ruff check` y `uv run ruff format --check` y `uv run mypy tests/integracion/test_rutas_protegidas.py` — los tres en verde, 09:02:48.
- [x] 2.2 **R11** (D7 del design, E8): un modelo base de cuerpo con `extra="forbid"` y `strict=True`, y el manejador de 422 de las rutas de dominio que devuelve el campo y el motivo, nunca el valor. Un barrido nuevo en `tests/integracion/test_altas_sin_id_del_cliente.py` recorre toda ruta `POST` de dominio que encuentra el barrido de 2.1, toma su cuerpo válido de un diccionario de **cuerpos de prueba por ruta** y le suma `id`, `administracion_id` y `complejo_id` con un marcador: espera 422 cuya ruta de error **nombra `id`**, ninguna fila nueva y el marcador ausente de la respuesta. Una ruta `POST` sin cuerpo de prueba **hace fallar la suite** nombrándola (nunca se saltea). Exclusiones, con el motivo escrito en el test: la asignación del 2a (ignora `administracion_id`, diferencia conocida) y `POST .../sin-saldos-previos` (sin cuerpo). **Rojo**, dos: con una ruta de prueba cuyo cuerpo no hereda del modelo base, el barrido falla nombrándola; con una ruta de prueba sin cuerpo de prueba en el diccionario, también. Escenarios: `edificios-y-unidades` › Una ruta de alta nueva sin cuerpo estricto; › Una ruta de alta nueva sin cuerpo de prueba. Lecciones: L-007, L-019.

  **SUPUESTO declarado**: `strict=True` a nivel de todo el modelo choca con cómo FastAPI valida el cuerpo (dict ya parseado de JSON, modo "python" de pydantic): en modo "python" estricto, un campo `UUID` exige una instancia de `UUID`, no el texto que es la única forma en que JSON puede representarlo — se verificó con un repro directo (`M.model_validate({"x": "<uuid-como-texto>"})` con `strict=True` da `is_instance_of`, mientras que `M.model_validate_json(...)` con el mismo modelo lo acepta: FastAPI usa la primera forma). Romper esto habría tumbado el alta real existente. Se resolvió con `Annotated[UUID, Field(strict=False)]` en cada campo `UUID` de `CuerpoAsignacion` (no es una decisión de negocio: es el mecanismo para lograr lo que D7 pide sin romper la ruta de hoy). Puente con el patrón ya usado en `compartido/tenant_de_tarea.py::_AdministracionId` (también `strict=True` + `UUID`, pero ahí el string ya se convierte a `UUID` ANTES de llegarle al modelo estricto; acá no se puede hacer eso porque FastAPI es quien parsea el cuerpo).

  **RED** — 2026-10-19 09:10:28, archivo nuevo completo (sin `CuerpoDeAlta` ni el manejador todavía):
  ```
  $ uv run pytest tests/integracion/test_altas_sin_id_del_cliente.py -v
  FAILED ...::test_alta_con_id_del_cliente_da_422_sin_escribir_ni_filtrar_el_valor[ruta_y_metodo0]
    AssertionError: el 422 repite el marcador (el valor rechazado) en la respuesta (L-007)
    assert 'marcador-nu...na-respuesta' not in '{"detail":[...ound 49"}}]}'
    {"detail":[{"type":"uuid_parsing","loc":["body","administracion_id"],"msg":"Input should be a valid UUID, invalid length: found 49","input":"marcador-nunca-tendria-que-salir-en-una-respuesta","ctx":{"error":"invalid length: found 49"}}]}
  1 failed, 2 passed in 8.14s
  ```
  (El 422 ya salía por la validación normal de `administracion_id`, no por R11: `id` y `complejo_id` se ignoraban en silencio — confirmado aparte con `CuerpoAsignacion.model_validate({...,"id":"x","complejo_id":"y"})`, que hoy no tira nada. El rojo real de R11 es que NINGÚN error nombra `id`, tapado en esta corrida por la fuga de L-007 que aparece primero.)

  **GREEN** — 2026-10-19 09:11:25, con `proptech_api/cuerpos.py` (`CuerpoDeAlta`, `manejador_422`), `CuerpoAsignacion(CuerpoDeAlta)` con los `UUID` en `Field(strict=False)`, y el handler registrado en `app.py`:
  ```
  $ uv run pytest tests/integracion/test_altas_sin_id_del_cliente.py -v
  PASSED test_toda_ruta_post_tiene_cuerpo_de_prueba
  PASSED test_alta_con_id_del_cliente_da_422_sin_escribir_ni_filtrar_el_valor[ruta_y_metodo0]
  PASSED test_las_exclusiones_documentadas_siguen_siendo_rutas_del_barrido
  3 passed in 8.69s
  ```
  Sin regresión, 2026-10-19 09:12:47 (asignación del 2a, candado R6, alcance e identidad — 34 passed):
  ```
  $ uv run pytest tests/integracion/test_altas_sin_id_del_cliente.py tests/integracion/test_asignar_edificio_api.py tests/integracion/test_rutas_protegidas.py tests/integracion/test_alcance_api.py tests/integracion/test_identidad_api.py -q
  34 passed in 38.22s
  ```
  Lint/formato/tipos (L-005): `ruff check`, `ruff format --check` y `mypy` en verde, 2026-10-19 09:12:37, sobre `cuerpos.py`, `complejos.py`, `app.py` y el test nuevo.
- [x] 2.3 Deuda del 1b con dueño 3, parte de código (D13): `Porcentaje` y `Superficie` en `proptech_core/compartido/` (texto decimal ASCII, `fullmatch`, rechazo de `float`, `bool`, `NaN`, `Infinity`, `-0`, dígitos Unicode y `\n` final, con tests en rojo primero); `parametros.py` y `semilla.py` pasan a usarlos (L-009: la misma batería sobre los dos lectores); `parametros.py` rechaza un tipo de unidad fuera de los cuatro de D-029, con la constante que va a usar el `CHECK` de 3.1 (nota N9 c; rojo: hoy `quincho` en `tipos_de_unidad` pasa); `Semilla.version: Literal[1]` (rojo: hoy `version: 2` pasa); `naming_convention` en la `MetaData`; `pydantic` declarado directo en `backend/pyproject.toml` (rojo: `tests/infra/test_dependencias.py` lo exige). Escenarios: `datos-semilla` › Versión distinta de 1. Lecciones: L-008, L-009.

**Evidencia de 2.3 (rojo por mutante, pegado el 19/10/2026)**

Mutación posterior a la implementación; no reconstruye el rojo histórico de `b52257d`. Base: HEAD; copia previa en memoria, restaurada byte a byte después de cada corrida. Horas locales (Argentina).
L-009: misma batería de sufijos (`\n`, `\r`, `\t`, espacio, NUL) en tasa, fondo, factor y superficie; el mutante deja pasar `\n` y los otros cuatro siguen rechazándose.

```text
Porcentaje — backend/src/proptech_core/compartido/porcentaje.py
@@ -47,0 +48,2 @@
+        if type(texto) is float:
+            texto = str(texto)
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_porcentaje.py::test_construccion_rechaza_tipos_que_no_son_str[0.1] -q --tb=line
10:28:41
E   Failed: DID NOT RAISE PorcentajeInvalido
FAILED tests/unitarios/test_porcentaje.py::test_construccion_rechaza_tipos_que_no_son_str[0.1]
1 failed in 0.06s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
Superficie — backend/src/proptech_core/compartido/superficie.py
@@ -42,0 +43,2 @@
+        if type(texto) is float:
+            texto = str(texto)
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_superficie.py::test_construccion_rechaza_tipos_que_no_son_str[0.1] -q --tb=line
10:28:42
E   Failed: DID NOT RAISE SuperficieInvalida
FAILED tests/unitarios/test_superficie.py::test_construccion_rechaza_tipos_que_no_son_str[0.1]
1 failed in 0.03s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
Tipo D-029 — backend/src/proptech_core/compartido/parametros.py
@@ -79 +79 @@
-    if valor not in TIPOS_DE_UNIDAD_VALIDOS:
+    if False:
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_parametros.py::test_tipo_de_unidad_fuera_de_los_cuatro_de_d029_falla -q --tb=line
10:28:43
E   Failed: DID NOT RAISE ValidationError
FAILED tests/unitarios/test_parametros.py::test_tipo_de_unidad_fuera_de_los_cuatro_de_d029_falla
1 failed in 0.09s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
Semilla.version — backend/src/proptech_core/compartido/semilla.py
@@ -93 +93 @@
-    version: Literal[1]
+    version: int
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_semilla.py::test_version_distinta_de_uno_falla -q --tb=line
10:28:44
E   Failed: DID NOT RAISE SemillaInvalida
FAILED tests/unitarios/test_semilla.py::test_version_distinta_de_uno_falla - ...
1 failed in 0.13s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
naming_convention — backend/src/proptech_core/compartido/base_de_datos.py
@@ -33 +33 @@
-    metadata = MetaData(naming_convention=_NAMING_CONVENTION)
+    metadata = MetaData()
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_base_de_datos_naming_convention.py::test_metadata_de_base_tiene_naming_convention_determinista -q --tb=line
10:28:44
E   AssertionError: falta la clave 'uq' en naming_convention: immutabledict({'ix': 'ix_%(column_0_label)s'})
FAILED tests/unitarios/test_base_de_datos_naming_convention.py::test_metadata_de_base_tiene_naming_convention_determinista
1 failed in 0.12s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
pydantic directo — backend/pyproject.toml
@@ -12 +11,0 @@
-  "pydantic>=2.14.0,<2.15.0",
$ cd backend && date +%T && uv run --offline pytest tests/infra/test_dependencias.py::test_pyproject_exige_pydantic_directo -q --tb=line
10:28:45
E   AssertionError: no se encontró pydantic declarado directo (no transitivo) en ['fastapi>=0.143.0,<0.144.0', 'uvicorn>=0.54.0,<0.55.0', 'sqlalchemy>=2.1.4,<2.2.0', 'alembic>=1.20.0,<1.21.0', 'psycopg[binary]>=3.3.6,<3.4.0', 'pydantic-settings>=2.15.0,<2.16.0', 'pyyaml>=6.0.3,<7', 'arq==0.28.0', 'redis[hiredis]>=5.3.1,<6']
FAILED tests/infra/test_dependencias.py::test_pyproject_exige_pydantic_directo
1 failed in 0.01s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
L-009 tasa — backend/src/proptech_core/compartido/porcentaje.py
@@ -50 +50 @@
-        if not _PATRON.fullmatch(texto):
+        if not _PATRON.match(texto):
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_tasa_mensual_rechaza_sufijo_peligroso -q --tb=line
10:28:46
E   Failed: DID NOT RAISE ValidationError
FAILED tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_tasa_mensual_rechaza_sufijo_peligroso[\n]
1 failed, 4 passed in 0.08s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
L-009 fondo — backend/src/proptech_core/compartido/porcentaje.py
@@ -50 +50 @@
-        if not _PATRON.fullmatch(texto):
+        if not _PATRON.match(texto):
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_fondo_de_reserva_rechaza_sufijo_peligroso -q --tb=line
10:28:47
E   Failed: DID NOT RAISE ValidationError
FAILED tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_fondo_de_reserva_rechaza_sufijo_peligroso[\n]
1 failed, 4 passed in 0.07s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
L-009 factor — backend/src/proptech_core/compartido/porcentaje.py
@@ -50 +50 @@
-        if not _PATRON.fullmatch(texto):
+        if not _PATRON.match(texto):
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_factor_de_estado_rechaza_sufijo_peligroso -q --tb=line
10:28:48
E   Failed: DID NOT RAISE ValidationError
FAILED tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_factor_de_estado_rechaza_sufijo_peligroso[\n]
1 failed, 4 passed in 0.07s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
L-009 superficie — backend/src/proptech_core/compartido/superficie.py
@@ -45 +45 @@
-        if not _PATRON.fullmatch(texto):
+        if not _PATRON.match(texto):
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_superficie_m2_rechaza_sufijo_peligroso -q --tb=line
10:28:48
E   Failed: DID NOT RAISE ValidationError
FAILED tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py::test_superficie_m2_rechaza_sufijo_peligroso[\n]
1 failed, 4 passed in 0.08s
$ git diff --quiet -- backend/src  # salida: 0; pytest: 1
```

Los diez mutantes dieron rojo; ninguno sobrevivió. Verde final con producción y dependencias restauradas:

```text
$ cd backend && uv run --offline pytest tests/unitarios/test_porcentaje.py tests/unitarios/test_superficie.py tests/unitarios/test_parametros.py tests/unitarios/test_semilla.py tests/unitarios/test_base_de_datos_naming_convention.py tests/unitarios/test_rompedor_patrones_fullmatch_salto_de_linea.py tests/infra/test_dependencias.py -q
209 passed in 0.47s
[código de salida: 0]
```

- [x] 2.4 Deuda del 1b con dueño 3, parte de infraestructura (D13). Choca con `main` en `backend/src/proptech_api/app.py` (no en Compose, el humo ni el CI, que no cambiaron desde el fork): la rama ya tiene `main` desde el rebase del 16/10; si `main` volvió a tocar `app.py`, rebasar antes de empezar. `app.py` sin app creada al importar, conservando el log de `arranque_fallido` que sumó `main`, y `uvicorn --factory proptech_api.app:crear_app` en Compose y Dockerfile; healthcheck de la web contra `127.0.0.1`; `.gitignore` ampliado; el test de `chmod` salteado en Windows. Rojo de cada uno en `tests/infra/` y `tests/unitarios/test_arranque_api.py` (importar `proptech_api.app` hoy crea la app). Humo en verde al final. Escenarios: ninguno nuevo (no cambia comportamiento observable). Lecciones: L-005.

**ROJO inicial de D13: importación sin configuración, CMD factory y salud web IPv4 (19/10/2026)**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api.py tests/unitarios/test_arranque_api_parametros.py tests/unitarios/test_arranque_api_password_vacio.py tests/unitarios/test_arranque_api_variable_malformada.py tests/infra/test_logs_y_proxy.py::test_dockerfile_backend_corre_uvicorn_sin_log_de_acceso_y_confiando_en_el_proxy tests/infra/test_compose.py::test_healthcheck_de_web_usa_loopback_ipv4 -q --tb=short
09:53:22
FF......FF                                                               [100%]
=================================== FAILURES ===================================
_ test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion[POSTGRES_APP_PASSWORD] _
tests/unitarios/test_arranque_api.py:32: in test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion
    assert resultado.returncode == 0, resultado.stderr
E   AssertionError: Traceback (most recent call last):
E       File "<string>", line 1, in <module>
E         import proptech_api.app; print('IMPORTADO')
E         ^^^^^^^^^^^^^^^^^^^^^^^
E       File "/home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_api/app.py", line 115, in <module>
E         app = crear_app()
E       File "/home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_api/app.py", line 47, in crear_app
E         configuracion = Configuracion()
E       File "/home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_core/compartido/configuracion.py", line 343, in __init__
E         raise ConfiguracionInvalida(
E             f"Configuración inválida — {_mensaje_configuracion_invalida(error)}"
E         ) from None
E     proptech_core.compartido.configuracion.ConfiguracionInvalida: Configuración inválida — falta configurar: POSTGRES_APP_PASSWORD
E
E   assert 1 == 0
E    +  where 1 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', "import proptech_api...re.compartido.configuracion.ConfiguracionInvalida: Configuración inválida — falta configurar: POSTGRES_APP_PASSWORD\n').returncode
_ test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion[PROPTECH_PARAMETROS] _
tests/unitarios/test_arranque_api.py:32: in test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion
    assert resultado.returncode == 0, resultado.stderr
E   AssertionError: Traceback (most recent call last):
E       File "<string>", line 1, in <module>
E         import proptech_api.app; print('IMPORTADO')
E         ^^^^^^^^^^^^^^^^^^^^^^^
E       File "/home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_api/app.py", line 115, in <module>
E         app = crear_app()
E       File "/home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_api/app.py", line 47, in crear_app
E         configuracion = Configuracion()
E       File "/home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_core/compartido/configuracion.py", line 343, in __init__
E         raise ConfiguracionInvalida(
E             f"Configuración inválida — {_mensaje_configuracion_invalida(error)}"
E         ) from None
E     proptech_core.compartido.configuracion.ConfiguracionInvalida: Configuración inválida — falta configurar: PROPTECH_PARAMETROS
E
E   assert 1 == 0
E    +  where 1 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', "import proptech_api...core.compartido.configuracion.ConfiguracionInvalida: Configuración inválida — falta configurar: PROPTECH_PARAMETROS\n').returncode
_ test_dockerfile_backend_corre_uvicorn_sin_log_de_acceso_y_confiando_en_el_proxy _
tests/infra/test_logs_y_proxy.py:36: in test_dockerfile_backend_corre_uvicorn_sin_log_de_acceso_y_confiando_en_el_proxy
    assert comando[:3] == ["uvicorn", "--factory", "proptech_api.app:crear_app"], comando
E   AssertionError: ['uvicorn', 'proptech_api.app:app', '--host', '0.0.0.0', '--port', '8000', ...]
E   assert ['uvicorn', '...pp', '--host'] == ['uvicorn', '...pp:crear_app']
E
E     At index 1 diff: 'proptech_api.app:app' != '--factory'
E     Use -v to get more diff
__________________ test_healthcheck_de_web_usa_loopback_ipv4 ___________________
tests/infra/test_compose.py:23: in test_healthcheck_de_web_usa_loopback_ipv4
    assert "fetch('http://127.0.0.1:3000')" in comando[3], comando
E   AssertionError: ['CMD', 'node', '-e', "fetch('http://localhost:3000').then(r=>{if(!r.ok)throw new Error(r.status)}).catch(()=>process.exit(1))"]
E   assert "fetch('http://127.0.0.1:3000')" in "fetch('http://localhost:3000').then(r=>{if(!r.ok)throw new Error(r.status)}).catch(()=>process.exit(1))"
=========================== short test summary info ============================
FAILED tests/unitarios/test_arranque_api.py::test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion[POSTGRES_APP_PASSWORD]
FAILED tests/unitarios/test_arranque_api.py::test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion[PROPTECH_PARAMETROS]
FAILED tests/infra/test_logs_y_proxy.py::test_dockerfile_backend_corre_uvicorn_sin_log_de_acceso_y_confiando_en_el_proxy
FAILED tests/infra/test_compose.py::test_healthcheck_de_web_usa_loopback_ipv4
4 failed, 6 passed in 4.73s
[código de salida: 1]
```

**VERDE de D13: importación sin efectos y arranque explícito con validación**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api.py tests/unitarios/test_arranque_api_parametros.py tests/unitarios/test_arranque_api_password_vacio.py tests/unitarios/test_arranque_api_variable_malformada.py tests/infra/test_logs_y_proxy.py::test_dockerfile_backend_corre_uvicorn_sin_log_de_acceso_y_confiando_en_el_proxy tests/infra/test_compose.py::test_healthcheck_de_web_usa_loopback_ipv4 -q --tb=short
09:54:07
..........                                                               [100%]
10 passed in 5.10s
[código de salida: 0]
```

Mutante temporal **M1 contraseña faltante aceptada**, con copia previa en `/tmp/proptech-2-4/` (L-013; sin commit del mutante):

```diff
--- backend/src/proptech_core/compartido/configuracion.py
+++ M1 contraseña faltante aceptada
@@ -164,7 +164,7 @@
     las usan la API y el worker, que sí hablan con Redis y leen los parámetros."""

     postgres_user: str = Field(validation_alias="POSTGRES_APP_USER")
-    postgres_password: SecretStr = Field(validation_alias="POSTGRES_APP_PASSWORD")
+    postgres_password: SecretStr = Field(default=SecretStr("prueba-mutante"), validation_alias="POSTGRES_APP_PASSWORD")

     redis_host: str
     redis_port: int = Field(default=6379, ge=1, le=65535)
```

**ROJO del mutante M1 contraseña faltante aceptada**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api.py::test_el_proceso_termina_si_falta_postgres_app_password -q --tb=short
09:54:54
F                                                                        [100%]
=================================== FAILURES ===================================
____________ test_el_proceso_termina_si_falta_postgres_app_password ____________
tests/unitarios/test_arranque_api.py:56: in test_el_proceso_termina_si_falta_postgres_app_password
    assert resultado.returncode != 0, (
E   AssertionError: el proceso arrancó (código 0) sin POSTGRES_APP_PASSWORD; stdout='' stderr=''
E   assert 0 != 0
E    +  where 0 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', 'from proptech_api.app import crear_app; crear_app()'], returncode=0, stdout='', stderr='').returncode
=========================== short test summary info ============================
FAILED tests/unitarios/test_arranque_api.py::test_el_proceso_termina_si_falta_postgres_app_password
1 failed in 0.61s
[código de salida: 1]
```

**Reversión de M1 contraseña faltante aceptada: diff contra copia previa**

```text
$ cd backend && date +%T && diff -u /tmp/proptech-2-4/M1-configuracion.py.original /home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_core/compartido/configuracion.py
09:54:55

[código de salida: 0]
```

Mutante temporal **M2 YAML con tasa negativa aceptado**, con copia previa en `/tmp/proptech-2-4/` (L-013; sin commit del mutante):

```diff
--- backend/src/proptech_api/app.py
+++ M2 YAML con tasa negativa aceptado
@@ -50,7 +50,7 @@
         raise
     # Idem con los parámetros del sistema (D6): un archivo inválido también
     # termina el arranque acá, nombrando cada campo con problemas.
-    leer_parametros(configuracion.proptech_parametros)
+    # Mutante temporal: se omite validar el contenido del YAML.

     @asynccontextmanager
     async def lifespan(app: FastAPI) -> AsyncIterator[None]:
```

**ROJO del mutante M2 YAML con tasa negativa aceptado**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_tasa_negativa_nombrando_el_campo -q --tb=short
09:54:55
F                                                                        [100%]
=================================== FAILURES ===================================
_________ test_el_proceso_termina_con_tasa_negativa_nombrando_el_campo _________
tests/unitarios/test_arranque_api_parametros.py:36: in test_el_proceso_termina_con_tasa_negativa_nombrando_el_campo
    assert resultado.returncode != 0
E   AssertionError: assert 0 != 0
E    +  where 0 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', 'from proptech_api.app import crear_app; crear_app()'], returncode=0, stdout='', stderr='').returncode
=========================== short test summary info ============================
FAILED tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_tasa_negativa_nombrando_el_campo
1 failed in 0.58s
[código de salida: 1]
```

**Reversión de M2 YAML con tasa negativa aceptado: diff contra copia previa**

```text
$ cd backend && date +%T && diff -u /tmp/proptech-2-4/M2-app.py.original /home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_api/app.py
09:54:56

[código de salida: 0]
```

Mutante temporal **M3 contraseña vacía aceptada**, con copia previa en `/tmp/proptech-2-4/` (L-013; sin commit del mutante):

```diff
--- backend/src/proptech_core/compartido/configuracion.py
+++ M3 contraseña vacía aceptada
@@ -187,7 +187,7 @@
     @field_validator("postgres_password")
     @classmethod
     def _password_recortada(cls, valor: SecretStr) -> SecretStr:
-        _recortado_sin_cambios(valor.get_secret_value())
+        # Mutante temporal: se acepta la contraseña vacía.
         return valor

     @field_validator(
```

**ROJO del mutante M3 contraseña vacía aceptada**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api_password_vacio.py -q --tb=short
09:55:25
F                                                                        [100%]
=================================== FAILURES ===================================
_____________ test_el_proceso_no_debe_arrancar_con_password_vacio ______________
tests/unitarios/test_arranque_api_password_vacio.py:40: in test_el_proceso_no_debe_arrancar_con_password_vacio
    assert resultado.returncode != 0, (
E   AssertionError: el proceso arrancó con POSTGRES_APP_PASSWORD vacío en vez de terminar nombrando el problema. stdout='ARRANCO\n'
E   assert 0 != 0
E    +  where 0 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', "from proptech_api.app import crear_app; crear_app(); print('ARRANCO')"], returncode=0, stdout='ARRANCO\n', stderr='').returncode
=========================== short test summary info ============================
FAILED tests/unitarios/test_arranque_api_password_vacio.py::test_el_proceso_no_debe_arrancar_con_password_vacio
1 failed in 0.63s
[código de salida: 1]
```

**Reversión de M3 contraseña vacía aceptada: diff contra copia previa**

```text
$ cd backend && date +%T && diff -u /tmp/proptech-2-4/M3-configuracion.py.original /home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_core/compartido/configuracion.py
09:55:26

[código de salida: 0]
```

Mutante temporal **M4 puerto abc aceptado**, con copia previa en `/tmp/proptech-2-4/` (L-013; sin commit del mutante):

```diff
--- backend/src/proptech_core/compartido/configuracion.py
+++ M4 puerto abc aceptado
@@ -103,7 +103,7 @@
     @field_validator("postgres_port", mode="before")
     @classmethod
     def _puerto_entero_ascii_estricto(cls, valor: object) -> object:
-        return _entero_ascii_estricto(valor)
+        return 5432 if valor == "abc" else _entero_ascii_estricto(valor)

     @field_validator("postgres_host", "postgres_db")
     @classmethod
```

**ROJO del mutante M4 puerto abc aceptado**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api_variable_malformada.py -q --tb=short
09:55:26
F                                                                        [100%]
=================================== FAILURES ===================================
___________ test_el_proceso_nombra_la_variable_con_puerto_malformado ___________
tests/unitarios/test_arranque_api_variable_malformada.py:37: in test_el_proceso_nombra_la_variable_con_puerto_malformado
    assert resultado.returncode != 0, "el proceso debería terminar con POSTGRES_PORT inválido"
E   AssertionError: el proceso debería terminar con POSTGRES_PORT inválido
E   assert 0 != 0
E    +  where 0 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', 'from proptech_api.app import crear_app; crear_app()'], returncode=0, stdout='', stderr='').returncode
=========================== short test summary info ============================
FAILED tests/unitarios/test_arranque_api_variable_malformada.py::test_el_proceso_nombra_la_variable_con_puerto_malformado
1 failed in 0.72s
[código de salida: 1]
```

**Reversión de M4 puerto abc aceptado: diff contra copia previa**

```text
$ cd backend && date +%T && diff -u /tmp/proptech-2-4/M4-configuracion.py.original /home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_core/compartido/configuracion.py
09:55:28

[código de salida: 0]
```

Mutante temporal **M5 ruta de parámetros faltante aceptada**, con copia previa en `/tmp/proptech-2-4/` (L-013; sin commit del mutante):

```diff
--- backend/src/proptech_core/compartido/configuracion.py
+++ M5 ruta de parámetros faltante aceptada
@@ -169,7 +169,7 @@
     redis_host: str
     redis_port: int = Field(default=6379, ge=1, le=65535)
     redis_password: SecretStr
-    proptech_parametros: str
+    proptech_parametros: str = '/home/juanisarmiento/Proyectos/PropTech/config/parametros.yaml'

     # Parámetros del pool del engine (D18, M14): opcionales con default, así
     # no se suma ninguna variable obligatoria a `.env`.
```

**ROJO del mutante M5 ruta de parámetros faltante aceptada**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_proptech_parametros_faltante_nombrando_la_variable -q --tb=short
09:55:28
F                                                                        [100%]
=================================== FAILURES ===================================
_ test_el_proceso_termina_con_proptech_parametros_faltante_nombrando_la_variable _
tests/unitarios/test_arranque_api_parametros.py:53: in test_el_proceso_termina_con_proptech_parametros_faltante_nombrando_la_variable
    assert resultado.returncode != 0
E   AssertionError: assert 0 != 0
E    +  where 0 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', 'from proptech_api.app import crear_app; crear_app()'], returncode=0, stdout='', stderr='').returncode
=========================== short test summary info ============================
FAILED tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_proptech_parametros_faltante_nombrando_la_variable
1 failed in 0.73s
[código de salida: 1]
```

**Reversión de M5 ruta de parámetros faltante aceptada: diff contra copia previa**

```text
$ cd backend && date +%T && diff -u /tmp/proptech-2-4/M5-configuracion.py.original /home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_core/compartido/configuracion.py
09:55:29

[código de salida: 0]
```

Mutante temporal **M6 ruta de parámetros vacía aceptada**, con copia previa en `/tmp/proptech-2-4/` (L-013; sin commit del mutante):

```diff
--- backend/src/proptech_core/compartido/configuracion.py
+++ M6 ruta de parámetros vacía aceptada
@@ -205,7 +205,7 @@
     @field_validator("redis_host", "proptech_parametros")
     @classmethod
     def _recortados(cls, valor: str) -> str:
-        return _recortado_sin_cambios(valor)
+        return '/home/juanisarmiento/Proyectos/PropTech/config/parametros.yaml' if valor == "" else _recortado_sin_cambios(valor)

     @field_validator("redis_password")
     @classmethod
```

**ROJO del mutante M6 ruta de parámetros vacía aceptada**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_proptech_parametros_vacia_nombrando_la_variable -q --tb=short
09:55:29
F                                                                        [100%]
=================================== FAILURES ===================================
_ test_el_proceso_termina_con_proptech_parametros_vacia_nombrando_la_variable __
tests/unitarios/test_arranque_api_parametros.py:70: in test_el_proceso_termina_con_proptech_parametros_vacia_nombrando_la_variable
    assert resultado.returncode != 0
E   AssertionError: assert 0 != 0
E    +  where 0 = CompletedProcess(args=['/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3', '-c', 'from proptech_api.app import crear_app; crear_app()'], returncode=0, stdout='', stderr='').returncode
=========================== short test summary info ============================
FAILED tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_proptech_parametros_vacia_nombrando_la_variable
1 failed in 0.61s
[código de salida: 1]
```

**Reversión de M6 ruta de parámetros vacía aceptada: diff contra copia previa**

```text
$ cd backend && date +%T && diff -u /tmp/proptech-2-4/M6-configuracion.py.original /home/juanisarmiento/Proyectos/PropTech/backend/src/proptech_core/compartido/configuracion.py
09:55:30

[código de salida: 0]
```

**VERDE focalizado después del formato y las reversiones**

```text
$ cd backend && date +%T && uv run --offline pytest tests/unitarios/test_arranque_api.py tests/unitarios/test_arranque_api_parametros.py tests/unitarios/test_arranque_api_password_vacio.py tests/unitarios/test_arranque_api_variable_malformada.py tests/infra/test_logs_y_proxy.py tests/infra/test_compose.py::test_healthcheck_de_web_usa_loopback_ipv4 -q --tb=short
10:08:30
................                                                         [100%]
16 passed in 5.07s
[código de salida: 0]
```

**Commit bloqueado por filesystem: git add no puede escribir .git/index.lock**

```text
$ cd backend && date +%T && git -C /home/juanisarmiento/Proyectos/PropTech add backend/Dockerfile backend/src/proptech_api/app.py backend/tests/infra/test_compose.py backend/tests/infra/test_logs_y_proxy.py backend/tests/integracion/test_causa_de_arranque_rechazado.py backend/tests/unitarios/test_arranque_api.py backend/tests/unitarios/test_arranque_api_parametros.py backend/tests/unitarios/test_arranque_api_password_vacio.py backend/tests/unitarios/test_arranque_api_variable_malformada.py backend/tests/unitarios/test_motor_unico.py infra/compose.yaml openspec/changes/configuracion-del-edificio/tasks.md
10:08:54
fatal: Unable to create '/home/juanisarmiento/Proyectos/PropTech/.git/index.lock': Read-only file system
[código de salida: 128]
```

**Suite completa solicitada: repetición con límite externo de 75 s tras bloqueo en TestClient**

```text
$ cd backend && date +%T && timeout --signal=INT --kill-after=5s 75s uv run --offline pytest tests/unitarios tests/infra -q
10:08:29
......................................................................Timeout (0:00:55)!
Thread 0x00007a2f071fe6c0 [asyncio-portal-] (most recent call first):
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/selectors.py", line 452 in select
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py", line 2019 in _run_once
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py", line 677 in run_forever
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py", line 706 in run_until_complete
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/runners.py", line 127 in run
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 2548 in run
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/_core/_eventloop.py", line 83 in run
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 538 in run_blocking_portal
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 1024 in run
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 1082 in _bootstrap_inner
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 1044 in _bootstrap

Thread 0x00007a2f0f8da740 [pytest] (most recent call first):
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 369 in wait
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/concurrent/futures/_base.py", line 445 in result
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 2780 in run_sync_from_thread
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 119 in run_sync
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 303 in _spawn_task_from_thread
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 384 in start_task_soon
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 340 in call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/starlette/testclient.py", line 356 in handle_request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1014 in _send_single_request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 979 in _send_handling_redirects
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 942 in _send_handling_auth
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 914 in send
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 825 in request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/starlette/testclient.py", line 463 in request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1053 in get
  File "/home/juanisarmiento/Proyectos/PropTech/backend/tests/unitarios/test_ataque_ruta.py", line 82 in test_ruta_logueada_es_la_plantilla_y_no_contiene_el_valor
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/python.py", line 167 in pytest_pyfunc_call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/python.py", line 1707 in runtest
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 184 in pytest_runtest_call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 250 in <lambda>
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 361 in from_call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 249 in call_and_report
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 139 in runtestprotocol
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 118 in pytest_runtest_protocol
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 408 in pytest_runtestloop
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 384 in _main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 330 in wrap_session
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 377 in pytest_cmdline_main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/config/__init__.py", line 229 in _main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/config/__init__.py", line 253 in _console_main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/pytest", line 10 in <module>
[código de salida: -9]
```

**ROJO de lint: línea de 104 caracteres**

```text
$ cd backend && date +%T && uv run --offline ruff check .
09:56:42
E501 Line too long (104 > 100)
  --> tests/unitarios/test_arranque_api_password_vacio.py:32:101
   |
31 |     resultado = subprocess.run(
32 |         [sys.executable, "-c", "from proptech_api.app import crear_app; crear_app(); print('ARRANCO')"],
   |                                                                                                     ^^^^
33 |         env=entorno,
34 |         capture_output=True,
   |

Found 1 error.
[código de salida: 1]
```

**ROJO de formato: lista de argumentos del subproceso**

```text
$ cd backend && date +%T && uv run --offline ruff format --check .
09:56:42
unformatted: File would be reformatted
  --> tests/unitarios/test_arranque_api_password_vacio.py:32:10
   |
31 |     resultado = subprocess.run(
   -         [sys.executable, "-c", "from proptech_api.app import crear_app; crear_app(); print('ARRANCO')"],
32 +         [
33 +             sys.executable,
34 +             "-c",
35 +             "from proptech_api.app import crear_app; crear_app(); print('ARRANCO')",
36 +         ],
37 |         env=entorno,
   |

1 file would be reformatted, 162 files already formatted
[código de salida: 1]
```

**VERDE de lint después de formatear la lista**

```text
$ cd backend && date +%T && uv run --offline ruff check .
09:57:10
All checks passed!
[código de salida: 0]
```

**VERDE de formato**

```text
$ cd backend && date +%T && uv run --offline ruff format --check .
09:57:10
163 files already formatted
[código de salida: 0]
```

**VERDE de tipos (L-005)**

```text
$ cd backend && date +%T && uv run --offline mypy
09:57:10
Success: no issues found in 155 source files
[código de salida: 0]
```


**Corridas interrumpidas y diagnóstico del bloqueo (sin resultado verde)**

Se ejecutaron primero estas dos corridas sin límite externo:

```text
uv run --offline pytest tests/unitarios tests/infra -q
uv run --offline pytest tests/unitarios tests/infra/test_logs_y_proxy.py tests/infra/test_compose.py::test_healthcheck_de_web_usa_loopback_ipv4 -q
```

Ambas se interrumpieron con Ctrl-C (código 130) tras ubicar el bloqueo.
El arnés capturaba stdout y sólo lo imprimía al terminar; al interrumpirlo
no se recuperó esa salida ni su hora inicial. No se atribuyen conteos ni
resultado a esas dos corridas. La orden completa se repitió con un límite
externo de 75 segundos y su hora/salida se registran por separado.

La corrida de diagnóstico con salida detallada fue:

```text
$ cd backend && date +%T
10:06:20
$ uv run --offline pytest tests/unitarios -vv -x 2>&1 | tee /tmp/proptech-2-4/unitarios-detalle.log
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0 -- /home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/juanisarmiento/Proyectos/PropTech/backend
configfile: pyproject.toml
plugins: anyio-4.15.1
collecting ... collected 648 items

tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-cargar_gastos_y_preparar_liquidacion] PASSED [  0%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-emitir_y_distribuir_liquidacion] PASSED [  0%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-anular_liquidacion] PASSED [  0%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-confirmar_pago_informado] PASSED [  0%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-revertir_o_reimputar_pago] PASSED [  0%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-condonar_intereses] PASSED [  0%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-dar_de_baja_deuda] PASSED [  1%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-aceptar_alertas_no_bloqueantes] PASSED [  1%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-aceptar_alertas_bloqueantes] PASSED [  1%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-invitar_usuarios_y_asignar_edificios] PASSED [  1%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[titular-informar_pago] PASSED [  1%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-cargar_gastos_y_preparar_liquidacion] PASSED [  1%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-emitir_y_distribuir_liquidacion] PASSED [  2%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-anular_liquidacion] PASSED [  2%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-confirmar_pago_informado] PASSED [  2%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-revertir_o_reimputar_pago] PASSED [  2%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-condonar_intereses] PASSED [  2%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-dar_de_baja_deuda] PASSED [  2%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-aceptar_alertas_no_bloqueantes] PASSED [  2%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-aceptar_alertas_bloqueantes] PASSED [  3%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-invitar_usuarios_y_asignar_edificios] PASSED [  3%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[colaborador-informar_pago] PASSED [  3%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-cargar_gastos_y_preparar_liquidacion] PASSED [  3%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-emitir_y_distribuir_liquidacion] PASSED [  3%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-anular_liquidacion] PASSED [  3%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-confirmar_pago_informado] PASSED [  4%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-revertir_o_reimputar_pago] PASSED [  4%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-condonar_intereses] PASSED [  4%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-dar_de_baja_deuda] PASSED [  4%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-aceptar_alertas_no_bloqueantes] PASSED [  4%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-aceptar_alertas_bloqueantes] PASSED [  4%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-invitar_usuarios_y_asignar_edificios] PASSED [  4%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[consejo-informar_pago] PASSED [  5%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-cargar_gastos_y_preparar_liquidacion] PASSED [  5%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-emitir_y_distribuir_liquidacion] PASSED [  5%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-anular_liquidacion] PASSED [  5%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-confirmar_pago_informado] PASSED [  5%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-revertir_o_reimputar_pago] PASSED [  5%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-condonar_intereses] PASSED [  6%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-dar_de_baja_deuda] PASSED [  6%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-aceptar_alertas_no_bloqueantes] PASSED [  6%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-aceptar_alertas_bloqueantes] PASSED [  6%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-invitar_usuarios_y_asignar_edificios] PASSED [  6%]
tests/unitarios/acceso/test_permisos.py::test_cada_celda_de_la_matriz[vecino-informar_pago] PASSED [  6%]
tests/unitarios/acceso/test_permisos.py::test_colaborador_de_nivel_ver_no_tiene_ninguna_fila_en_si PASSED [  6%]
tests/unitarios/acceso/test_permisos.py::test_una_accion_sin_fila_en_la_matriz_se_niega_para_todos PASSED [  7%]
tests/unitarios/acceso/test_permisos.py::test_alcanza_titular_cualquier_complejo_y_unidad PASSED [  7%]
tests/unitarios/acceso/test_permisos.py::test_alcanza_colaborador_solo_el_complejo_asignado PASSED [  7%]
tests/unitarios/acceso/test_permisos.py::test_alcanza_consejo_solo_su_complejo PASSED [  7%]
tests/unitarios/acceso/test_permisos.py::test_alcanza_vecino_su_complejo_y_su_unidad_no_otra PASSED [  7%]
tests/unitarios/acceso/test_permisos.py::test_alcanza_sin_ninguna_asignacion_es_falso PASSED [  7%]
tests/unitarios/test_arranque_api.py::test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion[POSTGRES_APP_PASSWORD] PASSED [  8%]
tests/unitarios/test_arranque_api.py::test_importar_el_modulo_no_crea_la_app_ni_valida_configuracion[PROPTECH_PARAMETROS] PASSED [  8%]
tests/unitarios/test_arranque_api.py::test_el_proceso_termina_si_falta_postgres_app_password PASSED [  8%]
tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_tasa_negativa_nombrando_el_campo PASSED [  8%]
tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_proptech_parametros_faltante_nombrando_la_variable PASSED [  8%]
tests/unitarios/test_arranque_api_parametros.py::test_el_proceso_termina_con_proptech_parametros_vacia_nombrando_la_variable PASSED [  8%]
tests/unitarios/test_arranque_api_password_vacio.py::test_el_proceso_no_debe_arrancar_con_password_vacio PASSED [  8%]
tests/unitarios/test_arranque_api_variable_malformada.py::test_el_proceso_nombra_la_variable_con_puerto_malformado PASSED [  9%]
tests/unitarios/test_arranque_worker.py::test_el_proceso_termina_si_falta_postgres_app_password PASSED [  9%]
tests/unitarios/test_arranque_worker_parametros.py::test_el_proceso_termina_con_tasa_negativa_nombrando_el_campo PASSED [  9%]
tests/unitarios/test_arranque_worker_parametros.py::test_el_proceso_termina_con_proptech_parametros_faltante_nombrando_la_variable PASSED [  9%]
tests/unitarios/test_arranque_worker_parametros.py::test_el_proceso_termina_con_proptech_parametros_vacia_nombrando_la_variable PASSED [  9%]
tests/unitarios/test_arranque_worker_parametros.py::test_el_proceso_termina_con_proptech_parametros_inexistente_nombrando_la_variable PASSED [  9%]
tests/unitarios/test_arranque_worker_password_vacio.py::test_el_proceso_no_arranca_con_postgres_password_vacio PASSED [ 10%]
tests/unitarios/test_arranque_worker_password_vacio.py::test_el_proceso_no_arranca_con_redis_password_vacia PASSED [ 10%]
tests/unitarios/test_arranque_worker_password_vacio.py::test_el_proceso_no_arranca_con_redis_password_en_blanco PASSED [ 10%]
tests/unitarios/test_arranque_worker_variable_malformada.py::test_el_proceso_nombra_la_variable_con_postgres_port_malformado PASSED [ 10%]
tests/unitarios/test_arranque_worker_variable_malformada.py::test_el_proceso_nombra_la_variable_con_redis_port_malformado PASSED [ 10%]
tests/unitarios/test_arranque_worker_variable_malformada.py::test_el_proceso_nombra_la_variable_con_redis_port_fuera_de_rango PASSED [ 10%]
tests/unitarios/test_ataque_ruta.py::test_ruta_logueada_es_la_plantilla_y_no_contiene_el_valor[/api/personas/pers-/api/personas/{dni}-pers] Timeout (0:00:55)!
Thread 0x00007a3f50dff6c0 [asyncio-portal-] (most recent call first):
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/selectors.py", line 452 in select
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py", line 2019 in _run_once
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py", line 677 in run_forever
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/base_events.py", line 706 in run_until_complete
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/asyncio/runners.py", line 127 in run
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 2548 in run
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/_core/_eventloop.py", line 83 in run
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 538 in run_blocking_portal
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 1024 in run
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 1082 in _bootstrap_inner
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 1044 in _bootstrap

Thread 0x00007a3f58d24740 [pytest] (most recent call first):
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/threading.py", line 369 in wait
  File "/home/juanisarmiento/.local/share/uv/python/cpython-3.14.4-linux-x86_64-gnu/lib/python3.14/concurrent/futures/_base.py", line 445 in result
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/_backends/_asyncio.py", line 2780 in run_sync_from_thread
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 119 in run_sync
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 303 in _spawn_task_from_thread
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 384 in start_task_soon
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/anyio/from_thread.py", line 340 in call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/starlette/testclient.py", line 356 in handle_request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1014 in _send_single_request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 979 in _send_handling_redirects
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 942 in _send_handling_auth
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 914 in send
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 825 in request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/starlette/testclient.py", line 463 in request
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/httpx/_client.py", line 1053 in get
  File "/home/juanisarmiento/Proyectos/PropTech/backend/tests/unitarios/test_ataque_ruta.py", line 82 in test_ruta_logueada_es_la_plantilla_y_no_contiene_el_valor
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/python.py", line 167 in pytest_pyfunc_call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/python.py", line 1707 in runtest
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 184 in pytest_runtest_call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 250 in <lambda>
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 361 in from_call
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 249 in call_and_report
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 139 in runtestprotocol
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/runner.py", line 118 in pytest_runtest_protocol
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 408 in pytest_runtestloop
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 384 in _main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 330 in wrap_session
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/main.py", line 377 in pytest_cmdline_main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_callers.py", line 121 in _multicall
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_manager.py", line 120 in _hookexec
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/pluggy/_hooks.py", line 512 in __call__
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/config/__init__.py", line 229 in _main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/lib/python3.14/site-packages/_pytest/config/__init__.py", line 253 in _console_main
  File "/home/juanisarmiento/Proyectos/PropTech/backend/.venv/bin/pytest", line 10 in <module>
[código de salida de la interrupción con Ctrl-C: 130]
```

EVIDENCIA: el primer caso de `test_ataque_ruta.py` queda esperando dentro de
`TestClient.get`; faulthandler vuelca la traza a los 55 s. Ese test crea una
`FastAPI()` propia y no importa `proptech_api.app`. Se verificó sin diferencias
con `git diff --exit-code HEAD -- backend/tests/unitarios/test_ataque_ruta.py
backend/src/proptech_api/seguimiento.py` (código 0, sin salida).
La causa del bloqueo no se verificó: atribuirla al sandbox es una hipótesis,
no una conclusión. El orquestador debe repetir también unitarios e infra,
además de integración y humo.

**Revisión del constructor de la continuación de 2.4 (19/10/2026)**

HEAD inicial: `8ca9441`, rama `main`, árbol limpio al comenzar. Horas de los
comandos tomadas con `date +%T`, zona `-03` (`2026-10-19`, UTC−03:00).
La API de Compose hereda el CMD del Dockerfile: no declara un arranque Uvicorn
propio que haya que reemplazar. Se conservan todas las opciones del CMD y todo
el cuerpo de `crear_app()`, incluidos ambos logs de `arranque_fallido`.

Los 17 archivos originales de `rg -l "proptech_api\.app" backend/tests`
se revisaron uno por uno en sus imports, subprocesos y creación de la app:

| Archivo bajo `backend/tests/` | Resultado de la revisión |
| --- | --- |
| `unitarios/test_arranque_api.py` | Subproceso de arranque llama la fábrica; dos casos nuevos distinguen importación de arranque. |
| `unitarios/test_arranque_api_parametros.py` | Los tres subprocesos llaman la fábrica; M2, M5 y M6 prueban cada rechazo. |
| `unitarios/test_arranque_api_password_vacio.py` | Subproceso llama la fábrica y exige el nombre de la variable; M3. |
| `unitarios/test_arranque_api_variable_malformada.py` | Subproceso llama la fábrica y usa las credenciales del rol de app; M4. |
| `unitarios/test_salud.py` | Ya usa `crear_app()`; no requiere cambios. |
| `unitarios/test_middleware_error_inesperado.py` | Ya usa `crear_app()`; no requiere cambios. |
| `unitarios/test_middleware_seguimiento.py` | Ya usa `crear_app()`; no requiere cambios. |
| `unitarios/test_motor_unico.py` | Ya usa `app_mod.crear_app()`; se actualiza el comentario sobre validación. |
| `integracion/test_causa_de_arranque_rechazado.py` | Se adapta el subproceso de API a la fábrica; los otros casos ya la llaman. Sin ejecutar. |
| `integracion/test_rutas_protegidas.py` | Fixture ya usa `crear_app()` y `TestClient`; sin ejecutar. |
| `integracion/test_zz_rompedor_api_application_name.py` | Ya usa `crear_app()` y `TestClient`; sin ejecutar. |
| `integracion/test_alcance_api.py` | Fixture ya usa `crear_app()` y `TestClient`; sin ejecutar. |
| `integracion/test_salud_cola_real.py` | Los tres casos ya usan `crear_app()`; sin ejecutar. |
| `integracion/test_identidad_api.py` | Fixture ya usa `crear_app()` y `TestClient`; sin ejecutar. |
| `integracion/test_asignar_edificio_api.py` | Fixture ya usa `crear_app()` y `TestClient`; sin ejecutar. |
| `integracion/test_cableado_real_del_arranque.py` | Fixture y rechazo de rol inseguro ya llaman la fábrica; sin ejecutar. |
| `integracion/test_altas_sin_id_del_cliente.py` | Fixture ya usa `crear_app()` y `TestClient`; sin ejecutar. |

Después de exigir el target de la fábrica en `tests/infra/test_logs_y_proxy.py`,
el mismo `rg` sobre todos los tests devuelve 18 archivos: el adicional es ese
test estático; los 17 consumidores originales siguen presentes.
Una inspección AST de los 17 confirma sintaxis válida y ausencia de
`from proptech_api.app import app`; esto no ejecuta integración.

Otros archivos leídos (completos o secciones pertinentes):

- `AGENTS.md`, `CLAUDE.md`, `/home/juanisarmiento/.claude/CLAUDE.md`.
- `CHANGES.md`, `knowledge-base/12_fichas_de_changes.md`, `knowledge-base/15_lecciones.md`.
- `.claude/skills/openspec-apply-change/SKILL.md` y las skills locales
  `test-driven-development/SKILL.md` y `fastapi-templates/SKILL.md`.
- `openspec/changes/configuracion-del-edificio/{proposal,design,tasks}.md` y sus
  siete `specs/*/spec.md` (contexto de apply; implementación limitada a D13/2.4).
- `backend/src/proptech_api/app.py`,
  `backend/src/proptech_core/compartido/configuracion.py`, `backend/Dockerfile`,
  `backend/pyproject.toml`, `backend/tests/conftest.py`,
  `backend/tests/unitarios/conftest.py`, `backend/tests/infra/test_compose.py`,
  `backend/tests/infra/test_logs_y_proxy.py`, `infra/compose.yaml`,
  `infra/ci/test-backend.sh`.
- Para diagnosticar la corrida: `backend/tests/unitarios/test_ataque_ruta.py`,
  `test_ataque_uvicorn_lifespan.py`, `test_ataque_salud_cola_lenta.py`,
  `backend/src/proptech_api/seguimiento.py`, `backend/tests/infra/conftest.py`,
  `test_caddyfile_request_id.py`, `test_caddyfile_seguridad.py`,
  `test_ci_workflow.py` (estos últimos tres bajo `backend/tests/infra/`).

Archivos cambiados, todos leídos:

- `backend/src/proptech_api/app.py` y `backend/Dockerfile`.
- `infra/compose.yaml`.
- `backend/tests/unitarios/test_arranque_api.py`.
- `backend/tests/unitarios/test_arranque_api_parametros.py`.
- `backend/tests/unitarios/test_arranque_api_password_vacio.py`.
- `backend/tests/unitarios/test_arranque_api_variable_malformada.py`.
- `backend/tests/unitarios/test_motor_unico.py` (comentario).
- `backend/tests/integracion/test_causa_de_arranque_rechazado.py`.
- `backend/tests/infra/test_compose.py` y `backend/tests/infra/test_logs_y_proxy.py`.
- Este `tasks.md`, solamente debajo de 2.4; la casilla sigue pendiente.

Incidencia del arnés temporal de mutación: al preparar M3, el primer
`python3 /tmp/proptech-2-4/mutar.py` terminó con
`AssertionError: M3 contraseña vacía aceptada` porque el selector encontraba
dos validadores (Postgres y Redis). La guardia actuó antes de modificar M3;
M1 y M2 ya estaban revertidos. Se acotó el selector al método de contraseña de
Postgres y se retomó con `python3 /tmp/proptech-2-4/mutar.py 3`; los seis rojos
y sus seis reversiones están arriba. Las copias previas son propias de esta
sesión (L-013); además se comparó `configuracion.py` con el HEAD inicial,
byte por byte, sin diferencias.

Las salidas se conservan quitando códigos ANSI de color y espacios al final
de línea para mantener `git diff --check` limpio.

**JUICIO:** confianza alta en la importación sin creación de app, en el
rechazo de configuración inválida al llamar la fábrica y en los cambios
estáticos de arranque/salud. Los seis casos de rechazo pueden dar rojo.
La suite completa queda sin validar por el bloqueo descrito abajo.

**SUPUESTO:** el comportamiento real con PostgreSQL, Redis, Uvicorn y Next
en contenedores queda por verificar. Integración está adaptada o ya usaba la
fábrica, pero no se ejecutó ningún test de `tests/integracion/`, ni humo ni
build de imágenes. Los ejecuta el orquestador. No se leyó `infra/.env`, ni se
modificaron `.gitignore`, el test de chmod, ni otras tareas.

**Commits:** ninguno. `git add` falló con código 128 porque `.git` es de sólo
lectura (`Unable to create .../.git/index.lock: Read-only file system`).
Mensaje propuesto para el orquestador: `refactor(api): crear la aplicación al arrancar con factory`.
No se hizo push.

**Verificación final de alcance y reversiones**

```text
$ cd backend && date +%T && python3 /tmp/proptech-2-4/verificar.py
10:10:25
12 archivos cambiados, todos dentro del alcance; .gitignore y chmod sin cambios.
tasks.md: sólo cambia 2.4; su casilla sigue [ ]; otras tareas idénticas a 8ca9441.
app.py: único cambio = quitar la instancia global; crear_app y sus logs intactos.
configuracion.py: idéntico a 8ca9441; 6 mutantes revertidos y documentados.
17 consumidores originales: AST válida y fábrica explícita; integración sin ejecutar.
[código de salida: 0]
```

**VERDE de whitespace del diff final**

```text
$ cd backend && date +%T && git diff --check
10:10:26

[código de salida: 0]
```

**VERDE fuera del sandbox, corrido por el orquestador (19/10/2026)**

El bloqueo de `test_ataque_ruta.py:82` que anotó el constructor es del sandbox de Codex: fuera de él la misma orden termina.

```text
$ cd backend && uv run --offline pytest tests/unitarios tests/infra -q -p no:cacheprovider
10:12:03
834 passed, 1 warning in 58.31s

$ bash infra/ci/test-backend.sh        # integración contra Postgres en contenedores
10:13:07
=========== 1030 passed, 1 xfailed, 16 warnings in 287.17s (0:04:47) ===========
[código de salida: 0]

$ bash infra/ci/humo.sh                # imagen con CMD --factory, healthcheck web en 127.0.0.1
10:17:58
HUMO OK
[código de salida: 0]
```

Commit sobre el que corrió: `8ca9441` más el diff de 2.4 sin commitear (el commit es el siguiente).

**Verificación independiente del bloque D por el orquestador (19/10/2026, HEAD `4e31885`)**

```text
$ bash infra/ci/test-backend.sh
11:35:24
1351 passed, 1 xfailed, 16 warnings in 430.48s (0:07:10)
[código de salida: 0]

$ bash infra/ci/humo.sh          # ROJO: regresión de 3.1 que ningún test unitario ni de integración ve
11:42:36
ERROR:  null value in column "localidad" of relation "complejo" violates not-null constraint
ERROR: paso 0 (compose up --build -d --wait) falló en la línea 38
[código de salida: 3]

# arreglo: la siembra del humo (infra/ci/humo.sh) suma `localidad`, NOT NULL desde 0005 (3.1)
$ bash infra/ci/humo.sh
11:43:35
HUMO OK
[código de salida: 0]
```

Lección para los bloques que siguen: una migración que agrega `NOT NULL` rompe a todo el que inserta en esa tabla, también fuera de `backend/` (el humo corre con psql). Desde el bloque E, el humo se corre al final de cada bloque.

## Vuelta 1 de correcciones (R3A)

Informe del rompedor: `.git/informes-3a/rompedor/informe-vuelta-1.md`. Base `072a960`, HEAD `11fe3d9`. 0 CRÍTICA, 2 ALTA, 2 MEDIA, 2 BAJA. Un commit por hallazgo.

### R3A-1 · ALTA · NUL en texto libre da 500

Test movido a `tests/integracion/test_texto_sin_caracteres_de_control.py` (ampliado a 10 casos: la familia completa, alta y edición). Arreglo: `proptech_core/compartido/texto.py` (`sin_caracteres_de_control`, `recortado_sin_control`), aplicado en `unidades.py`, `grupos.py`, `parametros.py` y `complejos.py`.

**RED** — 19/10/2026, 12:38:25:
```text
$ date +%T && uv run pytest tests/rompedor_3a/test_r3a_nul_en_textos.py -q --color=no
12:38:25
...
FAILED test_nul_en_un_texto_da_422_y_no_500[0..6] (7 casos): 500, sqlalchemy.exc.DataError
7 failed, 1 warning in 5.84s
12:38:33
```

**GREEN** — 19/10/2026, 12:43:09, con la familia ampliada (10 casos, incluye PATCH de grupo y categoría):
```text
$ date +%T && uv run pytest tests/integracion/test_texto_sin_caracteres_de_control.py -q --color=no
12:43:09
..........                                                               [100%]
10 passed, 1 warning in 6.69s
12:43:18
```

**Mutante (L-019)**: sacado el `AfterValidator` de `CuerpoEdicionGrupo.nombre` (API), el test de PATCH de grupo sigue en verde porque `grupos.DatosGrupo` (dominio) lo frena igual — defensa en dos capas, no una aserción muerta. Sacado también de `grupos.DatosGrupo.nombre`, el caso 6 de la familia (POST grupo) da rojo: `FAILED test_texto_con_caracter_de_control_da_422_y_no_500[6]`, 500 real. Las dos capas se restituyeron antes de commitear.

**Hallazgo fuera de alcance, no arreglado**: al construir el test de PATCH de grupo, crear un grupo nuevo con `"unidades": []` (sin miembros) da **500** (`sqlalchemy.exc.ProgrammingError: operator does not exist: uuid = integer`) — el `bindparam("ids", expanding=True)` de `grupos.py::_reemplazar` con lista vacía renderiza `IN (SELECT CAST(NULL AS INTEGER) WHERE 1!=1)`, que no tipa contra `uuid`. Ningún test existente lo pisa porque toda alta de grupo de la suite manda al menos un miembro. No es ninguno de los 6 hallazgos del informe; lo evité en el test (mandé un miembro real) y lo dejo señalado, sin arreglar.

### R3A-2 · ALTA · Parámetros con nombres de categoría repetidos sin mayúsculas

Tests movidos a `tests/unitarios/test_parametros.py` (dos: `Parametros` directo y `leer_parametros` con archivo) y `tests/integracion/test_crear_edificio.py` (defensa en profundidad). Arreglo: `parametros.py::_validar_cruzadas` compara `nombre.lower()`; `escritura.py::crear_edificio` usa `transaccion(sesion, {"uq_categoria_nombre": "categorias_de_gasto"})` en vez de un `begin_nested()` pelado.

**RED** — 19/10/2026, 12:45:13:
```text
$ date +%T && uv run pytest tests/rompedor_3a/test_r3a_parametros_nombres_repetidos.py -q --color=no
12:45:13
FAILED test_arranque_rechaza_nombres_de_categoria_repetidos_sin_mayusculas — DID NOT RAISE ParametrosInvalidos
FAILED test_crear_edificio_con_esos_parametros_no_revienta — "crear_edificio deja escapar la IntegrityError cruda (500 en la API)"
2 failed in 5.39s
12:45:19
```

**GREEN** — 19/10/2026, 12:49:01 (suite `unitarios/` + `test_crear_edificio.py` + categorías, 865 tests):
```text
$ date +%T && uv run pytest tests/unitarios/ tests/integracion/test_crear_edificio.py tests/integracion/test_categorias_casos_de_uso.py tests/integracion/test_categorias_db.py -q --color=no
12:48:13
865 passed, 1 warning in 47.10s
12:49:01
```

**Mutante (L-019)**: revertido `transaccion(...)` a `sesion.begin_nested() if ... else sesion.begin()` puro, `test_categorias_con_nombre_repetido_sin_mayusculas_da_conflicto_no_500` da rojo real: `sqlalchemy.exc.IntegrityError: ... duplicate key value violates unique constraint "uq_categoria_nombre"`. Restituido antes de commitear. El test de `_validar_cruzadas` ya tenía su rojo (arriba, mismo mecanismo que el rompedor demostró).

### R3A-3 · MEDIA · "Generales" borrable o modificable por SQL

### R3A-4 · MEDIA · Rol/nivel inválido en asignación da 500

### R3A-5 · BAJA · El 422 saneado repite parte del valor

### R3A-6 · BAJA · Unicidad de identificador/nombre con espacios al borde

## 3. Modelo

- [x] 3.1 Migración del edificio y la unidad completos (D2): `complejo.localidad`, `complejo.estado_migracion`; `unidad.identificador` (renombra `nombre`), `tipo`, `piso`, `coeficiente NUMERIC(7,6)`, `superficie_m2 NUMERIC(10,2)`, `estado` nulo; sus `CHECK` y el `UNIQUE` del identificador. Tests en `tests/integracion/test_rls_edificio.py`, como `proptech_app`: identificador repetido en el mismo edificio falla y en otro pasa; coeficiente `0` o `1.000001` falla por `CHECK`; mover una unidad a un edificio de otra administración falla; `downgrade` a `0004` y `upgrade` vuelven. Actualizar los tests del 2a que usan `nombre` (contados en 1.1), la respuesta de `GET /api/unidades/{id}` (`identificador`, cambio de contrato) y el guardián del catálogo en verde. Escenarios: `edificios-y-unidades` › Mover una unidad por SQL; › Identificador repetido (la parte de la base). Lecciones: L-016, L-017.

  **RED** — 19/10/2026, antes de `0005` y del cambio de contrato:
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_alcance_api.py::test_vecino_en_la_unidad_de_otro_vecino_da_404 -q
  10:31:43
  E AssertionError: {'nombre': '1A'} != {'identificador': '1A'}
  1 failed, 1 warning in 6.29s
  cd backend && date +%T && uv run pytest tests/integracion/test_rls_edificio.py -q
  10:33:01
  E psycopg.errors.UndefinedColumn: column "localidad" of relation "complejo" does not exist
  1 failed, 23 errors in 7.51s
  ```
  **Mutante L-019** — la FK del 2a ya protegía el movimiento. Copia previa en
  `backend/.pytest_cache/bloque_b/0005_original.py`; diff temporal al final de `upgrade()`:
  ```diff
  +    op.drop_constraint("fk_unidad_complejo", "unidad", type_="foreignkey")
  +
  ```
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_rls_edificio.py -k mover_unidad -q
  10:34:27
  E Failed: DID NOT RAISE ForeignKeyViolation
  1 failed, 23 deselected in 3.30s
  ```
  Mutante revertido desde la copia antes del verde. Tests/siembra nuevos como `proptech_app`,
  sin superusuario ni BYPASSRLS, tenant local; bases propias dentro del contenedor de sesión.
  **Contrato modificado:** `GET /api/unidades/{id}` devuelve `identificador` en lugar de `nombre`;
  JSON completo comprobado en `test_alcance_api.py`. Se actualizaron los 6 INSERT de unidad en
  los 5 archivos del 2a contados en 1.1 y los INSERT de complejo que necesitan localidad.
  `0004`/`Accion` quedan para 3.7 (D14); este bloque no agrega vocabulario.

  **GREEN** — mutante revertido; suite de los archivos tocados + guardián:
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_rls_edificio.py tests/integracion/test_alcance_api.py tests/integracion/test_altas_sin_id_del_cliente.py tests/integracion/test_asignar_edificio_api.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_identidad_api.py tests/integracion/test_rls_acceso_minimo.py tests/integracion/test_rutas_protegidas.py tests/integracion/test_tenant_por_transaccion.py tests/integracion/test_worker_tenant.py tests/integracion/test_catalogo_rls.py -q
  10:34:41
  101 passed, 1 warning in 51.59s
  cd backend && date +%T && uv run ruff check . && uv run ruff format --check . && uv run mypy
  10:35:11
  All checks passed! / 166 files already formatted / Success: no issues found in 157 source files
  ```
- [x] 3.2 Migración de grupos (D2): `grupo_de_reparto` y `grupo_unidad` con las tres FK compuestas que comparten `complejo_id` (a `complejo`, al grupo y a la unidad; la primera la exige el guardián), "Generales" único por edificio y por coeficiente. Tests como `proptech_app`, insertando de verdad (L-018): miembro con una unidad de otro edificio de la misma administración falla; de otra administración falla; unidad repetida en un grupo falla; un segundo "Generales" falla; `downgrade` y `upgrade`. Escenarios: `grupos-de-reparto` › La base frena lo que la aplicación deja pasar; › Unidad repetida en un grupo (la parte de la base). Lecciones: L-016, L-017, L-018.

  **RED** — 19/10/2026, antes de crear `0006`:
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_rls_grupos.py -q
  10:36:36
  E psycopg.errors.UndefinedTable: relation "grupo_de_reparto" does not exist
  7 failed, 11 errors in 3.90s
  ```
  **Mutante de la FK (L-018)** — copia previa en `backend/.pytest_cache/bloque_b/0006_original.py`;
  diff temporal al final de `upgrade()` (revertido desde la copia antes del verde):
  ```diff
  +    op.drop_constraint("fk_grupo_unidad_unidad", "grupo_unidad", type_="foreignkey")
  +
  ```
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_rls_grupos.py -k miembro_con_unidad -q
  10:37:42
  E Failed: DID NOT RAISE ForeignKeyViolation
  2 failed, 16 deselected in 4.66s
  ```
  Las dos entradas son UUID de unidades existentes: otro edificio de A y otra administración.
  Además: FK al grupo, duplicados de miembro/clave/Generales, métodos, aislamiento y escritura
  cruzada como app; ciclo `head → 0005 → head` conserva la unidad e inserta un miembro nuevo.

  **GREEN** — mutante revertido, incluidos 3.1 y el guardián:
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_rls_edificio.py tests/integracion/test_rls_grupos.py tests/integracion/test_catalogo_rls.py -q
  10:38:02
  48 passed in 16.14s
  cd backend && date +%T && uv run ruff check . && uv run ruff format --check . && uv run mypy
  10:38:17
  All checks passed! / 168 files already formatted / Success: no issues found in 158 source files
  ```
- [x] 3.3 Migración del modo de coeficientes (D15, D-100, P24): `grupo_de_reparto.modo_de_coeficientes` con su `CHECK` y su `UNIQUE` de cuatro columnas; `grupo_unidad.modo_de_coeficientes` y `coeficiente` nulo, la FK al grupo pasa a `(administracion_id, complejo_id, grupo_id, modo_de_coeficientes)` con `ON UPDATE CASCADE`; los `CHECK` de coherencia (modo propios ⇔ coeficiente presente; propios ⇒ método por coeficiente; "Generales" renormalizado). Tests como `proptech_app`, insertando de verdad (L-018): un miembro con coeficiente en un grupo renormalizado falla; uno sin coeficiente en un grupo propios falla; un miembro con un modo distinto del de su grupo falla por la FK; un grupo propios por superficie falla; `UPDATE` del modo de un grupo con miembros falla (el cascade choca con el `CHECK`); "Generales" con modo propios falla; `downgrade` y `upgrade`. Escenarios: `grupos-de-reparto` › Coeficiente propio en un grupo renormalizado; › Cambiar el modo por SQL con miembros. Lecciones: L-016, L-018.

  **RED** — 19/10/2026, antes de crear `0007`:
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_modo_de_coeficientes.py -q
  10:39:44
  E psycopg.errors.UndefinedColumn: column "modo_de_coeficientes" of relation "grupo_de_reparto" does not exist
  19 failed in 7.50s
  ```
  **Mutante de coherencia (L-018)** — copia previa en `backend/.pytest_cache/bloque_b/0007_original.py`;
  diff temporal al final de `upgrade()` (revertido desde la copia antes del cierre):
  ```diff
  +    op.drop_constraint("ck_grupo_unidad_modo_coeficiente", "grupo_unidad", type_="check")
  +
  ```
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_modo_de_coeficientes.py -k 'incoherente or cambiar_modo_con_miembros' -q
  10:40:58
  E Failed: DID NOT RAISE CheckViolation
  4 failed, 15 deselected in 4.79s
  ```
  FK probada con modos distintos pero miembros de forma válida; cascade probado en ambas
  direcciones, con savepoint y comparación posterior de grupo/miembro/coeficiente/unidad.
  El ciclo `head → 0006 → head → 0006 → head` conserva miembros del esquema anterior;
  se comprueba el relleno renormalizado, el coeficiente nulo y el retiro del default temporal.
  **GREEN del modelo** — antes del mutante, incluidos 3.1, 3.2 y guardián:
  ```text
  cd backend && date +%T && uv run pytest tests/integracion/test_modo_de_coeficientes.py tests/integracion/test_rls_edificio.py tests/integracion/test_rls_grupos.py tests/integracion/test_catalogo_rls.py -q
  10:40:23
  67 passed in 21.01s
  cd backend && date +%T && uv run ruff check . && uv run ruff format --check . && uv run mypy
  10:47:35
  All checks passed! / 170 files already formatted / Success: no issues found in 159 source files
  ```

  **GREEN de cierre del bloque B** — después de revertir el mutante, suite completa una vez:
  ```text
  date +%T && bash infra/ci/test-backend.sh
  10:41:31
  =========== 1091 passed, 1 xfailed, 16 warnings in 339.16s (0:05:39) ===========
  ```
- [x] 3.4 Migración de categorías (D2): `categoria_de_gasto` con clave y nombre únicos por edificio (nombre sin distinguir mayúsculas), `orden` único diferible, `activa`. Tests como `proptech_app`: "limpieza" junto a "Limpieza" falla; el mismo nombre en otro edificio pasa; dos categorías intercambian `orden` dentro de una transacción; una categoría de otra administración no se ve. Escenarios: `categorias-de-gasto` › Nombre repetido (la parte de la base). Lecciones: L-016.

  Evidencia 19/10/2026 (3.4):
  ```text
  RED: cd backend && date +%T; uv run pytest tests/integracion/test_categorias_db.py -q --tb=short
  10:49:30
  E psycopg.errors.UndefinedTable: relation "categoria_de_gasto" does not exist
  7 failed in 5.81s
  GREEN: cd backend && date +%T; uv run pytest tests/integracion/test_categorias_db.py tests/integracion/test_catalogo_rls.py -q --tb=short
  10:49:47
  13 passed in 10.45s
  uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 172 files already formatted / Success: no issues found in 160 source files
  ```
- [x] 3.5 **Tablas de sólo agregar en el paso de roles** (D16, B2, L-018), en `backend/src/proptech_core/compartido/roles.py` (si `main` lo volvió a tocar desde el rebase del 16/10, rebasar antes): `_TABLAS_DE_SOLO_AGREGAR`; `antes()` las saltea al otorgar permisos a la app; `despues()` hace `REVOKE UPDATE, DELETE, TRUNCATE` y `GRANT SELECT, INSERT` sobre cada una. El guardián `tests/integracion/test_catalogo_rls.py` se ajusta: acepta una tabla de la lista sólo con exactamente `SELECT, INSERT` y sólo si su trigger rechaza un `UPDATE` de verdad (caja negra); toda otra tabla con `administracion_id` sigue necesitando los cuatro permisos (L-020). **Rojo** con una tabla de prueba de sólo agregar y el `roles.py` de hoy: después de **dos `up`** (`roles antes`, migraciones, `roles despues`, dos veces), sobre una copia (L-013) con el trigger deshabilitado, `UPDATE` como `proptech_app` pasa; después del arreglo, `UPDATE` y `DELETE` dan "permission denied". Rojo del guardián: una tabla en la lista sin trigger hace fallar el guardián. Escenarios: `configuracion-versionada` › Editar una versión después de otro arranque. Lecciones: L-013, L-016, L-018, L-020.

  Evidencia 19/10/2026 (3.5):
  ```text
  RED: cd backend && date +%T; uv run pytest tests/integracion/test_roles_solo_agregar.py tests/integracion/test_catalogo_rls.py -q --tb=short
  10:51:27
  E Failed: DID NOT RAISE InsufficientPrivilege (UPDATE y DELETE tras dos up, trigger deshabilitado)
  E AssertionError: ['zz_solo_agregar: proptech_app no tiene los permisos SELECT/INSERT/UPDATE/DELETE']
  7 failed, 7 passed in 15.40s
  ```
  Guardián: exige los siete privilegios de tabla, exactamente SELECT/INSERT. Para llegar al
  trigger como app sin confundirlo con la capa de permisos, otorga UPDATE temporal dentro de
  un SAVEPOINT; SET LOCAL ROLE comprueba app sin superusuario/BYPASSRLS, y revierte permiso,
  tenant y filas. Sólo el error P0001 esperado de ese UPDATE cuenta como bloqueo.
  Mutante L-020 sobre copia previa `.atl/bloque-c/guardian.pre-mutante.py` (sin commit):
  ```diff
  -            elif not _app_tiene_los_cuatro_permisos(cur, tabla):
  +            elif tabla in _TABLAS_DE_SOLO_AGREGAR and not _app_tiene_los_cuatro_permisos(cur, tabla):
  ```
  ```text
  cd backend && date +%T; uv run pytest tests/integracion/test_catalogo_rls.py::test_tabla_fuera_de_la_lista_con_solo_select_insert_se_rechaza -q --tb=short
  10:53:03
  E AssertionError: assert [] == ['zz_ordinaria_con_permisos_incompletos: proptech_app no tiene los permisos SELECT/INSERT/UPDATE/DELETE']
  1 failed in 3.68s
  Mutante revertido y comparación byte a byte con la copia previa: idéntica.
  GREEN: cd backend && date +%T; uv run pytest tests/integracion/test_roles_solo_agregar.py tests/integracion/test_catalogo_rls.py tests/integracion/test_roles.py tests/integracion/test_auditoria_tabla.py -q --tb=short
  10:53:12
  60 passed in 85.34s (0:01:25)
  Tras acotar el except a la sentencia UPDATE, nueva corrida del guardián y puertas:
  cd backend && date +%T; uv run pytest tests/integracion/test_catalogo_rls.py -q --tb=short && uv run ruff check . && uv run ruff format --check . && uv run mypy
  10:53:55
  12 passed in 5.64s
  All checks passed! / 173 files already formatted / Success: no issues found in 161 source files
  ```
- [x] 3.6 Migración de la configuración versionada (D2, D3, E4, E9): columnas de R03 y R15, el vencimiento (`dia_de_vencimiento` del 1 al 28, `modalidad_de_vencimiento`, `dia_segundo_vencimiento` y `recargo_segundo_vencimiento` nulos) con los `CHECK` de rango de `parametros.py` y el `CHECK` de coherencia; `UNIQUE` por fecha de vigencia, autor con FK compuesta a `persona`, la tabla en `_TABLAS_DE_SOLO_AGREGAR` (3.5) y trigger que rechaza `UPDATE`, `DELETE` y `TRUNCATE`. `parametros.yaml` y `Parametros` suman el vencimiento (día por defecto, modalidad, rango del recargo), con rojo primero. Tests que **intentan** editar (L-018): `UPDATE`, `DELETE` y `TRUNCATE` como `proptech_app` y como `proptech_migrador` se rechazan y la fila queda igual; dos `INSERT` con la misma fecha en transacciones concurrentes, uno falla; día 0 y 29 fallan; doble sin recargo, único con recargo, segundo día igual al primero, fallan; `downgrade` y `upgrade`. Escenarios: `configuracion-versionada` › Editar una versión por SQL; › Dos pedidos simultáneos (la parte de la base); › Vencimiento incoherente por SQL. Lecciones: L-016, L-018.

  Evidencia 19/10/2026 (3.6):
  ```text
  RED: cd backend && date +%T; uv run pytest tests/integracion/test_configuracion_versionada_db.py tests/unitarios/test_parametros.py tests/unitarios/test_parametros_archivo_del_repo.py -q --tb=short
  10:56:03
  E psycopg.errors.UndefinedTable: relation "configuracion_versionada" does not exist
  E AttributeError: 'Parametros' object has no attribute 'vencimiento'
  41 failed, 45 passed in 7.30s
  RED adicional de coherencia de los defaults:
  cd backend && date +%T; uv run pytest tests/unitarios/test_parametros.py -q -k 'defaults_de_vencimiento' --tb=short
  10:56:33
  E ValidationError: vencimiento / Extra inputs are not permitted
  4 failed, 54 deselected in 0.15s
  ```
  `0009` sigue a `0008`. Se intenta UPDATE/DELETE/TRUNCATE como app (42501) y migrador
  (P0001 con el mensaje del trigger), comprobando la fila completa después de cada intento.
  La base de cada módulo corre dos ciclos completos de roles antes/migraciones/roles despues.
  Dos conexiones y una barrera compiten por la misma vigencia: una confirma y otra da UniqueViolation.
  El rango de parámetros queda en `vencimiento.rango_recargo.{minimo,maximo}`; admite defaults
  dobles completos y rechaza defaults incoherentes. Se actualizaron las fixtures antiguas para
  que el campo nuevo no tape el error que cada test intenta provocar.
  Mutante con copia previa `.atl/bloque-c/configuracion.pre-mutante.py` (sin commit):
  ```diff
  -            RAISE EXCEPTION 'configuracion_versionada no admite % (sólo agregar)', TG_OP;
  +            RETURN NEW;
  ```
  ```text
  cd backend && date +%T; uv run pytest tests/integracion/test_configuracion_versionada_db.py -q -k 'escritura_real and migrador' --tb=short
  10:58:49
  E Failed: DID NOT RAISE RaiseException (UPDATE, DELETE y TRUNCATE)
  3 failed, 27 deselected in 5.29s
  Mutante revertido, idéntico byte a byte a la copia previa.
  GREEN: cd backend && date +%T; uv run pytest tests/unitarios tests/integracion/test_rls_edificio.py tests/integracion/test_rls_grupos.py tests/integracion/test_modo_de_coeficientes.py tests/integracion/test_categorias_db.py tests/integracion/test_configuracion_versionada_db.py tests/integracion/test_catalogo_rls.py -q --tb=short
  10:59:11
  773 passed, 1 warning in 65.24s (0:01:05)
  uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 175 files already formatted / Success: no issues found in 162 source files
  ```
- [x] 3.7 Vocabulario y matriz (D5, D14, E3, E7, B5): `Accion` suma `crear_edificio`, `crear_version_de_configuracion`, `confirmar_sin_saldos_previos`, `configurar_padron` y `ver_configuracion_del_edificio`; `0004` congelada con la lista literal de las acciones del 2a y la migración nueva con su lista literal, sin importar `Accion`; la matriz con el reparto de E3 y la lectura (vecino no); `puede` acepta `complejo_id=None` sólo para `crear_edificio`. Tests: la matriz celda por celda para los cinco perfiles, incluidas las acciones del 2a; cada otra acción con `None` se niega; una base vacía con `upgrade head` deja `accion_de_auditoria` igual a `{a.value for a in Accion}` (rojo: con el 0004 de hoy, la migración nueva choca con la clave primaria); el arranque real con las migraciones nuevas no frena por D-2 (ninguna FK hacia `auditoria`). Escenarios: `autorizacion-por-rol` › La matriz completa. Lecciones: L-016.

  Evidencia 19/10/2026 (3.7):
  ```text
  RED: cd backend && date +%T; uv run pytest tests/unitarios/acceso/test_permisos.py tests/integracion/test_vocabulario_configuracion.py -q --tb=short
  11:01:21
  E ValueError: 'crear_edificio' is not a valid Accion
  E AssertionError: 0004_auditoria.py importa el vocabulario vivo
  64 failed, 106 passed, 1 warning in 7.36s
  RED D14: después de sumar enum, matriz y 0010, antes de congelar 0004:
  cd backend && date +%T; uv run pytest tests/integracion/test_vocabulario_configuracion.py::test_base_vacia_con_upgrade_head_y_arranque_real -q --tb=short
  11:01:49
  E psycopg.errors.UniqueViolation: duplicate key value violates unique constraint "pk_accion_de_auditoria"
  E DETAIL: Key (nombre)=(crear_edificio) already exists.
  1 warning, 1 error in 3.58s
  ```
  `0004` conserva sólo sus once acciones literales; `0010` tiene sus cinco literales propias.
  Ninguna importa Accion ni usa ON CONFLICT. Se verifica igualdad exacta enum/base desde cero,
  downgrade a 0004 y upgrade, ninguna FK hacia auditoria, y lifespan real como proptech_app.
  Matriz escrita a mano: 16 acciones × 5 perfiles, más 80 casos con complejo_id=None.
  Mutante con copia previa `.atl/bloque-c/permisos.pre-mutante.py` (sin commit):
  ```diff
  -    if complejo_id is None and accion is not Accion.CREAR_EDIFICIO:
  -        return False
  +    if complejo_id is None:
  +        return True
  ```
  ```text
  cd backend && date +%T; set -o pipefail; uv run pytest tests/unitarios/acceso/test_permisos.py -q -k 'sin_complejo' --tb=no | tail -n 4
  11:03:08
  FAILED test_sin_complejo_solo_crear_edificio_para_titular[vecino-ver_configuracion_del_edificio]
  79 failed, 1 passed, 87 deselected in 0.11s
  Mutante revertido, idéntico byte a byte a la copia previa.
  GREEN: cd backend && date +%T; uv run pytest tests/unitarios/acceso/test_permisos.py tests/integracion/test_vocabulario_configuracion.py tests/integracion/test_auditoria_transaccion.py -q --tb=short
  11:03:24
  176 passed, 1 warning in 10.61s
  uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 177 files already formatted / Success: no issues found in 163 source files
  ```

  Cierre del bloque C, una corrida completa:
  ```text
  date +%T; bash infra/ci/test-backend.sh > .atl/bloque-c/backend-completo.log 2>&1
  11:03:45
  =========== 1270 passed, 1 xfailed, 16 warnings in 317.85s (0:05:17) ===========
  ```
  El xfail es el existente de F2c, con dueño cambio 7 (test_zz_rompedor_v3_agotada_con_efecto).

## 4. Dominio puro

- [x] 4.1 **R01 en `compartido`** (D4, D10, B1, D-082): primero el test de fronteras, `test_compartido_no_importa_complejos` y que `compartido` no importe ningún módulo de dominio, en `tests/unitarios/test_fronteras_de_modulos.py`, con su **rojo** sobre una copia con un import de `complejos` agregado a `compartido` (L-013). Después, sin base: el tipo `Coeficiente` (texto decimal ASCII, hasta 6 decimales, `fullmatch`) y la función pura en `compartido/coeficientes.py`: suma y diferencia en `Decimal`, estado `ok`, `advertencia` (bordes 0,9999 y 1,0001 incluidos) o `fuera_de_tolerancia` (0,9998, 1,0002, cero unidades); rechazo de `float` en la entrada; con pruebas de propiedades (para cualquier conjunto de coeficientes válidos, el estado coincide con la distancia a 1 calculada en `Decimal`). La misma función informa un grupo con coeficientes propios. Escenarios: `grupos-de-reparto` › Suma exacta; › Borde inferior de la tolerancia; › Borde superior de la tolerancia; › Fuera de tolerancia; › Edificio sin unidades; › Grupo con coeficientes propios que no suman 1. Lecciones: L-008, L-009, L-013, L-019.

  EVIDENCIA (L-013: copia propia en `.evidencia-d/4_1`, no el árbol real; eliminada después):
  ```diff
  --- compartido/__init__.py (original)
  +++ compartido/__init__.py (copia)
  @@ -0,0 +1,2 @@
  +
  +from proptech_core import complejos
  ```
  ```text
  $ date +%T; cd backend && uv run pytest -q ../.evidencia-d/4_1/tests/unitarios/test_fronteras_de_modulos.py -k 'no_importa_complejos or ningun_modulo'
  11:11:03
  E AssertionError: {'complejos': ['proptech_core/compartido/__init__.py']}
  2 failed, 1 passed, 2 deselected in 0.23s
  $ date +%T; cd backend && uv run pytest -q tests/unitarios/test_coeficientes.py
  11:11:30
  E ModuleNotFoundError: No module named 'proptech_core.compartido.coeficientes'
  42 failed in 0.24s
  $ date +%T; cd backend && uv run pytest -q tests/unitarios/test_coeficientes.py tests/unitarios/test_fronteras_de_modulos.py
  11:11:49
  47 passed in 0.44s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 179 files already formatted / Success: no issues found in 165 source files
  ```
  JUICIO: bordes inclusivos, diferencia con signo, cero unidades, grupos propios y 2000 conjuntos
  generados con semilla reproducible; suma y distancia calculadas con Decimal. Sin dependencias nuevas.


## 5. Casos de uso, contra PostgreSQL real como `proptech_app`

- [x] 5.1 Crear un edificio (D3, D9, D10, E4): copia los parámetros recibidos (no relee el disco) o toma la configuración inicial del alta, crea la primera versión vigente desde hoy, las categorías, "Generales", estado `pendiente`, todo en una transacción con su auditoría. Tests: valores por defecto completos (incluido el vencimiento único el día por defecto); con configuración inicial en el alta, la primera versión la tiene y no hace falta otra; con otros parámetros pasados al caso de uso, el primer edificio no cambia; una falla a mitad (forzada) no deja nada, ni la auditoría. Escenarios: `edificios-y-unidades` › Edificio nuevo con los valores del archivo; › Edificio nuevo con la configuración de su reglamento; › Cambiar el archivo no toca edificios existentes; `auditoria-de-acciones` › Crear un edificio queda auditado. Lecciones: L-016.

  EVIDENCIA:
  ```text
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_crear_edificio.py
  11:13:05
  E AttributeError: module 'proptech_core.complejos.aplicacion.escritura' has no attribute 'crear_edificio'
  3 failed in 8.95s
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_crear_edificio.py tests/integracion/test_auditoria_transaccion.py
  11:14:53
  9 passed in 16.30s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 182 files already formatted / Success: no issues found in 168 source files
  ```
  JUICIO: parámetros recibidos, configuración inicial, categorías propias, Generales, autor y
  auditoría en una transacción/savepoint. La falla forzada comprueba primero que la auditoría se
  escribió y después verifica cero filas en las cinco tablas afectadas, como proptech_app.
  HALLAZGO: el barrido de acciones sensibles ahora verifica sin commit y revierte: confirmar una
  acción nueva impedía su downgrade final por la FK del vocabulario (D14), como está previsto.

- [x] 5.2 Unidades: alta y edición con `Coeficiente`/`Superficie` desde texto, identificador repetido como conflicto, sin poder cambiar de edificio; el informe de R01 de 4.1 en la respuesta del padrón. Tests: alta válida; "1A" repetida en el mismo edificio y en otro; editar con otro `complejo_id` se rechaza; una unidad de otra administración no se encuentra; un alta que deja la suma fuera de tolerancia se guarda igual y lo informa. Escenarios: `edificios-y-unidades` › Alta de unidad válida; › Identificador repetido; › Mismo identificador en otro edificio; › Mover una unidad por la API; › Unidad de otra administración; `grupos-de-reparto` › Fuera de tolerancia. Lecciones: L-017.

  EVIDENCIA:
  ```text
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_unidades_casos_de_uso.py
  11:16:03
  E ImportError: cannot import name 'unidades' from 'proptech_core.complejos.aplicacion'
  9 failed in 9.71s
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_unidades_casos_de_uso.py tests/integracion/test_crear_edificio.py tests/unitarios/test_coeficientes.py
  11:16:56
  54 passed in 15.94s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 185 files already formatted / Success: no issues found in 171 source files
  ```
  JUICIO: Coeficiente/Superficie desde texto, edición parcial sin cambio de edificio, conflicto de
  identificador traducido desde UniqueViolation y padrón con informe R01. Se guarda la suma parcial.
  El movimiento usa un edificio existente; otra administración e inexistente dan el mismo error.
  SUPUESTO: el identificador admite entre 1 y 40 caracteres; el máximo de 40 se eligió sin
  un límite explícito en la spec.

- [x] 5.3 Grupos (D6, D15): crear y editar un grupo, fijar sus unidades buscándolas dentro del edificio del grupo, con su modo y, si es `propios`, el coeficiente de cada una; cambiar el modo reescribe los miembros en una transacción; "Generales" inmutable; el informe de cada grupo `propios`. Tests: unidad de otro edificio y de otra administración dan el mismo error sin revelar cuál; repetida; cambiar el método de "Generales"; una unidad nueva entra sola en "Generales" (guarda de regresión, rojo sobre una copia, ver design); grupo renormalizado sin coeficientes; grupo propios que suma 0,8 se guarda y se informa `fuera_de_tolerancia`; pasar un grupo de renormalizado a propios con sus coeficientes. Escenarios: `grupos-de-reparto` › Grupo con una unidad de otro edificio; › Grupo con una unidad de otra administración; › Unidad repetida en un grupo; › Cambiar el método de Generales; › Una unidad nueva entra a Generales; › Grupo parcial renormalizado; › Grupo con coeficientes propios que no suman 1; › Cambiar el modo de un grupo. Lecciones: L-017.

  EVIDENCIA:
  ```text
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_grupos_casos_de_uso.py
  11:18:22
  E ImportError: cannot import name 'grupos' from 'proptech_core.complejos.aplicacion'
  11 failed in 11.13s
  ```
  L-013: copia propia de `backend/src` en `.evidencia-d/5_3/src`, luego eliminada;
  el mutante hace que Generales use miembros guardados en lugar de todas las unidades:
  ```diff
           if grupo["es_generales"]:
  -            unidades = generales
  +            unidades = miembros.get(grupo["id"], [])
           else:
  ```
  ```text
  $ date +%T; cd backend && PYTHONPATH=../.evidencia-d/5_3/src uv run pytest -q tests/integracion/test_grupos_casos_de_uso.py -k nueva_unidad
  11:19:39
  E AssertionError: assert [] == [{'unidad_id': ..., 'coeficiente': '0.100000'}]
  1 failed, 10 deselected in 7.92s
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_grupos_casos_de_uso.py tests/integracion/test_unidades_casos_de_uso.py tests/integracion/test_crear_edificio.py tests/unitarios/test_coeficientes.py
  11:19:52
  65 passed in 16.82s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 187 files already formatted / Success: no issues found in 173 source files
  ```
  JUICIO: ajenas existentes de ambos tipos dan exactamente `unidades: valor inválido`, sin grupo
  residual ni cambios de miembros. Generales inmutable y dinámico; modo reemplazado en transacción,
  renormalizado sin informe propio, propios con informe R01 incluso al sumar 0,8; repetidas en conflicto.

- [x] 5.4 Categorías: crear, renombrar, desactivar, reactivar y reordenar con el orden completo. Tests: agregar en A no aparece en B; renombrar en A no cambia B; nombre repetido; orden que omite, repite o trae una categoría de otro edificio no cambia nada. Escenarios: `categorias-de-gasto` › Agregar una categoría; › Renombrar una categoría; › Nombre repetido; › Desactivar; › Reordenar; › Orden incompleto. Lecciones: L-017.

  EVIDENCIA:
  ```text
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_categorias_casos_de_uso.py
  11:20:51
  E ImportError: cannot import name 'categorias' from 'proptech_core.complejos.aplicacion'
  7 failed in 8.00s
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_categorias_casos_de_uso.py tests/integracion/test_categorias_db.py tests/integracion/test_crear_edificio.py
  11:21:34
  17 passed in 21.14s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 189 files already formatted / Success: no issues found in 175 source files
  ```
  JUICIO: altas, renombres, desactivación/reactivación y orden completo (incluye inactivas);
  clave/nombre repetidos son conflictos. Omisión, repetición y categorías ajenas existentes no
  cambian nada. El bloqueo del edificio serializa altas y reordenamientos de sus categorías.

- [x] 5.5 Versiones de configuración y estado de migración: crear una versión (vigencia desde hoy en Mendoza o después, autor, auditoría, vencimiento único o doble), `configuracion_vigente(complejo, fecha)`, y confirmar "sin saldos previos" sólo desde `pendiente`, con auditoría. Tests: cambiar la tasa deja dos versiones y la vieja intacta; pasar a doble vencimiento con día 20 y recargo "5.00" deja la versión anterior única; vigencia de ayer se rechaza; con el reloj fijado a las 23:30 y a las 00:30 de Mendoza, "hoy" es el día de Mendoza; misma fecha dos veces es conflicto y no deja auditoría (el `UniqueViolation` se traduce de forma determinista, sin depender de dos pedidos a la vez); vigente para el 15/11 con versiones del 1/11 y el 1/12; fecha anterior a la primera; confirmar dos veces es conflicto. Escenarios: `configuracion-versionada` › Cambiar la tasa; › Pasar a doble vencimiento; › Dos versiones para el mismo día; › Versión retroactiva; › Vigente para una fecha; › Fecha anterior a la primera versión; `edificios-y-unidades` › Confirmar sin saldos previos; › Confirmar dos veces; `auditoria-de-acciones` › La versión que falla no deja auditoría; › El detalle no trae la tasa. Lecciones: L-016.

  EVIDENCIA:
  ```text
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_versiones_casos_de_uso.py
  11:23:01
  E AttributeError: module 'proptech_core.complejos.aplicacion.lectura' has no attribute 'listar_versiones'
  E AttributeError: module 'proptech_core.complejos.aplicacion.escritura' has no attribute 'crear_version_de_configuracion'
  7 failed in 9.39s
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed! / 190 files already formatted / Success: no issues found in 176 source files
  $ date +%T; cd backend && uv run pytest -q tests/integracion/test_versiones_casos_de_uso.py tests/integracion/test_auditoria_transaccion.py tests/integracion/test_crear_edificio.py
  11:24:33
  16 passed in 20.47s
  ```
  JUICIO: versiones inmutables con autor, doble vencimiento y detalle cerrado sin tasas/recargos;
  vigencia de hoy o futura con reloj inyectado y America/Argentina/Mendoza. A las 23:30 y a las
  00:30 se acepta el día local y se rechaza el anterior. Un observador de SQLAlchemy comprueba
  que la fecha repetida provoca UniqueViolation real, traducido a conflicto sin auditoría.
  La vigente del 15/11 es la del 1/11; antes de la primera no hay configuración. Confirmar sólo
  permite pendiente y audita una vez; repetir o partir de confirmada es conflicto.

  Cierre completo del bloque D:
  ```text
  $ date +%T; bash infra/ci/test-backend.sh
  11:25:12
  =========== 1351 passed, 1 xfailed, 16 warnings in 538.10s (0:08:58) ===========
  ```


## 6. API

- [x] 6.1 Rutas de edificios (D6): listar, crear (con configuración inicial opcional), ver, resumen con estado e informe de R01, confirmar "sin saldos previos". Cada ruta entra en la lista de 2.1 y en el diccionario de cuerpos de 2.2 en el mismo commit. Tests de contrato con identidad inyectada: 401 sin identidad y sin SQL; 422 del cuerpo antes que 404 y 403 (orden de D6); 404 idéntico para inexistente, fuera de alcance y de otra administración; 403 con `permiso_faltante` para colaborador al crear o confirmar; el vecino recibe 403 en el resumen de su edificio y 404 en el de otro; 409; 422 con marcador ausente; alta con `id` rechazada. Escenarios: `edificios-y-unidades` › Alta de edificio con id propio; › Lista de un colaborador; › Un colaborador confirma; › Volver atrás; `autorizacion-por-rol` › Un colaborador crea un edificio; › El vecino pide la configuración de su edificio; › El vecino pide la configuración de otro edificio. Lecciones: L-007, L-017.

  ROJO (rutas todavía ausentes):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_edificios_api.py -q --tb=short
  11:49:41
  E   assert 404 == 200
  21 failed, 1 passed, 1 warning in 6.89s
  ```
  El 404 del GET existente nació verde; mutante temporal y revertido en `finally`:
  ```diff
  - return HTTPException(status_code=404, detail="no encontrado")
  + return HTTPException(status_code=404, detail="mutante")
  ```
  ```text
  $ cd backend && date +%T && uv run python - <<'PY_MUTANTE'
  # cambia el mensaje, ejecuta el nodo siguiente y restaura la copia original en finally
  # uv run pytest 'tests/integracion/test_edificios_api.py::test_404_identico_para_inexistente_fuera_de_alcance_y_ajeno[GET-]' -q --tb=short --show-capture=no
  PY_MUTANTE
  11:50:03
  E   AssertionError: assert {'detail': 'mutante'} == {'detail': 'no encontrado'}
  1 failed, 1 warning in 7.17s
  ```

  VERDE (API, barridos, casos de uso y candado del 2a):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_edificios_api.py tests/integracion/test_rutas_protegidas.py tests/integracion/test_altas_sin_id_del_cliente.py tests/integracion/test_crear_edificio.py tests/integracion/test_versiones_casos_de_uso.py tests/integracion/test_alcance_api.py tests/integracion/test_identidad_api.py -q --tb=short --show-capture=no && uv run ruff check . && uv run ruff format --check . && uv run mypy
  11:52:34
  73 passed, 1 warning in 34.71s
  All checks passed!
  192 files already formatted
  Success: no issues found in 178 source files
  ```

- [x] 6.2 Rutas de unidades y de grupos (D6): alta, edición, lista, miembros con modo y coeficientes. Mismo contrato que 6.1. Tests propios: coeficiente y superficie como número JSON dan 422 sin el valor; `administracion_id` de otra administración en el cuerpo da 422 sin el id; el consejo y el colaborador "ver" reciben 403 al escribir y 200 al leer el padrón; el vecino recibe 403 al pedir el padrón de su edificio y 200 al pedir su unidad por `GET /api/unidades/{id}`. Escenarios: `edificios-y-unidades` › Coeficiente como número; › Coeficiente fuera de forma; › Tipo desconocido; › Alta de unidad con otra administración en el cuerpo; `autorizacion-por-rol` › El consejo edita una unidad de su edificio; › El consejo lee el padrón; › El vecino ve su unidad. Lecciones: L-007, L-008, L-017.

  ROJO (rutas ausentes y respuesta de unidad incompleta):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_padron_api.py tests/integracion/test_alcance_api.py -q --tb=short --show-capture=no
  11:54:39
  E   assert 404 == 201
  36 failed, 4 passed, 1 warning in 13.12s
  ```

  ROJO adicional (alcance de unidad antes del permiso en PATCH):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_padron_api.py::test_vecino_no_edita_unidad_ajena_del_mismo_edificio -q --tb=short --show-capture=no
  11:56:20
  E   assert 403 == 404
  1 failed, 1 warning in 6.73s
  ```
  VERDE (HTTP, barridos, casos de uso de unidades y grupos):
  ```text
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && date +%T && uv run pytest tests/integracion/test_padron_api.py tests/integracion/test_edificios_api.py tests/integracion/test_rutas_protegidas.py tests/integracion/test_altas_sin_id_del_cliente.py tests/integracion/test_alcance_api.py tests/integracion/test_unidades_casos_de_uso.py tests/integracion/test_grupos_casos_de_uso.py -q --tb=short --show-capture=no
  11:57:59
  134 passed, 1 warning in 34.59s
  ```
  Antes del commit, repetidos después del verde:
  ```text
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed!
  193 files already formatted
  Success: no issues found in 179 source files
  ```

- [x] 6.3 Rutas de categorías y de configuración (D6): categorías completas; versiones y vigente por fecha. Tests propios: tasa o recargo como número, `NaN`, fuera de rango, día 29 o con campo de capitalización dan 422; colaborador "editar" crea categoría y no versión (403); colaborador "ver" no crea categoría y sí lee la configuración; un `UniqueViolation` al crear la versión se traduce a 409 (la concurrencia real la prueba 3.6 en la base); no existe ruta para borrar una categoría ni una versión. Escenarios: `configuracion-versionada` › Tasa como número; › Tasa fuera de rango; › Pedido de capitalización; › Día de vencimiento fuera de rango; › Un colaborador cambia la tasa; › Dos pedidos simultáneos; `categorias-de-gasto` › Borrar; `autorizacion-por-rol` › Un colaborador "ver" crea una categoría. Lecciones: L-007.

  ROJO (rutas ausentes):
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_configuracion_api.py -q --tb=short --show-capture=no
  12:00:16
  E   assert 404 == 201
  30 failed, 1 warning in 7.94s
  ```
  ROJO de la ubicación del error antes de mover las validaciones a cada campo:
  ```text
  $ cd backend && date +%T && uv run pytest tests/integracion/test_configuracion_api.py -q --tb=short --show-capture=no
  12:01:49
  E   AssertionError: assert 'tasa_mensual' in ['body']
  E   AssertionError: assert 'dia_segundo_vencimiento' in ['body']
  5 failed, 25 passed, 1 warning in 8.70s
  ```
  La quinta falla era un nombre de categoría de prueba ya precargado; corregido a uno nuevo.


  VERDE (toda la API, barridos y casos de uso afectados):
  ```text
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && date +%T && uv run pytest tests/integracion/test_configuracion_api.py tests/integracion/test_edificios_api.py tests/integracion/test_padron_api.py tests/integracion/test_rutas_protegidas.py tests/integracion/test_altas_sin_id_del_cliente.py tests/integracion/test_versiones_casos_de_uso.py tests/integracion/test_categorias_casos_de_uso.py tests/integracion/test_crear_edificio.py -q --tb=short --show-capture=no
  12:02:37
  179 passed, 1 warning in 38.54s
  ```
  Antes del commit, repetidos después del verde:
  ```text
  $ cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy
  All checks passed!
  194 files already formatted
  Success: no issues found in 180 source files
  ```

## 7. El edificio de ejemplo

- [x] 7.1 Semilla y validador (D9, D10, D15): `estado_migracion: sin_saldos_previos` en `config/semilla/edificio-ejemplo.yaml`; el formato `grupos:` suma `modo` (por defecto `renormalizado`) y el coeficiente de cada miembro si es `propios`; el validador usa la función de R01 de `compartido` (4.1, L-009) para "Generales" y para cada grupo `propios`, valida el estado de migración y la coherencia del modo. Rojo: hoy 0.9999 se rechaza y los campos nuevos dan "campo desconocido". Escenarios: `datos-semilla` › Estado de migración del ejemplo; › La semilla del repositorio es válida; › Coeficientes dentro de la tolerancia; › Coeficientes que no suman 1; › Grupo con coeficientes propios en la semilla; › Tipo de unidad desconocido; › El archivo no tiene datos personales. Lecciones: L-009.

  ROJO (tolerancia, función compartida y campos nuevos):
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/test_semilla_configuracion.py -q --tb=short --show-capture=no
  12:05:35
  E   unidades: los coeficientes deben sumar exactamente 1 (suman 0.999900)
  E   edificio.estado_migracion: Extra inputs are not permitted
  E   assert 0 == 1  # ninguna llamada a la función compartida
  21 failed in 0.33s
  ```
  Formato: estado obligatorio en `edificio.estado_migracion`; grupos parciales con
  `{modo, unidades}` y miembros `{identificador, coeficiente}` para `propios`.
  Las listas de identificadores se conservan como abreviatura renormalizada.

  VERDE (semilla, comando, coeficientes y fronteras):
  ```text
  $ cd backend && date +%T && uv run pytest tests/unitarios/test_semilla_configuracion.py tests/unitarios/test_semilla.py tests/unitarios/test_semilla_comando.py tests/unitarios/test_rompedor_semilla_coeficiente_cero_y_duplicado.py tests/unitarios/test_coeficientes.py tests/unitarios/test_fronteras_de_modulos.py -q --tb=short --show-capture=no && uv run ruff check . && uv run ruff format --check . && uv run mypy
  12:07:18
  89 passed in 1.06s
  All checks passed!
  195 files already formatted
  Success: no issues found in 181 source files
  ```

  Cierre del bloque E, suite completa (salida 0; última línea):
  ```text
  $ date +%T && bash infra/ci/test-backend.sh > backend/.pytest_cache/bloque-e-backend.log 2>&1
  12:07:53
  =========== 1519 passed, 1 xfailed, 16 warnings in 415.99s (0:06:55) ===========
  ```

  Humo del cierre del bloque E, corrido por el orquestador (Codex se quedó sin cuota antes de correrlo):
  ```text
  $ bash infra/ci/humo.sh
  12:17:43
  HUMO OK
  [código de salida: 0]
  ```

- 7.2 **Movida al 3b** por la firma de E1 (Juani, 16/10/2026): sólo la necesita el acceso de desarrollo. Queda el texto como referencia para el propose del 3b. Comando de carga idempotente (D9, E6, E10; se recomienda mover al 3b, ver E1), como `proptech_migrador` con el tenant de la administración de ejemplo fijado a propósito, por los mismos casos de uso que la API. Tests contra PostgreSQL real: primera carga con los conteos esperados (13 unidades) y la auditoría de crear y confirmar; segunda carga igual sin cambios; segunda carga después de cambiar `parametros.yaml` da "ya estaba" (sólo compara lo que sale de la semilla, D-042); dos cargas en paralelo dejan un solo ejemplo; con una unidad editada falla sin escribir y dice qué difiere; otra administración con datos queda idéntica (comparación fila por fila); sin tenant no escribe nada. Escenarios: `datos-semilla` › Primera carga; › Segunda carga igual; › Cambiar los parámetros no hace fallar la carga; › Dos cargas a la vez; › El ejemplo cambió en la base; › Otras administraciones no se tocan. Lecciones: L-006, L-016.

## 8. Cierre

- [ ] 8.1 Corrida de cierre **después de la última vuelta de correcciones** (L-010), en orden y de a uno: `test-backend.sh`, `test-web.sh`, `humo.sh`, con conteos comparados contra 1.1 (L-003) y el commit. Ejercitar el Migration Plan (B3), con comandos y salida: (1) sobre una copia **sin auditoría nueva** (datos del 2a, sin edificios del 3a): `upgrade head`, `downgrade 0004`, `upgrade head`, con conteos iguales y `/api/salud` en 200; (2) sobre una copia **con el ejemplo cargado** (o con un edificio creado por la API, si la 7.2 pasó al 3b): `downgrade 0004` falla en la migración de vocabulario, los conteos quedan iguales, y restaurar el respaldo del 1d tomado antes de subir devuelve la base a su estado anterior. Un clon limpio del commit final levanta con los comandos del README tal cual. Verificación: el informe trae los comandos, la salida y la hora de cada paso. Escenarios: todos (corrida completa). Lecciones: L-003, L-005, L-010.
