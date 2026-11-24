# morosidad Specification

## Purpose
El personal del edificio ve quién debe, cuánto y desde cuándo, calculado desde el libro (R20, R30, HU-A8,
D-167), y quien puede lo baja en Excel con los mismos números.

## Requirements

### Requirement: La morosidad lista sólo las unidades con deuda vencida

`GET /api/complejos/{id}/morosidad` SHALL devolver, a hoy, una fila por cuenta de unidad con total vencido
mayor que cero, con su unidad, sus propietarios, su etiqueta de cobranza, total vencido, capital, intereses,
liquidaciones vencidas, el vencimiento más viejo impago y los días desde ese vencimiento.

#### Scenario: Moroso crítico y unidad al día

- **WHEN** `1A` debe septiembre, octubre y noviembre y `2B` pagó todo
- **THEN** `1A` aparece primera con etiqueta `moroso_critico` y `2B` no aparece

#### Scenario: Deuda pagada en partes

- **WHEN** una unidad paga una parte de su deuda vencida y después el resto
- **THEN** después del primer pago su total vencido baja en lo imputado y después del segundo deja de aparecer

### Requirement: La etiqueta es la del libro

La etiqueta y el total vencido de cada fila MUST ser los de `situacion_del_edificio` a la misma fecha; una
unidad con una sola liquidación vencida, o con total vencido menor al umbral, no es moroso crítico.

#### Scenario: Una sola liquidación vencida

- **WHEN** `1B` debe sólo noviembre
- **THEN** su etiqueta es `con_deuda_vencida`, no `moroso_critico`

### Requirement: Intereses registrados y antigüedad desde el vencimiento

Los intereses de cada fila SHALL ser el interés registrado e impago de sus obligaciones vencidas, sin estimar
el corrido desde el último corte; la antigüedad SHALL salir de la obligación vencida más vieja con algo impago,
capital o interés, contada desde su vencimiento.

#### Scenario: Sólo queda el interés de la más vieja

- **WHEN** de septiembre quedó impago sólo el interés y octubre sigue impago
- **THEN** la fila dice vencida desde el 10/09/2026

### Requirement: Quién ve y quién exporta la morosidad

Ver la morosidad MUST requerir `ver_morosidad` (super admin, administrador, contador, auxiliar y consejo en su
alcance) y exportarla `exportar_morosidad` (super admin, administrador y contador); fuera del alcance, 404; sin
la acción, 403. La respuesta no trae email, teléfono ni DNI.

#### Scenario: El vecino no ve la morosidad

- **WHEN** una propietaria del edificio pide la morosidad
- **THEN** responde 403 con `permiso_faltante` `ver_morosidad`

#### Scenario: El consejo ve pero no exporta

- **WHEN** el consejo del edificio pide la morosidad y después el Excel
- **THEN** la primera da 200 y la segunda 403 con `permiso_faltante` `exportar_morosidad`

### Requirement: Leer la morosidad no escribe

Pedir la morosidad o su Excel MUST NOT escribir en el libro ni en la auditoría.

#### Scenario: El libro queda igual

- **WHEN** se pide la morosidad
- **THEN** movimientos, imputaciones, obligaciones y auditoría quedan iguales

### Requirement: El Excel trae los mismos números

`GET /api/complejos/{id}/morosidad/excel` SHALL devolver un `.xlsx` con las mismas filas, en el mismo orden y
con los mismos montos que la lectura, escritos como números con formato de pesos, y la fila de totales.

#### Scenario: Celda por celda

- **WHEN** el administrador baja el Excel
- **THEN** cada monto de cada fila es un número igual al centavo al de la API

### Requirement: La pantalla de la morosidad

La pantalla del edificio SHALL mostrar "Morosidad" en el menú sólo a quien tiene `ver_morosidad`, con el
resumen, la lista y la fecha de los intereses, y el botón de exportar sólo a quien tiene `exportar_morosidad`.

#### Scenario: El consejo no ve el botón de exportar

- **WHEN** el consejo abre la morosidad
- **THEN** ve la lista y no ve "Exportar a Excel"
