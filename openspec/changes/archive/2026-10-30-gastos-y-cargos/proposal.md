## Why

Hoy el sistema sabe **quién paga** (grupos de reparto, R01), **en qué se gasta** (categorías, R16) y
**cómo se anota la plata** (el libro del 4b), pero no tiene dónde guardar **qué se gastó**. Sin gastos
cargados no hay nada que repartir: el cambio 7 (`liquidacion-y-emision`) no puede existir, y el 14
(`lectura-de-facturas`) no tiene dónde dejar lo que lee. Este cambio construye el almacén del gasto y
del cargo particular, con su ciclo de aprobación, para que el 7 encuentre un conjunto cerrado de
"gastos aprobados del período" al que aplicarle el reparto del 4a.

Es además el primer cambio que usa de verdad `grupo_de_reparto` y `categoria_de_gasto` como claves
foráneas: hasta hoy nada referenciaba esas dos tablas, y por eso el 3c las dejó desactivables en vez
de borrables (R16, D-128), prometiendo explícitamente "cuando exista el módulo de gastos (cambio 6)".

## What Changes

- **Módulo `gastos` nuevo** en `backend/src/proptech_core/gastos/`, con `dominio/`, `aplicacion/` y su
  router en `proptech_api`. Hoy el paquete no existe (verificado: no hay `gastos/` bajo
  `proptech_core/`).
- **Proveedores por edificio**: alta, edición, desactivación (nunca borrado, mismo patrón que R16),
  con CUIT validado. El CUIT es la llave con que R12 identifica al emisor de una factura y con que R23
  (cambio 7) arma el historial de 6 períodos.
- **Gastos con los cuatro estados de D-075** (`borrador`, `sin_ia`, `en_revision`, `aprobado`), con
  proveedor, concepto, categoría obligatoria (R16), grupo de reparto (R01), período, importe, tipo
  ordinario o extraordinario (R13) y, cuando hay factura, su clave `cuit + ptoVta + tipoCmp + nroCmp`
  (R12). Los estados `sin_ia` y `en_revision` **se crean y se prueban acá** aunque recién los use el 14
  (D-078: "los cuatro estados de D-075 los crea el cambio 6").
- **Control de factura duplicada** dentro del edificio, por la clave completa de R12 (incluye el tipo
  de comprobante, para que una factura y su nota de crédito con el mismo número no choquen, R22).
- **Sueldo del encargado como un gasto más** (D-028): no se calcula nada; se carga el recibo que
  liquidó el contador, con su categoría y su grupo.
- **Cargos particulares** (R14, D-025): un importe contra **una sola unidad**, sueltos o importados en
  lote desde un Excel, en borrador hasta aprobarse.
- **Notas de crédito** (R22, D-061): asociadas obligatoriamente a la factura que corrigen, con el monto
  topeado al de esa factura, descontadas del gasto **antes** de prorratear y dentro del mismo grupo.
- **Aprobación** como transición de estado auditada, con el permiso
  `cargar_gastos_y_preparar_liquidacion` que ya existe en la matriz de D-106 (verificado en
  `acceso/dominio/permisos.py`): no se agrega ninguna acción nueva a la matriz de permisos.
- **Lecturas para el 7**: "gastos aprobados del período por grupo, netos de notas de crédito" y las
  consultas que alimentan los controles de R34 ("gasto mensual obligatorio faltante"). **El control en
  sí lo arma el 7** (D-079); acá sólo nace la consulta.
- **Vocabulario de auditoría ampliado** con los eventos del gasto (migración, como hicieron 3a y 3c).
- **Frontera de módulo**: `gastos` no importa `cuenta_corriente` ni `liquidacion`, y su SQL sólo nombra
  tablas propias (el test de fronteras del 4a ya vigila esta forma; hay que sumarle el módulo nuevo).

### Deuda heredada, ya saneada antes de este propose

