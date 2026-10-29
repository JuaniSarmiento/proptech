## Purpose

Define el gasto del edificio (R12, R13, R16, D-075): qué se gastó, en qué período, de qué categoría y
grupo de reparto, con sus cuatro estados y con la aprobación como única puerta al cálculo, de modo que
el cambio 7 encuentre un conjunto cerrado de gastos aprobados al que aplicarle el reparto.

## ADDED Requirements

### Requirement: Carga manual de un gasto

Un gasto SHALL llevar siempre edificio, concepto (de 1 a 200 caracteres, sin quedar en blanco),
categoría de gasto, grupo de reparto, período, importe y tipo ordinario o extraordinario. La categoría
MUST ser obligatoria (R16) y MUST pertenecer al mismo edificio; el grupo de reparto MUST pertenecer al
mismo edificio y MUST estar activo al momento de cargar el gasto. El tipo MUST ser `ordinario` o
`extraordinario`, con `ordinario` por defecto (R13). El período MUST ser el primer día de un mes. El
importe MUST llegar como texto decimal ASCII con hasta dos decimales y MUST ser mayor que cero;
guardarse como `NUMERIC(14,2)` y devolverse como texto, nunca como número de punto flotante (R07,
D-046). Un importe con tres decimales MUST responder 422 nombrando el campo y el formato esperado. El
proveedor MUST ser opcional: un gasto sin factura (como el sueldo del encargado) MUST poder cargarse
sin proveedor. La base MUST rechazar una categoría, un grupo o un proveedor de otro edificio o de otra
administración aunque la aplicación se equivoque.

#### Scenario: Alta mínima de un gasto a mano
- **WHEN** el administrador carga un gasto con concepto, categoría, grupo, período, importe y tipo
- **THEN** el gasto queda creado en estado `borrador`, con su importe devuelto como texto con dos decimales

#### Scenario: Gasto sin categoría
- **WHEN** el administrador carga un gasto sin categoría
- **THEN** la API responde 422 nombrando el campo, y no crea nada

#### Scenario: Importe con tres decimales
- **WHEN** el importe llega con tres decimales
- **THEN** la API responde 422 nombrando el campo y el formato esperado, y no crea nada

#### Scenario: Importe cero o negativo
- **WHEN** el importe es cero o negativo
- **THEN** la API responde 422 y no crea nada

#### Scenario: Grupo de reparto desactivado
- **WHEN** el administrador carga un gasto contra un grupo de reparto desactivado
- **THEN** la API lo rechaza con 422, nombrando el grupo

#### Scenario: Categoría de otro edificio
- **WHEN** el administrador carga un gasto cuya categoría pertenece a otro edificio
- **THEN** la API responde 422 y, ante un intento por SQL directo, la base también lo rechaza

#### Scenario: Período que no es el primero del mes
- **WHEN** el período llega con un día distinto del primero
- **THEN** la API responde 422

#### Scenario: Tipo por defecto
- **WHEN** el administrador carga un gasto sin indicar el tipo
- **THEN** el gasto queda `ordinario`

### Requirement: El sueldo del encargado entra como un gasto más

El sueldo del encargado SHALL cargarse como un gasto común, con el total del recibo que liquidó el
contador (sueldo y cargas sociales), su categoría y su grupo (D-028). El sistema MUST NOT calcular
escalas, aportes ni contribuciones, y MUST NOT exigir proveedor para este gasto.

#### Scenario: Carga del recibo del encargado
- **WHEN** el administrador carga el total del recibo del encargado con su categoría y su grupo, sin proveedor
- **THEN** el gasto queda creado como cualquier otro y, una vez aprobado, entra en el cálculo de su grupo

#### Scenario: No hay cálculo de sueldo
- **WHEN** se busca en la API una operación que calcule un sueldo a partir de una escala
- **THEN** no existe

### Requirement: Los cuatro estados del gasto

Un gasto SHALL estar en uno de cuatro estados (D-075): `borrador` (cargado y sin aprobar), `sin_ia`
(la lectura automática falló y espera carga manual), `en_revision` (leído con alertas) y `aprobado`.
Un gasto nuevo cargado a mano MUST nacer en `borrador`. Sólo el estado `aprobado` MUST entrar en
cualquier cálculo o lectura destinada a liquidar; `borrador`, `sin_ia` y `en_revision` MUST quedar
afuera. Los estados `sin_ia` y `en_revision` MUST existir y poder fijarse y consultarse desde este
cambio, aunque quien los produzca automáticamente sea el cambio 14 (D-078). El estado MUST ser una
lista cerrada, controlada también por la base.

