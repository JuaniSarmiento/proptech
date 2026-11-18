# Contrato que asume la aceptación de H-020

Caja negra por la API real, como H-018 y H-019 (sus contratos siguen vigentes). Si el constructor necesita
cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-020), `openspec/changes/pagos-informados/design.md` (E6, E13), D-166, R04, R05, R11,
R19.

## Quién puede

Por edificio, en el orden de H-018: edificio fuera del alcance o de otra administración, **404**; sin
`confirmar_pago_informado` en ese edificio, **403** (el vecino, el consejo, el contador y el auxiliar); el
pago que no es de ese edificio (o no existe), **404** `{"detail": "no encontrado"}`; después el cuerpo (422) y
el estado (409).

## `POST /api/complejos/{id}/pagos/{pago_id}/confirmacion`

Cuerpo vacío (`{}`). **200** `{"pago_id": "<uuid>", "estado": "confirmado"}`. En **una** transacción:

- Por cada parte, un movimiento del libro tipo `pago`, crédito, con el importe de la parte, `fecha_valor` igual a
  la fecha de la transferencia, en la cuenta de la unidad de la parte, y su fila en `movimiento_de_pago` con papel
  `pago`.
- **R04 a la fecha de la transferencia (D-166)**: las imputaciones de ese movimiento van primero, con R04, a la
  deuda calculada como si las emisiones con período posterior a la fecha de la transferencia no existieran (ni
  sus obligaciones ni sus intereses); lo que sobra, con R04, a la deuda real que queda; lo que sobra después
  queda como crédito a favor (R05).
- El evento `confirmado` en `evento_de_pago`.
- Con `cbu_origen`, una fila en `cbu_de_unidad` por cada unidad de las partes.
- Una fila en `auditoria` con `accion` `confirmar_pago_informado`.

El libro lo escribe `proptech_core.cuenta_corriente.aplicacion.pagos.registrar_pago`, que `pagos` llama **una
vez por parte**, buscándola como atributo del módulo en el momento de llamarla (`from
proptech_core.cuenta_corriente.aplicacion import pagos as libro_de_pagos` y después
`libro_de_pagos.registrar_pago(...)`), así la aceptación la puede reemplazar con `monkeypatch` para hacer
fallar la segunda parte.

**Confirmar dos veces** (seguidas o en carrera): **200** con el mismo cuerpo, y un solo movimiento por parte y un
solo evento `confirmado`. **Confirmar un pago rechazado o revertido**: **409** `{"detail": "conflicto", "campo":
"pago", "motivo": "estado"}`.

## `POST /api/complejos/{id}/pagos/{pago_id}/rechazo`

Cuerpo `{"motivo": "<texto>"}`, de 3 a 500 caracteres sin contar los espacios de los bordes (si no, **422** con
`campo` `motivo`). **200** `{"pago_id": "<uuid>", "estado": "rechazado"}`. Deja el evento `rechazado` con el motivo
y una fila en `auditoria` con `accion` `rechazar_pago_informado`; no escribe nada en el libro. Rechazar uno
confirmado: **409** como arriba. Rechazar dos veces: 200 la primera; la segunda, **409**.

## Lo que ve el vecino

Después del rechazo, `GET .../pagos` (H-018) muestra el pago `rechazado` con su `motivo`.

## El libro de los ejemplos

La aceptación arma las emisiones con `registrar_emision` del libro (4b, 4c): septiembre, octubre y noviembre de
2026 con vencimiento el día 10, 3% mensual proporcional y gracia 0. "Hoy" (`proptech_api.pagos.hoy`) es el
18/11/2026.
