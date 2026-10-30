# auditoria-de-acciones Specification

## Purpose
Registra cada acción sensible con quién la hizo, sobre qué y cuándo, en la misma transacción que la
acción, de forma que no se pueda saltear, editar ni borrar (D-016).

## Requirements

### Requirement: La acción y su registro se confirman juntos

Cada acción sensible SHALL dejar exactamente una fila de auditoría en la misma transacción que la
acción: si la acción se revierte, la fila no queda; si la fila no se puede escribir, la acción se
revierte. La fila MUST llevar la administración, la persona que actuó, la acción, la entidad afectada,
el `request_id` del pedido y la marca de tiempo de la base.

#### Scenario: Acción confirmada

- **WHEN** el titular asigna un edificio
- **THEN** queda exactamente una fila de auditoría con su persona, la acción
  `invitar_usuarios_y_asignar_edificios`, el complejo y el `request_id` del pedido

#### Scenario: Acción revertida

- **WHEN** la acción falla después de haber escrito su fila de auditoría
- **THEN** no queda ni la acción ni la fila

#### Scenario: Registro que no se puede escribir

- **WHEN** la fila de auditoría es rechazada por la base
- **THEN** la acción tampoco queda

#### Scenario: Toda acción sensible registrada

- **WHEN** se ejecuta cada caso de uso marcado como sensible
- **THEN** cada uno deja exactamente una fila, y un caso de uso sensible sin registro hace fallar la
  suite

### Requirement: Vocabulario cerrado y detalle sin datos sensibles

La acción SHALL ser una de una lista cerrada, formada por los permisos de la matriz de D-106, los
eventos de acceso que no son permisos (`ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`,
`invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion`,
`quitar_asignacion`), los eventos del padrón (`editar_edificio`, `crear_unidad`, `editar_unidad`,
`crear_grupo`, `editar_grupo`, `fijar_unidades`, `editar_categoria`, `reordenar_categorias`) y los
eventos del gasto (`crear_proveedor`, `editar_proveedor`, `crear_gasto`, `editar_gasto`,
`aprobar_gasto`, `cargar_nota_de_credito`, `crear_cargo_particular`, `editar_cargo_particular`,
`aprobar_cargo_particular`, `importar_cargos_particulares`), controlada también por la base: sumar una
acción o un evento exige una migración.
El detalle MUST aceptar sólo las claves permitidas para esa acción y MUST NOT contener contraseñas,
tokens, emails, ids de Clerk en claro ni el texto de un error de terceros. Para los eventos del gasto,
el detalle MUST NOT contener ningún importe, ni del gasto, ni del cargo particular, ni de la nota de
crédito, ni el CUIT de un proveedor. Un mismo caso de uso sensible MUST registrarse con una sola acción
y una acción MUST NOT quedar registrada por dos casos de uso que se pisen sin que la suite lo note.

#### Scenario: Acción fuera de la lista

- **WHEN** se intenta registrar una acción que no está en la lista
- **THEN** la base la rechaza

#### Scenario: Clave no permitida en el detalle

- **WHEN** el detalle trae una clave fuera de las permitidas para esa acción
- **THEN** el registro se rechaza antes de escribir, sin repetir el valor en el error

#### Scenario: Evento de acceso

- **WHEN** se registra `ingreso_exitoso` con el detalle permitido
- **THEN** la base lo acepta, y el detalle no tiene email, token ni id de Clerk

#### Scenario: Dos casos de uso con la misma acción

- **WHEN** dos casos de uso distintos se marcan como sensibles con la misma acción
- **THEN** la suite falla nombrando la acción y los dos casos de uso

#### Scenario: El evento de editar el edificio existe en la base

- **WHEN** se registra `editar_edificio` contra una base migrada
- **THEN** la base lo acepta; y contra una base sin la migración de ese cambio, lo rechaza

#### Scenario: Los eventos del gasto existen en la base

- **WHEN** se registra `aprobar_gasto` contra una base migrada con este cambio
- **THEN** la base lo acepta; y contra una base sin esta migración, lo rechaza

#### Scenario: Ningún importe en el detalle de un evento del gasto

- **WHEN** se intenta registrar `aprobar_gasto`, `cargar_nota_de_credito` o `aprobar_cargo_particular` con el importe en el detalle
- **THEN** el registro se rechaza antes de escribir, nombrando la clave no permitida

#### Scenario: Ningún CUIT en el detalle de un proveedor

- **WHEN** se intenta registrar `crear_proveedor` con el CUIT en el detalle
- **THEN** el registro se rechaza antes de escribir

### Requirement: La auditoría sólo se agrega

Ningún rol de la aplicación SHALL poder modificar, borrar ni vaciar filas de auditoría, ni desactivar
lo que lo impide: ni `proptech_app` ni `proptech_migrador`. La tabla MUST pertenecer al rol de arranque,
de modo que el migrador no sea su dueño. Incluso el dueño MUST ver rechazados `UPDATE`, `DELETE` y
`TRUNCATE` mientras el bloqueo esté activo; el único que puede desactivarlo es el superusuario de
arranque, que ningún servicio permanente tiene. Cada administración MUST ver sólo su propia auditoría.

