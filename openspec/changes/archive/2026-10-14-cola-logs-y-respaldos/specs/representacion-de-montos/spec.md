## ADDED Requirements

### Requirement: Un monto se puede copiar y serializar sin perder la validación

Un monto SHALL poder copiarse (`copy.copy`, `copy.deepcopy`, `model_copy(deep=True)` de pydantic) y
serializarse con `pickle` en cualquier protocolo. Como es inmutable, una copia MUST devolver el mismo
objeto. La serialización MUST reconstruir el monto desde su texto, de modo que la reconstrucción pase
por la misma validación que la construcción y un contenido inválido falle con el error de monto
inválido.

#### Scenario: Ida y vuelta por pickle

- **WHEN** se serializa un monto con `pickle` en cada protocolo disponible y se lo vuelve a cargar
- **THEN** el resultado es un monto igual al original, con el mismo texto

#### Scenario: Copia superficial y profunda

- **WHEN** se copia un monto con `copy.copy` y con `copy.deepcopy`
- **THEN** las dos devuelven el mismo objeto, sin error

#### Scenario: Copia profunda de un modelo con montos

- **WHEN** un modelo de pydantic con un campo de monto se copia con `model_copy(deep=True)` y se
  serializa y carga con `pickle`
- **THEN** las dos operaciones terminan sin error y el monto conserva su valor

#### Scenario: Pickle con un monto inválido

- **WHEN** se carga un pickle armado a mano cuyo texto de monto es inválido (por ejemplo `"1e3"`)
- **THEN** la carga falla con el error de monto inválido
