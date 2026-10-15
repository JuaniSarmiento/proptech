## Purpose

Garantiza que ningún dato de una administración llegue a otra aunque el código de la aplicación
tenga un error: la base misma filtra por administración, con roles separados y el tenant fijado por
transacción (R10, D-016, D-076, D-087).

## ADDED Requirements

### Requirement: Roles de la base separados por trabajo

El sistema SHALL usar tres roles de PostgreSQL distintos: el rol de arranque del contenedor, sólo para
crear los otros dos y para los respaldos; `proptech_migrador`, dueño de las tablas, para las
migraciones; y `proptech_app`, para la API y el worker. Ni `proptech_migrador` ni `proptech_app` MUST
ser superusuario ni tener `BYPASSRLS`, `CREATEROLE` o `CREATEDB`. `proptech_app` MUST NOT ser dueño de
ninguna tabla. La creación de los roles MUST ser idempotente y funcionar también sobre un volumen de
datos que ya existía antes de este cambio.

#### Scenario: Los atributos de cada rol

- **WHEN** se levanta el stack y se consulta el catálogo de roles
- **THEN** `proptech_migrador` y `proptech_app` existen, ninguno es superusuario ni tiene `BYPASSRLS`,
  y `proptech_app` no es dueño de ninguna tabla del esquema

#### Scenario: Arranque repetido

- **WHEN** el paso que crea los roles corre dos veces seguidas sobre la misma base
- **THEN** la segunda corrida termina sin error y los roles quedan con los mismos atributos

#### Scenario: Volumen anterior a este cambio

- **WHEN** se levanta el stack sobre un volumen con las tablas de los cambios 1a a 1d, creadas por el
  rol de arranque
- **THEN** las migraciones terminan con éxito como `proptech_migrador` y esas tablas pasan a ser suyas

### Requirement: Toda tabla de una administración está aislada por la base

Toda tabla con datos de una administración SHALL tener `administracion_id NOT NULL`, Row-Level
Security activada y forzada, y una política que exija, para leer y para escribir, que
`administracion_id` sea igual al tenant fijado en la transacción. Una fila que referencia a otra
(un complejo, una unidad, una persona) MUST pertenecer a la misma administración que la fila
referenciada.

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

#### Scenario: Una tabla nueva sin candado

- **WHEN** existe en el esquema una tabla con columna `administracion_id` sin RLS forzada, sin política
  o sin permisos para `proptech_app`
- **THEN** la suite de tests falla nombrando la tabla

### Requirement: Sin tenant fijado, cero filas y nunca un error

Una transacción sin tenant fijado, o con el tenant fijado como cadena vacía, SHALL leer cero filas de
toda tabla de una administración y MUST NOT poder escribir en ellas; en ningún caso la consulta MUST
terminar en error por la ausencia del valor.

#### Scenario: Tenant ausente

- **WHEN** `proptech_app` consulta una tabla de una administración sin haber fijado el tenant
- **THEN** recibe cero filas, sin error

#### Scenario: Tenant vacío

- **WHEN** el tenant se fija como cadena vacía y se consulta la misma tabla
- **THEN** recibe cero filas, sin error, igual que con el tenant ausente

### Requirement: El tenant vive sólo lo que dura la transacción

El tenant SHALL fijarse al abrir cada transacción, desde la identidad autenticada, y MUST valer sólo
dentro de esa transacción. Una conexión que vuelve al pool MUST NOT llevar el tenant a la transacción
siguiente, ni después de confirmar ni después de revertir.

#### Scenario: El pedido siguiente no hereda

- **WHEN** con un pool de una sola conexión una transacción con el tenant de A termina (confirmando o
  revirtiendo) y la siguiente se abre sin identidad
- **THEN** la segunda lee cero filas de A

#### Scenario: Una segunda transacción en el mismo pedido

- **WHEN** dentro de un pedido con el tenant de A se confirma una transacción y se abre otra
- **THEN** la segunda también tiene el tenant de A fijado

### Requirement: La administración nunca sale del cliente

El tenant SHALL salir sólo de la identidad autenticada. Un identificador de administración enviado
por el cliente en la ruta, la query, un encabezado o el cuerpo MUST NOT cambiar el tenant de la
transacción.

#### Scenario: Encabezado o parámetro con otra administración

- **WHEN** un pedido con identidad de A manda el id de B en un encabezado, en la query o en el cuerpo
- **THEN** la transacción sigue con el tenant de A y la respuesta no trae datos de B
