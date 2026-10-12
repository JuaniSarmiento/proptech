## Context

Ver `proposal.md` (Why). Estado de partida del cambio original, leído del código al 09/10/2026:

- `infra/compose.yaml` (proyecto `proptech`): `db`, `migraciones`, `api`, `web`, `caddy`; redes `borde`
  e `interna` (`internal: true`, sin salida). Sólo Caddy publica 80/443.
- `backend/`: `Configuracion` (pydantic-settings, error que nombra variables sin valores, L-002),
  usada por la API **y por Alembic** (`migraciones/env.py`). Migración `0001` vacía. `pyyaml` estaba
  sólo en el grupo `dev`.
- `test_imagen_del_fixture_coincide_con_la_de_compose_db` comparaba una constante contra el mismo
  archivo del que salía: no podía fallar (deuda de D-051). El healthcheck de `db` usaba
  `pg_isready -U ${POSTGRES_USER...}` sin comillas (deuda de D-051).
- `config/` existía vacía.

Restricciones: L-002 (configuración faltante, vacía, en blanco, de tipo equivocado y fuera de rango,
nombrando la variable sin el valor), L-003 (contar tests contra la línea de base), L-005 (verde es todo
el workflow, humo incluido).

## División del cambio

El cambio original tenía 12 secciones. El constructor completó las 1 a 5 (19 tareas; 182 tests de
backend en verde según su informe) y Juani decidió partirlo. Lo que queda acá es lo construido; la
cola, el worker, la idempotencia, los logs con `request_id`, `/salud-web`, los backups, el humo
ampliado y el README pasan a `cola-logs-y-respaldos`, con sus decisiones D1 a D4, D7 a D9 y la parte
de Redis de D12, sin cambios de contenido.

Al releer el código contra las specs reducidas aparecieron cuatro huecos, que suma la sección 6 de
`tasks.md`:

1. **El stack de Compose no arranca.** `Configuracion()` exige `REDIS_HOST`, `REDIS_PASSWORD` y
   `PROPTECH_PARAMETROS`, y la llaman `crear_app()` y `migraciones/env.py`; Compose no pasa ninguna
   de las tres ni monta `config/`, y `.env.example` no tiene `REDIS_PASSWORD`. El trabajo de
   migraciones y la API terminarían con `ConfiguracionInvalida`, y el humo del CI en rojo. Los 182
   tests no lo ven porque los `conftest.py` definen esas variables. Tareas 6.1, 6.2 y 6.5.
2. **Rangos de los estados de unidad** sin validar (tarea 6.3, ver D6).
3. **`MontoInvalido` repite el texto recibido**, que dentro del lector de parámetros es contenido del
   archivo (tarea 6.4, ver D5).
4. **El cierre**: la corrida equivalente al CI (sección 12 del original) se necesita también para
   archivar esta mitad (tarea 6.5).

## Goals / Non-Goals

**Goals:**

- Que los cambios 3, 4 y 7 encuentren resueltos, probados y con una sola forma los parámetros, el
  monto y el edificio de ejemplo.
- Que un archivo de parámetros o una configuración rotos frenen el arranque con un error que diga qué
  campo o qué variable, sin mostrar valores.

**Non-Goals:**

- Cola, worker, logs, `request_id` y backups (`cola-logs-y-respaldos`).
- Tablas de edificio (cambio 3) y aritmética de montos (cambio 4).

## Decisions

Se conservan los números de D del cambio original para que las referencias de `tasks.md` y del
informe del constructor sigan valiendo. D1 a D4, D7 a D9 viven ahora en `cola-logs-y-respaldos`.

### D5 · El tipo `Dinero`

`proptech_core/compartido/dinero.py`, clase inmutable con `__slots__`:

```python
class MontoInvalido(ValueError): ...

class Dinero:
    def __init__(self, texto: str) -> None          # sólo str; type(texto) is str, si no MontoInvalido
    @classmethod
    def desde_decimal(cls, valor: Decimal) -> Dinero  # para adaptadores; finito, <=2 decimales, rango
    def a_texto(self) -> str                         # siempre 2 decimales: "20000.00"; -0 -> "0.00"
    @property
    def decimal(self) -> Decimal                     # cuantizado a 0.01
    __eq__ / __hash__ / __lt__ ... (total_ordering)  # sólo contra Dinero; otro tipo: NotImplemented
    __repr__ -> 'Dinero("20000.00")'
    __str__  -> a_texto()
```

