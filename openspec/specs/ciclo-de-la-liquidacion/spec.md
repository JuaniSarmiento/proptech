# ciclo-de-la-liquidacion Specification

## Purpose
Lleva una liquidación emitida a distribuida o anulada, con sus límites (R17, P26, D-074, D8), y corrige un
cargo cobrado de menos con una obligación nueva con motivo (R08, E11, D-157).

## Requirements

### Requirement: Distribuir, anular y corregir sin borrar nada

Una liquidación emitida SHALL poder distribuirse (por un puerto único e idempotente) o anularse con motivo
mientras no esté distribuida ni tenga emitido el período siguiente; anular MUST NOT modificar ni borrar
movimientos, obligaciones ni imputaciones. Un crédito de corrección de una emisión anulada SHALL quedar
retenido. Un cargo cobrado de menos SHALL ser una obligación nueva con motivo y vínculo a su origen.

#### Scenario: Distribuir

- **WHEN** el administrador distribuye una liquidación emitida
- **THEN** queda distribuida con origen manual, quién y cuándo, y se audita

#### Scenario: Distribuida por dos caminos

- **WHEN** el portal y el email la distribuyen uno detrás del otro
- **THEN** queda un solo evento, con el origen del primero

#### Scenario: Anular una emitida

- **WHEN** el administrador principal anula una emitida con motivo
- **THEN** queda anulada con motivo y responsable, la deuda vuelve a la de antes de emitir y ninguna fila del libro cambia

#### Scenario: Volver a emitir

- **WHEN** se anula noviembre y se emite de nuevo
- **THEN** la deuda de `1A` es octubre más la expensa nueva, una sola vez

#### Scenario: Pago imputado a una emisión anulada

- **WHEN** `1A` pagó el 05/11 y se anula noviembre
- **THEN** el pago vuelve a favor, la re-emisión lo imputa y diciembre no le cobra interés

#### Scenario: Crédito de corrección de una emisión anulada

- **WHEN** `1A` tenía una corrección de $1.000 sobre noviembre y se anula
- **THEN** el crédito queda retenido y la re-emisión no lo imputa (D8)

#### Scenario: Cargo cobrado de menos

- **WHEN** faltó cobrarle $1.500 a `1A` y se registra el 20/11
- **THEN** hay una obligación nueva con su motivo, vence el 20/11 y en diciembre genera $15 de interés

#### Scenario: El consejo y una liquidación sin distribuir

- **WHEN** noviembre está emitido y no distribuido
- **THEN** el consejo no lo ve; el contador sí; distribuida, el consejo también

#### Scenario: Anular una distribuida

- **WHEN** noviembre está distribuido
- **THEN** anularla da 409 y nada cambia

#### Scenario: Anular con el siguiente emitido

- **WHEN** octubre y noviembre están emitidos
- **THEN** anular octubre da 409; anulado noviembre, octubre se anula

#### Scenario: Anular y distribuir a la vez

- **WHEN** llegan juntos un pedido de anular y uno de distribuir
- **THEN** uno gana, el otro da 409 y queda un solo evento
