# Spec Delta

## Purpose

El administrador confirma o rechaza los pagos informados. Confirmar imputa con R04 a la fecha de la
transferencia y corrige el interés que una emisión cobró de más; rechazar no toca el libro (R11, R05, R19,
D-082, D-084, D-085, E6, E7).

## ADDED Requirements

### Requirement: Confirmar imputa con la fecha de la transferencia

`POST .../pagos/{id}/confirmacion` SHALL registrar por cada parte un crédito `pago` con `fecha_valor` igual a
la fecha de la transferencia, imputado con R04 primero a la deuda que existía ese día y después al resto;
el excedente queda como crédito a favor (R05). "La deuda que existía ese día" es la de las emisiones con
período hasta esa fecha (D-166). Deja el evento `confirmado`, guarda el CBU de origen si se
conoce y audita, todo en una transacción. Requiere `confirmar_pago_informado`.

#### Scenario: Confirmado tarde, sin interés por la demora

- **WHEN** `1A` debe $100.000 vencidos el 10/09, transfiere el 30/09 y el administrador confirma el 20/10
- **THEN** el interés de `1A` sólo corre del 11/09 al 30/09, igual que si se hubiera confirmado el 30/09

#### Scenario: Excedente

- **WHEN** el pago supera la deuda de la unidad
- **THEN** la deuda queda en cero y el resto es crédito a favor aplicable

#### Scenario: Reparto

- **WHEN** se confirma un pago repartido entre `1A` y `2B`
- **THEN** cada parte se imputa en su unidad con R04

### Requirement: Confirmar dos veces no duplica

Una segunda confirmación del mismo pago (doble clic, dos pestañas, en carrera) SHALL responder 200 con el
mismo resultado y MUST NOT registrar otro movimiento ni otro evento. Confirmar un pago rechazado o
revertido da 409 `motivo` `estado`.

#### Scenario: Doble clic

- **WHEN** dos confirmaciones del mismo pago llegan juntas
- **THEN** hay un solo crédito `pago` por parte y un solo evento `confirmado`

### Requirement: Rechazar con motivo no toca el libro

`POST .../pagos/{id}/rechazo` SHALL exigir un motivo de 3 a 500 caracteres, dejar el evento `rechazado` y no
escribir en el libro; el vecino ve el motivo. Rechazar uno confirmado da 409.

#### Scenario: Rechazo

- **WHEN** se rechaza con "el monto no coincide con el comprobante"
- **THEN** la deuda no cambia y el vecino ve el pago `rechazado` con ese motivo

### Requirement: El ajuste del interés cobrado de más

Al confirmar, cada interés que cuenta, de una emisión con período posterior a la fecha de la transferencia (D-166), SHALL
recalcularse sobre sus mismos tramos (con su tasa, forma y gracia guardadas) con la base que habría tenido
con el pago; si lo registrado supera lo recalculado, la diferencia se registra antes que el pago como
`ajuste_de_interes` con destino ese interés, `enlazado_a` ese interés y enlazado al pago. Lo que no entra
en su interés vuelve en la respuesta como `ajuste_sin_destino`.

#### Scenario: Pago confirmado después de una emisión que cobró interés

- **WHEN** `1A` debe $100.000 de octubre, transfiere $100.000 el 05/11, la emisión de diciembre le cobra noviembre
  entero sobre los $100.000 y el pago se confirma después
- **THEN** se registra un ajuste de $2.447,50 (lo cobrado, $3.000, menos lo que corresponde con el pago imputado el
  05/11, $552,50), y la cuenta queda igual al centavo que la de una unidad que confirmó el mismo pago el 05/11

#### Scenario: El ajuste sigue a su interés

- **WHEN** después se anula la emisión de diciembre
- **THEN** el ajuste deja de contar con el interés, sin contra-movimiento (D-085)

#### Scenario: Sin emisión de por medio

- **WHEN** el pago se confirma antes de la emisión siguiente
- **THEN** no hay ajuste
