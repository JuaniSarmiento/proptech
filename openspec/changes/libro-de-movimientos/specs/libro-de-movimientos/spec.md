# Spec Delta

## Purpose

Guarda la deuda de cada cuenta en un libro que sólo crece (R08): cuentas, emisiones, obligaciones,
movimientos e imputaciones, de donde se calcula el estado de cada cuenta sin guardar nunca un saldo.

## ADDED Requirements

### Requirement: El libro sólo se agrega

Ninguna fila de `cuenta`, `emision`, `evento_de_emision`, `obligacion`, `movimiento` ni `imputacion`
SHALL poder modificarse ni borrarse, por la aplicación ni por SQL directo, con ningún rol de servicio. Un
`UPDATE`, `DELETE`, `TRUNCATE` o `INSERT ... ON CONFLICT DO UPDATE` MUST rechazarse con `42501` por privilegios para la app después de `roles despues`; como rol de arranque,
los triggers MUST rechazarlo con `P0001` y el texto de la tabla, aunque no afecte ninguna fila.

#### Scenario: Editar un movimiento por SQL directo

- **WHEN** el rol de la aplicación ejecuta `UPDATE movimiento SET importe = importe` sobre un movimiento
  existente
- **THEN** la base lo rechaza con SQLSTATE `42501` por privilegios, y el
  movimiento sigue igual

#### Scenario: Borrar sin filas también se rechaza

- **WHEN** el rol de la aplicación ejecuta `DELETE FROM imputacion WHERE false`
- **THEN** la base lo rechaza con SQLSTATE `42501` por privilegios

#### Scenario: Vaciar una tabla con hijas

- **WHEN** el rol de arranque ejecuta `TRUNCATE cuenta CASCADE` dentro de un savepoint
- **THEN** la base lo rechaza con el texto de bloqueo de `cuenta` y ninguna tabla hija se vacía

#### Scenario: Upsert sobre el libro

- **WHEN** el rol de la aplicación ejecuta `INSERT INTO emision ... ON CONFLICT DO UPDATE` aunque no haya conflicto
- **THEN** la base lo rechaza con `42501` y no se inserta nada

### Requirement: El libro no guarda saldos

Ninguna tabla del libro SHALL tener una columna de saldo, de residual ni una marca de "pagada". El
residual de una obligación MUST calcularse siempre como su importe más sus débitos menos sus
imputaciones vigentes (R05).

#### Scenario: Catálogo sin columnas de saldo

- **WHEN** el ensayo del consumidor invoca la operación y se listan las columnas de las seis tablas del libro
- **THEN** ninguna se llama ni contiene `saldo`, `residual` ni `pagad`

### Requirement: Cada administración ve sólo su libro

Las seis tablas del libro SHALL estar aisladas por administración con RLS forzada, y toda referencia
entre ellas, y hacia `complejo`, `unidad` y `persona`, MUST incluir la administración, para que ninguna
fila apunte a una de otra administración.

#### Scenario: Otra administración no ve la cuenta

- **WHEN** la administración B consulta `cuenta` con su tenant fijado
- **THEN** no ve ninguna cuenta de la administración A

#### Scenario: Una obligación no puede apuntar a una cuenta ajena

- **WHEN** se inserta una obligación de la administración A que referencia una cuenta de la
  administración B
- **THEN** la base la rechaza por la clave foránea compuesta

### Requirement: Una cuenta es de una unidad o de una persona

Una cuenta SHALL pertenecer a exactamente una unidad o a exactamente una persona de un edificio, nunca a
las dos ni a ninguna. Una unidad MUST tener a lo sumo una cuenta, y una persona a lo sumo una por
edificio.

#### Scenario: Cuenta sin dueño

- **WHEN** el ensayo del consumidor invoca la operación y se inserta una cuenta sin unidad ni persona
- **THEN** la base la rechaza

#### Scenario: Cuenta con los dos dueños

