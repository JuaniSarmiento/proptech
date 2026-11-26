# Contrato que asume la aceptación de H-034

Las pantallas del cambio de titular y de las cuentas de vendedores, en navegador real contra la API falsa
(`web/e2e/api-falsa.ts` y `web/e2e/escenarios-cambio-de-titular.ts`, que escribe la aceptación). Siguen vigentes
los contratos de H-030, H-031, H-032 (`POST` y `GET .../unidades/{u}/cambios-de-titular`) y H-033
(`.../cuentas-de-vendedores`): la API falsa contesta con esas formas exactas. Si el constructor necesita cambiar algo
de esto, frena y lo pide. Locators exactos (L-085). No se toca la API falsa: la verificación la restaura del SHA
aprobado. Las pantallas pasan por la skill **impeccable**. Los montos se formatean con `dinero` de `lib/formato.ts`
(punto de miles, coma decimal) tal como vienen: la pantalla no suma, no resta ni redondea nada (N02).

Fuente: `HISTORIAS.md` (H-034), D-168, R32.

## Permisos y menú

- `registrar_cambio_de_titular` (del edificio, en la sesión): el padrón ofrece los dos enlaces de abajo y la pantalla
  del cambio funciona. Sin ella, los enlaces no están y la pantalla (`/cambio-de-titular`, directa por URL) muestra el
  estado "sin permiso" de `Estados` con el permiso faltante `registrar_cambio_de_titular` y ningún formulario (la API
  da 403 a la lectura).
- `ver_morosidad`: `seccionesDelEdificio` suma **"Cuentas de vendedores"** (`/edificios/{id}/cuentas-de-vendedores`), en el
  grupo "Liquidación". Sin esa acción en el edificio no está en el menú y la pantalla muestra "sin permiso" con
  `ver_morosidad`.
- `confirmar_pago_informado`: el cobro (el formulario "Registrar cobro") sólo existe con esa acción. Quien tiene
  `ver_morosidad` y no esta (contador, auxiliar, consejo) lee la lista y el detalle y no cobra.

## El padrón (`/edificios/{id}/unidades`)

Con `registrar_cambio_de_titular`, cada fila suma dos enlaces (en una columna propia o junto al identificador):

| Enlace | Nombre accesible (exacto) | Destino |
|---|---|---|
| Cambiar titular | `Cambiar titular de 1A` (con el identificador de la unidad) | `/edificios/{id}/unidades/{unidadId}/cambio-de-titular` |
| Historial | `Ver historial de cambios de titular de 1A` | el mismo destino, con `#historial` |

Después de un cambio, el padrón (al volver) ya muestra a los compradores: el panel "Editar unidad" de la unidad lista
como vecinos a los compradores (y ya no a los vendedores).

## `/edificios/{id}/unidades/{unidadId}/cambio-de-titular`

Lee `GET .../cambios-de-titular` y el padrón (`GET .../unidades`) y `/api/personal` desde el servidor de Next; los
propietarios actuales y los nombres de las personas salen de ahí (propietario = asignación `vecino` con vínculo
`propietario`; el inquilino no se ofrece). Dentro del edificio, con su menú lateral.

- Encabezado (`heading`) **"Cambiar titular de 1A"** y un enlace **"Volver al padrón"** (`/edificios/{id}/unidades`).
- Un `form` con nombre accesible **"Cambiar titular de 1A"**, con:
  - **"Fecha del cambio"** (`input type=date`).
  - Un grupo (`role=group`, `fieldset`) **"Vendedores"** con un checkbox por propietario actual, con el nombre de la
    persona como etiqueta ("Ana Prueba").
  - Un grupo **"Compradores"** con **"Nombre del comprador 1"** y **"Email del comprador 1 (opcional)"**; el botón
    **"Agregar otro comprador"** suma "Nombre del comprador 2" y "Email del comprador 2 (opcional)", y así.
  - Un grupo **"Expensa del mes"** con los radios **"Entera"** (marcado de entrada) y **"Prorrateo por días"**, y estas
    líneas visibles, cada una con su opción: "La expensa del mes completa queda en la unidad." y "El vendedor paga
    los días del mes anteriores a la fecha del cambio y la unidad el resto."
  - Un grupo **"Deuda previa"** con los radios **"Queda en la unidad"** (marcado de entrada) y **"A nombre del
    vendedor"**, con estas líneas: "La deuda de meses anteriores queda en la unidad y el comprador la hereda; se le
    avisa el monto." y "La deuda de meses anteriores pasa a una cuenta del vendedor y la unidad queda sin ella."
  - Un `select` **"Vendedor que queda con la deuda"** con una opción por vendedor marcado. **Sólo existe en el DOM**
    cuando hay más de un vendedor marcado **y** está "A nombre del vendedor" o "Prorrateo por días" (con un solo
    vendedor la pantalla manda ese como `vendedor_deudor` o lo omite; con la expensa entera y la deuda en la unidad
    no se manda).
  - El botón **"Registrar cambio de titular"** (un solo paso, sin confirmación aparte).
