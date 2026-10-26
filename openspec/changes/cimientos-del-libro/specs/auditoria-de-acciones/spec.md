# Spec Delta

## MODIFIED Requirements

### Requirement: Vocabulario cerrado y detalle sin datos sensibles

La acción SHALL ser una de una lista cerrada, formada por los permisos de la matriz de D-106, los
eventos de acceso que no son permisos (`ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`,
`invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion`,
`quitar_asignacion`) y los eventos del padrón (`editar_unidad`, `editar_grupo`, `fijar_unidades`,
`editar_categoria`, `reordenar_categorias`), controlada también por la base: sumar una acción o un
evento exige una migración.
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

## ADDED Requirements

### Requirement: Los cambios del padrón que deciden el reparto quedan auditados

Editar una unidad, editar un grupo de reparto, fijar las unidades de un grupo, editar una categoría y
reordenar las categorías SHALL registrarse en la auditoría, en la misma transacción, con su evento, la
persona y el `request_id`. El detalle MUST tener sólo el id del edificio y los nombres de los campos
que cambiaron, nunca sus valores. Si el cambio se revierte, MUST NOT quedar su fila.

#### Scenario: Cambiar el coeficiente de una unidad

- **WHEN** un administrador cambia el coeficiente de una unidad de "0.050000" a "0.060000"
- **THEN** hay una fila `editar_unidad` con la persona, el id de la unidad, el `request_id` y un
  detalle con el id del edificio y el campo `coeficiente`, sin "0.050000" ni "0.060000"

#### Scenario: Fijar las unidades de un grupo

- **WHEN** un administrador cambia qué unidades forman un grupo de reparto
- **THEN** hay una fila `fijar_unidades` con el id del grupo y el del edificio

#### Scenario: El cambio que falla no deja auditoría

- **WHEN** editar una unidad falla porque el identificador nuevo ya existe en el edificio
- **THEN** no queda ninguna fila `editar_unidad` de ese intento y la unidad sigue igual

#### Scenario: Cada caso de uso con su evento

- **WHEN** se ejecutan los cinco cambios del padrón una vez cada uno
- **THEN** hay exactamente cinco filas, una por evento, y ninguna comparte evento con otro caso de uso
