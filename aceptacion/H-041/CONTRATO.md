# Contrato que asume la aceptación de H-041

El certificado de libre deuda (change 10b `condonacion-judicial-y-libre-deuda`). Caja negra por la API real, con la
identidad inyectada. Fuente: `HISTORIAS.md` (H-041), R21, D-171 y D-172. Si el constructor necesita cambiar algo de
esto, frena y lo pide. Los nombres, rutas y claves de abajo los fija esta aceptación; las claves de cada objeto son
**exactamente** las listadas (los tests comparan el conjunto).

## El día de hoy

`proptech_api.libre_deuda.hoy` es una dependencia de FastAPI sin parámetros que devuelve la fecha de hoy en Mendoza
(`date`). La aceptación la reemplaza por el 18/11/2026 con `app.dependency_overrides` (L-090).

## Quién puede

Acción nueva `emitir_libre_deuda` en `Accion` y en `_MATRIZ`: **sólo el super admin** (D-172.2; que lo emita también el
administrador principal es la pregunta P72, no se asume). Es también vocabulario de auditoría: una migración la suma a
`accion_de_auditoria` (sube y baja como las de 10a). La piden las dos rutas de abajo, `POST` y `GET`.

Orden de chequeo (D7): edificio inexistente, de otra administración o fuera del alcance de la persona, **404**
`{"detail": "no encontrado"}`; sin `emitir_libre_deuda`, **403** con `detail` `{"codigo": "sin_permiso", "detalle":
"sin_permiso", "permiso_faltante": "emitir_libre_deuda"}` (administrador principal y por edificio, contador, auxiliar,
consejo y el vecino del edificio: 403; un administrador de otro edificio: 404); la unidad (que no existe, es de otro
edificio o de otra administración, aunque exista: 404 con el mismo cuerpo exacto); el cuerpo (422).

## `POST /api/complejos/{complejo_id}/unidades/{unidad_id}/libre-deuda`

Cuerpo `{"fecha_de_corte": "AAAA-MM-DD"}`, sólo esa clave. **422** si falta, es `null`, no es una fecha ISO válida o es
**posterior a hoy** (hoy es válido; una fecha pasada se acepta, con lo que el libro sabía a esa fecha). **201** con el
certificado, ya guardado. Cada pedido crea un certificado nuevo con otro `id`, aunque el corte se repita.

### El certificado (la misma forma en `POST` y en `GET`)

| clave | qué es |
|---|---|
| `id` | UUID del certificado, único |
| `unidad_id` | UUID de la unidad |
| `fecha_de_corte` | `AAAA-MM-DD` |
| `emitido_en` | instante de la emisión, ISO con zona horaria |
| `saldo` | `capital + intereses`, texto con dos decimales, nunca número |
| `capital` | lo que se debe de capital (todo componente que no es interés) de las obligaciones **con vencimiento hasta el corte**, a esa fecha |
| `interes_corrido` | el interés de R03 corrido hasta el corte que el libro todavía no registró (R21, D-081): texto con dos decimales, `"0.00"` sin vencimientos impagos; **no suma al `saldo`** ni a `intereses` |
| `intereses` | los intereses **registrados en el libro** con fecha valor hasta el corte, que se deben a esa fecha |
| `libre_de_deuda` | `true` si y sólo si `saldo` es `"0.00"` |
| `en_revision` | lista de pagos informados sin confirmar (ver abajo) |
| `vencen_despues` | lista de cuotas liquidadas con vencimiento posterior al corte (ver abajo) |
| `huella` | SHA-256 en hexadecimal minúscula (64 caracteres) de la foto del certificado |
| `en_gestion_judicial` | booleano; **por ahora siempre `false`** (C06: la marca llega con H-042, que le agrega la leyenda al PDF) |
| `enlace` | `{"url": "/api/libre-deuda/descarga?token=...", "vence_en": "<ISO con zona>"}`, firmado al responder |

- **Qué sabe el libro a la fecha de corte** (C02, C03): cuentan las obligaciones con vencimiento `<=` corte; los
  intereses con `fecha_valor` `<=` corte; los créditos (`pago` y el resto) con `fecha_valor` `<=` corte, **imputados
  con lo que valía a esa fecha**. Un movimiento posterior al corte no cambia el certificado, por más que se haya
  registrado hoy. Un pago informado y confirmado hoy con transferencia anterior al corte **sí** resta, porque el libro
  lo registra con la fecha de la transferencia (D-166, D-171.3). El libro se lee, no se escribe.
- **Nunca estima** (N04): nada de cargos aprobados sin liquidar ni gastos del período en curso en el saldo. El interés
  corrido de R21 (D-081) va **aparte**, en `interes_corrido` (C08). `capital` e `intereses` son
  **residuales** a esa fecha; la aceptación no fija cómo se reparte un pago entre ambos, sólo que suman `saldo`.
- **`interes_corrido`** (C08): el cálculo de dominio de la emisión (`calcular_intereses_del_corte`, R03 del 4c) para un
  corte en la fecha de corte sobre el libro tal como está: cobra los días desde el vencimiento más uno hasta el corte que
  ningún interés registrado cubre (0,1% por día sobre el capital impago en el proporcional). No se registra en el libro
  ni se suma al saldo. Se guarda en la foto y entra en la huella. El PDF lleva una línea "Interés corrido" con el
  monto (`100,00`).
