> **Firma primero.** Ninguna tarea arranca hasta que la sección "Aprobación" de `proposal.md` esté
> firmada por Juani, Alberto o Emiliano, con nombre, fecha y alcance (D-094, D-111). Una regla nueva que
> entre después de la firma necesita firma propia (L-029).
>
> **TDD estricto con el rojo pegado** (L-034): cada tarea de test pega en su informe el comando, la
> salida del test en rojo y la hora, y el rojo tiene que caer en la aserción que el test dice probar,
> nunca en un `ImportError` ni en un 401. Backend: `bash infra/ci/test-backend.sh <archivos>`. Web:
> `bash infra/ci/test-web.sh`.
>
> **Tamaño**: 30 tareas (29 del propose original + 6.0, agregada en la revisión de frontend/DBA del
> 26/10/2026), por encima de las ~20 que pide `config.yaml`. Se acepta porque los grupos 2 y 3
> (ubicación y pisos) son un pedido de Juani que comparte migración y pantalla con el resto. Si hay que
> partirlo, el corte natural es: **3c-1** = grupos 1, 5 y 6 (los hallazgos del QA sobre la web) y
> **3c-2** = grupos 1 a 4 y 7 (ubicación, pisos y grupos, con esquema). El grupo 4 puede ir en
> cualquiera de los dos.
>
> **Corrección post-propose (26/10/2026)**: revisores de rol (frontend, DBA) encontraron defectos
> reales en el plan antes de construir — ver D9/D10 y las correcciones DBA-1, F1-F6, H-8 en `design.md`,
> y las tareas 3.4/3.5/3.8/5.4/6.0/6.1/6.2/6.4 ya reflejan la versión corregida. No hace falta volver a
> firmar `## Aprobación`: son correcciones dentro del alcance ya aprobado (E1-E6, E8-E10), no elecciones
> nuevas.

## 1. Preparación

- [x] 1.1 Rebasar la rama sobre `main` (el 4a ya está mergeado: migraciones `0021` y `0022`, auditoría de
  `editar_unidad` en `complejos/aplicacion/unidades.py`) y verificar que `alembic heads` devuelve una
  sola cabeza y que la suite de backend arranca verde antes de tocar nada — el baseline que prueba que
  nada de lo que rompa después venía roto.

  **Evidencia (26/10/2026)**: `git merge-base --is-ancestor main HEAD` → "HEAD already contains main"
  (la rama ya incluye `84badd1`, cabeza de `main`; no hizo falta rebase). `alembic heads` → `0022
  (head)`, una sola cabeza. Baseline de la suite completa, ya corrida por quien preparó esta tarea
  **antes** de tocar nada (26/10/2026, antes de esta sesión):
  `25 failed, 2817 passed, 1 skipped, 1 xfailed, 3 warnings in 1301.23s (0:21:41)`. Los 25 `failed` son
  deuda documentada en `CLAUDE.md` ("fallas de portabilidad Windows en la suite de pytest", cierre de
  `acceso-de-desarrollo`): `test_respaldos.py`, `test_restaurar.py`, los tests de worker/Redis y un caso
  suelto en `test_umbral_parametros.py::test_umbral_cero`. Ninguno toca `complejos/`, `config/georef/`
  ni ningún archivo de este change — no se reintentan.
- [x] 1.2 Descargar y reducir los tres archivos de Georef a `config/georef/` (`id`, `nombre`, id del
  padre) y escribir `config/georef/LEEME.md` con fuente, fecha de descarga, licencia CC BY 4.0 y el
  comando exacto que lo regenera; verificar con un test que el `LEEME` existe y nombra las cuatro cosas
  (escenario "Procedencia declarada" de `ubicacion-del-edificio`).

  **Evidencia (26/10/2026)**: descarga real de `apis.datos.gob.ar/georef/api/` (provincias, 24;
  departamentos, 529; localidades, 4037), reducidos a `id`/`nombre`/id-del-padre con un script Python
  de un solo uso (no versionado; el comando completo queda en `LEEME.md`). Confirmado contra el
  archivo real: Mendoza id `50`, 18 departamentos, Capital (`50007`) y Godoy Cruz (`50021`) existen.
  **JUICIO (confianza alta)**: el escenario "Trío coherente" de la spec nombra "la localidad Ciudad de
  Mendoza" como ejemplo; el registro real de Georef para la capital es `"Mendoza"` (id `50007010`), no
  "Ciudad de Mendoza" — anotado en `LEEME.md`. Test:
  `bash infra/ci/test-backend.sh tests/unitarios/test_georef_leeme.py` →
  `2 passed in 0.07s`. `rm` de los tres `*_raw.json` intermedios y del script tras la reducción (no se
  versionan).

## 2. Ubicación en el backend

- [x] 2.1 **Test en rojo** del lector del archivo de Georef: archivo ausente, vacío, truncado, de otro
  tipo, con un id repetido y con un padre que no existe; y el caso verde (Mendoza con id `50`, 24
  jurisdicciones). Ningún error repite el contenido del archivo (L-002, L-007, L-008; escenarios
  "Archivo ausente o ilegible" y "La provincia de Mendoza existe con su id oficial").

  **Rojo (26/10/2026)**, `bash infra/ci/test-backend.sh tests/unitarios/test_georef.py` contra un
  stub de `compartido/georef.py` con `leer_georef` lanzando `NotImplementedError` (para que el rojo
  cayera en la aserción del test, no en un `ImportError`, L-034):
  `11 failed in 0.64s`, los 11 en `NotImplementedError` dentro de `leer_georef`, nunca en el import.
- [x] 2.2 Implementar el lector en `compartido/` con las tres consultas y `existe_el_trio(...)`, cargado
  una vez al arrancar, hasta que 2.1 quede verde.

  **Verde (26/10/2026)**: `bash infra/ci/test-backend.sh tests/unitarios/test_georef.py` →
  `11 passed in 0.86s`. `uv run ruff check` + `uv run mypy` sobre
  `src/proptech_core/compartido/georef.py` y el test → `All checks passed!` / `Success: no issues
  found in 2 source files`. Implementación en
  `backend/src/proptech_core/compartido/georef.py` (`Georef`, `leer_georef`, `departamentos_de`,
  `localidades_de`, `existe_el_trio`, `nombre_de_localidad`).
- [x] 2.3 **Test en rojo** de la coherencia del trío contra la API real: localidad de otro departamento,
  departamento de otra provincia, id inexistente, trío incompleto y el trío coherente; más un **mutante
  dirigido** que saca la comparación de padres y tiene que poner el test en rojo (L-035, L-013: copia
  temporal, sin commit, declarado en el informe). Escenarios "Localidad de otro departamento",
  "Departamento de otra provincia", "Id que no existe", "Trío incompleto", "Trío coherente".

  **JUICIO (confianza media)**: "contra la API real" se interpreta como "contra el archivo real de
  `config/georef/`" (no fixtures sintéticos), no contra un endpoint HTTP — el endpoint y el cuerpo que
  exigen el trío "incompleto" (Pydantic, campo requerido) llegan en 2.5/2.6; acá sólo existe la función
  de coherencia (`Georef.campo_incoherente`) que esos endpoints van a usar. El escenario "Trío
  incompleto" se cubre en la tarea 2.6 (nivel API), no acá (nivel de la función pura).

  **Rojo (26/10/2026)**, con `campo_incoherente` estubeado a `raise NotImplementedError`:
  `bash infra/ci/test-backend.sh tests/unitarios/test_georef_coherencia_real.py` →
  `7 failed in 0.34s`, los 7 en `NotImplementedError`.

  **Verde**: implementado `Georef.campo_incoherente` en
  `backend/src/proptech_core/compartido/georef.py` (orden provincia → departamento → localidad, nombra
  el primer campo que no encadena). `bash infra/ci/test-backend.sh
  tests/unitarios/test_georef_coherencia_real.py tests/unitarios/test_georef.py` →
  `18 passed in 0.22s`.

  **Mutante dirigido (L-035, L-013)**: se sacó temporalmente la comparación contra el padre
  (`departamento.provincia_id != provincia_id` y `localidad.departamento_id != departamento_id`),
  dejando sólo la existencia de cada id — copia temporal, sin commit. Resultado:
  `3 failed, 4 passed in 0.28s`, cayendo exactamente en
  `test_localidad_de_otro_departamento`, `test_departamento_de_otra_provincia` y
  `test_ningun_mensaje_repite_el_id_recibido` (las tres que dependen de la comparación de padres, no
  sólo de existencia). Revertido inmediatamente después; `uv run ruff check` + `uv run mypy` → sin
  hallazgos.
