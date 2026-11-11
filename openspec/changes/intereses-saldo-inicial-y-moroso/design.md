# Design

## Context

Ver `proposal.md` (Why). Lo que condiciona el enfoque, verificado contra `main` en `533a440`:

- **El libro existe y no se altera.** `0023` creó `cuenta`, `emision`, `evento_de_emision`, `obligacion`,
  `movimiento` e `imputacion`, de sólo agregar y de dueño el rol de arranque (D-115.1). Después de
  `roles despues`, el migrador no puede `ALTER`, `CREATE INDEX` ni `DROP INDEX` sobre ellas; cambiar
  columnas, CHECK o únicos exige el préstamo D-115.3, que **no está construido** (E10 del 4b). Sí puede
  crear tablas nuevas con FK a esas seis (E15 del 4b, `GRANT REFERENCES` en `roles.py:920-935`), pero
  **no** a `configuracion_versionada`, que también es protegida y no recibe `REFERENCES`.
- **Lo que `0023` ya anticipó para el 4c**: `movimiento.corte`, el CHECK `ck_mov_interes` (un interés
  exige obligación, componente `interes` y corte), el único `uq_mov_interes(administracion_id,
  obligacion_id, corte) WHERE tipo='interes'` (`0023:205-206`), `obligacion.operacion_id` con
  `ck_obligacion_origen` (emisión u operación, exactamente una), `uq_obligacion_operacion(administracion_id,
  operacion_id, cuenta_id, periodo)` (`0023:199-200`), el par `('saldo_inicial','credito')` en
  `tipo_de_movimiento`, y las claves compuestas `uq_obligacion_cuenta_id(administracion_id, complejo_id,
  cuenta_id, id)` y `uq_mov_sentido(administracion_id, complejo_id, cuenta_id, id, sentido)`
  (`0023:128-132`), que permiten FK que fijan tenant, edificio **y cuenta** a la vez.
- **No hay columnas para el detalle del interés** (días, tasa, base) ni para el origen del saldo inicial
  (archivo, fila, motivo, fecha de migración): van en tablas nuevas.
- **`registrar_emision`** (`cuenta_corriente/aplicacion/emisiones.py:124-229`) inserta emisión y
  obligaciones, bloquea sólo las cuentas de la emisión (`:193`), imputa pendientes por cuenta (`:220-221`,
  cada `imputar_pendientes` lee su propia `foto`) y publica el saldo anterior con una sola llamada a
  `fotos` (`:224`). El replay (`_replay`, `:85-121`) bloquea (`:116`) y vuelve a leer con `fotos`
  (`:117`); su comentario (`:113-115`, RB4B-05) declara que **el libro no persiste la foto del saldo
  anterior** y que el replay la recalcula.
- **`anular_emision`** (`:232-285`) descubre sus cuentas sólo desde `obligacion WHERE emision_id=:id`
  (`:257-264`) y las bloquea (`:265`). Las correcciones (`correcciones.py:167-189`) bloquean la cuenta del
  movimiento corregido y recién ahí miran `_anulada` de su emisión. Ningún caso de uso existente escribe
  `movimiento.emision_id` fuera de `registrar_emision` (verificado con `rg emision_id` en
  `correcciones.py` y `creditos.py`).
- **El estado** (`dominio/estado.py`) ya excluye movimientos de emisiones anuladas (`:112`, también los
  que sólo tienen `emision_id`, porque la foto junta en `anuladas` las emisiones de obligaciones **y** de
  movimientos, `lecturas.py:59-64`), pares de contra-asiento, débitos sobre obligaciones que no cuentan y
  ajustes de interés enlazados (D-085), y topea imputaciones (E7). No expone qué parte de cada imputación
  cuenta ni el `corte` de los movimientos. `calcular_estado` no recibe fecha: la foto
  (`lecturas.py:37-69`) trae **todo** lo registrado, sin filtro temporal.
- **La configuración** vive en `complejos` (`configuracion_versionada`, de sólo agregar): tasa
  `NUMERIC(4,2)` de 0 a 10, días de gracia 0 a 31, forma `proporcional_por_dia | mes_entero`,
  `umbral_saldo_chico` resuelto al escribir (D-114.1). Se lee con
  `complejos.aplicacion.lectura.configuracion_vigente(sesion, complejo_id, fecha)` (`lectura.py:213-227`),
  que **lanza `NoEncontrado` si el edificio no es visible** y **devuelve `None` si el edificio existe pero
  no hay versión con `vigente_desde <= fecha`**. El estado de migración se lee con `cargar_complejo`
  (campo `estado_migracion`).
- **RLS de las tablas nuevas**: `aislar_por_administracion` (`migraciones/ayudas_rls.py:41-48`) hace
  `ENABLE`, `FORCE` y la política. `proptech_app` no es dueño de ninguna tabla de sólo agregar después de
  `roles despues` (`roles.py:898-918`), así que para la app alcanzan `ENABLE` y la política: **quitar sólo
  el `FORCE` no le deja ver filas ajenas**. El `FORCE` lo vigilan el catálogo
  (`tests/integracion/test_catalogo_rls.py`, `_rls_forzada`, `:111-118`, desde `revisar_catalogo`, que recorre todas
  las tablas de `public`, `:268`) y el chequeo de arranque (`roles.py:788-800`, `_verificar_tabla_protegida`).
- **Fronteras** (D-116, `tests/unitarios/test_fronteras_de_modulos.py`): entre módulos sólo
  `aplicacion`; el SQL de cada módulo sólo nombra tablas propias (`_DUENO_DE_TABLA`). Hoy
  `cuenta_corriente` importa sólo `acceso` y `compartido`; `complejos` no importa `cuenta_corriente`, así
  que `cuenta_corriente → complejos.aplicacion` no crea ciclo.
- **Tests del libro**: la semilla `tests/integracion/_cuenta_corriente.py::sembrar` no crea ninguna
  versión de configuración. Llaman a `registrar_emision` directamente ocho archivos de integración
  (inventario del revisor, `propose-1-plan-reviewer.md:151-160`): `test_cc_lecturas.py`,
  `test_cc_emisiones.py`, `test_cc_creditos.py`, `test_cc_correcciones.py`, `test_cc_replay_carrera.py`,
  `test_cc_concurrencia.py`, `test_cc_anulacion_candado.py` y `test_cc_auditoria_api.py` (este último
  con `ApiEdificio`, no con `sembrar`). Ningún consumidor de producción.

## Goals / Non-Goals

**Goals:**

- Interés de R03 exacto al centavo, reproducible desde el libro y explicable por tramo.
- Un contrato de saldo inicial que el 5 pueda llamar al confirmar, sin que el 4c decida nada del
  borrador ni de la comparación, que acepte varias filas del archivo por período.
