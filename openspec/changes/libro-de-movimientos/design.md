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
- Que el 4c, el 7 y el 8 encuentren hechas las columnas y las funciones que necesitan, con los tipos anticipados y FK ya definidos; cualquier cambio estructural posterior requiere el préstamo de D-115.3.

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
Dependencias de esquema: `cuenta_corriente → complejos` (`complejo`, `unidad`) y
`cuenta_corriente → acceso` (`administracion`, `persona`), nunca en sentido inverso. Una composición de
cambio de titular (4d) vive en `proptech_api`; no se agrega un import inverso desde `complejos` (AR-3).

- **Descartado**: `Protocol` de repositorio con doble en memoria (D-120).
- **Costo de revertir**: refactor mecánico, sin migración.

### D1 · Ocho tablas en una migración, `0023`

Seis de sólo agregar y una de candados (D2), más el vocabulario global `tipo_de_movimiento`, sin tenant, como `accion_de_auditoria`. Las siete tablas por administración llevan `administracion_id NOT NULL`, RLS forzada por
`aislar_por_administracion`, montos `NUMERIC(14,2)` leídos con `Dinero.desde_decimal`, ids `UUID` que
genera la aplicación. Cada tabla de sólo agregar lleva su función `fn_<tabla>_bloqueada()` con `RAISE
EXCEPTION '<tabla> no admite %', TG_OP` y tres triggers con esa función: `trg_<tabla>_sin_update_delete`
(por fila), `trg_<tabla>_sin_truncate` (`BEFORE TRUNCATE`) y `trg_<tabla>_sin_update_delete_por_sentencia`
(`BEFORE UPDATE OR DELETE ... FOR EACH STATEMENT`), y se declara en `TABLAS_DE_SOLO_AGREGAR` con ese
texto y esos tres nombres. `roles.py:despues()` cambia para otorgar `REFERENCES` al migrador sobre las seis tablas del libro y `candado_de_cuenta` (E15), sin devolver su propiedad ni ampliar permisos de escritura de la app.

| tabla | columnas | claves y restricciones |
|---|---|---|
| `cuenta` | `id`, `administracion_id`, `complejo_id`, `unidad_id` nulo, `persona_id` nulo, `creada_en` | `CHECK num_nonnulls(unidad_id,persona_id)=1`; todas las claves y FK en la lista exhaustiva siguiente |
| `candado_de_cuenta` | `cuenta_id` PK, `administracion_id` | fuera de tablas protegidas; PK/FK en lista exhaustiva |
| `emision` | `id`, `administracion_id`, `complejo_id`, `periodo`, `intento`, `registrada_por`, `request_id`, `registrada_en` | período primer día del mes, intento >= 1; claves/FK en lista exhaustiva |
| `evento_de_emision` | `id`, `administracion_id`, `complejo_id`, `emision_id`, `tipo`, `motivo`, `persona_id`, `request_id`, `registrado_en` | tipo = 'anulada'; motivo normalizado de 1 a 500 caracteres; claves/FK en lista exhaustiva |
| `obligacion` | `id`, `administracion_id`, `complejo_id`, `cuenta_id`, `emision_id` nulo, `operacion_id` nulo, `periodo`, `vencimiento`, `ordinaria`, `fondo_de_reserva`, `extraordinaria`, `registrada_en` | exactamente uno de emision_id/operacion_id; componentes >= 0 y suma > 0; período primer día; claves/FK en lista exhaustiva |
| `movimiento` | `id`, `administracion_id`, `complejo_id`, `cuenta_id`, `tipo`, `sentido`, `importe`, `fecha_valor`, `registrado_por`, `request_id`, `registrado_en`, `operacion_id` nulo, `emision_id` nulo, `obligacion_id` nulo, `componente` nulo, `corte` nulo, `corrige_a` nulo, `tipo_corregido` nulo, `enlazado_a` nulo, `motivo` nulo | restricciones y claves/FK detalladas debajo |
| `imputacion` | `id`, `administracion_id`, `complejo_id`, `cuenta_id`, `movimiento_id`, `sentido_del_movimiento NOT NULL`, `obligacion_id`, `componente`, `importe`, `corrida_id`, `orden BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL`, `registrada_en` | importe > 0; sentido_del_movimiento NOT NULL y CHECK = 'credito'; claves/FK debajo |

**Vocabulario (E14, AR-2, AN-04)**: `tipo_de_movimiento(tipo TEXT NOT NULL, sentido TEXT NOT NULL)`
con PK `(tipo, sentido)`, `CHECK sentido IN ('debito', 'credito')` y tipo no vacío. El migrador lo amplía
con `INSERT`; la app sólo tiene `SELECT`. No es una tabla del libro protegida ni lleva RLS porque no
contiene datos de administraciones. Semilla: `interes/debito`, `pago/credito`,
`correccion/debito`, `correccion/credito`, `condonacion/credito`, `ajuste_de_interes/credito`,
`bonificacion/credito`, `reimputacion/debito`, `reimputacion/credito`, `baja_de_deuda/credito`,
`saldo_inicial/credito`, `reversion_de_pago/debito`, `traslado/debito`, `traslado/credito`.
`movimiento(tipo, sentido)` referencia esta PK: no hay lista cerrada de tipos en `movimiento`.

**`movimiento`**, restricciones (E10, E14):

