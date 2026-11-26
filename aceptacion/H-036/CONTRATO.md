# Contrato que asume la aceptación de H-036

Caja negra por la API real, con la identidad inyectada y la clave de enlaces `PROPTECH_CLAVE_DE_ENLACES` de prueba.
Fuente: `HISTORIAS.md` (H-036), D-169 y R12. Si el constructor necesita cambiar algo de esto, frena y lo pide.
Los códigos y nombres de abajo los fija esta aceptación (la historia sólo dice "el motivo" y "los datos del QR").

Dependencias nuevas que trae la construcción (D-169): `zxing-cpp` (leer el QR) y `pypdfium2` (rasterizar la primera
página del PDF). Los fixtures de la aceptación no las usan para generar (los arma `_qr.py` con Pillow y WeasyPrint);
si `zxingcpp` está instalado, el helper vuelve a leer cada fixture con él antes de subirlo.

## `POST /api/complejos/{complejo_id}/facturas`

Multipart con un único campo `archivo` (nombre, `content-type` y extensión no cuentan). Permiso
`cargar_gastos_y_preparar_liquidacion` (super admin, administrador principal o del edificio). Orden de los chequeos:
**404** `{"detail": "no encontrado"}` (edificio inexistente o que no alcanza) → **403** con
`detail.permiso_faltante` → **422** (archivo). El archivo se valida como el comprobante del 8: el tipo sale de los
primeros bytes (JPEG, PNG o PDF), no está vacío y mide **a lo sumo `TAMANO_MAXIMO` (10 MiB)**; si no, **422**. Sin el
campo `archivo` o sin multipart, **422**. Un 403, 404 o 422 no deja gasto, proveedor, archivo ni nada en el libro.

Un archivo con firma válida que no se puede abrir (imagen o PDF roto, una bomba de descompresión) **no es un 422 ni un
500**: se guarda y queda `sin_qr` con motivo `no_hay_qr`.

### 201: el gasto en borrador

Exactamente estas claves: las del gasto del 6 (`id`, `complejo_id`, `proveedor_id`, `categoria_id`, `grupo_id`,
`concepto`, `periodo`, `periodo_de_imputacion`, `tipo`, `importe`, `estado`, `cuit_emisor`, `punto_de_venta`,
`tipo_de_comprobante`, `numero_de_comprobante`, `documento_receptor`) más:

- `fecha_de_factura`: `AAAA-MM-DD` o `null` (columna nueva).
- `origen`: `"qr"` o `"sin_qr"` (columna nueva; los gastos cargados a mano del 6 quedan con `"manual"`).
- `motivo_sin_qr`: `null` si `origen` es `qr`; si no, uno de los códigos de abajo.
- `aviso`: texto o `null` (el del 6, idéntico).
- `factura`: `{"url": "/api/facturas/descarga?token=...", "vence_en": "<ISO con zona>"}`, vence a los 15 minutos.

`GET /api/gastos/{id}` y el listado del 6 devuelven las mismas claves **menos `aviso` y `factura`** (no hay link
permanente); `origen`, `motivo_sin_qr` y `fecha_de_factura` salen siempre.

### Con QR legible (`origen: "qr"`, `estado: "borrador"`)

- **Proveedor** (C01): por `cuit` del emisor **dentro del edificio** (los proveedores son del edificio). Si no existe se
  crea con `razon_social` `"CUIT <cuit>"`; si ya existe (lo cargó el 6) se reusa sin tocarlo. Se audita como el alta
  de proveedor del 6.
- `cuit_emisor`, `punto_de_venta`, `tipo_de_comprobante`, `numero_de_comprobante`: los enteros del JSON (`cuit`,
  `ptoVta`, `tipoCmp`, `nroCmp`) como texto decimal sin ceros a la izquierda ni `.0`.
- `fecha_de_factura`: el `fecha` del JSON. `documento_receptor`: `nroDocRec` como texto, o `null` si no viene.
- `importe`: **`importe × ctz`**, texto con dos decimales (Decimal, nunca float): 12100 × 65 = `"786500.00"`;
  100,5 × 1,5 = `"150.75"`. En pesos la cotización es 1.
- `concepto`, `categoria_id`, `grupo_id`, `periodo` y `periodo_de_imputacion` quedan **`null`**: el QR no los trae y los
  completa H-037 o la persona. `tipo` es `"ordinario"`. Hace falta una migración que los deje anulables (y `importe`,
  ver abajo) y las columnas nuevas; las restricciones del 6 que sigan valiendo con datos presentes se conservan.
- **Un gasto con esos campos vacíos no se aprueba**: `POST /api/gastos/{id}/aprobar` da **422** y el gasto queda en
  `borrador`. Los demás caminos del 6 (listado, detalle, `PATCH`) siguen andando con ellos.
