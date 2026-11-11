# situacion-de-cobranza Specification

## Purpose
Dice, para una cuenta de unidad o para todo un edificio y a una fecha, cuánto hay vencido, cuántas
liquidaciones vencidas con capital tiene, si está bajo el umbral de saldos chicos, si es sólo deuda de
intereses y si es moroso crítico (R20, R30, D-109.4, D-143), siempre derivado del libro y nunca guardado.

## Requirements

### Requirement: Una liquidación está vencida desde que corre su interés

Una obligación vigente SHALL contar como vencida a una fecha cuando esa fecha es posterior a su
vencimiento más los días de gracia de la configuración vigente a esa fecha (D-143, D-081). Una obligación
de una emisión anulada MUST NOT contar.

#### Scenario: Dentro de la gracia

- **WHEN** el edificio tiene 5 días de gracia y una obligación vence el 10/09/2026 sin pagar
- **THEN** al 15/09/2026 no está vencida y al 16/09/2026 sí

#### Scenario: Emisión anulada

- **WHEN** la única obligación impaga de una cuenta es de una emisión anulada
- **THEN** la cuenta no tiene nada vencido

### Requirement: El total vencido suma todo lo impago de las liquidaciones vencidas

El total vencido de una cuenta SHALL ser la suma de los residuales de capital y de interés de sus
obligaciones vencidas a la fecha, calculados desde las imputaciones, sin restar el crédito a favor (R05,
D-143). El interés cuenta en el período de la obligación que lo generó.

#### Scenario: Interés en su período

- **WHEN** una cuenta debe agosto ($80.000 de capital y $4.000 de interés) y septiembre ($85.000), los dos
  vencidos
- **THEN** su total vencido es $169.000 y tiene dos liquidaciones vencidas, no tres

### Requirement: El umbral de saldos chicos se compara con el total vencido de la unidad

Una cuenta con total vencido mayor que cero y menor que el umbral de R30 vigente a la fecha SHALL quedar
"bajo el umbral": MUST NOT contar como vencida para R20 ni como deuda de intereses. Un total vencido igual
o mayor al umbral MUST seguir el camino normal (R30, D-109.3; "$500 o más" ya decidido en D-143, E6 lo
ratifica).

#### Scenario: Saldo chico

- **WHEN** el umbral es $500 y una cuenta tiene $300 vencidos en dos períodos
- **THEN** queda bajo el umbral y no es moroso crítico

#### Scenario: Dos saldos chicos que juntos pasan el umbral

- **WHEN** el umbral es $500 y una cuenta tiene $300 vencidos de agosto y $250 de septiembre
- **THEN** no queda bajo el umbral y es moroso crítico

#### Scenario: Justo en el umbral

- **WHEN** el umbral es $500 y una cuenta tiene exactamente $500 vencidos en dos períodos
- **THEN** no queda bajo el umbral y es moroso crítico

#### Scenario: El umbral no frena el interés

- **WHEN** el umbral es $500, una cuenta debe $300 de septiembre vencido y el 7 registra la emisión de
  octubre al 3%
- **THEN** la emisión registra el interés de esos $300, aunque la cuenta esté bajo el umbral

### Requirement: Moroso crítico con dos o más liquidaciones vencidas con capital

Una cuenta que no está bajo el umbral SHALL ser moroso crítico cuando tiene dos o más obligaciones vencidas
con residual de capital mayor que cero. Una obligación vencida con sólo interés impago MUST NOT contar
como liquidación vencida, aunque la cuenta tenga otra con capital (R20, D-058, D-109.4; elección E7, no
deducción de D-143; E8). No es por monto.

#### Scenario: Una sola vencida

- **WHEN** una cuenta tiene sólo septiembre vencido con $85.000 impagos
- **THEN** no es moroso crítico

#### Scenario: Dos vencidas con saldo

- **WHEN** una cuenta tiene agosto y septiembre vencidos con capital impago
- **THEN** es moroso crítico

