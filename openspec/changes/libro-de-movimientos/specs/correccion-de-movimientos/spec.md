# Spec Delta

## Purpose

Corrige un error del libro sin editar ni borrar nada (R08, HU-A9): un movimiento nuevo con motivo,
responsable y referencia a lo que corrige, que deja los dos visibles y el saldo correcto.

## ADDED Requirements

### Requirement: Contra-asiento de un movimiento

Corregir un movimiento con un contra-asiento SHALL agregar un movimiento de corrección que lo referencia,
con el mismo importe y el sentido contrario. Desde ese momento ni el original ni la corrección MUST
contar en el estado de la cuenta, y los dos MUST seguir en el libro. Un movimiento MUST poder corregirse
a lo sumo una vez, y una corrección no se corrige.

#### Scenario: Corregir un pago registrado de más

- **WHEN** una cuenta debía $50.000, se registró un pago de $50.000 que no existió y se corrige con
  contra-asiento
- **THEN** la cuenta vuelve a deber $50.000, el pago y la corrección siguen en el libro y la corrección
  referencia al pago

#### Scenario: Corregir dos veces el mismo movimiento

- **WHEN** se corrige un movimiento que ya tiene una corrección, con otro `operacion_id`
- **THEN** se rechaza con un conflicto y el libro no cambia

#### Scenario: Corregir una corrección

- **WHEN** se pide el contra-asiento de un movimiento de corrección
- **THEN** se rechaza con un conflicto

#### Scenario: Las imputaciones de otros créditos no se rehacen

- **WHEN** un pago A cubrió agosto, un pago B cubrió septiembre y se corrige el pago A
- **THEN** agosto vuelve a deber lo que cubría A y septiembre sigue cubierto por B

### Requirement: Crédito de corrección por un importe

Corregir con un crédito de corrección SHALL agregar un crédito por el importe indicado, que referencia la
obligación a la que corresponde el error y se imputa con el orden de R04, como un pago (D-086).

#### Scenario: Un cargo cobrado de más

- **WHEN** la obligación de octubre incluyó $5.000 de un cargo que no correspondía y se registra un
  crédito de corrección de $5.000 que la referencia
- **THEN** la deuda de la cuenta baja $5.000 con el orden de R04 y el crédito queda en el libro con su
  motivo

#### Scenario: Importe que no es positivo

- **WHEN** se pide un crédito de corrección de $0,00
- **THEN** se rechaza nombrando el campo `importe`

### Requirement: Toda corrección lleva motivo y responsable

Una corrección SHALL guardar el motivo, la persona que la registró y su fecha. Una corrección con el
motivo vacío o en blanco MUST rechazarse sin escribir nada.

#### Scenario: Corrección sin motivo

- **WHEN** se pide una corrección con el motivo "   "
- **THEN** se rechaza nombrando el campo `motivo` y el libro no cambia

### Requirement: Sólo super admin y administrador principal corrigen

La corrección por la API SHALL estar permitida sólo a super admin y a administrador principal. Una
corrección sobre un movimiento u obligación de un edificio fuera del alcance del usuario MUST responder
404, igual que uno inexistente; dentro del alcance y sin el permiso, 403.

#### Scenario: Administrador por edificio

- **WHEN** un administrador por edificio pide una corrección en su edificio
- **THEN** la respuesta es 403 con el permiso faltante `corregir_movimiento` y el libro no cambia

#### Scenario: Movimiento de otro edificio

- **WHEN** un administrador principal pide corregir un movimiento con el id de un movimiento de otra
  administración
- **THEN** la respuesta es 404, igual que para un id que no existe

#### Scenario: Super admin corrige

- **WHEN** el super admin pide un contra-asiento válido
- **THEN** la respuesta es 201 con el id del movimiento de corrección

### Requirement: La ruta de corrección declara su contrato de error

La ruta de corrección SHALL declarar en el OpenAPI de la app sus respuestas 401, 403, 404, 409 y 422, con
los formatos que la API ya usa, y MUST responder sólo con esas formas. Un error MUST nombrar el campo,
nunca repetir el valor recibido.

#### Scenario: El OpenAPI declara las cinco respuestas

- **WHEN** se genera el OpenAPI de la app
- **THEN** la ruta de corrección declara 201, 401, 403, 404, 409 y 422, cada una con su esquema

#### Scenario: Sin identidad

- **WHEN** se llama a la ruta de corrección sin identidad
- **THEN** la respuesta es 401 y no se consulta el libro

#### Scenario: Cuerpo con un campo de más

- **WHEN** el cuerpo trae un campo que la ruta no conoce
- **THEN** la respuesta es 422 nombrando ese campo, y no repite su valor

#### Scenario: Importe con decimales de más

- **WHEN** el importe llega como "10.005"
- **THEN** la respuesta es 422 nombrando `importe`, y no repite "10.005"

#### Scenario: La misma corrección dos veces

- **WHEN** se manda dos veces la misma corrección con el mismo `operacion_id`
- **THEN** las dos respuestas son 201 con el mismo id y el libro tiene una sola corrección

#### Scenario: El mismo `operacion_id` con otro motivo

- **WHEN** se reusa un `operacion_id` con un motivo distinto
- **THEN** la respuesta es 409 nombrando `operacion_id`