- `tipo`, `sentido`, `importe`, `fecha_valor`, `registrado_por`, `request_id` y `registrado_en`
  son `NOT NULL`; `importe > 0`; `componente`, si no es nulo, pertenece a
  `('interes', 'ordinaria', 'fondo_de_reserva', 'extraordinaria')`.
- Se eligen **CHECK acotados a tipos conocidos** para destino y origen, no columnas duplicadas del
  vocabulario: una FK tipo/sentido basta para ampliarlo sin replicar metadatos de reglas en cada fila.
  `interes` exige obligación, componente `interes` y `corte`, todos no nulos;
  `condonacion` y `ajuste_de_interes` exigen obligación y componente `interes`, ambos NOT NULL;
  `bonificacion` exige obligación y componente `ordinaria`, ambos NOT NULL. Nuevos tipos entran por INSERT cuando sus
  reglas caben en el contrato genérico; una regla nueva que requiera cambiar esos CHECK necesita préstamo.
- Un débito sin `corrige_a` lleva obligación y componente, por CHECK genérico acotado al sentido. Todo tipo distinto de `interes` exige
  `operacion_id NOT NULL`. `correccion` exige motivo normalizado de 1 a 500 caracteres, con CHECK
  explícito `tipo <> 'correccion' OR (motivo IS NOT NULL AND length(motivo) BETWEEN 1 AND 500 AND
  btrim(motivo) <> '')`; no se deja que NULL pase el CHECK.
- `corrige_a` sólo aparece en `correccion`. `CHECK (num_nulls(corrige_a, tipo_corregido) IN (0,2))`:
  ambos nulos o ambos completos. Se elige este CHECK en vez de MATCH FULL porque tenant y cuenta son
  obligatorios, y la FK opcional quedaría parcialmente nula aun sin referencia. Las otras FK opcionales
  llevan sólo un identificador nullable; todos sus demás campos son NOT NULL. No hay bypass por sentido
  nulo: `imputacion.sentido_del_movimiento NOT NULL` y CHECK igual a `credito`.
- Contra-asiento: misma cuenta e importe mediante FK de abajo; sentido opuesto y blanco corregible
  se validan bajo candado en aplicación. Se permite contra-asiento de un crédito de corrección, una sola
  vez; no de un débito de corrección. Se elimina `tipo_corregido <> 'correccion'` (E6).
- Crédito de corrección sin `corrige_a`: obligación existente del edificio, que cuente, como referencia
  del error o crédito particular R14; se imputa con R04, no exclusivamente a esa obligación.
- `enlazado_a` puede unir cuentas y edificios distintos **de la misma administración** mediante
  `(administracion_id, enlazado_a)`, para reversión, reimputación o traslado. No habilita cruces de tenant.

**Lista exhaustiva de claves y FK de `0023` (DB-1, DB-9)**. Todas las tablas tienen PK `id`, salvo
`candado_de_cuenta` (PK `cuenta_id`) y el vocabulario (PK compuesta anterior). Todos los identificadores
no indicados como opcionales son NOT NULL. Las FK son `NO ACTION`, sin cascadas que modifiquen el libro.
Los nombres `uq_` se usan también en el mapa de errores de D10.

| tabla | todos los únicos adicionales y parciales | todas las FK |
|---|---|---|
| `cuenta` | `uq_cuenta_adm_id(administracion_id,id)`; `uq_cuenta_edificio_id(administracion_id,complejo_id,id)`; `uq_cuenta_unidad(administracion_id,unidad_id) WHERE unidad_id IS NOT NULL`; `uq_cuenta_persona(administracion_id,complejo_id,persona_id) WHERE persona_id IS NOT NULL` | `administracion_id → administracion(id)`; `(administracion_id,complejo_id) → complejo(administracion_id,id)`; `(administracion_id,complejo_id,unidad_id) → unidad(administracion_id,complejo_id,id)`; `(administracion_id,persona_id) → persona(administracion_id,id)` |
| `candado_de_cuenta` | ninguno además de PK | `(administracion_id,cuenta_id) → cuenta(administracion_id,id)` |
| `emision` | `uq_emision_edificio_id(administracion_id,complejo_id,id)`; `uq_emision_periodo_id(administracion_id,complejo_id,periodo,id)`; `uq_emision_intento(administracion_id,complejo_id,periodo,intento)` | `(administracion_id,complejo_id) → complejo(administracion_id,id)`; `(administracion_id,registrada_por) → persona(administracion_id,id)` |
| `evento_de_emision` | `uq_evento_emision_tipo(administracion_id,emision_id,tipo)` | `(administracion_id,complejo_id,emision_id) → emision(administracion_id,complejo_id,id)`; `(administracion_id,persona_id) → persona(administracion_id,id)` |
| `obligacion` | `uq_obligacion_cuenta_id(administracion_id,complejo_id,cuenta_id,id)`; `uq_obligacion_emision(administracion_id,emision_id,cuenta_id) WHERE emision_id IS NOT NULL`; `uq_obligacion_operacion(administracion_id,operacion_id,cuenta_id,periodo) WHERE operacion_id IS NOT NULL` | `(administracion_id,complejo_id,cuenta_id) → cuenta(administracion_id,complejo_id,id)`; `(administracion_id,complejo_id,periodo,emision_id) → emision(administracion_id,complejo_id,periodo,id)` |
| `movimiento` | `uq_mov_adm_id(administracion_id,id)`; `uq_mov_sentido(administracion_id,complejo_id,cuenta_id,id,sentido)`; `uq_mov_correccion(administracion_id,complejo_id,cuenta_id,id,tipo,importe)`; `uq_mov_operacion(administracion_id,operacion_id) WHERE operacion_id IS NOT NULL`; `uq_mov_corrige_a(administracion_id,corrige_a) WHERE corrige_a IS NOT NULL`; `uq_mov_interes(administracion_id,obligacion_id,corte) WHERE tipo = 'interes'` | `(tipo,sentido) → tipo_de_movimiento(tipo,sentido)`; `(administracion_id,complejo_id,cuenta_id) → cuenta(administracion_id,complejo_id,id)`; `(administracion_id,complejo_id,cuenta_id,obligacion_id) → obligacion(administracion_id,complejo_id,cuenta_id,id)`; `(administracion_id,complejo_id,emision_id) → emision(administracion_id,complejo_id,id)`; `(administracion_id,registrado_por) → persona(administracion_id,id)`; `(administracion_id,complejo_id,cuenta_id,corrige_a,tipo_corregido,importe) → movimiento(administracion_id,complejo_id,cuenta_id,id,tipo,importe)`; `(administracion_id,enlazado_a) → movimiento(administracion_id,id)` |
| `imputacion` | `orden` es secuencia monótona global; ningún único de corrida | `(administracion_id,complejo_id,cuenta_id,movimiento_id,sentido_del_movimiento) → movimiento(administracion_id,complejo_id,cuenta_id,id,sentido)`; `(administracion_id,complejo_id,cuenta_id,obligacion_id) → obligacion(administracion_id,complejo_id,cuenta_id,id)` |
| `tipo_de_movimiento` | ninguno además de PK | ninguna |