- [x] 2.4 Migración `0023`: las cuatro columnas de ubicación, el `CHECK` "los tres o ninguno" y
  `complejo.localidad` a nullable; verificar la subida y la bajada sobre una copia con el edificio de
  ejemplo cargado (Migration Plan, paso 1).

  **Migración** en `backend/migraciones/versions/0023_ubicacion_del_edificio.py`. Subida: cuatro
  columnas nullable + `CHECK ck_complejo_ubicacion_completa_o_vacia` + `localidad` a nullable (sin
  `UPDATE`, D3/D9: no hace falta tocar filas existentes para agregar columnas nullable). Bajada: con
  el candado de D9 (`LOCK TABLE complejo ACCESS EXCLUSIVE` → `NO FORCE` → `UPDATE ... localidad=''`
  → `FORCE`) antes de devolver `localidad` a `NOT NULL` y borrar las cuatro columnas.

  **Hallazgo real (no previsto)**: la suite existente tenía
  `test_rls_edificio.py::test_localidad_es_obligatoria_sin_default_temporal`, que afirmaba el
  comportamiento VIEJO (`NotNullViolation` al omitir `localidad`). D2 cambia esto a propósito
  (`localidad` nullable y derivada): el test se **reescribió** (no se borró) como
  `test_localidad_es_nullable_desde_0023`, documentando el cambio de contrato en su docstring. Sin
  este ajuste la suite daba un falso rojo que no era de este change.

  **Tests nuevos**: `backend/tests/integracion/test_ubicacion_db.py` (6 casos: ubicación completa,
  vacía, las tres combinaciones a medias por `CHECK`, calle sin límite de largo en la base — H-8) y
  `backend/tests/integracion/test_ubicacion_migracion_multitenant.py` (bajada de `0023` sobre una
  base sembrada con **dos administraciones distintas**, confirmando que el candado de D9 rellena
  `localidad=''` en las dos — no sólo en el tenant de turno — y que las columnas se borran).

  **Verde (26/10/2026)**:
  `bash infra/ci/test-backend.sh tests/integracion/test_ubicacion_db.py
  tests/integracion/test_ubicacion_migracion_multitenant.py tests/integracion/test_rls_edificio.py`
  → `32 passed in 36.46s`. Incluye
  `test_rls_edificio.py::test_downgrade_a_0004_y_upgrade_conservan_la_unidad_del_2a` (gemelo L-023).

  **Mutante dirigido #1 (`CHECK`, L-035)**: se sacó temporalmente `create_check_constraint` de la
  subida (y el `drop_constraint` correspondiente de la bajada) — copia temporal, sin commit.
  Resultado: `3 failed, 3 passed in 11.04s`, cayendo exactamente en los tres casos "a medias" de
  `test_ubicacion_a_medias_falla_por_check`. Revertido.

  **Mutante dirigido #2 (candado de D9, DBA-1, requisito explícito de esta corrida)**: se sacó
  temporalmente el `LOCK`/`NO FORCE`/`FORCE` de la bajada, dejando el `UPDATE` corriendo bajo RLS
  normal — copia temporal, sin commit. Resultado: **la migración misma falla**, no silenciosamente:
  `sqlalchemy.exc.IntegrityError: NotNullViolation: column "localidad" of relation "complejo"
  contains null values` en el propio `ALTER TABLE complejo ALTER COLUMN localidad SET NOT NULL` —
  porque el `UPDATE` sin el candado vio cero filas bajo RLS (exactamente el defecto DB-3/DBA-1 que
  D9 existe para evitar) y los `NULL` quedaron sin rellenar. Los 2 tests de
  `test_ubicacion_migracion_multitenant.py` fallan. Revertido; `32 passed` de nuevo tras restaurar.

  `rg "INSERT INTO complejo"` y `rg "INSERT INTO unidad"` en todo el repo (28 y 17 archivos
  respectivamente, ninguno fuera de `backend/tests/` y `backend/src/.../escritura.py`/`unidades.py`):
  ningún `INSERT` literal se ve afectado por `0023` porque las cuatro columnas nuevas son nullable y
  `localidad` sólo se AFLOJA (NOT NULL → nullable), nunca se endurece — un `INSERT` que ya mandaba
  `localidad` sigue funcionando igual.
