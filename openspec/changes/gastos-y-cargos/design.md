## Context

Ver `proposal.md` · Why. Lo que el repositorio ya tiene y condiciona este diseño, verificado en el
código:

- **No existe `backend/src/proptech_core/gastos/`.** Es un módulo nuevo entero.
- **El patrón hexagonal del proyecto** está ejercitado en `complejos/`: `dominio/` (reglas puras, sin
  SQLAlchemy ni psycopg, D-021), `aplicacion/` (casos de uso con `Session` y SQL por `text()`),
  `puertos.py`/`adaptadores/` cuando hay infraestructura externa. `complejos/aplicacion/categorias.py`
  es el ejemplo más cercano a lo que hay que escribir acá (CRUD por edificio, con auditoría,
  desactivación en vez de borrado y derivación de clave).
- **El reparto ya existe** en `compartido/reparto.py` (`repartir`, `redondear_al_centavo`,
  `ParteARepartir`, mayor resto, medio hacia arriba). Este cambio **no lo usa**: el reparto por unidad
  lo hace el 7. Acá sólo se suman importes por grupo.
- **`Dinero`** está en `compartido/dinero.py` (4a: suma y resta), con su tipo de SQLAlchemy en
  `compartido/dinero_sqlalchemy.py`.
- **La auditoría** se usa con el decorador `@accion_sensible(Evento...)` + `registrar`, en
  `acceso/aplicacion/auditoria.py`, con el vocabulario en `acceso/dominio/eventos.py`
  (`EventoDeAcceso`, `EventoDelPadron`) y la lista cerrada en la base (`accion_de_auditoria`).
- **El permiso ya existe**: `Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION` en
  `acceso/dominio/permisos.py`, desde el 2a. No hay que tocar la matriz de D-106.
- **Row-Level Security** se aplica con la ayuda `migraciones/ayudas_rls.aislar_por_administracion`,
  usada por `0023`.
- **Última migración en `main`: `0027`.** Las de este cambio arrancan en `0028`.
- **Alcance y errores**: el orden de D7 es cargar el recurso → 404 si no existe o no alcanza → 403 si
  no puede. `complejos/aplicacion/errores.py` tiene `NoEncontrado`, `EntradaInvalida`,
  `error_de_validacion` y `transaccion(sesion, conflictos)`.

## Goals / Non-Goals

**Goals:**

- Un módulo `gastos` autocontenido, que nadie más importa todavía, con su frontera vigilada por el test
  del 4a.
- Un conjunto de tablas nuevas y **vacías**, con sus `CHECK` y claves foráneas transaccionales desde el
  día uno (el mismo patrón de `0023`: tabla nueva y vacía permite constraints sin ventana de riesgo).
- Que el cambio 7 encuentre **una sola lectura** por la que pedir "los gastos aprobados del período,
  netos y agrupados", sin tener que entender el esquema de gastos.
- Que la aprobación sea la única puerta al cálculo, y que eso esté probado con un mutante, no afirmado.

**Non-Goals:**

- **No se escribe en el libro de movimientos.** Ni un `INSERT` en `movimiento`, `obligacion` ni
  `imputacion` (ver D1). La frontera de módulos lo vigila.
- **No hay tablas de sólo agregar nuevas.** Un gasto se edita mientras está en borrador; eso es
  deliberado (D4).
- No hay pantallas (ver `proposal.md` · Decisión de alcance).
- No hay lectura de QR ni IA (cambio 14), ni control de monto atípico R23 (cambio 7).
- No hay ingresos del consorcio R38 (propuesta, bloqueada por P15).

## Decisions

### D1 · Este cambio no escribe en el libro de movimientos

**Decisión**: `gastos` guarda gastos, notas de crédito y cargos particulares en tablas propias. Nada
de lo que hace genera un movimiento, una obligación ni una imputación. El 7 lee de acá y escribe allá.

**Por qué** (contra R14 y R25, que es lo que S-04 pedía verificar): R14 manda los créditos particulares
a "la misma ruta que cualquier crédito de corrección — construida en el 4b", y manda los cargos
aprobados a la expensa "al liquidar"; R22 opera "antes de prorratear". Las tres apuntan al 7 o al 4b,
ninguna pide una ruta nueva.

**Alternativa descartada**: que aprobar un cargo particular generara ya su movimiento en la cuenta de
la unidad. Más directo, pero rompe R08 (la cuenta corriente sólo agrega movimientos y una corrección es
un movimiento nuevo): un cargo aprobado y después corregido antes de emitir obligaría a un
contra-asiento por algo que todavía no es deuda de nadie. Además subiría el change a CRITICAL.

