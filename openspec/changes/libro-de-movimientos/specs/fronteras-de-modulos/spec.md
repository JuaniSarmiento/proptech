# Spec Delta

## ADDED Requirements

### Requirement: El SQL de cada módulo sólo nombra sus tablas

El SQL de cada módulo de `proptech_core` SHALL nombrar sólo tablas propias, salvo excepciones por archivo y tabla completos con motivo. El test MUST nombrar archivo y tabla ajena, ignorar mayúsculas y excluir `FOR UPDATE OF` y funciones en FROM. En `proptech_api` y `proptech_worker` MUST prohibir SQL directo sobre tablas del libro y `candado_de_cuenta`; sus consumidores usan `cuenta_corriente.aplicacion`.

#### Scenario: El código de hoy pasa con sus excepciones

- **WHEN** el ensayo del consumidor invoca la operación y corre el escaneo sobre el árbol con el libro construido
- **THEN** pasa, con `administracion` como tabla de `acceso` y las excepciones de
  `complejos/aplicacion/escritura.py` (`asignacion_rol`), `complejos/aplicacion/lectura.py` (`persona`)
  y `complejos/aplicacion/ejemplo.py` (`administracion`, `persona`, `asignacion_rol`)

#### Scenario: Una tabla sin dueño declarado

- **WHEN** el ensayo del consumidor invoca la operación y en una copia un módulo nombra en SQL una tabla que no figura en el mapa de dueños
- **THEN** el test falla nombrando esa tabla

#### Scenario: La liquidación nombra una tabla del libro

- **WHEN** el ensayo del consumidor invoca la operación y en una copia se agrega a `liquidacion/aplicacion/` un `SELECT ... FROM movimiento`
- **THEN** el test falla nombrando ese archivo y `movimiento`

#### Scenario: La cuenta corriente nombra una tabla de complejos

- **WHEN** el ensayo del consumidor invoca la operación y en una copia se agrega a `cuenta_corriente/aplicacion/` un `JOIN unidad`
- **THEN** el test falla nombrando ese archivo y `unidad`

#### Scenario: Sin la excepción de lectura

- **WHEN** el ensayo del consumidor invoca la operación y se saca la excepción de `lectura.py`
- **THEN** el test falla nombrando `complejos/aplicacion/lectura.py` y `persona`

#### Scenario: SQL del libro fuera del módulo

- **WHEN** el ensayo agrega `select * from movimiento` en `proptech_api` o `proptech_worker`
- **THEN** el test falla nombrando archivo y tabla, aun con SQL en minúsculas

#### Scenario: OF y funciones no son tablas

- **WHEN** el ensayo escanea `FOR UPDATE OF i`, `FROM unnest(...)` y `FROM generate_series(...)`
- **THEN** no denuncia OF ni esos nombres de función como tablas sin dueño
