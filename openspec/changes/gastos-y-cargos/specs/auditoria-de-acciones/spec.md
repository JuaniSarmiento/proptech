## MODIFIED Requirements

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

## ADDED Requirements

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
