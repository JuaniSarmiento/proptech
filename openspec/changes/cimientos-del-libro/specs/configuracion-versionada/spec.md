# Spec Delta

## ADDED Requirements

### Requirement: Cada versión lleva su umbral de saldos chicos

Cada versión de configuración SHALL guardar el umbral de saldos chicos de R30 como monto no negativo
(D-109.3). Si una versión nueva no lo trae, MUST tomar el de la versión vigente del edificio, y en la
primera versión el de `parametros.yaml`. La lectura de versiones MUST devolverlo como texto con dos
decimales. Las versiones previas a este cambio MUST quedar con $500,00.

#### Scenario: Versión nueva sin umbral

- **WHEN** un edificio tiene vigente una versión con umbral "300.00" y el administrador crea una versión
  nueva cambiando sólo la tasa
- **THEN** la versión nueva tiene umbral "300.00" y la anterior sigue igual

#### Scenario: Primera versión de un edificio nuevo

- **WHEN** se crea un edificio y con él su primera versión de configuración
- **THEN** la versión tiene el umbral de `parametros.yaml`, "500.00"

#### Scenario: Umbral explícito

- **WHEN** el administrador crea una versión con umbral "750.00"
- **THEN** la versión queda con "750.00" y la lectura lo devuelve igual

#### Scenario: Umbral inválido

- **WHEN** el umbral llega como `500` (número JSON), "-1.00", "1.001" o "abc"
- **THEN** la respuesta es 422 nombrando el umbral, sin repetir el valor, y no se crea la versión

#### Scenario: Versiones anteriores a este cambio

- **WHEN** se migra una base con versiones creadas antes de este cambio
- **THEN** cada una queda con umbral "500.00", y ninguna otra columna cambia

#### Scenario: El umbral no se edita por SQL

- **WHEN** `proptech_app` intenta `UPDATE` del umbral de una versión existente
- **THEN** la base lo rechaza, igual que con cualquier otra columna de la versión
