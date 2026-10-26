# Spec Delta

## Purpose

Corrige un error del libro sin editar ni borrar nada (R08, HU-A9): un movimiento nuevo con motivo,
responsable y referencia a lo que corrige, que deja los dos visibles y el saldo correcto.

## ADDED Requirements

### Requirement: Contra-asiento de un movimiento

Corregir SHALL agregar un movimiento del mismo importe y sentido contrario que referencia al original. El par MUST dejar de contar y seguir visible. Cada movimiento admite a lo sumo un contra-asiento; los créditos de corrección también, los débitos de corrección no. Las cadenas MUST evaluarse topológicamente desde el extremo sin corrección entrante hacia el original, sin ordenar por now ni UUID, sin excluir de nuevo un movimiento ya excluido por otra posterior. E6 queda a validar (P42, A-4).

#### Scenario: Corregir un pago registrado de más

- **WHEN** el ensayo del consumidor invoca la operación y una cuenta debía $50.000, se registró un pago de $50.000 que no existió y se corrige con
  contra-asiento
- **THEN** la cuenta vuelve a deber $50.000, el pago y la corrección siguen en el libro y la corrección
  referencia al pago

#### Scenario: Corregir dos veces el mismo movimiento

- **WHEN** el ensayo del consumidor invoca la operación y se corrige un movimiento que ya tiene una corrección, con otro `operacion_id`
- **THEN** se rechaza con un conflicto y el libro no cambia

#### Scenario: Corregir una corrección

- **WHEN** el AP pide el contra-asiento de un crédito de corrección de $50.000 registrado por error en vez de $5.000
- **THEN** registra el débito por $50.000 que lo referencia, los dos dejan de contar y el AP puede registrar el crédito correcto de $5.000 con otra operación; una segunda corrección del mismo crédito da `Conflicto("movimiento_id")`

#### Scenario: Las imputaciones de otros créditos no se rehacen

- **WHEN** el ensayo del consumidor invoca la operación y un pago A cubrió agosto, un pago B cubrió septiembre y se corrige el pago A
- **THEN** agosto vuelve a deber lo que cubría A y septiembre sigue cubierto por B

### Requirement: Crédito de corrección por un importe

Corregir con un crédito de corrección SHALL agregar un crédito por el importe indicado, que referencia la
obligación a la que corresponde el error o crédito particular de R14 y se imputa con el orden de R04, como un pago (D-086).

#### Scenario: Un cargo cobrado de más

- **WHEN** el AP registra un crédito de corrección de $5.000 que referencia octubre con $40.000 y un cargo indebido, mientras septiembre debe $10.000
- **THEN** septiembre queda con $5.000 y octubre sigue en $40.000 por R04; el crédito referencia octubre y conserva su motivo

#### Scenario: Importe que no es positivo

- **WHEN** el ensayo del consumidor invoca la operación y se pide un crédito de corrección de $0,00
- **THEN** se rechaza nombrando el campo `importe`

### Requirement: Toda corrección lleva motivo y responsable

Una corrección SHALL guardar el motivo, la persona que la registró y su fecha. Una corrección con el
motivo vacío o en blanco MUST rechazarse sin escribir nada. El motivo normalizado MUST tener de 1 a 500 caracteres; responsable y fecha de registro MUST ser observables en el movimiento.

#### Scenario: Corrección sin motivo

- **WHEN** el ensayo del consumidor invoca la operación y se pide una corrección con el motivo "   "
- **THEN** se rechaza nombrando el campo `motivo` y el libro no cambia

### Requirement: Sólo super admin y administrador principal corrigen

La corrección por la API SHALL estar permitida sólo a super admin y a administrador principal. Una
corrección sobre un movimiento u obligación de un edificio fuera del alcance del usuario MUST responder
404, igual que uno inexistente; dentro del alcance y sin el permiso, 403.

#### Scenario: Administrador por edificio

- **WHEN** un administrador por edificio pide una corrección en su edificio
- **THEN** la respuesta es 403 con el permiso faltante `corregir_movimiento` y el libro no cambia

#### Scenario: Movimiento de otro edificio

- **WHEN** un administrador principal pide corregir en el edificio X un movimiento del edificio Y de la misma administración
- **THEN** la respuesta es 404, igual que para un id que no existe

#### Scenario: Super admin corrige

- **WHEN** el super admin pide un contra-asiento válido
- **THEN** la respuesta es 201 con el id del movimiento de corrección

### Requirement: La ruta de corrección declara su contrato de error

La ruta SHALL declarar 401, 403, 404, 409, 422, 500 y 503 en OpenAPI y responder con esas formas. El 500 conserva `{"error":"interno","request_id":...}`; el 503 usa `{"detail":"temporalmente no disponible"}`. La traducción SQL MUST correr en SAVEPOINT (`begin_nested`). Validación y conflictos MUST nombrar el campo sin repetir su valor. El orden MUST ser 401, 422 de cuerpo, 404 de edificio, 403 de permiso, 404 de recurso, 409/422 de dominio.

#### Scenario: El OpenAPI declara las respuestas de error

- **WHEN** el ensayo del consumidor invoca la operación y se genera el OpenAPI de la app
- **THEN** la ruta de corrección declara 201, 401, 403, 404, 409, 422, 500 y 503, cada una con su esquema

#### Scenario: Sin identidad

- **WHEN** el ensayo del consumidor invoca la operación y se llama a la ruta de corrección sin identidad
- **THEN** la respuesta es 401 y no se consulta el libro

#### Scenario: Cuerpo con un campo de más

- **WHEN** el ensayo del consumidor invoca la operación y el cuerpo trae un campo que la ruta no conoce
- **THEN** la respuesta es 422 nombrando ese campo, y no repite su valor

