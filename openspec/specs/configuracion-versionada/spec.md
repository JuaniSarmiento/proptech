# configuracion-versionada Specification

## Purpose
Define la configuración de intereses por mora (R03), de vencimiento (R03, R26, D-100) y de fondo de
reserva (R15) de cada edificio como menús cerrados versionados (D-010, D-080): cada cambio es una
versión nueva con fecha de vigencia, autor y fecha de alta, y ninguna versión anterior se modifica ni
se borra.

## Requirements

### Requirement: Menú cerrado con los rangos de los parámetros

Una versión de configuración SHALL tener tasa mensual (texto decimal de 0.00 a 10.00, hasta 2
decimales), días de gracia (entero de 0 a 31), forma de cálculo (`proporcional_por_dia` o
`mes_entero`) y porcentaje de fondo de reserva (texto decimal de 0.00 a 100.00, hasta 2 decimales). El
interés MUST ser siempre simple: no hay opción para capitalizar ni fórmula libre. Un valor fuera de
rango, un número JSON en lugar de texto, `NaN`, `Infinity` o un campo desconocido MUST rechazarse con
422 nombrando el campo, sin repetir el valor.

#### Scenario: Tasa como número

- **WHEN** la tasa llega como `3.5` (número JSON)
- **THEN** la respuesta es 422 nombrando la tasa

#### Scenario: Tasa fuera de rango

- **WHEN** la tasa es "10.01" o "-1.00"
- **THEN** la respuesta es 422 nombrando la tasa y el rango

#### Scenario: Pedido de capitalización

- **WHEN** el cuerpo trae un campo de capitalización o de fórmula
- **THEN** la respuesta es 422 por campo desconocido

### Requirement: Vencimiento único o doble, con día fijo

Una versión de configuración SHALL tener un día fijo de vencimiento, entero del 1 al 28, y una
modalidad de vencimiento: `unico` o `doble` (D-100). Con `doble`, la versión MUST tener además el día
del segundo vencimiento, entero posterior al primero y hasta 28, y el recargo del segundo vencimiento
como porcentaje (texto decimal, mayor que 0, dentro del rango de los parámetros, hasta 2 decimales).
Con `unico`, la versión MUST NOT tener segundo vencimiento ni recargo. La base MUST rechazar una
versión incoherente aunque la aplicación se equivoque. Correr el vencimiento de una liquidación
puntual no cambia la configuración: lo hace el cambio 7 al emitir.

#### Scenario: Pasar a doble vencimiento

- **WHEN** el titular crea una versión con doble vencimiento, primer día 10, segundo día 20 y recargo
  "5.00", sobre un edificio con vencimiento único
- **THEN** hay dos versiones, la anterior sigue única y sin recargo, y la nueva tiene los dos días y el
  recargo como texto

#### Scenario: Día de vencimiento fuera de rango

- **WHEN** el día de vencimiento es 0, 29 o "10" como texto
- **THEN** la respuesta es 422 nombrando el campo

#### Scenario: Doble vencimiento incompleto

- **WHEN** la modalidad es `doble` sin recargo, o con el segundo día igual o anterior al primero
- **THEN** la respuesta es 422 nombrando el campo

#### Scenario: Vencimiento incoherente por SQL

- **WHEN** conectado como `proptech_app` se inserta una versión `unico` con recargo, o `doble` sin
  segundo día
- **THEN** la base rechaza la escritura

### Requirement: Cada cambio es una versión nueva y las anteriores no se tocan

Cambiar la configuración SHALL crear una versión nueva con su fecha de vigencia, la persona que la
creó y el momento de alta; la versión anterior MUST quedar igual. Ningún rol de la aplicación MUST
poder modificar ni borrar una versión: ni por la API ni por SQL como `proptech_app`, tampoco después
de que el sistema vuelva a arrancar y el paso de roles corra otra vez. Sólo el titular MUST poder
crear una versión, y la creación MUST quedar auditada.

#### Scenario: Cambiar la tasa

- **WHEN** el titular crea una versión con tasa "4.00" vigente desde mañana
- **THEN** hay dos versiones, la de 3.00 sigue intacta, y la nueva tiene autor, fecha de alta y una
  fila de auditoría

#### Scenario: Editar una versión por SQL

- **WHEN** `proptech_app` intenta `UPDATE` o `DELETE` sobre una versión existente
- **THEN** la base lo rechaza y la versión sigue igual

#### Scenario: Editar una versión después de otro arranque

- **WHEN** el paso de roles y las migraciones corrieron dos veces seguidas y, con el trigger de la
  tabla deshabilitado sobre una copia, `proptech_app` intenta `UPDATE` o `DELETE` sobre una versión
- **THEN** la base lo rechaza por permisos y la versión sigue igual

#### Scenario: Un colaborador cambia la tasa

- **WHEN** un colaborador "editar" del edificio intenta crear una versión
- **THEN** la respuesta es 403 con el permiso faltante

### Requirement: Vigencias sin superposición ni retroactividad

Un edificio SHALL tener a lo sumo una versión por fecha de vigencia, y la base MUST impedir una
segunda aunque lleguen dos pedidos a la vez. La primera versión nace con el edificio, vigente desde el
día de alta. Una versión nueva MUST tener vigencia desde la fecha de hoy o posterior, en hora de
Mendoza; una vigencia pasada MUST rechazarse con 422. La configuración vigente para una fecha MUST ser
la versión con la mayor fecha de vigencia que no supere esa fecha; antes de la primera versión no hay
configuración vigente.

#### Scenario: Dos versiones para el mismo día

- **WHEN** se crea una versión vigente desde una fecha que ya tiene versión
- **THEN** la respuesta es 409 y queda una sola versión para ese día

#### Scenario: Dos pedidos simultáneos

- **WHEN** dos transacciones crean a la vez una versión para la misma fecha del mismo edificio
- **THEN** una se guarda y la otra falla por la restricción de unicidad, que la API traduce a 409

#### Scenario: Versión retroactiva

- **WHEN** se crea una versión vigente desde ayer
- **THEN** la respuesta es 422 y no se guarda nada

#### Scenario: Vigente para una fecha

- **WHEN** hay versiones vigentes desde el 1/11 y el 1/12 y se pide la vigente para el 15/11
- **THEN** la respuesta es la del 1/11

#### Scenario: Fecha anterior a la primera versión

- **WHEN** se pide la configuración vigente para una fecha anterior a la creación del edificio
- **THEN** la respuesta dice que no hay configuración vigente para esa fecha

### Requirement: El historial nombra al autor de cada versión

Listar las versiones de configuración de un edificio SHALL devolver, para cada versión, además de sus
campos y su `autor_id`, el nombre de la persona que la creó. La base ya garantiza que el autor es una
persona de la misma administración (FK compuesta de la versión hacia `persona`), así que el nombre
MUST venir siempre. El permiso para listar no cambia.

#### Scenario: Historial con dos autores

- **WHEN** el titular A crea la primera versión y el titular B, de la misma administración, la segunda,
  y alguien con permiso de lectura lista las versiones
- **THEN** cada versión trae el nombre de quien la creó

#### Scenario: Edificio recién creado

- **WHEN** el titular crea un edificio y lista sus versiones
- **THEN** hay una versión y trae el nombre del titular que creó el edificio
