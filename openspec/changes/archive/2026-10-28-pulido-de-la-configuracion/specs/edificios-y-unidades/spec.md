# Spec Delta

## ADDED Requirements

### Requirement: El edificio lleva su ubicación, su calle y sus pisos

Un edificio SHALL guardar la provincia, el departamento y la localidad elegidos del listado del
repositorio (capability `ubicacion-del-edificio`), la calle y el número como texto libre opcional, la
cantidad de pisos sobre planta baja y la cantidad de subsuelos. Un edificio nuevo MUST traer la
ubicación y las dos cantidades; un edificio creado antes de este cambio MUST poder tener la ubicación
sin completar, y en ese caso la puesta a punto MUST pedirla. La lectura MUST devolver los ids y los
nombres de los tres niveles, para que la pantalla no tenga que resolverlos.

#### Scenario: Alta con ubicación y pisos

- **WHEN** el titular crea un edificio con provincia Mendoza, departamento Capital, localidad Ciudad de
  Mendoza, calle y número "Alsina 123", 4 pisos y 1 subsuelo
- **THEN** el edificio queda con esos datos y la lectura devuelve los tres ids con sus nombres

#### Scenario: Alta sin ubicación

- **WHEN** el titular crea un edificio sin los tres ids de ubicación
- **THEN** la respuesta es 422 nombrando el campo que falta y el edificio no se crea

#### Scenario: Alta sin calle

- **WHEN** el titular crea un edificio sin calle y número
- **THEN** el alta es exitosa y la calle queda vacía

#### Scenario: Cantidades fuera de rango

- **WHEN** los pisos sobre planta baja son 61 o -1, o los subsuelos son 6 o -1
- **THEN** la respuesta es 422 nombrando el campo, sin el valor

#### Scenario: Cantidades como texto

- **WHEN** los pisos llegan como `"4"` en lugar de `4`
- **THEN** la respuesta es 422 nombrando el campo

### Requirement: El edificio se puede editar

El sistema SHALL permitir modificar el nombre, la ubicación, la calle y el número, la cantidad de pisos
y la cantidad de subsuelos de un edificio existente, con el mismo permiso que configurar el padrón y el
mismo orden de respuestas que el resto del módulo: fuera de alcance 404, sin permiso 403. Una edición
MUST poder cambiar un campo sin mandar los demás, MUST NOT poder anular un campo obligatorio y MUST NOT
poder cambiar la administración ni el estado de migración. La edición MUST quedar auditada.

#### Scenario: Corregir la localidad

- **WHEN** el titular edita un edificio cambiando sólo la localidad por otra del mismo departamento
- **THEN** la ubicación queda con la localidad nueva, el resto de los campos sigue igual y queda un
  registro de auditoría

#### Scenario: Completar la ubicación de un edificio viejo

- **WHEN** el titular edita un edificio migrado, que tenía la ubicación sin completar, con un trío
  coherente
- **THEN** la ubicación queda completa y el paso de puesta a punto correspondiente pasa a `hecho`

#### Scenario: Anular un campo obligatorio

- **WHEN** la edición manda el nombre o la cantidad de pisos en `null`
- **THEN** la respuesta es 422 nombrando el campo y nada cambia

#### Scenario: Editar un edificio fuera del alcance

- **WHEN** un colaborador de un edificio edita otro edificio de la misma administración
- **THEN** la respuesta es 404 y nada cambia

#### Scenario: Editar sin permiso de configurar el padrón

- **WHEN** un contador edita un edificio de su alcance
- **THEN** la respuesta es 403 y nada cambia

#### Scenario: Cambiar la administración por la edición

- **WHEN** la edición trae la administración o el estado de migración en el cuerpo
- **THEN** la respuesta es 422 y nada cambia

### Requirement: Bajar la cantidad de pisos con unidades arriba se rechaza diciendo cuáles

Reducir la cantidad de pisos sobre planta baja, o la de subsuelos, SHALL rechazarse con 422 si alguna
unidad del edificio quedaría en un piso que ya no existe, y el error MUST nombrar los identificadores
de esas unidades para que el administrador sepa qué corregir. Si ninguna unidad queda afuera, la
reducción MUST aceptarse.

#### Scenario: Bajar pisos con unidades arriba

