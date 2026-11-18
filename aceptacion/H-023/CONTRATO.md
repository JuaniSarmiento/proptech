# Contrato que asume la aceptación de H-023

Caja negra por la API real, sobre H-018 a H-022 (sus contratos siguen vigentes). Si el constructor necesita
cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-023), `openspec/changes/pagos-informados/design.md` (E10, E13), R25 (vigente por D-163),
D-163 (P29), D-166, R20.

## Quién puede

Como H-022: sólo `revertir_o_reimputar_pago` (super admin y administrador principal); el orden 404 → 403 → 404 del
pago → 422 → 409.

## `POST /api/complejos/{id}/pagos/{pago_id}/reimputacion`

Cuerpo `{"desde_unidad_id": "<uuid>", "hacia_unidad_id": "<uuid>", "motivo": "<texto>"}`. **200** `{"pago_id":
"<uuid>", "estado": "confirmado"}` (un pago reimputado sigue confirmado).

Validaciones, en este orden: `motivo` de 3 a 500 caracteres (422 `motivo`); `hacia_unidad_id` inexistente o de otro
edificio (**404**); la misma unidad que `desde_unidad_id` (422 `hacia_unidad_id`); el pago no está `confirmado` (409
`{"detail": "conflicto", "campo": "pago", "motivo": "estado"}`); `desde_unidad_id` no es la unidad **vigente** de
ninguna parte del pago (422 `desde_unidad_id`).

La **unidad vigente** de una parte es la de su movimiento vigente: el `pago` de H-020 o, después de reimputar, el
`reimputacion` crédito de la unidad a la que se movió.

En **una** transacción, con los candados de las dos cuentas en orden:

1. **Origen**: un `reimputacion` (débito) con `corrige_a` el movimiento vigente de la parte, por su importe y con el
   motivo; la reversión de sus ajustes enlazados y el `interes_por_reversion` de P29, como H-022.
2. **Destino**: un `reimputacion` (crédito) por el importe de la parte, `fecha_valor` la fecha de la transferencia,
   `enlazado_a` el débito del origen, imputado con R04 a la fecha de la transferencia (D-166), con su ajuste de
   interés (H-021) si corresponde. Lo registra
   `proptech_core.cuenta_corriente.aplicacion.pagos.registrar_pago` (con el tipo `reimputacion`; la firma es libre),
   llamada como atributo del módulo en el momento, así la aceptación la puede hacer fallar.
3. Los movimientos nuevos con su fila en `movimiento_de_pago` (papel `reimputacion` para los dos `reimputacion`, y
   los de H-021 y H-022 para ajustes, reversiones e interés por reversión).
4. El evento `reimputado` con el motivo y una fila en `auditoria` con `accion` `reimputar_pago_informado`.

Si falla un paso no queda **ninguno**: la API responde 500 (el middleware convierte la excepción, L-094).

Después, revertir el pago (H-022) revierte el movimiento **vigente** de cada parte (el `reimputacion` crédito del
destino), no el del origen. Reimputar dos veces la misma parte en carrera: una gana; la otra no escribe nada (409 o
422).

## El libro de los ejemplos

Como H-020 a H-022: emisiones con `registrar_emision`, vencimiento el día 10, 3% mensual proporcional, gracia 0;
"hoy" es el 18/11/2026.
