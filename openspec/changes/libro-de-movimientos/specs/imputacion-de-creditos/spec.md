# Spec Delta

## Purpose

Decide a qué deuda va cada peso de un crédito (pago, corrección, condonación, ajuste, bonificación, baja)
y en qué orden (R04, R05, R13, D-086), y garantiza que dos créditos de la misma cuenta no se imputan
sobre la misma foto de la deuda.

## ADDED Requirements

### Requirement: El período más antiguo primero, y dentro del período por componente

Un crédito que va con el orden de R04 SHALL imputarse primero a la obligación del período más antiguo y,
dentro de cada período, al interés, después a la ordinaria, después al fondo de reserva y por último a
la extraordinaria. El lugar del fondo de reserva MUST tratarse como provisorio hasta la respuesta de
Alberto (P60).

#### Scenario: El ejemplo de R04

- **WHEN** una cuenta debe agosto ($80.000 de ordinaria y $4.000 de interés) y septiembre ($85.000 de
  ordinaria) y registra un pago de $100.000
- **THEN** se imputan $4.000 al interés de agosto, $80.000 a la ordinaria de agosto y $16.000 a la
  ordinaria de septiembre, que queda con $69.000

#### Scenario: Un pago parcial cubre la ordinaria antes que la extraordinaria

- **WHEN** una obligación tiene $40.000 de ordinaria y $10.000 de extraordinaria y entra un pago de
  $45.000
- **THEN** la ordinaria queda en cero y la extraordinaria con $5.000

#### Scenario: El fondo de reserva, entre la ordinaria y la extraordinaria

- **WHEN** una obligación tiene $40.000 de ordinaria, $2.000 de fondo y $10.000 de extraordinaria y
  entra un pago de $41.000
- **THEN** la ordinaria queda en cero, el fondo con $1.000 y la extraordinaria con $10.000

#### Scenario: Un pago que cubre exacto un período

- **WHEN** agosto debe $84.000 en total y entra un pago de $84.000
- **THEN** agosto queda en cero, septiembre no cambia y no queda crédito a favor

### Requirement: Lo que sobra queda como crédito a favor

Lo que un crédito no puede imputar porque no queda deuda SHALL quedar como crédito a favor de la cuenta,
sin crear ningún movimiento nuevo, y MUST imputarse con el mismo orden cuando la cuenta tenga una
obligación nueva (R05).

#### Scenario: Pago mayor que la deuda

- **WHEN** una cuenta debe $50.000 y entra un pago de $60.000
- **THEN** la deuda queda en cero y la cuenta tiene $10.000 de crédito a favor

#### Scenario: El crédito a favor se imputa en la emisión siguiente

- **WHEN** la cuenta con $10.000 a favor recibe la emisión de diciembre por $40.000
- **THEN** la obligación de diciembre queda con $30.000 y el crédito a favor en cero

#### Scenario: Un pago imputado a una emisión que se anula vuelve como crédito

- **WHEN** un pago de $40.000 se imputó a la emisión de noviembre y esa emisión se anula
- **THEN** la cuenta tiene $40.000 de crédito a favor, y al registrar la nueva emisión de noviembre se
  imputa a ella

### Requirement: Los créditos que no son pagos van a su destino fijo

La condonación SHALL imputarse sólo al interés que condona; el ajuste de interés, sólo al interés que
compensa; la bonificación, sólo a la ordinaria del período bonificado; la corrección, la reimputación y
la baja de deuda, con el orden de R04 (D-086). Lo que un destino fijo no puede absorber MUST quedar como
crédito a favor.

#### Scenario: Una condonación baja sólo el interés condonado

- **WHEN** agosto debe $4.000 de interés y $80.000 de ordinaria y se registra una condonación de $4.000
  sobre el interés de agosto
- **THEN** el interés de agosto queda en cero y la ordinaria sigue en $80.000

#### Scenario: Un ajuste de interés baja sólo el interés que compensa

- **WHEN** se registra un ajuste de $500 sobre el interés de septiembre, con deuda también en agosto
- **THEN** sólo el interés de septiembre baja $500

#### Scenario: Una bonificación va a la ordinaria de su período

- **WHEN** se registra una bonificación de $2.000 sobre la ordinaria de octubre, con agosto impago
- **THEN** sólo la ordinaria de octubre baja $2.000

#### Scenario: Destino fijo sin un componente que absorba

- **WHEN** se registra una condonación de $4.000 sobre una obligación sin interés
- **THEN** la deuda no cambia y la cuenta tiene $4.000 de crédito a favor

### Requirement: Ninguna obligación queda con residual negativo

Ninguna imputación SHALL hacer que el residual de un componente de una obligación quede por debajo de
cero.

#### Scenario: Dos créditos que juntos superan la deuda

- **WHEN** una obligación debe $10.000 y entran dos pagos de $8.000, uno después del otro
- **THEN** la obligación queda en cero y la cuenta tiene $6.000 de crédito a favor

### Requirement: Dos créditos de la misma cuenta nunca usan la misma foto

Toda escritura que impute sobre una cuenta SHALL serializarse con las demás escrituras de esa cuenta,
para que la segunda vea lo que imputó la primera (R04). Escrituras de cuentas distintas MUST poder correr
a la vez.

#### Scenario: Dos pagos simultáneos

- **WHEN** una cuenta debe $100.000 y dos transacciones registran a la vez un pago de $60.000 cada una,
  contra PostgreSQL real
- **THEN** la deuda queda en cero, la cuenta tiene $20.000 de crédito a favor y la suma de las
  imputaciones es $100.000

#### Scenario: Una emisión y un pago a la vez

- **WHEN** una emisión que toca diez cuentas y un pago de una de ellas corren a la vez
- **THEN** las dos terminan sin interbloqueo y el pago se imputa sobre el estado que dejó la que
  terminó primero

#### Scenario: Cuentas distintas no se esperan

- **WHEN** dos transacciones registran a la vez un pago en dos cuentas distintas y una de ellas se
  demora antes de confirmar
- **THEN** la otra confirma sin esperarla
