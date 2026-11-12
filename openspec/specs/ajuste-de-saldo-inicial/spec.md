# ajuste-de-saldo-inicial Specification

## Purpose
Corrige un saldo inicial cargado de menos, después de confirmar, con deuda nueva y su motivo, sin editar
ni borrar nada del libro (R08, R09, D-155, E11).

## Requirements

### Requirement: El ajuste es una obligación nueva con su motivo

Ajustar SHALL crear, sobre la cuenta de una unidad de un edificio con la migración `confirmada`, una
obligación sin emisión con el importe en el componente elegido (`ordinaria`, `fondo_de_reserva` o
`extraordinaria`), período el primer día del mes de la migración y vencimiento el día del ajuste, y su
registro en `ajuste_de_saldo_inicial` con motivo (1 a 500 caracteres, no en blanco), autor y fecha. Se
audita. No MUST modificar ni borrar ningún movimiento ni obligación existente.

#### Scenario: Saldo cargado de menos

- **WHEN** la unidad `1A` se migró el 15/10/2026 con $80.000 y debía $85.000, y el 05/11/2026 el
  administrador principal ajusta $5.000 de ordinaria con el motivo "Faltó la expensa extraordinaria de
  julio"
- **THEN** la cuenta de `1A` tiene una obligación nueva de $5.000, período 01/10/2026 y vencimiento
  05/11/2026, ligada a su ajuste con ese motivo, y una fila de auditoría

#### Scenario: Unidad en cero

- **WHEN** la unidad `5E` se migró sin saldo y se ajusta $2.000
- **THEN** la cuenta de `5E` (creada si no existía) tiene una obligación de $2.000

#### Scenario: Unidad con crédito a favor

- **WHEN** la unidad `4D` tiene $3.000 a favor y se ajusta $2.000
- **THEN** el crédito se imputa a la obligación nueva y `4D` queda con $1.000 a favor

### Requirement: El ajuste genera interés desde el día siguiente

La obligación del ajuste SHALL generar interés de R03 desde el día siguiente a su vencimiento, con la
gracia y la forma vigentes, como cualquier obligación; nunca por días anteriores al ajuste.

#### Scenario: Interés del ajuste

- **WHEN** se ajustan $5.000 el 05/11/2026, al 3% proporcional, sin pagar, y se emite diciembre (corte
  30/11/2026)
- **THEN** el interés del ajuste es de 25 días, $125,00

### Requirement: El ajuste rechaza lo que no puede registrar

Ajustar MUST rechazarse sin escribir nada cuando: el edificio no está `confirmada`; el motivo está vacío o
supera 500 caracteres; el importe no es mayor que cero o tiene más de 2 decimales; el componente no es
uno de los tres; la unidad es de otro edificio o de otra administración; o falta el permiso
`ajustar_saldo_inicial` (super admin o administrador principal). Repetir el ajuste con el mismo
`operacion_id` y los mismos datos devuelve lo registrado sin escribir; con otros datos, conflicto.

#### Scenario: Edificio pendiente

- **WHEN** se ajusta una unidad de un edificio con la migración `pendiente`
- **THEN** se rechaza con conflicto en `estado_migracion`

#### Scenario: Sin motivo

- **WHEN** el motivo es "   "
- **THEN** se rechaza nombrando `motivo`

#### Scenario: Administrador del edificio

- **WHEN** un administrador por edificio intenta ajustar
- **THEN** se rechaza con 403

#### Scenario: Replay del ajuste

- **WHEN** se repite el ajuste con el mismo `operacion_id` y los mismos datos
- **THEN** devuelve el mismo ajuste y no se agrega ninguna obligación

#### Scenario: El registro del ajuste no se edita

- **WHEN** el rol de la aplicación intenta `UPDATE` o `DELETE` sobre `ajuste_de_saldo_inicial`
- **THEN** la base lo rechaza con SQLSTATE `42501`