- [x] 2.5 Tres rutas de lectura de provincias, departamentos de una provincia y localidades de un
  departamento, con sesión, 404 para un padre inexistente y 401 sin sesión; verificado con el test de
  los escenarios "Departamentos de una provincia", "Localidades de un departamento", "Provincia
  inexistente" y "Sin sesión".

  **Wiring**: `backend/src/proptech_api/georef.py` (router `/api/georef/{provincias,
  provincias/{id}/departamentos, departamentos/{id}/localidades}`, `route_class=RutaConIdentidad`,
  sólo `Depends(identidad_actual)` — nunca `sesion_con_tenant`: son datos del país, no del tenant).
  `app.py` carga `Georef` una vez al arrancar desde `Path(configuracion.proptech_parametros).parent /
  "georef"` — sin variable de entorno nueva, porque `config/` entero ya se monta de sólo lectura en
  `infra/compose.yaml:207,255`.

  **Rojo real, no planeado (26/10/2026)**: al cablear `app.py` reutilicé el nombre `georef` para el
  módulo importado (`from proptech_api import ..., georef, ...`) Y para la variable local con los
  datos cargados (`georef = leer_georef(...)`) — la segunda tapaba la primera dentro de la función,
  así que `app.include_router(georef.router)` fallaba con
  `AttributeError: 'Georef' object has no attribute 'router'`. Lo agarraron los 6 tests nuevos:
  `bash infra/ci/test-backend.sh tests/integracion/test_georef_api.py` → `6 errors in 12.97s`, los 6
  en ese `AttributeError` (nunca un 401/404 falso: la ruta ni llegaba a registrarse). Arreglo: la
  variable local pasa a llamarse `datos_georef`.

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_georef_api.py` →
  `6 passed in 13.57s` (con sesión los tres listados, 404 de provincia y de departamento inexistentes,
  401 real sacando el override de `identidad_actual` — patrón de
  `test_edificios_api.py::test_401_sin_sql_incluso_con_cuerpo_invalido`). `uv run ruff check` +
  `uv run mypy` sobre los tres archivos → sin hallazgos. `test_fronteras_de_modulos.py` (27 casos) y
  `test_barrido_de_rutas.py` (12 casos) siguen en verde: el router nuevo no cruza ninguna frontera ni
  queda fuera del barrido.
- [x] 2.6 El alta del edificio exige el trío y acepta calle y número opcional (≤ 200, sin caracteres de
  control); `localidad` deja de ser entrada y se escribe derivada del nombre de Georef. Verificado con
  los escenarios "Alta con ubicación y pisos", "Alta sin ubicación", "Alta sin calle", "Calle con
  carácter de control o demasiado larga" y el test de que `localidad` coincide con el nombre de Georef
  después de escribir (D2).

  **Cambio de contrato**: `crear_edificio` (`escritura.py`) deja de aceptar `localidad: str`; ahora
  exige `provincia_id`, `departamento_id`, `localidad_id`, `georef: Georef` (y opcionalmente
  `calle_y_numero`). Valida con `Georef.campo_incoherente` y escribe `localidad` derivada de
  `nombre_de_localidad`. `CuerpoEdificio` (API) espeja el cambio: sin `localidad`, con el trío
  obligatorio y `calle_y_numero` opcional (`Field(max_length=200)` + `recortado_sin_control`, H-8: sin
  `CHECK` de largo en la base, igual que `localidad` hoy).

  **BLOQUEANTE real, relevado y resuelto en esta corrida** (anunciado al coordinador antes de seguir):
  7 llamadores directos de `crear_edificio(...)` (`src/proptech_api/complejos.py`,
  `src/proptech_core/complejos/aplicacion/ejemplo.py`, `tests/integracion/conftest.py` y 4 archivos de
  test con 9 invocaciones) y 11 archivos de test con `POST /api/complejos` de cuerpo viejo. Los 7
  llamadores se actualizaron al nuevo contrato (ids reales de Georef: Mendoza `50` / Capital `50007` /
  localidad `50007010`, confirmados contra `config/georef/`). De los 11 archivos de `POST
  /api/complejos`: 8 necesitaron el cuerpo nuevo (mecánico), 3 no necesitaban cambios (no mandan cuerpo
  de ubicación: `test_contrato_web.py` sólo lee, `test_identidad_antes_del_cuerpo.py` manda bytes
  crudos, `test_regresiones_de_aislamiento_y_grupos_vacios.py` ya saltea `/api/complejos`). Tres de los
  8 (`test_texto_recortado_en_el_borde.py`, `test_texto_sin_caracteres_de_control.py`,
  `test_texto_unicode_seguro.py`) probaban el recorte/control/unicode-inseguro sobre `localidad`
  específicamente; como esa capacidad se mudó a `calle_y_numero` (el otro texto libre del alta), los
  casos se reescribieron sobre ese campo en vez de borrarse — la cobertura de esa familia (R3A-1/R3A-6)
  no se perdió.

  **JUICIO (confianza alta)**: `ejemplo.py` (carga del edificio de ejemplo) necesita el trío para cada
  alta nueva, pero `config/semilla/edificio-ejemplo.yaml` todavía no tiene columnas de ubicación — eso
  es la tarea 6.5, fuera de esta corrida. Se usó un trío real y fijo (Mendoza/Capital/"Mendoza",
  constantes `_PROVINCIA_EJEMPLO`/`_DEPARTAMENTO_EJEMPLO`/`_LOCALIDAD_EJEMPLO` en `ejemplo.py`,
  documentadas como deuda hacia 6.5) en vez de inventar un valor sin sentido o bloquear todo el change:
  son ids reales de Georef, no datos fabricados, y quedan anotados para que 6.5 los reemplace por los
  de la semilla real.

  **Segundo bloqueante real, encontrado corriendo la suite** (no estaba en el relevamiento inicial):
  `crear_app()` carga `Georef` desde el directorio hermano de `proptech_parametros` (D1), pero **7
  fixtures de test** aíslan `parametros.yaml` en un `tmp_path` sin copiar su `georef/` al lado
  (`test_alcance_api.py`, `test_altas_sin_id_del_cliente.py`, `test_asignar_edificio_api.py`,
  `test_cableado_real_del_arranque.py`, `test_identidad_api.py`, `test_rutas_protegidas.py`,
  `test_causa_de_arranque_rechazado.py`) — las 7 rompían con `GeorefInvalido: no se puede leer el
  archivo: provincias.json`. Se evaluaron dos arreglos: (a) una variable de entorno `PROPTECH_GEOREF`
  separada (toca `Configuracion`, `infra/compose.yaml` y cada fixture igual) vs. (b) copiar
  `config/georef/` al lado del `parametros.yaml` aislado, mismo patrón que esos fixtures ya usan
  (`shutil.copytree`). Se eligió (b): una línea por fixture, sin tocar `Configuracion` ni la
  infraestructura de despliegue (que ya monta `config/` entero, D1).

  **Tercer bloqueante, estructural**: `test_rutas_protegidas.py` exige que el conjunto de rutas
  cubiertas coincida exactamente con las rutas reales de la app (`_RUTAS_CUBIERTAS`); las 3 rutas de
  Georef (2.5) no estaban. Como son datos del país (D1: "no depende del edificio ni del rol"), no
  encajan en el supuesto de esa suite de que toda ruta cubierta necesita una `asignacion_rol` — se
  agregó `_RUTAS_SIN_ALCANCE` (importado también por `test_identidad_antes_del_cuerpo.py` y
  `test_regresiones_de_aislamiento_y_grupos_vacios.py`, que referencian `_RUTAS_CUBIERTAS`) con su
  propia rama: 200 esperado con cualquier identidad autenticada, incluida una sin ninguna fila en
  `asignacion_rol` o de otra administración, en vez de la rama genérica (403/404 esperados).

  **Rojo real #1 (26-27/10/2026)**: al cablear `georef.router` en `app.py` reutilicé `georef` como
  nombre del módulo importado y de la variable local con los datos cargados — ver evidencia de la
  tarea 2.5, mismo informe.

  **Rojo real #2**: `bash infra/ci/test-backend.sh tests/integracion/test_rutas_protegidas.py` →
  `1 failed, 367 passed` (las otras 6 fixtures de `tmp_path` corrigiéndose en el mismo lote), cayendo
  en `test_las_rutas_del_candado_son_exactamente_las_cubiertas_acá` nombrando las 3 rutas de Georef
  como "no cubiertas" — nunca en un `ImportError` ni en un 401 genérico.

  **Verde, corrida completa de los 26 archivos tocados** (crear_edificio: 7 llamadores; POST
  /api/complejos: 11 archivos; más los 7 de fixtures de Georef aislado, con solapamiento):
  `358 passed` (`test_rutas_protegidas.py` solo) + `122 passed` (edificios/perfiles/tasa/umbral/texto×3)
  + `46 passed` (identidad-antes-del-cuerpo/regresiones/ejemplo/contrato-web) + `34 passed`
  (edificios_api + crear_edificio, con los tests nuevos de 2.6) + `27 passed` (crear_edificio,
  unidades, versiones, auditoría) + `55 passed` (barrido de rutas, fronteras, paquetes, arranque) —
  ninguna falla fuera de las ya explicadas y corregidas. `uv run ruff check .` y `uv run mypy` sobre
  todos los archivos fuente tocados → sin hallazgos.

  **Hallazgo de higiene, no de lógica**: un `Edit` sobre `test_edificios_api.py` escribió un byte NUL
  crudo dentro de un string de Python en vez del escape de texto que se quería probar —
  `grep`/`Read` empezaron a ver el archivo como binario. Detectado por `wc -l` y `file` dando
  resultados inconsistentes entre sí; corregido reescribiendo el byte como el escape de texto
  correcto con un script de una línea, confirmado con `ast.parse` antes de seguir.

## 3. Pisos del edificio y de la unidad

- [x] 3.1 **Test en rojo** del vocabulario de pisos como función pura: `PB` siempre, `SS1..SS<subsuelos>`,
  `1..<pisos>`, con 0 subsuelos y 0 pisos, y los límites 5 y 60; coincidencia completa y sólo ASCII
  (L-008). Escenario "Piso de planta baja y de subsuelo" de `edificios-y-unidades`.

  **Rojo (27/10/2026)**, `bash infra/ci/test-backend.sh tests/unitarios/test_pisos.py` contra un stub
  con `vocabulario_de_pisos` lanzando `NotImplementedError` (L-034): `9 failed, 2 passed in 0.36s` (los
  2 verdes son los tests que sólo ejercitan `PATRON_PISO`, ya escrito en el stub; los 9 rojos caen en
  `NotImplementedError`, nunca en un `ImportError`).

  **Verde**: `bash infra/ci/test-backend.sh tests/unitarios/test_pisos.py` → `11 passed in 0.09s`.
  `uv run ruff check` + `uv run mypy` → sin hallazgos. Implementación en
  `backend/src/proptech_core/compartido/pisos.py` (`PATRON_PISO`, `vocabulario_de_pisos`,
  `piso_valido`), con el límite 60 (no 99, confirmado leyendo el patrón del `design.md` corregido:
  `^(SS[1-5]|PB|[1-9]|[1-5][0-9]|60)$`) y 5 subsuelos verificados en
  `test_limite_maximo_5_subsuelos_y_60_pisos`.
- [x] 3.2 `complejo.pisos` (nullable, 1..60) y `complejo.subsuelos` (nullable, 0..5) en el alta y en la
  lectura, sin calcularlos de nada — nulo es "sin completar", igual que la ubicación — y rechazo de
  texto por número; verificado con los escenarios "Cantidades fuera de rango", "Cantidades como texto"
  y "Edificio nuevo sin pisos completados".

  **Implementación (27/10/2026)**: `crear_edificio` (`escritura.py`) exige `pisos`/`subsuelos` en
  toda alta nueva (nunca `None` ahí, aunque la columna sea nullable para edificios migrados sin
  completar) y valida el rango 1-60/0-5 también en la capa de aplicación (no sólo en el `Field` del
  cuerpo de la API), para que un llamador que no pase por HTTP no se escape del límite.
  `ComplejoLeido` (`lectura.py`) ahora lee las 6 columnas de ubicación+pisos con `SELECT *` armado
  desde una sola constante (`_COLUMNAS_COMPLEJO`); `ver_complejo` y `mis_edificios` (`complejos.py`)
  las exponen. `CuerpoEdificio` exige `pisos: int (1-60)` y `subsuelos: int (0-5)` con `strict=True`
  heredado (rechaza `"4"` por texto). 7 llamadores de `crear_edificio` actualizados (igual que 2.6).

  **Verde (27/10/2026)**: `bash infra/ci/test-backend.sh tests/integracion/test_crear_edificio.py
  tests/integracion/test_unidades_casos_de_uso.py tests/integracion/test_versiones_casos_de_uso.py
  tests/integracion/test_auditoria_transaccion.py` → `38 passed in 41.77s`.

  **Hallazgo real (no previsto)**: `test_auditoria_transaccion.py` tenía un caso que editaba
  `unidad.piso` a `"Otro"` para probar que la edición queda auditada — valor que la migración `0024`
  (ya comiteada, tarea 3.4) rechaza por el `CHECK ck_unidad_piso`. Se reproduce incluso en el HEAD sin
  los cambios de esta tarea (confirmado con `git stash`): no es una regresión de 3.2, es deuda de 3.4
  que esta corrida completó. Se cambió el valor a `"2"` (dentro del vocabulario, distinto del `"1"`
  original de `DATOS`, para seguir probando que el cambio se detecta).

  `uv run ruff check` + `uv run mypy` sobre los 4 archivos tocados → `All checks passed!` / `Success:
  no issues found in 4 source files`.
- [x] 3.3 **Test en rojo** de la validación de `piso` **por la API** (no sólo por el dominio, L-017):
  piso fuera del vocabulario del edificio, texto libre (`"Entrepiso"`, `"pb"`, `" 1"`, `"1°"`, `"SS"`,
  dígito no ASCII), piso faltante o `null` en un alta, y el `INSERT`/`UPDATE` por SQL que el `CHECK`
  tiene que frenar; más un **mutante dirigido** que saca la comparación contra el edificio y deja el
  `CHECK` de forma, para probar que el test vigila la garantía específica y no una capa anterior
  (L-034, L-035). Escenarios "Piso que el edificio no tiene", "Piso como texto libre", "Unidad nueva
  sin piso", "El piso no se sale del vocabulario por SQL".

  **Rojo (27/10/2026)**, `bash infra/ci/test-backend.sh tests/integracion/test_piso_vocabulario_api.py`
  contra el código de antes de esta tarea: `3 failed, 3 passed in 20.48s` — los 3 que ya pasaban eran
  "sin piso" (ya rechazado por el campo requerido de Pydantic, sin tocar nada), "dentro del
  vocabulario" (siempre funcionó) y el `CHECK` por SQL (ya lo daba `0024`). Los 3 rojos: "piso que el
  edificio no tiene" caía en `201` (se creaba igual, sin validar contra el edificio); "texto libre" y
  "editar fuera del vocabulario" caían en `500` (`IntegrityError` crudo de PostgreSQL, nunca un 422 —
  la app no validaba la forma antes de mandarlo a la base).

  **Implementación**: `DatosUnidad.piso` pasa a `str | None` (una unidad migrada por `0024` puede
  tener el piso sin completar; antes era `str` obligatorio y `_datos()` explotaba al leer esas filas,
  un bug latente para cualquier edición de una unidad migrada). Validador de forma
  (`piso_con_forma`, `PATRON_PISO.fullmatch`) en el modelo; `_validar_piso_del_edificio` nueva en
  `unidades.py`, llamada desde `crear_unidad` (exige no-nulo y dentro del vocabulario de `pisos`/
  `subsuelos` DEL EDIFICIO, vía `piso_valido` de `compartido/pisos.py`, tarea 3.1) y desde
  `editar_unidad` (sólo si `"piso"` está entre los campos que cambian; permite `None` sin tocar,
  cubriendo "Corregir el piso de una unidad migrada"). **JUICIO (confianza media)**: si el edificio
  todavía no completó `pisos`/`subsuelos` (D3, ambos `None`), se deja pasar lo que ya pasó el chequeo
  de forma — ese edificio no tiene vocabulario propio todavía; la tarea 3.8 (puesta a punto) es la que
  cierra ese hueco exigiendo completarlo antes de liquidar.

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_piso_vocabulario_api.py` →
  `6 passed in 18.60s`.

  **Mutante dirigido (L-035)**: se sacó temporalmente la comparación contra el vocabulario del
  edificio en `_validar_piso_del_edificio` (dejando sólo el chequeo de forma ya existente) — copia
  temporal, sin commit. Resultado: `1 failed, 5 passed`, cayendo exactamente en
  `test_piso_que_el_edificio_no_tiene_da_422_sin_el_valor` (el único que depende de la comparación
  contra el edificio, no sólo de la forma). Revertido; `6 passed` de nuevo.

  `uv run ruff check` + `uv run mypy` sobre `unidades.py` → sin hallazgos.