#### Scenario: Un gasto nace en borrador
- **WHEN** el administrador carga un gasto a mano
- **THEN** su estado es `borrador`

#### Scenario: Un gasto en borrador no entra en el cálculo
- **WHEN** se piden los gastos aprobados del período y existe un gasto en `borrador` de ese período
- **THEN** ese gasto no figura, y el total del grupo no lo incluye

#### Scenario: Un gasto sin IA no entra en el cálculo
- **WHEN** existe un gasto en `sin_ia` del período
- **THEN** no figura entre los aprobados, y el período se puede seguir consultando sin error

#### Scenario: Un gasto en revisión no entra en el cálculo
- **WHEN** existe un gasto en `en_revision` del período
- **THEN** no figura entre los aprobados

#### Scenario: Estado desconocido por SQL
- **WHEN** se intenta escribir por SQL directo un gasto con un estado fuera de los cuatro
- **THEN** la base lo rechaza

### Requirement: Aprobar un gasto es una transición única y auditada

Aprobar un gasto SHALL llevarlo a `aprobado` desde `borrador`, `sin_ia` o `en_revision`, exigiendo el
permiso `cargar_gastos_y_preparar_liquidacion`. Aprobar un gasto ya aprobado MUST NOT tener efecto ni
dejar un segundo registro: MUST responder de forma idempotente y la auditoría MUST quedar con una sola
fila. La aprobación MUST registrarse en la auditoría en la misma transacción, con la persona, el
`request_id`, el edificio y el id del gasto, y MUST NOT guardar el importe. Un gasto aprobado MUST NOT
poder editar su importe, su grupo, su período ni su tipo; corregir un gasto aprobado MUST pasar por
volverlo a `borrador` en una acción propia y auditada, o por una nota de crédito cuando el error es del
proveedor (R22).

#### Scenario: Aprobación simple
- **WHEN** el administrador aprueba un gasto en `borrador`
- **THEN** el gasto queda `aprobado` y entra en la lectura de aprobados del período

#### Scenario: Aprobar dos veces el mismo gasto
- **WHEN** el administrador aprueba dos veces el mismo gasto
- **THEN** el segundo pedido no cambia nada, no duplica el gasto en el cálculo y deja una sola fila de auditoría

#### Scenario: Editar el importe de un gasto aprobado
- **WHEN** el administrador intenta cambiar el importe de un gasto ya aprobado
- **THEN** la API lo rechaza y el importe no cambia

#### Scenario: Aprobar sin permiso
- **WHEN** un contador o un auxiliar sin el permiso intenta aprobar un gasto
- **THEN** la API responde 403 y el gasto sigue en su estado

#### Scenario: La auditoría falla al aprobar
- **WHEN** la escritura de la fila de auditoría falla al aprobar
- **THEN** el gasto no queda aprobado

### Requirement: Factura de proveedor y control de duplicados

Un gasto SHALL poder llevar los datos de su factura: CUIT del emisor, punto de venta, tipo de
comprobante y número (R12). Cuando los lleva, los cuatro MUST estar presentes juntos; traer algunos sí
y otros no MUST responder 422. La clave `cuit + punto de venta + tipo de comprobante + número` MUST NOT
repetirse dentro del edificio: una repetición MUST responder 409 al cargarla, nombrando que es un
duplicado. El tipo de comprobante MUST formar parte de la clave, de modo que una factura y una nota de
crédito con el mismo número no se confundan entre sí (R22). Dos edificios distintos MUST poder tener la
misma clave de factura sin conflicto. Si el documento del receptor viene informado y no coincide con el
del edificio, el sistema MUST avisarlo antes de confirmar, sin bloquear la carga.

#### Scenario: Factura cargada dos veces
- **WHEN** el administrador carga un gasto con una clave de factura que ya existe en ese edificio
- **THEN** la API responde 409 indicando que es un duplicado, y no crea nada

#### Scenario: Misma clave en otro edificio
- **WHEN** la misma clave de factura se carga en un edificio distinto
- **THEN** el gasto queda creado, sin conflicto

#### Scenario: Factura y nota de crédito con el mismo número
- **WHEN** se carga una nota de crédito cuyo número coincide con el de una factura ya cargada, con otro tipo de comprobante
- **THEN** no se marca como duplicada

#### Scenario: Datos de factura incompletos
- **WHEN** el gasto trae el CUIT y el número pero no el punto de venta ni el tipo
- **THEN** la API responde 422 nombrando los campos que faltan

#### Scenario: Receptor distinto del edificio
- **WHEN** el documento del receptor informado no coincide con el del edificio
- **THEN** la respuesta incluye el aviso y la carga no se bloquea

### Requirement: Lectura de los gastos aprobados del período

