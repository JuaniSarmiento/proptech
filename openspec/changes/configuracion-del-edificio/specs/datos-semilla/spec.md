## MODIFIED Requirements

### Requirement: Edificio de ejemplo ficticio y versionado

El repositorio SHALL incluir `config/semilla/edificio-ejemplo.yaml` con un edificio ficticio que tiene
unidades de los cuatro tipos (departamento, cochera, baulera y local), cada una con identificador
único, tipo, piso, coeficiente y superficie, la pertenencia de las unidades a los grupos de reparto y
el estado de migración del edificio, que para el edificio de ejemplo MUST ser `sin_saldos_previos`
(R09, D-083). La versión del archivo MUST ser exactamente 1. MUST NOT contener datos personales: ni
nombres de personas, ni emails, ni teléfonos, ni documentos, ni direcciones reales.

#### Scenario: El archivo no tiene datos personales

- **WHEN** se busca en el archivo de semilla cualquier campo de persona o contacto, o un texto con
  forma de email o teléfono
- **THEN** no hay ninguno

#### Scenario: Estado de migración del ejemplo

- **WHEN** se lee la semilla del repositorio
- **THEN** el estado de migración es `sin_saldos_previos`

#### Scenario: Versión distinta de 1

- **WHEN** la semilla declara `version: 2` o `version: "1"`
- **THEN** el lector falla nombrando el campo version

### Requirement: Semilla validada contra los parámetros

El lector de la semilla SHALL rechazar, nombrando el campo y la unidad, un archivo con: tipos de
unidad que no están en los parámetros, grupos que no están en los parámetros, identificadores de
unidad repetidos, unidades de un grupo que no existen, coeficientes que no son texto decimal positivo
con hasta 6 decimales, coeficientes de "Generales" cuya suma se aparta de 1 más de 0,0001, un estado de
migración fuera de `pendiente`, `confirmada` o `sin_saldos_previos`, superficies que no son texto
decimal positivo, y los mismos errores de formato que el lector de parámetros (YAML mal formado,
claves duplicadas, campos faltantes o desconocidos). Una suma que se aparta de 1 hasta 0,0001 inclusive
MUST aceptarse con una advertencia que diga la diferencia (R01, D-082), sin redondear para que cierre.
La validación de los grupos parciales sigue la respuesta a P24 y este requisito no la fija.

#### Scenario: La semilla del repositorio es válida

- **WHEN** se lee la semilla del repositorio con los parámetros del repositorio
- **THEN** la lectura es exitosa, los coeficientes suman exactamente 1, sin advertencia, y el grupo
  "Generales" abarca todas las unidades

#### Scenario: Coeficientes dentro de la tolerancia

- **WHEN** a la semilla se le cambia un coeficiente de modo que la suma da 0.9999
- **THEN** la lectura es exitosa con una advertencia que dice la diferencia "-0.000100"

#### Scenario: Coeficientes que no suman 1

- **WHEN** a la semilla se le cambia un coeficiente de modo que la suma da 0.9998
- **THEN** el lector falla diciendo que los coeficientes no suman 1 y la diferencia, sin redondear

#### Scenario: Tipo de unidad desconocido

- **WHEN** una unidad tiene tipo `quincho`
- **THEN** el lector falla nombrando la unidad y el campo tipo

## ADDED Requirements

### Requirement: Carga del edificio de ejemplo en la base

El sistema SHALL ofrecer un comando explícito que carga el edificio de ejemplo, ya validado, en una
administración de ejemplo propia, con ids fijos, como un edificio más: sus unidades, sus grupos, las
categorías y la primera versión de configuración de los parámetros, y su estado de migración. El
comando MUST fijar el tenant de la administración de ejemplo y MUST NOT tocar ninguna otra
administración. Nada lo corre al arrancar. Correrlo otra vez MUST NOT duplicar nada: si el ejemplo ya
está cargado igual, termina con código 0 diciendo que no hizo nada; si está cargado distinto, termina
con código distinto de 0 sin escribir nada. Una carga a medias MUST NOT quedar: todo en una
transacción.

#### Scenario: Primera carga

- **WHEN** se corre el comando sobre una base sin el ejemplo
- **THEN** existe la administración de ejemplo con el edificio, sus 13 unidades, sus grupos, sus
  categorías, su configuración y estado `sin_saldos_previos`, y el comando termina con código 0

#### Scenario: Segunda carga igual

- **WHEN** se corre el comando dos veces seguidas
- **THEN** la segunda termina con código 0, dice que el ejemplo ya estaba y los conteos de cada tabla
  no cambian

#### Scenario: Dos cargas a la vez

- **WHEN** se corre el comando dos veces en paralelo sobre una base sin el ejemplo
- **THEN** queda un solo edificio de ejemplo y ninguna corrida deja datos a medias

#### Scenario: El ejemplo cambió en la base

- **WHEN** después de cargarlo se edita una unidad del ejemplo y se corre el comando otra vez
- **THEN** termina con código distinto de 0, dice qué difiere y no escribe nada

#### Scenario: Otras administraciones no se tocan

- **WHEN** se corre el comando en una base que ya tiene otra administración con datos
- **THEN** los datos de esa administración quedan idénticos