`imputacion` incorpora `complejo_id NOT NULL` para esas FK. Su `componente NOT NULL` usa los mismos
cuatro valores de componente de movimiento. `obligacion` exige `vencimiento NOT NULL`; los montos,
período, intento, fechas de registro y responsables de las demás tablas son NOT NULL salvo los campos
marcados nulos en el cuadro. El vocabulario otorga SELECT, INSERT al migrador y sólo SELECT a la app. `periodo` repetido entre obligación y emisión
queda atado por su FK. El cuadro anterior reemplaza las claves abreviadas del primer cuadro: en
particular, no existe `uq_imputacion_corrida`, ni FK de enlace limitada a una cuenta. Todas las claves
referenciadas existen como PK o único no parcial, incluidos los destinos de las FK de sentido y corrección.

**Índices**, cada uno con su consulta: `obligacion(administracion_id,cuenta_id,periodo)` para
leer obligaciones de una cuenta ordenadas por período; `imputacion(administracion_id,cuenta_id)` para
leer sus imputaciones; `cuenta(administracion_id,complejo_id,id)` (único de FK) para enumerar cuentas del
edificio; `uq_mov_sentido` y `uq_mov_correccion` sirven las FK y la lectura de movimientos por
administración/edificio/cuenta; `uq_emision_intento` sirve D4. Los demás únicos existen para las FK o la
idempotencia nombradas en el cuadro. Se eliminan `imputacion(administracion_id,obligacion_id)` (D8
calcula exceso en memoria), el único con `corrida_id` (no sostiene idempotencia) y el índice simple de
movimiento redundante. D12 usa los índices compuestos con edificio y cuenta, y exige su EXPLAIN. Sin
particionar (~3 M filas/año con 1000 edificios, estimación del explore, no medición).

**Columnas anticipadas (E10)**: `corte`, `enlazado_a`, `movimiento.emision_id`,
`obligacion.operacion_id` y todos los pares del vocabulario anterior nacen en `0023`, con un INSERT
válido por cada par en 1.2. El 4c agrega detalle de interés (días, tasa, base) y origen de saldo inicial
(R09) en tablas nuevas que referencian el libro gracias a E15; el 7 puede referenciar `emision` y el 8
`movimiento`. Esto cubre **tipos/sentidos y referencias futuras**, no una promesa de nunca necesitar
ALTER. Después de `roles despues`, las seis tablas protegidas son del rol de arranque: el migrador no
puede `ALTER`, `CREATE INDEX` ni `DROP INDEX`. Agregar/quitar un único o cambiar un CHECK requiere el
préstamo de D-115.3. La misma limitación aplica al único de interés por obligación/corte: el 4c debe
resolver P53/P54 antes de construir; un interés corregido no se registra otra vez en el mismo corte. Si
necesita esa posibilidad u otra agrupación, debe construir/obtener el préstamo antes de modificarlo.