#### Scenario: Pago parcial que no cancela ninguna

- **WHEN** una cuenta con agosto y septiembre vencidos paga una parte de agosto
- **THEN** sigue siendo moroso crítico

#### Scenario: Un saldo grande y uno chico

- **WHEN** el umbral es $500 y una cuenta debe $500 de agosto y $20 de septiembre, los dos vencidos
- **THEN** es moroso crítico (D-143)

#### Scenario: Un período con sólo interés no cuenta

- **WHEN** una cuenta pagó todo el capital de agosto, le queda su interés de $4.000 impago, y debe
  septiembre vencido
- **THEN** tiene una sola liquidación vencida y no es moroso crítico

#### Scenario: Deshacer un pago vuelve a marcar

- **WHEN** una cuenta con agosto y septiembre vencidos había pagado agosto entero, y ese pago se
  contra-asienta (R08; la reversión de R18 la construye el 8)
- **THEN** vuelve a ser moroso crítico

### Requirement: Deuda de intereses

Una cuenta que no está bajo el umbral y cuyo total vencido es sólo interés SHALL marcarse como "deuda de
intereses" y MUST NOT ser moroso crítico. La deuda sigue existiendo y su monto no cambia (D-109.4).

#### Scenario: Sólo intereses

- **WHEN** una cuenta pagó todo el capital de agosto y septiembre y le quedan $4.000 de interés vencido
- **THEN** es deuda de intereses, no es moroso crítico y su total vencido es $4.000

### Requirement: El saldo inicial cuenta como liquidaciones vencidas

La deuda cargada como saldo inicial SHALL contar igual que la emitida: con detalle por período, cada
obligación vencida con capital cuenta como una liquidación; un total único cuenta como una sola (D-080).

#### Scenario: Migrada con dos períodos

- **WHEN** U1 migró con agosto y septiembre impagos
- **THEN** es moroso crítico

#### Scenario: Migrada con total único

- **WHEN** U2 migró con un total único de $50.000 impago y vencido
- **THEN** tiene una sola liquidación vencida y no es moroso crítico

### Requirement: La fecha de la situación clasifica, no reconstruye historia

La situación de cobranza SHALL calcularse sobre el libro tal como está al leer: todos los movimientos,
imputaciones y anulaciones registrados, cualquiera sea su fecha valor. La fecha que pide el llamador MUST
usarse sólo para decidir qué obligaciones están vencidas y qué versión de configuración rige (gracia y
umbral); MUST NOT reconstruir la deuda de una fecha pasada (E14).

#### Scenario: Un pago posterior cuenta aunque la fecha sea anterior

- **WHEN** una cuenta debía agosto y septiembre vencidos al 30/09/2026, pagó los dos el 20/10/2026, y el
  llamador pide su situación con fecha 30/09/2026
- **THEN** su total vencido es $0 y no es moroso crítico, porque el libro ya tiene los pagos

### Requirement: La situación se pide por cuenta o por edificio

La situación de cobranza SHALL calcularse para una cuenta de unidad o para todas las cuentas de unidad de
un edificio, dentro del tenant de la sesión. Sin versión de configuración vigente a la fecha pedida MUST
rechazarse con conflicto en `configuracion`; un edificio que la sesión no ve, con no encontrado. Las
cuentas de persona MUST quedar fuera (4d).

#### Scenario: Listado del edificio

- **WHEN** el 10a pide la situación del edificio al 31/10/2026
- **THEN** recibe una entrada por cada cuenta de unidad del edificio, con su total vencido, sus
  liquidaciones vencidas con capital, si está bajo el umbral, si es deuda de intereses y si es moroso
  crítico

#### Scenario: Edificio de otra administración

- **WHEN** la administración B pide la situación de un edificio de la administración A
- **THEN** se rechaza con no encontrado

#### Scenario: Sin configuración

- **WHEN** el edificio no tiene versión de configuración vigente a la fecha pedida
- **THEN** se rechaza con conflicto en `configuracion`