- Texto aceptado: `^-?\d{1,12}(\.\d{1,2})?$` (12 enteros = `NUMERIC(14,2)`). Se chequea el tipo con
  `type(x) is str` (no `isinstance`), así `bool` e `int` no entran por herencia.
- **Mensajes de error sin el valor**: `MontoInvalido` dice qué está mal (tipo, formato, rango), nunca
  el texto recibido, porque el mismo tipo valida campos de `parametros.yaml` y el lector promete no
  repetir el contenido del archivo. **Hoy el código** incluye el texto con `!r`: lo cierra la tarea 6.4.
- **Sin aritmética** en este cambio (spec). El cambio 4 la agrega junto con el mayor resto.
- **Pydantic**: `__get_pydantic_core_schema__` con un validador plano que acepta sólo `str` o
  `Dinero` (un número JSON da 422) y serializa con `a_texto()`; esquema JSON `type: string` con el
  patrón.
- **SQLAlchemy**: `TipoDinero(TypeDecorator[Dinero])` con `impl = Numeric(14, 2, asdecimal=True)`,
  `cache_ok = True`; `process_bind_param` acepta sólo `Dinero` o `None` (un `float`, `Decimal` o `str`
  levanta `MontoInvalido` antes de llegar a la base); `process_result_value` usa `desde_decimal`. Se
  prueba contra PostgreSQL real con una tabla temporal creada en el test (este cambio no agrega
  tablas con plata).
- **Descartado**: subclasear `Decimal` (heredaría la aritmética y `Decimal(0.1)`), un `NewType`
  (no valida nada en runtime).

### D6 · `config/parametros.yaml` y su lector

Esquema (versión 1), con todos los porcentajes y montos **como texto**:

```yaml
version: 1
intereses:
  tasa_mensual: "3.00"                 # % mensual simple, 0..10, hasta 2 decimales (R03)
  dias_de_gracia: 0                    # entero 0..31
  forma_de_calculo: proporcional_por_dia   # proporcional_por_dia | mes_entero
fondo_de_reserva:
  porcentaje: "0.00"                   # 0..100 (R15)
categorias_de_gasto:                   # R16, D-041; no vacía, claves únicas
  - { clave: encargado,      nombre: "Encargado y cargas sociales" }
  - { clave: seguridad,      nombre: "Seguridad" }
  - { clave: limpieza,       nombre: "Limpieza" }
  - { clave: ascensor,       nombre: "Ascensor" }
  - { clave: mantenimiento,  nombre: "Mantenimiento" }
  - { clave: servicios,      nombre: "Servicios" }
  - { clave: seguros,        nombre: "Seguros" }
  - { clave: administracion, nombre: "Administración" }
  - { clave: varios,         nombre: "Varios" }
grupos_de_reparto:                     # R01; debe incluir generales
  - { clave: generales, nombre: "Generales", metodo: coeficiente, alcance: todas_las_unidades }
  - { clave: ascensor,  nombre: "Ascensor",  metodo: coeficiente, alcance: a_elegir,
      descripcion: "Sin planta baja ni locales" }
  - { clave: cocheras,  nombre: "Cocheras",  metodo: coeficiente, alcance: a_elegir }
  - { clave: servicios_centrales, nombre: "Servicios centrales", metodo: coeficiente, alcance: a_elegir }
tipos_de_unidad:                       # D-029
  - { clave: departamento, nombre: "Departamento" }
  - { clave: cochera,      nombre: "Cochera" }
  - { clave: baulera,      nombre: "Baulera" }
  - { clave: local,        nombre: "Local" }
estados_de_unidad:                     # R02, desactivados en edificios (D-030)
  habilitados: false
  estados:
    - { clave: baldio,     nombre: "Baldío",     factor: "100.00", cargo_fijo: "0.00" }
    - { clave: en_obra,    nombre: "En obra",    factor: "100.00", cargo_fijo: "0.00" }
    - { clave: habitado,   nombre: "Habitado",   factor: "100.00", cargo_fijo: "0.00" }
    - { clave: desocupado, nombre: "Desocupado", factor: "100.00", cargo_fijo: "0.00" }
```