El mutante de **RB-5** del 4a (`modo_de_coeficientes` nunca entraba a `campos` de `fijar_unidades`), que
D-130 asignó a este cambio, **ya fue resuelto en esta misma rama** antes de abrir el propose, en el
commit `2e2e925` (`complejos/aplicacion/grupos.py` y `acceso/aplicacion/auditoria.py`). No vuelve a
aparecer en `tasks.md`: queda cerrado y fuera del alcance de este change.

## Capabilities

### New Capabilities
- `proveedores`: los proveedores de cada edificio, con CUIT único, desactivables y nunca borrables,
  como base de R12 y del historial de R23.
- `gastos-del-periodo`: el gasto con sus cuatro estados (D-075), su categoría, grupo, período, tipo e
  importe; el control de factura duplicada de R12; la aprobación como única puerta al cálculo; y las
  lecturas de "gastos aprobados del período" que consume el 7.
- `notas-de-credito`: la nota de crédito asociada a la factura que corrige, con su tope y su efecto de
  descuento antes de prorratear, dentro del mismo grupo (R22, D-061, D-082).
- `cargos-particulares`: el importe contra una sola unidad, suelto o importado desde un Excel, con su
  aprobación y la garantía de que nunca se reparte entre las demás (R14, D-025).

### Modified Capabilities
- `auditoria-de-acciones`: el vocabulario cerrado de acciones suma los eventos del gasto (crear, editar
  y aprobar un gasto; crear, editar y aprobar un cargo particular; crear y editar un proveedor; cargar
  una nota de crédito), con su detalle de claves permitidas y **sin guardar importes**, igual que el
  resto de los eventos del padrón.
- `fronteras-de-modulos`: se suma el módulo `gastos` a las reglas vigentes — existe como paquete, no
  importa `cuenta_corriente` ni `liquidacion` en ninguna de sus capas, y su SQL nombra sólo tablas
  propias.

## Impact

- **Backend**: `backend/src/proptech_core/gastos/` (nuevo), `backend/src/proptech_api/gastos.py`
  (nuevo), `backend/src/proptech_api/app.py` (registrar el router).
- **Migraciones**: tablas nuevas (`proveedor`, `gasto`, `nota_de_credito`, `cargo_particular`) con
  Row-Level Security forzada por administración y las claves foráneas que atan cada fila a su edificio;
  más la ampliación del vocabulario de `accion_de_auditoria`. Numeración a partir de `0028` (la última
  en `main` era `0027`); al integrar `main` el 30/10/2026 quedaron `0029` a `0033`, detrás de
  `0028_ver_personal` del 2d.
- **Reutiliza sin tocar**: `compartido/reparto.py` y `compartido/dinero.py` (4a),
  `compartido/claves.py`, `acceso/aplicacion/auditoria.py` y `acceso/dominio/permisos.py`.
- **Habilita**: el 7 (`liquidacion-y-emision`) y el 14 (`lectura-de-facturas`).
- **No toca**: el libro de movimientos del 4b, ni la web.

## Gobernanza

**Nivel: MEDIUM.** No se pide firma de D-094/D-111 para este cambio.

Por qué, y contra qué se comparó:

1. **Juani ya lo clasificó.** D-130 (28/10/2026) dice, textual, que el 3d y el 6 "quedan en paralelo,
   porque ninguno de los dos toca el camino crítico ni una zona CRITICAL", y asigna el 6 a Emiliano.
   Esa es una decisión escrita y fechada de quien firma, no una inferencia nuestra.
2. **No es cobros ni cuenta corriente.** La regla dura del proyecto reserva CRITICAL a "cobros y cuenta
   corriente". Este cambio no escribe un solo movimiento en el libro (ver S-04 más abajo): guarda lo que
   el consorcio gastó. Quien convierte un gasto en deuda de un vecino es el 7, y ése sí es CRITICAL.
3. **No es HIGH.** HIGH cubre configuración que afecta datos de usuario, o inyección en archivos del
   usuario. Un gasto no es configuración del edificio: es un dato de operación que nace y muere dentro
   del alcance del edificio.
