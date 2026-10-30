# fronteras-de-modulos Specification

## Purpose
Fija qué puede importar cada módulo de `proptech_core` (D-021, D-040) y exige que el test que lo
vigila dé rojo ante cada violación, antes de que exista la primera tabla de plata.

## Requirements

### Requirement: Sin ciclos entre módulos

Ningún módulo de `proptech_core` SHALL importar, por ninguna cadena de imports y en ninguna de sus
capas, a un módulo que a su vez lo importa. El test de fronteras MUST recorrer los imports sin ejecutar
el código y MUST nombrar el ciclo encontrado.

#### Scenario: El código de hoy no tiene ciclos

- **WHEN** se corre el test de fronteras sobre el árbol del repositorio
- **THEN** pasa, y lista los módulos que recorrió, incluido `cuenta_corriente`

#### Scenario: Un ciclo agregado a una copia

- **WHEN** en una copia temporal del código se agrega a `acceso` un import de `complejos.aplicacion`
- **THEN** el test da rojo nombrando el ciclo `acceso → complejos → acceso`

#### Scenario: Un ciclo de tres módulos

- **WHEN** en una copia temporal `cuenta_corriente` importa `complejos.aplicacion` y `acceso` importa
  `cuenta_corriente.aplicacion`
- **THEN** el test da rojo nombrando `acceso → cuenta_corriente → complejos → acceso`, aunque ningún par
  se importe en las dos direcciones

### Requirement: Entre módulos sólo se importa la capa de aplicación

Un módulo SHALL importar de otro módulo de `proptech_core` sólo su capa `aplicacion`. Las únicas
excepciones MUST estar escritas en el test, por submódulo destino y con su motivo:
`acceso.dominio.identidad`, `acceso.dominio.permisos` y `acceso.dominio.eventos`. `compartido` no
cuenta como módulo de dominio, y `proptech_api` y `proptech_worker` quedan fuera de esta regla.

#### Scenario: Las excepciones de hoy pasan

- **WHEN** se corre el test sobre el árbol del repositorio, donde `complejos` importa
  `acceso.dominio.identidad`, `acceso.dominio.permisos` y `acceso.dominio.eventos`
- **THEN** pasa

#### Scenario: Un import de dominio ajeno sin excepción

- **WHEN** en una copia temporal se agrega a `complejos/aplicacion` un import de `acceso.dominio.token`
- **THEN** el test da rojo nombrando el archivo y el submódulo importado

#### Scenario: Las tres formas de escribir un import

- **WHEN** en copias temporales se agrega el mismo import prohibido como `import a.b.c`,
  `from a.b import c` y `from a import b`
- **THEN** el test da rojo en las tres

#### Scenario: Un destino con prefijo parecido a una excepción

- **WHEN** en una copia temporal `complejos` importa `acceso.dominio.identidad_x`
- **THEN** el test da rojo

#### Scenario: Un import relativo entre módulos

- **WHEN** en una copia temporal se agrega a `complejos` un `from ...acceso.dominio import token`
- **THEN** el test da rojo

#### Scenario: Un import de adaptadores ajenos

- **WHEN** en una copia temporal se agrega a `complejos` un import de `acceso.adaptadores`
- **THEN** el test da rojo

### Requirement: El dominio sólo usa lo puro de `compartido`

Todo archivo bajo `dominio/` SHALL importar de `compartido` sólo una lista permitida de submódulos
puros: `dinero`, `coeficientes`, `porcentaje`, `superficie`, `texto`, `tipos_de_unidad` y `reparto`.
`parametros` MUST figurar como excepción con su motivo. Un submódulo nuevo de `compartido` MUST quedar
prohibido para `dominio/` hasta que alguien lo sume a la lista.

#### Scenario: El dominio de hoy pasa

- **WHEN** se corre el test sobre el árbol del repositorio, donde `complejos/dominio/configuracion.py`
  importa `compartido.parametros` y `compartido.porcentaje`
- **THEN** pasa

#### Scenario: El dominio importa la base

- **WHEN** en una copia temporal se agrega a un archivo de `dominio/` un import de
  `compartido.base_de_datos`
- **THEN** el test da rojo nombrando el archivo

#### Scenario: Un submódulo nuevo de compartido

- **WHEN** en una copia temporal se crea `compartido/nuevo.py` y un archivo de `dominio/` lo importa
- **THEN** el test da rojo, aunque nadie haya escrito `nuevo` en ninguna lista de prohibidos

### Requirement: La cuenta corriente no encola ni depende de la liquidación

