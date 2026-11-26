# Contrato que asume la aceptación de H-040

Las pantallas del portal del vecino y la app instalable (change 11 `portal-del-vecino`, D-170.6), en navegador real
contra la API falsa (`web/e2e/api-falsa.ts` y `web/e2e/escenarios-portal.ts`, que escribe la aceptación). La API
falsa contesta con las formas y los filtros EXACTOS de `aceptacion/H-038/CONTRATO.md` y `aceptacion/H-039/CONTRATO.md`
(comparada contra respuestas reales del backend construido, L-107). Si el constructor necesita cambiar algo de esto,
frena y lo pide. Locators exactos (L-085). No se toca la API falsa: la verificación la restaura del SHA aprobado. Las
pantallas pasan por la skill **impeccable**. Los montos se formatean con `dinero` de `lib/formato.ts` (punto de miles,
coma decimal, sin signo de moneda) tal como vienen: la pantalla no suma, no resta ni redondea nada (N02). Las fechas
`dd/mm/aaaa` (`fecha`), los períodos en palabras ("noviembre de 2026", `periodoEnPalabras`), los porcentajes con
`porcentaje` ("71,43 %").

Fuente: `HISTORIAS.md` (H-040), D-170, D-106.

## Quién entra y qué lee

Las pantallas leen de la API sólo `GET /api/mis-unidades` y las rutas `.../mis-unidades/{unidad_id}/...` (pagos,
documentos, liquidaciones, liquidación) desde el servidor de Next; el navegador nunca llega a `/api`. Una unidad o
liquidación que la API da como 404 es un 404 de la pantalla (`notFound()`, estado HTTP 404), sin ningún dato. Con 422
de UUID mal formado, lo mismo. Ninguna pantalla muestra las claves `extraordinari*` del inquilino porque la API no se
las manda (D-170.2); la pantalla tampoco las inventa ni las deriva (N01).

## Rutas y menú

| Ruta | Título (`heading` nivel 1) |
|---|---|
| `/inicio` | **Inicio** |
| `/mis-liquidaciones` | **Mis liquidaciones** |
| `/mis-liquidaciones/{unidadId}` | **Liquidaciones de 1A** (el identificador de la unidad) |
| `/mis-liquidaciones/{unidadId}/{liquidacionId}` | **Expensa de noviembre de 2026** (el período de la liquidación) |
| `/comprobantes` | **Comprobantes** |
| `/manifest.webmanifest`, `/sw.js` y los íconos | (archivos, públicos: sin sesión) |

**Menú del vecino (C04).** En las pantallas anteriores, una navegación (`navigation`) con nombre **"Portal del
vecino"** con cuatro enlaces exactos: **"Inicio"** (`/inicio`), **"Mis liquidaciones"** (`/mis-liquidaciones`),
**"Comprobantes"** (`/comprobantes`) y **"Mis pagos"** (`/edificios/{edificioId}/mis-pagos`, el edificio de la
**primera unidad** de `mis-unidades`). El del lugar actual lleva `aria-current="page"`. Dentro de un edificio, la
navegación **"Secciones del edificio"** de quien tiene `informar_pago` en él suma **"Inicio"**, **"Mis
liquidaciones"** y **"Comprobantes"** (mismos destinos) junto a "Mis pagos", que ya existe. La raíz `/` y el ingreso
no cambian en esta historia.

Los pares rotulados de las pantallas son listas de definiciones: `<dt>Rótulo</dt><dd>valor</dd>` (el `dd` inmediato
siguiente al `dt`); los tests los leen así.

## `/inicio` (C01, C05)

- Un `region` **"Total del conjunto"** con los pares **"Total a pagar"**, **"Intereses"**, **"Crédito aplicable"** y
  **"Crédito retenido"**: lo de `conjunto`, tal cual (el crédito retenido nunca se resta de nada).
- Una lista (`role=list`) **"Mis unidades"**, un `listitem` por unidad, **en el orden de la API**, con: el identificador,
  el nombre del edificio, el vínculo (**"Propietario"** o **"Inquilino"**), los pares **"Total a pagar"**,
  **"Vencimiento"** (`dd/mm/aaaa`, o **"Sin vencimiento"** si es `null`), **"Crédito aplicable"** y **"Crédito
  retenido"**, y un enlace **"Ver liquidaciones de 1A"** a `/mis-liquidaciones/{unidadId}`.
- **Aviso de iPhone (C05).** Sólo con `userAgent` de iPhone, la primera vez: un `region` con nombre **"Agregar a la
  pantalla de inicio"** que explica el paso (texto con **"Compartir"** y **"Agregar a inicio"**) y un botón **"Cerrar
  aviso"**. Al cerrarlo desaparece y no vuelve (se recuerda en el navegador, `localStorage` con `try/catch`: sin
  almacenamiento, el aviso se ve sin romper nada), ni al recargar ni en otras pantallas. Fuera de iPhone no existe. Va
  en el flujo, a 320 px sin desbordar, con foco y axe limpios.

## `/mis-liquidaciones`, `/mis-liquidaciones/{unidadId}` (C02)

- `/mis-liquidaciones`: una lista **"Mis unidades"** con un enlace **"Ver liquidaciones de 1B"** por unidad.
- `/mis-liquidaciones/{unidadId}`: una lista **"Liquidaciones"** con un
  `listitem` por liquidación **en el orden de la API** (la más nueva primero): el período en palabras, **"Vence el"** y
  la fecha (`dd/mm/aaaa`), el total (de **esa unidad**, según su vínculo) y un enlace **"Ver expensa de noviembre de
  2026"** a `/mis-liquidaciones/{unidadId}/{liquidacionId}`. Sin liquidaciones, un `status` "Todavía no hay
  liquidaciones emitidas.".

