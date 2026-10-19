# grupos-de-reparto Specification

## Purpose
Define los grupos de reparto de cada edificio (R01): quién paga cada gasto, con qué método, entre qué
unidades y con qué coeficientes (D-100), y cómo se informa si los coeficientes cierran, sin que un
grupo pueda incluir unidades de otro edificio ni de otra administración.

## Requirements

### Requirement: El grupo "Generales" es obligatorio y abarca todo el edificio

Todo edificio SHALL tener un grupo "Generales", creado con el edificio, por coeficiente, con los
coeficientes de las unidades y con todas sus unidades, incluidas las que se den de alta después. Su
método, su modo de coeficientes y su alcance MUST NOT poder cambiarse, y el grupo MUST NOT poder
borrarse.

#### Scenario: Una unidad nueva entra a Generales

- **WHEN** se da de alta una unidad en un edificio
- **THEN** la unidad forma parte de "Generales" sin ninguna acción adicional

#### Scenario: Cambiar el método de Generales

- **WHEN** se intenta cambiar el método de "Generales" a partes iguales
- **THEN** la respuesta es 422 y el grupo sigue por coeficiente

### Requirement: Grupos con método y unidades del mismo edificio

Un grupo SHALL tener una clave (`^[a-z][a-z0-9_]{0,39}$`, ASCII, coincidencia completa), un nombre de
hasta 80 caracteres, un método (`coeficiente`, `superficie` o `partes_iguales`) y sus unidades. Cada
unidad de un grupo MUST pertenecer al mismo edificio y a la misma administración que el grupo; la base
MUST rechazarlo aunque la aplicación se equivoque. Una unidad MUST figurar una sola vez en un grupo.
Una clave repetida dentro del edificio MUST responder 409.

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

### Requirement: Dos modos de coeficientes en los grupos parciales

Un grupo parcial por coeficiente SHALL tener un modo de coeficientes (D-100, P24): `renormalizado`,
por defecto, en el que cada unidad usa su coeficiente general dividido por la suma de los generales de
las unidades del grupo, o `propios`, en el que cada unidad del grupo lleva su propio coeficiente
(texto decimal ASCII, mayor que 0 y hasta 1, hasta 6 decimales) y la suma dentro del grupo se valida
como en R01. Un grupo por superficie o en partes iguales MUST ser `renormalizado`. Un miembro de un
grupo `renormalizado` MUST NOT llevar coeficiente propio y uno de un grupo `propios` MUST llevarlo; la
base MUST rechazar la incoherencia aunque la aplicación se equivoque. Cambiar el modo de un grupo MUST
reemplazar sus miembros en una sola operación, con la forma del modo nuevo.

#### Scenario: Grupo parcial renormalizado

- **WHEN** el titular crea "Ascensor" con cuatro unidades sin coeficientes propios
- **THEN** el grupo queda `renormalizado` y no informa una suma propia

#### Scenario: Coeficiente propio en un grupo renormalizado

- **WHEN** conectado como `proptech_app` se inserta por SQL un miembro con coeficiente en un grupo
  `renormalizado`, o uno sin coeficiente en un grupo `propios`
- **THEN** la base rechaza la escritura

#### Scenario: Cambiar el modo por SQL con miembros

- **WHEN** conectado como `proptech_app` se cambia por SQL el modo de un grupo que tiene miembros
- **THEN** la base rechaza la escritura y el grupo y sus miembros quedan iguales

#### Scenario: Cambiar el modo de un grupo

- **WHEN** el titular pasa "Cocheras" de `renormalizado` a `propios` mandando sus unidades con
  coeficientes que suman "1.000000"
- **THEN** el grupo queda `propios`, con esos coeficientes, y su informe dice estado `ok`

### Requirement: Informe de coeficientes según R01

Para el grupo "Generales" y para cada grupo con coeficientes `propios`, la API SHALL informar siempre
la suma de los coeficientes, la diferencia con 1 y un estado: `ok` si la suma es exactamente 1,
`advertencia` si se aparta hasta 0,0001 inclusive, y `fuera_de_tolerancia` si se aparta más. La suma y
la diferencia MUST calcularse en `Decimal`, con la misma función que usa el validador de la semilla, y
devolverse como texto. Cargar o editar unidades o grupos MUST NOT bloquearse por la suma: el bloqueo
lo hace el control "Coeficientes fuera de tolerancia" antes de emitir, en el cambio 7 (R34).

#### Scenario: Suma exacta

- **WHEN** las unidades del edificio de ejemplo suman 1.000000
- **THEN** el informe dice suma "1.000000", diferencia "0.000000", estado `ok`

#### Scenario: Borde inferior de la tolerancia

- **WHEN** los coeficientes suman 0.9999
- **THEN** el estado es `advertencia` con diferencia "-0.000100"

#### Scenario: Borde superior de la tolerancia

- **WHEN** los coeficientes suman 1.0001
- **THEN** el estado es `advertencia` con diferencia "0.000100"

#### Scenario: Fuera de tolerancia

- **WHEN** los coeficientes suman 0.9998 o 1.0002
- **THEN** el estado es `fuera_de_tolerancia`, con la diferencia, y el alta que llevó a esa suma
  igual quedó guardada

#### Scenario: Edificio sin unidades

- **WHEN** un edificio recién creado no tiene unidades
- **THEN** el informe dice suma "0.000000" y estado `fuera_de_tolerancia`

#### Scenario: Grupo con coeficientes propios que no suman 1

- **WHEN** un grupo `propios` tiene miembros cuyos coeficientes suman 0.800000
- **THEN** el grupo queda guardado y su informe dice suma "0.800000", diferencia "-0.200000" y estado
  `fuera_de_tolerancia`
