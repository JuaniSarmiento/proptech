## Context

Motivación y alcance en `proposal.md`. Lo que sigue es el estado del código que condiciona el cómo (HEAD
`84badd1`, 26/10/2026, rama `change/libro-de-movimientos`):

- `proptech_core/cuenta_corriente/` existe vacío (`__init__.py`, `dominio/`, `aplicacion/`), vigilado por
  las cinco reglas de D-116.
- `compartido/tablas_protegidas.py` declara `TABLAS_DE_SOLO_AGREGAR` con `auditoria` y
  `configuracion_versionada`, cada una con el texto de su `RAISE` y sus triggers. `roles antes` no se las
  devuelve al migrador; `roles despues` les transfiere tabla y función, revoca `UPDATE, DELETE, TRUNCATE`
  a la app, deja `SELECT, INSERT` y verifica por el efecto (`UPDATE ... WHERE false`, `DELETE ... WHERE
  false`, `TRUNCATE` con `CASCADE` si hay FK entrante), sin armar filas (D-114.4, D-115). La API, el
  worker, `alta_inicial` y `ejemplo` no arrancan si una tabla de la lista falta o no es de un superusuario.
- El trigger por sentencia bloquea `INSERT ... ON CONFLICT DO UPDATE` aunque no haya conflicto; `DO
  NOTHING` no (EVIDENCIA de DB-5 del 4a).
- `migraciones/ayudas_rls.py:aislar_por_administracion(tabla, permisos=...)` deja RLS forzada, la
  política por `app.administracion_id` y el `GRANT`. `complejo` tiene único `(administracion_id, id)`,
  `unidad` `(administracion_id, complejo_id, id)` y `persona` `(administracion_id, id)` (`0003`): las FK
  compuestas del libro se apoyan en ellos.
- `complejos/aplicacion/` es el patrón de D-120: SQL con `text()` sobre la `Session` del que llama,
  `FOR UPDATE` sobre tablas que la app puede actualizar (`categorias.py:34`, `grupos.py:54`,
  `unidades.py:152`), errores propios (`errores.py`) que `proptech_api/complejos.py` traduce a 404
  `{"detail": "no encontrado"}`, 409 `{"detail": "conflicto", "campo": ...}` y 422 con la forma de
  FastAPI; el 403 es `{"detail": {"detalle": "sin_permiso", "permiso_faltante": ...}}` y el 401 lo da
  `RutaConIdentidad` antes de leer el cuerpo.
- `acceso/dominio/permisos.py`: `Accion` es a la vez permiso y vocabulario de auditoría; la matriz
  `_MATRIZ` sigue a D-106. `acceso/aplicacion/auditoria.py:registrar()` exige transacción y valida el
  detalle por acción.
- `infra/ci/ensayo-roles.sh` baja hasta `0016` y vuelve; desde el 4a devuelve `configuracion_versionada`
  al migrador antes de bajar (`c345467`). No corre en CI (L-043).
- `hypothesis` ya está en el grupo `dev` (4a), con perfil `ci` derandomizado.

## Goals / Non-Goals

**Goals:**

- Que la deuda de cada cuenta viva en un libro que la base, y no la aplicación, impide editar o borrar, y
  que todo lo demás (residual, crédito a favor, saldo anterior) se calcule desde él.
- Que dos escrituras de la misma cuenta nunca imputen sobre la misma foto, y que dos de cuentas
  distintas no se esperen.
- Que cada garantía que vive en PostgreSQL tenga su test contra PostgreSQL real, con su mutante (L-035).
- Que el 4c, el 7 y el 8 encuentren hechas las columnas y las funciones que necesitan, sin pedir un
  `ALTER` sobre una tabla protegida.

**Non-Goals:**

- Intereses, saldo inicial, moroso crítico (4c); cambio de titular (4d); la acción de anular y la
  emisión real (7); pagos (8).
- Pantalla (D-120).
- El préstamo de propiedad para migraciones futuras (D-115.3).

## Decisions

### D0 · Sin puerto de repositorio (D-120)

Reglas puras en `cuenta_corriente/dominio/`, sin base: `imputacion.py` (`Componente`,
`ORDEN_DE_IMPUTACION`, `imputar(deudas, importe, destino)`) y `estado.py` (`calcular_estado(...)`).
Persistencia en `cuenta_corriente/aplicacion/` con SQL sobre la `Session` del que llama: `cuentas.py`
(cuenta de unidad y candado), `emisiones.py`, `creditos.py`, `correcciones.py`, `lecturas.py`,
`errores.py`. Todo caso de uso exige `sesion.in_transaction()`, nunca hace `commit` ni encola (explore
4.6). Imports permitidos: `compartido.dinero`, `acceso.dominio.identidad`, `acceso.dominio.permisos`,
`acceso.aplicacion.auditoria` (D-116).

- **Descartado**: `Protocol` de repositorio con doble en memoria (D-120).
- **Costo de revertir**: refactor mecánico, sin migración.

### D1 · Siete tablas en una migración, `0023`