**Consecuencia operativa**: si durante el apply aparece una tarea que necesita escribir en el libro, se
**frena** y se pide la firma. Está escrito en `proposal.md` · Gobernanza.

### D2 · Cuatro tablas, no una tabla polimórfica

**Decisión**: `proveedor`, `gasto`, `nota_de_credito` y `cargo_particular`, cada una con sus columnas y
sus `CHECK`.

**Por qué**: un gasto y un cargo particular comparten el importe y el período, y nada más. El gasto
apunta a un grupo de reparto y nunca a una unidad; el cargo apunta a una unidad y nunca a un grupo.
Una tabla única obligaría a `CHECK (num_nonnulls(grupo_id, unidad_id) = 1)` y a que toda consulta
filtre por discriminante — exactamente el tipo de columna nullable que después alguien olvida filtrar.
Con dos tablas, "un cargo particular nunca se reparte" es una propiedad del esquema, no de una
consulta bien escrita.

**Alternativa descartada**: una tabla `concepto_a_cobrar` con discriminante. Descartada por lo anterior
y porque R14 dice explícitamente que el cargo "no afecta el reparto de los demás": conviene que la base
lo haga imposible.

### D3 · La clave de factura vive en el gasto, no en el proveedor

**Decisión**: `gasto` lleva las cuatro columnas de la clave de R12 (`cuit_emisor`, `punto_de_venta`,
`tipo_de_comprobante`, `numero_de_comprobante`), nullable en bloque, con
`CHECK (num_nonnulls(...) IN (0, 4))` para que vengan las cuatro o ninguna. El índice único parcial es
`(complejo_id, cuit_emisor, punto_de_venta, tipo_de_comprobante, numero_de_comprobante) WHERE
cuit_emisor IS NOT NULL`.

**Por qué el CUIT en el gasto y no sólo el `proveedor_id`**: R12 identifica la factura por el CUIT del
**emisor**, que es el dato del comprobante. Un proveedor podría corregir su razón social, o un gasto
podría cargarse con factura antes de que exista su proveedor en el padrón. El `proveedor_id` queda
igual, opcional, para el historial de R23 del 7.

**Por qué el índice es parcial**: el sueldo del encargado y cualquier gasto sin factura no tienen clave,
y en PostgreSQL varios `NULL` no chocan en un único — pero el índice parcial lo deja explícito y más
barato.

**Por qué el tipo de comprobante está en la clave**: R22 lo exige, para que una factura y su nota de
crédito con el mismo número no se marquen duplicadas entre sí.

### D4 · El gasto se edita en borrador; aprobado es inmutable en lo que mueve plata

**Decisión**: con el gasto en `borrador`, `sin_ia` o `en_revision` se puede editar todo. Con el gasto
`aprobado`, no se puede cambiar importe, grupo, período ni tipo; para corregir hay que desaprobarlo
(acción propia y auditada) o cargar la nota de crédito si el error fue del proveedor.

**Por qué no una tabla de sólo agregar**: las tablas de sólo agregar (D-115, `tablas_protegidas.py`)
existen porque sus filas **son** la verdad contable. Un gasto en borrador es un papel sobre el
escritorio: se tacha y se vuelve a escribir. Protegerlo obligaría a una fila nueva por cada tipeo, y a
que el 7 tuviera que elegir la "última versión" de cada gasto — complejidad sin beneficio. Lo que sí es
contable (lo que el vecino termina pagando) lo escribe el 7 en el libro, que **sí** es de sólo agregar.

**Trazabilidad**: la auditoría cubre el hueco. Toda edición y toda aprobación dejan su fila con los
nombres de los campos que cambiaron, sin valores (misma regla de los eventos del padrón).

### D5 · Las notas de crédito se topean con un bloqueo de fila sobre su factura

**Decisión**: al cargar una nota de crédito, la transacción hace `SELECT ... FROM gasto WHERE id = :id
FOR UPDATE` sobre la factura y recién después suma las notas existentes y compara contra el importe.
El `CHECK` de la base cubre el monto individual positivo; el tope acumulado lo garantiza el bloqueo.

**Por qué**: el escenario "dos notas de crédito simultáneas que juntas superan la factura" es
exactamente el tipo de carrera que un `CHECK` por fila no puede ver. Es el mismo patrón que
`categorias.py` ya usa con `_bloquear_edificio` para serializar el cálculo del orden.

**Alternativa descartada**: una columna `acreditado` denormalizada en `gasto`, actualizada con
`UPDATE ... SET acreditado = acreditado + :monto` y un `CHECK (acreditado <= importe)`. Es atómico sin
bloqueo explícito y más rápido, pero duplica la verdad: si alguien inserta una nota sin pasar por el
caso de uso, los dos números se separan en silencio. Preferimos una verdad sola, derivada.