El módulo `cuenta_corriente` SHALL existir como paquete, aunque esté vacío, y MUST NOT importar
`compartido.cola` ni el módulo `liquidacion`, en ninguna de sus capas.

#### Scenario: El paquete existe y pasa

- **WHEN** se corre el test sobre el árbol del repositorio
- **THEN** `cuenta_corriente` figura entre los módulos recorridos y no tiene ofensores

#### Scenario: La cuenta corriente importa la cola

- **WHEN** en una copia temporal se agrega a `cuenta_corriente/aplicacion` un import de
  `compartido.cola`
- **THEN** el test da rojo nombrando el archivo

### Requirement: El dominio no depende de su propia infraestructura

Todo archivo bajo `dominio/` SHALL NOT importar la `aplicacion`, los `adaptadores` ni los `puertos` de
su propio módulo, ni `sqlalchemy` ni `psycopg` (D-021, D-114.7).

#### Scenario: El dominio de hoy pasa

- **WHEN** se corre el test sobre el árbol del repositorio
- **THEN** no hay ofensores

#### Scenario: El dominio importa la base

- **WHEN** en copias temporales un archivo de `complejos/dominio/` importa `sqlalchemy`, o
  `complejos.aplicacion.escritura`
- **THEN** el test da rojo en cada una, nombrando el archivo

### Requirement: El SQL de cada módulo sólo nombra sus tablas

El SQL de cada módulo de `proptech_core` SHALL nombrar sólo tablas propias, salvo excepciones por archivo y tabla completos con motivo. El test MUST nombrar archivo y tabla ajena, ignorar mayúsculas y excluir `FOR UPDATE OF` y funciones en FROM. En `proptech_api` y `proptech_worker` MUST prohibir SQL directo sobre tablas del libro y `candado_de_cuenta`; sus consumidores usan `cuenta_corriente.aplicacion`. El comando del edificio de ejemplo (`complejos/aplicacion/ejemplo.py`) MUST NOT tener excepción: la administración, la persona, la asignación y el vínculo de identidad del ejemplo se escriben por la capa de aplicación de `acceso`. Las tablas `proveedor`, `gasto`, `nota_de_credito` y `cargo_particular` MUST figurar en el mapa de dueños como tablas del módulo `gastos`, y ningún otro módulo MUST escribir SQL sobre ellas; `gastos` MUST NOT nombrar en su SQL ninguna tabla del libro (`cuenta`, `emision`, `evento_de_emision`, `obligacion`, `movimiento`, `imputacion`, `candado_de_cuenta`), ni siquiera por excepción.

#### Scenario: El código de hoy pasa con sus excepciones

- **WHEN** el constructor ejecuta el escaneo sobre el árbol con el libro y el módulo de gastos construidos
- **THEN** pasa, con `administracion` como tabla de `acceso` y sólo las excepciones de
  `complejos/aplicacion/escritura.py` (`asignacion_rol`) y `complejos/aplicacion/lectura.py` (`persona`)

#### Scenario: El ejemplo vuelve a escribir una tabla de acceso

- **WHEN** el constructor agrega en una copia un `INSERT INTO persona` a `complejos/aplicacion/ejemplo.py`
- **THEN** el test falla nombrando ese archivo y `persona`

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

### Requirement: La vinculación de desarrollo sólo se importa desde el comando del ejemplo

El módulo de `acceso.aplicacion` que vincula una cuenta de Clerk de desarrollo al ejemplo, sin
invitación, SHALL poder importarse sólo desde `complejos/aplicacion/ejemplo.py`, por lista permitida
(mismo estilo que las reglas de D-116). Cualquier otro archivo de `proptech_core`, `proptech_api` o
`proptech_worker` que lo importe, por `import` o por `from … import`, MUST hacer fallar el test
nombrando el archivo.

#### Scenario: El código de hoy pasa

- **WHEN** corre el test de fronteras sobre el árbol del change
- **THEN** pasa, con `complejos/aplicacion/ejemplo.py` como único importador

#### Scenario: La API importa la vinculación de desarrollo

- **WHEN** el constructor agrega en una copia un `from proptech_core.acceso.aplicacion.<módulo> import
  <función>` a `proptech_api/sesion.py`
- **THEN** el test falla nombrando `proptech_api/sesion.py`

#### Scenario: Otro módulo de acceso la importa

- **WHEN** el constructor agrega en una copia un `import` de ese módulo a
  `acceso/aplicacion/invitaciones.py`
- **THEN** el test falla nombrando ese archivo

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