Seis de sólo agregar y una de candados (D2). Todas con `administracion_id NOT NULL`, RLS forzada por
`aislar_por_administracion`, montos `NUMERIC(14,2)` leídos con `Dinero.desde_decimal`, ids `UUID` que
genera la aplicación. Cada tabla de sólo agregar lleva su función `fn_<tabla>_bloqueada()` con `RAISE
EXCEPTION '<tabla> no admite %', TG_OP` y tres triggers con esa función: `trg_<tabla>_sin_update_delete`
(por fila), `trg_<tabla>_sin_truncate` (`BEFORE TRUNCATE`) y `trg_<tabla>_sin_update_delete_por_sentencia`
(`BEFORE UPDATE OR DELETE ... FOR EACH STATEMENT`), y se declara en `TABLAS_DE_SOLO_AGREGAR` con ese
texto y esos tres nombres. `roles.py` no cambia de lógica (D1 del 4a).

| tabla | columnas | claves y restricciones |
|---|---|---|
| `cuenta` | `id`, `administracion_id`, `complejo_id`, `unidad_id` nulo, `persona_id` nulo, `creada_en` | `CHECK num_nonnulls(unidad_id, persona_id) = 1`; FK compuestas a `complejo`, `unidad` (`administracion_id, complejo_id, unidad_id`) y `persona`; único `(administracion_id, complejo_id, id)`; único parcial `(administracion_id, unidad_id)` y `(administracion_id, complejo_id, persona_id)` |
| `candado_de_cuenta` | `cuenta_id` PK, `administracion_id` | FK compuesta a `cuenta`; **no** protegida (D2) |
| `emision` | `id`, `administracion_id`, `complejo_id`, `periodo`, `intento`, `registrada_por`, `request_id`, `registrada_en` | `CHECK periodo = date_trunc('month', periodo)::date`; `CHECK intento >= 1`; único `(administracion_id, complejo_id, periodo, intento)` (D4); único `(administracion_id, complejo_id, id)` |
| `evento_de_emision` | `id`, `administracion_id`, `complejo_id`, `emision_id`, `tipo`, `motivo`, `persona_id`, `request_id`, `registrado_en` | `CHECK tipo IN ('anulada')`; `CHECK btrim(motivo) <> ''`; FK compuesta a `emision`; único `(administracion_id, emision_id, tipo)` |
| `obligacion` | `id`, `administracion_id`, `complejo_id`, `cuenta_id`, `emision_id` nulo, `operacion_id` nulo, `periodo`, `vencimiento`, `ordinaria`, `fondo_de_reserva`, `extraordinaria`, `registrada_en` | `CHECK num_nonnulls(emision_id, operacion_id) = 1` (emisión o saldo inicial del 4c, H-03); los tres importes `>= 0` y su suma `> 0`; período primer día del mes; FK compuestas a `cuenta` y `emision` por `(administracion_id, complejo_id, ...)`; único parcial `(administracion_id, emision_id, cuenta_id)` y `(administracion_id, operacion_id, cuenta_id, periodo)`; único `(administracion_id, cuenta_id, id)` |
| `movimiento` | `id`, `administracion_id`, `complejo_id`, `cuenta_id`, `tipo`, `sentido`, `importe`, `fecha_valor`, `registrado_por`, `request_id`, `registrado_en`, `operacion_id` nulo, `emision_id` nulo, `obligacion_id` nulo, `componente` nulo, `corte` nulo, `corrige_a` nulo, `tipo_corregido` nulo, `enlazado_a` nulo, `motivo` nulo | ver abajo |
| `imputacion` | `id`, `administracion_id`, `cuenta_id`, `movimiento_id`, `sentido_del_movimiento`, `obligacion_id`, `componente`, `importe`, `corrida_id`, `registrada_en` | `CHECK importe > 0`; `CHECK sentido_del_movimiento = 'credito'` con la FK `(administracion_id, cuenta_id, movimiento_id, sentido_del_movimiento)` a `movimiento (administracion_id, cuenta_id, id, sentido)`: **la base** impide imputar un débito; FK `(administracion_id, cuenta_id, obligacion_id)`: **la base** impide imputar a otra cuenta; único `(administracion_id, corrida_id, movimiento_id, obligacion_id, componente)` |

**`movimiento`**, restricciones:

- `tipo IN ('interes', 'pago', 'correccion', 'condonacion', 'ajuste_de_interes', 'bonificacion',
  'reimputacion', 'baja_de_deuda', 'saldo_inicial')`; `sentido IN ('debito', 'credito')`; `componente
  IN ('interes', 'ordinaria', 'fondo_de_reserva', 'extraordinaria')`; `importe > 0`.
- `interes` es débito, con `obligacion_id`, `componente = 'interes'` y `corte` no nulos, y único parcial
  `(administracion_id, obligacion_id, corte) WHERE tipo = 'interes'` (su idempotencia, para el 4c).