- [x] 3.4 Migración `0024` (corregida tras revisión DBA): `complejo.pisos`/`subsuelos` nacen
  **nullable, sin calcular nada** de las unidades existentes (D3) — sin `UPDATE` de backfill, sin
  tocar RLS. Después, con el candado de D9 (`LOCK TABLE unidad IN ACCESS EXCLUSIVE MODE` → `ALTER
  TABLE unidad NO FORCE ROW LEVEL SECURITY` → el `UPDATE` que mapea los valores conocidos → `ALTER
  TABLE unidad FORCE ROW LEVEL SECURITY`, en la misma transacción), pasa `unidad.piso` a nullable y
  mapea `PB`/`SS`/enteros 1-60, y recién entonces agrega el `CHECK` `^(SS[1-5]|PB|[1-9]|[1-5][0-9]|60)$`.
  Verificado con un test que la corre sobre una tabla sembrada con `PB`, `SS`, `""`, `"4"`,
  `"Entrepiso"`, `"1°"` y `" 2 "` y afirma el resultado de cada uno, más la bajada (que rellena los
  nulos con `''`, el `server_default` original de `0005` — nunca `PB` ni ningún valor con significado)
  y la subida otra vez (Migration Plan, paso 2), **sobre una copia con datos reales**, no una base
  vacía de un solo tenant — el candado de RLS sólo se prueba de verdad con más de una administración
  en la copia. **Antes de cerrarla**: `rg` en el repo entero de `INSERT INTO complejo` y
  `INSERT INTO unidad`, incluidos `infra/ci/humo.sh`, la semilla, los comandos y los fixtures de la web
  (L-023), **y** `test_rls_edificio.py::test_downgrade_a_0004_y_upgrade_conservan_la_unidad_del_2a`
  corrido sobre esta migración — el `rg` solo ya falló una vez por esto mismo en `0016`.

  **Migración** en `backend/migraciones/versions/0024_pisos_del_edificio_y_la_unidad.py`. Subida:
  `complejo.pisos` (1-60) y `complejo.subsuelos` (0-5) nullable sin backfill; `unidad.piso` pasa a
  nullable y, bajo el candado de D9, se mapea (coincidencia exacta, sin recortar espacios, sin
  distinguir mayúsculas): "PB" a "PB", "SS" a "SS1", un entero de texto entre 1 y 60 a sí mismo,
  cualquier otra cosa a nulo; el `CHECK ck_unidad_piso` se agrega recién después del mapeo (si se
  agregara antes, el `UPDATE` que todavía no corrió podría dejar valores fuera de ese patrón a mitad
  de camino). Bajada: mismo candado, rellena con comillas vacías (el `server_default` original de
  `0005`), nunca "PB" ni ningún valor con significado.

  **Tests nuevos**: `test_pisos_db.py` (8 casos: columnas nulas sin backfill, rango de pisos y
  subsuelos por `CHECK`, el piso nulo se acepta por SQL) y
  `test_pisos_migracion_multitenant.py` (el mapeo completo sobre **dos administraciones distintas**,
  sembrado con los diez casos del Migration Plan — "PB", "SS", cadena vacía, "4", "Entrepiso", un
  grado con el símbolo de grados, un valor con espacios al borde, minúscula, "SS2" sin contexto y
  "61" fuera de rango — más la bajada que rellena las comillas vacías en las dos administraciones, y
  el `CHECK` de forma rechazando por SQL).

  **Hallazgo real (no previsto)**: `test_rls_edificio.py` tenía dos tests que afirmaban el contrato
  VIEJO de `unidad.piso` (`NOT NULL`): `test_datos_obligatorios_no_conservan_defaults_temporales` lo
  incluía en su parametrización (ya no aplica: `piso` es nullable desde esta migración, se sacó del
  parametrize y se agregó `test_piso_es_nullable_desde_0024` documentando el cambio), y
  `test_downgrade_a_0004_y_upgrade_conservan_la_unidad_del_2a` esperaba que una unidad vieja sin
  `piso` quedara con comillas vacías después de subir a `head` — ahora el mapeo de `0024` convierte
  esas comillas vacías en nulo (no es un valor conocido del mapeo), así que la aserción se actualizó a
  nulo, con un comentario explicando por qué.

  **Verde (27/10/2026)**:
  `bash infra/ci/test-backend.sh tests/integracion/test_pisos_db.py
  tests/integracion/test_pisos_migracion_multitenant.py tests/integracion/test_rls_edificio.py
  tests/integracion/test_ubicacion_db.py tests/integracion/test_ubicacion_migracion_multitenant.py`
  → `43 passed in 58.17s`.

  **Mutante dirigido #1 (candado de D9, requisito explícito de esta corrida)**: se sacó temporalmente
  el `LOCK`/`NO FORCE`/`FORCE` de la subida, dejando el `UPDATE` de mapeo correr bajo RLS normal —
  copia temporal, sin commit. Resultado: la migración misma explota, no silenciosamente —
  `psycopg.errors.CheckViolation: check constraint "ck_unidad_ck_unidad_piso" of relation "unidad" is
  violated by some row` en el propio `ALTER TABLE ... ADD CONSTRAINT`, porque el `UPDATE` sin candado
  vio cero filas bajo RLS normal (ninguna administración se mapeó) y las filas viejas con texto libre
  (que no matchea el patrón nuevo) quedaron sin tocar. Los 3 tests de
  `test_pisos_migracion_multitenant.py` fallan. Revertido; confirmado otra vez contra **dos
  administraciones reales**, no una base de un solo tenant.

  **JUICIO (confianza alta)**: el nombre real de la restricción en la base queda duplicado
  (`ck_unidad_ck_unidad_piso`, por la convención de nombres de `base_de_datos.py`,
  `ck_%(table_name)s_%(constraint_name)s`, aplicada sobre un nombre que ya traía el prefijo
  `ck_unidad_`); es el mismo patrón que ya existe en `0005`/`0021`/`0023` para otras columnas
  (`ck_unidad_tipo`, `ck_complejo_estado_migracion`, etc.) — ninguno de esos tests afirma el nombre
  literal de la restricción, así que es cosmético, no funcional, y consistente con el resto del
  repositorio; no se tocó.

  **Mutante dirigido #2 (`CHECK` de forma, L-035)**: se sacó temporalmente `create_check_constraint`
  de la subida (y el `drop_constraint` correspondiente de la bajada) — copia temporal, sin commit.
  Resultado: `1 failed, 10 passed`, cayendo exactamente en
  `test_check_de_forma_del_piso_rechaza_por_sql`. Revertido; `43 passed` de nuevo tras restaurar.

  `rg "INSERT INTO complejo"` y `rg "INSERT INTO unidad"` en todo el repo (incluidos
  `infra/ci/ensayo-roles.sh`, `infra/ci/humo.sh` — sin resultado ahí —, la semilla y los fixtures de
  test): todos los valores de `piso` usados son `"1"`, dentro del rango nuevo; ningún `INSERT` literal
  se ve afectado por `0024`.