- Estados: `factor` es un porcentaje 0..100 con hasta dos decimales (mismo validador que el fondo) y
  `cargo_fijo` un `Dinero` no negativo; la lista `estados` no puede estar vacía. **Hoy el código** usa
  `Dinero` sin rango para los dos y no exige lista no vacía: lo cierra la tarea 6.3.
- `metodo`: `coeficiente | superficie | partes_iguales`. `alcance`: `todas_las_unidades | a_elegir`;
  `generales` MUST ser `coeficiente` + `todas_las_unidades` (default de R01). Claves:
  `^[a-z][a-z0-9_]{0,39}$`. Nombres: no vacíos ni en blanco, hasta 80 caracteres.
- **Rango de la tasa 0..10 % mensual**: la spec necesita un tope (L-002). 10 % mensual ya es más del
  triple del default; un valor mayor es casi seguro un error de tipeo (`30` por `3.0`). Se valida con
  un administrador junto con P4 (está en Supuestos).
- **Lector** `leer_parametros(ruta) -> Parametros` en `proptech_core/compartido/parametros.py`:
  1. Lee bytes; si no existe o no se puede leer: `ParametrosInvalidos("no se puede leer el archivo")`.
  2. `yaml.load` con un `SafeLoader` propio cuyo `construct_mapping` **rechaza claves duplicadas**
     (PyYAML se queda con la última en silencio) y conserva la línea del error de sintaxis.
  3. Raíz no-mapa o vacía: error.
  4. Modelos pydantic con `ConfigDict(strict=True, extra="forbid", frozen=True)`. Los porcentajes
     son `str` con patrón `^\d{1,3}(\.\d{1,2})?$` convertidos a `Decimal` y chequeados por rango; en
     modo estricto un número YAML (`float` o `int`) es error de tipo y un `bool` no pasa como `int`.
  5. Se juntan **todos** los errores de pydantic y de las validaciones cruzadas (claves únicas,
     `generales` presente) en un solo `ParametrosInvalidos`, una línea por problema:
     `intereses.tasa_mensual: debe estar entre 0 y 10`, `categorias_de_gasto[3].nombre: no puede
     estar en blanco`. Nunca se incluye el valor recibido (se usa `loc` y un motivo propio, no `input`).