4. **No toca autenticación ni la matriz de permisos.** Reutiliza
   `Accion.CARGAR_GASTOS_Y_PREPARAR_LIQUIDACION`, que ya está en `permisos.py` desde el 2a.

**Condición de escalamiento, explícita**: este nivel vale mientras el cambio **no escriba en el libro
de movimientos**. Si durante el apply apareciera una tarea que inserta en `movimiento`, `obligacion` o
`imputacion`, el change **sube a CRITICAL en ese punto** y se frena hasta tener la firma escrita y
fechada de Juani, Alberto o Emiliano. No se construye esa tarea "mientras tanto".

## Supuestos y preguntas abiertas señaladas

### S-04 · ¿Este cambio escribe en el libro de movimientos? — resuelto como NO

CHANGES.md arrastra el supuesto S-04 del arquitecto del 4, "sin verificar contra R14 y R25". Lo
verificamos contra el texto de esas reglas:

- **R14** dice que los cargos particulares aprobados "entran en la expensa de esa unidad" **al
  liquidar**, y que los créditos particulares "se registran como corrección (R08), por la misma ruta que
  cualquier crédito de corrección — **construida en el 4b**". Es decir: R14 manda al 4b, no pide una
  ruta nueva.
- **R22** dice que la nota de crédito "se descuenta del gasto **antes de prorratear**": opera sobre el
  gasto, no sobre un movimiento.
- La ficha §6 cierra con "un gasto en borrador, sin IA o en revisión no aparece en ningún cálculo; sólo
  el aprobado entra" — y el cálculo es del 7.

**JUICIO (confianza alta)**: este cambio **no escribe en el libro**. Queda como punto a confirmar en la
revisión del propose, no como supuesto silencioso. De todas formas la dependencia está satisfecha: el 4b
está archivado desde el 27/10/2026, así que incluso con la lectura contraria el cambio podría arrancar.

### Preguntas abiertas que la ficha §6 marca como bloqueantes

`knowledge-base/10_preguntas_abiertas.md` marca **P25, P36 y P37 con "antes del cambio 6"**: bloquean
este change. No las inventamos; las dejamos acá con una propuesta y el pedido explícito de respuesta.

| Pregunta | Qué bloquea | Propuesta (a confirmar por Juani o Alberto) |
|---|---|---|
| **P36** · un gasto que quedó afuera de su período y se aprueba después, ¿entra en el siguiente? | **Bloquea el modelo**: define si el gasto tiene un período y basta, o además un "período en que se liquidó" | El gasto conserva su **período de origen** y entra en la **primera liquidación que lo encuentre aprobado**, igual que R22 hace con la nota de crédito de una factura ya liquidada (D-082: se descuenta en el período en que se carga, sin reabrir el emitido). Guardar los dos datos; nunca reabrir un emitido |
| **P37** · dónde y quién marca un "gasto mensual obligatorio" | **Bloquea el esquema**: la marca vive en la categoría, en el proveedor o en el gasto | En la **categoría de gasto** del edificio (una categoría marcada como obligatoria mensual): es la única de las tres que existe antes de que haya gastos, y es lo que permite al 7 decir "falta el gasto de ascensor de este mes" sin un gasto previo que mirar |
| **P25** · nota de crédito mayor que los gastos del período en que se carga | **No bloquea este change**: el reparto negativo sólo puede darse al liquidar (cambio 7) | Acá se construye sólo el tope de R22 (la nota no supera **su factura**). El caso "el reparto del grupo daría negativo" queda para el 7, con P25 todavía abierta |

Las otras dos que la ficha nombra **no bloquean**:

- **P15** (ingresos mayores que los gastos): R38 es **propuesta** y las propuestas "entran si se
  validan" (D-079). R38 **no entra en este change**; sin ingresos, P15 no tiene efecto acá.
- **P17** (IVA de los consorcios): el gasto se guarda por el **total de la factura**, sin desglose de
  IVA. Si un contador confirmara lo contrario, agregar el desglose es una migración aditiva más
  adelante, no un rediseño. **SUPUESTO declarado**, no verificado con un contador.

## Qué queda fuera del cambio

