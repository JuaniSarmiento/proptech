# Spec Delta

## MODIFIED Requirements

### Requirement: Vocabulario cerrado y detalle sin datos sensibles

La acción SHALL ser una de una lista cerrada, formada por los permisos de la matriz de D-106, los
eventos de acceso que no son permisos (`ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`,
`invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion`,
`quitar_asignacion`) y los eventos del padrón (`crear_unidad`, `editar_unidad`, `crear_grupo`,
`editar_grupo`, `fijar_unidades`, `editar_categoria`, `reordenar_categorias`), controlada también por la base: sumar una acción o un
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