- `correccion` puede ser débito (sólo como contra-asiento) o crédito; los demás tipos son créditos.
- Un débito sin `corrige_a` lleva `obligacion_id` y `componente` (es deuda de un componente).
- Destinos fijos de D-086: `condonacion` y `ajuste_de_interes` exigen `obligacion_id` y `componente =
  'interes'`; `bonificacion` exige `obligacion_id` y `componente = 'ordinaria'`.
- Todo tipo que no es `interes` lleva `operacion_id`; único parcial `(administracion_id, operacion_id)`.
- Una `correccion` con `corrige_a` es un contra-asiento (débito si corrige un crédito, crédito si corrige
  un interés); sin `corrige_a`, es un crédito de corrección y lleva `obligacion_id` (la obligación del
  error). Un débito de corrección sin `corrige_a` no existe (D7).
- `correccion` exige `btrim(motivo) <> ''`. `corrige_a` sólo en `correccion`, con `tipo_corregido` e
  `importe`: FK `(administracion_id, cuenta_id, corrige_a, tipo_corregido, importe)` a `movimiento
  (administracion_id, cuenta_id, id, tipo, importe)` y `CHECK tipo_corregido <> 'correccion'`. Así **la
  base** exige que el contra-asiento sea de la misma cuenta, por el mismo importe, y que una corrección no
  se corrija. Único parcial `(administracion_id, corrige_a)`: un movimiento se corrige una sola vez. El
  sentido opuesto lo exige la aplicación (no hay forma barata en una FK).
- `enlazado_a` con FK `(administracion_id, cuenta_id, enlazado_a)` (ajuste de interés del 8 hacia el
  interés que compensa, reversión, reimputación).

**Índices** (cada uno con la consulta que sirve): `obligacion (administracion_id, cuenta_id, periodo)` y
`movimiento (administracion_id, cuenta_id)` e `imputacion (administracion_id, cuenta_id)` para el estado
de una cuenta (D12); `emision (administracion_id, complejo_id, periodo)` lo da el único de D4;
`imputacion (administracion_id, obligacion_id)` para el exceso de D8. Sin particionar (DBA-6 del
explore: ~3 M filas por año con 1000 edificios).

**Columnas anticipadas (E10)**: `corte`, `enlazado_a`, `movimiento.emision_id`, `obligacion.operacion_id`
y los tipos `interes`, `condonacion`, `ajuste_de_interes`, `bonificacion`, `reimputacion`,
`baja_de_deuda` y `saldo_inicial` no los usa el código del 4b (sus tests los arman a mano, D-079). Nacen
acá porque, desde que la tabla pasa al rol de arranque, un `ALTER` necesita el préstamo de D-115.3, que no
existe. **Lo que el 4c o el 8 necesiten además** (el detalle del interés: días, tasa y base; el archivo y
la fila de origen del saldo inicial, R09) **va en una tabla nueva de su change**, que referencia la fila
del libro: crear una tabla no necesita préstamo.

**Desvío del explore**: la clave de `imputacion` lleva `corrida_id` (un UUID por llamada que imputa). Con
`(movimiento, obligación, componente)` solos, un crédito a favor que se imputa al mismo componente en dos
momentos (por ejemplo, después de que entró más interés) chocaría con su propia imputación anterior. La
idempotencia de la imputación no viene de esa clave sino del candado: se calcula bajo él, y repetir la
llamada no encuentra nada nuevo que imputar.

- **Descartadas**: columnas `unidad_id`/`persona_id` excluyentes en cada tabla (cambiar a `cuenta`
  después exige `UPDATE` sobre el libro, A-12 del explore); el capital de la obligación en una sola
  columna (A-4 obligaría a partir filas que no se pueden editar); una fila por componente en `obligacion`
  (multiplica por tres las filas y la clave natural para lo mismo); el detalle del interés en `JSONB`
  dentro de `movimiento` (montos en JSON fuera de la representación de D-046, y nadie valida su forma).
- **Costo de revertir**: mientras ninguna base con datos reales tenga filas, una migración que borra y
  recrea (ver Migration Plan); después, sólo hacia adelante con tablas nuevas.

### D2 · Candado por cuenta en una tabla aparte (E2)

**El hallazgo**: la exploración (4.13, A-11) propone `SELECT 1 FROM cuenta WHERE id = :id FOR UPDATE`
citando el patrón de `complejos`. Pero en PostgreSQL `FOR UPDATE` (y `FOR SHARE`, `FOR KEY SHARE`)
exige permiso de `UPDATE`, y la app tiene sólo `SELECT, INSERT` sobre toda tabla de sólo agregar (D-115):

```
EVIDENCIA (proponente, 26/10/2026 19:10 UTC; contenedor descartable postgres:18.6-trixie,
la imagen de infra/compose.yaml; nombre propose-4b-sonda-<pid>, borrado al terminar)
  tabla con triggers por fila y por sentencia, GRANT SELECT, INSERT a "app"
  SET ROLE app; SELECT 1 FROM cuenta WHERE id=1 FOR UPDATE;      -> ERROR: permission denied for table cuenta
  SET ROLE app; SELECT 1 FROM cuenta WHERE id=1 FOR KEY SHARE;   -> ERROR: permission denied for table cuenta
  GRANT UPDATE (candado) ON cuenta TO app;
  SET ROLE app; SELECT ... FOR UPDATE;                            -> 1 fila (el trigger por fila no se dispara)
                UPDATE cuenta SET candado = true WHERE id=1;      -> ERROR: cuenta no admite UPDATE
  REVOKE UPDATE ON cuenta FROM app;  (lo que hace roles despues)
  SET ROLE app; SELECT ... FOR UPDATE;                            -> ERROR: permission denied (el REVOKE de tabla saca el de columna)
```