**Desvíos del explore**: se restaura `traslado`, omitido en el primer propose (AR-2); cuenta de persona
única por **edificio** `(administracion_id,complejo_id,persona_id)`, en vez de sólo por administración
(AR-6, P52), para aislar la deuda del vendedor en su edificio. Descartado: cuenta personal común a todos
los edificios (mezcla alcances); revertir exige préstamo y resolver los datos existentes. `corrida_id`
identifica la corrida pero no es clave única: imputar dos veces al mismo componente en momentos
distintos es válido; el candado y el cálculo evitan duplicar.

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
`INSERT ... SELECT unnest(:ids) ORDER BY cuenta_id ON CONFLICT (cuenta_id) DO NOTHING`, después `SELECT cuenta_id FROM
candado_de_cuenta WHERE cuenta_id = ANY(:ids) ORDER BY cuenta_id FOR UPDATE`, y exige tantas filas como
ids. Corre al principio de toda escritura que imputa (crédito, corrección, emisión) y **antes** de leer
imputaciones. La emisión bloquea todas sus cuentas en una sola sentencia, en orden de id: el mismo orden
para todos, sin interbloqueo. Si alguien borra un candado, el `INSERT ... ON CONFLICT (cuenta_id) DO NOTHING` lo recrea y dos
transacciones que lo recrean a la vez se serializan en el índice único: no hay hueco.
La cuenta y su candado nacen en la misma transacción. Para varias unidades se crean cuentas en una
sola sentencia `INSERT ... SELECT ... ORDER BY unidad_id` con su árbitro de D5; los candados también
se insertan en una sentencia ordenada por cuenta_id. `bloquear_cuentas` se llama **una sola vez por
transacción**, con todas las cuentas necesarias: obligación explícita del llamador, no un bucle de
llamadas unitarias. El INSERT de una fila nueva también puede esperar por un único, por eso el orden
empieza en la creación, antes del SELECT.
Antes de bloquear exige `current_setting('transaction_isolation') = 'read committed'`; otro nivel
lanza `AislamientoNoAdmitido` antes de imputar. REPEATABLE READ puede conservar una foto anterior al
candado; el test de 3.6 lo demuestra al quitar el chequeo. Si el SELECT devuelve menos ids que los
pedidos se lanza `CandadoIncompleto`, sin continuar ni imputar. La app no tiene DELETE sobre el candado
(`REVOKE DELETE` en 0023 y refuerzo idempotente en `despues()`); el borrado intercalado por rol de
arranque se prueba con barrera y exige ese error.
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

Todas reciben la `Session` del que llama, exigen transacción y no confirman. Fuera de ella lanzan
`RegistroFueraDeTransaccion`. Los INSERT toman `administracion_id` de la identidad autenticada y
verifican al entrar que coincide con `current_setting('app.administracion_id')`; nunca del cliente.
Las funciones sin identidad usan el tenant ya fijado por el contexto autenticado de la Session.
Permisos de emitir, anular y registrar créditos quedan a cargo del llamador (7, 8 o 10b); la API verifica
el permiso de corregir. El llamador de `anular_emision` debe auditar en la misma transacción (D9).
Una anulación ya existente da `Conflicto("emision_id")` también si el motivo coincide (R17); el único
impide duplicados, no autoriza un replay exitoso. Los ids de emisión, cuenta u obligación inexistentes
o ajenos dan `NoEncontrado` en `anular_emision`, `registrar_credito` y corrección de crédito.

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

1. Busca primero por `emision_id`: compara edificio, período y el conjunto de obligaciones; iguales,
   devuelve sin escribir ni imputar; distintos, `Conflicto("emision_id")`.
2. Lee los intentos y eventos del período. Si alguno no está anulado, `Conflicto("periodo")`; si no,
   calcula `intento = max + 1` (o 1). Todavía no insertó: intento es NOT NULL.
3. Inserta con `ON CONFLICT (id) DO NOTHING`; si perdió contra el mismo id, lee y compara como en 1.
   Con otro id, el único `uq_emision_intento` produce 23505 traducido a `Conflicto("periodo")` dentro de
   SAVEPOINT (D10). La prueba concurrente pone la barrera **después del paso 2**; el mutante elimina ese
   único. El mutante secuencial conserva `max+1` pero omite comprobar eventos no anulados: produce una
   segunda emisión activa y debe fallar (no se usa `intento=1` fijo, que escondería el defecto).
4. Crea todas las cuentas ordenadas por unidad_id en una sola sentencia y sus candados en la misma
   transacción, bloquea el conjunto una sola vez (D2), inserta obligaciones y corre `imputar_pendientes`
   por cuenta en orden de id (E12). Después de imputar pendientes, calcula y devuelve la foto de saldo anterior (D12).

Validaciones (`EntradaInvalida` con el campo): período primer día de mes; al menos una obligación; una
por unidad; importes no negativos con suma positiva. Una unidad de otro edificio la rechaza la FK
compuesta (`NoEncontrado`).

- **Descartadas**: bloquear la fila de `complejo` (frena el padrón del edificio entero durante cada
  emisión); un único parcial sobre "no anuladas" (imposible: el estado vive en `evento_de_emision`); una
  columna "anulada" en `emision` (exige `UPDATE`).
- **Costo de revertir**: una columna y un único; cambiarlos requiere préstamo tras roles, y con datos sólo hacia adelante.

### D5 · Idempotencia de punta a punta (E4)

La garantía vive en el libro (explore 4.4), con únicos que empiezan por `administracion_id`:

| escritura | árbitro exacto de `ON CONFLICT ... DO NOTHING` |
|---|---|
| cuenta de unidad | `(administracion_id, unidad_id) WHERE unidad_id IS NOT NULL` |
| candado | `(cuenta_id)` |
| emisión | `(id)` |
| anulación | `(administracion_id, emision_id, tipo)`; conflicto se rechaza según R17 |
| obligación de emisión | `(administracion_id, emision_id, cuenta_id) WHERE emision_id IS NOT NULL` |
| obligación saldo inicial (4c) | `(administracion_id, operacion_id, cuenta_id, periodo) WHERE operacion_id IS NOT NULL` |
| crédito o corrección | `(administracion_id, operacion_id) WHERE operacion_id IS NOT NULL` |
| interés (4c) | `(administracion_id, obligacion_id, corte) WHERE tipo = 'interes'` |
| imputación | INSERT simple; replay y candado impiden duplicarla |

