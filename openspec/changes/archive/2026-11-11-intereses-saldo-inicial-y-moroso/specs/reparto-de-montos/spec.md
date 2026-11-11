# Spec Delta

## MODIFIED Requirements

### Requirement: Un monto suelto se redondea medio hacia arriba

Redondear un valor decimal al centavo SHALL usar medio hacia arriba, alejándose del cero en los
negativos, como `REDONDEAR` de Excel (D-109.1, D-113). Es una operación distinta del reparto: el
reparto MUST NOT usarla para sus partes. Un `float` MUST rechazarse. Un valor cuyo redondeo no entra en
la precisión de trabajo MUST rechazarse con el error de monto inválido, nunca con un error aritmético
crudo (RB-6).

#### Scenario: El medio sube

- **WHEN** se redondean 0.125, 0.124999 y -0.125
- **THEN** dan $0,13, $0,12 y -$0,13

#### Scenario: Float rechazado

- **WHEN** se intenta redondear el `float` `0.125`
- **THEN** falla con el error de monto inválido

#### Scenario: Valor enorme rechazado como monto inválido

- **WHEN** se intenta redondear `Decimal("1e30")`, `Decimal("-1e30")` o `Decimal("1e40")`
- **THEN** cada uno falla con el error de monto inválido y no con `decimal.InvalidOperation`