**Decisión**: `candado_de_cuenta`, una fila por cuenta, aislada por administración y **fuera** de la lista
de sólo agregar (la app puede `UPDATE`). `bloquear_cuentas(sesion, cuenta_ids)`, en `aplicacion/cuentas.py`:
`INSERT ... SELECT unnest(:ids ordenados) ON CONFLICT DO NOTHING`, después `SELECT cuenta_id FROM
candado_de_cuenta WHERE cuenta_id = ANY(:ids) ORDER BY cuenta_id FOR UPDATE`, y exige tantas filas como
ids. Corre al principio de toda escritura que imputa (crédito, corrección, emisión) y **antes** de leer
imputaciones. La emisión bloquea todas sus cuentas en una sola sentencia, en orden de id: el mismo orden
para todos, sin interbloqueo. Si alguien borra un candado, el `INSERT ... DO NOTHING` lo recrea y dos
transacciones que lo recrean a la vez se serializan en el índice único: no hay hueco.
`anular_emision` no bloquea: sólo agrega un evento, y su efecto se calcula (D8); una imputación que corre
a la vez contra una obligación que se anula queda excluida al leer, y su crédito vuelve a favor.

- **Descartadas**: `FOR UPDATE` sobre `cuenta` (falla, arriba); darle `UPDATE` de una columna a la app
  sobre `cuenta` (funciona, pero `roles despues` lo revoca, así que hay que cambiar la lógica de
  `roles.py`, y una tabla protegida queda con un permiso de escritura donde hoy sólo el trigger la
  defendería: una excepción a D-115.1); `pg_advisory_xact_lock` (invisible, sin RLS, colisiones de hash;
  explore); `FOR UPDATE` sobre `unidad` (frena el padrón y no sirve para la cuenta de persona; explore);
  `SERIALIZABLE` (reintentos en todos los caminos, sin precedente en el repo; explore).
- **Costo de revertir**: borrar la tabla y cambiar una función; ningún dato de plata vive ahí.

### D3 · Qué expone el libro (reemplaza las firmas tentativas del explore §5)

Todas reciben la `Session` del que llama, exigen transacción y no confirman.

```
cuenta_de_unidad(sesion, *, complejo_id, unidad_id) -> UUID                      # crea si falta
registrar_emision(sesion, identidad, *, emision_id, complejo_id, periodo,
                  obligaciones: Sequence[ObligacionAEmitir], request_id) -> EmisionRegistrada
anular_emision(sesion, identidad, *, emision_id, motivo, request_id) -> None
registrar_credito(sesion, identidad, *, cuenta_id, tipo, importe, fecha_valor, operacion_id,
                  destino: Destino | None, request_id) -> UUID                      # lo llama el 8
corregir(sesion, identidad, *, complejo_id, pedido: PedidoDeCorreccion, request_id) -> UUID
estado_de_cuenta(sesion, *, cuenta_id) -> EstadoDeCuenta
deuda_del_edificio(sesion, *, complejo_id) -> list[DeudaDeCuenta]
saldo_anterior(sesion, *, emision_id, cuenta_id) -> Dinero                         # R06, para el 7
```

`ObligacionAEmitir(unidad_id, vencimiento, ordinaria, fondo_de_reserva, extraordinaria)`. `registrar_credito`
acepta los tipos de crédito salvo `correccion` (que entra por `corregir`) y `saldo_inicial` (4c), y exige
`destino` para los de destino fijo. `calcular_intereses`, `registrar_intereses`, `cargar_saldo_inicial`,
`es_moroso_critico` y la deuda a una fecha son del 4c (E12).

### D4 · Una emisión por período con `intento` (E3)

La exploración dejó abierto (R-4) cómo sostener "una por período salvo anulada" con el estado en otra
tabla. `registrar_emision`:

1. `INSERT INTO emision ... ON CONFLICT (id) DO NOTHING`. Si ya existía: se comparan edificio, período y
   el conjunto de obligaciones; iguales, devuelve lo registrado sin escribir; distintos, `Conflicto("emision_id")`.
2. Lee los intentos del período y sus eventos. Si alguno no está anulado, `Conflicto("periodo")`. Si no,
   usa `intento = max + 1` (o 1).
3. Dos emisiones simultáneas calculan el mismo intento y la segunda choca con el único
   `(administracion_id, complejo_id, periodo, intento)`: `23505` se traduce a `Conflicto("periodo")`. **La
   base** sostiene la regla aunque la aplicación se equivoque en el paso 2.
