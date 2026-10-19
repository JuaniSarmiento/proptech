## ADDED Requirements

### Requirement: Ninguna ruta de dominio queda fuera del barrido

El barrido de rutas protegidas SHALL ver toda ruta que la app registra, sin depender de cómo se montó:
con el prefijo en el router, con `include_router(prefix=...)`, con `add_api_route` sobre la app o
anidada en otro router. Toda ruta que no sea pública a propósito MUST figurar en la lista que el
barrido prueba, y toda ruta de esa lista MUST responder 401 sin identidad y sin tocar la base.

#### Scenario: Ruta montada con prefijo de inclusión

- **WHEN** se agrega a la app un router sin prefijo propio montado con `include_router(prefix="/api")`,
  con una ruta que no está en la lista del barrido
- **THEN** la suite de tests falla nombrando esa ruta

#### Scenario: Ruta agregada directo a la app

- **WHEN** se agrega una ruta con `add_api_route` directo sobre la app
- **THEN** la suite de tests falla nombrando esa ruta

#### Scenario: Las rutas de hoy siguen cubiertas

- **WHEN** corre el barrido sobre la app sin cambios
- **THEN** encuentra exactamente las rutas de la lista, incluidas las tres del cambio 2a

## MODIFIED Requirements

### Requirement: Permiso por acción según D-096

Cada acción sensible SHALL estar permitida sólo a los roles que marca la matriz de D-096; el
colaborador con nivel "ver" MUST NOT poder ninguna acción de escritura. Dentro del alcance y sin el
permiso, la respuesta MUST ser 403 con el nombre del permiso faltante. Fuera del alcance, la respuesta
MUST ser 404 aunque tampoco tenga el permiso: el alcance se evalúa primero. Una acción que no está en
la matriz MUST negarse.

La matriz SHALL incluir las acciones de configuración del edificio con este reparto: crear un
edificio, crear una versión de configuración de intereses, vencimiento y fondo de reserva, y confirmar
"sin saldos previos", sólo el titular; dar de alta y editar unidades, grupos y categorías, el titular
y el colaborador con nivel "editar" en ese edificio; leer la configuración del edificio (padrón,
resumen, grupos, categorías, configuración vigente y versiones), el titular, el colaborador con
cualquier nivel en ese edificio y el consejo de ese edificio. El vecino MUST NOT poder ninguna de
estas acciones, tampoco leer la configuración: ve sólo sus unidades y el complejo de cada una. Crear
un edificio, que todavía no tiene alcance, MUST evaluar sólo el permiso: sin él, 403 con el permiso
faltante.

#### Scenario: La matriz completa

- **WHEN** se evalúa cada acción de la matriz de D-096, incluidas las de configuración y la de lectura
  de la configuración, para titular, colaborador "editar", colaborador "ver", consejo y vecino
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

#### Scenario: Un colaborador crea un edificio

- **WHEN** un colaborador "editar" intenta crear un edificio
- **THEN** la respuesta es 403 con el permiso faltante y no se crea nada

#### Scenario: Un colaborador "ver" crea una categoría

- **WHEN** un colaborador "ver" del edificio intenta crear una categoría
- **THEN** la respuesta es 403 con el permiso faltante

#### Scenario: El consejo edita una unidad de su edificio

- **WHEN** el consejo del edificio intenta editar una unidad de ese edificio
- **THEN** la respuesta es 403 con el permiso faltante y la unidad no cambia

#### Scenario: El consejo lee el padrón

- **WHEN** el consejo del edificio pide el padrón de unidades de ese edificio
- **THEN** la respuesta es 200 con las unidades y el informe de coeficientes

#### Scenario: El vecino pide la configuración de su edificio

- **WHEN** un vecino pide el padrón, los grupos, las categorías, el resumen o la configuración del
  complejo donde tiene su unidad
- **THEN** la respuesta es 403 con el permiso faltante `ver_configuracion_del_edificio` y no trae
  ningún dato de otras unidades

#### Scenario: El vecino pide la configuración de otro edificio

- **WHEN** un vecino pide el padrón de un complejo de su administración donde no tiene unidades
- **THEN** la respuesta es 404, no 403

#### Scenario: El vecino ve su unidad

- **WHEN** un vecino pide su propia unidad
- **THEN** la respuesta es 200 con su identificador, tipo, piso, coeficiente y superficie, como texto
