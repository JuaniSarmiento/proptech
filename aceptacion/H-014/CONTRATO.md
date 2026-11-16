# Contrato que asume la aceptación de H-014

Caja negra por la API real, como H-011 a H-013 (sus contratos siguen vigentes). Los pagos se registran con
`cuenta_corriente.aplicacion.creditos.registrar_credito` (tipo `pago`, el 8 no existe) y los créditos de
corrección con `correcciones.corregir` (4b). Si el constructor necesita cambiar algo, frena y lo pide.

Fuente: `HISTORIAS.md` (H-014), `design.md` (E9, E10, E11, E14), D-157 y la spec `ciclo-de-la-liquidacion`.

## Estado de una liquidación

`GET /api/complejos/{id}/liquidaciones/{liquidacion_id}` (H-013) suma `"estado"`: `emitida`,
`distribuida` o `anulada`, y `"distribucion"`: `null` o `{"origen": "manual"|"email"|"portal",
"en": "<instante>"}`, y `"anulacion"`: `null` o `{"motivo", "por": "<persona_id>", "en"}`.

### `GET /api/complejos/{id}/liquidaciones`

Lista `[{"liquidacion_id", "periodo", "estado", "total", "emitida_en"}]`, de la más nueva a la más vieja,
con permiso `ver_liquidaciones`. **El consejo no ve las `emitida` sin distribuir** (P39, D-157): no
aparecen en su lista y su `GET` por id da 404. Contador y administradores ven todas.

## Distribuir

### `POST /api/complejos/{id}/liquidaciones/{liquidacion_id}/distribucion`

Sin cuerpo. Permiso `emitir_y_distribuir_liquidacion`. **200** `{"estado": "distribuida"}`, con origen
`manual`, quién y cuándo, y una auditoría `emitir_y_distribuir_liquidacion`. **409** `{"detail":
"conflicto", "campo": "estado", "motivo": "ya_distribuida" | "anulada"}` si ya estaba distribuida o
anulada. 404 como siempre.

### El puerto (E9)

`proptech_core.liquidacion.aplicacion.distribucion.registrar_distribucion(sesion, *, emision_id: UUID,
origen: str, persona_id: UUID | None, request_id: UUID) -> bool`: en la transacción del llamador, registra
el evento si no estaba y devuelve `True`; si ya estaba distribuida devuelve `False` sin escribir
(idempotente, gana el primero). Sobre una anulada lanza el `Conflicto` de `cuenta_corriente` (o uno propio
que la ruta traduce a 409). La ruta manual lo usa con `origen="manual"`.

## Anular

### `POST /api/complejos/{id}/liquidaciones/{liquidacion_id}/anulacion`

Cuerpo `{"motivo": "<1 a 500, no en blanco>"}`. Permiso `anular_liquidacion` (super admin y administrador
principal; el de edificio 403). Bajo el candado de E5 (la fila de `complejo` antes que las cuentas):

- 422 sin motivo o en blanco.
- **409** `{"detail": "conflicto", "campo": "estado", "motivo": "ya_distribuida" | "anulada"}`.
- **409** `{"detail": "conflicto", "campo": "periodo", "motivo": "periodo_siguiente_emitido"}` si hay una
  emisión sin anular de un período posterior del mismo edificio (P26).
- **200** `{"estado": "anulada"}`: llama a `anular_emision` del libro y audita `anular_liquidacion` en la
  misma transacción. No modifica ni borra ninguna fila de `movimiento`, `obligacion` ni `imputacion`.

**D8 (D-157)**: después de anular, un crédito de corrección (`correccion`) imputado a una obligación de la
emisión anulada queda **retenido**: el estado de la cuenta (`lecturas.estado_de_cuenta`) lo cuenta en
`credito_a_favor_retenido`, nunca en `credito_a_favor_aplicable`, y la re-emisión no lo imputa. Un `pago`
imputado a esa emisión vuelve como crédito a favor aplicable, con su `fecha_valor` original (P38), y la
re-emisión lo imputa.

## Cargo cobrado de menos (E11)

### `POST /api/complejos/{id}/unidades/{unidad_id}/cargos-cobrados-de-menos`

Cuerpo `{"operacion_id": "<uuid>", "obligacion_origen_id": "<uuid>", "importe": "1500.00", "componente":
"ordinaria"|"fondo_de_reserva"|"extraordinaria", "motivo": "<1 a 500>"}`. Permiso `corregir_movimiento`.
**201** `{"cargo_id", "obligacion_id", "obligacion_origen_id", "importe", "componente", "vencimiento",
"motivo", "registrado_por", "registrado_en"}`. 422 con importe ≤ 0, sin motivo o componente inválido; 404 si
la obligación de origen no es de esa unidad o de ese edificio. Mismo `operacion_id` y cuerpo: replay.

Crea una **obligación nueva sin emisión** en la cuenta de la unidad, con el importe en el componente, el
período de la obligación de origen y vencimiento el día del registro (fecha de Mendoza); su interés corre
desde el día siguiente. Guarda motivo, origen, quién y cuándo en una tabla propia de sólo agregar
(migración nueva), y audita `corregir_movimiento`.

**Una sola migración nueva, la `0042`**: el evento `distribuida` en `evento_de_emision` (con su origen) y la
tabla del cargo cobrado de menos, de sólo agregar y protegida (ensayo de roles, L-083).

El caso de uso es `proptech_core.liquidacion.aplicacion.cargos.registrar_cargo_cobrado_de_menos(sesion,
identidad, *, complejo_id, unidad_id, obligacion_origen_id, operacion_id, importe: Dinero, componente:
str, motivo: str, request_id, reloj)`, con `reloj` como en `cuenta_corriente` para fijar el día.

## La pantalla

- `/edificios/{id}/liquidaciones/{AAAA-MM}` con el período ya emitido muestra la liquidación emitida (no la
  preliquidación): el estado en texto ("Emitida", "Distribuida" o "Anulada") y el total.
- Con estado `emitida`: botones "Distribuir" y "Anular". "Anular" abre una confirmación con un campo
  "Motivo" obligatorio ("Confirmar" deshabilitado hasta escribirlo). Los dos piden confirmación.
- Con estado `distribuida`: ninguno de los dos botones.

### API falsa

| Edificio | `GET .../liquidaciones` y `GET .../periodos/2026-11-01/preliquidacion` | Escrituras |
|---|---|---|
| `00000000-0000-0000-0000-000000001401` | una liquidación `emitida` de noviembre (total `191500.00`), id `00000000-0000-0000-0000-000000014011`; la preliquidación da 409 `periodo_emitido` | `POST .../distribucion` y `.../anulacion` 200 y guardan la última escritura |
| `00000000-0000-0000-0000-000000001402` | la misma, `distribuida`, id `00000000-0000-0000-0000-000000014021` | — |
