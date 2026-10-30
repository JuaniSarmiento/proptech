## ADDED Requirements

### Requirement: La lista de pisos de la unidad va en orden de altura

La lista de pisos que la web ofrece al dar de alta o editar una unidad SHALL traer, de arriba hacia
abajo, los subsuelos del más profundo al más cercano a la planta baja (`SS<subsuelos>` … `SS1`), después
`PB`, y después los pisos de `1` a la cantidad de pisos del edificio. La opción vacía inicial MUST seguir
siendo la primera. Este orden es sólo el de la lista; el conjunto de valores válidos y la validación
del servidor no cambian.

#### Scenario: Edificio con dos subsuelos

- **WHEN** se abre la lista de pisos de un edificio de 4 pisos y 2 subsuelos
- **THEN** las opciones son, en este orden: la vacía, `SS2`, `SS1`, `PB`, `1`, `2`, `3`, `4`

#### Scenario: Edificio con un subsuelo

- **WHEN** se abre la lista de pisos de un edificio de 4 pisos y 1 subsuelo
- **THEN** las opciones son, en este orden: la vacía, `SS1`, `PB`, `1`, `2`, `3`, `4`

#### Scenario: Edificio sin subsuelos

- **WHEN** se abre la lista de pisos de un edificio de 4 pisos y 0 subsuelos
- **THEN** las opciones son, en este orden: la vacía, `PB`, `1`, `2`, `3`, `4`
