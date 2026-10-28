## MODIFIED Requirements

### Requirement: La administración nunca sale del cliente

El tenant SHALL salir sólo de la identidad autenticada. Un identificador de administración enviado
por el cliente en la ruta, la query o el cuerpo MUST NOT cambiar el tenant de la transacción. La única
excepción es la administración elegida en el selector (D-099), que el servidor de la web manda en un
encabezado propio: la API MUST usarla sólo si la identidad verificada tiene ahí una persona vinculada
con asignación. En cualquier otro caso MUST responder sin leer datos de esa administración: 401 si la
identidad tiene acceso en alguna administración, y el 403 `sin_acceso` de `autenticacion-con-clerk` si
no lo tiene en ninguna, que prevalece sobre el 401.

#### Scenario: Encabezado o parámetro con otra administración

- **WHEN** un pedido con identidad de A manda el id de B en un encabezado cualquiera, en la query o en
  el cuerpo
- **THEN** la transacción sigue con el tenant de A y la respuesta no trae datos de B

#### Scenario: Selector con una administración ajena

- **WHEN** una identidad vinculada con asignación sólo en A manda el id de B en el encabezado del
  selector
- **THEN** la respuesta es 401 y no se leyó ninguna fila de B

#### Scenario: Selector ajeno de una identidad sin acceso

- **WHEN** una identidad sin acceso en ninguna administración manda el id de B en el encabezado del
  selector
- **THEN** la respuesta es el 403 `sin_acceso` y no se leyó ninguna fila de B