- **Duplicado (N01)**: la clave de R12 (`cuit + ptoVta + tipoCmp + nroCmp`) dentro del edificio, igual que el 6 y
  también contra un gasto cargado a mano, en los dos sentidos: **409** `{"detail": "conflicto", "campo": "factura"}`,
  sin crear gasto, proveedor ni archivo. El mismo número con otro tipo, punto de venta o CUIT, o en otro edificio, no
  choca.
- **Receptor (C04)**: si `complejo.cuit` está cargado y `nroDocRec` existe y es distinto, `aviso` es el texto del 6
  (`_aviso_de_receptor_distinto`) y el gasto igual se crea. Sin `nroDocRec` o sin CUIT en el edificio, `aviso` es `null`.

### Sin QR legible (`origen: "sin_qr"`, `estado: "borrador"`)

Un gasto con **todos** los campos de datos `null` (`proveedor_id`, los cuatro de la factura, `importe`,
`fecha_de_factura`, `documento_receptor`, `concepto`, `categoria_id`, `grupo_id`, `periodo`,
`periodo_de_imputacion`), `aviso: null`, sin proveedor creado, y el archivo guardado con su `factura.url`. Como no hay
clave de duplicado, dos facturas sin QR conviven. `importe` pasa a ser anulable (en un `sin_qr` no hay con qué
llenarlo). El QR descartado no deja ningún dato a medias, ni en la respuesta ni en la base. Los códigos de
`motivo_sin_qr`:

| código | cuándo |
|---|---|
| `no_hay_qr` | ningún QR decodificable en el archivo (en un PDF, sólo se mira la **primera página**), o el archivo no se puede abrir |
| `dominio_ajeno` | hay un QR pero su texto no es `https://<host>/fe/qr/?p=...` con host **exactamente** `arca.gob.ar`, `www.arca.gob.ar`, `afip.gob.ar` o `www.afip.gob.ar` (nada de `startswith`, subdominios, sufijos ni `usuario@host`) |
| `version_desconocida` | el JSON no trae `ver`, o `ver` no es el entero `1` |
| `json_invalido` | `p` no es base64 válido, no decodifica a JSON, o el JSON no es un objeto |
| `importe_invalido` | `importe` ausente, no numérico (texto o booleano), `<= 0` o con más de dos decimales; `ctz` no numérico o `<= 0` |
| `datos_invalidos` | `cuit` que no es un CUIT válido (once dígitos, verificador módulo 11), `ptoVta`, `tipoCmp` o `nroCmp` ausentes o no enteros, o `fecha` que no es una fecha `AAAA-MM-DD` existente |

Si un archivo cumple varias, vale el primero de la tabla, de arriba abajo.

## La factura guardada y su link (C03)

El archivo (los bytes tal cual se subieron y su tipo) queda guardado, con RLS por administración como el comprobante
del 8, y no se baja con un `GET` autenticado: sólo con un link firmado.

- **`GET /api/facturas/descarga?token=...`**: pública, sin sesión; el token es la autorización y el tenant sale del token
  verificado. **200** con los bytes y su `content-type` (`image/png`, `image/jpeg` o `application/pdf`) y los
  encabezados `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`. **410** token vencido, **403** token
  alterado, de otro tipo, de otra administración o de un gasto que no existe, **422** sin `token`.
- El token es el de `proptech_core.compartido.enlaces.firmar` con tipo **`factura`** y datos `{"a": administracion_id,
  "g": gasto_id}`. Un token de `comprobante` o de `expensa` no baja una factura y uno de factura no baja un
  comprobante ni una expensa (403).
- **`POST /api/gastos/{gasto_id}/factura/enlace`** → **201** `{"url", "vence_en"}`, un link nuevo a pedido, con la regla de
  lectura del gasto (`ver_configuracion_del_edificio`). **404** si el gasto no existe, no alcanza (otro edificio u otra
  administración) o **no tiene factura** (se cargó a mano en el 6).

## Lo que no hace H-036

No llama a la IA (H-037), no aprueba, no emite ni toca el libro (`movimiento`, `obligacion`, `imputacion`, `emision`
siguen en cero), no tiene pantalla (6c) y no valida el CAE contra ARCA.

## Detalles que la construcción tiene que decidir y reportar

- La auditoría de `crear_gasto` y `crear_proveedor` para esta ruta (la aceptación no la compara).
- Cómo rasterizar el PDF (`pypdfium2` a escala suficiente) y el tope de píxeles de una imagen (la "bomba" de
  30000 x 30000 tiene que dar `sin_qr`, no un 500).
- Los tests viejos del 6 que fijen la lista exacta de claves del gasto se actualizan en la construcción, no acá.