- **WHEN** el ensayo del consumidor invoca la operación y se inserta una cuenta con unidad y con persona
- **THEN** la base la rechaza

#### Scenario: Pedir dos veces la cuenta de una unidad

- **WHEN** el ensayo del consumidor invoca la operación y se pide la cuenta de la unidad "1A" dos veces, también desde dos transacciones simultáneas
- **THEN** existe una sola cuenta para esa unidad y las dos llamadas devuelven el mismo id

### Requirement: Una emisión por edificio y período, salvo anulada

Una emisión SHALL registrar un edificio, un período (el primer día de un mes) y sus obligaciones, una por
cuenta. Un período MUST tener a lo sumo una emisión no anulada: una nueva emisión del mismo período MUST
rechazarse salvo que todas las anteriores estén anuladas.

#### Scenario: Segunda emisión del mismo período

- **WHEN** el ensayo del consumidor invoca la operación y el edificio ya tiene la emisión de octubre de 2026 sin anular y se registra otra de octubre
- **THEN** se rechaza con un conflicto y el libro no cambia

#### Scenario: Emitir de nuevo después de anular

- **WHEN** el ensayo del consumidor invoca la operación y la emisión de octubre está anulada y se registra otra de octubre
- **THEN** se registra como el segundo intento de ese período

#### Scenario: Dos emisiones simultáneas del mismo período

- **WHEN** el ensayo del consumidor invoca la operación y dos transacciones registran a la vez una emisión de octubre del mismo edificio
- **THEN** una se registra y la otra se rechaza con un conflicto, contra PostgreSQL real

#### Scenario: Período que no es un mes

- **WHEN** el ensayo del consumidor invoca la operación y se registra una emisión con período 15/10/2026
- **THEN** se rechaza nombrando el campo `periodo`

### Requirement: Registrar dos veces lo mismo no duplica

Toda escritura del libro SHALL llevar una clave que la identifica (el id de la emisión, el tipo de evento
de una emisión, el `operacion_id` de un crédito o una corrección). Repetirla con los mismos datos MUST
devolver lo ya registrado sin escribir nada; repetirla con datos distintos MUST rechazarse con un
conflicto.

#### Scenario: La misma emisión dos veces

- **WHEN** el ensayo del consumidor invoca la operación y se registra dos veces la emisión con el mismo id y las mismas obligaciones
- **THEN** existe una sola emisión con sus obligaciones, y la segunda llamada no falla

#### Scenario: El mismo id con otras obligaciones

- **WHEN** el ensayo del consumidor invoca la operación y se registra una emisión con un id ya usado y un importe distinto en una obligación
- **THEN** se rechaza con un conflicto y el libro no cambia

#### Scenario: El mismo crédito dos veces

- **WHEN** el ensayo del consumidor invoca la operación y se registra dos veces un crédito con el mismo `operacion_id` y el mismo importe
- **THEN** existe un solo movimiento y un solo juego de imputaciones

### Requirement: Una obligación desglosa su capital

Cada obligación SHALL guardar, en importes separados y no negativos, la ordinaria (con los cargos
particulares), el fondo de reserva y la extraordinaria de una cuenta en un período, con su vencimiento
(R13, R15). Una obligación con los tres importes en cero MUST rechazarse.

#### Scenario: Obligación con importe negativo

- **WHEN** el ensayo del consumidor invoca la operación y se registra una obligación con ordinaria de -$1,00
- **THEN** la base la rechaza

#### Scenario: Capital desglosado

- **WHEN** el ensayo del consumidor invoca la operación y se registra una obligación de $40.000 de ordinaria, $2.000 de fondo y $10.000 de
  extraordinaria
- **THEN** el estado de la cuenta muestra los tres componentes por separado y $52.000 de deuda

### Requirement: Anular una emisión la saca del saldo sin borrar nada