- Situación de cobranza como función derivada, sin estado guardado, con un significado explícito de su
  fecha.
- Cerrar RF-01, RF-02 y RB-6 con tests que se vean fallar por su mutante, y extender la garantía de
  RF-02 a las cuentas que la emisión sólo toca con interés.
- Cero cambios a las tablas de `0023` y ningún préstamo D-115.3.

**Non-Goals:**

- Rutas de API, pantallas, permisos nuevos o vocabulario de auditoría (lo traen el 5, el 7 y el 10a).
- Cuentas de persona (4d), recargo de segundo vencimiento (R26), día inhábil (R35), tasa de la
  extraordinaria (R36), unidades del consorcio (R39), gestión judicial (R31).
- Corregir intereses ya registrados con otra lógica: lo que el libro registró, queda.
- Situación de cobranza **histórica** (el libro reconstruido a una fecha pasada): ver E14.
- Persistir la foto del saldo anterior de cada emisión: ver E15.

## Decisions

### D0 · Cuentas alcanzadas por una emisión

Las **cuentas alcanzadas** por una emisión son las que tienen una obligación de esa emisión **más** las
que tienen un movimiento con su `emision_id` (en el 4c, sólo sus intereses: con E10 una unidad sin
expensa ese mes puede recibir interés). Se leen en una sentencia:
`SELECT cuenta_id FROM obligacion WHERE emision_id=:id UNION SELECT cuenta_id FROM movimiento WHERE
emision_id=:id`. El conjunto queda fijo cuando la emisión se confirma: sólo `registrar_emision`, dentro
de su transacción, escribe movimientos con `emision_id` (Context).

Lo usan tres caminos, cada uno con **un solo** `bloquear_cuentas` sobre el conjunto ordenado (E2 del 4b):

- `anular_emision`: bloquea las cuentas alcanzadas, no sólo las de sus obligaciones (PR-02). Así un
  contra-asiento del interés de una cuenta sin obligación en la emisión (que bloquea esa cuenta y después
  mira `_anulada`) y la anulación se serializan.
- `_replay`: bloquea las cuentas alcanzadas y lee **una** foto de todas.
- `registrar_emision`: la foto final, la que publica el saldo anterior, pide las cuentas alcanzadas.

- **Alternativa descartada**: dejar la anulación como está y que el 7 bloquee de más antes de anular. El
  contrato nuevo (interés en cuentas sin obligación) nace en el 4c; delegarlo deja una ventana entre
  el 4c y el 7 y un consumidor que puede olvidarlo.

### D1 · El interés se registra dentro de `registrar_emision`

`registrar_emision` calcula y registra el interés en la misma transacción, después de insertar las
obligaciones de la emisión y antes de imputar pendientes, para que el crédito a favor vaya primero al
interés (R04) y el saldo anterior lo incluya.

- **Orden dentro del SAVEPOINT** (pasos 3 y 4 de hoy): insertar emisión → crear cuentas de las unidades
  de la emisión → leer las cuentas de unidad del edificio → `bloquear_cuentas` **una sola vez** con la
  unión ordenada → insertar obligaciones → `fotos` de las cuentas bloqueadas → si alguna obligación que
  cuenta vence antes del corte, `configuracion_vigente(sesion, complejo_id, corte)`: si devuelve `None`,
  `Conflicto("configuracion")`; si lanza `NoEncontrado`, se propaga tal cual (no se convierte en conflicto
  de configuración; en la práctica la FK de `emision` ya rechazó un edificio invisible en el paso 3) →
  calcular en el dominio → insertar intereses y tramos → imputar pendientes en las cuentas alcanzadas →
  **una** `fotos` final de las cuentas alcanzadas.
- **Contrato de `EmisionRegistrada`**: conserva `emision_id`, `intento` y `cuentas` (unidad → cuenta de
  las obligaciones, como hoy); el saldo anterior pasa a cubrir las **cuentas alcanzadas**; suma
  `intereses`: por cuenta, los débitos de interés con `emision_id` de esta emisión (obligación, corte,
  importe), leídos del libro.
- **Replay** (E15, opción por defecto): devuelve los mismos `intereses` (los registrados, leídos por
  `emision_id`, cuenten o no hoy) y un saldo anterior **recalculado** al momento del replay, como hace
  el 4b (RB4B-05). No promete el mismo saldo anterior que la primera respuesta si después hubo pagos,
  correcciones o la anulación. Nunca escribe.
- **Alternativa descartada**: un caso de uso aparte `registrar_intereses` que llama el 7. El interés
  referencia la emisión (FK), así que va después de ella, y el saldo anterior se publica dentro de
  `registrar_emision`: el 7 tendría que repetir la foto y la publicación, o publicar un saldo sin el
  interés. Además deja al 7 la posibilidad de olvidarlo.
- **Costo de revertir**: bajo; es lógica de aplicación, sin esquema propio salvo `tramo_de_interes`.

### D2 · Cálculo puro en `cuenta_corriente/dominio/intereses.py`

Una función pura recibe la foto de una cuenta (obligaciones con su `interes_desde`, movimientos con
`fecha_valor`, `corte` y sus `tramos` como pares `(desde, hasta)`, partes de imputación que cuentan), el
corte y los parámetros (tasa, gracia, forma, versión) y devuelve, por obligación, los tramos y el importe
redondeado. Reglas:

- **Inicio natural**: el día siguiente al vencimiento; para una obligación de saldo inicial, el día
  siguiente a `max(vencimiento, fecha_de_migracion)` (`interes_desde`).
- **Días cubiertos** (E17, PR-12): la **unión de los intervalos** `[desde, hasta]` de los tramos de los
  intereses **que cuentan** de esa obligación. Un interés que no cuenta (emisión anulada, contra-asentado)
  no cubre ningún día (E1). Un interés sin tramos (sólo el importado, con corte en la migración) no aporta
  intervalos: todos sus días son anteriores al inicio natural. **No** se usa el máximo de los `hasta`: si
  se contra-asienta un interés anterior y uno posterior sigue contando, el hueco queda sin cubrir y se
  cobra.
- **Días a cobrar**: los días entre el inicio natural y el corte que no están cubiertos. Pueden ser
  varios intervalos (un hueco viejo más el tramo nuevo); todos se cobran en este corte, con la
  configuración vigente al corte (E4). Si no hay ninguno, nada.
- **Si ya existe un interés con este corte para esa obligación, cuente o no**, no se calcula nada para
  ella en este corte (E1; respeta `uq_mov_interes` sin tocarlo). Sus días siguen sin cubrir y los cobra
  el corte siguiente.
