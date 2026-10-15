# autorizacion-por-rol Specification

## Purpose
Define quién puede ver qué complejo y qué unidad dentro de su administración y quién puede hacer cada
acción sensible, con 404 fuera de alcance y 403 sin permiso, según D-037, D-076 y la matriz de D-096.

## Requirements

### Requirement: Sin identidad no hay acceso ni consultas

Todo endpoint de dominio SHALL exigir una identidad. Sin identidad, MUST responder 401 sin ejecutar
ninguna consulta a la base. Hasta que exista el login (cambio 2b), la identidad de producción MUST
faltar siempre; sólo los tests pueden inyectarla.

#### Scenario: Pedido sin identidad

- **WHEN** se pide un complejo, una unidad o una asignación sin identidad
- **THEN** la respuesta es 401 y no se ejecutó ninguna sentencia SQL

### Requirement: Alcance por edificio según el rol

Dentro de su administración, cada persona SHALL ver sólo los complejos y unidades de su alcance: el
titular, todos; el colaborador, los complejos asignados; el consejo, su complejo; el vecino, sus
unidades y el complejo de cada una. El rol y el alcance MUST leerse de las asignaciones guardadas en la
base, nunca de lo que diga el pedido.

#### Scenario: Colaborador en un edificio no asignado

- **WHEN** un colaborador pide un complejo de su administración que no tiene asignado
- **THEN** la respuesta es 404

#### Scenario: Vecino en la unidad de otro vecino

- **WHEN** un vecino pide una unidad de su mismo complejo que no es suya
- **THEN** la respuesta es 404

#### Scenario: Consejo en otro edificio

- **WHEN** un miembro del consejo pide un complejo distinto del suyo
- **THEN** la respuesta es 404

#### Scenario: Titular

- **WHEN** el titular pide cualquier complejo o unidad de su administración
- **THEN** la respuesta es 200 con el dato

### Requirement: Fuera de alcance es indistinguible de inexistente

Un recurso de otra administración, uno fuera del alcance del rol y uno que no existe SHALL responder
igual: mismo código 404, mismo cuerpo y mismos encabezados, salvo el `X-Request-ID`.

#### Scenario: Id de otra administración contra id inexistente

- **WHEN** la misma identidad pide un complejo de otra administración (id con formato válido) y un
  complejo que no existe
- **THEN** las dos respuestas son 404 con cuerpo y encabezados idénticos salvo el `X-Request-ID`

### Requirement: Permiso por acción según D-096

Cada acción sensible SHALL estar permitida sólo a los roles que marca la matriz de D-096; el
colaborador con nivel "ver" MUST NOT poder ninguna. Dentro del alcance y sin el permiso, la respuesta
MUST ser 403 con el nombre del permiso faltante. Fuera del alcance, la respuesta MUST ser 404 aunque
tampoco tenga el permiso: el alcance se evalúa primero. Una acción que no está en la matriz MUST
negarse.

#### Scenario: La matriz completa

- **WHEN** se evalúa cada acción de la matriz de D-096 para titular, colaborador "editar", colaborador
  "ver", consejo y vecino
- **THEN** el resultado coincide celda por celda con la matriz

#### Scenario: Colaborador asigna un edificio

- **WHEN** un colaborador con nivel "editar" intenta asignar un edificio a una persona en un complejo
  que tiene asignado
- **THEN** la respuesta es 403 con el permiso faltante `invitar_usuarios_y_asignar_edificios`

#### Scenario: Sin permiso y fuera de alcance

- **WHEN** un colaborador intenta asignar un edificio en un complejo que no tiene asignado
- **THEN** la respuesta es 404, no 403

#### Scenario: Titular asigna un edificio

- **WHEN** el titular asigna un complejo de su administración a un colaborador de su administración
- **THEN** la asignación queda guardada y el colaborador pasa a ver ese complejo

#### Scenario: Asignar a una persona de otra administración

- **WHEN** el titular de A intenta asignar un complejo a una persona de B (id con formato válido)
- **THEN** la respuesta es 404 y no queda nada escrito
