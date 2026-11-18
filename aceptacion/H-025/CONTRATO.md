# Contrato que asume la aceptación de H-025

Las pantallas de pagos en navegador real contra la API falsa (`web/e2e/api-falsa.ts`), más una ruta nueva de la API
real. Siguen vigentes los contratos de H-018 a H-024. Si el constructor necesita cambiar algo de esto, frena y lo
pide. Locators exactos y alertas filtradas por texto (L-085); cada e2e espera la escritura (L-087).

Fuente: `HISTORIAS.md` (H-025), `openspec/changes/pagos-informados/design.md` (E14), HU-V4, HU-A6, D-131.

## La ruta nueva de la API real

`GET /api/complejos/{id}/pagos/unidades`: **200** `[{"unidad_id": "<uuid>", "identificador": "1A"}, ...]`, en orden
natural, con las unidades para las que la persona puede informar: las suyas si es vecino (propietario o inquilino),
todas las del edificio si tiene `confirmar_pago_informado`. Sin `informar_pago` ni `confirmar_pago_informado`:
**403**; edificio fuera del alcance: **404**.

## Las pantallas

Todas dentro del edificio, con el menú lateral (`seccionesDelEdificio`):

- **Menú**: "Mis pagos" (`/edificios/{id}/mis-pagos`) sólo con `informar_pago` en ese edificio; "Pagos"
  (`/edificios/{id}/pagos`) sólo con `confirmar_pago_informado`. Los dos en el grupo "Liquidación".
- **`/edificios/{id}/mis-pagos`**: encabezado "Mis pagos"; un link "Informar un pago" a
  `/edificios/{id}/mis-pagos/informar`; una lista con nombre accesible "Pagos informados" con un `listitem` por pago
  que muestra el número de operación, el monto con punto de miles y coma decimal, el estado en texto ("Informado",
  "Confirmado", "Rechazado", "Revertido") y el motivo de un rechazo o una reversión.
- **`/edificios/{id}/mis-pagos/informar`**: encabezado "Informar un pago"; un campo de archivo con etiqueta
  "Comprobante". Al elegir el archivo manda `POST .../pagos/lectura` y muestra los campos con la propuesta: "Banco",
  "Número de operación", "Fecha de la transferencia" (`type="date"`), "Monto" y "CBU de origen". Si la lectura vuelve
  `fallida` o `sin_ia`, los campos quedan vacíos y aparece un `role="alert"` con "No pudimos leer el comprobante".
  Por cada unidad de `GET .../pagos/unidades`, un campo "Importe para <identificador>"; si hay una sola unidad, ya
  trae el monto. El botón "Enviar" manda `POST .../pagos` con lo que está en pantalla (las partes son las unidades
  con importe); la pantalla **no suma ni redondea**: si la API responde 422 con `campo` `partes`, muestra un
  `role="alert"` con "Las partes tienen que sumar el monto". Con 201, vuelve a "Mis pagos".
- **`/edificios/{id}/pagos`**: encabezado "Pagos"; una lista con nombre accesible "Pagos del edificio", un `listitem`
  por pago como en "Mis pagos" y, según su estado:
  - `informado`: botones "Confirmar" (abre un diálogo con un botón "Confirmar" que manda `POST .../confirmacion`) y
    "Rechazar" (diálogo con un campo "Motivo" y un botón "Rechazar" que manda `POST .../rechazo`);
  - `confirmado`: "Revertir" (diálogo con "Motivo" y un botón "Revertir", `POST .../reversion`) y "Reimputar"
    (diálogo con un `select` "Unidad de destino", "Motivo" y un botón "Reimputar", `POST .../reimputacion` con
    `desde_unidad_id` la unidad de la parte y `hacia_unidad_id` la elegida);
  - todos: "Ver comprobante", que manda `POST .../comprobante/enlace` y abre el comprobante por una ruta de Next
    (`/comprobantes/descarga?token=...`), porque Caddy no publica `/api/*`.
- Las tres pantallas pasan por la skill **impeccable**, sin scroll horizontal a 320 px y sin errores de axe.

## API falsa

| Edificio | Qué tiene |
|---|---|
| `00000000-0000-0000-0000-000000002501` | La lectura devuelve `ok` con banco "Banco Nación", número "12345678", fecha "2026-11-05", monto "43350.00", sin CBU, y `comprobante_id` `00000000-0000-0000-0000-000000025900`. `GET .../pagos/unidades`: para `user_vecina`, `1A` (`...025101`) y `2B` (`...025104`); para el resto, `1A`, `1B` (`...025102`), `2A` (`...025103`) y `2B`. `GET .../pagos`: cuatro pagos, `...025001` `informado` (número "11110001", $43.350,00, `1A`), `...025002` `confirmado` ("11110002", $37.425,00, `2B`), `...025003` `rechazado` ("11110003", motivo "El monto no coincide con el comprobante") y `...025004` `revertido` ("11110004", motivo "Cheque rechazado"). `POST .../pagos` responde 201 si las partes suman el monto y 422 `partes` si no. Confirmar, rechazar, revertir, reimputar y el enlace responden como la API real. Todas las escrituras guardan la última escritura. |
| `00000000-0000-0000-0000-000000002502` | Igual, pero la lectura devuelve `fallida` con la propuesta vacía. |

Identidad nueva `user_vecina`: la sesión trae sólo `informar_pago` en esos dos edificios (ninguna acción de
administración ni de todos los edificios). El resto de las identidades sigue "como el super admin" (que ya trae
`confirmar_pago_informado` y `revertir_o_reimputar_pago` en todos los edificios) y **no** tiene `informar_pago`.
