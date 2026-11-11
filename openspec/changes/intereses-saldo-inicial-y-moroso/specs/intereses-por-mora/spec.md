# Spec Delta

## Purpose

Hace crecer la deuda vencida con interés simple por mora (R03) al emitir cada liquidación, con su corte
al cierre del período, su detalle por tramo y la configuración del edificio que rigió, sin cobrar nunca
interés sobre interés ni dos veces el mismo día.

## ADDED Requirements

### Requirement: La emisión registra el interés de la deuda vencida

Al registrar una emisión del período P, el sistema SHALL registrar, en la misma transacción, un débito de
interés por cada obligación vigente de las cuentas de unidad del edificio que acumuló interés hasta el
corte de esa emisión: el último día del mes anterior a P (D-109.5, D-113, E2). El débito MUST referenciar
la emisión que lo registró, la obligación que lo generó y el corte.

#### Scenario: Expensa de septiembre impaga en la emisión de octubre

- **WHEN** el 7 registra la emisión de octubre de 2026 de un edificio con tasa 3% mensual, gracia 0 y
  "proporcional por día", y una cuenta debe la ordinaria de septiembre de $100.000 vencida el 10/09/2026
- **THEN** queda un débito de interés de $2.000,00 sobre la obligación de septiembre, con corte
  30/09/2026, que referencia la emisión de octubre

#### Scenario: Unidad sin obligación en la emisión nueva

- **WHEN** el 7 registra la emisión de octubre sin obligación para una unidad que debe septiembre vencido
- **THEN** esa cuenta también recibe su débito de interés con corte 30/09/2026, y queda entre las
  cuentas alcanzadas por la emisión

#### Scenario: Emisión anulada no genera interés sobre sus obligaciones

- **WHEN** la emisión de septiembre está anulada y el 7 registra la de octubre
- **THEN** ninguna obligación de la emisión anulada recibe interés

### Requirement: El interés es simple y sólo sobre el capital impago

El interés de cada día SHALL calcularse sobre el capital impago de la obligación ese día (ordinaria, fondo
de reserva y extraordinaria, más sus débitos de capital que cuentan, menos sus imputaciones de capital que
cuentan con fecha efectiva anterior a ese día), nunca sobre un interés ya registrado ni importado (R03,
art. 770 del CCyC). Una tasa 0 o una base 0 MUST NOT registrar ningún débito.

#### Scenario: Nunca interés sobre interés

- **WHEN** la cuenta no paga nada y el 7 registra la emisión de noviembre después de la de octubre que
  registró $2.000,00 de interés sobre los $100.000 de septiembre
- **THEN** el interés con corte 31/10/2026 es $3.100,00 (31 días sobre $100.000), no sobre $102.000

#### Scenario: Pago parcial reduce la base

- **WHEN** la cuenta pagó $40.000 con fecha valor 20/09/2026 sobre la obligación de $100.000 vencida el
  10/09/2026, y el 7 registra la emisión de octubre
- **THEN** el interés con corte 30/09/2026 es $1.600,00: 10 días sobre $100.000 y 10 días sobre $60.000

#### Scenario: Tasa cero

- **WHEN** la configuración vigente al corte tiene tasa 0,00% y hay deuda vencida
- **THEN** la emisión no registra ningún débito de interés

### Requirement: Los días de gracia deciden si corre, no desde cuándo

Una parte del capital pagada con fecha valor dentro de los días de gracia SHALL no generar interés. Si el
capital sigue impago después de la gracia, el interés MUST correr desde el día siguiente al vencimiento,
no desde el fin de la gracia (R03, D-081). Mientras el corte esté dentro de la gracia, MUST NOT registrarse
interés y los días quedan para el corte siguiente.

#### Scenario: Pago dentro de la gracia

- **WHEN** el edificio tiene 5 días de gracia y la obligación de $100.000 vencida el 10/09/2026 se pagó
  entera con fecha valor 15/09/2026
- **THEN** la emisión de octubre no registra interés sobre ella

