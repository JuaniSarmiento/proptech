## Purpose

Define los grupos de reparto de cada edificio (R01): quién paga cada gasto, con qué método y entre qué
unidades, y cómo se informa si los coeficientes cierran, sin que un grupo pueda incluir unidades de
otro edificio ni de otra administración.

## ADDED Requirements

### Requirement: El grupo "Generales" es obligatorio y abarca todo el edificio

Todo edificio SHALL tener un grupo "Generales", creado con el edificio, por coeficiente y con todas
sus unidades, incluidas las que se den de alta después. Su método y su alcance MUST NOT poder
cambiarse, y el grupo MUST NOT poder borrarse.

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

### Requirement: Informe de coeficientes según R01

Para el grupo "Generales", la API SHALL informar siempre la suma de los coeficientes, la diferencia con
1 y un estado: `ok` si la suma es exactamente 1, `advertencia` si se aparta hasta 0,0001 inclusive, y
`fuera_de_tolerancia` si se aparta más. La suma y la diferencia MUST calcularse en `Decimal` y
devolverse como texto. Cargar o editar unidades MUST NOT bloquearse por la suma: el bloqueo lo hace el
control antes de emitir del cambio 7 (R34). Los grupos parciales se informan según la respuesta a P24,
que este requisito no fija.

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
