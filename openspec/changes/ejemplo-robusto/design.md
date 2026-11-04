## Context

Motivación en `proposal.md`, comportamiento en `specs/datos-semilla/spec.md`. Lo que condiciona el cómo:

- `backend/tests/integracion/test_ejemplo_casos_de_uso.py` no puede deshacer una carga: "Generales" y `auditoria` no admiten borrado (docstring del módulo). Hoy todo el ciclo vive en un solo test y las otras carreras usan `base_fresca`, una base nueva por test.
- El test de fronteras marca cualquier SQL de `ejemplo.py` sobre `persona` o `asignacion_rol`, también un `SELECT`. D-133 sacó ese SQL y no se vuelve atrás.
- `complejo` no tiene fecha de creación ni unicidad por nombre: sólo `id` aleatorio, `administracion_id` y `nombre` como columnas de origen (migración `0003`).
- `crear_administracion_y_super_admin` usa `ON CONFLICT DO NOTHING`, y toda la carga va en una transacción. En READ COMMITTED el perdedor espera al ganador, así que "administración sin edificio" no es una carga en curso: es un estado que quedó de otra forma.
- Los informes del PR #1 (`.git/informes-*`) están en la máquina de Juani. Que M5 sea modo, M6 estado de migración, M7 tipo y piso y M8 conjunto de grupos es SUPOSICIÓN por el orden de la ficha. No cambia el trabajo, porque se cubren los cuatro.

## Goals / Non-Goals

**Goals:** que cada garantía del comando tenga un test que da rojo con el defecto, y que un error se entienda sin leer un traceback.

**Non-Goals:** rediseñar la carga, cambiar sus casos de uso o tocar `acceso`. El alcance excluido está en `proposal.md`.

## Decisions

### D1. Los casos de comparación alteran la semilla, no la base

Se carga el ejemplo una vez por módulo y cada caso llama a `cargar()` con una copia alterada de `Semilla` (`model_copy`, que no revalida). Como la comparación falla antes de escribir, ningún caso ensucia la base compartida.

- **Por qué**: la base no se puede deshacer, y algunas columnas tienen triggers y restricciones que frenarían el `UPDATE` antes de llegar a la rama probada (L-034).
- **Descartado**: una `base_fresca` por caso, porque repite 33 migraciones por cada uno de los más de 12 casos; y editar la base y volver atrás, porque los triggers lo impiden en parte.
- **Límite**: el camino "se editó la base" ya lo cubre el caso de coeficiente del ciclo completo. La persona sí se altera en la base (D3), con una `base_fresca`.

### D2. El edificio se identifica por el nombre de la semilla, sin `LIMIT`

Se traen los edificios de la administración de ejemplo y se separan los que coinciden con `semilla.edificio.nombre`:

| Edificios | Coinciden | Resultado |
|---|---|---|
| Ninguno | 0 | Espera y reintenta, como hoy |
| Uno o más | 1 | Compara ése |
| Uno o más | 0 o 2 o más | `EjemploDistinto`, sin esperar |

- **Por qué no `ORDER BY id`**: el `id` es aleatorio. Sería determinístico, pero podría elegir siempre el edificio equivocado.
- **Por qué no agregar una columna o un id fijo**: exige migración y `crear_edificio` genera el id; es desproporcionado para un comando de desarrollo.
- **Riesgo aceptado**: renombrar el ejemplo da "distinto". Es correcto, porque el nombre sale de la semilla.

### D3. La persona se lee con `listar_personal`, sin tocar `acceso`

`acceso.aplicacion.usuarios.listar_personal(sesion)` ya devuelve nombre, email y asignaciones, con RLS. La API ya lo usa y el test de fronteras permite importar `acceso.aplicacion`. Se busca la persona de id fijo y se compara nombre, email y que tenga una asignación `super_admin`.

- **Por qué alcanza con "tiene"**: asignaciones de más o personas de más no son "el ejemplo cambió". El spec `acceso-de-desarrollo` ya contempla otra persona que aceptó una invitación ahí, y `vinculado` tampoco se compara.
- **Descartado**: una función nueva en `acceso` o una excepción en `_EXCEPCIONES_SQL`. La primera toca `acceso`, cosa que la guía manda frenar; la segunda deshace D-133.
- **Costo**: `listar_personal` también lee invitaciones que acá no se usan. No importa en un comando de desarrollo.

### D4. Tabla de códigos con la guarda en 1

La tabla está en el spec. La guarda conserva el 1 porque D-112 lo fija y el pedido no alcanza para reemplazar una decisión. Para que el 1 sea exclusivo de la guarda, `_main` envuelve el trabajo y una excepción no prevista termina en 9: Python usa 1 para una excepción sin capturar.