- La pantalla manda el cuerpo de H-030 a H-032 (`fecha` `AAAA-MM-DD`, `vendedores` ids, `compradores` con `nombre` y
  `email` o `null`, `expensa_del_mes`, `deuda_previa`, `vendedor_deudor`) y no calcula nada.
- **Resultado (C02).** Con el 201, una región (`role=region`) con nombre **"Resultado del cambio de titular"**, que
  sigue visible hasta que se recarga, con:
  - el `heading` **"Cambio de titular registrado"**;
  - **"Aviso de deuda"** y, si `aviso` no es nulo, **"La unidad queda con una deuda de 45.230,10."**; si es nulo,
    **"La unidad no tiene deuda para avisar."**;
  - sólo si la respuesta trae `trasladado` y `cuenta_del_vendedor` no nula: **"Deuda pasada al vendedor"**, el monto
    ("45.230,10") y el enlace **"Ver la cuenta del vendedor"** a `/edificios/{id}/cuentas-de-vendedores/{cuenta_del_vendedor}`;
  - sólo si trae `prorrateo`: **"Prorrateo de la expensa"** y su estado. `pendiente`: la palabra **"Pendiente"**, el
    período como **"11/2026"** (mm/aaaa) y "9 de 30 días" (`dias_del_vendedor` de `dias_del_mes`); no dice
    "Aplicado". `aplicado`: **"Aplicado"**, la parte del vendedor ("8.333,33") y "9 de 30 días"; no dice "Pendiente";
  - el enlace **"Volver al padrón"**.
