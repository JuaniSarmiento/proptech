# borrador-de-saldos Specification

## Purpose
Guarda los saldos previos importados en un borrador que no toca el libro, los compara unidad por unidad
con el control del administrador y registra la aceptación de las diferencias (R09, D-068).

## Requirements

### Requirement: La hoja Saldos se valida con el contrato del saldo inicial

Cada fila de `Saldos` SHALL validarse antes de guardar nada: `Unidad` existente en el padrón (el importado
en la misma subida o el existente); con `Período`, un mes no posterior al de la migración, `Vencimiento`
no posterior a la fecha de migración, `Concepto` (`Ordinaria`, `Fondo de reserva`, `Extraordinaria`) e
`Importe` ≥ 0; sin `Período`, total único; `Importe` negativo es crédito a favor (sin concepto ni
período); `Interés acumulado` ≥ 0. Las filas de un mismo período de una unidad MUST tener el mismo
vencimiento; un período que suma capital 0 con interés MUST ser error (E11 del 4c); una unidad no puede
mezclar filas con y sin período.

#### Scenario: Unidad que no existe

- **WHEN** la fila 5 de `Saldos` trae la unidad `9Z`
- **THEN** es error de la columna `Unidad` y no se guarda nada

#### Scenario: Vencimiento posterior a la migración

- **WHEN** la migración es el 15/10/2026 y una fila vence el 20/10/2026
- **THEN** es error de la columna `Vencimiento`

#### Scenario: Mismo período con dos vencimientos

- **WHEN** dos filas de septiembre de la unidad `1A` vencen el 10/09 y el 15/09
- **THEN** es error de la columna `Vencimiento` en la segunda

#### Scenario: Mezcla de detalle y total

- **WHEN** la unidad `1A` tiene una fila con período y otra sin período
- **THEN** es error de la columna `Período`

### Requirement: El borrador no toca el libro

Un archivo válido SHALL guardar sus filas de saldo y de control en el borrador de la importación, sin
crear cuentas, obligaciones ni movimientos. Una importación nueva con el padrón ya creado MUST descartar el
borrador anterior.

#### Scenario: Borrador sin movimientos

- **WHEN** se importa un archivo con saldos de 12 unidades
- **THEN** el libro del edificio no tiene ninguna cuenta, obligación ni movimiento nuevo

#### Scenario: Un borrador nuevo reemplaza al anterior

- **WHEN** después de un borrador se sube otro archivo de saldos (otro contenido) para el mismo edificio
- **THEN** el anterior queda descartado y la comparación muestra sólo el nuevo

### Requirement: La comparación muestra cada diferencia por unidad

La comparación SHALL listar cada unidad con saldo o control: saldo del borrador (capital más interés
importado menos crédito), saldo de control, diferencia; el total del borrador, el total de control y la
cantidad de unidades con diferencia. Una diferencia por unidad MUST mostrarse aunque los totales
coincidan.

#### Scenario: Dos errores de signo opuesto

- **WHEN** el borrador de `1A` tiene $10.000 más que su control y el de `2B` $10.000 menos
- **THEN** los totales coinciden y la comparación muestra las dos diferencias

#### Scenario: Unidad con control y sin saldo

- **WHEN** el control trae `3C` con $5.000 y el borrador no tiene filas de `3C`
- **THEN** la comparación muestra `3C` con borrador $0, control $5.000 y diferencia −$5.000

#### Scenario: Crédito a favor

- **WHEN** `4D` trae un importe de −$3.000 y su control es −$3.000
- **THEN** `4D` aparece sin diferencia

### Requirement: La comparación avisa el mes de la migración con mes entero

Cuando la forma de cálculo vigente a la fecha de migración es "mes entero", la comparación SHALL avisar,
para cada unidad con deuda, que el primer interés del sistema cubre el mes de la migración (E18 del 4c).

#### Scenario: Mes entero

- **WHEN** el edificio usa "mes entero" y migra el 15/10/2026
- **THEN** cada unidad con deuda muestra "El primer interés del sistema cubre octubre de 2026"

### Requirement: Las diferencias se aceptan con registro

Con diferencias, aceptarlas SHALL exigir el permiso `aceptar_diferencias_de_saldos` y registrar quién,
cuándo y la lista exacta de diferencias aceptadas; se audita. Un borrador sin diferencias no necesita
aceptación. Si el borrador cambia después, la aceptación MUST dejar de valer.

#### Scenario: Aceptar diferencias

- **WHEN** el administrador principal acepta las dos diferencias de `1A` y `2B`
- **THEN** queda una aceptación con esas dos diferencias, su autor y su fecha, y una fila de auditoría

#### Scenario: Administrador del edificio

- **WHEN** un administrador por edificio intenta aceptar diferencias
- **THEN** se rechaza con 403

#### Scenario: Borrador nuevo después de aceptar

- **WHEN** después de aceptar se sube otro borrador
- **THEN** la aceptación anterior no vale para el nuevo