- **Traducción**: `ConfiguracionInvalida`, `ParametrosInvalidos`, `SemillaInvalida` y `GeorefInvalido` son propias y se reenvían (3). No repiten valores (L-002, L-007), con dos salvedades. `SemillaInvalida` nombra el identificador de una unidad o la clave de un grupo, porque el requisito del lector lo pide. Y el lector de archivos repite la ruta: como `--semilla` es algo que se tipeó y puede ser el id de la cuenta, `_ejecutar` la reemplaza sólo cuando el mensaje es el de "no se puede leer el archivo", nunca dentro de otro texto. `EntradaInvalida` (3) nombra su `campo`, sin su `motivo` (D10). `RolDeAplicacionInseguro` usa texto fijo (4). `TablasDeSoloAgregarDesprotegidas` se reenvía (4), porque su texto sólo trae cada tabla y el motivo (`verificar_tablas_de_solo_agregar`), y la tabla es lo que hay que ir a arreglar. `OperationalError`, texto fijo (5): incluye `lock_timeout` y `statement_timeout`, a los que sólo se llega con esos ajustes en la base, y el comando no los fija. `IntegrityError` y otro `DBAPIError` (8). La espera agotada pasa a una excepción propia (8). `KeyboardInterrupt`, texto fijo (130, D10).
- **`argparse`** repite lo que se tipeó mal, que también puede ser el id, así que `_Parser` da siempre el mismo mensaje y termina con 2. Corre antes de la guarda: un error de uso da 2 en cualquier entorno y `--help` da 0. Ninguno de los dos corre el comando ni se conecta.
- **Orden**: argumentos (2), guarda (1), `--semilla` vacío y formato del id (2), emisor (3), configuración (3), archivos (3), base (4 y 5), carga (3, 6, 7 y 8). Las líneas `:460` y `:461` hoy están fuera de todo `try`, igual que `:471` y `:473-477` para errores de base. La ficha cita `:463-466`, pero ésas sí están dentro de uno.
- **Descartado**: dejar el 1 para todo con mensajes distintos, porque la ficha pide códigos propios. También reasignar la guarda, porque exige una decisión nueva sin beneficio.
- **Costo**: el código 9 esconde el traceback de un bug real. Para depurarlo se llama a `cargar()` desde un test.

### D5. Lectura de configuración propia, sin aflojar la de la app

`_LectorDelEjemplo` hereda de `_LectorDeAppSoloPostgres` (usuario y contraseña con sus validadores) y agrega `proptech_parametros` y los parámetros del pool, con los mismos validadores que `_LectorDeApp`. `ConfiguracionDelEjemplo` expone lo que usan el comando y `crear_engine`.

- **Por qué no `ConfiguracionDeAppSoloPostgres`**: no trae los parámetros ni el pool.
- **Por qué no hacer opcional Redis en `_LectorDeApp`**: la API y el worker arrancarían sin Redis, justo lo que el spec prohíbe.
- **`clerk_emisor=` sale de `Configuracion`**: su único consumidor es `ejemplo.py:460`. El comando ya valida `CLERK_EMISOR` con `_emisor_de_desarrollo` antes de leer la configuración, y la lectura nueva no lee Clerk.
- **`crear_engine`** pasa a aceptar un `Protocol` con los campos que lee (`url_sqlalchemy` y los `db_*`). `mypy` sobre todo `src/` lo vigila (L-063).
- **Gemelos**: los validadores de pool y parámetros quedan en dos lectores. La tarea 4.2 corre los mismos valores inválidos contra los dos (L-009).

### D6. La carrera se fuerza con una barrera en el `INSERT` de la administración

Un `threading.Barrier(2, timeout=15)` en `before_cursor_execute` de cada engine, cuando la sentencia es `INSERT INTO administracion`, mismo patrón que `test_dos_vinculaciones_a_la_vez_no_pisan_a_la_ganadora`. Si los hilos se serializan, la barrera se rompe por tiempo y el test da rojo. Eso es lo que hoy no pasa. Mutante de prueba: un `Lock` alrededor de la carga en el test.

### D7. Espera agotada y reintento

`cargar()` ya acepta `intentos` y `espera_s`. Agotamiento: administración creada sin edificio, con `intentos=2, espera_s=0`. Reintento: `time.sleep` reemplazado por una función que carga el edificio con otra sesión y confirma. El mensaje actual ("otra corrida en paralelo no confirmó") se reemplaza porque afirma una causa que el contexto descarta: ahora dice que la administración existe sin edificio.

