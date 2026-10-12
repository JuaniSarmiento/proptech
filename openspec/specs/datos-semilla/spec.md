# datos-semilla Specification

## Purpose
Define el edificio de ejemplo con el que se desarrolla y se demuestra el sistema mientras no hay datos
del piloto: un archivo versionado, ficticio y validado contra los parámetros, que el cambio 3 carga en
la base cuando existan sus tablas.

## Requirements

### Requirement: Edificio de ejemplo ficticio y versionado

El repositorio SHALL incluir `config/semilla/edificio-ejemplo.yaml` con un edificio ficticio que tiene
unidades de los cuatro tipos (departamento, cochera, baulera y local), cada una con identificador
único, tipo, piso, coeficiente y superficie, y la pertenencia de las unidades a los grupos de
reparto. MUST NOT contener datos personales: ni nombres de personas, ni emails, ni teléfonos, ni
documentos, ni direcciones reales.

#### Scenario: El archivo no tiene datos personales

- **WHEN** se busca en el archivo de semilla cualquier campo de persona o contacto, o un texto con
  forma de email o teléfono
- **THEN** no hay ninguno

### Requirement: Semilla validada contra los parámetros

El lector de la semilla SHALL rechazar, nombrando el campo y la unidad, un archivo con: tipos de
unidad que no están en los parámetros, grupos que no están en los parámetros, identificadores de
unidad repetidos, unidades de un grupo que no existen, coeficientes que no son texto decimal positivo
con hasta 6 decimales, coeficientes que no suman exactamente 1, superficies que no son texto decimal
positivo, y los mismos errores de formato que el lector de parámetros (YAML mal formado, claves
duplicadas, campos faltantes o desconocidos).

#### Scenario: La semilla del repositorio es válida

- **WHEN** se lee la semilla del repositorio con los parámetros del repositorio
- **THEN** la lectura es exitosa, los coeficientes suman exactamente 1 y el grupo "Generales" abarca
  todas las unidades

#### Scenario: Coeficientes que no suman 1

- **WHEN** a la semilla se le cambia un coeficiente de modo que la suma da 0.999999
- **THEN** el lector falla diciendo que los coeficientes no suman 1, sin redondear para que cierre

#### Scenario: Tipo de unidad desconocido

- **WHEN** una unidad tiene tipo `quincho`
- **THEN** el lector falla nombrando la unidad y el campo tipo

### Requirement: Verificación de la semilla por comando

El sistema SHALL ofrecer un comando que lee y valida la semilla contra los parámetros y termina con
código 0 si es válida o distinto de 0 con los errores si no. En este cambio el comando MUST NOT
escribir en la base.

#### Scenario: Comando sobre la semilla del repositorio

- **WHEN** se corre el comando de verificación sobre la semilla del repositorio, con
  `PROPTECH_PARAMETROS` apuntando a los parámetros del repositorio y sin ninguna variable de
  PostgreSQL definida
- **THEN** termina con código 0, sin intentar conectarse a la base

#### Scenario: Comando sobre una semilla inválida

- **WHEN** se corre el comando sobre una semilla con un error
- **THEN** termina con código 1 y muestra los errores nombrando unidad y campo
