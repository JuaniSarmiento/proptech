# Spec Delta

## MODIFIED Requirements

### Requirement: Vocabulario cerrado y detalle sin datos sensibles

La acción SHALL ser una de una lista cerrada, formada por los permisos de la matriz de D-106, los
eventos de acceso que no son permisos (`ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`,
`invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion`,
`quitar_asignacion`) y los eventos del padrón (`editar_edificio`, `crear_unidad`, `editar_unidad`,
`crear_grupo`, `editar_grupo`, `fijar_unidades`, `editar_categoria`, `reordenar_categorias`),
controlada también por la base: sumar una acción o un evento exige una migración.
El detalle MUST aceptar sólo las claves permitidas para esa acción y MUST NOT contener contraseñas,
tokens, emails, ids de Clerk en claro ni el texto de un error de terceros. Un mismo caso de uso sensible
MUST registrarse con una sola acción y una acción MUST NOT quedar registrada por dos casos de uso que se
pisen sin que la suite lo note.

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
- **THEN** la base lo acepta; y contra una base sin la migración de este cambio, lo rechaza

## ADDED Requirements

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
