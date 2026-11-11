# Spec Delta

## Purpose

Recibe en el libro, una sola vez por edificio, la deuda y el crédito que el edificio trae al migrar (R09),
con detalle por período o como total único, sin recalcular el interés anterior y guardando de qué filas del
archivo salió cada obligación, interés importado o crédito, para que el importador (5) la cargue al confirmar.

## ADDED Requirements

### Requirement: Una sola carga de saldo inicial por edificio, mientras la migración está pendiente

Registrar el saldo inicial de un edificio SHALL aceptarse sólo si su estado de migración es `pendiente` y
el edificio no tiene ya una carga. Con el estado `confirmada` o `sin_saldos_previos`, o con otra carga
existente, MUST rechazarse con conflicto sin escribir nada (R09, D-082).

#### Scenario: Edificio sin saldos previos

- **WHEN** el 5 intenta registrar el saldo inicial de un edificio confirmado "sin saldos previos"
- **THEN** se rechaza con conflicto en `estado_migracion` y el libro no cambia

#### Scenario: Importador cerrado sin carga previa

- **WHEN** el edificio está en `confirmada`, no tiene ninguna carga, y el 5 intenta una con un
  `operacion_id` nuevo
- **THEN** se rechaza con conflicto en `estado_migracion` y el libro no cambia

#### Scenario: Segunda carga con otra operación

- **WHEN** el edificio ya tiene una carga de saldo inicial y el 5 intenta otra con otro `operacion_id`
- **THEN** se rechaza con conflicto y existe una sola carga

#### Scenario: Dos cargas simultáneas

- **WHEN** dos conexiones registran a la vez cargas distintas del mismo edificio pendiente
- **THEN** una se registra y la otra se rechaza con conflicto, contra PostgreSQL real

### Requirement: Las filas con detalle se agrupan en una obligación por período

Con detalle por período, el 5 SHALL pasar las filas del archivo tal como vienen (número de fila, período,
vencimiento, componente, importe e interés acumulado), con el concepto ya traducido a componente. La carga
MUST agrupar las filas de deuda de cada unidad por período en una sola obligación de la cuenta de la unidad,
con la suma de cada componente, sin emisión y ligada a la carga (R09, D-080, E16). Todas las filas de un
período MUST tener el mismo vencimiento.

#### Scenario: Dos períodos viejos

- **WHEN** el 5 carga para la unidad U1, con fecha de migración 15/10/2026, la fila 7 (agosto, ordinaria
  $80.000, vence 10/08/2026) y la fila 8 (septiembre, ordinaria $85.000, vence 10/09/2026)
- **THEN** la cuenta de U1 tiene dos obligaciones, de agosto y de septiembre, y debe $165.000 de capital

#### Scenario: Dos conceptos del mismo período

- **WHEN** el 5 carga para U5 la fila 12 (septiembre, ordinaria $85.000, vence 10/09/2026, $3.000 de interés
  acumulado) y la fila 13 (septiembre, extraordinaria $20.000, vence 10/09/2026, sin interés)
- **THEN** la cuenta de U5 tiene una sola obligación de septiembre con $85.000 de ordinaria y $20.000 de
  extraordinaria, un débito de interés importado de $3.000,00, y R20 la cuenta como una liquidación

#### Scenario: Mismo período con vencimientos distintos

- **WHEN** el 5 carga para U5 la fila 12 de septiembre que vence el 10/09/2026 y la fila 13 de septiembre que
  vence el 15/09/2026
- **THEN** se rechaza nombrando `vencimiento` y el libro no cambia

### Requirement: El total único genera una sola obligación que vence en la migración

Con total único, las filas de deuda de la unidad SHALL sumarse en una sola obligación con todo el capital
en ordinaria, vencimiento en la fecha de migración y período el primer día del mes de la migración (R09,
D-080).

#### Scenario: Total único

- **WHEN** el 5 carga para U2 un total único de $50.000 con fecha de migración 15/10/2026
- **THEN** la cuenta de U2 tiene una sola obligación de $50.000, período 01/10/2026 y vencimiento
  15/10/2026

### Requirement: El interés acumulado entra tal cual y no genera interés

El interés que el administrador trae acumulado SHALL entrar como un débito de interés sobre la obligación
de su período, por la suma exacta informada en sus filas, con corte en la fecha de migración, y MUST NOT
formar parte de la base de ningún interés posterior (R09, D-082, D-083, R03).

#### Scenario: Interés importado sin recalcular

- **WHEN** el 5 carga agosto de U1 con $4.000 de interés acumulado
- **THEN** la cuenta de U1 tiene un débito de interés de $4.000,00 sobre agosto con corte 15/10/2026, y
  el interés posterior se calcula sólo sobre los $80.000