Nunca `ON CONFLICT DO NOTHING` sin árbitro ni `DO UPDATE`. Todo **otro** único produce 23505 y se
traduce por su nombre (D10), en particular `uq_mov_corrige_a → movimiento_id`.
Primero se busca por `operacion_id`, **antes de validar si ya tiene corrección o ejecutar
imputar_pendientes**; replay igual no escribe ni audita. Tras una carrera en el INSERT se lee y compara
igual. Para crédito/corrección se comparan `cuenta_id`, `tipo`, `sentido`, `destino`
(`obligacion_id`, `componente`), `importe`, `fecha_valor` explícita si el pedido la trae, `forma`,
`corrige_a`, motivo normalizado y complejo de la ruta/contexto; se excluyen `request_id`,
`registrado_por` y fecha de registro asignada por el servidor. En contra-asiento, importe/cuenta/tipo
se comparan contra el original sin volver a exigir que siga sin corregir; para replay no se recalcula
"hoy". Cambiar cualquiera de los datos del pedido da `Conflicto("operacion_id")`. Cuenta de unidad
compara edificio/unidad; obligación compara cuenta, emisión, período, vencimiento y sus tres importes;
emisión compara edificio, período y obligaciones ordenadas por unidad_id.

- **Descartadas**: reusar `trabajos_hechos` (PK global, sin tenant, la app puede borrar); un
  `Idempotency-Key` HTTP como única defensa (explore 4.4).
- **Costo de revertir**: asimétrico: quitar o agregar un único requiere el préstamo de D-115.3 después de roles;
  agregarlo con duplicados además exige resolverlos sin editar el libro. Por eso se deciden en `0023`.

### D6 · Orden de imputación (E5, provisorio en el fondo de reserva)

`dominio/imputacion.py`:

- `Componente`: `INTERES`, `ORDINARIA`, `FONDO_DE_RESERVA`, `EXTRAORDINARIA`.
- `ORDEN_DE_IMPUTACION = (INTERES, ORDINARIA, FONDO_DE_RESERVA, EXTRAORDINARIA)`, **en un solo lugar**: la
  respuesta de Alberto a A-4 (P60) cambia esta tupla y sus tests, y nada más. Las imputaciones ya
  registradas quedan como hechos con el orden que regía.
- `imputar(deudas, importe, destino) -> (imputaciones, sobrante)`: con destino fijo, sólo el componente
  de esa obligación; sin destino, las deudas ordenadas por `(periodo, orden del componente,
  vencimiento, obligacion_id)`, consumidas de a una hasta agotar el importe. Trabaja con `Dinero` (suma y
  resta, D-118). Ningún residual queda negativo. Sin destino fijo, el sobrante es crédito a favor. Con destino fijo,
  se rechaza el pedido que excede la capacidad de su componente, con `EntradaInvalida("destino")`, 422,
  sin registrar ninguna parte. No se convierte condonación en pago de capital (E16). `imputar` exige
  importe positivo, también sin API; cero o negativo dan `EntradaInvalida("importe")`.

**Por qué el fondo en tercer lugar**: R15 dice que "forma parte de la ordinaria" para la imputación, y
R04 pone la ordinaria antes que la extraordinaria porque "sostiene la operación diaria". El fondo no
paga la operación diaria; ponerlo detrás de la ordinaria y delante de la extraordinaria respeta las dos
frases. Es una lectura, no una regla escrita: **lo firma Juani (E5) y lo confirma Alberto (A-4)**.

- **Descartadas**: el fondo mezclado con la ordinaria en un solo importe (A-4 no tendría arreglo sin
  partir filas); el fondo antes que la ordinaria (contradice el "por qué" de R04 sin una respuesta de
  Alberto que lo pida); fondo a prorrata con ordinaria (otra lectura posible de R15, pendiente A-4).
- **Costo de revertir**: una tupla y sus tests, mientras la respuesta de A-4 llegue antes de que haya
  imputaciones reales que alguien quiera rehacer (no se rehacen: son hechos).

### D7 · Corrección (E6, R08, HU-A9)

Dos formas, con motivo obligatorio (texto normalizado como el resto de los textos libres, D-104, entre 1
y 500 caracteres) y `operacion_id`:

1. **Contra-asiento** de un movimiento: un `movimiento` `correccion` con `corrige_a`, el mismo importe y
   el sentido contrario. Rechazado con `Conflicto("movimiento_id")` si el movimiento ya tiene corrección,
   si es un débito de corrección, o si su emisión está anulada. No se usa el predicado general de
   exclusión para rechazar un crédito de contra-asiento: justamente ese crédito está en el par que se
   quiere deshacer. El par deja de contar (D8). Un **crédito de corrección sí admite contra-asiento, una sola vez**;
   si era un contra-asiento de interés, deshacerlo vuelve a hacer contar el interés original. No se
   habilita un débito de corrección libre.
2. **Crédito de corrección** por un importe positivo, que referencia la obligación del error
   (`obligacion_id`) y se imputa con R04, como un pago (D-086). La obligación tiene que existir en el
   edificio y contar.

`fecha_valor` de una corrección es la fecha de registro, tomada de la misma fuente de "hoy" que ya usa
`complejos`; si no hay una, el constructor lo trae al orquestador antes de elegir (L-030). Primero resuelve replay por operacion_id (D5), después valida el movimiento u obligación del mismo
edificio de la ruta, que si es ajeno da NoEncontrado. Toda
corrección nueva bloquea la cuenta (D2), corre `imputar_pendientes` y registra la auditoría en la misma
transacción (D9).

