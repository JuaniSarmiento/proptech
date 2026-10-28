# datos-semilla Specification

## Purpose
Define el edificio de ejemplo con el que se desarrolla y se demuestra el sistema mientras no hay datos
del piloto: un archivo versionado, ficticio y validado contra los parámetros, que el cambio 3 carga en
la base cuando existan sus tablas.

## Requirements

### Requirement: Edificio de ejemplo ficticio y versionado

El repositorio SHALL incluir `config/semilla/edificio-ejemplo.yaml` con un edificio ficticio que tiene
unidades de los cuatro tipos (departamento, cochera, baulera y local), cada una con identificador
único, tipo, piso, coeficiente y superficie, la pertenencia de las unidades a los grupos de reparto con
el modo de coeficientes de cada grupo parcial, y el estado de migración del edificio, que para el
edificio de ejemplo MUST ser `sin_saldos_previos` (R09, D-083). La versión del archivo MUST ser
exactamente 1. MUST NOT contener datos personales: ni nombres de personas, ni emails, ni teléfonos, ni
documentos, ni direcciones reales.

El edificio de ejemplo SHALL declarar su ubicación con los tres ids de Georef (provincia, departamento
y localidad) en lugar de la localidad como texto libre, y su cantidad de pisos sobre planta baja y de
subsuelos. El piso de cada unidad MUST salir del vocabulario de pisos de ese edificio: las cuatro
unidades que hoy dicen `"SS"` (las cocheras `C1` a `C3` y la baulera `B1`) MUST pasar al subsuelo
numerado. La calle y el número MUST ser una dirección inventada, nunca una real.

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

#### Scenario: Ubicación del ejemplo

- **WHEN** se lee la semilla del repositorio
- **THEN** el edificio trae los tres ids de ubicación, coherentes entre sí contra el archivo de Georef, y
  ya no una localidad de texto libre

#### Scenario: Pisos del ejemplo

- **WHEN** se lee la semilla del repositorio
- **THEN** el edificio declara 4 pisos y al menos 1 subsuelo, y cada unidad tiene un piso de ese
  vocabulario: `PB` el local, `1` a `4` los departamentos y el subsuelo numerado las tres cocheras y la
  baulera

#### Scenario: Semilla con un piso fuera del vocabulario

- **WHEN** la semilla declara una unidad en el piso `"5"` o en `"SS"` en un edificio de 4 pisos y 1
  subsuelo
- **THEN** el lector falla nombrando el campo piso y la unidad

#### Scenario: Semilla con una ubicación incoherente

- **WHEN** la semilla declara una localidad que no pertenece al departamento declarado
- **THEN** el lector falla nombrando el campo de la localidad

### Requirement: Semilla validada contra los parámetros

El lector de la semilla SHALL rechazar, nombrando el campo y la unidad, un archivo con: tipos de
unidad que no están en los parámetros, grupos que no están en los parámetros, identificadores de
unidad repetidos, unidades de un grupo que no existen, coeficientes que no son texto decimal positivo
con hasta 6 decimales, coeficientes de "Generales" o de un grupo con modo `propios` cuya suma se aparta
de 1 más de 0,0001, un modo de grupo fuera de `renormalizado` o `propios`, un miembro con coeficiente
propio en un grupo `renormalizado` o sin él en uno `propios`, un estado de migración fuera de
`pendiente`, `confirmada` o `sin_saldos_previos`, superficies que no son texto decimal positivo, y los
mismos errores de formato que el lector de parámetros (YAML mal formado, claves duplicadas, campos
faltantes o desconocidos). Un grupo sin modo MUST leerse como `renormalizado`. Una suma que se aparta
de 1 hasta 0,0001 inclusive MUST aceptarse con una advertencia que diga la diferencia (R01, D-082),
sin redondear para que cierre. La validación de la suma MUST usar la misma función que el informe de
la API.

#### Scenario: La semilla del repositorio es válida

- **WHEN** se lee la semilla del repositorio con los parámetros del repositorio
- **THEN** la lectura es exitosa, los coeficientes suman exactamente 1, sin advertencia, el grupo
  "Generales" abarca todas las unidades y los grupos parciales son `renormalizado`