#### Scenario: Pago un día después de la gracia

- **WHEN** el edificio tiene 5 días de gracia y la misma obligación se pagó entera con fecha valor
  16/09/2026
- **THEN** la emisión de octubre registra $600,00 de interés: 6 días desde el vencimiento

#### Scenario: Corte dentro de la gracia

- **WHEN** el edificio tiene 5 días de gracia, la obligación de $100.000 vence el 28/09/2026 y sigue
  impaga, y el 7 registra las emisiones de octubre y de noviembre
- **THEN** la de octubre no registra interés sobre ella y la de noviembre registra 33 días desde el
  vencimiento, $3.300,00

### Requirement: Cada corte cobra los días que ningún interés que cuenta cubre

Al registrar una emisión, el sistema SHALL cobrar en su corte, por cada obligación, los días desde su
inicio natural (el día siguiente al vencimiento o a la migración) hasta el corte que no estén cubiertos.
Lo cubierto MUST ser la unión de los tramos de sus intereses **que cuentan**, no el último día cubierto; un
interés que no cuenta no cubre nada (E1, E17). Todos los días a cobrar usan la configuración del corte
(E4).

#### Scenario: Lo cubierto por un interés anterior no se vuelve a cobrar

- **WHEN** la obligación de $100.000 vencida el 10/09/2026 tiene un interés que cuenta con corte
  30/09/2026 y el 7 registra noviembre
- **THEN** el interés con corte 31/10/2026 empieza el 01/10/2026

#### Scenario: Un hueco anterior se recupera aunque haya un interés posterior

- **WHEN** la obligación de septiembre de $100.000 vence el 10/09/2026, al 3% proporcional y sin pagos; la
  emisión de octubre registró $2.000,00 de interés (11/09 a 30/09) y la de noviembre $3.100,00 (01/10 a
  31/10); el administrador contra-asienta sólo el interés registrado en octubre; y el 7 registra la
  emisión de diciembre
- **THEN** el interés con corte 30/11/2026 es $5.000,00, con un tramo del 11/09 al 30/09/2026 (20 días) y
  otro del 01/11 al 30/11/2026 (30 días), y el interés de noviembre sigue contando

#### Scenario: Los días de un corte con tasa cero se cobran después

- **WHEN** el edificio tiene 0% desde el 01/01/2026 y 3% proporcional desde el 01/10/2026, y la obligación
  de $100.000 vencida el 10/09/2026 sigue impaga al registrar las emisiones de octubre y de noviembre
- **THEN** la de octubre (corte 30/09/2026) no registra interés y la de noviembre registra 51 días al 3%,
  del 11/09 al 31/10/2026, $5.100,00 (E19)

### Requirement: Forma de cálculo proporcional por día o mes entero

Con "proporcional por día", cada día a cobrar SHALL cobrar la tasa mensual / 30 sobre el capital impago
de ese día (E3). Con "mes entero", cada mes calendario con algún día a cobrar MUST cobrar la tasa mensual
completa una vez, sobre el capital impago de su primer día a cobrar, aunque sea una fracción del mes, en
un tramo que nunca pasa el corte (E3, E13; decisión de Juani del 30/10/2026: meses calendario).

#### Scenario: Un día de atraso con mes entero

- **WHEN** el edificio usa "mes entero" al 3% y una obligación de $100.000 vencida el 29/09/2026 sigue
  impaga al registrar la emisión de octubre
- **THEN** el interés con corte 30/09/2026 es $3.000,00, con un tramo del 30/09/2026 al 30/09/2026

#### Scenario: El mes siguiente con mes entero

- **WHEN** esa obligación sigue impaga y el 7 registra la emisión de noviembre
- **THEN** el interés con corte 31/10/2026 es otros $3.000,00, con un tramo del 01/10/2026 al 31/10/2026

#### Scenario: Corte dentro de la gracia con mes entero

