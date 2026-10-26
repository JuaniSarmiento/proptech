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

- **WHEN** el 8 registra un pago de $100.000 en una cuenta que debe agosto ($80.000 de ordinaria y $4.000 de interés) y septiembre ($85.000 de ordinaria)
- **THEN** se imputan $4.000 al interés de agosto, $80.000 a la ordinaria de agosto y $16.000 a la
  ordinaria de septiembre, que queda con $69.000

#### Scenario: Un pago parcial cubre la ordinaria antes que la extraordinaria

- **WHEN** el 8 registra un pago de $45.000 sobre una obligación de $40.000 de ordinaria y $10.000 de extraordinaria
- **THEN** la ordinaria queda en cero y la extraordinaria con $5.000

#### Scenario: El fondo de reserva, entre la ordinaria y la extraordinaria

- **WHEN** el 8 registra un pago de $41.000 sobre una obligación de $40.000 de ordinaria, $2.000 de fondo y $10.000 de extraordinaria
- **THEN** la ordinaria queda en cero, el fondo con $1.000 y la extraordinaria con $10.000

#### Scenario: Un pago que cubre exacto un período

- **WHEN** el 8 registra un pago de $84.000 sobre una cuenta que debe $84.000 en agosto y tiene además deuda de septiembre
- **THEN** agosto queda en cero, septiembre no cambia y no queda crédito a favor

### Requirement: Lo que sobra queda como crédito a favor

Lo que un crédito sin destino fijo no puede imputar porque no queda deuda SHALL quedar como crédito a favor de la cuenta,
sin crear ningún movimiento nuevo, y MUST imputarse con el mismo orden cuando la cuenta tenga una
obligación nueva (R05).

#### Scenario: Pago mayor que la deuda

- **WHEN** el 8 registra un pago de $60.000 en una cuenta que debe $50.000
- **THEN** la deuda queda en cero y la cuenta tiene $10.000 de crédito a favor

#### Scenario: El crédito a favor se imputa en la emisión siguiente

- **WHEN** el 7 registra la emisión de diciembre por $40.000 para una cuenta con $10.000 a favor
- **THEN** la obligación de diciembre queda con $30.000 y el crédito a favor en cero

#### Scenario: Un pago imputado a una emisión que se anula vuelve como crédito

- **WHEN** el 7 anula la emisión de noviembre a la que se había imputado un pago de $40.000 registrado por el 8
- **THEN** la cuenta tiene $40.000 de crédito a favor, y al registrar la nueva emisión de noviembre se
  imputa a ella

### Requirement: Los créditos que no son pagos van a su destino fijo

Condonación y ajuste de interés SHALL ir sólo al interés referenciado; bonificación, a la ordinaria bonificada. Corrección, reimputación y baja de deuda MUST usar R04 (D-086). Un destino fijo sin capacidad MUST rechazarse con `EntradaInvalida("destino")` (422), sin registrar el pedido. Una bonificación de una emisión anulada MUST quedar atada a su destino y saltearse en `imputar_pendientes` hasta su reversión en el 8. E16 queda a validar (P42, A-4).

#### Scenario: Una condonación baja sólo el interés condonado

- **WHEN** el 10b registra una condonación de $4.000 sobre el interés de agosto, que tiene $4.000 de interés y $80.000 de ordinaria
- **THEN** el interés de agosto queda en cero y la ordinaria sigue en $80.000

#### Scenario: Un ajuste de interés baja sólo el interés que compensa

- **WHEN** el 8 registra un ajuste de $500 sobre el interés de septiembre, con deuda también en agosto
- **THEN** sólo el interés de septiembre baja $500

#### Scenario: Una bonificación va a la ordinaria de su período

- **WHEN** el 8 registra una bonificación de $2.000 sobre la ordinaria de octubre, con agosto impago
- **THEN** sólo la ordinaria de octubre baja $2.000

#### Scenario: Destino fijo sin un componente que absorba

