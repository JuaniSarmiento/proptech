## MODIFIED Requirements

### Requirement: Toda tabla de una administración está aislada por la base

Toda tabla con datos de una administración SHALL tener `administracion_id NOT NULL`, Row-Level
Security activada y forzada, y una política que exija, para leer y para escribir, que
`administracion_id` sea igual al tenant fijado en la transacción. Una fila que referencia a otra
(un complejo, una unidad, una persona) MUST pertenecer a la misma administración que la fila
referenciada. Toda tabla que cuelga de un edificio MUST llevar `complejo_id NOT NULL` con clave foránea
compuesta `(administracion_id, complejo_id)`. La única política adicional permitida es una de **sólo
lectura** que deja ver las filas de `persona` (o de `invitacion`) cuyo id de Clerk (o resumen de token)
es igual al valor fijado en la transacción para la identidad ya verificada (o el token presentado); esa
política MUST NOT permitir insertar, actualizar ni borrar, y sin ese valor fijado MUST dar cero filas.

#### Scenario: Otra administración no ve nada

- **WHEN** con el tenant de la administración A se consulta un complejo de la administración B por su
  id, con formato válido
- **THEN** la consulta devuelve cero filas

#### Scenario: Escritura cruzada rechazada

- **WHEN** con el tenant de A se inserta o se actualiza una fila con `administracion_id` de B
- **THEN** la base rechaza la escritura y no queda nada escrito

#### Scenario: Referencia cruzada rechazada

- **WHEN** con el tenant de A se crea una unidad que apunta a un complejo de B
- **THEN** la base rechaza la escritura

#### Scenario: Referencia a otro edificio rechazada

- **WHEN** con el tenant de A se crea una asignación de vecino que apunta a una unidad de un complejo
  distinto del que dice la fila
- **THEN** la base rechaza la escritura

#### Scenario: Una tabla nueva sin candado

- **WHEN** existe en el esquema una tabla con columna `administracion_id` sin RLS forzada, sin política,
  sin permisos para `proptech_app`, o con columna `complejo_id` que admite nulos o no tiene la FK
  compuesta con la administración (fuera de la lista explícita de excepciones)
- **THEN** la suite de tests falla nombrando la tabla

#### Scenario: Lectura por identidad verificada

- **WHEN** sin tenant y con el id de Clerk de una identidad fijado en la transacción, `proptech_app`
  lee `persona`
- **THEN** recibe sólo las personas vinculadas a ese id, de cualquier administración, y cero filas de
  cualquier otra tabla

#### Scenario: La lectura por identidad no escribe

- **WHEN** sin tenant y con el id de Clerk fijado, `proptech_app` intenta actualizar o borrar una de
  esas personas, o insertar una nueva
- **THEN** la base no escribe nada

#### Scenario: Política extra fuera de lo permitido

- **WHEN** existe en el esquema una política sobre una tabla de una administración que no es la del
  tenant ni una de sólo lectura de las dos permitidas
- **THEN** la suite de tests falla nombrando la tabla y la política

### Requirement: La administración nunca sale del cliente

El tenant SHALL salir sólo de la identidad autenticada. Un identificador de administración enviado
por el cliente en la ruta, la query o el cuerpo MUST NOT cambiar el tenant de la transacción. La única
excepción es la administración elegida en el selector (D-099), que el servidor de la web manda en un
encabezado propio: la API MUST usarla sólo si la identidad verificada tiene ahí una persona vinculada
con asignación, y en cualquier otro caso MUST responder 401 sin leer datos de esa administración.

#### Scenario: Encabezado o parámetro con otra administración

- **WHEN** un pedido con identidad de A manda el id de B en un encabezado cualquiera, en la query o en
  el cuerpo
- **THEN** la transacción sigue con el tenant de A y la respuesta no trae datos de B

#### Scenario: Selector con una administración ajena

- **WHEN** una identidad vinculada sólo en A manda el id de B en el encabezado del selector
- **THEN** la respuesta es 401 y no se leyó ninguna fila de B