- **La lectura de facturas por QR y por IA** (cambio 14). Acá la carga es **manual**. Los estados
  `sin_ia` y `en_revision` se crean y se prueban, pero nadie los produce automáticamente todavía.
- **El control de monto atípico R23** (cambio 7/14): necesita el historial de 6 períodos, que recién
  existe con gastos cargados.
- **Los controles de R34 antes de emitir** (cambio 7, D-079): acá nacen las **consultas**, no los
  controles ni sus niveles.
- **Los ingresos del consorcio (R38)**: propuesta, bloqueada por P15.
- **Los cargos recurrentes del reglamento (R14, D-082)**: propuesta, los genera el motor de reglas
  (cambio 6b).
- **El consumo variable de agua** (D-026): se carga como cargos particulares por Excel, nada más.
- **El cálculo del sueldo del encargado** (D-028): se carga el recibo, no se liquida.
- **Toda pantalla.** Ver abajo.

### Decisión de alcance: este change es backend y API, sin pantallas

**Decidido por Emiliano, dueño del change, el 28/10/2026.** El change se llama `gastos-y-cargos`, no se
parte, y construye **las 30 tareas de backend y API completas**. Las pantallas de HU-A3 y HU-A3b quedan
para un **change nuevo, todavía sin crear y sin nombre definitivo**.