- **Corte sin importe** (E19): si el cálculo da $0,00 (tasa 0, base 0 o una base tan chica que redondea a
  cero), no se registra nada y esos días siguen sin cubrir: los cobra el primer corte que registre, con su
  configuración. Una tasa 0 difiere, no perdona.
- **Gracia**: si `corte - vencimiento <= dias_de_gracia`, nada en este corte. Una imputación de capital
  con fecha efectiva `<= vencimiento + gracia` se trata como pagada al vencimiento (no genera interés).
- **Base del día t**: capital de la obligación + débitos de capital que cuentan con `fecha_valor < t` −
  partes de imputación de capital que cuentan con fecha efectiva `< t` (o dentro de la gracia), nunca
  menor que cero. La fecha efectiva de una imputación es la `fecha_valor` del crédito que la hizo (E5).
- **Proporcional**: suma de `base(t) * tasa / 100 / 30` para cada día a cobrar (E3). Los tramos
  guardados se cortan donde cambia la base y donde termina un intervalo de días a cobrar.
- **Mes entero, por meses calendario** (E3 y E13, decididos por Juani el 30/10/2026): los días a cobrar se
  agrupan por **mes calendario**; cada mes calendario con al menos un día a cobrar cobra **un mes entero**,
  `base(primer día a cobrar de ese mes) * tasa / 100`, aunque tenga un solo día (una fracción de mes
  calendario cuenta como mes entero: "un día de atraso cobra el mes completo", R03). Cada mes cobrado es un
  tramo guardado con `desde` = su primer día a cobrar y `hasta` = su último día a cobrar. Como el corte es
  siempre el último día de un mes (D-113, E2), ningún tramo pasa el corte y `hasta` es siempre el último
  día de su mes. **No** hay bloques de 30 días: tras un corte proporcional hasta el 30/09, el corte del
  31/10 cobra **un** mes, $3.000,00 sobre $100.000 al 3% (PR-10). Consecuencias:
  - una obligación que vence el 29/09 cobra un mes en el corte 30/09 (tramo 30/09-30/09) y otro en el
    corte 31/10 (tramo 01/10-31/10);
  - una obligación migrada el 15/10 cobra en el corte 31/10 un mes entero por la fracción 16/10-31/10 y
    nunca días anteriores a la migración (E18 decide si esa fracción se cobra);
  - al pasar de proporcional a mes entero, el primer mes cobrado es el siguiente al último corte
    proporcional; al pasar de mes entero a proporcional, el proporcional empieza el día siguiente al
    último mes cobrado: sin hueco ni doble cobro, porque los dos terminan siempre en un fin de mes;
  - si el corte cae dentro de la gracia, el corte siguiente cobra cada mes calendario pendiente: vence
    28/09, gracia 5, corte 30/09 sin interés, corte 31/10 cobra septiembre (29/09-30/09) y octubre,
    $6.000,00 sobre $100.000 al 3%, lo mismo que sin gracia en dos cortes.
- **Invariante de mes entero**: dentro de un mes calendario, los días a cobrar son contiguos. Se sigue de
  que los cortes son fines de mes y de que cada interés cuenta o deja de contar entero, con todos sus
  tramos: lo cubierto dentro de un mes es vacío o va desde el inicio natural (o el día 1) hasta el fin del
  mes. Si el dominio encontrara días a cobrar no contiguos dentro de un mes, lanza un error y la emisión no
  se registra: nunca cobra dos meses por uno. La propiedad de la tarea 4.5 lo ejercita.
- **Aritmética**: exacta (`fractions.Fraction` o `Decimal` con contexto local amplio), sin `float`;
  el importe se redondea **una vez** con `compartido.reparto.redondear_al_centavo` (D-113). Si da $0,00,
  no se registra nada.

El dominio importa sólo `compartido.dinero`, `compartido.porcentaje` y `compartido.reparto` (lista
permitida de D-116.c).

### D3 · `estado.py` expone lo que el cálculo necesita, sin cambiar lo que ya calcula

`calcular_estado` agrega al `EstadoDeCuenta` las partes de imputación que cuentan (movimiento,
obligación, componente, parte topeada), que hoy calcula y descarta en el paso 3. `Movimiento` suma
`corte: date | None` y `tramos: tuple[tuple[date, date], ...]` (vacía si no es interés o es el importado);
`Obligacion` suma `interes_desde: date`. La foto SQL (`lecturas.py:37-69`, que ya arma cada movimiento con
`json_build_object`) suma `'corte', m.corte` y `'tramos', (SELECT coalesce(json_agg(json_build_array(tr.desde,
tr.hasta) ORDER BY tr.desde), '[]') FROM tramo_de_interes tr WHERE tr.administracion_id = t.adm AND
tr.movimiento_id = m.id)` dentro del objeto de cada movimiento, y, con un `LEFT JOIN` a
`carga_de_saldo_inicial` por `operacion_id`, el `interes_desde` de cada obligación. Sigue siendo **una**
sentencia por foto. Se traen **todos** los intervalos, no su máximo (E17): el dominio necesita la unión.

- **Riesgo**: los planes de `EXPLAIN` fijados por la tarea 3.7 del 4b. Se vuelven a correr; el `JOIN` va
  por `(administracion_id, operacion_id)`, con su único, y el subselect por
  `ix_tramo_movimiento(administracion_id, movimiento_id)`.
- **Alternativa descartada**: una segunda consulta para el detalle. Rompe "una sola sentencia por foto"
  (E12 del 4b).

### D4 · Tabla `tramo_de_interes`

`tramo_de_interes(id, administracion_id, complejo_id, cuenta_id, movimiento_id, sentido_del_movimiento,
desde, hasta, dias, base NUMERIC(14,2), tasa_mensual NUMERIC(4,2), forma_de_calculo, dias_de_gracia,
configuracion_id, registrado_en)`:

- FK `(administracion_id, complejo_id, cuenta_id, movimiento_id, sentido_del_movimiento)` →
  `movimiento` por `uq_mov_sentido`: fija tenant, edificio y **cuenta** del movimiento, en un solo
  candado de base. `sentido_del_movimiento` con CHECK `= 'debito'`.
- **Sin `obligacion_id`**: la obligación sale del movimiento (`movimiento.obligacion_id`, obligatoria
  por `ck_mov_interes`). Guardarla dos veces abriría una incoherencia (tramo de una obligación, movimiento
  de otra) que ninguna FK existente impide.
- FK `(administracion_id, complejo_id)` → `complejo`, como `fk_mov_complejo` de `0023`: la exige el
  catálogo (`test_catalogo_rls.py`, `_tiene_fk_compuesta_a_complejo`) para toda tabla con `complejo_id`.
  Las tres tablas nuevas la llevan.