- **WHEN** el edificio usa "mes entero" al 3% con 5 días de gracia, la obligación de $100.000 vence el
  28/09/2026 y sigue impaga, y el 7 registra las emisiones de octubre y de noviembre
- **THEN** la de octubre no registra interés sobre ella y la de noviembre registra $6.000,00, con un tramo
  del 29/09 al 30/09/2026 y otro del 01/10 al 31/10/2026

#### Scenario: Pago a mitad de mes con mes entero

- **WHEN** el edificio usa "mes entero" al 3% con gracia 0, la obligación de $100.000 vence el 10/09/2026, la cuenta
  paga $40.000 con fecha valor 20/09/2026 sobre ella y el 7 registra octubre y noviembre
- **THEN** el interés con corte 30/09/2026 es $3.000,00 (base del 11/09, $100.000) y el de corte
  31/10/2026 es $1.800,00 (base del 01/10, $60.000)

#### Scenario: Febrero proporcional

- **WHEN** una obligación de $100.000 vencida el 10/02/2028 sigue impaga y el 7 registra la emisión de
  marzo de 2028, al 3% proporcional
- **THEN** el interés con corte 29/02/2028 cuenta 19 días: $1.900,00

#### Scenario: De proporcional a mes entero

- **WHEN** el edificio usa 3% proporcional desde el 01/01/2026 y 3% "mes entero" desde el 01/10/2026, la
  obligación de $100.000 vencida el 10/09/2026 sigue impaga y el 7 registra octubre y noviembre
- **THEN** el interés con corte 30/09/2026 es $2.000,00 (20 días proporcional) y el de corte 31/10/2026 es
  $3.000,00, un solo mes, con un tramo del 01/10/2026 al 31/10/2026, sin días sin cobrar en el medio y
  no $6.000,00

#### Scenario: De mes entero a proporcional

- **WHEN** el edificio usa 3% "mes entero" desde el 01/01/2026 y 3% proporcional desde el 01/10/2026, la
  obligación de $100.000 vencida el 29/09/2026 sigue impaga y el 7 registra octubre y noviembre
- **THEN** el interés con corte 30/09/2026 es $3.000,00 (septiembre, tramo del 30/09 al 30/09/2026) y el de
  corte 31/10/2026 es $3.100,00 (31 días proporcional, del 01/10 al 31/10/2026), sin volver a cobrar el
  30/09

### Requirement: El interés se corta al cierre del período

Un débito de interés SHALL cobrar sólo días hasta su corte, con cualquiera de las dos formas. Los días
posteriores MUST cobrarse en la emisión siguiente, aunque la emisión se registre después del corte
(D-109.5).

#### Scenario: Emitir a mitad de mes no adelanta interés

- **WHEN** el 7 registra la emisión de octubre el 15/10/2026 y la cuenta debe septiembre impago, al 3%
  proporcional
- **THEN** el interés de esa emisión llega hasta el 30/09/2026, y los días del 1 al 31 de octubre los
  registra la emisión de noviembre

### Requirement: Cada corte usa la configuración vigente al corte

El interés de un corte SHALL calcularse con la versión de configuración del edificio vigente en la fecha de
corte (tasa, gracia y forma de cálculo). Un interés ya registrado MUST NOT cambiar cuando cambia la
configuración.

#### Scenario: Cambio de tasa entre períodos

- **WHEN** el edificio tiene 3% desde el 01/01/2026 y 6% desde el 01/10/2026, la cuenta no paga
  septiembre ($100.000, vence 10/09/2026) y el 7 registra octubre y noviembre
- **THEN** el interés con corte 30/09/2026 es $2.000,00 al 3%, el de corte 31/10/2026 es $6.200,00 al 6%,
  y el primero no cambia

### Requirement: Sin configuración vigente al corte la emisión se rechaza

Si hay una obligación que cuenta vencida antes del corte y no hay versión vigente al corte (ninguna, o sólo
versiones que empiezan después), la emisión SHALL rechazarse con conflicto en `configuracion` sin escribir
nada. Un edificio que la sesión no ve MUST rechazarse con no encontrado, nunca con conflicto de
configuración.