**El motivo real es un hueco del roadmap, no la continuación de un patrón.** Hay que decirlo así porque
la lectura cómoda sería "el 3 se partió en 3a (modelo y API) y 3b (pantallas), entonces el 6 hace lo
mismo" — y esa lectura es **falsa**: el 3a dejó las pantallas a un change **ya planificado** (el 3b), y
el 4a y el 4b nombran explícitamente a qué change futuro le toca cada pantalla que no construyeron ("la
pantalla de corrección, `pesos()` y la API falsa (8, D-120)", "la acción de anular en sí, con su
ventana y motivo en pantalla (7, D-124)"). Revisado el roadmap completo de `CHANGES.md` el 28/10/2026,
**`gastos-y-cargos` no nombra a ningún consumidor de pantalla en ningún lado**: no hay change hermano
planificado para HU-A3 ni HU-A3b, ni en el árbol de dependencias, ni en los gates de paralelismo, ni en
la ficha §6. Dejar el scope sin pantallas invocando un precedente que acá no existe habría escondido
ese hueco en vez de registrarlo.

Por eso la decisión se toma de frente y se registra fuera de `openspec/`, donde la va a encontrar quien
planifique lo que sigue: en la entrada `[C-09]` de `CHANGES.md`, en la ficha §6 de
`knowledge-base/12_fichas_de_changes.md` y como decisión propia en
`knowledge-base/09_decisiones_y_supuestos.md` (**D-140**).

**Qué implica para este change**: HU-A3 y HU-A3b describen criterios de aceptación de administrador que
acá **se verifican contra la API**, no contra una pantalla. El change nuevo que construya la superficie
web necesitará, como el 3b, su sesión de `impeccable shape` por pantalla antes del propose (D-102);
nombrarlo y ubicarlo en el roadmap es una decisión de quien coordine, no de este propose.

## Knowledge Base Impact

| Archivo | Qué pasa | REWRITE / APPEND |
|---|---|---|
| `knowledge-base/04_modelo_de_datos.md` | Las cuatro entidades nuevas (`proveedor`, `gasto`, `nota_de_credito`, `cargo_particular`) pasan de "planificadas" a existentes, con su ERD | **REWRITE** |
| `knowledge-base/05_reglas_de_negocio.md` | R12, R13, R14, R16 y R22 pasan a tener código que las sostiene; R12 queda acotada a su parte manual (el QR y la IA siguen en el 14) | **REWRITE** |
| `knowledge-base/12_fichas_de_changes.md` | La ficha §6 se cierra con lo construido, lo que quedó afuera y la deuda del cierre; la ficha §4a anota RB-5 como cerrada por `2e2e925` | **REWRITE** |
| `knowledge-base/09_decisiones_y_supuestos.md` | **D-140 ya entró con este propose** (pantallas sin change hermano, decisión de Emiliano del 28/10/2026). Las respuestas a P36 y P37, y cualquier decisión nueva del apply, entran después como D-NNN nuevas | **APPEND** |
| `knowledge-base/10_preguntas_abiertas.md` | P36 y P37 se marcan resueltas con su D-NNN; P25 sigue abierta y pasa a "antes del cambio 7"; P15 y P17 siguen abiertas | **REWRITE** |
| `knowledge-base/15_lecciones.md` | Las lecciones que proponga el auditor al cerrar | **APPEND** |
| `knowledge-base/06_funcionalidades.md` | HU-A3 y HU-A3b quedan cubiertas en su parte manual y de API; se aclara qué parte espera al 14 y qué parte espera pantallas | **REWRITE** |
| `CHANGES.md` | **La nota de "No construye" ya entró con este propose** (pantallas pendientes de un change nuevo). Al cerrar, el `[C-09]` pasa a `[x]` con la nota de que no escribe en el libro (S-04 resuelto) | **REWRITE** |
| `knowledge-base/02_descripcion_general.md` | El módulo `gastos` deja de estar vacío en la lista de módulos | **REWRITE** |
| `knowledge-base/11_glosario.md` | Entran "proveedor", "nota de crédito" y "cargo particular" con su definición | **REWRITE** |

No afectan: `01`, `03`, `07`, `08`, `13`, `14`, `16` — este change no mueve visión, actores, flujos de
punta a punta, arquitectura, el motor de reglas, la forma de trabajo ni las fases post-MVP.

## Lecciones aplicadas (`knowledge-base/15_lecciones.md`)

| Lección | Cómo la cubre este change |
|---|---|
| **L-023** · una migración con `NOT NULL` o `CHECK` rompe fuera de `backend/` | Antes de cerrar cada migración, `rg` de todo `INSERT` a las tablas nuevas en el repo entero, incluido `infra/ci/humo.sh` y la semilla |
| **L-019 / L-035** · un test que no puede dar rojo es peor que no tenerlo | Cada garantía nueva (el tope de R22, el duplicado de R12, el cargo que no se reparte) lleva su **mutante dirigido** que la hace fallar en su propia aserción, no antes |
| **L-034 / L-049** · el mutante tiene que fallar en la aserción que el test dice probar | Cada RED se lee línea por línea del traceback; un rojo que muere en un helper o en la autenticación no cuenta |
| **L-041** · un chequeo de arranque cierra con la suite completa | Si alguna tarea toca `roles.py`, `tablas_protegidas.py` o cualquier fixture que levante la app, cierra con la suite entera, no con su grupo |
| **L-051** · arreglar el campo que encontró el QA no deja una regla | Todo campo nuevo con límite o patrón (CUIT, importe, período) expone su formato en la ayuda y en el error **desde una constante compartida**, no con un mensaje genérico |
| **L-016** · una observación tiene que poder dar otro resultado | Ningún test afirma "0 gastos en el cálculo" sin que exista un caso donde ese número pueda ser distinto |
| **L-010 / L-031** · la corrida de cierre va después del último commit | La suite de cierre corre sobre el SHA final, con `git rev-parse HEAD` anotado al lado |
| **L-042** · "pusheé" no es "leí el CI verde" | Antes de citar CI de esta rama, `gh run list --commit <sha>`; si está vacío, se dispara y se lee |
| **L-025 / L-024** · el constructor no se revisa a sí mismo | El rompedor y el auditor son de una familia distinta a la del constructor, y la última vuelta de arreglos la cierran revisores de rol de sólo lectura |
| **L-012** · la deuda se asigna al primer cambio que usa la pieza | Toda deuda del cierre se asigna leyendo `CHANGES.md`, no por cercanía temática |
| **L-047** · `infra/ci/humo.sh` fija `-p proptech` | Si el cierre corre humo, va con el envoltorio que fuerza un `-p` propio; nunca contra el stack real sin avisar |
