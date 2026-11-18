# Contrato que asume la aceptación de H-021

Caja negra por la API real, sobre H-018 a H-020 (sus contratos siguen vigentes). Si el constructor necesita
cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-021), `openspec/changes/pagos-informados/design.md` (E7), D-082, D-084, D-085, D-166,
R03, R05, R11.

## El ajuste al confirmar

`POST .../pagos/{pago_id}/confirmacion` (H-020), por cada parte, **antes** de registrar el pago y en la misma
transacción:

1. Toma cada interés que cuenta en la cuenta de la parte y que pertenece a una **emisión con período posterior a
   la fecha de la transferencia** (D-166).
2. Lo recalcula sobre **sus mismos tramos** (los días de `tramo_de_interes` de ese movimiento, con la tasa, la
   forma y la gracia guardadas en esos tramos, nunca con la configuración de hoy) con la base que habría tenido con
   el pago imputado como manda E6 (R04 a la fecha de la transferencia).
3. Si lo registrado supera lo recalculado, registra la diferencia como un movimiento `ajuste_de_interes`
   (crédito) con destino ese componente de interés de esa obligación, `enlazado_a` el movimiento de interés que
   compensa, y su fila en `movimiento_de_pago` con papel `ajuste_de_interes`.

Después registra el pago (H-020). Las imputaciones del ajuste tienen un `orden` menor que las del pago.

**La vista de la fase 1** (R04 a la fecha de la transferencia, H-020) es el estado del libro con las emisiones de
período posterior a esa fecha tratadas como si no existieran; un ajuste `enlazado_a` un interés de esas emisiones
tampoco cuenta ahí (como D-085 con una emisión anulada).

**Lo que no entra**: si el componente de interés no tiene residual suficiente (otro crédito ya lo pagó), el ajuste
se registra hasta lo que entra (o no se registra si no entra nada) y la respuesta de la confirmación agrega
`"ajuste_sin_destino": "<importe>"` con lo que quedó afuera. Sin ese caso, la respuesta es la de H-020 (`{"pago_id",
"estado"}`), sin esa clave.

Un pago confirmado antes de la emisión siguiente no genera ajuste. Confirmar dos veces no registra otro ajuste.
Anular la emisión del interés compensado deja fuera al ajuste junto con él, sin contra-movimiento (D-085, ya en
`cuenta_corriente/dominio/estado.py`).

## La función de la diferencia

Pura, en `proptech_core.cuenta_corriente.dominio.intereses`:

```python
def diferencia_de_interes(
    tramos: Sequence[TramoGuardado], base_antes: Callable[[date], Decimal], base_despues: Callable[[date], Decimal]
) -> Dinero: ...
```

donde `TramoGuardado` es un dataclass del mismo módulo con `desde`, `hasta` (fechas), `tasa_mensual`
(`Porcentaje`), `forma_de_calculo` (`"proporcional_por_dia"` o `"mes_entero"`). Devuelve el interés de esos tramos
con `base_antes` menos el interés con `base_despues`, redondeando cada total una sola vez como
`calcular_intereses` (puede ser negativo). La aceptación la usa con `hypothesis`.

## El libro de los ejemplos

Como H-020: emisiones del libro con `registrar_emision`, vencimiento el día 10, 3% mensual proporcional (o mes
entero donde se dice), gracia 0. "Hoy" es el 18/11/2026; un crédito con fecha posterior se registra directo con
`registrar_credito` del libro.
