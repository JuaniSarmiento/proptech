# preliquidacion Specification

## Purpose
Muestra, antes de emitir y sin escribir nada, lo que va a pagar cada unidad en un período: el reparto de
los gastos aprobados por grupo, el fondo de reserva, los cargos particulares y el interés por mora, con la
huella que la emisión exige para emitir exactamente lo revisado (HU-A4, R01, R03, R07, R13, R14, R15, R16,
R22, R40, D-157).

## Requirements

### Requirement: Lo de cada unidad, al centavo

La preliquidación de un período SHALL repartir, por grupo de reparto y según su método, los gastos
`aprobado` del edificio cuyo período de imputación es el período, netos de las notas de crédito cargadas
en ese período, separados en ordinario y extraordinario; SHALL calcular el fondo de reserva sobre la
ordinaria prorrateada de cada unidad (sin cargos ni intereses) con el porcentaje de la configuración
vigente el primer día del período; SHALL sumar los cargos particulares `aprobado` del período como líneas
propias y el interés por mora a cobrar. Cada reparto MUST sumar exacto su total (mayor resto, R07).

#### Scenario: La base de los ejemplos

- **WHEN** se pide la preliquidación de noviembre de 2026 de "Torre Ficticia" con los gastos, la nota de
  crédito y los cargos de la base
- **THEN** `1A` paga $43.350,00, `1B` $48.350,00, `2A` $62.375,00 y `2B` $37.425,00, y el total es
  $191.500,00

#### Scenario: Mayor resto

- **WHEN** el único gasto es ordinario de Generales por $333,33 con fondo 0%
- **THEN** `1A` y `1B` pagan $100,00, `2A` $83,33 y `2B` $50,00

#### Scenario: Grupo parcial

- **WHEN** el único gasto es del grupo Ascensor
- **THEN** `1A` y `1B` quedan en $0,00 y sin obligación

#### Scenario: Lo que no entra

- **WHEN** hay gastos en borrador, sin IA o en revisión, gastos aprobados de otro período o de otro
  edificio y cargos particulares en borrador
- **THEN** ninguno cambia lo que paga ninguna unidad

#### Scenario: Fondo sin cargos

- **WHEN** `1B` tiene una multa de $5.000,00 y el fondo es 5%
- **THEN** el fondo de `1B` es el 5% de su ordinaria prorrateada, igual al de `1A`

### Requirement: El interés es el mismo que se va a emitir

El interés de cada unidad en la preliquidación SHALL calcularse con la misma función y las mismas
lecturas que usa la emisión del libro, y MUST ser igual, al centavo, al que registra la emisión del mismo
período si nada cambió en el medio.

#### Scenario: Deuda vencida de septiembre

- **WHEN** `1A` debe una ordinaria de septiembre de $100.000,00 vencida el 10/09/2026, con 3% mensual
  proporcional y gracia 0, y se preliquida octubre
- **THEN** `1A` muestra $2.000,00 de interés, igual al que registra la emisión de octubre

### Requirement: Sin efectos y con huella

Pedir la preliquidación MUST NOT escribir en ninguna tabla. SHALL devolver una huella que no cambia si
nada cambió y cambia si cambia cualquier cosa que la compone.

#### Scenario: Nada escrito

- **WHEN** se pide la preliquidación
- **THEN** el conteo de filas de todas las tablas es el mismo antes y después

#### Scenario: La huella cambia con un gasto aprobado

- **WHEN** se aprueba un gasto del período después de pedirla
- **THEN** la huella nueva es distinta

### Requirement: Los períodos van en orden

Un período SHALL poder preliquidarse sólo si es el primero del edificio (no hay emisiones sin anular) o si
el anterior tiene una emisión sin anular. Un período con una emisión sin anular MUST rechazarse.

#### Scenario: Un período salteado

- **WHEN** octubre está emitido y se pide diciembre
- **THEN** la respuesta es 409 con `periodo_anterior_sin_emitir`

#### Scenario: Un período ya emitido

- **WHEN** octubre está emitido y se pide octubre
- **THEN** la respuesta es 409 con `periodo_emitido`

#### Scenario: Un período anulado se vuelve a preliquidar

- **WHEN** la emisión de octubre se anuló
- **THEN** octubre se preliquida