#### Scenario: Total único con interés traído

- **WHEN** el 5 carga para U2 un total único de $50.000 con $2.000 de interés ya devengado
- **THEN** U2 debe $52.000 y el interés de R03 corre sólo sobre los $50.000

#### Scenario: Fila de sólo interés junto a otra con capital

- **WHEN** el 5 carga para U6 la fila 14 (septiembre, ordinaria $0, $500 de interés acumulado) y la fila 15
  (septiembre, ordinaria $10.000, sin interés), las dos con vencimiento 10/09/2026
- **THEN** U6 tiene una obligación de septiembre de $10.000 y un interés importado de $500,00 sobre ella

### Requirement: El interés de R03 corre desde la fecha de migración

Para una obligación cargada como saldo inicial, el interés de R03 SHALL correr desde el día siguiente a la
fecha de migración, aunque su vencimiento original sea anterior, y nunca por días anteriores a la
migración. Con "mes entero", el mes calendario de la migración MUST cobrarse como un mes entero por su
fracción posterior a la migración, y los siguientes como meses enteros (E3, E13, E18). Para un total único,
MUST aplicar los días de gracia desde su vencimiento, que es la fecha de migración.

#### Scenario: Primer interés después de migrar

- **WHEN** U1 migró el 15/10/2026 con agosto ($80.000) y septiembre ($85.000), al 3% proporcional, y el
  7 registra la emisión de noviembre
- **THEN** el interés con corte 31/10/2026 es de 16 días: $1.280,00 sobre agosto y $1.360,00 sobre
  septiembre

#### Scenario: Mes entero después de migrar

- **WHEN** U1 migró el 15/10/2026 con agosto ($80.000, vencido el 10/08/2026) y septiembre ($85.000), al
  3% "mes entero", y el 7 registra la emisión de noviembre
- **THEN** el interés con corte 31/10/2026 es $2.400,00 sobre agosto y $2.550,00 sobre septiembre, cada uno
  con un tramo del 16/10/2026 al 31/10/2026, y ninguno cubre días anteriores a la migración

#### Scenario: Mes entero después de migrar, con interés importado

- **WHEN** lo mismo, pero agosto trae $4.000 de interés acumulado
- **THEN** el interés con corte 31/10/2026 sobre agosto sigue siendo $2.400,00

#### Scenario: Segundo mes después de migrar

- **WHEN** en "Mes entero después de migrar" U1 sigue sin pagar y el 7 registra la emisión de diciembre
- **THEN** el interés con corte 30/11/2026 es otros $2.400,00 sobre agosto, con un tramo del 01/11/2026 al
  30/11/2026

### Requirement: El crédito inicial entra como crédito a favor

Un crédito que la unidad trae a favor SHALL entrar como un crédito de saldo inicial de la cuenta, por la
suma de sus filas de crédito (importes positivos: el 5 convierte el saldo negativo del archivo), con fecha
valor en la fecha de migración, y MUST imputarse con el orden de R04 como cualquier crédito a favor (R09,
R05).

#### Scenario: Unidad con saldo a favor

- **WHEN** el 5 carga para U3 un crédito de $3.000
- **THEN** la cuenta de U3 no debe nada y tiene $3.000 de crédito a favor aplicable

#### Scenario: Deuda y crédito en la misma unidad

- **WHEN** el 5 carga para U4 septiembre por $10.000 y un crédito de $3.000
- **THEN** el crédito se imputa a septiembre y U4 debe $7.000

### Requirement: Cada fila guarda su origen

La carga SHALL guardar su origen: `importador`, con el nombre del archivo y el número de cada fila, o
`manual`, con un motivo. Cada fila MUST quedar ligada a lo que formó: la obligación de su período (o el
crédito) si trae importe, y el interés importado de su período si trae interés, en tablas de sólo agregar
aisladas por administración y de la misma cuenta que lo referenciado (R09, trazabilidad). El libro guarda
qué filas formaron cada cosa, no cuánto aportó cada fila (E16).

#### Scenario: Origen del importador

- **WHEN** el 5 carga desde el archivo `saldos-octubre.xlsx` la fila 7, de agosto de U1
- **THEN** la obligación de agosto de U1 queda ligada a la fila 7 de `saldos-octubre.xlsx`

#### Scenario: Origen de dos conceptos del mismo período

- **WHEN** se registra la carga de "Dos conceptos del mismo período"
- **THEN** la obligación de septiembre de U5 queda ligada a las filas 12 y 13, y el interés importado sólo
  a la fila 12