- **WHEN** el 10b intenta registrar una condonación de $4.000 sobre una obligación sin interés
- **THEN** el pedido se rechaza con 422 nombrando `destino`; no queda crédito a favor y una emisión posterior de diciembre por $40.000 queda en $40.000

### Requirement: Ninguna obligación queda con residual negativo

Ninguna imputación SHALL hacer que el residual de un componente de una obligación quede por debajo de
cero.

#### Scenario: Dos créditos que juntos superan la deuda

- **WHEN** el 8 registra dos pagos de $8.000, uno después del otro, sobre una obligación que debe $10.000
- **THEN** la obligación queda en cero y la cuenta tiene $6.000 de crédito a favor

### Requirement: Dos créditos de la misma cuenta nunca usan la misma foto

Toda escritura que impute sobre una cuenta SHALL serializarse con las demás escrituras de esa cuenta,
para que la segunda vea lo que imputó la primera (R04). Escrituras de cuentas distintas MUST poder correr
a la vez.

#### Scenario: Dos pagos simultáneos

- **WHEN** dos confirmaciones de pago del 8 registran a la vez $60.000 cada una sobre una cuenta que debe $100.000, contra PostgreSQL real
- **THEN** la deuda queda en cero, la cuenta tiene $20.000 de crédito a favor y la suma de las
  imputaciones es $100.000

#### Scenario: Una emisión y un pago a la vez

- **WHEN** los llamadores del 7 y del 8 registran a la vez una emisión de $40.000 por cuenta que toca diez cuentas y un pago de $40.000 de una de ellas, cuya deuda inicial era cero
- **THEN** las dos terminan sin interbloqueo; en esa cuenta la deuda y el crédito quedan en cero y las imputaciones suman $40.000

#### Scenario: Cuentas distintas no se esperan

- **WHEN** el 8 registra pagos simultáneos en dos cuentas distintas, y una transacción demora antes de confirmar
- **THEN** la otra confirma sin esperarla

#### Scenario: Bonificación de una emisión anulada

- **WHEN** el llamador del 8 bonifica $2.000 de la ordinaria de noviembre, el 7 anula esa emisión y emite diciembre por $40.000
- **THEN** diciembre queda en $40.000; la bonificación sigue atada a noviembre y no se imputa a diciembre, pendiente de reversión por el 8. La lectura devuelve `credito_a_favor="2000.00"`, `credito_a_favor_aplicable="0.00"` y `credito_a_favor_retenido="2000.00"` (valores Dinero, representados acá como texto); el vecino ve crédito a favor retenido separado del aplicable en su futura pantalla del 11

### Requirement: El exceso vuelve desde la imputación más reciente

Si un componente pierde deuda por corrección, sus imputaciones SHALL contar hasta el tope de lo debido. El exceso MUST volver a los créditos de la imputación más reciente a la más antigua, usando una secuencia monótona `orden` de `imputacion`, sin desempatar por `now()` ni UUID. E7 queda a validar (P42, A-4).

#### Scenario: Crédito retroactivo con imputación posterior

- **WHEN** sobre una obligación de octubre de $40.000 de capital e intereses I1 $4.000 e I2 $6.000 de cortes distintos, el 8 registra B $6.000 el 15/10 con fecha valor 15/10, luego A $4.000 el 16/10 con fecha valor 1/9, y el AP contra-asienta I1 el 17/10
- **THEN** B se imputa antes que A por el flujo real de D8; tras corregir, B conserva $6.000 imputados y A $0, con A a favor $4.000 y B $0, y deuda de capital $40.000; el mutante que ordena créditos por fecha valor devuelve B $4.000 y falla en la atribución aunque el total sea igual

#### Scenario: Dos imputaciones con la misma fecha de registro

