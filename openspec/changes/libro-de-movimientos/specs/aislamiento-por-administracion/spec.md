# Spec Delta

## ADDED Requirements

### Requirement: Las tablas del libro son de sólo agregar

Las seis tablas del libro (`cuenta`, `emision`, `evento_de_emision`, `obligacion`, `movimiento`,
`imputacion`) SHALL estar en la lista única de tablas de sólo agregar, nacer con sus triggers por fila,
de `TRUNCATE` y por sentencia, y pasar al rol de arranque después de migrar, como `configuracion_versionada`.
La tabla de candados por cuenta MUST quedar aislada por administración y fuera de esa lista.

#### Scenario: El paso de roles verifica las seis por el efecto

- **WHEN** corre `roles despues` sobre una base con `0023`
- **THEN** las seis tablas quedan del rol de arranque y su bloqueo se prueba con `UPDATE` y `DELETE` sin
  filas y con `TRUNCATE ... CASCADE`, exigiendo el texto de cada una

#### Scenario: Una tabla del libro sin declarar

- **WHEN** en una copia se saca `movimiento` de la lista de tablas de sólo agregar
- **THEN** el test que compara la lista con el catálogo falla nombrando `movimiento`

#### Scenario: La API no arranca con una tabla del libro del migrador

- **WHEN** `imputacion` queda con dueño `proptech_migrador`
- **THEN** la API y el worker no arrancan y el log nombra `imputacion`

#### Scenario: Una tabla homónima en otro esquema no hace pasar el chequeo

- **WHEN** existe `otro.movimiento` del rol de arranque y `public.movimiento` es del migrador, en
  cualquier orden de creación
- **THEN** el chequeo de arranque falla nombrando `movimiento`

#### Scenario: El candado no es de sólo agregar

- **WHEN** se lista la tabla de candados por cuenta
- **THEN** tiene RLS forzada con la política por administración, y no está en la lista de sólo agregar

#### Scenario: Un candado borrado no abre un hueco

- **WHEN** se borra la fila de candado de una cuenta y después dos transacciones registran a la vez un
  pago en esa cuenta
- **THEN** las dos se serializan igual y ninguna imputa sobre la foto de la otra