### D6 · La importación de Excel es todo o nada, y valida antes de escribir

**Decisión**: se parsea la planilla entera, se validan todas las filas contra el padrón del edificio en
una sola consulta, se junta la lista completa de errores y recién si está vacía se insertan los cargos,
en una transacción. La respuesta de error nombra **todas** las filas con problema, con su número.

**Por qué nombrar todas y no la primera**: quien importa 200 cargos y recibe "fila 7 inválida" corrige
y vuelve a subir para recibir "fila 12 inválida". El costo de juntar la lista es nulo; el costo de no
hacerlo lo paga el administrador en cada vuelta.

**Formato**: el parseo del archivo vive en un adaptador (`gastos/adaptadores/`), detrás de un puerto que
devuelve filas ya tipadas. El caso de uso no sabe que existe Excel. Eso deja al cambio 5
(`importacion-desde-excel`) libre de reusar el mismo puerto con otro lector si hace falta.

### D7 · Dónde vive la marca de "gasto mensual obligatorio" — propuesta sujeta a P37

**Decisión propuesta**: una columna `obligatorio_mensual BOOLEAN NOT NULL DEFAULT false` en
`categoria_de_gasto`.

**Por qué la categoría y no el proveedor ni el gasto**: la pregunta que el control de R34 tiene que
contestar es "¿falta algo este mes?", y eso exige una lista que exista **sin que haya gastos**. El gasto
no sirve (es lo que falta). El proveedor tampoco: un edificio puede cambiar de empresa de ascensores y
el ascensor sigue siendo obligatorio. La categoría es la única de las tres que describe "en qué se
gasta todos los meses" con independencia de quién lo factura.

**P37 está abierta y es de Juani o Alberto.** Si la respuesta fuera "en el proveedor", el cambio es una
columna en otra tabla y la consulta cambia su `JOIN`; el resto del diseño no se mueve. Por eso la tarea
que la implementa está marcada como bloqueada en `tasks.md` y no arranca sin respuesta.

### D8 · Período de origen y período de imputación — propuesta sujeta a P36

**Decisión propuesta**: `gasto` lleva `periodo` (el del gasto, siempre) y `periodo_de_imputacion`
(el período en que entra a liquidar, que arranca igual a `periodo`). Un gasto que queda afuera de su
período y se aprueba después se imputa en el **primer período no emitido** al momento de aprobarlo; el
sistema lo fija al aprobar y lo deja registrado. Nunca se reabre un período emitido.

**Por qué**: es la misma mecánica que D-082 ya fijó para la nota de crédito de una factura ya liquidada
("se descuenta en el período en que se carga, sin reabrir el emitido"). Tener dos columnas conserva el
dato de cuándo se gastó de verdad, que la contabilidad del consorcio necesita, sin mentir sobre cuándo
se cobró.

**P36 está abierta y es de Juani o Alberto.** Si la respuesta fuera "no entra nunca en otro período",
`periodo_de_imputacion` desaparece y el gasto tardío simplemente no se liquida. La tarea que lo
implementa está marcada como bloqueada en `tasks.md`.

### D9 · Row-Level Security y dueño de las tablas

**Decisión**: las cuatro tablas nuevas usan `aislar_por_administracion` (la misma ayuda de `0023`), con
RLS **forzada**, y el dueño es `proptech_migrador`, no el rol de arranque. Cada tabla lleva
`administracion_id` y `complejo_id` `NOT NULL`, con claves foráneas compuestas contra `complejo` para
que la base rechace un cruce de edificio aunque la aplicación se equivoque (mismo patrón que 3a, R3A-3
y RF-D-1).

**Por qué el migrador y no el rol de arranque**: el rol de arranque es dueño sólo de las tablas de
**sólo agregar** (D-115, `tablas_protegidas.py`). Ninguna de estas cuatro lo es (ver D4), así que meter
el rol de arranque acá rompería la propiedad que el chequeo de arranque verifica.

### D10 · Lecturas pensadas para el 7, no para la web

**Decisión**: la API expone dos lecturas de consumo del 7, además del CRUD:

1. `GET .../periodos/{periodo}/gastos-aprobados` — totales por grupo, netos de notas de crédito, con
   bloques ordinaria/extraordinaria y subtotales por categoría.
2. `GET .../periodos/{periodo}/obligatorios-faltantes` — qué gastos mensuales obligatorios no tienen
   gasto aprobado en el período, **sin nivel de alerta ni bloqueo** (el control es del 7, D-079).