**Lo que no hace**: no rehace las imputaciones de otros créditos (precedente: R17 con D-081, el pago
vuelve como crédito y no se reacomoda nada más); no permite un débito de corrección libre; contra-asentar un crédito sí restablece deuda. **Cargo
cobrado de menos** queda como caso nombrado del 7: cargo complementario con motivo y vínculo al origen,
sin disfrazarlo de un pago. **Saldo inicial bajo R09** queda como ajuste con motivo del 4c, con origen y
trazabilidad. Knowledge Base Impact entrega ambos casos a sus fichas; no se implementan en el 4b.

- **Descartadas**: corregir editando (R08); un contra-asiento parcial (dos formas de hacer lo mismo que el
  crédito de corrección); reimputar todo lo posterior al corregir (reescribe la historia de imputaciones
  que el vecino ya vio).
- **Costo de revertir**: una función y su ruta; las correcciones registradas quedan.

### D8 · El estado de una cuenta y lo que no cuenta (E7)

`dominio/estado.py:calcular_estado(obligaciones, movimientos, imputaciones, emisiones_anuladas)`, puro:

1. **No cuentan**: las obligaciones de una emisión anulada; los movimientos con `emision_id` anulada; los pares de contra-asiento activos, resueltos desde el extremo de cada cadena (sin corrección entrante) hacia el original
   (el orden es topológico por corrige_a, no fecha ni UUID; se omite una corrección ya excluida por otra posterior: I débito, C1 crédito que corrige I y C2
   débito que corrige C1 excluyen C2/C1 y restauran I); un `ajuste_de_interes` enlazado a un interés
   que no cuenta (D-085); las imputaciones cuyo crédito u obligación no cuentan.
2. **Lo que se debe** por obligación y componente: el capital de su columna (para el interés, cero) más
   los débitos que cuentan con ese `(obligacion_id, componente)`.
3. **Lo imputado** por componente: si supera lo que se debe (por ejemplo, se corrigió un interés que un
   pago ya había cubierto), las imputaciones cuentan en orden `orden` ascendente (secuencia monótona de `imputacion`, nunca `now()` ni UUID) hasta cubrir lo que se
   debe, y **el exceso vuelve a su crédito, de la imputación más reciente a la más antigua**.
4. **Residual** = lo que se debe menos lo imputado que cuenta; nunca negativo.
5. **Crédito a favor** = por cada crédito que cuenta, su importe menos lo que imputó y cuenta.

**Caso AN-02 que distingue el orden**: la obligación de octubre tiene dos intereses, I1 $4.000 e I2
$6.000 de cortes distintos. Pago A registrado 1/9 conserva $4.000 a favor; B del 15/10 imputa $6.000
al componente de interés de octubre; A se imputa a ese mismo componente el 1/11 por $4.000. Contra-asentar
I1 deja $6.000 de interés: vuelven $4.000 a A, B conserva $6.000 imputados. Ordenar por fecha de crédito
restituiría $4.000 a B y dejaría a A aplicado: el saldo total igual no basta como aserción.

**Propiedades** con hypothesis, además de la identidad contable: residual >= 0 por componente;
imputado que cuenta <= debido por componente; crédito a favor >= 0 por crédito; con imputaciones
positivas que cuentan sobre capital vigente y sin débitos adicionales, deuda < suma del capital. Se
prueban los mutantes "sin tope del paso 3" e "ignora imputaciones"; quitar un max redundante no prueba
nada. El oráculo implementa su propia exclusión, no importa el predicado de producción. Datos acotados:
a lo sumo 20 obligaciones y 20 créditos de 1 a 1.000.000,00 cada uno y suma absoluta <= 40.000.000,00,
dentro de NUMERIC(14,2), más casos de borde explícitos hasta 999999999999.99 y rechazo de overflow.
**Invariante adicional**, no prueba suficiente del reparto: Σ débitos que cuentan (capital incluido) − Σ créditos que cuentan = deuda total − crédito a
favor.

`imputar_pendientes(sesion, cuenta_id, corrida_id)`: con la cuenta bloqueada, imputa con R04 el crédito libre a
favor y conserva el destino de cada crédito fijo que lo tenga, del más viejo al más nuevo (`fecha_valor`, `registrado_en`, `id`). Los créditos de destino fijo siempre conservan su destino: si la emisión de una bonificación se
anula, se saltea esa bonificación hasta su reversión por el 8 (R37, E16), aunque exista deuda nueva.
Lo
corren la emisión, todo crédito y toda corrección antes de imputar lo suyo. Entre una anulación y la
escritura siguiente, una cuenta puede mostrar deuda y crédito a favor a la vez; el estado informa los dos.

- **Descartadas**: el exceso devuelto a la imputación más antigua (la última es la que quedó de más);
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
duplicaría filas; auditar sólo en el libro dejaría al 7 auditando a medias. Es obligación explícita
del llamador: evento y auditoría comparten transacción. Para el saldo, `evento_de_emision` del libro es
la autoridad de "anulada"; el 7 deriva ese estado, no mantiene otra autoridad independiente. El estado
"distribuida" vive sólo en los eventos de liquidación del 7. La emisión y la anulación
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

