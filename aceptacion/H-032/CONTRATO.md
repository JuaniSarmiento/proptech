# Contrato que asume la aceptación de H-032

Caja negra por la API real de H-030/H-031 y el libro (`obligacion`, `movimiento`, `estado_de_cuenta`), con la identidad
inyectada y `proptech_api.morosidad.hoy` fijo en el 15/12/2026 (L-090). La emisión se hace por el camino real
(`GET .../preliquidacion` y `POST .../periodos/{p}/emision` con su huella), porque ahí se aplica el prorrateo
pendiente. Si el constructor necesita cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-032), D-168.5 y R32.

## `POST /api/complejos/{c}/unidades/{u}/cambios-de-titular`

`expensa_del_mes` acepta `"prorrateo"` (además de `"entera"`, el defecto). El período del cambio es el mes de `fecha`.

**201** con `expensa_del_mes: "prorrateo"`: las claves de H-030 más `prorrateo`, y `trasladado` y `cuenta_del_vendedor`
**sólo con `deuda_previa: "a_nombre_del_vendedor"`** (como en H-031: el prorrateo solo no las agrega). Con
`expensa_del_mes: "entera"` no hay clave `prorrateo`.

```
"prorrateo": {"estado": "aplicado" | "pendiente", "periodo": "AAAA-MM-01", "dias_del_vendedor": int,
              "dias_del_mes": int, "parte_del_vendedor": "0.00" | null}
```

Decisiones de forma de esta aceptación (las toma el orquestador al fijar el contrato; se cambian pidiéndolo):

- **D1. Cuándo es `aplicado`**: si el período ya tiene su emisión al registrar. Si no, `pendiente` con
  `parte_del_vendedor` nula; el `GET` del mismo cambio muestra `aplicado` y su parte apenas se emite el período.
  `dias_del_vendedor` = días del mes **anteriores** a la fecha (el día del cambio es del comprador: 0 si es el día 1);
  `dias_del_mes` los del mes calendario (febrero de 2028, 29).
- **D2. `parte_del_vendedor` es lo efectivamente trasladado** (suma de los tres componentes, texto con dos decimales),
  no la parte nominal: si la unidad ya pagó algo, es menor (D4). Con el día 1 es `"0.00"`.
- **D3. `GET .../cambios-de-titular`**: cada ítem con `expensa_del_mes: "prorrateo"` trae el mismo `prorrateo`
  (actualizado); los de `"entera"` no lo traen.
- **D4. Qué se traslada (C06)**: por componente, `max(parte_por_dias − ya_pagado, 0)`, donde `ya_pagado` es lo que la
  unidad pagó de ese componente de esa obligación (capital emitido menos impago, según el libro). Un pago se entiende
  imputado primero a los días del vendedor: baja lo que él debe y la unidad conserva lo que quedó de cada componente
  (`impago − trasladado`). **Es una lectura de "sólo se traslada lo impago de la parte del vendedor"; si el
  orquestador prefiere `min(parte, impago)`, se cambia acá y en `partes_esperadas` de `_h032.py`.**
- **D5. El cálculo (C02)**: por componente, `round_half_up(componente × dias_del_vendedor ÷ dias_del_mes, 2)` para el
  vendedor; la unidad conserva el resto. Los tres componentes de la obligación del mes (`ordinaria`,
  `fondo_de_reserva`, `extraordinaria`); nunca el interés (N05). El único traslado de la unidad en el mes por
  componente es un crédito `traslado` sobre la obligación del período, enlazado (`enlazado_a`, en cualquiera de los dos
  sentidos) a un único débito `traslado` del mismo importe y componente en la cuenta del vendedor, ambos con
  `operacion_id` no nulo. Sin parte (cero o todo pagado) no hay movimientos ni cuenta de persona nueva.
- **D6. El vendedor deudor**: la parte va a la cuenta de persona del `vendedor_deudor` (mismo campo y misma regla que
  H-031): se puede omitir con un solo vendedor; con dos vendedores y sin `vendedor_deudor`, 422 y no queda nada. A
  diferencia de H-031, `vendedor_deudor` también se acepta con `expensa_del_mes: "prorrateo"` y `deuda_previa:
  "en_la_unidad"`. La cuenta de persona se crea o se reutiliza (`uq_cuenta_persona`) cuando hay algo que trasladar.
- **D7. Los dos juntos (C05)**: `trasladado` sigue siendo sólo la deuda previa de H-031 (períodos anteriores al mes);
  el prorrateo va aparte en `prorrateo.parte_del_vendedor`. Las dos cosas van a la misma cuenta del vendedor, que debe
  la suma; la suma de las dos cuentas no cambia y nada se traslada dos veces.
- **D8. `aviso`**: como en H-031 D2, se calcula después de los traslados (lo que le queda a la unidad, o `null`).
- **D9. Pendiente (C04)**: mientras está pendiente no se escribe nada en el libro ni se crea la cuenta del vendedor. Al
  emitir (`POST .../emision`, 201), en la **misma transacción** de la emisión, después de crear las obligaciones, se
  aplica con el mismo traslado de H-031; repetir el mismo pedido de emisión (200) no escribe nada. Si el traslado falla,
  la emisión entera falla (≥ 400, o el error del servidor) y no queda emisión, liquidación, obligación ni movimiento; el
  cambio sigue `pendiente` y una emisión posterior lo aplica.

## Errores y rechazos

- **422** si `vendedor_deudor` falta con más de un vendedor, y para un segundo cambio con `"prorrateo"` en la misma
  unidad y el mismo período (pendiente o aplicado); en ese 422 no queda nada (libro, personas, asignaciones, cambios,
  auditorías). Un cambio con `"entera"` en esa unidad y período sigue siendo válido.
- **409** al anular (`POST .../liquidaciones/{id}/anulacion`) la liquidación de un período con prorrateo `aplicado`,
  con cualquier orden de llegada (ya emitido o aplicado al emitir): no cambia nada, ni auditoría de anulación, y la
  liquidación sigue `emitida`. Hasta que una historia posterior resuelva cómo deshacerlo (deuda a anotar en la ficha 4).

## Efectos que se verifican

- La unidad queda con `impago − trasladado` por componente; el vendedor debe lo trasladado (más lo de H-031 si lo hay);
  los `pago` de la unidad no se tocan.
- La parte trasladada no genera interés: al emitir un período siguiente la cuenta del vendedor no recibe `interes` ni
  crece su deuda, y la unidad paga interés sólo por lo que le quedó (comparada al centavo, ±0,05, con una unidad
  testigo de la misma obligación).
- El interés y el capital de períodos anteriores no se mueven con `deuda_previa: "en_la_unidad"`.
- Los cargos particulares entran sumados a la ordinaria (E15 de H-013) y hoy se prorratean con ella; **no se verifica**
  (deuda de N05).