- `configuracion_id` **sin FK**: `configuracion_versionada` es protegida y no da `REFERENCES` al
  migrador (Context). La coherencia la asegura la aplicación (lee la versión en la misma transacción) y
  la prueba la tarea 5.2.
- Que el movimiento referenciado sea de tipo `interes` lo asegura la aplicación (no hay único de
  `movimiento` con `tipo` sin `importe`); límite declarado, con test de aplicación.
- CHECK `hasta >= desde`, `dias = hasta - desde + 1`, `base > 0`, forma en el vocabulario de la
  configuración y, si la forma es `mes_entero`, que el tramo sea de un solo mes calendario y termine en
  su último día (E3, E13): `extract(day FROM hasta + 1) = 1 AND desde > hasta - extract(day FROM
  hasta)::int` (sin `date_trunc` sobre `date`, que resuelve a `timestamptz`). Cada condición tiene su
  negativo discriminante (PR-14, tarea 2.1): 30/09-31/10 con `dias = 32` termina en fin de mes y sólo lo
  rechaza la de mismo mes; 01/10-30/10 es de un solo mes y sólo lo rechaza la de fin de mes. Sin columna de interés por
  tramo: el importe vive en el movimiento y la suma exacta de los tramos se verifica en test.
- Los tramos de un mismo movimiento **pueden no ser contiguos** (un hueco recuperado más el tramo nuevo,
  E17); que no se solapen entre sí ni con los de otro interés que cuenta de la misma obligación lo asegura
  el dominio y lo vigila la propiedad de 4.5, no la base.

- **Alternativa descartada**: guardar el detalle en una columna JSON de `movimiento` (exige `ALTER` con
  préstamo) o un solo renglón con base promedio (pierde "pago parcial reduce la base").

### D5 · Saldo inicial: una carga por edificio, filas del archivo y dos tablas de origen

`registrar_saldo_inicial(sesion, identidad, *, complejo_id, operacion_id, fecha_de_migracion, origen,
unidades, request_id, reloj) -> SaldoInicialRegistrado` en `cuenta_corriente/aplicacion/saldo_inicial.py`.
Contrato pensado para el 5 (E9, E16):

- `origen`: `importador` con `archivo` (texto, 1 a 255) o `manual` con `motivo` (1 a 500, normalizado
  como en las correcciones).
- `unidades`: por unidad, un modo (`detalle` o `total`) y sus **filas**, tal como vienen del archivo
  después de que el 5 traduce el concepto a componente y el signo a deuda o crédito:
  - fila de deuda en `detalle`: `fila` (número de fila del archivo; nulo sólo en carga manual),
    `periodo`, `vencimiento`, `componente` (`ordinaria`, `fondo_de_reserva`, `extraordinaria`),
    `importe` (≥ 0) e `interes_acumulado` (≥ 0);
  - fila de deuda en `total`: `fila`, `importe` (≥ 0) e `interes_acumulado` (≥ 0);
  - fila de crédito: `fila` e `importe` (> 0). El 5 convierte el saldo negativo del Excel en esta fila.
- **Agrupación, en el 4c** (E16, opción por defecto): las filas de deuda de una unidad en `detalle` se
  agrupan por `periodo` en **una** obligación con la suma por componente; el interés acumulado del
  período es la suma de sus filas. Reglas: todas las filas de un mismo período tienen el mismo
  `vencimiento` (si no, se rechaza nombrando `vencimiento`); un número de `fila` no se repite en toda la
  carga (si no, `fila`); un período cuyas filas suman capital 0 se rechaza nombrando `interes_acumulado`
  (E11). Las filas de una unidad en `total` se suman en una obligación con todo el capital en
  `ordinaria`. Varias filas de crédito de una unidad se suman en un crédito.
- Devuelve el `operacion_id`, la cuenta de cada unidad y los totales de capital, interés importado y
  crédito, por unidad y del edificio, para que el 5 los compare con su borrador.

- **Firma del pedido** (PR-11, E16): agrupar pierde el aporte de cada fila (dos filas de septiembre de
  ordinaria por $85.000 y $20.000 dejan la misma obligación de $105.000 que $84.000 y $21.000), así que el
  replay **no** puede compararse contra lo que quedó en el libro, como hace `_replay` de emisiones
  (`emisiones.py:72`, `_firma`, y `:97-111`). La carga guarda `firma_del_pedido`: `"v1:"` + SHA-256 en hexadecimal del pedido
  **validado y normalizado**, serializado como JSON canónico (claves ordenadas, sin espacios, UTF-8). La
  normalización: `complejo_id`, `fecha_de_migracion`, `origen` con `archivo` o `motivo` ya normalizado; las
  unidades ordenadas por `unidad_id`, cada una con su modo y sus filas **ordenadas** por la tupla completa
  (`fila`, tipo deuda o crédito, `periodo`, `vencimiento`, `componente`, `importe`, `interes_acumulado`;
  fila nula primero); fechas ISO; importes como texto con dos decimales (`85000` y `85000.00` dan lo
  mismo). Quedan fuera `operacion_id`, `request_id`, la identidad y el reloj, como en la firma del 4b. El
  orden en que el 5 manda filas o unidades no cambia la firma; cualquier diferencia en un dato de una fila,
  sí. El prefijo `v1` permite cambiar la normalización en el futuro sin romper el replay de cargas viejas
  (una versión nueva compara con la suya). Por qué una firma y no el aporte por fila en
  `origen_de_saldo_inicial`: es una columna y una función pura, sin reconstruir el pedido con SQL; cubre
  todo el pedido (modo, archivo, filas en cero) y no sólo lo que forma movimientos; y R09 pide guardar
  archivo y fila de origen ("Trazabilidad", `05_reglas_de_negocio.md:356`), no el importe por fila, que
  conserva el borrador del 5. Costo: el libro sabe qué filas formaron cada obligación, interés o crédito,
  pero no cuánto aportó cada una (lo mismo que la alternativa de E16).

Pasos: transacción e identidad → validar (spec "La carga rechaza entradas…") → calcular la firma →
replay por `operacion_id` (antes de validar el estado, como D5 del 4b): si existe una carga con ese
`operacion_id` y la misma firma, devuelve lo registrado; con otra firma, `Conflicto("operacion_id")` →
estado de migración `pendiente` vía `cargar_complejo` → insertar `carga_de_saldo_inicial` con su firma
(único por `(administracion_id, complejo_id)` y por `(administracion_id, operacion_id)`) → crear cuentas → `bloquear_cuentas` una vez → obligaciones con
`operacion_id` (total único: período el primer día del mes de migración, vencimiento la migración) →
interés acumulado de cada período como movimiento `interes` con `corte = fecha_de_migracion`, sin emisión
ni `operacion_id` → crédito como movimiento `saldo_inicial` con un `operacion_id` derivado
determinísticamente (`uuid5` del `operacion_id` de la carga y la unidad), porque `uq_mov_operacion` no
deja reusar el de la carga → `origen_de_saldo_inicial`: cada fila con importe > 0 liga la obligación (o
el crédito) que formó, y cada fila con interés > 0 liga además el movimiento de interés de su período →
`imputar_pendientes` por cuenta.