`importe` como texto con `Dinero` (D-046), positivo en el modelo del cuerpo (negativo/cero → 422,
antes de SQL). UUID del cuerpo con `Annotated[UUID, Field(strict=False)]`, como `cuerpos.py`. Respuesta 201 `{"movimiento_id": UUID}`; la repetición
idempotente también 201 con el mismo id. Orden: 401 (`RutaConIdentidad`, antes de leer el cuerpo); 422
del cuerpo; 404 del edificio; 403 del permiso; 404 del movimiento u obligación inexistente, de otro edificio
incluida la misma administración, o de otra administración; 409/422 del dominio. El control del permiso
precede a buscar el recurso: un AE no puede usar errores para descubrir movimientos.

`proptech_api/errores.py` declara **una vez** los modelos de las formas que la API ya usa (401 `{"detail":
str}`, 403 `{"detail": {"detalle", "permiso_faltante"}}`, 404 `{"detail": "no encontrado"}`, 409
`{"detail": "conflicto", "campo"}` y el 422 de FastAPI) y `RESPUESTAS_DE_ERROR`, que la ruta pasa en
`responses=`. También declara 500 `{"error":"interno","request_id": UUID}` como el middleware y 503
`{"detail":"temporalmente no disponible"}`. Un test compara OpenAPI con las siete formas. Las rutas viejas no se
retocan (explore 4.8). Los errores del dominio (`cuenta_corriente/aplicacion/errores.py`) se traducen con
un manejador propio, con las mismas formas.

La traducción de errores SQL corre dentro de `sesion.begin_nested()` (SAVEPOINT), como `complejos`;
se revierte ese SAVEPOINT antes de lanzar el error de aplicación. Nunca se deja la Session del
llamador en 25P02; la API deshace toda su transacción si la operación falla. Sin filtrar SQL ni valores:

| SQLSTATE | traducción / respuesta |
|---|---|
| 23505 `uq_mov_operacion` / `uq_obligacion_operacion` | `Conflicto("operacion_id")`, 409 |
| 23505 `uq_mov_corrige_a` | `Conflicto("movimiento_id")`, 409 |
| 23505 `uq_emision_intento` | `Conflicto("periodo")`, 409 |
| 23505 `emision_pkey` / `uq_obligacion_emision` | `Conflicto("emision_id")`, 409 |
| 23505 `uq_evento_emision_tipo` | `Conflicto("emision_id")`, 409 |
| 23505 `uq_cuenta_unidad` / `uq_cuenta_persona` | `Conflicto("unidad_id")` / `Conflicto("persona_id")`, 409 |
| 23505 de otro nombre no reconocido | 500 declarado; no inventar un campo |
| 23503 | `NoEncontrado`, 404 |
| 23514 | 500 declarado: violación de contrato que el borde debía rechazar |
| 40P01 / 40001 | 503 declarado, sin reintento interno; el llamador puede repetir con la misma clave |
| 42501 | 500 declarado; tenant/privilegio incoherente no se expone al cliente |
| 55P03 / 57014 si hay límites de espera | 503 declarado, sin replay parcial |

Se elige 503 antes que retry interno: evita repetir una unidad transaccional del llamador a medias;
revertir esta elección exige diseñar el retry de la transacción completa y sus tests, no sólo el INSERT.

- **Descartado**: el esquema nuevo `{"detail": {"tipo", "campo"?, "detalle"?}}` del explore 4.8. Dejaría
  dos formas de error conviviendo en la misma API, y la web ya parsea las de hoy.
- **Costo de revertir**: un archivo de modelos y un test.

### D11 · El SQL de cada módulo sólo nombra sus tablas (E11, explore 4.2)

Test nuevo en `test_fronteras_de_modulos.py`: recorre con `ast` los literales de texto de cada archivo de
`proptech_core/<módulo>/` (sin `compartido`, que es infraestructura), y `proptech_api` / `proptech_worker`
para impedir que nombren directamente las siete tablas del libro/candado. Busca, insensible a
mayúsculas, `FROM`, `JOIN`, `INTO`, `UPDATE` y `TABLE` seguidos de un nombre; excluye `FOR UPDATE OF` y
funciones en FROM (`unnest`, `generate_series`), y compara contra un mapa tabla → módulo declarado en el test.
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

`estado_de_cuenta` y `deuda_del_edificio` obtienen **una sola foto con una sentencia SQL** (CTEs
que devuelven conjuntos de filas, sin multiplicarlos con joins cartesianos); luego llaman a
`calcular_estado`. En READ COMMITTED, el snapshot por sentencia evita mezclar movimientos de una
transacción con imputaciones de otra. Descartadas: varias sentencias sin candado (foto inconsistente),
REPEATABLE READ para escribir (D2 lo prohíbe), bloquear para cada lectura (serializa consultas).
La lectura del edificio primero enumera `cuenta` por `(administracion_id,complejo_id)` y usa JOIN o
`= ANY(ids)` para obligaciones, movimientos e imputaciones; no filtra sólo por complejo en esas tablas.
La 3.7 exige `EXPLAIN (ANALYZE, BUFFERS)` con datos de varios edificios y rechaza todo `Seq Scan`,
incluido paralelo, sobre `obligacion`, `movimiento` e `imputacion`.

