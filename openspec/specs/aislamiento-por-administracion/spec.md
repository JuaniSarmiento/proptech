# aislamiento-por-administracion Specification

## Purpose
Garantiza que ningún dato de una administración llegue a otra aunque el código de la aplicación
tenga un error: la base misma filtra por administración, con roles separados y el tenant fijado por
transacción (R10, D-016, D-076, D-087).

## Requirements

### Requirement: Roles de la base separados por trabajo

El sistema SHALL usar cuatro roles de PostgreSQL distintos: el rol de arranque del contenedor
(superusuario), sólo para crear y reparar los otros y como dueño de la auditoría; `proptech_migrador`,
dueño de las tablas de dominio, para las migraciones; `proptech_app`, para la API y el worker; y
`proptech_respaldo`, sólo para volcar la base. Ninguno de los tres roles del proyecto MUST ser
superusuario ni tener `CREATEROLE` o `CREATEDB`; `proptech_migrador` y `proptech_app` MUST NOT tener
`BYPASSRLS`; `proptech_app` MUST NOT ser dueño de ninguna tabla. `proptech_migrador` MUST poder crear
tablas en el esquema de la aplicación, y `proptech_app` MUST tener permisos sobre las tablas que ya
existían antes de este cambio. La creación de los roles MUST ser idempotente y funcionar también sobre
un volumen de datos que ya existía.

#### Scenario: Los atributos de cada rol

- **WHEN** se levanta el stack y se consulta el catálogo de roles
- **THEN** `proptech_migrador`, `proptech_app` y `proptech_respaldo` existen, ninguno es superusuario,
  sólo `proptech_respaldo` tiene `BYPASSRLS`, y `proptech_app` no es dueño de ninguna tabla

#### Scenario: Arranque repetido

- **WHEN** el paso que crea los roles corre dos veces seguidas sobre la misma base
- **THEN** la segunda corrida termina sin error y los roles quedan con los mismos atributos

#### Scenario: Volumen anterior a este cambio

- **WHEN** se levanta el stack sobre un volumen con las tablas de los cambios 1a a 1d, creadas por el
  rol de arranque
- **THEN** las migraciones terminan con éxito como `proptech_migrador`, esas tablas pasan a ser suyas y
  `proptech_app` puede leer y escribir `trabajos_hechos`

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
Ambas políticas MUST incluir `AND nullif(current_setting('app.administracion_id', true), '') IS NULL`:
con tenant fijado, la lectura extra no aporta filas ajenas. `app.invitacion_token` MUST llevar sólo el
hexadecimal del resumen SHA-256, nunca el token crudo. RLS filtra filas, no columnas.
El guardián MUST conservar la regla actual para políticas ordinarias (`current_setting` de dos
argumentos en `qual` y `with_check`) y admitir sólo las dos tuplas completas de D2: tabla, nombre,
`cmd = SELECT`, permisiva, roles, `qual` completo y `with_check = NULL`.
El vínculo MUST ser único por `(clerk_usuario_id, administracion_id)`, en ese orden, para resolver
sin tenant por identidad. `invitacion` MUST tener `vence NOT NULL`, un índice
`(administracion_id, persona_id)` para historial y listado de personal y el único parcial
`(administracion_id, persona_id) WHERE estado IN ('pendiente','enviada','fallida')` para una abierta
por persona. No se limpian invitaciones viejas en este cambio.

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

#### Scenario: Identidad o resumen junto con tenant

- **WHEN** `proptech_app` fija el tenant de A junto con la identidad de B, o el resumen hexadecimal de
  una invitación de B
- **THEN** las políticas adicionales no aportan filas de B y sólo se ve lo permitido por el tenant de A

#### Scenario: Reset de las tres variables del pool

- **WHEN** una conexión vuelve al pool tras commit, rollback o un `SET` accidental sin `LOCAL` de
  `app.administracion_id`, `app.identidad_clerk` o `app.invitacion_token`
- **THEN** el reset limpia las tres y la siguiente sesión no hereda ningún contexto; si la conexión
  está rota se invalida sin impedir su devolución

#### Scenario: La lectura por identidad no escribe

- **WHEN** sin tenant y con el id de Clerk fijado, `proptech_app` intenta actualizar o borrar una de
  esas personas, o insertar una nueva
- **THEN** la base no escribe nada

#### Scenario: Política extra fuera de lo permitido

- **WHEN** existe en el esquema una política sobre una tabla de una administración que no es la del
  tenant ni una de las dos tuplas completas de la lista blanca, incluso una `FOR SELECT` en otra
  tabla o con el nombre correcto pero otro `qual`
- **THEN** la suite de tests falla nombrando la tabla y la política

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
