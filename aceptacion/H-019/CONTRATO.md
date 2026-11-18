# Contrato que asume la aceptación de H-019

Caja negra por la API real, como H-018 (su contrato sigue vigente: `POST /api/complejos/{id}/pagos/lectura`,
`proptech_api.pagos.hoy`). Si el constructor necesita cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-019), `openspec/changes/pagos-informados/design.md` (E5), D-164.

## El puerto

`proptech_core.pagos.puertos.LectorDeComprobantes`: un `Protocol` con

```python
def leer(self, contenido: bytes, tipo: str) -> Mapping[str, object]: ...
```

`tipo` es `"image/jpeg"`, `"image/png"` o `"application/pdf"` (lo que decidió la validación de H-018 por los
primeros bytes). Devuelve la propuesta **cruda** con las claves `banco`, `numero_de_operacion`, `fecha`,
`monto` y `cbu_origen`; puede lanzar cualquier excepción.

## Cómo lo recibe la API

`proptech_api.pagos.lector` es una dependencia de FastAPI que devuelve `LectorDeComprobantes | None`. Por
defecto arma el adaptador de OpenRouter con la configuración, o devuelve `None` si falta
`PROPTECH_OPENROUTER_API_KEY` o `PROPTECH_OPENROUTER_MODELO`. La aceptación la reemplaza con
`app.dependency_overrides` por un lector falso o por el adaptador real con un transporte HTTP falso.

`proptech_api.pagos.tope_de_lectura` es una dependencia sin parámetros que devuelve los segundos del tope
(`20.0` por defecto); la aceptación lo baja a `0.3`.

## La lectura

`POST .../pagos/lectura` (H-018) llama al lector después de guardar el comprobante:

- Sin lector (`None`): `lectura` `sin_ia` y la propuesta vacía, sin llamar a la red.
- El lector lanza, o no devuelve dentro del tope: `lectura` `fallida`, propuesta vacía. **201** igual.
- El lector devuelve: `lectura` `ok` y la propuesta **validada** campo por campo; el que no cumple vuelve
  `null`:
  - `banco` y `numero_de_operacion`: texto no vacío de hasta 100 caracteres (sin espacios de los bordes).
  - `fecha`: fecha ISO real (`AAAA-MM-DD`), no posterior a hoy ni anterior a hoy menos 365 días.
  - `monto`: texto `^[0-9]+\.[0-9]{2}$` mayor que cero.
  - `cbu_origen`: 22 dígitos exactos.
  - Un valor que no es texto (número, lista, objeto) vuelve `null`. Claves de más se ignoran.
- La columna `lectura` de `comprobante_de_pago` guarda el resultado (`ok`, `fallida` o `sin_ia`) y la columna
  `propuesta` (jsonb) la propuesta validada, la misma que devuelve la API (o `null` sin lectura).
- Nada de la lectura crea un pago, un evento ni un movimiento.

## El adaptador de OpenRouter

`proptech_core.pagos.adaptadores.openrouter.LectorOpenRouter(clave: str, modelo: str, cliente: httpx.Client |
None = None)`, que cumple el puerto. Por pedido:

- `POST https://openrouter.ai/api/v1/chat/completions` con la cabecera `Authorization: Bearer <clave>`.
- Cuerpo JSON con `model` igual al modelo; `provider` igual a `{"zdr": true, "data_collection": "deny",
  "require_parameters": true}`; `response_format` con `type` `json_schema` y `json_schema` con `strict` `true` y
  un `schema` de tipo objeto cuyas `properties` son exactamente las cinco claves; sin `tools`.
- Los mensajes llevan el comprobante como URL de datos: `data:image/png;base64,<bytes>` (o `image/jpeg`) en
  una parte `image_url`, o `data:application/pdf;base64,<bytes>` para un PDF. Además, una instrucción fija.
  Nada más: ni el nombre de la persona, ni la unidad, ni el edificio.
- Lee `choices[0].message.content` como JSON y lo devuelve. Un estado HTTP que no es 2xx, un cuerpo que no
  es JSON o un contenido sin esas claves: lanza.
- La clave nunca aparece en un log ni en un mensaje de excepción.

## Configuración

`PROPTECH_OPENROUTER_API_KEY` (secreto, opcional) y `PROPTECH_OPENROUTER_MODELO` (opcional) en
`proptech_core/compartido/configuracion.py`, con su línea en la tabla de variables del README y en `08`.