Registrar la anulación de una emisión SHALL exigir motivo y responsable y agregar un evento, sin tocar
ninguna otra fila. Desde ese momento, el estado de cada cuenta MUST excluir las obligaciones de esa
emisión, los movimientos que generó y los ajustes de interés enlazados a su interés (R17, D-073, D-079,
D-085).

#### Scenario: Anular deja la deuda como antes de emitir

- **WHEN** el ensayo del consumidor invoca la operación y una cuenta debía $50.000, se registra la emisión de noviembre con $40.000 y después se anula
- **THEN** la cuenta vuelve a deber $50.000, y la emisión, su obligación y el evento de anulación siguen
  en el libro

#### Scenario: Anular sin motivo

- **WHEN** el ensayo del consumidor invoca la operación y se registra la anulación de una emisión con el motivo en blanco
- **THEN** se rechaza nombrando el campo `motivo` y la emisión sigue vigente

#### Scenario: Anular dos veces

- **WHEN** el ensayo del consumidor invoca la operación y se registra dos veces la anulación de la misma emisión
- **THEN** la segunda llamada se rechaza con `Conflicto("emision_id")` según R17, incluso con el mismo motivo, y existe un solo evento de anulación

#### Scenario: El ajuste que compensaba el interés anulado

- **WHEN** el ensayo del consumidor invoca la operación y la emisión de noviembre registró $1.000 de interés, un ajuste de interés de $1.000 lo
  compensa y la emisión se anula
- **THEN** ni el interés ni el ajuste cuentan, y la cuenta no queda debiendo ni con crédito de más

### Requirement: El estado de una cuenta se calcula desde el libro

El estado de una cuenta SHALL informar, por obligación vigente y por componente, cuánto se debe, y
aparte el crédito a favor. Ningún residual MUST ser negativo. La deuda total MUST ser la suma de los
residuales y no repetir una obligación vieja en una nueva (R06).

#### Scenario: Saldo anterior sin débito nuevo

- **WHEN** el ensayo del consumidor invoca la operación y una cuenta debe $30.000 de marzo y se registra la emisión de abril con $35.000
- **THEN** el saldo anterior de la emisión de abril es $30.000, la deuda total es $65.000 y no existe
  ningún movimiento nuevo por los $30.000 de marzo

#### Scenario: Pagar marzo lo saca del saldo anterior

- **WHEN** el ensayo del consumidor invoca la operación y después de pagar los $30.000 de marzo se registra la emisión de mayo
- **THEN** el saldo anterior de la emisión de mayo es $35.000, sólo abril

#### Scenario: Deuda de un edificio

- **WHEN** el ensayo del consumidor invoca la operación y se pide la deuda del edificio
- **THEN** devuelve una fila por cuenta con su deuda y su crédito a favor, que coinciden con el estado
  de cada cuenta pedido por separado

#### Scenario: Los triggers frenan aun con permiso de escritura

- **WHEN** el rol de arranque ejecuta por separado `UPDATE movimiento`, `DELETE FROM imputacion WHERE false` y un `INSERT ... ON CONFLICT DO UPDATE` en `emision`, dentro de savepoints
- **THEN** cada sentencia falla con `P0001` y el texto de bloqueo de su tabla; ninguna fila cambia

### Requirement: El vocabulario de movimientos permite ampliaciones por INSERT

`movimiento` SHALL referenciar por FK el par `(tipo, sentido)` de `tipo_de_movimiento`. El vocabulario MUST incluir los tipos actuales, `reversion_de_pago` débito, `reimputacion` débito y crédito y `traslado` débito y crédito. `enlazado_a` MUST permitir otra cuenta de la misma administración y rechazar otra administración. Las restricciones de destino de los tipos conocidos MUST conservarse mediante CHECK acotados a esos tipos, sin cerrar el conjunto de tipos futuros.

#### Scenario: Tipos anticipados válidos

- **WHEN** el migrador siembra el vocabulario y el ensayo inserta un movimiento válido de cada par previsto, incluidos interés con corte, condonación, ajuste enlazado, bonificación, baja de deuda, saldo inicial con operación, reversión de pago, reimputaciones y traslados
- **THEN** todos entran con su sentido y destino válidos; un par no sembrado se rechaza por FK

