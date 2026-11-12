# confirmacion-de-saldos Specification

## Purpose
Confirma el borrador de saldos: el libro recibe el saldo inicial (4c), el edificio pasa a `confirmada` y
el importador se cierra (R09, D-068).

## Requirements

### Requirement: Confirmar carga el saldo inicial en una sola transacción

Confirmar SHALL, en una transacción y con el complejo bloqueado: verificar el permiso
`confirmar_saldos_iniciales`, el estado `pendiente`, que exista un borrador vigente y que sus diferencias
estén aceptadas si las hay; llamar a `registrar_saldo_inicial` con las filas del borrador traducidas
(concepto a componente, importe negativo a crédito), con `operacion_id` igual al id de la importación y el
origen `importador` con el nombre del archivo; pasar el edificio a `confirmada` y la importación a
`confirmada`; y auditar. Si algo falla, nada queda escrito.

#### Scenario: Confirmar sin diferencias

- **WHEN** el administrador principal confirma un borrador sin diferencias de 12 unidades
- **THEN** el libro tiene las obligaciones, los intereses importados y los créditos del borrador, el
  edificio está en `confirmada` y queda una fila de auditoría

#### Scenario: La suma importada coincide con el archivo

- **WHEN** se confirma un archivo cuyos saldos suman $215.300 de capital, $6.000 de interés y $3.000 de
  crédito
- **THEN** los totales que devuelve la carga son exactamente esos

#### Scenario: Diferencias sin aceptar

- **WHEN** el borrador tiene diferencias sin aceptar
- **THEN** confirmar se rechaza con conflicto en `diferencias` y el libro no cambia

#### Scenario: Repetir la confirmación

- **WHEN** se confirma dos veces la misma importación
- **THEN** la segunda se rechaza con conflicto en `estado_migracion` y existe una sola carga

### Requirement: Confirmar respeta permisos, tenant y concurrencia

Confirmar SHALL exigir `confirmar_saldos_iniciales` (super admin o administrador principal) en un edificio
de la administración de la sesión. Dos confirmaciones simultáneas, o una confirmación y un "sin saldos
previos" simultáneos, MUST serializarse por el candado del complejo: una gana y la otra da conflicto.

#### Scenario: Administrador del edificio

- **WHEN** un administrador por edificio intenta confirmar
- **THEN** se rechaza con 403

#### Scenario: Otra administración

- **WHEN** la administración B confirma una importación de A
- **THEN** se rechaza con 404

#### Scenario: Confirmar contra sin saldos previos

- **WHEN** una conexión confirma la importación y otra, a la vez, confirma "sin saldos previos"
- **THEN** una termina y la otra da conflicto en `estado_migracion`

### Requirement: El importador cerrado no acepta nada

Con el edificio en `confirmada`, subir otra importación, aceptar diferencias o confirmar MUST rechazarse
con conflicto en `estado_migracion`.

#### Scenario: Subir después de confirmar

- **WHEN** el edificio está confirmado y se sube otro archivo
- **THEN** se rechaza con conflicto en `estado_migracion`

### Requirement: La web nombra el estado confirmado

El resumen del edificio SHALL mostrar `confirmada` como "Saldos iniciales confirmados", y el paso de
saldos previos MUST ofrecer "Importar desde Excel" y "Confirmar sin saldos previos" mientras la migración
esté pendiente.

#### Scenario: Resumen confirmado

- **WHEN** el edificio está en `confirmada`
- **THEN** el resumen dice "Saldos iniciales confirmados" y no ofrece importar