La API SHALL ofrecer la lectura de los gastos aprobados de un período, agrupados por grupo de reparto y
con el tipo ordinario o extraordinario de cada uno, con el total de cada grupo **neto de sus notas de
crédito** (R22). Los importes MUST devolverse como texto en `Decimal`, nunca como punto flotante, y el
total de cada grupo MUST ser exactamente la suma de sus gastos menos sus notas de crédito, al centavo.
La lectura MUST incluir el desglose por categoría dentro de cada tipo, para la presentación de R16.
Esta lectura MUST NOT repartir ni calcular nada por unidad: el reparto lo hace el cambio 7 con
`compartido/reparto.py`.

#### Scenario: Total por grupo
- **WHEN** un período tiene gastos aprobados en dos grupos distintos
- **THEN** la lectura devuelve el total de cada grupo por separado, y ninguno incluye los del otro

#### Scenario: El total es neto de notas de crédito
- **WHEN** un grupo tiene un gasto aprobado de 100.000,00 y una nota de crédito de 15.000,00 sobre su factura
- **THEN** el total del grupo es 85.000,00

#### Scenario: Ordinario y extraordinario separados
- **WHEN** un grupo tiene gastos aprobados ordinarios y extraordinarios
- **THEN** la lectura los devuelve en bloques separados, cada uno con su subtotal

#### Scenario: Desglose por categoría
- **WHEN** un bloque tiene gastos de dos categorías
- **THEN** la lectura devuelve el subtotal de cada categoría dentro de ese bloque

#### Scenario: Sin gastos aprobados
- **WHEN** el período no tiene ningún gasto aprobado
- **THEN** la lectura devuelve los grupos con total cero, sin error

#### Scenario: Los importes son texto
- **WHEN** se lee cualquier total
- **THEN** llega como texto decimal con dos decimales, no como número de punto flotante

### Requirement: Consulta de gasto mensual obligatorio faltante

La API SHALL ofrecer una consulta que, para un período, devuelva qué gastos mensuales obligatorios del
edificio no tienen ningún gasto aprobado en ese período (R34, D-079). La consulta MUST devolver
únicamente el hecho (qué falta), sin nivel de alerta ni bloqueo: el control, su nivel y la posibilidad
de aceptarlo los construye el cambio 7. Un edificio sin ningún gasto mensual obligatorio marcado MUST
devolver una lista vacía, nunca un error.

#### Scenario: Falta un obligatorio
- **WHEN** el edificio tiene un gasto mensual obligatorio marcado y el período no tiene ningún gasto aprobado que lo cubra
- **THEN** la consulta lo devuelve entre los faltantes

#### Scenario: El obligatorio está cubierto
- **WHEN** el período tiene un gasto aprobado que cubre ese obligatorio
- **THEN** la consulta no lo devuelve entre los faltantes

#### Scenario: Un gasto en borrador no cubre un obligatorio
- **WHEN** el único gasto que cubriría el obligatorio está en `borrador`
- **THEN** la consulta lo sigue devolviendo entre los faltantes

#### Scenario: Edificio sin obligatorios
- **WHEN** el edificio no tiene ningún gasto mensual obligatorio marcado
- **THEN** la consulta devuelve una lista vacía, sin error

#### Scenario: La consulta no bloquea nada
- **WHEN** hay obligatorios faltantes
- **THEN** la consulta los informa y ninguna operación de carga ni de aprobación queda bloqueada por eso

### Requirement: Alcance, permisos y aislamiento de los gastos

Un gasto SHALL verse y escribirse sólo dentro de su edificio. Un pedido sobre un gasto de un edificio
fuera del alcance de quien lo hace MUST responder 404, y uno sin el permiso necesario MUST responder
403, con el orden de D7. Cargar, editar y aprobar gastos MUST exigir el permiso
`cargar_gastos_y_preparar_liquidacion`. El contador y el consejo MUST poder leer los gastos de su
alcance y MUST NOT poder escribirlos (D-106). Row-Level Security por administración MUST valer también
para las tablas nuevas, y MUST impedir ver o escribir un gasto de otra administración aun por SQL
directo.

#### Scenario: Gasto de otro edificio
- **WHEN** un administrador con alcance sobre el edificio A pide un gasto del edificio B
- **THEN** la API responde 404

#### Scenario: El consejo lee pero no escribe
- **WHEN** un miembro del consejo lista los gastos de su edificio y luego intenta cargar uno
- **THEN** la lista llega y la carga responde 403

#### Scenario: Aislamiento por administración, también por SQL
- **WHEN** una sesión con el tenant de la administración A consulta por SQL directo los gastos de la administración B
- **THEN** no obtiene ninguna fila