- `carga_de_saldo_inicial(id, administracion_id, complejo_id, operacion_id, fecha_de_migracion, origen,
  archivo, motivo, firma_del_pedido, registrado_por, request_id, registrado_en)` con CHECK
  `origen='importador' AND archivo IS NOT NULL` o `origen='manual' AND motivo IS NOT NULL`, CHECK
  `firma_del_pedido ~ '^v1:[0-9a-f]{64}$'`, único `(administracion_id, complejo_id, id)`
  para la FK compuesta de su origen, FK `(administracion_id, complejo_id)` → `complejo` y
  `(administracion_id, registrado_por)` → `persona`.
- `origen_de_saldo_inicial(id, administracion_id, complejo_id, carga_id, cuenta_id, fila,
  obligacion_id, movimiento_id, sentido_del_movimiento)` con `num_nonnulls(obligacion_id, movimiento_id)
  = 1`, `fila >= 1` (nula sólo en una carga manual, verificado por la aplicación), FK
  `(administracion_id, complejo_id)` → `complejo`, `(administracion_id, complejo_id, carga_id)` → carga, `(administracion_id, complejo_id, cuenta_id,
  obligacion_id)` → `obligacion` por `uq_obligacion_cuenta_id` y `(administracion_id, complejo_id,
  cuenta_id, movimiento_id, sentido_del_movimiento)` → `movimiento` por `uq_mov_sentido`: la fila de
  origen y lo que referencia son de la misma cuenta.
- **Por qué el interés importado es un `interes` con corte en la migración**: no necesita vocabulario
  nuevo, nunca entra en la base (componente `interes`), y sus días quedan antes del inicio natural de la
  obligación, que arranca el día siguiente a la migración (D2), así R03 corre desde la migración con la
  misma regla. No choca con `uq_mov_interes`: un corte de
  emisión igual a la fecha de migración no tiene días que calcular.
- **Alternativas descartadas**: un tipo nuevo `interes_previo` (necesita `operacion_id` único por fila y
  una regla aparte en el cálculo); varias cargas por edificio (sin una forma de serializarlas, porque
  `cuenta_corriente` no puede bloquear `complejo`; el único por edificio las serializa en la base); una
  obligación por fila o por concepto (choca con `uq_obligacion_operacion` y haría contar un mes como dos
  liquidaciones en R20, contra D-143); un "ajuste de saldo inicial" posterior a la confirmación dentro
  del 4c (R09 manda corregir con R08; ver PA-1).

### D6 · Situación de cobranza en `dominio/cobranza.py` y `aplicacion/cobranza.py`

Función pura `clasificar(estado, *, fecha, dias_de_gracia, umbral) -> SituacionDeCobranza` con
`total_vencido`, `liquidaciones_vencidas` (obligaciones vencidas con capital residual), `bajo_umbral`,
`deuda_de_intereses` y `moroso_critico`, más una etiqueta única con precedencia: sin deuda vencida →
bajo el umbral → deuda de intereses → moroso crítico → con deuda vencida. En aplicación,
`situacion_de_cuenta(sesion, *, cuenta_id, fecha)` y `situacion_del_edificio(sesion, *, complejo_id,
fecha)` leen la configuración vigente a `fecha` (`None` → `Conflicto("configuracion")`; `NoEncontrado`
se propaga) y la foto de las cuentas de unidad del edificio (`SENTENCIA_DEL_EDIFICIO`). Sin candado: es
una lectura.