### D8. La guarda de QA-5 recibe la raíz como parámetro

`_puntos_de_entrada_prohibidos(raiz)` devuelve los que existen. Un test corre contra el repo real y exige que exista `infra/`, para que no pase en vacío si cambia la ruta (L-016); otro corre contra una copia en `tmp_path` con cada archivo prohibido y exige que aparezca. Sólo mira existencia, sin recorrer carpetas reales (L-033).

### D9. Un mensaje por cada campo de la unidad

Cada campo que difiere suma su propia línea: `unidades[1A].piso: difiere de la semilla`. Sin valores, igual que el resto de la comparación de unidades.

- **Por qué**: el spec pide nombrar el dato, y el objetivo del change es que se entienda sin leer nada más. Hasta acá `unidades[1A]: difiere de la semilla` obligaba a mirar la fila.
- **Descartado**: corregir el spec para que alcance con nombrar la unidad, porque achica la garantía para esquivar seis líneas.

### D10. Lo que el rompedor encontró afuera de la tabla

**El rechazo del caso de uso es un 3.** `leer_semilla` deja pasar `pisos: 0`, un identificador de más de 40 caracteres y `estado_migracion: confirmada`, y la carga los rechaza. `_ejecutar` captura `EntradaInvalida` y `_crear_desde_cero` la lanza en lugar de `NotImplementedError`. Sólo sale `campo`: el módulo de errores dice que `motivo` no llega al cliente.

- **Costo**: en estos casos el comando ya se conectó, cosa que el escenario "Configuración rota" prohíbe para lo que frena el lector. La transacción revierte, así que no escribe nada.
- **Descartado**: copiar esos topes en `leer_semilla`. `compartido/semilla.py` está fuera del change, y dos copias de los mismos topes se separan con el tiempo (L-009).
- **`Conflicto`** sigue en el 9: `leer_semilla` ya frena los repetidos, y nadie lo reprodujo.

**Ctrl-C es un 130.** `_main` lo captura, porque es la única salida de una persona con el comando colgado y la promesa es que no haya traceback. El 130 es la convención de los shells y no choca con la tabla.

- **Descartado**: declararlo fuera y corregir el comentario. Costaba lo mismo, y dejaba un traceback en la salida más probable de un comando que espera.
- **Texto**: no dice "no se escribió nada", porque la interrupción puede llegar después del commit. Dice que una carga a medias no queda, y eso sí lo garantiza la transacción.

**`--semilla=` vacío es un 2.** Hoy cae en la semilla por defecto, así que un `--semilla "$VARIABLE"` sin definir cargaría otra semilla sin avisar. Su gemelo `--clerk-usuario=` ya da 2.

## Risks / Trade-offs

- **[Qué edificio elige `LIMIT 1`]** → El plan suponía el orden físico, y el constructor midió otra cosa: con `uq_complejo_administracion_id`, `LIMIT 1` devuelve el `id` más bajo, que es aleatorio, y el `UPDATE` no lo mueve. Con un segundo edificio el falso "distinto" sale a cara o cruz. El test fija el `id` más bajo con una fila propia y prueba también recorriendo la tabla.
- **[Cambian tres tests que fijan el código 1 y uno que espera `RolDeAplicacionInseguro` en el texto]** → Es el cambio pedido por BE-3, no se debilita la aserción: pasan a exigir el código nuevo y que no haya traceback.
- **[`test_arranque_tablas_protegidas.py` espera que la excepción salga de `_main`]** → El caso `ejemplo` pasa a exigir el código 4 y la tabla en el mensaje. No se puede volver a lanzar la excepción dentro de su `pytest.raises(..., match=tabla)`, porque esa aserción se cumpliría sola (L-019, L-035).
- **[Una nueva clase de configuración en `compartido`]** → 4.3 prueba que `Configuracion` sigue exigiendo Redis.
- **[Las fallas de portabilidad en Windows, D-110]** → Durante el apply se corren los archivos tocados; el juez de la suite entera es el CI del PR (8.1). `wsl -l` sólo muestra `docker-desktop`, así que hoy no hay un Linux propio en esta máquina. El constructor midió 56 fallas que ya existen en Windows sobre `9649471`, de más familias que las que nombra D-110, y las separó corriéndolas en un contenedor Linux.
- **[`uv` local 0.13.6, imagen 0.12.24]** → Se usa `uv sync --locked`, que no reescribe `uv.lock`. Si el archivo aparece modificado, no se commitea y se avisa.

## Migration Plan

Sin migraciones ni cambios de despliegue. Se revierte con el commit. El comando corre sólo en desarrollo (D-112).
