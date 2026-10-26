# Spec Delta

## ADDED Requirements

### Requirement: El SQL de cada módulo sólo nombra sus tablas

Las sentencias SQL escritas en el código de un módulo de `proptech_core` SHALL nombrar sólo tablas de ese
módulo, salvo excepciones declaradas por archivo y tabla, con su motivo. El test MUST nombrar el archivo
y la tabla ajena, y cada excepción MUST compararse por archivo y tabla completos.

#### Scenario: El código de hoy pasa con sus excepciones

- **WHEN** corre el escaneo sobre el árbol con el libro construido
- **THEN** pasa, con `administracion` como tabla de `acceso` y las excepciones de
  `complejos/aplicacion/escritura.py` (`asignacion_rol`), `complejos/aplicacion/lectura.py` (`persona`)
  y `complejos/aplicacion/ejemplo.py` (`administracion`, `persona`, `asignacion_rol`)

#### Scenario: Una tabla sin dueño declarado

- **WHEN** en una copia un módulo nombra en SQL una tabla que no figura en el mapa de dueños
- **THEN** el test falla nombrando esa tabla

#### Scenario: La liquidación nombra una tabla del libro

- **WHEN** en una copia se agrega a `liquidacion/aplicacion/` un `SELECT ... FROM movimiento`
- **THEN** el test falla nombrando ese archivo y `movimiento`

#### Scenario: La cuenta corriente nombra una tabla de complejos

- **WHEN** en una copia se agrega a `cuenta_corriente/aplicacion/` un `JOIN unidad`
- **THEN** el test falla nombrando ese archivo y `unidad`

#### Scenario: Sin la excepción de lectura

- **WHEN** se saca la excepción de `lectura.py`
- **THEN** el test falla nombrando `complejos/aplicacion/lectura.py` y `persona`
