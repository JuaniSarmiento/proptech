## ADDED Requirements

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
