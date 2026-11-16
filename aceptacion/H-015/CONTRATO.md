# Contrato que asume la aceptación de H-015

Caja negra por la API real y las funciones de aplicación nombradas abajo, como H-011 a H-014 (sus contratos
siguen vigentes). Si el constructor necesita cambiar algo, frena y lo pide.

Fuente: `HISTORIAS.md` (H-015), `design.md` (E12, E13), D-060 (lo investigado el 15/11/2026: el CCyC pide
archivar las liquidaciones, art. 2067 inc. i; la Ley 941 de CABA sirve de modelo de contenido, no es
exigencia en Mendoza), D-070, D-106 y D-158 (H-016, el corte del worker).

## Los documentos

- Al **emitir** (la transacción de H-013), por cada unidad con obligación se crean dos documentos en
  estado `pendiente`: variante `completa` y variante `sin_extraordinaria` (la del inquilino, D-106).
  Después de confirmar, se encola la tarea `generar_pdf_de_expensa` por documento con la `Cola` de la app
  (`request.app.state.cola`). **Si encolar falla (Redis caído), la emisión responde 201 igual** y los
  documentos quedan `pendiente`.
- `proptech_core.liquidacion.aplicacion.documentos.generar_documento(sesion, *, documento_id: UUID,
  renderizar: Callable[[str], bytes] | None = None) -> None`: arma el HTML de la expensa desde lo
  **guardado** en la liquidación (nunca recalculado), lo convierte a PDF (por defecto WeasyPrint;
  `renderizar` permite inyectar otro) y lo guarda: el documento pasa a `generado` con los bytes, su SHA-256
  y la fecha. Si `renderizar` lanza, pasa a `fallido` con un `motivo` y no lanza. Sobre un `generado` no hace
  nada (el PDF archivado no se reescribe nunca, CCyC art. 2067 inc. i).
- La tarea del worker `generar_pdf_de_expensa` (registrada en `AjustesDelWorker.functions`) llama a
  `generar_documento` **a través de `ejecutar_con_corte`** (H-016) con una cota propia.
- El worker tiene además un barrido periódico (`cron_jobs` de ARQ) que reencola los `pendiente`.

### `GET /api/complejos/{id}/liquidaciones/{liquidacion_id}/documentos`

Permiso `ver_liquidaciones` (con la regla del consejo de H-014). **200** `[{"documento_id", "unidad_id",
"identificador", "variante", "estado", "motivo"}]`, por orden natural de unidad y después variante
(`completa` antes que `sin_extraordinaria`).

### `POST /api/complejos/{id}/liquidaciones/{liquidacion_id}/documentos/reproceso`

Permiso `emitir_y_distribuir_liquidacion`. Pasa los `fallido` a `pendiente` y encola todos los
`pendiente`. **202** `{"encolados": N}`. Si la cola falla: **503** y los documentos quedan `pendiente`.

## El PDF

Texto extraíble (la aceptación lo lee con `pypdf`, que entra como dependencia de desarrollo). La variante
`completa` de una unidad trae, como texto:

- el nombre del edificio y el identificador de la unidad;
- el **código para la transferencia** (R19): las iniciales en mayúscula de las palabras del nombre del
  edificio, un guion y el identificador (`Torre Ficticia`, `1B` → `TF-1B`);
- el período en palabras (`noviembre de 2026`) y el vencimiento (`10/11/2026`);
- los bloques "Ordinaria" y "Extraordinaria" con sus categorías y los importes de la unidad; el fondo de
  reserva; cada cargo particular con su concepto; los intereses; el **saldo anterior** de la foto; el
  total; todos con punto de miles y coma decimal (`48.350,00`).

La variante `sin_extraordinaria` es igual sin el bloque extraordinario: ni sus categorías ni su importe, y
su total es el de la unidad menos la extraordinaria (`33.350,00` para `1B`).

## Los enlaces firmados (D-070, E13)

### `POST /api/complejos/{id}/documentos/{documento_id}/enlace`

Cuerpo `{"variante": "completa" | "sin_extraordinaria"}` (el `documento_id` de esa variante). **201**
`{"url": "/api/documentos/descarga?token=<token>", "vence_en": "<instante ISO>"}`, que vence a los 15
minutos. Pueden pedirlo los perfiles con `ver_liquidaciones` y el **vecino de esa unidad**: el propietario,
las dos variantes; el **inquilino, sólo `sin_extraordinaria`** (pedir la completa da 403). Un vecino de otra
unidad: 404. Un documento que no está `generado`: **409** `{"detail": "conflicto", "campo": "documento",
"motivo": "no_generado"}`.

### `GET /api/documentos/descarga?token=<token>`

Sin sesión: el token es la autorización. **200** `application/pdf` con los bytes archivados. Token vencido:
**410**. Token alterado o inválido (otro documento, otra administración, firma mal): **403**. El token es
un HMAC-SHA256 con la clave de la configuración `PROPTECH_CLAVE_DE_ENLACES` (32 caracteres o más; la
aceptación la fija con `monkeypatch`) sobre administración, documento, variante y vencimiento; nunca lleva
datos personales.

`proptech_core.liquidacion.aplicacion.enlaces.firmar_enlace(*, administracion_id: UUID, documento_id:
UUID, variante: str, vence_en: datetime, clave: str) -> str` arma el token (la aceptación lo usa para
fabricar uno vencido).

## La pantalla

En la liquidación emitida (`/edificios/{id}/liquidaciones/{AAAA-MM}`, H-014), una región "Documentos" con
una fila por documento (identificador, variante en texto, estado en texto: "Pendiente", "Generado",
"Fallido") y un botón "Reprocesar" que manda el `POST .../reproceso`. Cada documento `generado` tiene un
botón "Descargar <identificador>" (más la variante) que pide el enlace y abre la URL.

### API falsa

| Edificio | Liquidación | Documentos |
|---|---|---|
| `00000000-0000-0000-0000-000000001501` | emitida, noviembre, id `00000000-0000-0000-0000-000000015011` | `1A` completa `generado` (id `...015101`), `1A` sin extraordinaria `fallido` con motivo "sin fuentes" (id `...015102`) |

`POST .../reproceso` responde 202 `{"encolados": 1}` y `POST .../enlace` 201 con una URL; los dos guardan la
última escritura.