#### Scenario: Sin configuración vigente

- **WHEN** el edificio no tiene ninguna versión de configuración y una cuenta debe septiembre vencido
- **THEN** la emisión de octubre se rechaza con conflicto en `configuracion` y el libro no cambia

#### Scenario: Sólo una versión futura

- **WHEN** la única versión de configuración del edificio rige desde el 01/10/2026 y una cuenta debe
  septiembre vencido
- **THEN** la emisión de octubre, con corte 30/09/2026, se rechaza con conflicto en `configuracion` y el
  libro no cambia

#### Scenario: Edificio de otra administración

- **WHEN** la administración B registra una emisión para un edificio de la administración A
- **THEN** se rechaza con no encontrado y el libro no cambia

### Requirement: El interés se redondea una sola vez al registrarse

El importe de un débito de interés SHALL ser la suma exacta de sus tramos, redondeada al centavo una sola
vez y medio hacia arriba (R07, D-113). Un importe que redondea a $0,00 MUST NOT registrarse.

#### Scenario: Medio centavo hacia arriba

- **WHEN** una obligación de $62,50 vence el 28/09/2026 al 3% proporcional y sigue impaga en la emisión
  de octubre
- **THEN** el interés es $0,13 (2 días de $0,0625, total $0,125), no $0,12

#### Scenario: Redondeo único sobre dos tramos

- **WHEN** una obligación de $64,00 vence el 28/09/2026 al 3% proporcional con gracia 0, la cuenta paga
  $1,00 con fecha valor 29/09/2026 (imputado a esa ordinaria) y el 7 registra la emisión de octubre
- **THEN** el débito tiene dos tramos (29/09 sobre $64,00, $0,064; 30/09 sobre $63,00, $0,063) y su
  importe es $0,13, no $0,12 como daría redondear cada tramo y sumar

### Requirement: Cada interés guarda su detalle por tramo

Cada débito de interés SHALL guardar uno o más tramos, cada uno con fecha desde, fecha hasta, días, base,
tasa mensual, forma de cálculo, días de gracia y la versión de configuración usada, en una tabla de sólo
agregar aislada por administración, ligada al movimiento de su misma cuenta. La suma exacta de los tramos
MUST redondear al importe del débito.

#### Scenario: Detalle de un pago parcial

- **WHEN** se registra el interés de $1.600,00 del pago parcial de $40.000
- **THEN** el débito tiene dos tramos: del 11/09 al 20/09 con base $100.000 y del 21/09 al 30/09 con base
  $60.000, ambos al 3%

#### Scenario: Detalle de un pago total

- **WHEN** una obligación de $100.000 vence el 10/09/2026 al 3% proporcional con gracia 0, la cuenta la paga
  entera con fecha valor 20/09/2026 y el 7 registra la emisión de octubre
- **THEN** el interés con corte 30/09/2026 es $1.000,00 con un solo tramo, del 11/09 al 20/09 con base
  $100.000, y ningún tramo cubre del 21/09 al 30/09 (base cero, que no se registra)

#### Scenario: Detalle de un pago total con mes entero

- **WHEN** una obligación de $100.000 vence el 10/09/2026 al 3% mes entero con gracia 0, la cuenta la paga
  entera con fecha valor 20/09/2026 y el 7 registra la emisión de octubre
- **THEN** el interés con corte 30/09/2026 es $3.000,00 con un solo tramo, del 11/09 al 30/09 con base
  $100.000 (la de su primer día a cobrar), aunque la base diaria sea cero desde el 21/09: en mes entero la
  exclusión de días con base cero del proporcional no aplica

#### Scenario: El detalle no se edita

- **WHEN** el rol de la aplicación intenta `UPDATE` o `DELETE` sobre un tramo de interés
- **THEN** la base lo rechaza con SQLSTATE `42501` y el tramo sigue igual

#### Scenario: Otra administración no ve el detalle

