# Contrato que asume la aceptación de H-031

Caja negra por la API real de H-030 y el libro (`estado_de_cuenta`, tabla `movimiento`), con la identidad inyectada y
`proptech_api.morosidad.hoy` fijo en el 15/12/2026 (L-090). Si el constructor necesita cambiar algo de esto, frena y
lo pide.

Fuente: `HISTORIAS.md` (H-031), D-168.2 y R32.

## `POST /api/complejos/{c}/unidades/{u}/cambios-de-titular`

Suma al cuerpo de H-030: `deuda_previa: "a_nombre_del_vendedor"` (el otro valor sigue siendo `"en_la_unidad"`, el
defecto) y `vendedor_deudor` (id de persona, opcional si hay un solo vendedor). `expensa_del_mes` sigue en `"entera"`.

**201**: las claves de H-030 más `trasladado` (texto con dos decimales) y `cuenta_del_vendedor` (uuid). **Esas dos
claves sólo vienen con `a_nombre_del_vendedor`**; con el defecto la respuesta es la de H-030, sin ellas.

Decisiones de forma de esta aceptación (las toma el orquestador; se cambian pidiéndolo):

- **D1. Sin deuda previa**: `trasladado` es `"0.00"` y `cuenta_del_vendedor` es `null`. No se crea la cuenta de persona
  ni se escribe nada en el libro.
- **D2. `aviso`**: se calcula después del traslado. Es la deuda que le queda a la unidad (`{"deuda": "..."}`, o `null`
  si no queda), no la de antes.
- **D3. Cuándo se traslada**: lo impago (capital por componente e interés registrado, ya imputado) de las obligaciones
  de períodos **anteriores al mes de `fecha`** (cualquier día del mes: el 1 y el 30 de noviembre dan lo mismo). El mes
  del cambio y los siguientes no se tocan.
- **D4. `operacion_id`**: la criterio dice "el `operacion_id` del cambio", pero `uq_mov_operacion` lo hace único por
  movimiento. La aceptación sólo exige que cada `traslado` traiga un `operacion_id` no nulo (derivado del cambio, p. ej.
  `uuid5(cambio_id, ...)`, como las reversiones).
- **D5. Cuenta del vendedor**: `GET`/`estado_de_cuenta(cuenta_id)` tiene que funcionar sobre la cuenta de persona
  (`deuda` = lo trasladado). Una por (administración, edificio, persona): se reutiliza (`uq_cuenta_persona`).

## Movimientos `traslado`

Por cada obligación trasladada, en la cuenta de la unidad un crédito `traslado` con su `obligacion_id` (el
período de la obligación está entre los trasladados, ninguno posterior), y en la cuenta del vendedor un débito
`traslado` del mismo importe. Se enlazan con `enlazado_a` (en cualquiera de los dos sentidos; la aceptación acepta
cualquiera), uno a uno. La suma de los créditos y la de los débitos es `trasladado`. Los créditos de la unidad pueden
partirse por componente si el constructor lo necesita: la aceptación sólo agrupa por obligación y por importe total.

## Efectos que se verifican

- La cuenta de la unidad queda en cero por los períodos anteriores (cada componente) y no cambia lo posterior ni lo
  pagado (los `pago` y sus `imputacion` idénticos); la suma de las dos cuentas no cambia.
- `registrar_emision` no genera interés en la cuenta del vendedor (ni `interes` ni crecimiento de su deuda) y sigue
  generándolo en la unidad sólo sobre lo que le quedó (comparado al centavo contra una unidad testigo sin traslado).
- La cuenta de persona no aparece en `GET .../morosidad` ni en `cobranza.situacion_del_edificio`.
- Un `pago` posterior sobre la unidad no se imputa a la deuda trasladada (ni siquiera de más: el exceso queda a favor
  de la unidad).
- Un segundo cambio de la misma unidad traslada sólo lo que quedó impago desde entonces (nunca lo ya trasladado).

## Errores

**422** si `vendedor_deudor` no es uno de `vendedores`, o falta con más de un vendedor; los 422 de H-030 siguen. Todo
en una transacción: un 422 no deja movimientos, cuenta de persona nueva, fila de `cambio_de_titular`, auditoría,
persona nueva ni asignaciones cambiadas, y repetir el pedido corregido funciona y traslada una sola vez.

## Auditoría y tabla

La fila de `cambio_de_titular` guarda `deuda_previa = 'a_nombre_del_vendedor'`. El detalle de la auditoría sigue
exactamente como en H-030 (mismas claves; `deuda_previa` ya está en él).
