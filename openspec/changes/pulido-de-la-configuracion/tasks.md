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
- [ ] 2.4 Migración `0023`: las cuatro columnas de ubicación, el `CHECK` "los tres o ninguno" y
  `complejo.localidad` a nullable; verificar la subida y la bajada sobre una copia con el edificio de
  ejemplo cargado (Migration Plan, paso 1).
- [ ] 2.5 Tres rutas de lectura de provincias, departamentos de una provincia y localidades de un
  departamento, con sesión, 404 para un padre inexistente y 401 sin sesión; verificado con el test de
  los escenarios "Departamentos de una provincia", "Localidades de un departamento", "Provincia
  inexistente" y "Sin sesión".
- [ ] 2.6 El alta del edificio exige el trío y acepta calle y número opcional (≤ 200, sin caracteres de
  control); `localidad` deja de ser entrada y se escribe derivada del nombre de Georef. Verificado con
  los escenarios "Alta con ubicación y pisos", "Alta sin ubicación", "Alta sin calle", "Calle con
  carácter de control o demasiado larga" y el test de que `localidad` coincide con el nombre de Georef
  después de escribir (D2).

## 3. Pisos del edificio y de la unidad

- [ ] 3.1 **Test en rojo** del vocabulario de pisos como función pura: `PB` siempre, `SS1..SS<subsuelos>`,
  `1..<pisos>`, con 0 subsuelos y 0 pisos, y los límites 5 y 60; coincidencia completa y sólo ASCII
  (L-008). Escenario "Piso de planta baja y de subsuelo" de `edificios-y-unidades`.
- [ ] 3.2 `complejo.pisos` (nullable, 1..60) y `complejo.subsuelos` (nullable, 0..5) en el alta y en la
  lectura, sin calcularlos de nada — nulo es "sin completar", igual que la ubicación — y rechazo de
  texto por número; verificado con los escenarios "Cantidades fuera de rango", "Cantidades como texto"
  y "Edificio nuevo sin pisos completados".
- [ ] 3.3 **Test en rojo** de la validación de `piso` **por la API** (no sólo por el dominio, L-017):
  piso fuera del vocabulario del edificio, texto libre (`"Entrepiso"`, `"pb"`, `" 1"`, `"1°"`, `"SS"`,
  dígito no ASCII), piso faltante o `null` en un alta, y el `INSERT`/`UPDATE` por SQL que el `CHECK`
  tiene que frenar; más un **mutante dirigido** que saca la comparación contra el edificio y deja el
  `CHECK` de forma, para probar que el test vigila la garantía específica y no una capa anterior
  (L-034, L-035). Escenarios "Piso que el edificio no tiene", "Piso como texto libre", "Unidad nueva
  sin piso", "El piso no se sale del vocabulario por SQL".
- [ ] 3.4 Migración `0024` (corregida tras revisión DBA): `complejo.pisos`/`subsuelos` nacen
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
- [ ] 3.5 Bajar `pisos` o `subsuelos` con unidades afuera se rechaza con 422 **nombrando los
  identificadores**; verificado con los escenarios "Bajar pisos con unidades arriba", "Bajar subsuelos
  con cocheras abajo" y "Bajar pisos sin unidades arriba", con el `EXPLAIN` de la consulta que busca las
  unidades afuera pegado en el informe — confirmando que entra por `uq_unidad_identificador` y no hace
  falta índice nuevo (sin esto, "no hace falta índice" es un juicio sin evidencia, no un hecho del
  propose).
- [ ] 3.6 `PATCH /complejos/{id}`: nombre, ubicación, calle y número, pisos y subsuelos, con
  `Accion.CONFIGURAR_PADRON` (404 fuera de alcance, 403 sin permiso, en ese orden) y `CuerpoDeEdicion`
  (un campo puede faltar, ninguno puede ser `null`); verificado con los escenarios "Corregir la
  localidad", "Completar la ubicación de un edificio viejo", "Anular un campo obligatorio", "Editar un
  edificio fuera del alcance", "Editar sin permiso de configurar el padrón" y "Cambiar la administración
  por la edición".
- [ ] 3.7 Auditoría de `editar_edificio`: evento nuevo en `EventoDelPadron`, fila nueva del vocabulario
  en la migración `0025`, detalle con el edificio y los nombres de los campos cambiados y nada más
  (D-016); verificado con los escenarios "Editar la ubicación", "La edición falla", "Edición sin
  cambios" y "El evento de editar el edificio existe en la base".
- [ ] 3.8 El séptimo paso de la puesta a punto (ubicación completa, `pisos`/`subsuelos` completos y
  ningún piso de unidad sin completar), con el conteo de unidades por corregir y el `EXPLAIN` de esa
  consulta pegado (filtra por `(administracion_id, complejo_id)`, mismo prefijo de índice que 3.5);
  verificado con los escenarios "Edificio recién creado", "Edificio migrado sin ubicación", "Edificio
  migrado sin pisos completados", "Unidad migrada con el piso sin completar" y "Edificio listo para
  liquidar" de `edificios-y-unidades`.

## 4. Grupos desactivables y claves autogeneradas

- [ ] 4.1 **Test en rojo** de la función pura que deriva la clave del nombre: tildes, signos, guiones
  bajos repetidos y de borde, prefijo por letra, recorte a 40, desempate `_2`, y un nombre del que no
  sale ninguna clave (`"123"`, `"— —"`). Escenarios "Clave derivada del nombre", "Nombre con tildes y
  signos", "Clave derivada repetida" y "Nombre del que no sale ninguna clave".
- [ ] 4.2 **Test en rojo** de que "Generales" no se desactiva, ni por la API (422) ni por SQL, con un
  **mutante dirigido** al trigger ampliado (L-035); escenarios "Desactivar Generales" y "Desactivar
  Generales por SQL".
- [ ] 4.3 Migración `0025`: `grupo_de_reparto.activo` (`NOT NULL DEFAULT true`), el trigger de `0011`
  ampliado y `editar_edificio` en el vocabulario de auditoría; subida y bajada probadas sobre una copia
  con datos (Migration Plan, paso 3) y `rg` de `INSERT INTO grupo_de_reparto` en el repo entero (L-023).
- [ ] 4.4 Aplicar la autogeneración de clave en **sus dos llamadores**, grupos y categorías, con sus
  tests en los dos (L-009), manteniendo la clave explícita aceptada por API y la clave inmutable al
  renombrar; escenarios "Renombrar no cambia la clave", "Clave explícita inválida" y "Agregar una
  categoría" / "Renombrar una categoría" de `categorias-de-gasto`.
- [ ] 4.5 `PATCH /grupos/{id}` acepta `activo`, sin ninguna ruta de borrado, y los grupos desactivados
  salen del filtro de disponibles y de la puesta a punto; verificado con los escenarios "Desactivar un
  grupo parcial", "Reactivar", "Borrar", "Un grupo desactivado no reclama unidades" y "Grupo parcial
  vacío pero desactivado".

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
