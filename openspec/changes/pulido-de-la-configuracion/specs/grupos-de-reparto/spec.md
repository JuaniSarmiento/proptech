# Spec Delta

## ADDED Requirements

### Requirement: Un grupo parcial se desactiva, nunca se borra

Un grupo de reparto MUST NOT poder borrarse: se desactiva y se puede reactivar, igual que una categoría
de gasto (R16), para que los gastos que lo usen (cambio 6) conserven su grupo. Un grupo desactivado
MUST seguir existiendo con su nombre, su clave, su método y sus unidades, MUST NOT aparecer entre los
grupos disponibles para repartir un gasto y MUST NOT hacer que la puesta a punto del edificio reclame
unidades. "Generales" MUST NOT poder desactivarse, y la base MUST rechazarlo aunque la aplicación se
equivoque.

#### Scenario: Desactivar un grupo parcial

- **WHEN** el titular desactiva el grupo "Pileta"
- **THEN** el grupo sigue en el edificio, marcado inactivo, con sus unidades, y no aparece entre los
  grupos disponibles

#### Scenario: Reactivar

- **WHEN** el titular reactiva "Pileta"
- **THEN** el grupo vuelve a estar disponible, con las mismas unidades que tenía

#### Scenario: Borrar

- **WHEN** se intenta borrar un grupo
- **THEN** no existe ruta que lo permita y el grupo sigue

#### Scenario: Desactivar Generales

- **WHEN** se intenta desactivar "Generales"
- **THEN** la respuesta es 422 y el grupo sigue activo

#### Scenario: Desactivar Generales por SQL

- **WHEN** conectado como `proptech_app` con el tenant del edificio se desactiva "Generales" por SQL
- **THEN** la base rechaza la escritura

#### Scenario: Un grupo desactivado no reclama unidades

- **WHEN** el único grupo parcial sin unidades está desactivado
- **THEN** el paso de grupos de la puesta a punto está `hecho`

## MODIFIED Requirements

### Requirement: Grupos con método y unidades del mismo edificio

Un grupo SHALL tener una clave (`^[a-z][a-z0-9_]{0,39}$`, ASCII, coincidencia completa), un nombre de
hasta 80 caracteres, un método (`coeficiente`, `superficie` o `partes_iguales`) y sus unidades. Cada
unidad de un grupo MUST pertenecer al mismo edificio y a la misma administración que el grupo; la base
MUST rechazarlo aunque la aplicación se equivoque. Una unidad MUST figurar una sola vez en un grupo.
Una clave repetida dentro del edificio MUST responder 409.

La clave de un grupo nuevo SHALL derivarse del nombre cuando el pedido no la traiga: minúsculas, sin
tildes, los caracteres que no son letras ni dígitos ASCII reemplazados por guion bajo sin repetirlo,
empezando por una letra y recortada a 40 caracteres; si la clave derivada ya existe en el edificio MUST
desempatarse con un sufijo numérico. Un nombre del que no sale ninguna clave válida MUST responder 422
nombrando el nombre. La API MUST seguir aceptando una clave explícita, para la semilla y el importador.
La clave de un grupo existente MUST NOT cambiar al renombrarlo.

#### Scenario: Grupo con una unidad de otro edificio

- **WHEN** el titular crea en el edificio A un grupo con una unidad del edificio B de su misma
  administración (id válido, fila que existe)
- **THEN** la respuesta es 422 y el grupo no se crea

#### Scenario: Grupo con una unidad de otra administración

- **WHEN** el titular de A manda en un grupo el id de una unidad de B
- **THEN** la respuesta es la misma 422 que para una unidad de otro edificio, sin revelar que existe

#### Scenario: La base frena lo que la aplicación deja pasar

- **WHEN** conectado como `proptech_app` con el tenant de A se inserta por SQL un miembro de grupo que
  apunta a una unidad de otro edificio
- **THEN** la base rechaza la escritura

#### Scenario: Unidad repetida en un grupo

- **WHEN** se agrega dos veces la misma unidad a un grupo
- **THEN** la respuesta es 409 y la unidad figura una sola vez

#### Scenario: Clave derivada del nombre

- **WHEN** el titular crea un grupo llamado "Pileta y SUM" sin mandar clave
- **THEN** el grupo queda con la clave `pileta_y_sum`

#### Scenario: Nombre con tildes y signos

- **WHEN** el nombre es "Ascensor — línea B (2° torre)"
- **THEN** la clave derivada es ASCII, empieza con letra, no tiene guiones bajos repetidos ni al final, y
  no pasa los 40 caracteres

#### Scenario: Clave derivada repetida

- **WHEN** el edificio ya tiene un grupo con clave `pileta` y se crea otro llamado "Pileta"
- **THEN** la clave del nuevo se desempata con un sufijo numérico y las dos conviven

#### Scenario: Nombre del que no sale ninguna clave

- **WHEN** el nombre es "123" o "— —"
- **THEN** la respuesta es 422 nombrando el nombre y el grupo no se crea

#### Scenario: Clave explícita inválida

- **WHEN** un cliente de la API manda la clave `Pileta`, `pileta-1` o `1pileta`
- **THEN** la respuesta es 422 nombrando la clave, con el motivo de la regla, sin repetir el valor

#### Scenario: Renombrar no cambia la clave

- **WHEN** el titular renombra "Pileta" a "Pileta y solárium"
- **THEN** el nombre cambia y la clave sigue siendo `pileta`

### Requirement: El grupo "Generales" es obligatorio y abarca todo el edificio

Todo edificio SHALL tener un grupo "Generales", creado con el edificio, por coeficiente, con los
coeficientes de las unidades y con todas sus unidades, incluidas las que se den de alta después. Su
método, su modo de coeficientes y su alcance MUST NOT poder cambiarse, el grupo MUST NOT poder borrarse
y MUST NOT poder desactivarse.

#### Scenario: Una unidad nueva entra a Generales

- **WHEN** se da de alta una unidad en un edificio
- **THEN** la unidad forma parte de "Generales" sin ninguna acción adicional

#### Scenario: Cambiar el método de Generales

- **WHEN** se intenta cambiar el método de "Generales" a partes iguales
- **THEN** la respuesta es 422 y el grupo sigue por coeficiente

#### Scenario: Generales siempre activo

- **WHEN** se lee la lista de grupos de cualquier edificio
- **THEN** "Generales" está activo