#### Scenario: Editar o borrar como la app

- **WHEN** `proptech_app` intenta `UPDATE`, `DELETE` o `TRUNCATE` sobre la auditoría
- **THEN** la base lo rechaza y las filas siguen iguales

#### Scenario: Editar, borrar o desactivar el bloqueo como el migrador

- **WHEN** `proptech_migrador` intenta `UPDATE`, `DELETE`, `TRUNCATE`, `ALTER TABLE ... DISABLE
  TRIGGER` o `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` sobre la auditoría
- **THEN** la base lo rechaza por no ser dueño ni tener el permiso, y las filas y el bloqueo siguen
  iguales

#### Scenario: Editar o borrar como el dueño

- **WHEN** el rol de arranque, dueño de la tabla, intenta `UPDATE`, `DELETE` o `TRUNCATE` sin
  desactivar antes el bloqueo
- **THEN** la base lo rechaza y las filas siguen iguales

#### Scenario: Dueño de la tabla después de las migraciones

- **WHEN** termina el arranque del stack
- **THEN** el dueño de la auditoría es el rol de arranque, no `proptech_migrador`

#### Scenario: Auditoría de otra administración

- **WHEN** con el tenant de A se lee la auditoría
- **THEN** no aparece ninguna fila de B

### Requirement: Acciones de configuración auditadas

Crear un edificio, crear una versión de configuración de intereses, vencimiento y fondo de reserva, y
confirmar "sin saldos previos" SHALL registrarse en la auditoría, en la misma transacción que la
acción, con su acción del vocabulario cerrado (sumada por migración) y un detalle con claves
permitidas: el id del edificio y, para una versión, su fecha de vigencia. El detalle MUST NOT contener
los valores de la tasa, del porcentaje ni del recargo. Si la acción se revierte, MUST NOT quedar su
fila de auditoría.

#### Scenario: Crear un edificio queda auditado

- **WHEN** el titular crea un edificio
- **THEN** hay una fila de auditoría con la acción de crear edificio, el id del edificio, la persona y
  el `request_id`

#### Scenario: La versión que falla no deja auditoría

- **WHEN** la creación de una versión de configuración falla por la fecha repetida
- **THEN** no queda ninguna fila de auditoría de esa acción

#### Scenario: El detalle no trae la tasa

- **WHEN** se registra la creación de una versión con tasa "4.00" y recargo del segundo vencimiento
  "5.00"
- **THEN** el detalle tiene sólo el id del edificio y la fecha de vigencia

### Requirement: Los cambios del padrón que deciden el reparto quedan auditados

Crear y editar una unidad, crear y editar un grupo de reparto, fijar las unidades de un grupo, editar
una categoría y reordenar las categorías SHALL registrarse en la auditoría, en la misma transacción,
con su evento, la persona y el `request_id`, sólo si algo cambió. Si la acción o su registro fallan,
MUST NOT quedar ni el cambio ni la fila.

#### Scenario: Fijar las unidades de un grupo

- **WHEN** un administrador cambia qué unidades forman un grupo de reparto
- **THEN** hay una fila `fijar_unidades` con el id del grupo y el del edificio

#### Scenario: El cambio que falla no deja auditoría

- **WHEN** editar una unidad falla porque el identificador nuevo ya existe en el edificio
- **THEN** no queda ninguna fila `editar_unidad` de ese intento y la unidad sigue igual

#### Scenario: Si la auditoría falla, el cambio no queda

- **WHEN** el registro de la auditoría de una edición de unidad falla
- **THEN** la unidad sigue igual y la respuesta no repite ningún valor

#### Scenario: Guardar sin cambios

- **WHEN** se edita una unidad mandando los mismos valores, incluido el coeficiente "0.05" contra el
  "0.050000" guardado
- **THEN** no queda ninguna fila de auditoría

#### Scenario: Cada caso de uso con su evento

- **WHEN** se ejecutan los siete cambios del padrón una vez cada uno, cambiando algo
- **THEN** hay exactamente siete filas, una por evento, y ninguna comparte evento con otro caso de uso

### Requirement: El detalle guarda el coeficiente anterior y el nuevo

El detalle de un evento del padrón SHALL tener el id del edificio y los nombres de los campos que
cambiaron. Cuando cambia un coeficiente, de la unidad o de un miembro con coeficiente propio de un
grupo, MUST guardar además el valor anterior y el nuevo como texto, con la unidad a la que pertenece
(D-114.2). De los demás campos, MUST NOT guardar valores.

#### Scenario: Cambiar el coeficiente de una unidad

- **WHEN** un administrador cambia el coeficiente de una unidad de "0.050000" a "0.060000" y su piso
- **THEN** la fila `editar_unidad` tiene los campos `coeficiente` y `piso`, el coeficiente anterior
  "0.050000" y el nuevo "0.060000", y no tiene el piso anterior ni el nuevo

#### Scenario: Coeficientes propios de un grupo