#### Scenario: Carga manual sin motivo

- **WHEN** el 5 intenta una carga manual con motivo en blanco
- **THEN** se rechaza nombrando el campo `motivo` y el libro no cambia

#### Scenario: El origen no se edita

- **WHEN** el rol de la aplicación intenta `UPDATE` o `DELETE` sobre una carga o una fila de origen
- **THEN** la base lo rechaza con SQLSTATE `42501`

### Requirement: La carga rechaza fechas y capital que no puede registrar

La carga SHALL rechazarse entera, sin escribir nada y nombrando el campo, cuando: un período no es el primer
día de un mes o es posterior al mes de migración; un vencimiento es posterior a la fecha de migración; las
filas de un período tienen vencimientos distintos; la fecha de migración es posterior a hoy; o un período
suma capital 0 (E11).

#### Scenario: Vencimiento futuro

- **WHEN** el 5 carga una fila con vencimiento 20/10/2026 y fecha de migración 15/10/2026
- **THEN** se rechaza nombrando `vencimiento` y el libro no cambia

#### Scenario: Período con sólo interés

- **WHEN** el 5 carga para una unidad julio con una sola fila de capital $0 y $500 de interés acumulado
- **THEN** se rechaza nombrando `interes_acumulado` y el libro no cambia

### Requirement: La carga rechaza unidades y filas mal formadas

La carga SHALL rechazarse entera, sin escribir nada y nombrando el campo, cuando: una unidad aparece dos
veces o sin filas; una unidad mezcla filas de detalle y de total; un número de fila se repite en la carga;
o un importe es negativo o un crédito no es positivo.

#### Scenario: Unidad repetida

- **WHEN** el 5 carga dos veces la unidad U1
- **THEN** se rechaza nombrando `unidades` y el libro no cambia

#### Scenario: Fila repetida

- **WHEN** el 5 carga la fila 7 en U1 y otra vez la fila 7 en U2
- **THEN** se rechaza nombrando `fila` y el libro no cambia

### Requirement: Repetir la misma carga no duplica

Repetir la carga con el mismo `operacion_id` y el mismo pedido SHALL devolver lo ya registrado sin
escribir nada, aunque el estado de migración ya no sea `pendiente`. "El mismo pedido" MUST compararse por
la firma del pedido normalizado guardada en la carga, no por lo que quedó en el libro: el orden de
unidades y filas no cuenta, y cualquier dato distinto de una fila sí, aunque las sumas coincidan. Con otro
pedido MUST rechazarse con conflicto en `operacion_id` sin escribir nada.

#### Scenario: Replay de la carga

- **WHEN** el 5 repite la carga con el mismo `operacion_id` y las mismas filas después de confirmar
- **THEN** recibe el mismo resultado y no se agrega ninguna fila

#### Scenario: Misma operación con otros datos

- **WHEN** el 5 repite el `operacion_id` cambiando el importe de una fila
- **THEN** se rechaza con conflicto en `operacion_id`

#### Scenario: Misma operación con iguales sumas y otras filas

- **WHEN** el 5 cargó para U5 la fila 12 (septiembre, ordinaria $85.000, vence 10/09/2026, $3.000 de interés
  acumulado) y la fila 13 (septiembre, ordinaria $20.000, vence 10/09/2026, sin interés), y repite el mismo
  `operacion_id` con la fila 12 por $84.000 y la fila 13 por $21.000, con el mismo interés
- **THEN** se rechaza con conflicto en `operacion_id` y el libro no cambia, aunque la obligación de
  septiembre ($105.000 de ordinaria), el interés importado ($3.000,00) y las filas ligadas serían los mismos

#### Scenario: Mismo pedido en otro orden

- **WHEN** el 5 repite el mismo `operacion_id` con las mismas unidades y filas, en otro orden y con los
  importes escritos como `85000` en vez de `85000.00`
- **THEN** recibe el mismo resultado y no se agrega ninguna fila

### Requirement: La carga respeta el tenant y no autoriza ni audita

La carga SHALL exigir una transacción abierta y una identidad de la administración de la sesión, y MUST
rechazar con no encontrado un edificio o una unidad de otro edificio o de otra administración. Autorizar y
auditar la carga, en la misma transacción, es del llamador (5), como emitir lo es del 7.

#### Scenario: Unidad de otro edificio

- **WHEN** el 5 carga una fila de una unidad de otro edificio de la misma administración
- **THEN** se rechaza con no encontrado y el libro no cambia

#### Scenario: Otra administración no ve la carga

- **WHEN** la administración B consulta las cargas de saldo inicial con su tenant fijado
- **THEN** no ve ninguna carga de la administración A
