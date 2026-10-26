# Spec Delta

## Purpose

Fija qué puede importar cada módulo de `proptech_core` (D-021, D-040) y exige que el test que lo
vigila dé rojo ante cada violación, antes de que exista la primera tabla de plata.

## ADDED Requirements

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