- **WHEN** en un grupo con coeficientes propios se cambia el de una unidad, se agrega otra y se quita
  una tercera
- **THEN** la fila `fijar_unidades` lista las tres unidades con su anterior y su nuevo, vacío el
  anterior de la agregada y vacío el nuevo de la quitada

#### Scenario: Alta de una unidad y de un grupo

- **WHEN** se crea una unidad con coeficiente "0.080000" y un grupo con coeficientes propios
- **THEN** la fila `crear_unidad` tiene el nuevo "0.080000" sin anterior, y la fila `crear_grupo` tiene
  el coeficiente nuevo de cada miembro

#### Scenario: Un campo que no es de ese evento

- **WHEN** se intenta registrar `editar_grupo` con `campos` que incluye `coeficiente`, o
  `editar_unidad` con un valor anterior del piso
- **THEN** el registro se rechaza antes de escribir, sin repetir el valor

### Requirement: La corrección de un movimiento queda auditada

Toda corrección SHALL registrar en la auditoría la acción `corregir_movimiento` en la misma transacción
que el movimiento de corrección, con el edificio, el id de lo corregido y la forma de la corrección,
nunca el motivo ni el importe. Si la auditoría falla, la corrección MUST no quedar escrita.

#### Scenario: Corrección auditada

- **WHEN** el super admin registra un contra-asiento
- **THEN** existe una fila de auditoría `corregir_movimiento` con el id del movimiento de corrección como
  entidad, y su detalle no contiene el motivo ni el importe

#### Scenario: Falla la auditoría

- **WHEN** el AP pide una corrección por la API real y el registro de auditoría falla
- **THEN** la API no confirma: otra conexión comprueba que ni la corrección ni sus imputaciones quedaron en el libro

#### Scenario: El vocabulario nuevo

- **WHEN** el migrador aplica `0024` y el test de catálogo lista `accion_de_auditoria`
- **THEN** contiene `corregir_movimiento`, y bajar `0024` con una corrección auditada falla con `23503`

### Requirement: Editar el edificio queda auditado

Modificar el nombre, la ubicación, la calle y el número, la cantidad de pisos o la cantidad de
subsuelos de un edificio SHALL quedar registrado con la acción `editar_edificio`, en la misma
transacción que el cambio (D-016). El detalle MUST guardar el edificio y los nombres de los campos que
cambiaron, y MUST NOT guardar ningún otro valor. Un pedido de edición que no cambia nada MUST NOT dejar
registro.

#### Scenario: Editar la ubicación

- **WHEN** el titular cambia la localidad y la calle de un edificio
- **THEN** queda un registro `editar_edificio` con el edificio y los nombres de los dos campos, y sin
  los valores

#### Scenario: La edición falla

- **WHEN** la edición se rechaza por un trío de ubicación incoherente
- **THEN** no queda ningún registro y nada cambió

#### Scenario: Edición sin cambios

- **WHEN** el pedido de edición trae los mismos valores que ya tenía el edificio
- **THEN** no queda ningún registro

### Requirement: Los eventos del gasto quedan auditados

Crear y editar un proveedor, crear, editar y aprobar un gasto, cargar una nota de crédito, y crear,
editar, aprobar e importar cargos particulares SHALL registrarse en la auditoría, en la misma
transacción que la acción, con su evento, la persona y el `request_id`, **sólo si algo cambió**. El
detalle MUST tener el id del edificio y el id de la entidad afectada, y para una edición los nombres de
los campos que cambiaron, sin sus valores. Una aprobación repetida sobre una entidad ya aprobada MUST
NOT dejar una segunda fila. Una importación de cargos particulares MUST dejar **una sola** fila, con la
cantidad de cargos creados, nunca una fila por cargo. Si la acción o su registro fallan, MUST NOT
quedar ni el cambio ni la fila.

#### Scenario: Aprobar un gasto deja una fila

- **WHEN** se aprueba un gasto en `borrador`
- **THEN** queda exactamente una fila con `aprobar_gasto`, la persona, el `request_id`, el edificio y el id del gasto

#### Scenario: Aprobar dos veces deja una sola fila

- **WHEN** se aprueba dos veces el mismo gasto
- **THEN** la auditoría tiene una sola fila de `aprobar_gasto` para ese gasto

#### Scenario: Edición que no cambia nada

- **WHEN** se edita un gasto, un proveedor o un cargo particular mandando exactamente los mismos valores
- **THEN** no queda ninguna fila de auditoría

#### Scenario: La importación deja una sola fila

- **WHEN** se importan treinta cargos particulares desde una planilla
- **THEN** queda una sola fila de `importar_cargos_particulares`, con la cantidad creada y sin ningún importe

#### Scenario: La importación rechazada no deja fila

- **WHEN** una importación se rechaza entera por una fila inválida
- **THEN** no queda ninguna fila de auditoría ni ningún cargo creado

#### Scenario: La auditoría falla y la acción se revierte

- **WHEN** la escritura de la fila de auditoría falla al aprobar un gasto
- **THEN** el gasto no queda aprobado