## `/mis-liquidaciones/{unidadId}/{liquidacionId}` (C02, N01, N02)

Con un enlace **"Volver a las liquidaciones de 1A"** a la lista de la unidad. La lectura del detalle distribuye la
liquidación al abrirla (D-074) del lado de la API: la pantalla no hace nada aparte.

- Un `region` **"Gastos ordinarios"** con el texto **"Subtotal"** y el subtotal, y un `listitem` por categoría con su
  nombre, su importe y su porcentaje (**"71,43 %"**). Un `region` **"Gastos extraordinarios"** igual. **El inquilino
  no tiene este segundo `region`** (la API no manda `extraordinario`).
- Un `region` **"Por grupo de reparto"** con un `listitem` por grupo: el nombre, **"Ordinaria 30.000,00"** y, sólo si el
  grupo trae `extraordinaria` (propietario), **"Extraordinaria 15.000,00"**.
- Una tabla (`table`) **"Tu expensa"** con una fila por concepto, de dos celdas (rótulo y monto), en este orden:
  **"Ordinaria"**, una fila por cada cargo particular con su `concepto` ("Multa 5.000,00"), **"Fondo de reserva"**,
  **"Extraordinaria"** (sólo si la API la manda), **"Intereses"** y **"Total"**. El nombre accesible de cada fila es
  "rótulo monto" (por ejemplo `Total 46.500,00`).
- La comparación, si `comparacion` no es `null`: un `region` **"Comparación con el mes anterior"** con un `heading`
  **"Comparación con octubre de 2026"** (el período de la anterior), los pares **"Total del mes anterior"**
  (`total_anterior`) y **"Diferencia"** (`diferencia_total`, tal cual: la falsa lo desajusta un centavo a propósito,
  N02), y una tabla **"Comparación por categoría"** con una fila por categoría de cuatro celdas (nombre, importe de
  este mes, importe anterior, diferencia): `Limpieza 100.000,00 80.000,00 20.000,00`. Con `comparacion: null`, **sin**
  ese `region` y un `status` **"No hay una liquidación anterior para comparar."**.

## `/comprobantes` (C03)

Un `region` por unidad, en el orden de la API, con nombre **"Comprobantes de 1A"** (sin repetir identificadores en los
ejemplos), con:

- Una lista **"PDFs de 1A"** con un `listitem` por documento (el período en palabras) y un enlace **"Descargar PDF de
  noviembre de 2026"** con `href` `/documentos/descarga?token=...` (el token que viene en el `url` de la API,
  `/api/documentos/descarga?token=...`; la ruta de la web que ya existe): el navegador nunca recibe `/api/...`. Sin
  documentos, un `status` **"No hay PDFs disponibles."**.
- Una lista **"Pagos confirmados de 1A"** con un `listitem` por pago **en el orden de la API**: la fecha
  (`dd/mm/aaaa`), el banco, **"OP-0001"** (el número de operación) y el importe. Sin pagos, un `status` **"No hay
  pagos confirmados."**.

## App instalable (C05, N03)

- **`/manifest.webmanifest`**: público (sin sesión), JSON (`content-type` que incluya `json`) con `name` (no vacío),
  `short_name` (de 1 a 12 caracteres), `start_url` `"/inicio"`, `scope` `"/"`, `display` `"standalone"`, `lang` que
  empiece con `es`, `theme_color` y `background_color` en `#rrggbb`, e `icons` con al menos un PNG de `192x192`, uno de
  `512x512` y uno con `purpose` que incluya `maskable`; cada `src` baja con 200 y `image/png` sin sesión (la lista de
  `matcher` del proxy ya deja pasar `*.png` y `*.js`). Las páginas del portal traen `<link rel="manifest"
  href="/manifest.webmanifest">` y `<meta name="theme-color">` con el mismo `theme_color`.
- **`/sw.js`**: público, `content-type` JavaScript, registrado con alcance `/` desde las pantallas del portal (queda
  `activated` y, tras una recarga, controlando la página). **La CSP estricta del proxy (`script-src` sin `'self'`,
  `default-src 'self'`) bloquea hoy el registro de un worker: hay que sumar `worker-src 'self'` a las directivas de
  `proxy.ts`** (y registrar con el nonce de Next si el registro es en línea).
- **N03**: el service worker no guarda nada de `/api` ni ninguna página con datos del vecino: ninguna entrada de
  `caches` con direcciones de `/api/`, `/inicio`, `/mis-liquidaciones`, `/comprobantes`, `/documentos`, `/edificios` o
  `/_next/data`, ni con cuerpos que tengan montos o nombres del vecino; y sin conexión no hay pantalla con datos
  (no hay modo sin conexión). Alcanza con un worker que no guarde nada o sólo guarde estáticos sin datos.

## Estado de la sesión del vecino en la API falsa

`user_vecino_portal` (Ana, propietaria de `9A`, `1A` y `2B`) y `user_inquilino_portal` (Beto, inquilino de `1B`) traen en
la sesión sólo `informar_pago` en sus edificios (como el vecino real). El personal recibe de `mis-unidades` la lista
vacía, como la real. Los ids de edificios, unidades y liquidaciones están en `web/e2e/escenarios-portal.ts` y en la
cabecera del test.