Las sumas se hacen en SQL con `NUMERIC` y se devuelven como texto. Ninguna de las dos reparte por
unidad.

**Por qué separadas del CRUD**: el 7 no debería paginar el listado de gastos para sumar. Una lectura
con la forma exacta que necesita evita que el 7 reimplemente la regla "sólo el aprobado entra" — que es
precisamente la regla que más barato sale romper por accidente.

## Risks / Trade-offs

| Riesgo | Mitigación |
|---|---|
| **P36 y P37 sin respuesta** frenan dos tareas con efecto en el esquema | Esas tareas están marcadas bloqueadas en `tasks.md` y no arrancan sin la respuesta. El resto del change avanza sin ellas: son una columna cada una, aditivas |
| **El 7 reimplementa "sólo el aprobado entra"** y se olvida del filtro | D10: una sola lectura con la forma que el 7 necesita, con su mutante que la prueba. El 7 no debería tener que filtrar nada |
| **Una migración con `NOT NULL` rompe fuera de `backend/`** (L-023) | Antes de cerrar cada migración, `rg` de todo `INSERT` a las tablas nuevas en el repo entero, incluido `infra/ci/humo.sh` y la semilla. Las cuatro tablas nacen vacías, así que el riesgo real es bajo, pero el chequeo se hace igual |
| **Un test de aprobación que no puede dar rojo** (L-019, L-035) | Cada garantía (tope de R22, duplicado de R12, cargo que no se reparte, borrador que no entra) lleva su mutante dirigido, con el traceback leído línea por línea para confirmar que cae en su propia aserción (L-034, L-049) |
| **El `CHECK` de la clave de factura en bloque** puede rechazar una carga legítima con sólo tres de los cuatro datos | Es deliberado: una clave parcial no sirve para el control de duplicados y lo volvería silenciosamente inútil. El error nombra los campos que faltan |
| **La columna en `categoria_de_gasto` (D7) toca una tabla del 3a** | Es aditiva, con `DEFAULT false`, y su `down` la quita. No cambia ninguna garantía existente de `categorias-de-gasto` |
| **El importador de Excel abre una superficie de parseo** | El adaptador no ejecuta fórmulas, no sigue enlaces externos y acota el tamaño del archivo y la cantidad de filas; valida todo contra el padrón antes de escribir |

## Migration Plan

1. **`0028_gastos_y_proveedores`** — `proveedor` y `gasto` con sus `CHECK`, claves foráneas compuestas
   contra `complejo`, el índice único parcial de la clave de factura y RLS forzada.
2. **`0029_notas_de_credito_y_cargos`** — `nota_de_credito` y `cargo_particular`, con RLS forzada y sus
   claves foráneas (la nota contra `gasto`, el cargo contra `unidad`, las dos con el par
   `administracion_id, complejo_id`).
3. **`0030_vocabulario_del_gasto`** — los diez eventos nuevos en `accion_de_auditoria`.
4. **`0031_categoria_obligatoria_mensual`** — la columna de D7. **Bloqueada por P37**: si la respuesta
   cambia el dueño de la marca, esta migración se escribe contra otra tabla.

Cada `down` se ejecuta contra una copia real antes de darla por buena (regla fija del DBA del
proyecto). Las cuatro tablas nacen vacías, así que el `downgrade` no pierde datos de negocio; el de
`0031` sí borra la marca, y eso queda escrito en la migración.

**Orden de los bloques de apply** (ver `tasks.md`): fronteras y esqueleto del módulo → proveedores →
gastos y sus estados → notas de crédito → cargos particulares e importación → lecturas para el 7 →
cierre. Cada bloque cierra con su suite; el que toque un chequeo de arranque cierra con la suite
completa (L-041).

## Open Questions

Estas no cambian specs, enfoque ni tareas; se pueden contestar después sin reabrir nada:

- **P17 · IVA**: guardamos el total de la factura, sin desglose. Si un contador dijera que hace falta
  separar el IVA, es una columna aditiva. **SUPUESTO declarado**, no verificado.
- **P25 · nota de crédito mayor que los gastos del período**: acá sólo se construye el tope contra la
  propia factura, que es lo que R22 exige. El caso "el reparto del grupo daría negativo" es del 7.
- **Qué pasa con una nota de crédito sobre un gasto que se desaprueba después**: hoy la nota queda y el
  neto sigue el estado del gasto. Nadie lo pidió todavía; si aparece, es una regla nueva, no un cambio
  de esquema.

Lo que **no** está acá porque sí cambia el diseño y necesita respuesta antes de construir su tarea:
**P36** (D8) y **P37** (D7).