4. Obtiene o crea las cuentas, las bloquea (D2), inserta las obligaciones y corre `imputar_pendientes`
   por cuenta, en orden de id (E12).

Validaciones (`EntradaInvalida` con el campo): período primer día de mes; al menos una obligación; una
por unidad; importes no negativos con suma positiva. Una unidad de otro edificio la rechaza la FK
compuesta (`NoEncontrado`).

- **Descartadas**: bloquear la fila de `complejo` (frena el padrón del edificio entero durante cada
  emisión); un único parcial sobre "no anuladas" (imposible: el estado vive en `evento_de_emision`); una
  columna "anulada" en `emision` (exige `UPDATE`).
- **Costo de revertir**: una columna y un único; con datos, sólo hacia adelante.

### D5 · Idempotencia de punta a punta (E4)

La garantía vive en el libro (explore 4.4), con únicos que empiezan por `administracion_id`:

| escritura | clave |
|---|---|
| cuenta de unidad | `(administracion_id, unidad_id)` |
| emisión | `id` (el mismo que usará la `liquidacion` del 7, explore 4.2) |
| anulación | `(administracion_id, emision_id, tipo)` |
| obligación de una emisión | `(administracion_id, emision_id, cuenta_id)` |
| crédito o corrección | `(administracion_id, operacion_id)`, `operacion_id` UUID que manda el que llama |
| interés (4c) | `(administracion_id, obligacion_id, corte)` |

Siempre `INSERT ... ON CONFLICT ... DO NOTHING` y, si no insertó, leer la fila existente y compararla:
iguales, devolver su id; distintos, `Conflicto` con el campo de la clave (`operacion_id`, `emision_id`).
Nunca `DO UPDATE` (lo bloquea el trigger por sentencia, D-114.4). Una repetición no vuelve a auditar ni
a imputar.

- **Descartadas**: reusar `trabajos_hechos` (PK global, sin tenant, la app puede borrar); un
  `Idempotency-Key` HTTP como única defensa (explore 4.4).
- **Costo de revertir**: asimétrico; sacar un único es trivial, **agregarlo** sobre un libro con
  duplicados es imposible. Por eso todos nacen en `0023`.

### D6 · Orden de imputación (E5, provisorio en el fondo de reserva)

`dominio/imputacion.py`:

- `Componente`: `INTERES`, `ORDINARIA`, `FONDO_DE_RESERVA`, `EXTRAORDINARIA`.
- `ORDEN_DE_IMPUTACION = (INTERES, ORDINARIA, FONDO_DE_RESERVA, EXTRAORDINARIA)`, **en un solo lugar**: la
  respuesta de Alberto a A-4 (P60) cambia esta tupla y sus tests, y nada más. Las imputaciones ya
  registradas quedan como hechos con el orden que regía.
- `imputar(deudas, importe, destino) -> (imputaciones, sobrante)`: con destino fijo, sólo el componente
  de esa obligación; sin destino, las deudas ordenadas por `(periodo, orden del componente,
  vencimiento, obligacion_id)`, consumidas de a una hasta agotar el importe. Trabaja con `Dinero` (suma y
  resta, D-118). Ningún residual queda negativo; lo que no entra es el sobrante (crédito a favor).

**Por qué el fondo en tercer lugar**: R15 dice que "forma parte de la ordinaria" para la imputación, y
R04 pone la ordinaria antes que la extraordinaria porque "sostiene la operación diaria". El fondo no
paga la operación diaria; ponerlo detrás de la ordinaria y delante de la extraordinaria respeta las dos
frases. Es una lectura, no una regla escrita: **lo firma Juani (E5) y lo confirma Alberto (A-4)**.

- **Descartadas**: el fondo mezclado con la ordinaria en un solo importe (A-4 no tendría arreglo sin
  partir filas); el fondo antes que la ordinaria (contradice el "por qué" de R04 sin una respuesta de
  Alberto que lo pida).
- **Costo de revertir**: una tupla y sus tests, mientras la respuesta de A-4 llegue antes de que haya
  imputaciones reales que alguien quiera rehacer (no se rehacen: son hechos).

### D7 · Corrección (E6, R08, HU-A9)

Dos formas, con motivo obligatorio (texto normalizado como el resto de los textos libres, D-104, entre 1
y 500 caracteres) y `operacion_id`:

1. **Contra-asiento** de un movimiento: un `movimiento` `correccion` con `corrige_a`, el mismo importe y
   el sentido contrario. Rechazado con `Conflicto("movimiento_id")` si el movimiento ya tiene corrección,
   si es una corrección, o si ya no cuenta (su emisión está anulada). El par deja de contar (D8).
2. **Crédito de corrección** por un importe positivo, que referencia la obligación del error
   (`obligacion_id`) y se imputa con R04, como un pago (D-086). La obligación tiene que existir en el
   edificio y contar.

`fecha_valor` de una corrección es la fecha de registro, tomada de la misma fuente de "hoy" que ya usa
`complejos`; si no hay una, el constructor lo trae al orquestador antes de elegir (L-030). Toda
corrección bloquea la cuenta (D2), corre `imputar_pendientes` y registra la auditoría en la misma
transacción (D9).