- **Historial (C03).** Una lista (`role=list`) con nombre **"Historial de cambios de titular"**, en la misma pantalla
  (ancla `#historial`), un `listitem` por cambio **en el orden de la API** (el más nuevo primero), con: la fecha
  `dd/mm/aaaa`; los vendedores y los compradores por nombre, separados por coma (los vendedores se resuelven por
  `/api/personal`); la expensa ("Entera" o "Prorrateo por días"); la deuda previa ("Queda en la unidad" o "A nombre
  del vendedor"); si trae `trasladado`, "Deuda pasada al vendedor" con el monto; si trae `prorrateo`, "Aplicado" con la
  parte ("3.500,00") y "10 de 30 días", o "Pendiente". Sin cambios: en lugar de la lista, un `role=status` con
  **"Esta unidad todavía no tuvo cambios de titular"**.
- **Errores (C05).** Un 422 de la API (siempre `value_error`, que hoy diría "valor inválido") se muestra **en su campo**
  y nunca como "valor inválido" ni "Este valor no es válido"; los datos cargados no se pierden. El mensaje es de la
  pantalla, por campo de la API (`loc` `body.<campo>`):

  | Campo de la API | Dónde se muestra | Mensaje exacto |
  |---|---|---|
  | `fecha` | descripción accesible de "Fecha del cambio" | Poné una fecha válida, que no sea posterior a hoy. |
  | `vendedores` | grupo "Vendedores" | Elegí al menos un vendedor entre los propietarios actuales. |
  | `compradores` (y `compradores.N.*`) | grupo "Compradores" | Revisá los compradores: tiene que haber al menos uno y ninguno puede ser también vendedor. |
  | `vendedor_deudor` | grupo "Vendedores" | Elegí cuál de los vendedores queda con la deuda. |
  | `expensa_del_mes` | grupo "Expensa del mes" | Ya hay un prorrateo para esta unidad en ese mes. Elegí la expensa entera. |
  | `deuda_previa` | grupo "Deuda previa" | Elegí qué pasa con la deuda de meses anteriores. |

  (La aceptación fija `fecha`, `compradores` y `expensa_del_mes`; los demás quedan a cargo del constructor con el
  mismo criterio.)

## `/edificios/{id}/cuentas-de-vendedores`

Lee `GET .../cuentas-de-vendedores` desde el servidor de Next. Con el menú lateral ("Cuentas de vendedores" marcada).

- `heading` **"Cuentas de vendedores"**.
- Una lista (`role=list`) con nombre **"Cuentas de vendedores"** y un `listitem` por cuenta, **en el orden de la API**
  (deuda de mayor a menor, también las que están en cero), con: el nombre de la persona como enlace (nombre accesible
  exacto "Ana Prueba") a `/edificios/{id}/cuentas-de-vendedores/{cuenta_id}`; la deuda con `dinero` ("30.000,00",
  "0,00"); y las unidades por identificador separadas por coma ("1B, 2A").
- Sin `ver_morosidad` (403): "sin permiso" con `ver_morosidad`, sin lista.

## `/edificios/{id}/cuentas-de-vendedores/{cuentaId}`

Lee `GET .../cuentas-de-vendedores/{cuenta_id}`. Cuenta que no existe (404): el estado "no existe".

- `heading` **"Cuenta de Luis Intermedio"** y el enlace **"Volver a cuentas de vendedores"**.
- Una región (`role=region`) con nombre **"Deuda de la cuenta"** con la `deuda` de la API (nunca la suma de los
  períodos) y las unidades por identificador.
- Una tabla (`role=table`) con nombre **"Deuda por período"**, columnas **"Período"**, **"Componente"**, **"Debe"**,
  **"Cobrado"**, **"Pendiente"**, una fila por período y componente (en el orden de la API); el período como `mm/aaaa`
  ("08/2025") y el componente en palabras: "Interés", "Ordinaria", "Fondo de reserva", "Extraordinaria".
- Una tabla con nombre **"Movimientos"**, columnas **"Fecha"** (`dd/mm/aaaa`), **"Movimiento"** y **"Importe"**, una fila
  por movimiento en el orden de la API; `tipo` en palabras: `traslado` = **"Traslado de deuda"**, `pago` = **"Cobro"**.
- **Cobro (C04).** Sólo con `confirmar_pago_informado`: un `form` con nombre **"Registrar cobro"** con **"Importe"** (se
  escribe con coma decimal, "20000,00"; viaja `"20000.00"`) y **"Fecha del cobro"** (`input type=date`) y el botón
  **"Registrar cobro"**. Al enviarlo se abre un diálogo (`role=dialog`) con nombre **"Confirmar cobro"** que dice
  **"Vas a registrar un cobro de 20.000,00 del 20/11/2026."** y tiene los botones **"Confirmar cobro"** y
  **"Cancelar"** (cancelar cierra el diálogo y no manda nada). Al confirmar, la pantalla manda
  `POST .../cobros` con exactamente `{"importe", "fecha"}` y muestra lo que devuelve la API: un `role=status` con
  **"Cobro registrado"**, la región de la deuda con la deuda nueva, las dos tablas actualizadas. Un 422 cierra el
  diálogo y se muestra en el campo:

  | Campo de la API | Dónde se muestra | Mensaje exacto |
  |---|---|---|
  | `importe` | descripción accesible de "Importe" | Poné un importe mayor a cero y que no supere la deuda de la cuenta. |
  | `fecha` | descripción accesible de "Fecha del cobro" | Poné una fecha válida, que no sea posterior a hoy. |

## API falsa (la escribe la aceptación)

`web/e2e/escenarios-cambio-de-titular.ts`, enganchada en `api-falsa.ts`: seis edificios `00000000-0000-0000-0000-00000000340k`
(k = 1 a 6) con **estado en memoria** (cada test que escribe tiene el suyo) y las identidades `user_titular` (el
administrador, con `registrar_cambio_de_titular` además de lo de siempre) y `user_lector` (sólo
`ver_configuracion_del_edificio` y `ver_morosidad`); `user_vecina` no trae ninguna acción de estos edificios.

| Edificio | Para qué |
|---|---|
| 3401 | Lectura. Unidades `1A` (propietarios Ana Prueba y Bruno Prueba; deuda 45.230,10; dos cambios en su historial), `1B` (Carla Prueba) y `2A` (Carla Prueba propietaria y Dario Inquilino). Cuentas: Ana Prueba 30.000,00 (`1B`, `2A`), Luis Intermedio **12.500,51 a propósito un centavo más que la suma de sus períodos** (`1A`), Pedro Anterior 0,00 con su cobro. |
| 3402 | Los cobros (misma semilla de cuentas). El cobro de Luis devuelve 10.000,52 (no 10.000,51). |
| 3403 | La venta de `1A` con la deuda a nombre del vendedor y el prorrateo **pendiente** (`trasladado` 45.230,10, aviso nulo). |
| 3404 | La venta de `1A` con la deuda en la unidad (aviso 45.230,10) y el prorrateo **aplicado** (parte 8.333,33). |
| 3405 | Los 422. `1A` ya tiene un prorrateo pendiente de noviembre de 2026. |
| 3406 | El recorrido a 320 px (la venta y el cobro). |

La API falsa valida como la real y en el mismo orden (404, 403, 422): fecha no posterior a hoy; vendedores
propietarios actuales, sin repetir y no vacíos; compradores no vacíos y ninguno que (por email) sea también vendedor;
`vendedor_deudor` obligatorio con más de un vendedor si hay traslado o prorrateo; un segundo prorrateo del mismo mes
en la misma unidad da 422 en `expensa_del_mes`; el cobro: `importe` texto positivo con a lo sumo dos decimales y no
mayor que la deuda, `fecha` no posterior a hoy. `GET .../cambios-de-titular` y `GET .../cuentas-de-vendedores[/id]`
dan 403 con `permiso_faltante` a quien no tiene la acción (`registrar_cambio_de_titular`, `ver_morosidad`); el cobro,
`confirmar_pago_informado`.