- **Qué significa `fecha`** (E14, opción por defecto): es la **fecha de clasificación**, no un corte
  histórico. El estado es el del libro **al leer**: todos los movimientos, imputaciones y anulaciones
  registrados hasta ese momento, cualquiera sea su fecha valor. `fecha` sólo decide qué obligaciones
  están vencidas (`fecha > vencimiento + gracia`) y qué versión de configuración rige (gracia y umbral).
  Los consumidores (8, 10a, 10b) la piden con la fecha de hoy. Pedir una fecha pasada **no** reconstruye
  la deuda de ese día: un pago registrado después cuenta igual (escenario "Un pago posterior cuenta
  aunque la fecha sea anterior").
- **Alternativa descartada**: guardar una marca de moroso (D-074 la prohíbe: se deriva cada vez).

### D7 · RB-6

`redondear_al_centavo` captura `decimal.InvalidOperation` del `quantize` y la traduce a `MontoInvalido`.
El test con `1e30`, `-1e30` y `1e40` se escribe y se ve fallar antes.

### D8 · RF-01 y RF-02

- **RF-01**: el test registra, con un escucha `before_cursor_execute` de SQLAlchemy, cada ejecución de la
  sentencia de la foto (identificada por su texto compilado, no por la plantilla con `:ids`) con sus
  parámetros reales, durante `registrar_emision`; afirma que la última pide exactamente las cuentas
  alcanzadas, para emisión nueva y replay. Mutantes: "una `foto` por cuenta" en `emisiones.py:224`
  (emisión nueva) y en `:117` (replay; `:116` es el bloqueo); cada uno rojo porque la última lectura pide
  una sola cuenta. No depende de la carrera con la anulación, que hoy no puede matarlo (D-138).
- **RF-02**: el mismo `test_rf02_...` se parametriza en forma `credito` y `contra_asiento`; la segunda
  contra-asienta un crédito de corrección de una obligación de la emisión con el helper `contra(...)` de
  `test_cc_correcciones.py:114`. El crédito original se registra **antes** de instalar la pausa sobre
  `_anulada`, para que la carrera observe el contra-asiento y no su preparación. Mutante:
  `anular_emision` sin `bloquear_cuentas` debe poner rojas las dos formas.
- **RF-02 con interés** (PR-02, tarea 5.4): la misma carrera con el contra-asiento del interés de una
  cuenta que la emisión sólo alcanzó con interés. Mutante: `anular_emision` descubre sus cuentas sólo
  desde `obligacion` (como hoy) → rojo.

### D9 · Los casos de uso no autorizan ni auditan

Igual que `registrar_emision` (D9 del 4b): `registrar_saldo_inicial` lo autoriza y audita el 5, y las
situaciones de cobranza las expone con su permiso el 10a. El 4c no agrega vocabulario de auditoría ni
permisos. **Riesgo**: un llamador que no audite. Mitigación: sin ruta en el 4c, el escaneo
`test_composicion_no_escribe_sql_del_libro` y la ficha del 5 que lo nombra como obligación.

### D10 · Migración `0034_intereses_y_saldo_inicial.py`

Crea las tres tablas con el patrón de `0023`: tres triggers (fila, `TRUNCATE`, sentencia) con su
función, `aislar_por_administracion` (`ENABLE`, `FORCE`, política), las FK compuestas de D4 y D5, sin
`DELETE` para la app. Se suman a `TABLAS_DE_SOLO_AGREGAR` para que `roles despues` las transfiera al rol
de arranque, revoque `UPDATE`/`DELETE`/`TRUNCATE` de la app y las verifique por el efecto con su cierre
de dependencias (D-115.1, D-129, L-054). Índices: `ix_tramo_movimiento(administracion_id,
movimiento_id)` y `ix_origen_carga(administracion_id, carga_id)`. La bajada sólo con tablas vacías y con
el ciclo real de devolución de propiedad (como `0023`), no con un `alembic downgrade -1` aislado.

**Qué defensa vigila cada test** (PR-06): cada aserción de seguridad tiene un mutante que apaga **esa**
defensa y deja las demás, con su rojo esperado en una aserción concreta (tabla en la tarea 2.1). Resumen:
`FORCE` lo detectan el catálogo y el arranque, no el aislamiento visto por la app; `ENABLE` + política,
el aislamiento como `proptech_app`; el filtro de tenant del SQL, un ensayo con una conexión que no pasa
por RLS (precondición afirmada en el test, transacción revertida).

## Elecciones a firmar

Cada una cambia lo que se construye; el plan está escrito con la **propuesta**. Si quien firma elige otra,
vuelve al planner (no se construye con una elección sin firmar). La columna "Si se elige otra" dice qué
cambia en el plan.

| Elección | Propuesta (recomendación) | Alternativas y su consecuencia | Si se elige otra |
|---|---|---|---|
| **E1 · Re-emisión y único de interés** (contradicción con `uq_mov_interes`) | Si ya existe un interés con ese corte para la obligación, cuente o no, no se registra otro; el corte siguiente cobra los días que ningún interés que cuenta cubre (E17). Ningún día se cobra dos veces. **No hay equivalencia monetaria garantizada**: los días diferidos se cobran recién cuando exista una emisión siguiente, con la configuración vigente a **ese** corte (E4); si la tasa o la forma cambian en el medio, el importe difiere del que tenía el interés anulado | (a) Interés sin `emision_id`, que no se excluye al anular: contradice R17 y D-085 vigentes y deja sin arreglo un interés mal calculado. (b) Préstamo D-115.3 y único con `emision_id`: construye un préstamo de propiedad sobre el libro (frontera de seguridad) dentro de un change de plata | (a) cambia D0, D1 y la tarea 4.4; (b) agrega un change de infraestructura antes del 4c. PR-02 y PR-05 se resuelven aparte (D0, E15), cualquiera sea E1 |
| **E2 · Corte de cada emisión** | Último día del mes anterior al período que se emite (la emisión de octubre corta el 30/09). Coincide con "al emitir la liquidación siguiente" de R03 y con el ejemplo de D-143 | Último día del mes del período: cobraría días que todavía no pasaron si se emite a principio de mes | Escenarios de corte y tarea 5.1 |
| **E3 · Convención diaria y mes entero** | Dos partes. (1) **Proporcional, elección abierta** (D-113 no la fija): tasa mensual / 30 por día calendario de atraso. (2) **Mes entero, decidido por Juani el 30/10/2026** (orquestador, intento 3 del propose; se ratifica al firmar y se registra como decisión al archivar): se cuentan **meses calendario**, no bloques de 30 días; cada corte cobra un mes entero por cada mes calendario con días sin cubrir, aunque sea una fracción, con la base del primer día a cobrar de ese mes (D2). Tras un corte proporcional hasta el 30/09, el corte del 31/10 cobra $3.000,00 sobre $100.000 al 3%, no $6.000,00 (PR-10) | (1) Año de 365 (tasa × 12 / 365) o días reales del mes (tasa / 28..31). A validar con P58 y P42, que no bloquean. (2) Bloques de 30 días anclados en lo cubierto (plan del intento 2): descartado por Juani; cobraba dos bloques en el ejemplo | (1) tareas 4.1 y 4.5 cambian su divisor y sus importes. (2) no aplica: decidido |
| **E4 · Qué configuración rige** | Una sola versión por corte: la vigente al corte para el interés; la vigente a la fecha pedida para la cobranza | Partir el tramo en cada cambio de versión (más exacto, más tramos, y "mes entero" queda ambiguo) | Tareas 4.x y 5.2 |
| **E5 · Base día por día** | Fecha efectiva de una imputación = `fecha_valor` de su crédito; lo pagado dentro de la gracia no genera interés; una corrección baja la base desde su propia fecha | Base al corte (ignora el pago parcial, contra el test mínimo de R03); fecha de registro de la imputación | Tareas 4.1 y 4.2 |
| **E6 · Umbral con `>=`** (ratificación, no elección abierta) | Ya decidido por D-143 ("$500 o más"). Se firma sólo que el 4c lo cumple y que al archivar se corrige la palabra "supera" que quedó en R20 | Ninguna vigente | No aplica |
| **E7 · Período con sólo interés** | Elección adicional al texto amplio de R20, **no** deducción inevitable de D-143: un período con el capital pagado y sólo su interés impago no cuenta como liquidación vencida, aunque la cuenta tenga otro período con capital. Una cuenta con sólo interés vencido es "deuda de intereses" (D-109.4). Caso mixto explícito: agosto con sólo $4.000 de interés y septiembre con capital → una liquidación vencida, no moroso crítico | Contarlo como liquidación vencida en el caso mixto (agosto y septiembre → moroso crítico); se conserva "deuda de intereses" sólo cuando no hay capital vencido en ningún período | Escenario "Un período con sólo interés no cuenta" y mutante de la tarea 7.1 |
| **E8 · Qué se cuenta en R20** | Obligaciones vencidas con capital, no meses distintos | Meses distintos (cambia sólo si una carga y una emisión comparten mes) | Tarea 7.1 |
| **E9 · Saldo inicial** | D5 entero: una carga por edificio, sólo en `pendiente`, origen importador o manual, interés importado como `interes` con corte en la migración, crédito como `saldo_inicial`, dos tablas de origen | Ver D5 | Grupo 6 |
| **E10 · Alcance del interés y candado** | Todas las cuentas de unidad del edificio, bloqueadas en un solo pedido ordenado al emitir; las de persona quedan fuera hasta el 4d. Consecuencia técnica, no elección aparte: anular y repetir bloquean las cuentas alcanzadas (D0) | Sólo las cuentas de la emisión (una unidad sin expensa ese mes dejaría de generar interés) | Tareas 5.1 y 5.4 |
| **E11 · Período migrado con sólo interés** | Se rechaza la carga, nombrando `interes_acumulado`, cuando un período de una unidad suma capital 0 y trae interés: `ck_obligacion_importes` (`0023:82-83`) no admite una obligación sin capital. **Excluye una entrada plausible del Excel** (una unidad que pagó el capital de julio y debe sólo su interés); quien firma acepta esa limitación para el contrato del 5. Con E16 por defecto, una fila de sólo interés **sí** entra si su período tiene otra fila con capital. El 4c nunca suma ese interés a otro período por su cuenta | Que el 5 lo sume a otro período (cambia su período y con él R20); una obligación ficticia con capital simbólico; reabrir el esquema con préstamo D-115.3 | Tarea 6.1 y contrato del 5 |
| **E12 · Sin auditoría ni permiso propios** | D9 | Auditar dentro del 4c (doble auditoría cuando el 5 audite la confirmación) | Grupo 6 y 7 |
| **E13 · "Mes entero" de una obligación migrada y al cambiar de forma** (PR-03, PR-10; ratificación de la decisión de Juani del 30/10/2026, no elección abierta) | Con meses calendario (E3.2) ya no hay anclaje que elegir: el mes de cada día es fijo. Una obligación migrada nunca cobra días anteriores a la migración: su primer día a cobrar es el siguiente a la migración (R09). Al cambiar de forma entre cortes no queda hueco ni doble cobro, porque todo corte termina en un fin de mes. Vence 10/08, migra 15/10, mes entero 3%, $80.000: el corte 31/10 cobra octubre (tramo 16/10-31/10), $2.400,00, y el corte 30/11 cobra noviembre (01/11-30/11), $2.400,00, haya o no interés importado. Si esa fracción de octubre se cobra o no es E18 | Las alternativas de anclaje del intento 2 (en el vencimiento original o en lo cubierto, por bloques de 30 días) quedan descartadas por la decisión de Juani | No aplica |
| **E14 · Qué significa la situación "a una fecha"** (PR-04) | Fecha de clasificación sobre el libro actual (D6): sirve a 8, 10a y 10b, que preguntan por hoy. No ofrece historia | Historia efectiva: reconstruir el libro a esa fecha (movimientos con fecha valor y registro hasta ese día, imputaciones de esos créditos, anulaciones registradas hasta ese día) | Agrega un filtro temporal a la foto y a `calcular_estado`, con sus propios escenarios (fecha valor contra fecha de registro, anulación posterior) y sus mutantes; probablemente una tarea más en el grupo 7. La pide recién un certificado o reporte histórico (R21), que no está en el 4c |
| **E15 · Saldo anterior del replay** (PR-05) | Separar: el replay devuelve los mismos intereses registrados (estables, leídos del libro) y un saldo anterior **recalculado** al repetir, como el 4b (RB4B-05). El 7, que guarda la liquidación, es quien conserva la foto | Persistir la foto: tabla nueva de sólo agregar `saldo_anterior_de_emision(emision_id, cuenta_id, importe)` escrita al emitir y leída por el replay | Una cuarta tabla en `0034` con su protección y mutantes (tarea 2.1), escritura y lectura en 5.1 y 5.3, y la ficha del 7 deja de guardarla |
| **E16 · Varias filas del Excel en un mismo período** (PR-07, PR-11) | El 4c recibe filas (fila, período, vencimiento, componente, importe, interés) y las agrupa por unidad y período en una obligación (D5); mismo período con vencimientos distintos se rechaza. Cada fila queda ligada a lo que formó (qué obligación, interés importado o crédito), **no** a cuánto aportó: el aporte por fila se pierde al agrupar, en esta opción igual que en la alternativa. El replay compara la **firma del pedido** guardada en la carga (D5), así detecta un pedido distinto con iguales sumas ($85.000/$20.000 frente a $84.000/$21.000) | (a) El 5 agrupa y pasa un renglón por período con `filas` (varios números): el libro tampoco sabe cuánto aportó cada fila, el replay sólo ve lo agrupado (un cambio entre filas del 5 pasa como replay salvo que el 5 lo controle), y E11 vuelve a rechazar toda fila de sólo interés. (b) Guardar el aporte de cada fila (componente, importe e interés) en `origen_de_saldo_inicial` y reconstruir el pedido por SQL para el replay: el libro sí sabe cuánto aportó cada fila, a costa de dos columnas con CHECK, una consulta de reconstrucción y sus mutantes, y no cubre filas en cero ni el modo | (a) contrato de D5, tareas 6.1, 6.2 y 6.4 y el escenario "Dos conceptos del mismo período"; (b) cambia D5 (`origen_de_saldo_inicial`, sin `firma_del_pedido`), la 2.1 (CHECK nuevos) y la 6.4 (replay por reconstrucción) |
| **E17 · Cobertura del interés por intervalos** (PR-12) | Lo cubierto de una obligación es la **unión de los intervalos** de los tramos de sus intereses que cuentan (D2), no el máximo de sus `hasta`. Si se contra-asienta un interés anterior y uno posterior sigue contando, el corte siguiente cobra el hueco además de sus días nuevos, todo con la configuración vigente a ese corte (E4). Septiembre $100.000 vence 10/09, 3% proporcional: el corte 30/09 registra $2.000,00 (11/09-30/09), el 31/10 $3.100,00 (01/10-31/10); se contra-asienta sólo el primero; el corte 30/11 registra $5.000,00 en dos tramos, 11/09-30/09 y 01/11-30/11 | (a) Máximo de los `hasta` (plan del intento 2): el hueco 11/09-30/09 no se cobra nunca ($2.000,00 perdidos en el ejemplo), contra lo que promete PA-2. (b) Restringir las correcciones de interés al último interés que cuenta de cada obligación (cambia `correcciones.py:185-194`, que hoy admite cualquier interés no corregido de una emisión vigente): conserva el máximo, pero el administrador no puede contra-asentar un interés mal calculado si ya hay otro después, y toca un caso de uso del 4b que nadie pidió tocar | (a) D2, D3 vuelven al máximo; se borra el escenario "Un hueco anterior se recupera" y PA-2 dice que el hueco se pierde. (b) agrega una regla y su test a `correcciones.py` (frontera CRITICAL del 4b), y PA-2 dice qué intereses se pueden corregir |
| **E18 · La fracción del mes de la migración con "mes entero"** (consecuencia de E3.2 sobre un saldo inicial, duda real de plata) | Se cobra: una obligación migrada el 15/10 cobra en el corte 31/10 un mes entero por 16/10-31/10 ($2.400,00 sobre $80.000 al 3%). Es la regla de Juani (una fracción de mes cuenta como mes) y R09 ("R03 corre desde la fecha de migración"). **Riesgo de doble cobro**: si el interés que trae el Excel ya cobró octubre entero (un sistema con mes entero que cobra el mes al pasar el vencimiento del 10/10), octubre se cobra dos veces. Mitigación propuesta: el 5 muestra en su comparación, por unidad, que el primer interés del sistema cubre el mes de la migración, y P58 se amplía a Alberto: "¿el interés acumulado de tu Excel incluye el mes en curso?" | (a) No cobrar el mes de la migración: el primer mes cobrado es el siguiente. Si el Excel cortó el interés en el mes anterior, se pierde hasta un mes de interés por obligación. (b) Cobrar el mes de la migración sólo sin interés importado en ese período: depende de un dato que el Excel no trae (hasta qué fecha llega su interés) | (a) cambia D2 (inicio natural de una migrada con mes entero: el día 1 del mes siguiente) y los escenarios "Mes entero después de migrar" (corte 31/10 sin interés, $2.400,00 recién el 30/11); (b) agrega un dato al contrato del 5 y una rama al dominio |
| **E19 · Días de un corte sin importe** (consecuencia de E1, E4 y E17 encontrada en este intento) | Un corte que da $0,00 (tasa 0, base 0 o redondeo a cero) no registra nada y sus días quedan sin cubrir: los cobra el primer corte que registre, con su configuración (E4). Con tasa 0 en septiembre y 3% desde el 01/10, la obligación de $100.000 vencida el 10/09 cobra en el corte 31/10 51 días al 3%, $5.100,00. Ventaja: los centavos de una base chica no se pierden. **Consecuencia**: una tasa 0 difiere, no perdona; un edificio que pasa de 0% a 3% cobra al 3% los días que corrieron con 0%. Perdonar es condonación (R29, propuesta) | Días exentos: un día no se cobra si la versión vigente al fin de **su** mes tenía tasa 0. Exige leer la historia de versiones de `configuracion_versionada` (hoy `configuracion_vigente` devuelve una) y pasarla al dominio | Agrega una lectura de versiones a `complejos.aplicacion`, un parámetro al dominio, escenarios y mutantes en 4.2 y 5.2; vuelve al planner |

## Risks / Trade-offs

- **[Cambio de contrato del 4b]** `registrar_emision` empieza a escribir interés y a exigir configuración
  → la semilla `sembrar` suma una versión con tasa 0 para los tres edificios del mundo (tarea 2.2), y cada
  test del 4b que cambie de resultado se revisa uno por uno (tarea 5.5, con el inventario de los ocho
  archivos); ninguno se "arregla" cambiando su expectativa sin explicar por qué.
- **[Candado más ancho]** Bloquear todas las cuentas de unidad del edificio al emitir serializa la
  emisión con los pagos de cualquier unidad → aceptable: emitir es una vez por mes; el orden único evita
  interbloqueos (E2 del 4b). La espera no está medida: es una expectativa, no un dato. Test de
  concurrencia con un pago en otra unidad.
- **[Anulación más ancha]** Anular bloquea también las cuentas que sólo recibieron interés (D0) →
  mismo orden único, mismo análisis.
- **[Interés corrido un mes]** Con E1, después de anular y re-emitir, el interés de ese corte aparece en
  la emisión siguiente, con la configuración de ese corte → documentado en R17 al cerrar; el 7 lo
  muestra.
- **[Corrección retroactiva]** Un contra-asiento de un pago deja sin cobrar el interés de los tramos ya
  registrados (el libro no recalcula) → límite; lo compensa un cargo del 7 o del 8 cuando exista.
- **[Huecos recuperados con otra configuración]** Con E17, un hueco viejo se cobra con la tasa y la forma
  del corte que lo recupera (E4), y con E19 también los días de un corte con tasa 0 → visible en el detalle
  por tramo (cada tramo guarda su versión); el 7 y el 11 lo muestran.
- **[Mes de la migración con "mes entero"]** Posible doble cobro si el interés importado ya incluye ese
  mes → E18, con su mitigación en el 5 y la pregunta a Alberto.
- **[Doble vencimiento]** Con modalidad `doble`, el 4c usa el vencimiento de la obligación y no aplica
  recargo → supuesto atado a P59 y R26.
- **[Saldo inicial cargado de menos]** Después de confirmar no hay forma de sumar deuda (R08 sin débito
  libre) → PA-1: el 4c **no** cumple la corrección posconfirmación de R09, y el 5 no se habilita hasta
  decidirla.
- **[Mutantes sobre la carrera]** El test de RF-01 de hoy pasa con el mutante (D-138) → la aserción nueva
  mira la sentencia, no la carrera.
- **[Mutantes de aislamiento tapados]** Una defensa puede esconder otra (PR-06, L-034) → cada mutante
  declara qué apaga y dónde espera el rojo; los ensayos con una conexión sin RLS afirman su precondición.
- **[Tests estructurales]** Versión de alembic, tablas protegidas, dueño de tablas, planes de `EXPLAIN`
  → tarea 2.1 y suite completa al cierre, tarea 8.1 (L-064).

## Migration Plan

1. `0034` crea tres tablas vacías; `roles despues` las transfiere y verifica. No toca datos existentes.
2. Despliegue: no hay emisiones ni cargas reales todavía (el 5 y el 7 no existen), así que no hay
   intereses que migrar.
3. Bajada: `0034` baja sólo con las tres tablas vacías y después de devolver la propiedad, como `0023`;
   con datos, migración hacia adelante.

## Open Questions

- **PA-1 · Saldo inicial cargado de menos después de confirmar.** R09 dice "se corrige con un ajuste con
  motivo (R08)", pero R08 no admite débito libre y una obligación de saldo inicial no es un movimiento que
  se pueda contra-asentar para subir su capital. No cambia el código del 4c, pero el 4c **no** declara
  cumplida esa parte de R09: queda como decisión **bloqueante del 5** (anotada en su ficha al cerrar).
- **PA-2 · Contra-asentar un interés.** Con E1 y E17, los días de un interés contra-asentado se vuelven
  a cobrar en el corte siguiente, aunque haya intereses posteriores que siguen contando, con la
  configuración de ese corte. Si el administrador quería perdonarlo, tiene que usar condonación (R29,
  propuesta). No cambia el 4c; se informa al 8 y al 10b.
- **PA-3 · Vecinos de P58 y P59.** Si Alberto corta el interés en otra fecha o usa doble vencimiento con
  interés diario, cambian E2/E3 antes del piloto (parámetros y lógica, no esquema). P58 suma la pregunta
  de E18: si el interés acumulado de su Excel incluye el mes en curso al migrar.