#### Scenario: Importe con decimales de más

- **WHEN** el ensayo del consumidor invoca la operación y el importe llega como "10.005"
- **THEN** la respuesta es 422 nombrando `importe`, y no repite "10.005"

#### Scenario: La misma corrección dos veces

- **WHEN** el AP manda dos veces el mismo contra-asiento con el mismo `operacion_id`, aun con otro request_id o responsable
- **THEN** las dos respuestas son 201 con el mismo id y el libro tiene una sola corrección

#### Scenario: El mismo `operacion_id` con otro motivo

- **WHEN** el ensayo del consumidor invoca la operación y se reusa un `operacion_id` con un motivo distinto
- **THEN** la respuesta es 409 nombrando `operacion_id`

#### Scenario: Contra-asiento de un interés cubierto

- **WHEN** el AP contra-asienta un interés de $4.000 ya cubierto por un pago
- **THEN** interés y contra-asiento dejan de contar y $4.000 vuelven al pago como crédito a favor

#### Scenario: Corregir el crédito que contra-asentó un interés

- **WHEN** el AP contra-asienta el crédito C1 que había contra-asentado un interés I de $4.000
- **THEN** C1 y su contra-asiento débito C2 dejan de contar y vuelve a contar I por $4.000; cada movimiento tiene a lo sumo un contra-asiento

#### Scenario: Contra-asiento de un débito de corrección

- **WHEN** el AP pide contra-asentar un débito de corrección
- **THEN** recibe `Conflicto("movimiento_id")` sin escribir

#### Scenario: Contra-asiento sobre emisión anulada

- **WHEN** el AP pide contra-asentar un movimiento generado por una emisión anulada
- **THEN** recibe `Conflicto("movimiento_id")` y el libro no cambia

#### Scenario: Crédito sobre obligación que no cuenta

- **WHEN** el AP pide un crédito de corrección sobre una obligación de una emisión anulada
- **THEN** recibe `Conflicto("obligacion_id")` sin escribir

#### Scenario: Obligación inexistente

- **WHEN** el AP pide un crédito de corrección con `obligacion_id` inexistente
- **THEN** el caso de uso devuelve `NoEncontrado` y la API 404 sin escribir

#### Scenario: Obligación de otra administración

- **WHEN** el AP pide un crédito de corrección con `obligacion_id` de otra administración
- **THEN** el caso de uso devuelve el mismo `NoEncontrado` y la API 404 sin escribir

#### Scenario: Movimiento de otra administración

- **WHEN** el AP pide un contra-asiento de un movimiento de otra administración
- **THEN** recibe 404 igual que para un movimiento inexistente

#### Scenario: Obligación de otro edificio de la misma administración

- **WHEN** el AP pide en el edificio X un crédito de corrección sobre una obligación del edificio Y de la misma administración
- **THEN** recibe `NoEncontrado` y la API 404 sin escribir ni auditar con el edificio incorrecto

#### Scenario: Motivo de longitud inválida

- **WHEN** el AP manda un motivo vacío después de normalizarlo o de 501 caracteres
- **THEN** recibe 422 nombrando `motivo`; motivos normalizados de 1 y 500 caracteres son válidos

#### Scenario: Responsable y fecha observables

- **WHEN** el AP registra una corrección válida el 10/11/2026
- **THEN** el movimiento conserva su persona como responsable, fecha de registro y fecha valor 10/11/2026, además del motivo normalizado y la referencia

#### Scenario: Replay con otros datos de negocio

- **WHEN** el llamador reusa `operacion_id` con otra cuenta, tipo, destino, importe, forma, referencia o complejo de la ruta, o con motivo normalizado distinto
- **THEN** recibe `Conflicto("operacion_id")`, sin imputar ni auditar otra vez

#### Scenario: Replay antes de validar si ya está corregido

- **WHEN** el AP repite el mismo contra-asiento por `operacion_id` después de que quedó registrado
- **THEN** recibe el id existente antes de validar si el original ya tiene corrección; no se escriben nuevas imputaciones ni auditoría

#### Scenario: Único de corrección aunque falte el chequeo previo

- **WHEN** el ensayo elimina sólo el chequeo previo de "ya tiene corrección" y el AP corrige por segunda vez un movimiento con otra operación
- **THEN** el único de `corrige_a` produce 23505 traducido a 409 `movimiento_id`, sin absorberlo con el árbitro de `operacion_id`

#### Scenario: Error de base con transacción recuperable

- **WHEN** el ensayo provoca un 23505 conocido dentro de la corrección
- **THEN** el SAVEPOINT se revierte, se devuelve 409 con su campo y la transacción del llamador admite otra sentencia, sin 25P02

#### Scenario: Errores internos y transitorios declarados

- **WHEN** el ensayo provoca por separado 23514, 42501, 40P01 y 40001 a través de la API
- **THEN** los dos primeros producen el 500 declarado y los dos últimos el 503 declarado sin reintento automático, sin filtrar SQL ni valores del pedido

#### Scenario: Un usuario sin permiso no averigua si existe el recurso

- **WHEN** un administrador por edificio pide corregir en su edificio un id existente o inexistente
- **THEN** ambos devuelven 403 antes de consultar el recurso del libro

#### Scenario: UUID de texto y montos no positivos

- **WHEN** el AP manda UUID válidos como texto y un importe positivo de dos decimales
- **THEN** el cuerpo es válido con UUID `strict=False`; si manda cero o negativo recibe 422 nombrando `importe`

#### Scenario: Traducción de clave foránea y único desconocido

- **WHEN** el ensayo provoca por la API un 23503 y, por separado, un 23505 de constraint desconocido
- **THEN** recibe respectivamente 404 y el 500 declarado, sin revelar los valores del constraint