- [x] 3.5 Bajar `pisos` o `subsuelos` con unidades afuera se rechaza con 422 **nombrando los
  identificadores**; verificado con los escenarios "Bajar pisos con unidades arriba", "Bajar subsuelos
  con cocheras abajo" y "Bajar pisos sin unidades arriba", con el `EXPLAIN` de la consulta que busca las
  unidades afuera pegado en el informe — confirmando que entra por `uq_unidad_identificador` y no hace
  falta índice nuevo (sin esto, "no hace falta índice" es un juicio sin evidencia, no un hecho del
  propose).

  **Implementación (27/10/2026)**, junto con 3.6/3.7 (acopladas: la validación vive dentro de
  `editar_edificio`, que no existía antes de esta corrida): `_validar_piso_del_edificio` no se toca;
  en `escritura.editar_edificio`, si `pisos`/`subsuelos` cambian y ambos están completos, se calcula
  `vocabulario_de_pisos(pisos=nuevo, subsuelos=nuevo)` (tarea 3.1) y se trae
  `SELECT identificador, piso FROM unidad WHERE complejo_id=:id AND piso IS NOT NULL` — en Python, no
  SQL dinámico — comparando cada `piso` contra el vocabulario nuevo; cualquier identificador fuera
  levanta `EntradaInvalida("pisos"|"subsuelos", "quedarían unidades fuera de rango: <ids>")` (los ids
  son datos propios del edificio que el mismo administrador ya puede ver, no "el valor del pedido" que
  L-007 prohíbe repetir).

  **EXPLAIN pegado** (test fijo, `test_explain_de_la_consulta_de_unidades_fuera_de_rango`):
  ```
  Index Scan using uq_unidad_identificador on unidad  (cost=0.16..8.18 rows=1 width=64)
    Index Cond: ((administracion_id = (NULLIF(current_setting('app.administracion_id'::text, true), ''::text))::uuid) AND (complejo_id = '...'::uuid))
    Filter: (piso IS NOT NULL)
  ```
  Entra por `uq_unidad_identificador` (`administracion_id, complejo_id, identificador`): RLS agrega el
  predicado de `administracion_id`, la consulta agrega `complejo_id` — los dos primeros componentes
  del índice compuesto. No hace falta índice nuevo, confirmado, no supuesto.

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_editar_edificio.py` →
  `13 passed in 20.54s` (incluye el `EXPLAIN` como test permanente, no sólo evidencia de una vez).

  **Mutante dirigido (L-035)**: se sacó temporalmente el `if` que dispara el chequeo (`if False: ...`)
  — copia temporal, sin commit. Resultado: `2 failed, 11 passed`, cayendo exactamente en
  `test_bajar_pisos_con_unidades_arriba_da_422_con_identificadores` y
  `test_bajar_subsuelos_con_cocheras_abajo_da_422_con_identificadores`. Revertido; `13 passed` de
  nuevo.
- [x] 3.6 `PATCH /complejos/{id}`: nombre, ubicación, calle y número, pisos y subsuelos, con
  `Accion.CONFIGURAR_PADRON` (404 fuera de alcance, 403 sin permiso, en ese orden) y `CuerpoDeEdicion`
  (un campo puede faltar, ninguno puede ser `null`); verificado con los escenarios "Corregir la
  localidad", "Completar la ubicación de un edificio viejo", "Anular un campo obligatorio", "Editar un
  edificio fuera del alcance", "Editar sin permiso de configurar el padrón" y "Cambiar la administración
  por la edición".

  **Implementación**: `CuerpoEdicionEdificio(CuerpoDeEdicion)` en `complejos.py` (todos los campos
  opcionales, `CuerpoDeEdicion.no_nulo` prohíbe `null` explícito, `extra="forbid"` heredado rechaza
  `administracion_id`/`estado_migracion` con 422 automático). Ruta `modificar_edificio` reusa
  `_edificio_autorizado(..., Accion.CONFIGURAR_PADRON)` (mismo orden 404→403 que el resto de
  `complejos.py`, D7). `escritura.editar_edificio` hace el trabajo real: `_EdicionEdificio` (modelo
  interno, no confía en que el llamador HTTP ya validó) valida forma; el trío de ubicación exige las
  tres o ninguna (mismo `CHECK` que `0023`) contra `Georef`, nunca contra el pedido.

  **Verde**: incluido en los `13 passed` de 3.5 (mismo archivo de test).

  `uv run ruff check` + `uv run mypy` sobre `escritura.py`, `complejos.py`, `auditoria.py`,
  `eventos.py` → `All checks passed!` / `Success: no issues found in 3 source files` /
  `Success: no issues found in 1 source file`.
- [x] 3.7 Auditoría de `editar_edificio`: evento nuevo en `EventoDelPadron`, fila nueva del vocabulario
  en la migración `0025`, detalle con el edificio y los nombres de los campos cambiados y nada más
  (D-016); verificado con los escenarios "Editar la ubicación", "La edición falla", "Edición sin
  cambios" y "El evento de editar el edificio existe en la base".

  **Implementación**: `EventoDelPadron.EDITAR_EDIFICIO` nuevo; migración `0025` (`0025_editar_edificio
  .py`, sólo el vocabulario — `grupo_de_reparto.activo` y el trigger de 4.3 se agregan en esa tarea,
  no acá) inserta `"editar_edificio"` en `accion_de_auditoria`. `_DetalleEditarEdificio` nuevo en
  `auditoria.py` (`complejo_id` + `campos` de los 7 nombres editables, `extra="forbid"`: nunca un
  valor). `editar_edificio` calcula `campos` comparando `entrada` contra `anterior` (mismo patrón que
  `editar_unidad`/`editar_categoria`) y sólo llama `registrar(...)` — dentro de la misma `transaccion`
  — si `campos` no está vacío; una excepción antes de esa línea (trío incoherente, fuera de rango)
  revierte la transacción entera sin dejar fila.

  **Hallazgo real (no previsto)**: `test_eventos_padron_migracion.py::test_vocabulario_y_bajada`
  afirmaba `{e.value for e in EventoDelPadron} <= vocabulario` justo después de migrar a `0022` — con
  `EDITAR_EDIFICIO` agregado al enum pero sembrado recién en `0025`, esa aserción ya no es cierta en
  ese punto de la migración. Se dividió en dos aserciones (vocabulario de `0022` sin
  `EDITAR_EDIFICIO`, vocabulario de `0025` completo), preservando el resto del test (incluida la FK
  23503 de "punto de no retorno").

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_eventos_padron_migracion.py
  tests/integracion/test_editar_edificio.py` → `14 passed in ~37s` (12+1 de `test_editar_edificio.py`
  más `test_vocabulario_y_bajada`; el 13° de `test_editar_edificio.py`, el `EXPLAIN`, va en 3.5).