- **WHEN** un edificio con unidades en el piso 4 se edita a 3 pisos
- **THEN** la respuesta es 422 nombrando la cantidad de pisos y los identificadores de las unidades del
  piso 4, y nada cambia

#### Scenario: Bajar subsuelos con cocheras abajo

- **WHEN** un edificio con cocheras en "SS1" se edita a 0 subsuelos
- **THEN** la respuesta es 422 nombrando los identificadores de esas cocheras

#### Scenario: Bajar pisos sin unidades arriba

- **WHEN** un edificio de 6 pisos con unidades hasta el 4 se edita a 4 pisos
- **THEN** la edición es exitosa

## MODIFIED Requirements

### Requirement: Unidades con tipo, coeficiente y superficie

Cada unidad SHALL tener un identificador único dentro de su edificio, uno de los cuatro tipos de
D-029 (departamento, cochera, baulera, local), un piso, un coeficiente y una superficie. El
coeficiente MUST llegar como texto decimal ASCII, mayor que 0 y hasta 1, con hasta 6 decimales; la
superficie, como texto decimal ASCII positivo con hasta 2 decimales. Un número JSON en lugar de texto
MUST rechazarse con 422, nombrando el campo y sin repetir el valor. La API MUST devolver estos valores
como texto, nunca como número.

El piso MUST salir del vocabulario de pisos de su edificio y MUST NOT ser texto libre: `PB`, un
subsuelo `SS1` a `SS<subsuelos>` o un número de `1` a la cantidad de pisos del edificio, con
coincidencia completa y sólo ASCII. Los cuatro tipos de unidad MUST elegir del mismo vocabulario. Un
piso que no está en el vocabulario del edificio MUST responder 422 nombrando el campo piso, sin repetir
el valor. El piso de una unidad migrada de antes de este cambio MUST poder estar sin completar, y
mientras lo esté la puesta a punto del edificio MUST pedirlo; una unidad nueva MUST traerlo.

#### Scenario: Alta de unidad válida

- **WHEN** el titular da de alta la unidad "1A", departamento, piso "1", coeficiente "0.100000",
  superficie "60.00" en un edificio de 4 pisos
- **THEN** la unidad queda en el edificio con esos valores y la respuesta los devuelve como texto

#### Scenario: Identificador repetido

- **WHEN** se da de alta una segunda unidad "1A" en el mismo edificio
- **THEN** la respuesta es 409 y queda una sola "1A"

#### Scenario: Mismo identificador en otro edificio

- **WHEN** se da de alta una unidad "1A" en otro edificio de la misma administración
- **THEN** el alta es exitosa

#### Scenario: Coeficiente como número

- **WHEN** el coeficiente llega como `0.1` (número JSON) o la superficie como `60.5`
- **THEN** la respuesta es 422 nombrando el campo, sin el valor

#### Scenario: Coeficiente fuera de forma

- **WHEN** el coeficiente es "0", "-0.1", "1.000001", "0.1234567", "0.1\n" o trae un dígito no ASCII
- **THEN** la respuesta es 422 nombrando el campo

#### Scenario: Tipo desconocido

- **WHEN** la unidad tiene tipo "quincho"
- **THEN** la respuesta es 422 nombrando el campo tipo

#### Scenario: Piso de planta baja y de subsuelo

- **WHEN** en un edificio de 4 pisos y 1 subsuelo se dan de alta un local en "PB" y una cochera en
  "SS1"
- **THEN** las dos altas son exitosas

#### Scenario: Piso que el edificio no tiene

- **WHEN** en un edificio de 4 pisos y 1 subsuelo se da de alta una unidad en el piso "5", en "SS2" o
  en "0"
- **THEN** la respuesta es 422 nombrando el campo piso, sin el valor, y la unidad no se crea

#### Scenario: Piso como texto libre

- **WHEN** el piso llega como "Entrepiso", "pb", " 1", "1°", "SS" o con un dígito no ASCII
- **THEN** la respuesta es 422 nombrando el campo piso

#### Scenario: Unidad nueva sin piso

- **WHEN** el alta de una unidad no trae el piso, o lo trae en `null`
- **THEN** la respuesta es 422 nombrando el campo piso

#### Scenario: Corregir el piso de una unidad migrada

