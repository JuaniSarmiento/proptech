## ADDED Requirements

### Requirement: El módulo de gastos no depende del libro ni de la liquidación

El módulo `gastos` SHALL existir como paquete bajo `proptech_core`, con sus capas `dominio/` y
`aplicacion/`, y MUST NOT importar el módulo `cuenta_corriente` ni el módulo `liquidacion`, en ninguna
de sus capas y por ninguna cadena de imports. Esta frontera MUST vigilar la decisión de alcance de este
cambio: gastos y cargos **no escriben en el libro de movimientos**; quien convierte un gasto aprobado
en deuda de una unidad es el cambio 7, desde `liquidacion`. El test de fronteras MUST recorrer los
imports sin ejecutar el código y MUST nombrar el archivo ofensor.

#### Scenario: El paquete existe y pasa

- **WHEN** se corre el test sobre el árbol del repositorio
- **THEN** `gastos` figura entre los módulos recorridos y no tiene ofensores

#### Scenario: Gastos importa la cuenta corriente

- **WHEN** en una copia temporal se agrega a `gastos/aplicacion` un import de `cuenta_corriente.aplicacion`
- **THEN** el test da rojo nombrando el archivo

#### Scenario: Gastos importa la liquidación

- **WHEN** en una copia temporal se agrega a `gastos/aplicacion` un import de `liquidacion`
- **THEN** el test da rojo nombrando el archivo

#### Scenario: El dominio de gastos no toca su infraestructura

- **WHEN** en una copia temporal un archivo de `gastos/dominio/` importa `sqlalchemy` o la `aplicacion` de su propio módulo
- **THEN** el test da rojo en cada caso, nombrando el archivo

## MODIFIED Requirements

### Requirement: El SQL de cada módulo sólo nombra sus tablas

El SQL de cada módulo de `proptech_core` SHALL nombrar sólo tablas propias, salvo excepciones por archivo y tabla completos con motivo. El test MUST nombrar archivo y tabla ajena, ignorar mayúsculas y excluir `FOR UPDATE OF` y funciones en FROM. En `proptech_api` y `proptech_worker` MUST prohibir SQL directo sobre tablas del libro y `candado_de_cuenta`; sus consumidores usan `cuenta_corriente.aplicacion`. Las tablas `proveedor`, `gasto`, `nota_de_credito` y `cargo_particular` MUST figurar en el mapa de dueños como tablas del módulo `gastos`, y ningún otro módulo MUST escribir SQL sobre ellas; `gastos` MUST NOT nombrar en su SQL ninguna tabla del libro (`cuenta`, `emision`, `evento_de_emision`, `obligacion`, `movimiento`, `imputacion`, `candado_de_cuenta`), ni siquiera por excepción.

#### Scenario: El código de hoy pasa con sus excepciones

- **WHEN** el constructor ejecuta el escaneo sobre el árbol con el libro y el módulo de gastos construidos
- **THEN** pasa, con `administracion` como tabla de `acceso` y las excepciones de
  `complejos/aplicacion/escritura.py` (`asignacion_rol`), `complejos/aplicacion/lectura.py` (`persona`)
  y `complejos/aplicacion/ejemplo.py` (`administracion`, `persona`, `asignacion_rol`)

#### Scenario: Una tabla sin dueño declarado

- **WHEN** el constructor agrega en una copia SQL sobre una tabla que no figura en el mapa de dueños
- **THEN** el test falla nombrando esa tabla

#### Scenario: La liquidación nombra una tabla del libro

- **WHEN** el constructor agrega en una copia un `SELECT ... FROM movimiento` a `liquidacion/aplicacion/`
- **THEN** el test falla nombrando ese archivo y `movimiento`

#### Scenario: La cuenta corriente nombra una tabla de complejos

- **WHEN** el constructor agrega en una copia un `JOIN unidad` a `cuenta_corriente/aplicacion/`
- **THEN** el test falla nombrando ese archivo y `unidad`

#### Scenario: Sin la excepción de lectura

- **WHEN** el constructor saca en una copia la excepción de `lectura.py` y ejecuta el escaneo
- **THEN** el test falla nombrando `complejos/aplicacion/lectura.py` y `persona`

#### Scenario: SQL del libro fuera del módulo

- **WHEN** el ensayo agrega `select * from movimiento` en `proptech_api` o `proptech_worker`
- **THEN** el test falla nombrando archivo y tabla, aun con SQL en minúsculas

#### Scenario: OF y funciones no son tablas

- **WHEN** el ensayo escanea `FOR UPDATE OF i`, `FROM unnest(...)` y `FROM generate_series(...)`
- **THEN** no denuncia OF ni esos nombres de función como tablas sin dueño

#### Scenario: Gastos nombra una tabla del libro

- **WHEN** el constructor agrega en una copia un `INSERT INTO movimiento` o un `SELECT ... FROM obligacion` a `gastos/aplicacion/`
- **THEN** el test falla nombrando ese archivo y la tabla del libro

#### Scenario: Otro módulo nombra una tabla de gastos

- **WHEN** el constructor agrega en una copia un `SELECT ... FROM gasto` a `cuenta_corriente/aplicacion/`
- **THEN** el test falla nombrando ese archivo y `gasto`
