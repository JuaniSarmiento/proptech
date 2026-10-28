# Spec Delta

## MODIFIED Requirements

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
