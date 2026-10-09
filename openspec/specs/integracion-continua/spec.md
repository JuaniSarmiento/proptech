# integracion-continua Specification

## Purpose
Define qué verifica la integración continua en cada push a `main` y garantiza que falle cuando falla
cualquiera de esas verificaciones, para que "el CI está en verde" sea una afirmación con valor.

## Requirements

### Requirement: Verificaciones en cada push

El CI SHALL correr en cada push a `main` y a pedido manual, y MUST ejecutar: lint y formato de
Python, chequeo de tipos de Python, tests de Python (unitarios y de integración contra PostgreSQL
real), lint y formato de TypeScript, chequeo de tipos de TypeScript, tests de la web, una prueba de
humo del stack completo y una búsqueda de secretos en el historial del repositorio.

#### Scenario: Push con todo correcto

- **WHEN** se pushea a `main` un commit donde todas las verificaciones pasan
- **THEN** el workflow termina en verde y cada una de las verificaciones listadas aparece como paso
  ejecutado

### Requirement: El CI falla cuando falla una verificación

Cada verificación SHALL hacer fallar el workflow si falla. Ningún paso MUST ignorar su código de
salida, y una suite que no recolecta ningún test MUST contar como falla.

#### Scenario: Test roto de Python

- **WHEN** un test de Python falla
- **THEN** el workflow termina en rojo

#### Scenario: Test roto de la web

- **WHEN** un test de la web falla
- **THEN** el workflow termina en rojo

#### Scenario: Error de lint o de formato

- **WHEN** un archivo de Python o de TypeScript no cumple el lint o el formato
- **THEN** el workflow termina en rojo

#### Scenario: Suite vacía

- **WHEN** la suite de Python o la de la web no encuentra ningún test
- **THEN** el workflow termina en rojo

### Requirement: Canario de test roto

En cada corrida, el CI SHALL demostrar que sus comandos de test fallan ante un test roto: agrega en
una copia de trabajo descartable un test que falla a propósito, en Python y en la web, corre el mismo
comando de test que usa el paso normal y MUST exigir que ese comando termine con código distinto de 0.
Si el comando termina en 0 con el test roto, el workflow MUST terminar en rojo. El test roto MUST NOT
quedar commiteado.

#### Scenario: Comando de test que traga fallas

- **WHEN** el comando de test de Python o de la web se configura de forma que termina en 0 aunque un
  test falle (por ejemplo, con `|| true`)
- **THEN** el canario detecta el código 0 con el test roto y el workflow termina en rojo

#### Scenario: Corrida normal

- **WHEN** los comandos de test están bien configurados
- **THEN** el canario ve código distinto de 0 con el test roto, el paso del canario pasa y el árbol
  de trabajo commiteado no contiene el test roto

### Requirement: Tests de integración contra PostgreSQL real

Los tests de integración SHALL correr contra un PostgreSQL real de la misma versión mayor y menor que
usa Compose, y MUST NOT reemplazarlo por otro motor de base de datos. El mismo mecanismo MUST
funcionar en la máquina del desarrollador y en el CI.

#### Scenario: Migraciones en el CI

- **WHEN** corre la suite de integración en el CI
- **THEN** las migraciones se aplican y se revierten contra un PostgreSQL real levantado para la
  corrida

#### Scenario: Versión de PostgreSQL desalineada

- **WHEN** la imagen de PostgreSQL usada por los tests difiere de la declarada en Compose
- **THEN** un test falla y nombra las dos versiones

### Requirement: Prueba de humo del stack detrás del proxy

El CI SHALL levantar el stack completo con Compose y verificar que `GET /api/salud` a través del
proxy responde 200 con la base conectada y que el único servicio con puertos publicados es el proxy.

#### Scenario: Humo en el CI

- **WHEN** corre el paso de humo
- **THEN** el stack se levanta, el endpoint de salud responde 200 a través del proxy, la verificación
  de puertos publicados pasa y el stack se baja al terminar, aun si el paso falló

### Requirement: Búsqueda de secretos

El CI SHALL buscar secretos en todo el historial de git del repositorio y MUST fallar si encuentra
alguno. Los valores de `.env.example` MUST NOT disparar la búsqueda.

#### Scenario: Secreto commiteado

- **WHEN** un commit contiene algo con forma de credencial real (por ejemplo una clave privada o un
  token de un proveedor conocido)
- **THEN** el workflow termina en rojo y señala el archivo y el commit

### Requirement: Versiones de herramientas fijadas

Las acciones del workflow, las imágenes de Docker y las herramientas de lint y test SHALL estar
fijadas a una versión exacta. Ninguna imagen de Compose ni del CI MUST usar la etiqueta `latest` ni
una etiqueta sin versión de parche.

#### Scenario: Imagen sin versión fija

- **WHEN** un archivo de Compose o un Dockerfile referencia una imagen con `latest`, sin etiqueta, o
  con una etiqueta sin versión de parche
- **THEN** un test falla y nombra la imagen