**Lo que no hace**: no rehace las imputaciones de otros créditos (precedente: R17 con D-081, el pago
vuelve como crédito y no se reacomoda nada más); no permite una corrección que **suba** la deuda (un
cargo cobrado de menos se cobra como cargo en la emisión siguiente, 6 y 7). Si Juani la quiere en el 4b,
es un tipo de débito con `obligacion_id` y componente, una regla más y una tarea más.

- **Descartadas**: corregir editando (R08); un contra-asiento parcial (dos formas de hacer lo mismo que el
  crédito de corrección); reimputar todo lo posterior al corregir (reescribe la historia de imputaciones
  que el vecino ya vio).
- **Costo de revertir**: una función y su ruta; las correcciones registradas quedan.

### D8 · El estado de una cuenta y lo que no cuenta (E7)

`dominio/estado.py:calcular_estado(obligaciones, movimientos, imputaciones, emisiones_anuladas)`, puro:

1. **No cuentan**: las obligaciones de una emisión anulada; los movimientos con `emision_id` anulada; el
   par de un contra-asiento (el corregido y la corrección); un `ajuste_de_interes` enlazado a un interés
   que no cuenta (D-085); las imputaciones cuyo crédito u obligación no cuentan.
2. **Lo que se debe** por obligación y componente: el capital de su columna (para el interés, cero) más
   los débitos que cuentan con ese `(obligacion_id, componente)`.
3. **Lo imputado** por componente: si supera lo que se debe (por ejemplo, se corrigió un interés que un
   pago ya había cubierto), las imputaciones cuentan en orden `(registrada_en, id)` hasta cubrir lo que se
   debe, y **el exceso vuelve a su crédito, de la imputación más reciente a la más antigua**.
4. **Residual** = lo que se debe menos lo imputado que cuenta; nunca negativo.
5. **Crédito a favor** = por cada crédito que cuenta, su importe menos lo que imputó y cuenta.

**Invariante** (probada con `hypothesis` y un oráculo que suma por otro camino, sin pasar por los
componentes): Σ débitos que cuentan (capital incluido) − Σ créditos que cuentan = deuda total − crédito a
favor.

`imputar_pendientes(sesion, cuenta_id, corrida_id)`: con la cuenta bloqueada, imputa con R04 el crédito a
favor de cada crédito que lo tenga, del más viejo al más nuevo (`fecha_valor`, `registrado_en`, `id`). Lo
corren la emisión, todo crédito y toda corrección antes de imputar lo suyo. Entre una anulación y la
escritura siguiente, una cuenta puede mostrar deuda y crédito a favor a la vez; el estado informa los dos.

- **Descartadas**: el exceso devuelto al crédito más viejo (el más reciente es el que llegó "de más");
  saldo neto sin residuales por componente (R13 y R04 necesitan el desglose); recalcular imputaciones al
  leer en vez de guardarlas (el vecino ve a qué fue cada pago, R05).
- **Costo de revertir**: funciones puras; nada persiste del cálculo.

### D9 · Permiso `corregir_movimiento` y su auditoría (E8)

