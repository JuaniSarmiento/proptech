## MODIFIED Requirements

### Requirement: Sin identidad no hay acceso ni consultas

Todo endpoint de dominio SHALL exigir una identidad. Sin un token de sesión válido (ausente, mal
formado, con firma, algoritmo, vigencia u origen inválidos), MUST responder 401 sin ejecutar ninguna
consulta a la base. Con un token válido, la identidad MUST resolverse leyendo sólo el vínculo de esa
identidad de Clerk con una persona y sus asignaciones; si no hay persona vinculada en la administración
en uso, o no tiene ninguna asignación, la respuesta MUST ser el mismo 401, con el mismo cuerpo y los
mismos encabezados salvo el `X-Request-ID`, sin leer ningún dato de dominio. Los tests pueden seguir
inyectando la identidad.

#### Scenario: Pedido sin identidad

- **WHEN** se pide un complejo, una unidad o una asignación sin identidad
- **THEN** la respuesta es 401 y no se ejecutó ninguna sentencia SQL

#### Scenario: Token inválido

- **WHEN** se pide un complejo con un token de sesión vencido o firmado con otra clave
- **THEN** la respuesta es 401, idéntica a la de un pedido sin identidad, y no se ejecutó ninguna
  sentencia SQL

#### Scenario: Token válido sin vínculo

- **WHEN** se pide un complejo con un token válido de una identidad de Clerk sin persona vinculada
- **THEN** la respuesta es 401, idéntica a la de un pedido sin identidad, y no se leyó ninguna fila de
  complejo, unidad ni asignación
