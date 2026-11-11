# Spec Delta

## ADDED Requirements

### Requirement: El saldo anterior publicado sale de una sola lectura de todas las cuentas

El saldo anterior que devuelve el registro de una emisión, nueva o repetida, SHALL salir de una única
lectura del libro que pide juntas todas las cuentas alcanzadas por la emisión (las que tienen una
obligación suya y las que tienen un movimiento suyo, como su interés), tomada bajo sus candados y después
de la última escritura de la emisión (RF-01, E12 del 4b). Leer cuenta por cuenta MUST considerarse un
defecto.

#### Scenario: Una sola lectura al publicar una emisión nueva

- **WHEN** el 7 registra la emisión de octubre de dos cuentas
- **THEN** la última lectura del estado del libro dentro del registro es una sola sentencia que pide las
  dos cuentas

#### Scenario: Una sola lectura al repetir una emisión

- **WHEN** el 7 repite por su id la emisión de octubre de dos cuentas
- **THEN** la última lectura del estado del libro dentro del registro es una sola sentencia que pide las
  dos cuentas

#### Scenario: La lectura incluye la cuenta que sólo recibió interés

- **WHEN** el 7 registra la emisión de octubre con obligación sólo para U1, y U2, sin obligación nueva,
  recibe interés por septiembre
- **THEN** la última lectura es una sola sentencia que pide U1 y U2, y el registro devuelve el saldo
  anterior de las dos

### Requirement: La anulación bloquea todas las cuentas alcanzadas por su emisión

Al anular una emisión, el sistema SHALL bloquear, en un solo pedido ordenado y antes de escribir el evento,
todas las cuentas alcanzadas por la emisión: las que tienen una obligación suya y las que sólo tienen un
movimiento suyo, como un interés (E10, R17).

#### Scenario: Anular bloquea también la cuenta que sólo recibió interés

- **WHEN** la emisión de octubre tiene obligación sólo para U1 y registró interés para U1 y U2, y se anula
- **THEN** la anulación pide los candados de U1 y U2 en una sola llamada, ordenados

### Requirement: La anulación espera a una corrección en curso, en sus dos formas

Una anulación SHALL esperar a que termine una corrección en curso sobre una cuenta alcanzada por su
emisión, tanto con un crédito de corrección como con un contra-asiento, para que ninguna corrección quede
escrita sobre una emisión que ya estaba anulada al escribirse (RF-02, E6, R08).

#### Scenario: Anulación durante un crédito de corrección

- **WHEN** un crédito de corrección sobre una obligación de la emisión E pasa su chequeo de anulación y,
  en ese momento, otra conexión intenta anular E
- **THEN** la anulación espera a que la corrección se confirme, y al escribirse la corrección E no
  estaba anulada

#### Scenario: Anulación durante un contra-asiento

- **WHEN** un contra-asiento de un crédito de corrección de una obligación de la emisión E pasa su
  chequeo de anulación y, en ese momento, otra conexión intenta anular E
- **THEN** la anulación espera a que el contra-asiento se confirme, y al escribirse el contra-asiento E
  no estaba anulada

#### Scenario: Anulación durante el contra-asiento de un interés de una cuenta sin obligación

- **WHEN** U2 no tiene obligación en la emisión E pero recibió de E un interés por septiembre, un
  contra-asiento de ese interés pasa su chequeo de anulación y, en ese momento, otra conexión intenta
  anular E
- **THEN** la anulación espera a que el contra-asiento se confirme, y al escribirse el contra-asiento E no
  estaba anulada
