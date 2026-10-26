# Spec Delta

## MODIFIED Requirements

### Requirement: Archivo de parámetros con los valores iniciales de D-042

El repositorio SHALL incluir `config/parametros.yaml` con: tasa de interés mensual 3%, 0 días de
gracia, forma de cálculo proporcional por día, fondo de reserva 0%, las nueve categorías de gasto
precargadas de R16, los grupos de reparto típicos de un edificio de R01 (Generales, Ascensor,
Cocheras, Servicios centrales), los tipos de unidad de D-029 (departamento, cochera, baulera, local),
los estados de unidad de R02 (baldío, en obra, habitado, desocupado) desactivados para edificios
(D-030) con factor 100% y cargo fijo 0, y el umbral de saldos chicos de R30 en $500 (D-109).

#### Scenario: El archivo del repositorio es válido y tiene los defaults

- **WHEN** se lee `config/parametros.yaml` del repositorio con el lector
- **THEN** la lectura es exitosa y devuelve tasa 3.00, días de gracia 0, forma proporcional por día,
  fondo 0.00, nueve categorías, un grupo "Generales" por coeficiente que abarca todas las unidades,
  cuatro tipos de unidad, los cuatro estados desactivados y el umbral de saldos chicos 500.00

### Requirement: Rangos de los parámetros

El lector SHALL aceptar sólo: tasa mensual entre 0 y 10 inclusive con hasta dos decimales; días de
gracia enteros entre 0 y 31; forma de cálculo `proporcional_por_dia` o `mes_entero`; fondo de reserva
entre 0 y 100 con hasta dos decimales; factor por estado entre 0 y 100; cargo fijo por estado como
monto válido no negativo; umbral de saldos chicos como monto válido no negativo, escrito como texto;
listas de categorías, grupos, tipos y estados no vacías y con claves únicas en minúsculas.

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

#### Scenario: Umbral de saldos chicos inválido

- **WHEN** el umbral falta, está vacío o en blanco, es `"-0.01"`, tiene tres decimales o viene como
  número YAML (`500`)
- **THEN** el lector falla nombrando el campo del umbral, sin repetir el valor recibido

#### Scenario: Umbral en cero

- **WHEN** el umbral es `"0.00"`
- **THEN** el lector acepta el archivo