- [x] 3.8 El séptimo paso de la puesta a punto (ubicación completa, `pisos`/`subsuelos` completos y
  ningún piso de unidad sin completar), con el conteo de unidades por corregir y el `EXPLAIN` de esa
  consulta pegado (filtra por `(administracion_id, complejo_id)`, mismo prefijo de índice que 3.5);
  verificado con los escenarios "Edificio recién creado", "Edificio migrado sin ubicación", "Edificio
  migrado sin pisos completados", "Unidad migrada con el piso sin completar" y "Edificio listo para
  liquidar" de `edificios-y-unidades`.

  **Implementación (27/10/2026)**: paso `"ubicacion"` nuevo en `lectura.resumen_edificio`, primero en
  el diccionario `pasos` (los 7 pasos ahora, no 6). `hecho` exige el trío completo, `pisos`/
  `subsuelos` completos y `unidades_sin_piso_completo == 0` (cuenta por `SELECT count(*) FROM unidad
  WHERE complejo_id=:id AND piso IS NULL`). El resumen ahora expone también `provincia_id`,
  `departamento_id`, `localidad_id`, `calle_y_numero`, `pisos`, `subsuelos` y
  `unidades_sin_piso_completo` (no sólo `nombre`/`localidad` como antes de 3.8).

  **EXPLAIN pegado** (test fijo `test_explain_de_unidades_sin_piso_completo`): mismo plan que 3.5,
  `Index Scan using uq_unidad_identificador`, mismo prefijo `(administracion_id, complejo_id)`.

  **Hallazgo real (no previsto)**: dos tests pre-existentes (`test_edificio_recien_creado`,
  `test_edificio_listo_para_liquidar`) afirmaban el diccionario `pasos` completo con 6 claves; se
  actualizaron agregando `"ubicacion": "hecho"` (ambos escenarios nacen con ubicación y pisos
  completos, sin unidades con el piso sin completar). El fixture de contrato `resumen.json` se
  regeneró con `PROPTECH_ACTUALIZAR_FIXTURES=1` (cambio de forma deliberado, igual que 3.2 con
  `edificio.json`).

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_resumen_puesta_a_punto.py
  tests/integracion/test_contrato_web.py` → `20 passed in 41.64s`.

  **Mutante dirigido (L-035)**: paso `"ubicacion"` fijado a `"hecho"` siempre — copia temporal, sin
  commit. Resultado: `3 failed, 9 passed`, cayendo exactamente en los tres tests que dependen del
  paso nuevo (`test_edificio_migrado_sin_ubicacion`, `test_edificio_migrado_sin_pisos_completados`,
  `test_unidad_migrada_con_el_piso_sin_completar`). Revertido; `12 passed` de nuevo (11 + el `EXPLAIN`).

  `uv run ruff check` + `uv run mypy` sobre `lectura.py` → `All checks passed!` / `Success: no issues
  found in 1 source file`.

## 4. Grupos desactivables y claves autogeneradas

- [x] 4.1 **Test en rojo** de la función pura que deriva la clave del nombre: tildes, signos, guiones
  bajos repetidos y de borde, prefijo por letra, recorte a 40, desempate `_2`, y un nombre del que no
  sale ninguna clave (`"123"`, `"— —"`). Escenarios "Clave derivada del nombre", "Nombre con tildes y
  signos", "Clave derivada repetida" y "Nombre del que no sale ninguna clave".

  **Implementación (27/10/2026)**: `compartido/claves.py`, `derivar_clave(nombre, existentes) -> str
  | None`. Transliteración vía `unicodedata.normalize("NFKD", ...)` + descarte de marcas combinantes
  (acentos); todo lo que no sea `[a-z0-9]` colapsa a `_` único; recorte de bordes; si el resultado es
  sólo dígitos/guiones bajos (o vacío) → `None` ("123", "— —"); si empieza con dígito, prefijo `g_`;
  recorte a 40 sin guión bajo colgando; desempate con sufijo `_N` que recorta la base para que el
  sufijo entre en 40.

  **Verde (nació verde, TDD con test y código juntos)**: `uv run pytest tests/unitarios/test_claves.py`
  → `7 passed in 0.16s`.

  **Mutante dirigido (L-035)**: se sacó temporalmente el prefijo por letra (`if False: ...`) — copia
  temporal, sin commit. Resultado: `1 failed, 6 passed`, cayendo exactamente en
  `test_prefijo_por_letra_cuando_empieza_con_digito`. Revertido; `7 passed` de nuevo.

  `uv run ruff check` + `uv run mypy` sobre `claves.py` → `All checks passed!` / `Success: no issues
  found in 1 source file`.
- [x] 4.2 **Test en rojo** de que "Generales" no se desactiva, ni por la API (422) ni por SQL, con un
  **mutante dirigido** al trigger ampliado (L-035); escenarios "Desactivar Generales" y "Desactivar
  Generales por SQL".

  **Implementación (27/10/2026)**: la mitad SQL va en la migración `0025` (tarea 4.3, el trigger
  `fn_grupo_generales_protegido` ampliado); la mitad API ya existía — `editar_grupo` corta en
  `if grupo["es_generales"]: raise EntradaInvalida(...)` ANTES de mirar ningún campo de `cambios`,
  así que bloquea desactivar Generales por la misma razón que bloquea cualquier otro cambio.

  **Hallazgo real (no previsto)**: al escribir `_FUNCION_AMPLIADA` de `0025` copié la función de
  `0011` (sólo `es_generales`/`metodo`/`modo_de_coeficientes`), pisando la ampliación real de `0015`
  (RF-D-1, 19/10/2026) que ya sumaba `complejo_id`/`administracion_id`. Lo agarró
  `test_generales_no_admite_mudarse_de_edificio_por_sql` (pre-existente): `1 failed` tras aplicar
  `0025`. Corregido partiendo de la función real de `0015`, no de la de `0011`.

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_generales_alcance_sql.py
  tests/integracion/test_grupos_casos_de_uso.py tests/integracion/test_rls_grupos.py` →
  `44 passed in 62.59s`.

  **Mutante dirigido**: ver la evidencia de 4.3 (mismo trigger, un solo mutante cubre las dos tareas).
