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

### Requirement: Permisos de configuración del edificio

Las acciones de configuración SHALL sumarse a la matriz de D-096 con este reparto: crear un edificio,
crear una versión de configuración de intereses y fondo de reserva, y confirmar "sin saldos previos",
sólo el titular; dar de alta y editar unidades, grupos y categorías, el titular y el colaborador con
nivel "editar" en ese edificio. El colaborador "ver", el consejo y el vecino MUST NOT poder ninguna.
Crear un edificio, que todavía no tiene alcance, MUST evaluar sólo el permiso: sin él, 403 con el
permiso faltante.

#### Scenario: La matriz de configuración completa

- **WHEN** se evalúa cada acción de configuración para titular, colaborador "editar", colaborador
  "ver", consejo y vecino
- **THEN** el resultado coincide celda por celda con el reparto de este requisito

#### Scenario: Un colaborador crea un edificio

- **WHEN** un colaborador "editar" intenta crear un edificio
- **THEN** la respuesta es 403 con el permiso faltante y no se crea nada

#### Scenario: Un colaborador "ver" crea una categoría

- **WHEN** un colaborador "ver" del edificio intenta crear una categoría
- **THEN** la respuesta es 403 con el permiso faltante

#### Scenario: El consejo edita una unidad de su edificio

- **WHEN** el consejo del edificio intenta editar una unidad de ese edificio
- **THEN** la respuesta es 403 con el permiso faltante y la unidad no cambia