`saldo_anterior(emision_id,cuenta_id)` es **deuda residual no negativa** sin obligaciones de esa emisión,
calculada desde el estado actual, no saldo neto; el crédito a favor se informa separado. Si sólo hay
$5.000 a favor, saldo anterior es $0,00. El 7 lo toma bajo el candado **después de imputar pendientes en la
nueva emisión**, incluyendo las nuevas imputaciones a deuda previa, y lo guarda como foto al emitir para R06: releerlo tras un pago posterior puede dar
otro valor, no debe reescribir la foto publicada. `registrar_emision` devuelve esa foto por cuenta en
`EmisionRegistrada`, para que el 7 la persista. La deuda a fecha pasada no entra: su consumidor 4c
resuelve fecha de registro/valor/evento en P53/P54, y 10b para libre deuda. El interés se imputa al
período de la obligación que lo generó; contestar P53 "septiembre" cambia el moroso crítico (4c), no
reubica las imputaciones R04 del libro.

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
- [Después de roles el migrador no puede ALTER, CREATE INDEX ni DROP INDEX sobre las seis tablas]
  → E10 declara ese costo: lo que no esté en 0023 queda así hasta el préstamo D-115.3. Tablas nuevas
  pueden referenciar las existentes mediante REFERENCES de E15, sin alterar el libro.
- [La numeración `0023` choca con el 3c] → quien mergee segundo renumera `revision`/`down_revision` y corre
  la suite completa; `ensayo-roles.sh` nombra revisiones, así que se revisa también. Antes del merge,
  tarea 6.1 hace git fetch y compara versions/ contra origin/main; con 0023+ ajenas renumera y reencadena.
  Los dos changes pueden tocar `unidades.py` y `grupos.py` por auditoría, `_edificios.py`, tipos y
  fixtures web: resolver por contenido y correr suites, no sólo renumerar.
- [INSERT de cuentas o candados nuevos también espera en un índice único] → ordenar cuentas por
  unidad_id en una sentencia, candados por cuenta_id y bloquear una sola vez por transacción; 3.6
  cruza emisiones de unidades nuevas (no sólo cuentas ya existentes).
- [El exceso devuelto (D8) es una regla nueva que ninguna decisión escribe] → E7 la firma; R05 la escribe
  al archivar.
- [El fondo de reserva en tercer lugar es una lectura] → E5 provisorio, A-4 (P60) antes del piloto.
- [`TRUNCATE ... CASCADE` de la sonda toma `ACCESS EXCLUSIVE` sobre las siete tablas durante `despues()`]
  → sólo en el deploy, dentro de un savepoint que se revierte (D2 del 4a).
- [Un `ROLLBACK` del deploy que borra tablas con plata] → el `downgrade` de `0023` se niega si alguna tabla
  del libro tiene filas (Migration Plan).

### Preguntas abiertas que el design no cierra

- **A-4 (P60), a validar (P42)**: fondo de reserva (E5), corrección del crédito de corrección (E6),
  exceso por imputación más reciente (E7) y destino fijo sin sobrante libre (E16). No se inventa R42:
  se llevan como preguntas de validación de R05/R08 por AN-11.
- **"Hoy" de la corrección** (D7): si `complejos` no tiene una fuente única de la fecha del día, el
  constructor lo trae antes de elegir.

## Migration Plan

**Deploy**: `roles antes` → `alembic upgrade head` (`0023` y `0024` juntas, en una transacción por
`env.py`) → `roles despues` (transfiere las seis tablas y sus seis funciones al rol de arranque, da REFERENCES al migrador
sobre las seis y el candado, revoca DELETE del candado a la app y verifica por el efecto) → API y worker (el chequeo de arranque ahora incluye las seis). Un corte en
cualquier punto deja la base en `0022`, o con las tablas todavía del migrador y la API sin arrancar.

**Rollback, mientras ninguna tabla del libro tenga filas y nadie haya corregido nada**. El código viejo
no arranca sobre la base nueva (su `alembic upgrade head` no encuentra `0024`), así que el orden es:

1. Con el código **nuevo** todavía desplegado, como rol de arranque: comprobar que las seis tablas están
   vacías (`SELECT EXISTS` en cada una; el superusuario no pasa por RLS). **Si alguna tiene filas, no se
   sigue**: es el punto de no retorno. Si están vacías, devolver al migrador las seis tablas y sus seis
   funciones (`ALTER TABLE ... OWNER TO proptech_migrador`, `ALTER FUNCTION fn_<tabla>_bloqueada() OWNER
   TO proptech_migrador`). `ensayo-roles.sh` hace este paso (1.4).
2. Con el código nuevo, como migrador: `alembic downgrade 0022`. Baja `0024` (el valor del vocabulario) y
   `0023` (las ocho tablas, incluido el vocabulario). El `downgrade` de `0023` se vuelve a negar por su cuenta si encuentra filas:
   como dueño, hace `NO FORCE ROW LEVEL SECURITY` y cuenta (con `FORCE`, el migrador sin tenant vería
   cero filas y borraría plata creyendo que no hay, DB-3 del 4a).
3. Recién entonces, desplegar el código viejo.

**Punto de no retorno**: la primera fila en cualquier tabla del libro, o la primera corrección auditada
(bajar `0024` choca con `fk_auditoria_accion`, `23503`). Desde ahí, la única vuelta atrás es restaurar el
respaldo, o arreglar hacia adelante. Se acepta así porque todavía no hay producción (como D-114.5). La
tarea 1.4 ensaya la bajada completa en un compose aislado y fija con un test la negativa del `downgrade`
con una fila. Incluye mutante sin NO FORCE, sin tenant en la conexión Alembic, y diff de
`pg_dump --schema-only` en 0022 antes/después del ciclo, con dueños, permisos, políticas y funciones;
normaliza sólo cabeceras volátiles del dump, nunca DDL ni ACL.

Ninguna migración reescribe filas.