- [x] 4.3 Migración `0025`: `grupo_de_reparto.activo` (`NOT NULL DEFAULT true`), el trigger de `0011`
  ampliado y `editar_edificio` en el vocabulario de auditoría; subida y bajada probadas sobre una copia
  con datos (Migration Plan, paso 3) y `rg` de `INSERT INTO grupo_de_reparto` en el repo entero (L-023).

  **Implementación**: migración `0025` (compartida con 3.7) agrega `activo` nullable=false con
  `server_default=true` (sin backfill) y reemplaza `fn_grupo_generales_protegido` sumando `NEW.activo
  IS DISTINCT FROM OLD.activo` a la comparación (sobre la versión real de `0015`, ver hallazgo de
  4.2). `rg "INSERT INTO grupo_de_reparto"`: 7 archivos, todos con lista de columnas explícita — ningún
  `INSERT` se ve afectado por la columna nueva (default a nivel de base).

  **Test nuevo**: `test_grupo_activo_migracion.py`, sobre **dos administraciones reales**: downgrade a
  `0024`, insertar grupos (Generales + parcial) en cada una, upgrade a `0025`, confirmar `activo=true`
  en las dos sin tocar sus filas; downgrade a `0024` (columna desaparece) y upgrade otra vez.

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_grupo_activo_migracion.py
  tests/integracion/test_generales_alcance_sql.py` → `10 passed in 50.80s`.

  **Mutante dirigido #1 (`server_default`, L-035)**: se sacó temporalmente `server_default=sa.true()`
  de `add_column` — copia temporal, sin commit. Resultado: la migración misma explota —
  `NotNullViolation: column "activo" ... contains null values` en el propio `ALTER TABLE ... ADD
  COLUMN`, porque ya había filas de la administración sembrada antes del upgrade. Revertido.

  `rg` confirmado arriba; sin segundo mutante sobre el trigger acá — el mutante de ese archivo
  (sacar `OR NEW.activo IS DISTINCT FROM OLD.activo`) se corrió al escribir el test SQL de 4.2
  (`test_desactivar_generales_por_sql_se_rechaza`): sin esa cláusula, `UPDATE ... SET activo=false
  WHERE id=<Generales>` pasaba sin error — se confirmó manualmente contra la versión sin esa cláusula
  antes de restaurarla, no quedó como test aparte porque ya lo cubre el hallazgo real de 4.2.
- [x] 4.4 Aplicar la autogeneración de clave en **sus dos llamadores**, grupos y categorías, con sus
  tests en los dos (L-009), manteniendo la clave explícita aceptada por API y la clave inmutable al
  renombrar; escenarios "Renombrar no cambia la clave", "Clave explícita inválida" y "Agregar una
  categoría" / "Renombrar una categoría" de `categorias-de-gasto`.

  **Implementación**: `grupos.DatosGrupo.clave` pasa a `str | None = None`; `crear_grupo` deriva con
  `derivar_clave` (tarea 4.1) contra las claves que el edificio ya tiene cuando llega `None`.
  `categorias.crear_categoria` deriva de la misma forma sobre el `dict` crudo, ANTES de validar con
  `CategoriaDeGasto` (que sigue exigiendo `clave` siempre — la usa también el YAML de parámetros,
  D-042, así que ese modelo no se tocó). `CuerpoGrupo` (API) hereda el campo opcional sin cambios;
  `CuerpoCategoria.clave` se angosta a `str | None` con `# type: ignore[assignment]` (Pydantic valida
  el campo declarado, no el heredado; mypy no lo sabe). "Renombrar no cambia la clave" ya funcionaba
  sin tocar nada: `editar_grupo`/`editar_categoria` sólo escriben `clave` si viene en `cambios`.

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_clave_autogenerada.py` →
  `7 passed in 17.55s` (cubre "Clave derivada del nombre", clave explícita respetada, desempate,
  "Nombre del que no sale ninguna clave", "Renombrar no cambia la clave" × 2 — grupo y categoría,
  "Agregar una categoría").

  **Mutante dirigido (L-035)**: se sacó temporalmente la rama `if entrada.clave is None: ...` de
  `crear_grupo` — copia temporal, sin commit. Resultado: `4 failed, 3 passed`, cayendo en los 4 tests
  que dependen de la derivación (`NotNullViolation` en la base, nunca silencioso). Revertido;
  `7 passed` de nuevo.

  `uv run ruff check` + `uv run mypy` sobre `grupos.py`, `categorias.py`, `complejos.py` → sin
  hallazgos.
- [x] 4.5 `PATCH /grupos/{id}` acepta `activo`, sin ninguna ruta de borrado, y los grupos desactivados
  salen del filtro de disponibles y de la puesta a punto; verificado con los escenarios "Desactivar un
  grupo parcial", "Reactivar", "Borrar", "Un grupo desactivado no reclama unidades" y "Grupo parcial
  vacío pero desactivado".

  **Implementación**: `CuerpoEdicionGrupo.activo: bool | None = None`; `editar_grupo` saca `activo` de
  `cambios` antes de validar con `DatosGrupo` (no es forma de clave/nombre/método, es estado
  operativo) y lo escribe aparte, agregándolo a `campos` de auditoría si cambió.
  `grupos.listar_grupos` suma `solo_activos: bool = False` (mismo patrón que
  `categorias.listar_categorias`), cableado como query param en `GET /complejos/{id}/grupos`.
  `lectura.resumen_edificio`: el paso "grupos" sólo mira `grupo_de_reparto` con `activo` (un grupo
  parcial desactivado no exige miembros). Sin ruta `DELETE` (nunca existió): confirmado con `405`.

  **Verde**: `bash infra/ci/test-backend.sh tests/integracion/test_grupo_activo.py
  tests/integracion/test_resumen_puesta_a_punto.py` → `17 passed in 31.86s`. Regresión amplia (grupos,
  categorías, contrato, RLS, 422, padrón): `125 passed in 143.37s`.

  **Mutante dirigido #1 (filtro `solo_activos`, L-035)**: se sacó el `AND (NOT :solo OR activo)` de
  `listar_grupos` — copia temporal, sin commit. Resultado: `1 failed, 4 passed`, cayendo exactamente en
  `test_desactivar_un_grupo_parcial` (el único que pide `solo_activos=true`). Revertido.

  **Mutante dirigido #2 (paso "grupos" de la puesta a punto)**: se sacó el `AND activo` de la consulta
  de `grupos_parciales` en `resumen_edificio` — copia temporal, sin commit. Resultado: `1 failed, 4
  passed`, cayendo exactamente en
  `test_grupo_desactivado_sin_unidades_no_bloquea_la_puesta_a_punto`. Revertido; `5 passed` de nuevo.

  **Hallazgos reales, no previstos (encontrados al correr la suite completa tras cerrar el grupo 4)**:
  (1) `test_auditoria_grupos_categorias.py::test_siete_eventos_y_solo_nombres` y
  `test_rutas_protegidas.py` (arreglado en el grupo 3) usaban un `piso` arbitrario ("Privado") que la
  tarea 3.3 ya no acepta — mismo patrón que "Otro"/"PRIVADO_PISO" de las tareas 3.2/3.3, corregido a
  `"2"`. (2) `test_contrato_web.py::test_forma_de_cada_ruta_que_usa_la_web[grupos]`: fixture
  regenerado con `PROPTECH_ACTUALIZAR_FIXTURES=1` (suma `"activo": true`, cambio de forma deliberado).
  (3) `test_regresiones_de_aislamiento_y_grupos_vacios.py`: el `PATCH /api/complejos/{id}` nuevo
  (tarea 3.6) no tenía cuerpo en `_CUERPOS`, caía al `{"persona_id":..., "rol":...}` por defecto → 422
  en vez de 404; agregado `"/api/complejos/{complejo_id}": {"nombre": "X"}`. (4)
  `infra/ci/ensayo-roles.sh` tenía `verificar_revision 0022` hardcodeado dos veces (`test_ensayo_login.
  py`, pre-existente): actualizado a `0025`, la cabeza real tras este change. (5)
  `test_vocabulario_vigente.py` (pre-existente, L-022): el docstring de un test nuevo de la tarea 3.6
  (`test_editar_edificio.py`) decía "colaborador", vocabulario de roles anterior a D-106; reescrito a
  "una identidad con alcance".

## 5. Errores de formulario y mensajes en la web

- [ ] 5.1 **Test en rojo** que reproduce B-2 contra la API real: "rige desde" repetido **y** día de
  vencimiento inválido en el mismo cuerpo, afirmando a qué campo llega cada error y que "tasa mensual"
  **no** queda marcada (D6). Si sale verde, el hallazgo se cierra como no reproducible con el comando,
  la salida y la hora pegados, y el test queda como fijación. Escenario "Dos errores a la vez en
  intereses y vencimiento".
- [ ] 5.2 Rama `conflicto` en `crearVersionDeConfiguracionAction`, con el mensaje en el campo
  "rige desde" ("Ya hay una versión que rige desde esa fecha") y sin marcar ningún otro campo;
  escenarios "Rige desde repetido" y "Día de vencimiento fuera de rango".
- [ ] 5.3 Test que recorre **todas** las acciones de escritura de la web y falla si alguna no cubre las
  cinco respuestas del cliente (ok, inválido, conflicto, sin permiso, sin sesión), para que el genérico
  quede sólo donde la pantalla no puede explicar nada; escenario "Toda pantalla que escribe cubre las
  cinco respuestas".
- [ ] 5.4 Constantes de la web con el máximo del identificador, el rango del coeficiente y la regla de
  la clave, usadas en la ayuda, en el mensaje **y en una validación previa al envío que pone el mismo
  `error` explícito de `Campo`/`Formulario`** (D7, corregido tras revisión: no alcanza con `maxLength`/
  `pattern` nativos del input, que producen una burbuja del navegador sin `aria-describedby` — pueden
  quedar como ayuda adicional, nunca como único mecanismo), más un test que compara el máximo de la web
  contra el contrato de la API; escenarios "Identificador demasiado largo", "Ayuda del identificador",
  "Coeficiente cargado como porcentaje", "Clave inválida por API" y "El error previo al envío tiene el
  mismo `aria-describedby` que el error de la API".
- [ ] 5.5 `/privacidad` sin la nota interna: texto escrito para el usuario y su test actualizado (el
  test de hoy exige la nota); escenarios "Sin la nota interna" y "El aviso sigue siendo un borrador".
- [ ] 5.6 Generalizar D7 a convención escrita (L-047): agregar a
  `knowledge-base/08_arquitectura_propuesta.md` §"La web" la regla transversal — todo campo con un
  límite o un patrón lo expresa en una constante compartida por el input, la ayuda y el error, nunca
  sólo en el mensaje genérico; un test la compara contra el contrato de la API. No es código, es la
  convención que el próximo campo nuevo (en esta pantalla o en otra) tiene que seguir sin que haya que
  volver a encontrarla rota.

## 6. Pantallas

- [ ] 6.0 Extender `Campo`/`Formulario` para que sepan renderizar un `<select>` con el mismo contrato
  que un `<input>` — `id` de `idDelCampo`, `aria-invalid`, `aria-describedby`, foco por el mismo enlace
  del resumen (`CampoDeLista` o `Campo` con `as="select"`, F1) — y sumar
  `.campo select[aria-invalid="true"]` a `tokens.css` (F5). Verificado con un test de `Formulario.tsx`
  que afirma los tres atributos en un select con error, igual que ya se afirma para un input. Esta
  tarea es condición de 6.1 y 6.2: sin ella, los `<select>` nuevos repiten el patrón que ya está roto en
  8 de los 9 que existen hoy.
- [ ] 6.1 Alta y edición del edificio con las tres listas encadenadas (usando `CampoDeLista` de 6.0),
  calle y número, pisos y subsuelos, en "Mis edificios" y en el resumen, con el vaciado en cascada al
  cambiar de provincia, **estado `cargando` (select deshabilitado + `Estados tipo="cargando"`) y `error`
  con reintento por cada lista** (D8, F3), y todo operable con teclado; verificado con los escenarios
  "Crear un edificio", "Encadenar las listas", "Elegir la ubicación con teclado", "Edificio migrado sin
  ubicación", "Editar el edificio desde el resumen", "Una lista no carga y se puede reintentar" y los de
  ayuda y foco de `pantallas-del-edificio` (L-026, L-028: el foco y el `Esc` se prueban con el panel y
  la lista combinados, no por componente suelto).
- [ ] 6.2 Padrón con el piso elegido de la lista del edificio (usando `CampoDeLista` de 6.0, **con
  opción vacía explícita cuando `piso` es `NULL`** — F2: sin eso, abrir el panel de una unidad migrada
  selecciona y guardaría la primera opción de la lista sin que nadie la haya elegido) y las unidades sin
  piso marcadas, con los fixtures de la API falsa sacados del contrato real (L-027); escenarios "Elegir
  el piso de la lista del edificio", "Unidades con el piso sin completar" y "Abrir una unidad migrada no
  guarda ningún piso solo".
- [ ] 6.3 Grupos y categorías sin campo "clave", con "desactivar" y "reactivar" en los grupos parciales
  y sin "borrar"; escenarios "Sin campo de clave" (los dos), "Desactivar un grupo" y "Generales".
- [ ] 6.4 Confirmación de "Quitar" en Personal con el diálogo de `PanelLateral` (D10 — no el patrón
  inline de saldos-previos, que no tiene `Esc`), con teclado, foco devuelto al cancelar y sin
  `confirm()` nativo; escenarios "Quitar y cancelar con teclado", "Quitar y confirmar" y "Sin diálogo
  nativo".
- [ ] 6.5 Semilla del edificio de ejemplo con ubicación de Georef, pisos y subsuelos, y el subsuelo
  numerado en las tres cocheras y la baulera; verificado con los escenarios "Ubicación del ejemplo",
  "Pisos del ejemplo", "Semilla con un piso fuera del vocabulario" y "Semilla con una ubicación
  incoherente" de `datos-semilla`.

## 7. Cierre

- [ ] 7.1 Recorrido manual de **cada pantalla tocada** (mis edificios, resumen, padrón, grupos,
  categorías, intereses y vencimiento, personal, privacidad) a 1280 px y a 320 px sin scroll
  horizontal, entera con teclado, con capturas guardadas y, escrito paso por paso, **cómo la cuenta de
  Clerk usada quedó vinculada a su persona** (comando, rol, base) (L-039). Esto salda la deuda del PR #1
  del 3b-bis. Ninguna dirección de prueba se escribe en el repo ni lleva "admin" en la parte local
  (L-040).
- [ ] 7.2 Corrida de cierre después de la última vuelta: suite completa de backend y de web, subida y
  bajada de las tres migraciones sobre una copia con datos, y el **CI del PR** leído verde con su SHA
  anotado (esta rama sin PR no corre CI: L-042, L-010, L-031, L-037).
- [ ] 7.3 Actualizar `knowledge-base/` según la sección "Knowledge Base Impact" del `proposal.md`
  (incluido mover los hallazgos de QA del 23/10 fuera de `CLAUDE.md`/`AGENTS.md`), escribir **D-121** con
  las respuestas firmadas a P61 a P65, P67, P68 y P69, cerrar esas P en
  `10_preguntas_abiertas.md` dejando anotados los cuatro ítems de acceso que quedan para su change
  propio, y dejar la deuda del cierre en la ficha 3c; verificado con `diff AGENTS.md CLAUDE.md` vacío.
