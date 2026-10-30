## Purpose

Define la nota de crédito de un proveedor (R22, D-061, D-082): queda asociada a la factura que corrige,
su monto nunca supera el de esa factura, y se descuenta del gasto antes de prorratear dentro del mismo
grupo de reparto, sin reabrir nunca una liquidación ya emitida.

## ADDED Requirements

### Requirement: Toda nota de crédito está asociada a una factura

Una nota de crédito SHALL registrarse siempre asociada al gasto con factura que corrige. Una nota de
crédito sin factura asociada MUST rechazarse con 422, nombrando el campo. La factura asociada MUST
pertenecer al mismo edificio: una factura de otro edificio o de otra administración MUST responder 404,
y la base MUST rechazarlo aunque la aplicación se equivoque. Una nota de crédito MUST llevar su propia
clave de comprobante (`cuit + punto de venta + tipo de comprobante + número`), que MUST NOT repetirse
dentro del edificio; el tipo de comprobante distinto MUST permitir que comparta número con la factura
que corrige, sin marcarse como duplicada (R12).

#### Scenario: Nota de crédito sin factura
- **WHEN** se carga una nota de crédito sin indicar la factura que corrige
- **THEN** la API responde 422 nombrando el campo, y no crea nada

#### Scenario: Factura de otro edificio
- **WHEN** la factura indicada pertenece a otro edificio
- **THEN** la API responde 404 y no crea nada

#### Scenario: Mismo número que su factura
- **WHEN** la nota de crédito tiene el mismo número que la factura que corrige, con otro tipo de comprobante
- **THEN** queda creada y no se marca como duplicada

#### Scenario: Dos notas de crédito con la misma clave
- **WHEN** se carga dos veces la misma nota de crédito, con la misma clave de comprobante
- **THEN** la segunda responde 409

### Requirement: El monto de la nota de crédito está topeado al de su factura

El monto de una nota de crédito MUST NOT superar el importe del gasto de la factura que corrige. Si una
factura tiene más de una nota de crédito, la **suma** de todas ellas MUST NOT superar ese importe. Un
pedido que superaría el tope MUST responder 422 indicando el tope, sin crear nada y sin dejar la
factura parcialmente acreditada. El monto MUST llegar como texto decimal ASCII de hasta dos decimales,
mayor que cero, y guardarse como `NUMERIC(14,2)`.

#### Scenario: Nota de crédito menor que su factura
- **WHEN** una factura de 100.000,00 recibe una nota de crédito de 15.000,00
- **THEN** la nota queda registrada

#### Scenario: Nota de crédito igual al monto de su factura
- **WHEN** una factura de 100.000,00 recibe una nota de crédito de 100.000,00
- **THEN** la nota queda registrada y el gasto neto de esa factura queda en cero

#### Scenario: Nota de crédito mayor que su factura
- **WHEN** una factura de 100.000,00 recibe una nota de crédito de 100.000,01
- **THEN** la API responde 422 indicando el tope, y no se registra nada

#### Scenario: Dos notas de crédito que juntas superan la factura
- **WHEN** una factura de 100.000,00 ya tiene una nota de crédito de 60.000,00 y se carga otra de 50.000,00
- **THEN** la segunda responde 422 indicando el tope restante, y no se registra

#### Scenario: Carrera entre dos notas de crédito simultáneas
- **WHEN** dos pedidos simultáneos cargan notas de crédito que, sumadas, superarían el importe de la misma factura
- **THEN** sólo una queda registrada y la otra es rechazada; la suma registrada nunca supera el importe de la factura

### Requirement: La nota de crédito se descuenta antes de prorratear, en el grupo de su factura

Una nota de crédito SHALL descontarse del gasto **antes** de prorratear, dentro del **mismo grupo de
reparto** de la factura original: MUST NOT registrarse como un gasto negativo suelto ni cambiar el
total de ningún otro grupo. La lectura de gastos aprobados del período MUST devolver el total de cada
grupo ya neto de sus notas de crédito. Una nota de crédito sobre una factura de un gasto que todavía no
está aprobado MUST poder registrarse igual, y MUST afectar el neto recién cuando el gasto se apruebe.

#### Scenario: Baja el total de su grupo
- **WHEN** una nota de crédito corrige una factura del grupo "Ascensor"
- **THEN** el total neto del grupo "Ascensor" baja en ese monto

#### Scenario: No toca los otros grupos
- **WHEN** una nota de crédito corrige una factura del grupo "Ascensor"
- **THEN** el total de "Generales" y el de cualquier otro grupo quedan iguales

#### Scenario: No es un gasto negativo
- **WHEN** se listan los gastos del período
- **THEN** la nota de crédito no figura como un gasto, sino asociada a su factura

#### Scenario: Nota de crédito sobre un gasto no aprobado
- **WHEN** la factura corregida está en `borrador` y se registra su nota de crédito
- **THEN** la nota queda registrada y el neto del grupo no cambia hasta que el gasto se apruebe

### Requirement: Una nota de crédito nunca reabre un período ya emitido

Si la factura que corrige ya fue liquidada en un período emitido, la nota de crédito SHALL descontarse
en el **período en que se carga**, dentro del mismo grupo (D-082). MUST NOT modificar, recalcular ni
reabrir la liquidación emitida, ni generar ningún movimiento en el libro. El período de imputación de
la nota MUST quedar registrado junto a ella, distinto del período de su factura cuando corresponda.

#### Scenario: Factura ya liquidada
- **WHEN** se carga una nota de crédito sobre una factura de un período ya emitido
- **THEN** se descuenta en el período en que se carga y la liquidación emitida no cambia

#### Scenario: Queda registrado en qué período se descontó
- **WHEN** se consulta una nota de crédito de una factura de un período anterior
- **THEN** devuelve el período de su factura y el período en que se descuenta, separados

#### Scenario: No escribe en el libro
- **WHEN** se carga cualquier nota de crédito
- **THEN** no queda ningún movimiento, obligación ni imputación nuevo en el libro

### Requirement: Cargar una nota de crédito queda auditado

Cargar una nota de crédito SHALL registrarse en la auditoría, en la misma transacción, con la persona,
el `request_id`, el edificio, el id de la nota y el id de la factura que corrige. El detalle MUST NOT
guardar el monto. Si la escritura de la auditoría falla, la nota MUST NOT quedar registrada. Cargar una
nota de crédito MUST exigir el permiso `cargar_gastos_y_preparar_liquidacion`.

#### Scenario: Alta auditada
- **WHEN** se carga una nota de crédito
- **THEN** queda exactamente una fila de auditoría con la persona, el `request_id`, el edificio, la nota y su factura, sin el monto

#### Scenario: La auditoría falla
- **WHEN** la escritura de la fila de auditoría falla
- **THEN** la nota de crédito no queda registrada

#### Scenario: Sin permiso
- **WHEN** un contador intenta cargar una nota de crédito
- **THEN** la API responde 403