#### Scenario: Enlace entre cuentas de la administración

- **WHEN** el ensayo registra una reimputación crédito en una cuenta y enlaza el pago original de otra cuenta de la misma administración
- **THEN** la FK lo admite; si el pago pertenece a otra administración lo rechaza

### Requirement: Las referencias compuestas no admiten huecos por NULL

El esquema SHALL exigir `sentido_del_movimiento NOT NULL` y que `corrige_a` y `tipo_corregido` estén ambos presentes o ambos ausentes. Las FK MUST atar cuenta, administración, edificio y período donde se repiten, incluidos los movimientos y sus obligaciones y emisiones.

#### Scenario: Los casos de NULL y cuenta ajena se rechazan

- **WHEN** el ensayo intenta imputar un débito con sentido NULL, corregir con tipo corregido NULL, registrar un débito con obligación de otra cuenta o un movimiento con cuenta inexistente
- **THEN** la base rechaza cada INSERT por la restricción correspondiente, sin escribir filas

#### Scenario: Edificio y período coherentes

- **WHEN** el ensayo intenta una obligación con período distinto al de su emisión o un movimiento con edificio distinto al de su cuenta
- **THEN** la FK compuesta rechaza cada INSERT

### Requirement: Las operaciones resuelven recursos dentro del tenant

`anular_emision` y `registrar_credito` SHALL resolver sus ids bajo el tenant de la sesión y devolver `NoEncontrado` para un recurso inexistente o de otra administración, sin dejar escrituras.

#### Scenario: Anular una emisión inexistente

- **WHEN** el llamador del 7 pide anular una emisión inexistente
- **THEN** recibe `NoEncontrado` y no se agrega ningún evento

#### Scenario: Anular una emisión de otra administración

- **WHEN** el llamador del 7 pide anular una emisión de otra administración
- **THEN** recibe el mismo `NoEncontrado` y no se agrega ningún evento

#### Scenario: Registrar crédito en cuenta inexistente

- **WHEN** el llamador del 8 pide registrar un crédito en una cuenta inexistente
- **THEN** recibe `NoEncontrado` y no se agrega movimiento ni imputación

#### Scenario: Registrar crédito en cuenta de otra administración

- **WHEN** el llamador del 8 pide registrar un crédito en una cuenta de otra administración
- **THEN** recibe el mismo `NoEncontrado` y no se agrega movimiento ni imputación

### Requirement: Las lecturas usan una foto consistente y el saldo anterior no es saldo neto

Cada lectura SHALL obtener las filas en una sola sentencia SQL con snapshot READ COMMITTED. La deuda del edificio MUST acceder al libro mediante sus cuentas. `saldo_anterior` MUST ser la deuda residual actual excluyendo la emisión pedida, nunca negativa por crédito a favor; incluye imputaciones pendientes hechas al emitir. El 7 MUST guardar ese valor al emitir para reproducir el documento sin recalcularlo.

#### Scenario: Saldo anterior con crédito a favor

- **WHEN** el llamador del 7 emite $40.000 para una cuenta sin deuda previa y con $10.000 a favor
- **THEN** el saldo anterior es $0, la nueva obligación queda en $30.000 y el 7 guarda ese saldo anterior

#### Scenario: Lectura durante una confirmación

- **WHEN** el lector pide el estado mientras otra conexión confirma un crédito con imputaciones
- **THEN** obtiene la foto anterior o la posterior completa, nunca imputaciones sin su movimiento

#### Scenario: Plan del edificio con datos de varios edificios

- **WHEN** el ensayo consulta la deuda de un edificio sobre datos de varios edificios y obtiene EXPLAIN ANALYZE
- **THEN** el plan no contiene Seq Scan sobre `obligacion`, `movimiento` ni `imputacion`