- **WHEN** la administración B consulta los tramos de interés con su tenant fijado
- **THEN** no ve ningún tramo de la administración A

#### Scenario: Un tramo no se cuelga de otra cuenta

- **WHEN** se intenta guardar un tramo con la cuenta de una unidad y el movimiento de interés de otra
- **THEN** la base lo rechaza por su clave foránea

### Requirement: El tramo de un interés que no cuenta pasa al corte siguiente

Si para una obligación ya existe un interés con el mismo corte que no cuenta (su emisión se anuló o se
contra-asentó), la nueva emisión SHALL NOT registrar otro en ese corte. El corte siguiente MUST cobrar los
días que ningún interés que cuenta cubre (E17), así ningún día se cobra dos veces. Los días diferidos se
cobran con la configuración vigente a ese corte siguiente, por lo que el importe MAY diferir del interés
que no cuenta (E1, E4).

#### Scenario: Anular y volver a emitir no cobra dos veces

- **WHEN** el 7 emite octubre (interés de $2.000,00 con corte 30/09/2026), la anula y emite octubre de
  nuevo
- **THEN** el interés de la emisión anulada sigue en el libro sin contar, no se registra otro con corte
  30/09/2026 y la cuenta debe $100.000 de septiembre más la obligación nueva de octubre

#### Scenario: El corte siguiente recupera el tramo

- **WHEN** después de esa re-emisión el 7 registra noviembre, la tasa sigue en 3% y la cuenta sigue sin
  pagar
- **THEN** el interés con corte 31/10/2026 cubre del 11/09 al 31/10/2026, 51 días, $5.100,00

#### Scenario: El tramo recuperado usa la tasa del corte siguiente

- **WHEN** lo mismo, pero el edificio pasó al 6% desde el 01/10/2026
- **THEN** el interés con corte 31/10/2026 es de 51 días al 6%, $10.200,00, y no los $2.000,00 + $6.200,00
  que habría dado sin anular

### Requirement: La emisión devuelve los intereses que registró

`EmisionRegistrada` SHALL informar por cuenta los débitos de interés con el id de esa emisión (obligación,
corte e importe) y el saldo anterior de cada cuenta alcanzada. El saldo anterior MUST incluir los intereses
que cuentan, porque son deuda de obligaciones anteriores.

#### Scenario: Saldo anterior con interés

- **WHEN** el 7 emite octubre para la cuenta que debe $100.000 de septiembre
- **THEN** `EmisionRegistrada` informa un interés de $2.000,00 para esa cuenta y un saldo anterior de
  $102.000,00

### Requirement: Repetir la emisión devuelve los mismos intereses y recalcula el saldo

Repetir la emisión por su id SHALL devolver los mismos intereses registrados, cuenten o no, sin escribir
nada. El saldo anterior del replay MUST recalcularse con el libro del momento del replay y no promete
igualar al de la primera respuesta (E15).

#### Scenario: Replay inmediato de una emisión con interés

- **WHEN** el 7 repite la emisión de octubre con el mismo id y las mismas obligaciones, sin que nada haya
  cambiado en el libro
- **THEN** recibe el interés de $2.000,00 y el saldo anterior de $102.000,00, y no se agrega ningún
  movimiento ni tramo

#### Scenario: Replay después de un pago

- **WHEN** después de emitir octubre la cuenta paga $30.000 con fecha valor 05/10/2026 (imputados $2.000 al
  interés y $28.000 a la ordinaria de septiembre) y el 7 repite la emisión
- **THEN** recibe el mismo interés de $2.000,00, un saldo anterior recalculado de $72.000,00, y no se agrega
  ningún movimiento ni tramo

#### Scenario: Replay después de anular

- **WHEN** la emisión de octubre se anuló y el 7 la repite por su id
- **THEN** recibe el interés registrado de $2.000,00, que ya no cuenta, un saldo anterior de $100.000,00, y
  no se agrega ningún movimiento ni tramo
