# Contrato que asume la aceptación de H-018

Caja negra por la API real, con la identidad inyectada como en H-011 a H-017. Si el constructor necesita
cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-018), `openspec/changes/pagos-informados/design.md` (E1 a E4), D-163 (P40), R10 y
R11.

## El día de hoy

`proptech_api.pagos.hoy` es una dependencia de FastAPI sin parámetros que devuelve la fecha de hoy
(`date`). Las rutas de pagos la usan para validar la fecha de la transferencia; la aceptación la reemplaza
por el 18/11/2026 con `app.dependency_overrides` (L-090).

## Quién puede

Por edificio, en este orden: el edificio fuera del alcance de la persona (o de otra administración) da
**404** `{"detail": "no encontrado"}`; sin `informar_pago` ni `confirmar_pago_informado` en ese edificio,
**403**; después la validación del pedido (**422**) y las unidades (**404**). Un vecino es una
`asignacion_rol` con rol `vecino`, `complejo_id`, `unidad_id` y `vinculo` (`propietario` o `inquilino`).

## `POST /api/complejos/{id}/pagos/lectura`

Multipart con el campo `archivo`. Acepta JPEG (empieza con `FF D8 FF`), PNG (`89 50 4E 47 0D 0A 1A 0A`) o
PDF (`%PDF-`), de hasta 10 MB (10 × 1024 × 1024 bytes); se decide por los primeros bytes, nunca por el nombre
ni el `content-type`. Otro contenido o más grande: **422** con `campo` `archivo` y nada guardado.

**201** `{"comprobante_id": "<uuid>", "lectura": "sin_ia", "propuesta": {"banco": null,
"numero_de_operacion": null, "fecha": null, "monto": null, "cbu_origen": null}}` mientras no haya adaptador
de IA configurado (H-019 lo agrega; sin `PROPTECH_OPENROUTER_API_KEY` sigue respondiendo `sin_ia`).

## `POST /api/complejos/{id}/pagos`

```json
{"comprobante_id": "<uuid>", "banco": "Banco Nación", "numero_de_operacion": "12-345.678",
 "fecha_de_transferencia": "2026-11-05", "monto": "43350.00", "cbu_origen": null,
 "partes": [{"unidad_id": "<uuid>", "importe": "43350.00"}]}
```

**201** `{"pago_id": "<uuid>", "estado": "informado"}`. No escribe nada en `movimiento`, `imputacion` ni
`obligacion`.

- `monto` e `importe`: texto con dos decimales exactos (`^[0-9]+\.[0-9]{2}$`), mayor que cero. Un número
  JSON, tres decimales o cero: 422 con `campo` `monto` (o `partes`).
- `partes`: una o más, sin unidades repetidas, que suman el monto: si no, 422 `partes`.
- `fecha_de_transferencia`: ISO, no posterior a hoy ni anterior a hoy menos 365 días: si no, 422
  `fecha_de_transferencia`.
- `banco` y `numero_de_operacion`: texto no vacío (sin contar espacios) de hasta 100 caracteres: si no, 422
  con su campo.
- `cbu_origen`: nulo o 22 dígitos: si no, 422 `cbu_origen`.
- `comprobante_id`: un comprobante subido **por la misma persona**, del mismo edificio y no usado por otro
  pago. Si no existe, es de otro edificio u otra administración, lo subió otra persona o ya se usó: 422
  `comprobante_id`.
- Unidades: el vecino sólo informa para unidades donde tiene asignación de vecino; el personal con
  `confirmar_pago_informado` para cualquier unidad del edificio. Una unidad que no cumple (ajena,
  inexistente o de otro edificio): **404** y nada creado.
- Número de operación: único por edificio entre los pagos no rechazados, comparando banco y número
  normalizados (sin espacios, guiones ni puntos, en minúscula y sin tildes). Repetido: **409**
  `{"detail": "conflicto", "campo": "numero_de_operacion", "motivo": "repetido"}`.

Orden de las validaciones (el 422 informa el **primero** que falla): la forma de cada campo en este orden,
`monto`, `partes` (al menos una, cada `importe` con su formato), `fecha_de_transferencia`, `banco`,
`numero_de_operacion`, `cbu_origen`; después que las partes sumen el monto y no repitan unidad (`partes`);
después el comprobante (`comprobante_id`); después las unidades (404); por último el número (409).

El cuerpo de un 422 es el de las rutas existentes: `{"detail": [{"loc": [..., "<campo>"], ...}]}`; la
aceptación lee el campo del último elemento de `loc`.

## Leer los pagos

- `GET /api/complejos/{id}/pagos`: **200** con una lista. El personal con `confirmar_pago_informado` ve
  todos los del edificio; un vecino, los que tienen alguna parte en una unidad donde tiene asignación.
  Cada elemento: `pago_id`, `estado` (`informado`, `confirmado`, `rechazado`, `revertido`), `motivo` (del
  rechazo o la reversión, o nulo), `banco`, `numero_de_operacion`, `fecha_de_transferencia`, `monto`,
  `partes` (`unidad_id`, `identificador`, `importe`).
- `GET /api/complejos/{id}/pagos/{pago_id}`: el mismo objeto; un pago que la persona no puede ver, de otro
  edificio u otra administración: **404**.

## La base

Migración `0044` (revisión `"0044"`, baja a `"0043"`). Tablas, todas con `administracion_id`, RLS habilitada
y forzada, protegidas por el rol de arranque (el rol de la app no tiene `UPDATE` ni `DELETE`):
`comprobante_de_pago`, `pago_informado`, `parte_de_pago`, `evento_de_pago`, `movimiento_de_pago` y
`cbu_de_unidad`.

El estado sale de `evento_de_pago`. La aceptación siembra un rechazo (rechazar es H-020) con el rol de la
app y el tenant fijado:

```sql
INSERT INTO evento_de_pago (administracion_id, pago_id, tipo, motivo, registrado_por)
VALUES (%s, %s, 'rechazado', 'Motivo ficticio', %s)
```

Así que `evento_de_pago` necesita esas columnas (las demás, con valor por defecto) y `tipo` admite
`rechazado`.