- **WHEN** una unidad migrada tiene el piso sin completar y el titular la edita eligiendo "SS1"
- **THEN** la unidad queda en "SS1" y la edición queda auditada como hasta ahora

#### Scenario: El piso no se sale del vocabulario por SQL

- **WHEN** conectado como `proptech_app` se inserta o actualiza por SQL una unidad con piso "Entrepiso"
- **THEN** la base rechaza la escritura

### Requirement: Resumen y puesta a punto del edificio

El resumen de un edificio SHALL informar su nombre, su ubicación (los tres niveles con id y nombre, o
sin completar), su calle y número, su cantidad de pisos y de subsuelos, la cantidad de unidades, su
estado de migración, el informe de coeficientes de R01 y los siete pasos de puesta a punto, cada uno
`hecho` o `falta`, más `listo_para_liquidar`, que MUST ser verdadero sólo si los siete están `hecho`.
El criterio de cada paso MUST vivir en el servidor y MUST ser éste:

1. **ubicación**: el edificio tiene los tres ids de ubicación completos y ninguna unidad con el piso sin
   completar.
2. **unidades**: el edificio tiene al menos una unidad.
3. **coeficientes**: el edificio tiene unidades y el informe de R01 de "Generales" está `ok` o
   `advertencia`.
4. **grupos**: todo grupo parcial activo tiene al menos una unidad y todo grupo con coeficientes propios
   tiene su informe `ok` o `advertencia`.
5. **categorías**: el edificio tiene al menos una categoría activa.
6. **intereses y vencimiento**: hay una versión de configuración vigente hoy, en hora de Mendoza.
7. **saldos previos**: el estado de migración no es `pendiente`.

Leer el resumen MUST exigir el mismo permiso que leer la configuración del edificio, con las mismas
respuestas fuera de alcance (404) y sin permiso (403). Montos y proporciones MUST viajar como texto.

#### Scenario: Edificio recién creado

- **WHEN** el titular pide el resumen de un edificio recién creado, sin unidades
- **THEN** recibe nombre, ubicación completa, 0 unidades, estado `pendiente`, el paso ubicación en
  `hecho` (un edificio nuevo nace con ubicación, y sin unidades no hay piso que falte), los pasos
  unidades, coeficientes y saldos previos en `falta`, los pasos grupos, categorías e intereses y
  vencimiento en `hecho` (nacen con los valores de los parámetros, D-042), y `listo_para_liquidar` falso

#### Scenario: Edificio migrado sin ubicación

- **WHEN** el titular pide el resumen de un edificio creado antes de este cambio, con la ubicación sin
  completar
- **THEN** el paso ubicación está `falta`, enlaza a la pantalla donde se completa, y
  `listo_para_liquidar` es falso

#### Scenario: Unidad migrada con el piso sin completar

- **WHEN** el edificio tiene la ubicación completa pero una unidad con el piso sin completar
- **THEN** el paso ubicación está `falta` y el resumen dice cuántas unidades tienen el piso sin
  completar

#### Scenario: Coeficientes en advertencia

- **WHEN** las unidades de un edificio suman 0,9999
- **THEN** el paso coeficientes está `hecho` y el informe dice `advertencia` con la diferencia

#### Scenario: Coeficientes fuera de tolerancia

- **WHEN** las unidades de un edificio suman 0,9998
- **THEN** el paso coeficientes está `falta` y `listo_para_liquidar` es falso

#### Scenario: Grupo parcial vacío

- **WHEN** el edificio tiene un grupo parcial activo sin unidades
- **THEN** el paso grupos está `falta`

#### Scenario: Grupo parcial vacío pero desactivado

- **WHEN** el único grupo parcial sin unidades está desactivado
- **THEN** el paso grupos está `hecho`

#### Scenario: Edificio listo para liquidar

- **WHEN** el edificio tiene ubicación completa, todas sus unidades con piso, unidades que suman 1,
  grupos completos, una categoría activa, una versión vigente y estado `sin_saldos_previos`
- **THEN** los siete pasos están `hecho` y `listo_para_liquidar` es verdadero

#### Scenario: El vecino pide el resumen

- **WHEN** un vecino pide el resumen de su edificio
- **THEN** la respuesta es 403, como para el resto de la configuración
