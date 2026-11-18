# Spec Delta

## Purpose

Suma a los controles de R34 el de los pagos informados que siguen sin confirmar (8, E12).

## MODIFIED Requirements

### Requirement: Cada control con su nivel, su mensaje y dónde

La preliquidación SHALL traer `controles`, una lista de objetos con `codigo`, `nivel` (`duro`,
`bloqueante` o `advertencia`), `mensaje` y `detalle`, en este orden fijo: `saldos_iniciales_sin_validar`,
`coeficientes_fuera_de_tolerancia`, `bloque_negativo`, `doble_vencimiento_sin_regla` (duros);
`gastos_en_revision` (bloqueante); `gastos_sin_ia`, `gasto_mensual_obligatorio_faltante`, `pagos_sin_confirmar` (advertencias).
Sólo mira el edificio pedido. No MUST existir un control de factura duplicada (lo garantiza
`uq_gasto_factura`) ni de ingresos mayores que los gastos (R38 no existe).

#### Scenario: Saldos iniciales sin validar

- **WHEN** la migración del edificio está `pendiente`
- **THEN** aparece `saldos_iniciales_sin_validar`, duro; con `confirmada` o `sin_saldos_previos`, no

#### Scenario: Coeficientes fuera de tolerancia

- **WHEN** los coeficientes de Generales suman 0,9998
- **THEN** aparece `coeficientes_fuera_de_tolerancia`, duro, con el grupo, la suma `0.999800` y la
  diferencia `-0.000200`; con 0,9999 no aparece

#### Scenario: Bloque negativo

- **WHEN** una nota de crédito de noviembre de $60.000 sobre una factura de octubre deja el ordinario de
  Generales de noviembre en −$10.000
- **THEN** aparece `bloque_negativo`, duro, con el grupo, el bloque y el importe, y la preliquidación
  responde igual

#### Scenario: Doble vencimiento

- **WHEN** la configuración vigente tiene vencimiento doble
- **THEN** aparece `doble_vencimiento_sin_regla`, duro

#### Scenario: Gastos en revisión

- **WHEN** hay un gasto del período en revisión
- **THEN** aparece `gastos_en_revision`, bloqueante, con la cantidad y los ids, y el gasto no entra en el
  cálculo

#### Scenario: Facturas sin cargar

- **WHEN** hay dos gastos del período sin IA
- **THEN** aparece `gastos_sin_ia`, advertencia, con "hay 2 facturas sin cargar"

#### Scenario: Gasto mensual obligatorio faltante

- **WHEN** la categoría Seguridad es obligatoria mensual y no tiene un gasto aprobado en el período
- **THEN** aparece `gasto_mensual_obligatorio_faltante`, advertencia, con la categoría; desaparece al
  aprobar un gasto de Seguridad

#### Scenario: Pagos sin confirmar

- **WHEN** el edificio tiene dos pagos informados sin confirmar ni rechazar, por $30.000 y $15.000
- **THEN** aparece `pagos_sin_confirmar`, advertencia, al final de la lista, con la cantidad 2 y el total
  `45000.00`; no frena la emisión, y con los dos confirmados o rechazados no aparece
