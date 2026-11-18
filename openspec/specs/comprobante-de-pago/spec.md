# comprobante-de-pago Specification

## Purpose
El comprobante de un pago se descarga sólo con un link firmado que vence, y sólo lo pide quien puede ver
ese pago (D-070, E11).

## Requirements

### Requirement: El comprobante se descarga con un link firmado

`POST .../pagos/{id}/comprobante/enlace` SHALL responder 201 `{url, vence_en}` a 15 minutos a quien puede ver
ese pago (el vecino de una de sus unidades o el personal con `confirmar_pago_informado`); a otro, 404.
`GET /api/comprobantes/descarga?token=` sin sesión responde 200 con los bytes y su tipo; vencido, 410;
alterado, de otra administración o de un tipo de enlace distinto, 403.

#### Scenario: Descarga

- **WHEN** el administrador pide el enlace del comprobante de un pago y lo abre
- **THEN** descarga los mismos bytes que se subieron

#### Scenario: Un token de expensa no sirve para un comprobante

- **WHEN** se usa en la descarga de comprobantes un token firmado para una expensa
- **THEN** responde 403
