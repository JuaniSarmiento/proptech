# emision-de-liquidacion Specification

## Purpose
Emite exactamente la preliquidación revisada: una obligación por unidad en el libro, en una transacción,
con todo lo usado guardado, las alertas aceptadas registradas y el vencimiento que se haya corrido (HU-A5,
R03, R06, R13, R15, R16, R17, R34, P36, D-157).

## Requirements

### Requirement: Se emite lo revisado, una vez

Emitir SHALL recibir la huella de la preliquidación revisada y rechazar la emisión si la preliquidación
recalculada bajo el candado del período tiene otra huella; SHALL rechazar cualquier control duro activo y
exigir que las alertas aceptadas sean exactamente los bloqueantes activos; MUST NOT escribir nada en un
rechazo. Un mismo período sólo SHALL tener una emisión sin anular; el mismo pedido repetido devuelve lo
mismo.

#### Scenario: Emitir la base

- **WHEN** se emite la preliquidación revisada de la base de noviembre
- **THEN** cada unidad tiene una obligación con su ordinaria (más cargos), fondo y extraordinaria, que vence el 10/11, y hay una auditoría

#### Scenario: Interés igual al preliquidado

- **WHEN** `1A` debe septiembre y se emite octubre
- **THEN** el interés registrado es el que mostró la preliquidación, $2.000

#### Scenario: Lo emitido no cambia

- **WHEN** después de emitir se renombra una categoría y se cambia el fondo
- **THEN** la liquidación leída es idéntica a la de antes

#### Scenario: Saldo anterior guardado

- **WHEN** `1A` debe octubre, se emite noviembre y después se le acredita una corrección
- **THEN** el saldo anterior guardado es el del libro al emitir y no cambia

#### Scenario: Vencimiento corrido

- **WHEN** se emite con el vencimiento corrido al 12/11 y un motivo
- **THEN** las obligaciones vencen el 12/11, queda la fecha original, quién y el motivo, y la configuración no cambia

#### Scenario: Bloqueante aceptado

- **WHEN** hay un gasto en revisión y el administrador principal lo acepta
- **THEN** se emite y queda la alerta aceptada con quién y cuándo

#### Scenario: Gasto aprobado después de emitir

- **WHEN** noviembre está emitido y se aprueba un gasto de noviembre
- **THEN** su período de imputación pasa a diciembre

#### Scenario: Reintento del mismo pedido

- **WHEN** se manda dos veces el mismo pedido
- **THEN** la segunda devuelve la misma liquidación sin escribir nada

### Requirement: Rechazos sin efectos

Cada rechazo de emitir MUST dejar la base como estaba.

#### Scenario: La preliquidación cambió

- **WHEN** se aprobó un gasto después de revisar
- **THEN** emitir con la huella vieja da 409 y no escribe nada

#### Scenario: Control duro activo

- **WHEN** la migración está pendiente, aunque se pida aceptarlo
- **THEN** emitir da 422 `control_duro` y no escribe nada

#### Scenario: Alertas aceptadas distintas

- **WHEN** se aceptan de menos, de más o una advertencia
- **THEN** emitir da 409 y no escribe nada

#### Scenario: Emitir dos veces el mismo período

- **WHEN** noviembre ya está emitido
- **THEN** otra emisión de noviembre da 409 `periodo_emitido`

#### Scenario: Dos emisiones a la vez

- **WHEN** dos pedidos de noviembre llegan juntos
- **THEN** uno emite, el otro da 409 y hay una sola obligación por unidad

#### Scenario: Gasto aprobado durante la emisión

- **WHEN** se aprueba un gasto mientras se emite
- **THEN** o la emisión falla por huella y el gasto queda en noviembre, o la emisión sale y el gasto pasa a diciembre

#### Scenario: Unidad sin nada que pagar

- **WHEN** el único gasto es del grupo Ascensor
- **THEN** sólo `2A` y `2B` reciben obligación
