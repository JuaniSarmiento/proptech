# ubicacion-del-edificio Specification

## Purpose
Define de dónde salen la provincia, el departamento y la localidad de un edificio (un archivo oficial
de Georef guardado en el repositorio, con su licencia y su fecha), cómo se encadenan las tres listas y
qué valida el servidor antes de guardar una ubicación.

## Requirements

### Requirement: Las listas de ubicación salen de un archivo del repositorio, no de un servicio en vivo

El repositorio SHALL incluir el listado de provincias, departamentos y localidades de Argentina en
`config/georef/`, derivado de Georef (Servicio de Normalización de Datos Geográficos, datos.gob.ar),
con el id oficial, el nombre y el id del padre de cada registro. Junto al dato MUST haber un archivo de
procedencia que declare la fuente, la fecha de descarga, la licencia (Creative Commons Atribución 4.0)
y el comando exacto que lo regenera. Ni la API ni la web MUST consultar Georef en tiempo de ejecución:
la única llamada a Georef es la regeneración manual del archivo.

#### Scenario: Procedencia declarada

- **WHEN** se lee `config/georef/`
- **THEN** hay un archivo de procedencia con fuente, fecha de descarga, licencia CC BY 4.0 y el comando
  que regenera el dato

#### Scenario: Nada sale a la red

- **WHEN** se buscan llamadas a `apis.datos.gob.ar` o a `infra.datos.gob.ar` en el código de la API, del
  worker y de la web
- **THEN** no hay ninguna, y la CSP de la web no declara ningún origen nuevo

#### Scenario: Archivo ausente o ilegible

- **WHEN** el archivo falta, está vacío, está truncado o no es del tipo esperado
- **THEN** el proceso falla al arrancar nombrando el archivo, sin repetir su contenido en el error

#### Scenario: La provincia de Mendoza existe con su id oficial

- **WHEN** se piden las provincias
- **THEN** Mendoza está con el id oficial `50` y la lista tiene las 24 jurisdicciones

### Requirement: Las tres listas se encadenan

El servidor SHALL ofrecer las provincias, los departamentos de una provincia y las localidades de un
departamento, cada lista ordenada por nombre y con id y nombre. Pedir los departamentos de una
provincia que no existe, o las localidades de un departamento que no existe, MUST responder 404. Leer
las listas MUST exigir una sesión válida y MUST NOT depender del edificio ni del rol, porque son datos
públicos del país.

#### Scenario: Departamentos de una provincia

- **WHEN** se piden los departamentos de la provincia `50`
- **THEN** la respuesta trae los 18 departamentos de Mendoza, ordenados por nombre, y ninguno de otra
  provincia

#### Scenario: Localidades de un departamento

- **WHEN** se piden las localidades del departamento de Godoy Cruz
- **THEN** la respuesta trae sólo localidades de ese departamento

#### Scenario: Provincia inexistente

- **WHEN** se piden los departamentos de la provincia `99`
- **THEN** la respuesta es 404

#### Scenario: Sin sesión

- **WHEN** se piden las provincias sin sesión
- **THEN** la respuesta es 401 y no se devuelve ninguna lista

### Requirement: El servidor valida que el trío de ubicación sea coherente

Guardar la ubicación de un edificio SHALL exigir los tres ids juntos (provincia, departamento y
localidad) y MUST verificar, contra el mismo archivo del repositorio, que cada uno exista y que la
localidad pertenezca a ese departamento y el departamento a esa provincia. Un id que no existe o un
trío incoherente MUST responder 422 nombrando el campo que falla, sin repetir el valor recibido. La web
MUST NOT ser la autoridad: el rechazo MUST ocurrir aunque el pedido venga armado a mano.

#### Scenario: Localidad de otro departamento

- **WHEN** se manda la provincia de Mendoza, el departamento Capital y una localidad de Godoy Cruz
- **THEN** la respuesta es 422 nombrando la localidad y la ubicación no se guarda

#### Scenario: Departamento de otra provincia

- **WHEN** se manda la provincia de Mendoza con un departamento de San Juan y una localidad de ese
  departamento
- **THEN** la respuesta es 422 nombrando el departamento

#### Scenario: Id que no existe

- **WHEN** alguno de los tres ids no está en el archivo
- **THEN** la respuesta es 422 nombrando ese campo, sin el valor

#### Scenario: Trío incompleto

- **WHEN** se manda la provincia y el departamento pero no la localidad
- **THEN** la respuesta es 422 nombrando la localidad y no se guarda nada

#### Scenario: Trío coherente

- **WHEN** se manda provincia Mendoza, departamento Capital y la localidad Ciudad de Mendoza
- **THEN** la ubicación queda guardada con los tres ids

### Requirement: Sólo Argentina, y la calle es texto libre

El sistema MUST NOT ofrecer un campo ni un selector de país: toda ubicación es argentina. La calle y el
número SHALL ser un único campo de texto opcional, de hasta 200 caracteres, sin caracteres de control y
recortado en los bordes, y MUST NOT validarse contra ningún listado de calles.

#### Scenario: Sin país

- **WHEN** se lee o se escribe la ubicación de un edificio
- **THEN** no hay ningún campo de país en el contrato ni en la pantalla

#### Scenario: Calle cualquiera

- **WHEN** la calle y número es "Pasaje sin nombre, lote 4"
- **THEN** se guarda tal cual

#### Scenario: Calle con carácter de control o demasiado larga

- **WHEN** la calle y número trae un carácter de control o pasa los 200 caracteres
- **THEN** la respuesta es 422 nombrando el campo, sin el valor
