# Contrato que asume la aceptación de H-022

Caja negra por la API real, sobre H-018 a H-021 (sus contratos siguen vigentes). Si el constructor necesita
cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-022), `openspec/changes/pagos-informados/design.md` (E8, E9, E13), D-083, D-085, D-163
(P29), D-166, R03, R18, R20.

## Quién puede

En el orden de H-020: edificio fuera del alcance, **404**; sin `revertir_o_reimputar_pago` (sólo el super admin y el
administrador principal lo tienen: el administrador de un edificio, el vecino, el consejo, el contador y el
auxiliar no), **403**; pago que no es del edificio, **404**; cuerpo, **422**; estado, **409**.

## `POST /api/complejos/{id}/pagos/{pago_id}/reversion`

Cuerpo `{"motivo": "<texto>"}`, de 3 a 500 caracteres sin los espacios de los bordes (si no, **422** `motivo`).
Sólo un pago `confirmado` (si no, **409** `{"detail": "conflicto", "campo": "pago", "motivo": "estado"}`). **200**
`{"pago_id": "<uuid>", "estado": "revertido"}`. En una transacción, con los candados de las cuentas de las partes:

1. **Por cada parte**, un movimiento `reversion_de_pago` (débito) con `corrige_a` el movimiento **vigente** de esa
   parte (el `pago` de H-020; en H-023, el `reimputacion` crédito si se reimputó), por su mismo importe, con el
   motivo, y su fila en `movimiento_de_pago` con papel `reversion_de_pago`. El par deja de contar
   (`_excluidos` de `estado.py`): la unidad vuelve a deber lo que debía sin ese pago.
2. Cada `ajuste_de_interes` enlazado a ese pago (H-021) se revierte con un movimiento con `corrige_a` el ajuste
   (sentido débito, el tipo que el libro admita para un contra-asiento), también con papel `reversion_de_pago`.
3. **P29 (D-163)**: cada interés que cuenta en esa cuenta, de una emisión con período posterior a la fecha de la
   transferencia (D-166), se recalcula sobre sus mismos tramos **sin** el pago (con `diferencia_de_interes` de
   H-021). Si lo recalculado supera lo registrado, la diferencia es un movimiento nuevo **`interes_por_reversion`**
   (débito, componente `interes`, la misma obligación, `enlazado_a` ese interés), con papel `interes_por_reversion`.
4. El evento `revertido` con el motivo y una fila en `auditoria` con `accion` `revertir_pago_informado`.

El pago original no cambia ni se borra: sigue en `GET .../pagos` con estado `revertido` y su motivo. Revertir dos
veces (seguidas o en carrera): la segunda, **409**; un solo `reversion_de_pago` por parte.

## `interes_por_reversion`

Un tipo nuevo de `tipo_de_movimiento` (débito), sembrado por una migración nueva con su ciclo (L-089). En el estado
de la cuenta: suma al debido del componente interés de su obligación; **no** genera interés (la base de
`_base_del_dia` nunca suma componentes de interés, R03); y deja de contar si deja de contar el interés al que está
`enlazado_a` (como el ajuste, D-085), sin contra-movimiento.

## Moroso crítico

Después de revertir, `cobranza.situacion_de_cuenta(sesion, cuenta_id=..., fecha=...)` (4c) da `moroso_critico`
según el libro, sin nada que actualizar.

## El libro de los ejemplos

Como H-020 y H-021: emisiones con `registrar_emision`, vencimiento el día 10, 3% mensual proporcional, gracia 0;
"hoy" es el 18/11/2026.