#### Scenario: Coeficientes dentro de la tolerancia

- **WHEN** a la semilla se le cambia un coeficiente de modo que la suma da 0.9999
- **THEN** la lectura es exitosa con una advertencia que dice la diferencia "-0.000100"

#### Scenario: Coeficientes que no suman 1

- **WHEN** a la semilla se le cambia un coeficiente de modo que la suma da 0.9998
- **THEN** el lector falla diciendo que los coeficientes no suman 1 y la diferencia, sin redondear

#### Scenario: Grupo con coeficientes propios en la semilla

- **WHEN** a la semilla se le pone el grupo "Cocheras" en modo `propios` con coeficientes que suman
  0.9998
- **THEN** el lector falla nombrando el grupo y la diferencia; con coeficientes que suman 1, la lectura
  es exitosa

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

### Requirement: Carga del edificio de ejemplo en la base

El sistema SHALL ofrecer un comando explícito que carga el edificio de ejemplo, ya validado, en una
administración de ejemplo propia, con ids fijos, como un edificio más y por los mismos casos de uso
que la API: sus unidades, sus grupos, las categorías y la primera versión de configuración de los
parámetros, y su estado de migración. El comando MUST fijar el tenant de la administración de ejemplo
y MUST NOT tocar ninguna otra administración. Nada lo corre al arrancar. Correrlo otra vez MUST NOT
duplicar nada, y la comparación MUST abarcar sólo lo que sale de la semilla (unidades, grupos y estado
de migración), no lo que viene de los parámetros (D-042): si el ejemplo ya está cargado igual, termina
con código 0 diciendo que no hizo nada; si está cargado distinto, termina con código distinto de 0 sin
escribir nada. Una carga a medias MUST NOT quedar: todo en una transacción. Precondición (D-112):
el comando MUST NOT correr salvo que `PROPTECH_ENTORNO` valga exactamente `desarrollo`; sin eso
termina con código distinto de 0, lo dice y no se conecta ni escribe nada. Los escenarios de abajo
suponen esa variable puesta, salvo "Fuera de desarrollo no corre".

#### Scenario: Primera carga

- **WHEN** se corre el comando sobre una base sin el ejemplo
- **THEN** existe la administración de ejemplo con el edificio, sus 13 unidades, sus grupos, sus
  categorías, su configuración y estado `sin_saldos_previos`, y el comando termina con código 0

#### Scenario: Segunda carga igual

- **WHEN** se corre el comando dos veces seguidas
- **THEN** la segunda termina con código 0, dice que el ejemplo ya estaba y los conteos de cada tabla
  no cambian

#### Scenario: Cambiar los parámetros no hace fallar la carga

- **WHEN** después de cargar el ejemplo se cambia la tasa en el archivo de parámetros y se corre el
  comando otra vez
- **THEN** termina con código 0 diciendo que el ejemplo ya estaba, y la configuración del ejemplo no
  cambia

#### Scenario: Dos cargas a la vez

- **WHEN** se corre el comando dos veces en paralelo sobre una base sin el ejemplo
- **THEN** queda un solo edificio de ejemplo y ninguna corrida deja datos a medias

#### Scenario: El ejemplo cambió en la base

- **WHEN** después de cargarlo se edita una unidad del ejemplo y se corre el comando otra vez
- **THEN** termina con código distinto de 0, dice qué difiere y no escribe nada

#### Scenario: Fuera de desarrollo no corre

- **WHEN** se corre el comando sin `PROPTECH_ENTORNO=desarrollo` (ausente, otro valor, otra mayúscula
  o con espacios)
- **THEN** termina con código distinto de 0, dice que hace falta `PROPTECH_ENTORNO=desarrollo` y no
  se conecta a la base ni escribe nada

#### Scenario: Otras administraciones no se tocan

- **WHEN** se corre el comando en una base que ya tiene otra administración con datos
- **THEN** los datos de esa administración quedan idénticos