- **WHEN** el ensayo imputa primero un crédito de $6.000 y luego otro de $4.000 a $10.000 de interés (I1 de $4.000 e I2 de $6.000, cortes distintos) de una obligación en una misma emisión, con `registrada_en` iguales, y el AP contra-asienta I1
- **THEN** las imputaciones tienen valores `orden` distintos y los $4.000 vuelven siempre al segundo crédito, dejando los $6.000 del primero imputados, también al repetir veinte veces; el mutante que desempata por UUID debe cambiar esa atribución

### Requirement: El estado conserva topes por componente

El cálculo SHALL devolver residual no negativo por componente, imputado que cuenta no mayor a lo debido por componente y crédito a favor no negativo por crédito. En casos con capital positivo, sin exclusiones ni nuevos débitos y con imputación efectiva positiva, la deuda MUST ser menor que la suma del capital. El oráculo de propiedades MUST calcular exclusiones por su propio camino, sin importar el predicado productivo.

#### Scenario: Imputaciones efectivas reducen deuda

- **WHEN** el ensayo calcula $10.000 de capital con un pago imputado de $4.000
- **THEN** la deuda es $6.000, menor a $10.000; el mutante que ignora imputaciones falla en esa aserción

#### Scenario: Tope luego de corregir el interés

- **WHEN** el ensayo calcula un componente de interés reducido a cero con $4.000 imputados antes de corregirlo
- **THEN** el imputado que cuenta es cero, el residual es cero y $4.000 vuelven al crédito; el mutante sin el tope del paso 3 falla

#### Scenario: Pago con fecha valor anterior a una corrección

- **WHEN** el ensayo parte de una obligación ya saldada a la que el AP referencia un crédito de corrección de $5.000 el 10/11; el 8 registra después un pago de $7.000 con fecha valor 1/11 y el 7 emite $8.000 sin deuda residual anterior
- **THEN** se imputan primero $7.000 del pago y luego $1.000 de la corrección; quedan $4.000 de la corrección a favor

### Requirement: El candado exige READ COMMITTED

`bloquear_cuentas` SHALL ser pública e idempotente dentro de la transacción y exigir READ COMMITTED; otro nivel da `AislamientoNoAdmitido` antes de imputar. Si el llamador toca varias cuentas, MUST prebloquearlas todas juntas en una llamada ordenada antes de escribir; las operaciones unitarias bloquean por dentro. Las cuentas nuevas MUST crearse ordenadas por `unidad_id`, con su candado en la misma transacción.

#### Scenario: REPEATABLE READ no usa una foto vieja

- **WHEN** el ensayo abre REPEATABLE READ, lee una deuda de $100.000 y espera el candado mientras otra conexión imputa $60.000, y luego intenta imputar otros $60.000
- **THEN** recibe `AislamientoNoAdmitido` antes de escribir; el mutante sin el chequeo muestra la doble imputación de $120.000

#### Scenario: Emisiones con unidades nuevas cruzadas

- **WHEN** dos ejecuciones del 7 registran en el mismo edificio emisiones de períodos distintos, octubre y noviembre, por $40.000 por unidad, con las unidades nuevas A y B recibidas en orden cruzado
- **THEN** ambas emisiones se registran sin interbloqueo y comparten una sola cuenta por unidad con su candado; las cuentas se crean en orden de `unidad_id`; el mutante que las crea en órdenes cruzados provoca 40P01 y falla el éxito de ambas

#### Scenario: Importe no positivo

- **WHEN** el llamador del 8 pide registrar un crédito de cero o negativo, o el ensayo llama a `imputar` con esos importes
- **THEN** recibe `EntradaInvalida("importe")` sin escribir ni imputar

#### Scenario: Varias cuentas prebloqueadas y rebloqueo interno

- **WHEN** dos composiciones del 8 prebloquean públicamente las cuentas A y B juntas y luego registran operaciones unitarias en órdenes A/B y B/A dentro de sus respectivas transacciones
- **THEN** ambas terminan sin 40P01, las operaciones internas pueden re-bloquear sin error y cada escritura conserva su efecto una sola vez; el mutante sin prebloqueo que adquiere incrementalmente A/B y B/A falla con las barreras del test
