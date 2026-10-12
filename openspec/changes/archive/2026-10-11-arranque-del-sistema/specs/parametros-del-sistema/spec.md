## Purpose

Define el archivo único con los parámetros con que arranca el sistema (D-042) y qué hace su lector con
un archivo válido, mal formado, incompleto o fuera de rango, para que ningún valor por defecto viva
escrito en el código.

## ADDED Requirements

### Requirement: Archivo de parámetros con los valores iniciales de D-042

El repositorio SHALL incluir `config/parametros.yaml` con: tasa de interés mensual 3%, 0 días de
gracia, forma de cálculo proporcional por día, fondo de reserva 0%, las nueve categorías de gasto
precargadas de R16, los grupos de reparto típicos de un edificio de R01 (Generales, Ascensor,
Cocheras, Servicios centrales), los tipos de unidad de D-029 (departamento, cochera, baulera, local)
y los estados de unidad de R02 (baldío, en obra, habitado, desocupado) desactivados para edificios
(D-030) con factor 100% y cargo fijo 0.

#### Scenario: El archivo del repositorio es válido y tiene los defaults

- **WHEN** se lee `config/parametros.yaml` del repositorio con el lector
- **THEN** la lectura es exitosa y devuelve tasa 3.00, días de gracia 0, forma proporcional por día,
  fondo 0.00, nueve categorías, un grupo "Generales" por coeficiente que abarca todas las unidades,
  cuatro tipos de unidad y los cuatro estados desactivados

### Requirement: Lector validado con errores que nombran cada campo

El lector SHALL rechazar un archivo inválido con un único error que liste **todos** los problemas
encontrados, cada uno con la ruta del campo (por ejemplo `intereses.tasa_mensual`) y el motivo. El
error MUST NOT incluir el contenido del archivo. Se consideran inválidos, como mínimo: archivo
inexistente o ilegible, YAML mal formado, raíz que no es un mapa, claves duplicadas, campos
faltantes, campos desconocidos, valores vacíos o en blanco, tipos equivocados y valores fuera de
rango.

#### Scenario: Tasa negativa

- **WHEN** el archivo tiene `tasa_mensual: "-1.00"`
- **THEN** el lector falla nombrando `intereses.tasa_mensual` y el rango permitido

#### Scenario: Varios problemas a la vez

- **WHEN** el archivo tiene la tasa fuera de rango, le faltan los días de gracia y trae un campo
  desconocido
- **THEN** el error nombra los tres campos en un solo mensaje

#### Scenario: YAML mal formado

- **WHEN** el archivo no es YAML válido o está vacío
- **THEN** el lector falla con un mensaje que dice que el archivo está mal formado (con línea si se
  conoce), sin traza ni contenido

#### Scenario: Clave duplicada

- **WHEN** el archivo repite una clave en el mismo nivel
- **THEN** el lector falla nombrando la clave duplicada, en lugar de quedarse con la última en silencio

#### Scenario: Porcentaje escrito como número

- **WHEN** la tasa o el fondo de reserva vienen como número YAML (`3.5`) en lugar de texto (`"3.50"`)
- **THEN** el lector falla nombrando el campo y pidiendo texto, porque un número YAML se lee como `float`

#### Scenario: Valores en blanco y tipos equivocados

- **WHEN** un nombre de categoría es `"  "`, los días de gracia son `"diez"` o la forma de cálculo no
  es una de las permitidas
- **THEN** el lector falla nombrando cada campo con su motivo

#### Scenario: Listas inconsistentes

- **WHEN** dos categorías comparten clave, falta el grupo `generales` o un estado aparece repetido
- **THEN** el lector falla nombrando la lista y la clave en conflicto

### Requirement: Rangos de los parámetros

El lector SHALL aceptar sólo: tasa mensual entre 0 y 10 inclusive con hasta dos decimales; días de
gracia enteros entre 0 y 31; forma de cálculo `proporcional_por_dia` o `mes_entero`; fondo de reserva
entre 0 y 100 con hasta dos decimales; factor por estado entre 0 y 100; cargo fijo por estado como
monto válido no negativo; listas de categorías, grupos, tipos y estados no vacías y con claves únicas
en minúsculas.

#### Scenario: Bordes aceptados

- **WHEN** la tasa es `"0.00"` o `"10.00"`, los días de gracia son 0 o 31 y el fondo es `"100.00"`
- **THEN** el lector acepta el archivo

#### Scenario: Bordes rechazados

- **WHEN** la tasa es `"10.01"` o tiene tres decimales, o los días de gracia son 32
- **THEN** el lector falla nombrando el campo

#### Scenario: Estados de unidad fuera de rango

- **WHEN** un estado tiene factor `"100.01"` o `"-0.01"`, o cargo fijo `"-1.00"`, o la lista de
  estados está vacía
- **THEN** el lector falla nombrando el estado y el campo, sin repetir el valor recibido

### Requirement: Los procesos no arrancan con parámetros inválidos

La API SHALL leer y validar el archivo de parámetros al arrancar, desde la ruta indicada
por la variable `PROPTECH_PARAMETROS`, y MUST terminar con error si el archivo es inválido, nombrando
los campos con problema.

#### Scenario: API con parámetros inválidos

- **WHEN** la API arranca con un archivo de parámetros que tiene la tasa negativa
- **THEN** el proceso termina con un error que nombra `intereses.tasa_mensual`

#### Scenario: Variable de la ruta faltante o vacía

- **WHEN** la API arranca sin `PROPTECH_PARAMETROS`, con ella vacía o apuntando a un
  archivo que no existe
- **THEN** el proceso termina con un error que nombra `PROPTECH_PARAMETROS`