- `pyyaml` pasa de `dev` a dependencias de ejecución (`>=6.0.2,<7`).
- **Ruta**: variable `PROPTECH_PARAMETROS` (en `Configuracion`, validada como el resto, más "el
  archivo existe"). En Compose, `../config:/app/config:ro` montado en `api` (y en `worker` cuando exista) y
  `PROPTECH_PARAMETROS=/app/config/parametros.yaml`. **Descartado** copiar `config/` en la imagen: el
  contexto de construcción es `backend/` y cambiarlo a la raíz arrastra al build todo el repositorio
  (incluido lo que el humo verifica que no entre).
- `crear_app()` llama a `leer_parametros` después de `Configuracion()`: falla rápido igual que con una
  variable faltante (el `on_startup` del worker hace lo mismo en `cola-logs-y-respaldos`). En este cambio nadie más consume los
  parámetros; el cambio 3 los copia al crear un edificio.

### D7 a D9 · Movidas a `cola-logs-y-respaldos`

### D10 · Datos semilla

- No hay tablas de edificios hasta el cambio 3 y crearlas acá obligaría al cambio 2 a rehacerlas con
  `tenant_id` y RLS. Por eso "lo que el esquema permite" es **ninguna fila**: la semilla es un archivo
  versionado, validado y verificable por comando; el cambio 3 la inserta.
- `config/semilla/edificio-ejemplo.yaml`, versión 1:

  ```yaml
  version: 1
  edificio: { nombre: "Edificio Ejemplo", localidad: "Mendoza" }
  unidades:                     # 13 unidades; coeficientes suman 1.000000
    - { identificador: "L-PB", tipo: local,        piso: "PB", coeficiente: "0.080000", superficie_m2: "45.00" }
    - { identificador: "1A",   tipo: departamento, piso: "1",  coeficiente: "0.100000", superficie_m2: "60.00" }
    # ... 1B, 2A, 2B, 3A, 3B, 4A, 4B con 0.100000 y 60.00
    - { identificador: "C1",   tipo: cochera,      piso: "SS", coeficiente: "0.030000", superficie_m2: "12.50" }
    # ... C2, C3 iguales
    - { identificador: "B1",   tipo: baulera,      piso: "SS", coeficiente: "0.030000", superficie_m2: "4.00" }
  grupos:
    generales: todas
    ascensor: ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B"]
    cocheras: ["C1", "C2", "C3"]
  ```

  0,08 + 8 × 0,10 + 3 × 0,03 + 0,03 = 1. Sin personas, sin contacto, sin calle.
- **Precisión de coeficientes provisoria**: texto con hasta 6 decimales y suma **exacta** 1 con
  `Decimal`. El cambio 3 fija la precisión en la base; si elige otra, ajusta el archivo.
- `leer_semilla(ruta, parametros) -> Semilla` en `proptech_core/compartido/semilla.py`, mismo
  cargador YAML (claves duplicadas) y mismo armado de errores que D6. Comando
  `python -m proptech_core.compartido.semilla <ruta>` (parámetros desde `PROPTECH_PARAMETROS`), código
  0 o 1 con los errores. No abre conexión a la base. El cambio 3 lo mueve al módulo `complejos`.

### D11 · Configuración ampliada

- `_ConfiguracionBase` suma `redis_host`, `redis_port` (1..65535, default 6379), `redis_password` y
  `proptech_parametros`, con el mismo validador de no vacío ni en blanco y el mismo armado de errores
  que ya nombra variables sin valores. `proptech_parametros` además exige que el archivo exista.
  Hecho y probado (tareas 2.1 y 2.2).
- **Las variables de Redis quedan obligatorias en 1b aunque Redis llegue en el cambio siguiente.**
  Alternativas consideradas:
  - *Opcionales hasta `cola-logs-y-respaldos`*: obliga a cambiar ahora los tests de L-002 ya escritos
    para el caso "faltante" y a volver a cambiarlos un cambio después, con una ventana en la que la
    API arranca sin saber a qué cola hablar. Dos vueltas sobre el mismo validador por una sola
    variable de diferencia.
  - *Obligatorias y cableadas ya* (**elegida**): Compose pasa `REDIS_HOST: redis`, `REDIS_PORT: "6379"`
    y `REDIS_PASSWORD: "${REDIS_PASSWORD:?falta REDIS_PASSWORD}"` a `api`, y `.env.example` suma
    `REDIS_PASSWORD` con un valor de ejemplo. Nadie se conecta a Redis en 1b (no hay cliente ni
    servicio), así que un host que todavía no existe no rompe nada: la API sólo valida la forma de la
    variable. El cambio siguiente agrega el servicio y no toca la configuración.
  - **Lo que esta opción no tapa**: la ausencia de las variables en Compose y `.env.example` hoy, que
    rompe el arranque (punto 1 de "División del cambio"). **Para el auditor**: el informe del
    constructor dio por verde 1b sin correr el humo; la tarea 6.5 lo exige.
- **Alembic no depende de Redis ni de los parámetros** (tarea 6.1). Las migraciones sólo necesitan la
  base; que el trabajo `migraciones` falle por una variable de Redis acopla dos cosas que no tienen
  relación. Se separa la parte de PostgreSQL (la que usan `migraciones/env.py` y `crear_engine`) de
  la de procesos (Redis y parámetros, la que valida `crear_app()`), con el mismo armado de errores.
  **Alternativa más barata descartada**: pasar también las variables de Redis y montar `config/` en
  `migraciones`; funciona, pero cada variable nueva de la API tendría que repetirse en el trabajo
  de migraciones.
- Compose monta `../config:/app/config:ro` en `api` y define
  `PROPTECH_PARAMETROS=/app/config/parametros.yaml` (D6).
- Healthcheck de `db` entrecomillado:
  `pg_isready -U "$${POSTGRES_USER}" -d "$${POSTGRES_DB}"` (variables del contenedor, con comillas).
  Hecho (tarea 1.2).

### D12 · El chequeo de la imagen de PostgreSQL

- **Reemplazo del test tautológico**: `test_imagen_del_fixture_coincide_con_la_de_compose_db` se borró.
  En su lugar, un test de integración pide la imagen **del contenedor que corrió**
  (`get_wrapped_container().image.tags`) y la compara con Compose, nombrando las dos si difieren. Un
  test unitario aparte afirma que `conftest.py` no tiene una imagen escrita a mano (la deriva de
  Compose). Hecho (tarea 1.3).
- La extensión de ese chequeo a la imagen de Redis y el fixture `redis_contenedor` pasan a
  `cola-logs-y-respaldos`.

### D13 · Vuelta 2 (rompedor): dígitos no-ASCII y parsers que agotan recursos

El rompedor encontró tres fallas en el código ya construido (1b vuelta 1), las tres de la misma
familia que L-002 ("la configuración/los datos se rompen de muchas formas, no sólo faltando"):

- **Dígitos Unicode no-ASCII aceptados como si fueran 0-9.** `\d` en una expresión regular de Python,
  sin el flag `re.ASCII`, matchea cualquier dígito Unicode de categoría `Nd` (arábigo-índico,
  arábigo-índico extendido/persa, de ancho completo, etc.), y `Decimal()` los interpreta con su valor
  numérico igual que a los ASCII. Esto afectaba a los tres puntos de entrada de texto numérico del
  cambio: `_PATRON` de `Dinero` (D5, `dinero.py`), `_PATRON_PORCENTAJE` de `_validador_porcentaje`
  (D6, `parametros.py`, compartido por `tasa_mensual` y `fondo_de_reserva.porcentaje`) y
  `_PATRON_COEFICIENTE` (D10, `semilla.py`). Se agregó `re.ASCII` a los tres patrones y un test de
  regresión por punto de entrada (`test_rompedor_dinero_digitos_unicode.py`,
  `test_porcentaje_con_digitos_no_ascii_falla` en `test_parametros.py`,
  `test_coeficiente_con_digitos_no_ascii_falla` en `test_semilla.py`). **Descartado**: no se tocó la
  validación de `postgres_port`/`redis_port` en `configuracion.py` (enteros vía pydantic-settings).
  **Corrección (auditor, cambio 1b vuelta 3)**: esta nota decía que esos campos "también aceptan
  dígitos Unicode a través de `int()`"; es falso. `pydantic-core` no delega en el `int()` de Python
  al convertir un `str` de entorno a `int`: tiene su propio parser numérico, que ya rechaza dígitos
  Unicode no-ASCII (verificado: `int("١")` de Python da `1`, pero un campo `int` de pydantic con
  `"١"` levanta `int_parsing`). No hay ahí ninguna familia de L-002 pendiente; se descarta por eso,
  no porque nadie lo haya señalado.
- **Mensaje de la tasa negativa sin el rango.** `_validador_porcentaje` fallaba en el chequeo de
  *formato* antes de llegar al chequeo de *rango* para cualquier valor con signo, así que el mensaje
  nunca mencionaba el rango permitido pese a que la spec ("Tasa negativa") lo exige. El mensaje de
  formato ahora incluye siempre el rango (mínimo y máximo), para `tasa_mensual` y para
  `fondo_de_reserva.porcentaje` (mismo validador).
- **`RecursionError` sin capturar en `cargar_yaml`.** Un YAML chico (unos pocos KB) pero muy anidado
  agota la pila de recursión del parser antes de terminar, y el `RecursionError` se propagaba sin
  control a través de `leer_parametros` y `leer_semilla` (sólo atrapaban `ErrorDeCarga`) hasta el
  arranque de la API o el comando de la semilla. `cargar_yaml` ahora atrapa `RecursionError` y
  `MemoryError` (misma familia: agotar un recurso del proceso al parsear) y los convierte en
  `ErrorDeCarga`, sin traza ni contenido, igual que el resto de sus errores.
  **Corrección (auditor, cambio 1b vuelta 3)**: "igual que el resto de sus errores" no era cierto
  cuando se escribió esto. El `except yaml.YAMLError` de `cargar_yaml` armaba el mensaje con
  `f"...: {error}"`, y `str(error)` de PyYAML incluye el snippet de la línea que rompió el parseo
  (el texto exacto, con un `^` marcando la columna): un `tasa_mensual: "SECRETO-ABC` mal cerrado
  filtraba `SECRETO-ABC` en el mensaje. Arreglado en esa misma vuelta: ahora ese `except` también
  reporta sólo posición (línea y columna) y una descripción genérica, nunca `str(error)`; recién con
  ese cambio la frase es cierta para los cuatro `except` de la función. Además se agregó un
  límite de tamaño de archivo de **1 MiB** (`_TAMANIO_MAXIMO_BYTES`) como segunda barrera,
  independiente del límite de anidamiento: ni `config/parametros.yaml` ni
  `config/semilla/edificio-ejemplo.yaml` se acercan a ese tamaño. **Descartado**: limitar la
  profundidad de anidamiento explícitamente (recorrer el árbol y contar niveles) en vez de capturar
  `RecursionError`; más código para el mismo resultado, dado que PyYAML no expone un límite de
  profundidad configurable en su API pública.
- **Clave de YAML que no es texto (constructor, cambio 1b vuelta 4; L-009).** `leer_parametros`
  atajaba el `TypeError` de `Parametros(**datos)` (clave no-string al desempaquetar como kwargs) y lo
  reenviaba envuelto en `ParametrosInvalidos`, pero con el texto de la excepción de Python; `leer_semilla`
  no lo atajaba en absoluto y el mismo `TypeError`, con traceback, escapaba hasta el comando de la
  semilla. Se cierra una sola vez, en `cargar_yaml._construir_mapeo_sin_duplicados`: rechaza cualquier
  clave que no sea `str`, para la raíz y para cualquier mapa anidado (es el mismo constructor el que
  arma todos los niveles), antes de que ninguno de los dos lectores llegue a ver el dato.
  **Precisión, para que quede explícito**: los mensajes de este módulo (y los de sus dos lectores)
  pueden nombrar **claves** — nombres de campo, índices de lista, la clave repetida o no-texto en
  cuestión — porque son parte de la ruta al problema, no el contenido de un valor; lo que nunca
  incluyen es el **valor** asociado a esa clave ni el texto crudo de un error de PyYAML (L-002, D13
  vuelta 2/3). El mensaje de esta vuelta sigue esa regla: nombra el tipo recibido y la posición
  (línea, columna), nunca el valor de la clave ni el de su valor.

## Risks / Trade-offs

- [Una tasa mayor a 10 % mensual queda rechazada] → Tope elegido sin validar con un administrador
  (P4). Subirlo es cambiar una constante y su test.
- [La semilla no se carga en la base en este cambio] → Lo pide la ficha ("sólo lo que el esquema
  permita"). La ficha 3 se reescribe al archivar para que la cargue.
- [`REDIS_PASSWORD` obligatoria sin Redis desplegado] → Quien levante 1b tiene que inventar una
  contraseña que todavía no protege nada. Se acepta: es una línea de `.env` y evita tocar el
  validador dos veces (D11).
- [El tipo `Dinero` se usa para `cargo_fijo` en parámetros antes de que exista su aritmética] → Sólo
  se valida y se lee; el cambio 3 lo copia a la base.

## Migration Plan

- Sin migraciones de base. Para volver atrás: revertir el commit.
- Al actualizar una copia local existente: copiar `REDIS_PASSWORD` de `.env.example` a `.env`. Compose
  la nombra si falta.

## Open Questions

Ninguna que cambie las specs o las tareas.
