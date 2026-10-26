# Spec Delta

## ADDED Requirements

### Requirement: Cada versión lleva su umbral de saldos chicos

Cada versión de configuración SHALL guardar el umbral de saldos chicos de R30 como monto no negativo
(D-109.3). Si una versión nueva no lo trae (ausente o `null`), MUST tomar el de la versión
inmediatamente anterior por `vigente_desde`, aunque sea futura, y si no hay ninguna, el de
`parametros.yaml` (D-114.1). La lectura MUST devolverlo como texto con dos decimales.

#### Scenario: Versión nueva sin umbral

- **WHEN** un edificio tiene vigente una versión con umbral "300.00" y se crea una versión nueva
  cambiando sólo la tasa
- **THEN** la versión nueva tiene umbral "300.00" y la anterior sigue igual

#### Scenario: Hereda de la anterior por fecha, aunque sea futura

- **WHEN** v1 rige desde hoy con umbral "300.00", v2 está programada para diciembre con "700.00", y se
  crea v3 para enero sin umbral
- **THEN** v3 tiene "700.00"; y una v4 creada para noviembre sin umbral tiene "300.00"

#### Scenario: Null explícito

- **WHEN** el cuerpo de una versión nueva trae el umbral en `null`
- **THEN** el resultado es el mismo que si el campo no viniera

#### Scenario: Primera versión de un edificio nuevo

- **WHEN** se crea un edificio con su configuración inicial sin umbral
- **THEN** la respuesta es 201 y la primera versión tiene el umbral de `parametros.yaml`, "500.00"

#### Scenario: Umbral explícito

- **WHEN** un cliente de la API crea una versión con umbral "750.00", o en el alta del edificio con
  "0.00"
- **THEN** la versión queda con ese valor y la lectura lo devuelve igual (en el 4a no hay pantalla que
  lo cargue)

#### Scenario: Umbral inválido

- **WHEN** el umbral llega como `500` (número JSON), "-1.00", "1.001" o "abc", en una versión o en el
  alta de un edificio
- **THEN** la respuesta es 422 nombrando el umbral, sin repetir el valor, y no se crea nada

#### Scenario: Versiones anteriores a este cambio

- **WHEN** se migra una base con versiones creadas antes de este cambio
- **THEN** cada una queda con umbral "500.00", y ninguna otra columna cambia

#### Scenario: El umbral no se edita por SQL

- **WHEN** `proptech_app` intenta `UPDATE` del umbral de una versión existente
- **THEN** la base lo rechaza por permisos (SQLSTATE `42501`), y como rol dueño lo rechaza el trigger
  de bloqueo
