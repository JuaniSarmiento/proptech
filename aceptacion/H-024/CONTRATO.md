# Contrato que asume la aceptación de H-024

Caja negra por la API real, sobre H-018 a H-023 y H-012 y H-015 del 7 (sus contratos siguen vigentes). Si el
constructor necesita cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-024), `openspec/changes/pagos-informados/design.md` (E1, E11, E12), D-070, R34.

## El enlace del comprobante

### `POST /api/complejos/{id}/pagos/{pago_id}/comprobante/enlace`

Sin cuerpo. **201** `{"url": "/api/comprobantes/descarga?token=<token>", "vence_en": "<instante ISO con zona>"}`,
que vence a los **15 minutos**. Lo pueden pedir quienes pueden ver ese pago (H-018): el personal con
`confirmar_pago_informado` en el edificio y el vecino (propietario o inquilino) de una unidad de alguna de sus
partes. A cualquier otro (un vecino de otra unidad, otra administración, el edificio fuera del alcance), **404**
`{"detail": "no encontrado"}`. El consejo, el contador y el auxiliar: **403** si el edificio está en su alcance.

### `GET /api/comprobantes/descarga?token=<token>`

Sin sesión: el token es la autorización. **200** con los bytes exactos que se subieron y `content-type` el tipo
detectado (`image/png`, `image/jpeg` o `application/pdf`). Token vencido: **410**. Token alterado, de otra
administración, mal formado o **firmado para otro tipo de enlace** (el de una expensa de H-015): **403**. Y al revés:
un token de comprobante en `GET /api/documentos/descarga` (H-015) también da **403**.

### La firma compartida

La firma HMAC-SHA256 con `PROPTECH_CLAVE_DE_ENLACES` pasa a `proptech_core.compartido.enlaces` con un **tipo** dentro
del cuerpo firmado; `proptech_core.liquidacion.aplicacion.enlaces.firmar_enlace` (H-015) conserva su firma y su
contrato. Para fabricar un token vencido, la aceptación usa:

```python
proptech_core.pagos.aplicacion.enlaces.firmar_enlace_del_comprobante(
    *, administracion_id: UUID, pago_id: UUID, vence_en: datetime, clave: str
) -> str
```

El token nunca lleva datos personales (sólo identificadores, tipo y vencimiento).

## El control de pagos sin confirmar

La preliquidación (`GET /api/complejos/{id}/periodos/{AAAA-MM-01}/preliquidacion`, H-011 y H-012) suma al final de
`controles`:

```json
{"codigo": "pagos_sin_confirmar", "nivel": "advertencia", "mensaje": "<texto>",
 "detalle": {"cantidad": 2, "total": "45000.00"}}
```

con los pagos del edificio que siguen `informado` (ni confirmados, ni rechazados). Sin pagos informados, no aparece.
Es una advertencia: no frena la emisión (H-013).