- **`en_revision`**: un elemento por pago informado de la unidad que sigue en estado `informado` (no confirmado, no
  rechazado, no revertido) con `fecha_de_transferencia` `<=` corte. Claves exactas: `pago_id`, `importe` (la parte que ese
  pago carga **a esa unidad**), `fecha_de_transferencia` (`AAAA-MM-DD`), `banco` y `numero_de_operacion`. Orden: por
  fecha de transferencia y, ante empate, por `pago_id`. No resta del saldo.
- **`vencen_despues`**: un elemento por obligación no anulada con vencimiento posterior al corte y emitida (existente en
  el libro hoy). Claves exactas: `periodo` (`AAAA-MM-01`), `vencimiento` (`AAAA-MM-DD`) e `importe` (lo pendiente de
  esa obligación a la fecha de corte, texto con dos decimales). Orden por período ascendente. No suma al saldo.
- **`huella`**: determinística. Depende del contenido (unidad, corte, saldo, capital, intereses, `en_revision`,
  `vencen_despues`) y **no** del `id` ni de `emitido_en`: dos emisiones con el mismo corte y el libro sin cambios dan la
  misma; otra unidad, otro corte o un saldo distinto dan otra.

## `GET /api/complejos/{complejo_id}/unidades/{unidad_id}/libre-deuda`

**200** con la lista de los certificados de esa unidad, el más nuevo primero (por `emitido_en`), cada uno con la forma de
arriba y un `enlace` recién firmado. Lista vacía si no hay ninguno. Mismos 403 y 404 que el `POST`.

## `GET /api/libre-deuda/descarga?token=...`

Pública por diseño: el token firmado ES la autorización, como `/api/documentos/descarga` (D-070, E13). **200** con
`application/pdf` (empieza con `%PDF`). El token es el de `proptech_core.compartido.enlaces.firmar` con tipo
**`libre_deuda`**, datos `{"a": "<administracion_id>", "i": "<certificado_id>"}`, vencimiento a los 15 minutos y la
clave `PROPTECH_CLAVE_DE_ENLACES`. Token alterado, mal formado o de otro tipo (por ejemplo `expensa`): **403**; vencido:
**410**; sin `token`: 403 o 422; firma buena de un certificado que no existe: **404**. El PDF lo hace WeasyPrint y lleva
el `id` del certificado (completo), el nombre del edificio, el identificador de la unidad, el corte como `DD/MM/AAAA`,
el saldo, el capital y los intereses como `20.720,00`, los pagos en revisión, las cuotas que vencen después y, sólo si
`saldo` es `"0.00"`, la leyenda "libre de deuda". **Siempre es el mismo archivo para ese certificado**: se guarda al
emitir y no se regenera (las dos descargas son idénticas byte a byte, antes y después de que el libro cambie).

## La tabla nueva: `certificado_de_libre_deuda`

De sólo agregar (D-016): la aplicación (`proptech_app`) lee e inserta; `UPDATE` y `DELETE` fallan. Con RLS por
administración como las demás y registrada como tabla protegida (`compartido/tablas_protegidas.py`, con su sonda).
Columnas que la aceptación lee: `id`, `administracion_id`, `complejo_id`, `unidad_id`, `fecha_de_corte` (`date`),
`saldo` (`NUMERIC(14,2)`), `capital`, `intereses`, `huella`, `emitido_por` (la persona en sesión) y `emitido_en`. El
resto (la foto de `en_revision` y de `vencen_despues`, `en_gestion_judicial`, el PDF) lo decide el constructor.

## Auditoría (C07)

Una fila de `auditoria` por emisión: `accion` `emitir_libre_deuda`, `entidad` `certificado_de_libre_deuda`, `entidad_id`
el certificado, `persona_id` el super admin en sesión, `detalle` exactamente `{"unidad_id": "<uuid>", "fecha_de_corte":
"AAAA-MM-DD"}` y `creado_en` el de la emisión. Un pedido rechazado (403, 404, 422) no guarda ni audita nada. Leer
(`GET`, descarga) no se audita.

## Lo que no hace

Emitir no escribe en el libro (N03): `movimiento`, `imputacion`, `obligacion` y `cuenta` quedan iguales. No hay otras
rutas de escritura. La marca de gestión judicial y su leyenda, la condonación y las pantallas son de H-042 y H-043.

## Los datos de la aceptación

Torre Ficticia (`1A` a `2B`, 3% mensual proporcional, gracia 0, vencimiento el día 10), con septiembre, octubre y
noviembre de 2026 emitidos con `registrar_emision` (1A 10.000,00; 1B 40.000,00; 2A 5.000,00; 2B 8.000,00) y hoy el
18/11/2026. `1A` no paga: al 05/11 capital 20.000,00 + intereses 720,00 (200,00 al 30/09 y 520,00 al 31/10) = 20.720,00,
con noviembre (10.000,00, vence el 10) aparte. `1B` pagó en término: saldo 0,00. `2B`: P1 8.000,00 transferidos el 20/10
y P3 1.000,00 transferidos el 12/11, ambos confirmados el 18/11, y P2 3.000,00 transferidos el 02/11 sin confirmar:
al 05/11 saldo 8.489,76 (16.000,00 + 489,76 - 8.000,00) y P2 en revisión; al 15/11, 15.489,76. Interés corrido: `1A` 100,00 al 05/11, 350,00 al 15/11 y 440,00 al 18/11; `2B` 40,80 al 05/11; `1B` 0,00.
