# Contrato que asume la aceptación de H-012

Caja negra sobre la misma ruta de H-011 (`GET /api/complejos/{id}/periodos/{AAAA-MM-01}/preliquidacion`,
ver `aceptacion/H-011/CONTRATO.md`, que sigue vigente). Si el constructor necesita cambiar algo de esta
lista, frena y lo pide.

Fuente: `HISTORIAS.md` (H-012), `design.md` (E6) y la spec `controles-antes-de-emitir`.

## `controles`

Lista de objetos `{"codigo", "nivel", "mensaje", "detalle"}`; `nivel` en `duro`, `bloqueante`,
`advertencia`; `mensaje` en español, no vacío. Orden fijo (los que estén activos, en este orden):

| `codigo` | `nivel` | Se dispara cuando | `detalle` |
|---|---|---|---|
| `saldos_iniciales_sin_validar` | duro | `complejo.estado_migracion` no es `confirmada` ni `sin_saldos_previos` | `{"estado_migracion": "<estado>"}` |
| `coeficientes_fuera_de_tolerancia` | duro | Generales o un grupo **activo** con `modo_de_coeficientes = 'propios'` informa `fuera_de_tolerancia` con `informar_coeficientes` (±0,0001, borde incluido) | `{"grupos": [{"grupo_id", "nombre", "suma", "diferencia"}]}` (suma y diferencia como las da `informar_coeficientes`, seis decimales) |
| `bloque_negativo` | duro | el neto de un bloque (ordinario o extraordinario) de un grupo en el período es menor que cero | `{"bloques": [{"grupo_id", "nombre", "bloque", "importe"}]}` |
| `doble_vencimiento_sin_regla` | duro | la versión de configuración vigente el primer día del período tiene `modalidad_de_vencimiento = 'doble'` | `{"modalidad": "doble"}` |
| `gastos_en_revision` | bloqueante | hay gastos del edificio en `en_revision` con período de imputación igual al período | `{"cantidad": N, "gastos": ["<uuid>", ...]}` |
| `gastos_sin_ia` | advertencia | ídem en `sin_ia`; el mensaje dice "hay N facturas sin cargar" | `{"cantidad": N, "gastos": [...]}` |
| `gasto_mensual_obligatorio_faltante` | advertencia | `obligatorios_faltantes` del 6 devuelve alguna categoría | `{"categorias": [{"categoria_id", "nombre"}]}` |

- Sólo el edificio pedido. Ningún control escribe nada.
- Los controles entran en la huella (cambia si cambia el conjunto de controles o su detalle).
- No existen `factura_duplicada` ni `ingresos_mayores_que_los_gastos` (D-157).
- Con un bloque negativo la preliquidación responde 200 igual (el reparto de un total negativo es el
  del positivo con el signo cambiado, R07).

## La pantalla

En `/edificios/{id}/liquidaciones/{AAAA-MM}` (H-011), una región (`role=region`) con nombre "Controles
antes de emitir" con una lista (`ul`/`ol`) y un `listitem` por control, en el orden de la API, que muestra su nivel **en texto** ("Duro", "Bloqueante",
"Advertencia") y su mensaje. Cada duro dice "no se puede aceptar". Sin controles, la región dice que no
hay controles pendientes. Sin errores de axe y sin scroll horizontal a 320 px.

### API falsa

| Edificio | `GET .../periodos/2026-11-01/preliquidacion` |
|---|---|
| `00000000-0000-0000-0000-000000001201` | la base de H-011 con `controles`: `saldos_iniciales_sin_validar` (duro, mensaje "Faltan validar los saldos iniciales del edificio"), `gastos_en_revision` (bloqueante, "Hay 1 factura leída con alertas") y `gastos_sin_ia` (advertencia, "Hay 2 facturas sin cargar") |
| `00000000-0000-0000-0000-000000001101` | (el de H-011) `controles: []` |