`Accion.CORREGIR_MOVIMIENTO = "corregir_movimiento"`, en `_MATRIZ` con `{_SA, _AP}` (HU-A9: "super admin o
administrador principal"; misma fila que "Revertir o reimputar pago"). Migración `0024` suma el valor a
`accion_de_auditoria` como literal (patrón de `0010` y `0022`). `corregir` llama a
`registrar(sesion, identidad, Accion.CORREGIR_MOVIMIENTO, entidad="movimiento", entidad_id=<corrección>,
request_id, detalle={"complejo_id", "forma", "corrige"})` con un modelo `extra="forbid"`; ni el motivo
ni el importe van al detalle (los guarda el libro, bajo RLS, L-007). Una repetición idempotente no
audita de nuevo.

Emitir y anular **no** se auditan desde el libro: los llama el 7, que audita con
`EMITIR_Y_DISTRIBUIR_LIQUIDACION` y `ANULAR_LIQUIDACION`, que ya existen. Auditar en los dos lugares
duplicaría filas; auditar sólo en el libro dejaría al 7 auditando a medias. La emisión y la anulación
guardan igual su responsable y su `request_id` en el libro.

- **Descartadas**: reusar `REVERTIR_O_REIMPUTAR_PAGO` (es otra acción del 8); permitir al administrador
  por edificio (HU-A9 lo reserva).
- **Costo de revertir**: `0024` baja sólo si nadie corrigió (FK de `auditoria`, `23503`): es parte del punto
  de no retorno.

### D10 · Contrato de error de la ruta nueva (E9)

`POST /api/complejos/{complejo_id}/correcciones`, en un router nuevo `proptech_api/cuenta_corriente.py`
montado como los demás (barrido de rutas, R6 del 2a). Cuerpo con `extra="forbid"`, discriminado por
`forma`:

```
{"forma": "contra_asiento", "operacion_id": UUID, "motivo": str, "movimiento_id": UUID}
{"forma": "credito", "operacion_id": UUID, "motivo": str, "obligacion_id": UUID, "importe": "5000.00"}
```

`importe` como texto con `Dinero` (D-046). Respuesta 201 `{"movimiento_id": UUID}`; la repetición
idempotente también 201 con el mismo id. Orden: 401 (`RutaConIdentidad`, antes de leer el cuerpo); 422
del cuerpo; 404 si el edificio, el movimiento o la obligación no existen o no alcanzan (una sola función,
L-017); 403 si no tiene el permiso; 409 o 422 del dominio.

`proptech_api/errores.py` declara **una vez** los modelos de las formas que la API ya usa (401 `{"detail":
str}`, 403 `{"detail": {"detalle", "permiso_faltante"}}`, 404 `{"detail": "no encontrado"}`, 409
`{"detail": "conflicto", "campo"}` y el 422 de FastAPI) y `RESPUESTAS_DE_ERROR`, que la ruta pasa en
`responses=`. Un test compara el OpenAPI de la ruta contra esas cinco formas. Las rutas viejas no se
retocan (explore 4.8). Los errores del dominio (`cuenta_corriente/aplicacion/errores.py`) se traducen con
un manejador propio, con las mismas formas.

- **Descartado**: el esquema nuevo `{"detail": {"tipo", "campo"?, "detalle"?}}` del explore 4.8. Dejaría
  dos formas de error conviviendo en la misma API, y la web ya parsea las de hoy.
- **Costo de revertir**: un archivo de modelos y un test.

### D11 · El SQL de cada módulo sólo nombra sus tablas (E11, explore 4.2)

Test nuevo en `test_fronteras_de_modulos.py`: recorre con `ast` los literales de texto de cada archivo de
`proptech_core/<módulo>/` (sin `compartido`, que es infraestructura), busca `FROM`, `JOIN`, `INTO`,
`UPDATE` y `TABLE` seguidos de un nombre, y compara contra un mapa tabla → módulo declarado en el test.
Una tabla que no está en el mapa da rojo (falla cerrada). Excepciones por archivo y tabla, con motivo.

**EVIDENCIA** (proponente, 26/10/2026, `rg -o '(FROM|JOIN|INTO|UPDATE)\s+"?[a-z_]+'` sobre
`proptech_core` sin `compartido`): además de `complejos/aplicacion/escritura.py → asignacion_rol` y
`lectura.py → persona` (los dos rojos que contaba el explore), `complejos/aplicacion/ejemplo.py` nombra
`administracion`, `persona` y `asignacion_rol`, y `acceso/aplicacion/alta_inicial.py` y `sesion.py`
nombran `administracion`. **Decisión propuesta**: `administracion` es de `acceso` (es el tenant y sale del
login, D-076), así que `acceso` pasa limpio; tres excepciones, `escritura.py` (decidida en el 2.2a,
ARQ-3), `lectura.py` (nueva: el autor de una versión, `JOIN persona` por FK compuesta y RLS) y `ejemplo.py`
(nueva: comando de carga, que AR-5 del 4a propone mover a una raíz de composición). Si el test encuentra
otra, el constructor la trae al orquestador; no la agrega por su cuenta (L-029, L-030).

**Límite declarado**: mira literales; un nombre de tabla armado en tiempo de ejecución no lo ve.

- **Descartadas**: `administracion` de `complejos` (deja rojas a dos rutas de acceso que existen por el
  login); escanear también `compartido` (`roles.py` y `base_de_datos.py` nombran tablas de todos por
  diseño).
- **Costo de revertir**: un test.

### D12 · Lecturas (E12)

`estado_de_cuenta` y `deuda_del_edificio` leen las filas del libro de la cuenta (o del edificio) y llaman
a `calcular_estado`. `saldo_anterior(emision_id, cuenta_id)` = la deuda de la cuenta sin contar las
obligaciones de esa emisión, calculada con el estado actual (el 7 la llama dentro de la transacción de la
emisión, R06). **La deuda a una fecha pasada no entra**: necesita decidir qué fecha manda en cada fila
(registro o valor, la del evento de anulación), y su primer consumidor es el moroso crítico (4c, con P53 y
P54) y el libre deuda (10b).

- **Descartado**: exponer `deuda_por_cuenta(al=...)` como en el explore §5, sin un consumidor que fije la
  semántica de la fecha.
- **Costo de revertir**: agregar un parámetro en el 4c.

### D13 · Deuda del 4a con dueño 4b (E13)

De la tabla "4a · deuda del cierre" de `12_fichas_de_changes.md`:

- **RB-4**: test con `otro.<tabla>` del rol de arranque creada **antes** que `public.<tabla>` del migrador,
  y al revés, para que el filtro `schemaname = 'public'` se vea fallar con su mutante en los dos órdenes
  (1.3).
- **QA-15**: una función de bloqueo con otro dueño, y el texto de bloqueo de otra tabla en la función de
  una, dan rojo en `despues()` (1.3).
- **Ensayo de roles**: `infra/ci/ensayo-roles.sh` devuelve también las seis tablas y sus funciones antes de
  bajar de `0023`, se corrige el mensaje `ciclo 0018/0016/0018` y se corre en un compose aislado (1.4).
- **RB-7**: `Dinero(texto)` construido bajo un contexto decimal de baja precisión no levanta
  `InvalidOperation`: el constructor usa su `localcontext`, como la aritmética (5.1).
- **QA-6, QA-7, QA-9, QA-12, QA-14**: el design del 4a los mandó "a las tareas si entraban"; al archivar no
  se verificó cuáles entraron. 5.1 verifica cada uno contra los tests del 4a y escribe el que falte.
- **Fuera**: RB-5 (dueño: quien toque `grupos.py`), RB-6 (4c, primer consumidor del redondeo), el cacheo
  de Chromium, `PROPTECH_COMPOSE_PROYECTO` (salvo que el arreglo del ensayo lo toque).

## Risks / Trade-offs

- [Un índice único que falta en `0023` no se puede agregar después si ya hay duplicados] → todas las
  claves de D5 nacen en `0023`; 1.1 y 1.2 prueban cada una con su duplicado.
- [El 4c o el 8 necesitan una columna que no está] → tabla nueva en su change (D1, E10); el préstamo de
  D-115.3 sigue sin construir.
- [La numeración `0023` choca con el 3c] → quien mergee segundo renumera `revision`/`down_revision` y corre
  la suite completa; `ensayo-roles.sh` nombra revisiones, así que se revisa también.
- [El orden del `INSERT ... ON CONFLICT` de varios candados no es un contrato de PostgreSQL] → el bloqueo
  real es el `SELECT ... ORDER BY cuenta_id FOR UPDATE`; el test de 3.6 corre una emisión y un crédito a
  la vez y una emisión contra otra de cuentas cruzadas, y exige que terminen sin `40P01`.
- [El exceso devuelto (D8) es una regla nueva que ninguna decisión escribe] → E7 la firma; R05 la escribe
  al archivar.
- [El fondo de reserva en tercer lugar es una lectura] → E5 provisorio, A-4 (P60) antes del piloto.
- [`TRUNCATE ... CASCADE` de la sonda toma `ACCESS EXCLUSIVE` sobre las siete tablas durante `despues()`]
  → sólo en el deploy, dentro de un savepoint que se revierte (D2 del 4a).
- [Un `ROLLBACK` del deploy que borra tablas con plata] → el `downgrade` de `0023` se niega si alguna tabla
  del libro tiene filas (Migration Plan).

### Preguntas abiertas que el design no cierra

- **A-4 (P60)**: dónde va el fondo de reserva. Default provisorio en D6, a firmar en E5.
- **"Hoy" de la corrección** (D7): si `complejos` no tiene una fuente única de la fecha del día, el
  constructor lo trae antes de elegir.

## Migration Plan

**Deploy**: `roles antes` → `alembic upgrade head` (`0023` y `0024` juntas, en una transacción por
`env.py`) → `roles despues` (transfiere las seis tablas y sus seis funciones al rol de arranque y las
verifica por el efecto) → API y worker (el chequeo de arranque ahora incluye las seis). Un corte en
cualquier punto deja la base en `0022`, o con las tablas todavía del migrador y la API sin arrancar.

**Rollback, mientras ninguna tabla del libro tenga filas y nadie haya corregido nada**. El código viejo
no arranca sobre la base nueva (su `alembic upgrade head` no encuentra `0024`), así que el orden es:

1. Con el código **nuevo** todavía desplegado, como rol de arranque: comprobar que las seis tablas están
   vacías (`SELECT EXISTS` en cada una; el superusuario no pasa por RLS). **Si alguna tiene filas, no se
   sigue**: es el punto de no retorno. Si están vacías, devolver al migrador las seis tablas y sus seis
   funciones (`ALTER TABLE ... OWNER TO proptech_migrador`, `ALTER FUNCTION fn_<tabla>_bloqueada() OWNER
   TO proptech_migrador`). `ensayo-roles.sh` hace este paso (1.4).
2. Con el código nuevo, como migrador: `alembic downgrade 0022`. Baja `0024` (el valor del vocabulario) y
   `0023` (las siete tablas). El `downgrade` de `0023` se vuelve a negar por su cuenta si encuentra filas:
   como dueño, hace `NO FORCE ROW LEVEL SECURITY` y cuenta (con `FORCE`, el migrador sin tenant vería
   cero filas y borraría plata creyendo que no hay, DB-3 del 4a).
3. Recién entonces, desplegar el código viejo.

**Punto de no retorno**: la primera fila en cualquier tabla del libro, o la primera corrección auditada
(bajar `0024` choca con `fk_auditoria_accion`, `23503`). Desde ahí, la única vuelta atrás es restaurar el
respaldo, o arreglar hacia adelante. Se acepta así porque todavía no hay producción (como D-114.5). La
tarea 1.4 ensaya la bajada completa en un compose aislado y fija con un test la negativa del `downgrade`
con una fila.

Ninguna migración reescribe filas.
