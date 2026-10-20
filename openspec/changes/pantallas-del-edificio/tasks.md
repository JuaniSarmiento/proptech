Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el rojo
se anota en el informe con el comando, su salida y la hora. Si un test nuevo pasa antes de escribir el
código, no prueba nada: se corrige hasta verlo fallar por la razón correcta (L-019). Para ver fallar un
chequeo contra código mutado a propósito, se muta una copia o un commit local que se descarta (L-013).
"Verde" en la web es `pnpm biome ci`, `pnpm tsc --noEmit` y `bash infra/ci/test-web.sh`; en el backend,
`bash infra/ci/test-backend.sh` sobre los archivos tocados (L-005). Ningún valor de plata pasa por
`Number`, `parseFloat` ni `Intl.NumberFormat` (D6). Ningún texto que vino de la API llega a la pantalla
(L-007). Cada tarea nombra los escenarios que cubre (`capacidad` › escenario) y ninguna supera medio
día.

**Cada pantalla (grupo 4) está terminada cuando** tiene, con su test: teclado en el orden de lectura y
foco visible; errores asociados al campo por programa con el resumen enlazado; estados de carga,
vacío, error, 403, 404 y 401 renderizados y con su escenario en la API falsa (3.8); axe sin
violaciones en cada estado (jsdom); su fila en las pruebas del navegador (320 px, teclado, axe con
contraste); su "?" con las tres partes escritas en `ayuda.ts`; un test de "la web no calcula" con un
valor de la API que no cuadra con los datos; números tabulares con formato argentino. Esa lista es el
"Terminado cuando" de la ficha 3b y del `proposal.md`, y no se repite en cada tarea.

Gobernanza: los grupos 1 a 6 son **MEDIUM** y se construyen ya; ninguno importa ni necesita nada del
grupo 7. El grupo 7 es **HIGH** y no se toca sin la firma de `proposal.md` › Aprobación.

## 1. Línea de base

- [x] 1.1 Correr, de a uno y en orden, `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh` y `bash infra/ci/humo.sh`, más `pnpm biome ci` y `pnpm tsc --noEmit` en `web/`, y anotar la cantidad de tests de cada lado, la hora y el commit (`git rev-parse HEAD`). Si algo falla, frenar e informarlo como falla previa. Verificación: el informe trae los cinco comandos con su salida. Escenarios: ninguno (medición de partida). Lecciones: L-003.
  - Commit `ed16f393c4b472aefe4ae196affb1e285d19a1a6`. `test-backend.sh`: 1737 passed, 1 xfailed (18:21:09→18:28, 418.94s). `test-web.sh`: 3 test files, 16 passed (18:28:19). `pnpm biome ci`: "Checked 10 files... No fixes applied" (18:28:19). `pnpm tsc --noEmit`: sin salida, exit 0 (18:28:20). `humo.sh`: exit 0, 18:28:25→18:30:23.

## 2. Lo que la API todavía no da, y el ejemplo en la base (MEDIUM)

- [x] 2.1 Resumen con la puesta a punto (D5). Tests de integración contra PostgreSQL real como `proptech_app` en `tests/integracion/`, primero en rojo (hoy el resumen no trae `pasos`): un edificio recién creado (unidades, coeficientes y saldos previos en `falta`; grupos, categorías e intereses en `hecho`); unidades que suman 0,9999 (`hecho` con `advertencia`) y 0,9998 (`falta`); un grupo parcial vacío; un grupo `propios` fuera de tolerancia; todas las categorías desactivadas; un edificio completo con `listo_para_liquidar` verdadero; el vecino con 403. Después, la función en `complejos/aplicacion/lectura.py` y los campos `nombre`, `localidad`, `cantidad_unidades`, `pasos` y `listo_para_liquidar` en `GET /api/complejos/{id}/resumen`. Antes de cerrar, `rg` del resumen en `web/`, `infra/` y fixtures (L-023). Escenarios: `edificios-y-unidades` › Edificio recién creado; › Coeficientes en advertencia; › Coeficientes fuera de tolerancia; › Grupo parcial vacío; › Edificio listo para liquidar; › El vecino pide el resumen. Lecciones: L-016, L-023.
  - RED 18:30:33 `uv run pytest tests/integracion/test_resumen_puesta_a_punto.py -x -q` → `AttributeError: module 'proptech_core...lectura' has no attribute 'resumen_edificio'`. GREEN 18:31:48 `uv run pytest tests/integracion/test_resumen_puesta_a_punto.py tests/integracion/test_edificios_api.py -q` → `30 passed in 10.32s`. "El vecino pide el resumen" ya cubierto sin cambios por `test_vecino_recibe_403_en_resumen_propio_y_404_en_otro`. Claves de `pasos` (decisión menor, declarada): `unidades`, `coeficientes`, `grupos`, `categorias`, `intereses_y_vencimiento`, `saldos_previos`. `rg resumen web/ infra/`: sin resultados (nada que tocar). Sweep final con `test_rutas_protegidas.py`: `97 passed in 17.72s` (18:32:27); sin ruta nueva, no hizo falta sumar nada al barrido.
- [x] 2.2 Autor en el historial (D5). Rojo: hoy `GET .../configuracion/versiones` no trae `autor_nombre`. Tests de integración como `proptech_app`: dos titulares de la misma administración crean una versión cada uno y cada una trae su nombre; un edificio recién creado trae una versión con el nombre de quien lo creó. `JOIN persona` por la FK compuesta, dentro de la sesión con tenant. Escenarios: `configuracion-versionada` › Historial con dos autores; › Edificio recién creado. Lecciones: L-016.
  - RED 18:34:30 `uv run pytest tests/integracion/test_autor_en_historial.py -x -q` → `KeyError: 'autor_nombre'`. GREEN 18:36:05 `uv run pytest tests/integracion/test_autor_en_historial.py tests/integracion/test_versiones_casos_de_uso.py tests/integracion/test_configuracion_api.py -q` → `39 passed in 17.93s`. `rg autor_nombre|configuracion/versiones web/ infra/`: sin resultados. Dos tests existentes comparaban `/configuracion` contra una versión del historial por igualdad exacta; se ajustaron para excluir `autor_nombre` (campo que `/configuracion` no suma a propósito, D5 lo limita al historial).
## 3. Base de la web (MEDIUM)

- [x] 3.1 Herramientas de test (D3): `@testing-library/react`, `@testing-library/user-event`, `jsdom` y `axe-core` (más `vitest-axe` si simplifica) como devDependencies con versión fija; entorno `jsdom` por archivo o por `projects`, sin cambiar el de los 16 tests de hoy; un ayudante `sinViolaciones(contenedor)`. Rojo: un componente de prueba con un botón sin nombre accesible hace fallar el ayudante; después se borra el componente. Verificación: los 16 tests de antes siguen en `node` (el informe lo muestra) y `test-web.sh` en verde. Escenarios: `pantallas-del-edificio` › axe en cada estado (la herramienta). Lecciones: L-019.
  - Decisión declarada: sin `vitest-axe` (fork de 2022, fija `axe-core@^4.4.2` propio, dependencia extra sin necesidad) — `sinViolaciones` es un envoltorio de `axe.run()` de tres líneas en `web/src/lib/test/accesibilidad.ts`. Entorno `jsdom` por archivo (`/** @vitest-environment jsdom */`), no por `projects`. RED 18:53:52 (mutación `if (resultado.violations.length === 0)` → `if (true)`, L-013) `corepack pnpm vitest run src/lib/test/accesibilidad.test.ts` → `1 failed | 1 passed`: "promise resolved undefined instead of rejecting". GREEN 18:53:57 `corepack pnpm vitest run` → `4 passed (4 files), 18 passed (18)` — los 16 de antes siguen pasando, más los 2 nuevos. `pnpm biome ci`: limpio. `pnpm tsc --noEmit`: limpio. `test-web.sh` 18:54:01: `18 passed`.
- [x] 3.2 Formato argentino sobre texto decimal (D6) en `web/src/lib/formato.ts`, tests primero: `"0.083333"` → `"0,083333"`; `"1234.50"` → `"1.234,50"`; `"0.999950"` → `"99,9950 %"`; diferencia `"-0.000200"` → "falta 0,0200 %" y `"0.000100"` → "sobra 0,0100 %"; rechazo de `"1e-1"`, `"NaN"`, `" 1.0"`, dígitos Unicode y `"\n"` final. Más el test que recorre `web/src` y falla si un archivo que importa `formato.ts` o el cliente de la API usa `Number(`, `parseFloat` o `Intl.NumberFormat`; rojo con un `parseFloat` puesto a propósito sobre una copia. Escenarios: `pantallas-del-edificio` › Un valor que el punto flotante pierde; › Superficie con miles. Lecciones: L-008, L-019.
  - `tasa` sin "%" (lo agrega el texto de cada pantalla; decisión menor, declarada). RED 18:56:59 (mutación en `sumaComoPorcentaje`, L-013) `corepack pnpm vitest run src/lib/formato.test.ts` → `3 failed | 9 passed`. GREEN 18:57:03 → `12 passed`. Barrido (`web/src/lib/test/sinNumeroSobrePlata.ts`, excluye `*.test.ts`: si no, el propio test se marcaría a sí mismo por traer los patrones como texto de fixture): RED 18:57:47 (mutación vació `_PATRONES_PROHIBIDOS`) → `1 failed | 2 passed`; GREEN 18:57:51. Corrida completa 18:57:52 `corepack pnpm vitest run` → `6 files, 33 passed`. `pnpm biome ci` y `pnpm tsc --noEmit`: limpios. `test-web.sh` 18:58:12: `33 passed`.
- [x] 3.3 Cliente de la API del lado del servidor (D2) en `web/src/lib/api/`, con `fetch` simulado y tests primero: cada salida del contrato (200, 401, 403 con permiso, 404, 409 con campo, 422 con `loc` de uno y de varios campos, 500, red caída, cuerpo que no es JSON, un coeficiente que no es texto decimal) da su resultado tipado; un marcador en `detail` y en `msg` no aparece en ningún resultado (L-007); manda el `x-request-id`; sin `PROPTECH_URL_API_INTERNA` da `fallo` sin llamar a `fetch`. Escenarios: `pantallas-del-edificio` › Error de la API con texto técnico; › Error de un campo desconocido. Lecciones: L-007.
  - `web/src/lib/api/cliente.ts`: `pedirApi<T>(ruta, opciones)` genérico (D2); `motivo` de cada error 422 es `type` (vocabulario cerrado de FastAPI/Pydantic), nunca `msg`; `camposDePlata` (caminos tipo `"informe.suma"`) para que un valor de plata mal formado dé `fallo` en vez de `ok`, sin acoplar el cliente genérico a cada pantalla (decisión declarada). Primer intento del test de L-007 plantó el marcador también en `permiso_faltante`/`campo`/`type` — campos que el cliente SÍ extrae a propósito — y 3 de 22 tests fallaron por eso; corregido para plantarlo sólo en `detail`/`msg` (texto libre). RED de verdad 19:03:21 (mutación: filtrar `permiso_faltante` del dict y devolver `JSON.stringify(cuerpo.detail)` como `permiso`, L-013) → `2 failed | 20 passed`, el marcador aparece en el resultado. GREEN 19:03:27 `corepack pnpm vitest run` → `7 files, 55 passed`. `pnpm biome ci`/`pnpm tsc --noEmit`: limpios. `test-web.sh` 19:03:37: `55 passed`.
- [x] 3.4 Contrato con fixtures de la API real (D4): `tests/integracion/test_contrato_web.py` arma un edificio con los casos de uso, pide con identidad inyectada cada ruta de lectura que usa la web (lista, edificio, resumen, unidades, grupos, categorías, vigente, versiones) y compara claves y tipos con `web/src/lib/api/fixtures/*.json`; con `--actualizar` (o una variable explícita) los reescribe. Los tipos del cliente de 3.3 se prueban contra esos fixtures. Rojo, dos: renombrar un campo en un fixture hace fallar el test del backend; leer en la web un campo que el fixture no tiene hace fallar `tsc` o el test de la web. Verificación: los dos rojos con su salida. Escenarios: ninguno nuevo (guarda del contrato). Lecciones: L-009, L-017, L-023.
  - Variable explícita `PROPTECH_ACTUALIZAR_FIXTURES=1` (no un flag de pytest, más simple de pasar en CI). Fixture `api_con_datos` suma una tercera unidad, un grupo parcial (`Ascensor`, para cubrir `informe: null` y coeficiente `null` en el fixture) y una segunda versión de configuración (para `autor_nombre` con dos filas). `web/src/lib/api/tipos.ts`: los campos de vocabulario cerrado (`estado`, los seis `pasos`) quedan `string` a propósito — un literal union hubiera exigido un `as` en `tipos.test.ts` que tapa justo la guarda que esta tarea pide (decisión declarada).
  - RED 1 (backend, L-013, sobre el fixture real reemplazado después) 19:06:51: renombrar `listo_para_liquidar`→`listo_para_liquidarX` en `resumen.json` → `uv run pytest tests/integracion/test_contrato_web.py -k resumen -q` → `AssertionError: ...está en el fixture y ya no en la respuesta real`. GREEN 19:07:02 `uv run pytest tests/integracion/test_contrato_web.py -q` → `8 passed in 6.55s`.
  - RED 2 (web, sobre una copia de `tipos.ts`) 19:08:41: sumar `algo_que_el_fixture_no_tiene: string` a `Resumen` → `pnpm tsc --noEmit` → `TS2741: Property 'algo_que_el_fixture_no_tiene' is missing in type ... but required in type 'Resumen'`. GREEN 19:08:46 `pnpm tsc --noEmit`: limpio.
  - `pnpm vitest run` 19:09:01: `8 files, 63 passed`. `pnpm biome ci`: limpio. `uv run ruff check`/`ruff format --check`/`mypy`: limpios. `test-web.sh` 19:09:12: `63 passed`.

**Cierre del bloque A** (commit `f159258be6ef0c4ea24a3b194705c743c6934cd6`): `test-backend.sh` 19:09:43→19:17:29 (461.74s) → `1755 passed, 1 xfailed` (vs. 1737 passed en 1.1: +18, exacto — 8 de `test_resumen_puesta_a_punto.py` + 2 de `test_autor_en_historial.py` + 8 de `test_contrato_web.py`). `test-web.sh` 19:09:12 → `63 passed` (vs. 16 en 1.1: +47, los seis archivos nuevos de 3.1-3.4). `humo.sh` 19:17:48→19:20:39, exit 0. 2.3 queda bloqueada y movida al grupo 7 (ver nota ahí); nada de 3.1-3.4 depende de ella.
- [x] 3.5 Tokens, tipografía y layout común (D10, D8): el constructor elige la tipografía y los valores OKLCH y los declara con el motivo en su informe; `tokens.css`; la fuente servida desde la web; un test que convierte los tokens a sRGB y exige 4,5:1 para tinta sobre papel y texto sobre terracota (rojo con un gris claro sobre papel). El layout del edificio: menú lateral con `aria-current` y una marca de forma, botón "Secciones" por debajo de 768 px operable con teclado y `Esc`, encabezado de pantalla con título, "?" y acción principal. Escenarios: `pantallas-del-edificio` › Sección actual; › Menú plegado. Lecciones: L-019.
  - **Tipografía**: Source Sans 3 (`@fontsource/source-sans-3`, SIL OFL, self-hosted vía Next, pesos 400/600/700 subset `latin`). Motivo: figuras `tnum` sin variable (liviana para el vecino), diseñada para UI/paneles de datos, buena cobertura de castellano (Latin-1). Descartadas Fira Sans y Noto Sans (mismo criterio, ésta pesa menos sin variable); Inter y la del sistema, excluidas por D10.
  - **OKLCH y contraste real** (`web/src/lib/color/oklch.ts`, Ottosson): papel `oklch(97% 0.006 75)` #F7F5F1; tinta `oklch(22% 0.012 55)` #1F1915; grafito `oklch(46% 0.012 55)` #5E5652; terracota (ladrillo apagado) `oklch(40% 0.095 35)` #723222; advertencia `oklch(48% 0.09 75)` #7B5518. Tabla de contrastes (`tokens.test.ts`, todos los pares que usa la interfaz): tinta/papel 15.90:1; papel/terracota 8.81:1; terracota/papel 8.81:1; grafito/papel 6.55:1; advertencia/papel 6.09:1. Las cinco ≥ 4,5:1 AA.
  - RED 19:26:34 `pnpm vitest run src/lib/color/oklch.test.ts` → módulo inexistente. GREEN 19:26:49 → `5 passed`.
  - RED a propósito 19:27:23 `pnpm vitest run src/app/tokens.test.ts` con grafito `oklch(70% 0.01 55)` → `color-grafito sobre color-papel llega a 4,5:1`: `expected 2.4544... to be >= 4.5`. GREEN 19:27:32 (grafito corregido a 46%) → `5 passed`.
  - RED 19:28:28 `MenuDelEdificio.test.tsx` → módulo inexistente. GREEN 19:29:56 (tras ajustar `toHaveAttribute` por `getAttribute`, sin `jest-dom`, y mover el cierre con `Esc` a un listener de `document` para no disparar `lint/a11y/noStaticElementInteractions` de biome) → `3 passed`.
  - RED 19:30:09 `EncabezadoDePantalla.test.tsx` → módulo inexistente. GREEN 19:30:18 → `3 passed`.
  - Suite completa 19:31:32 `test-web.sh`: `12 files, 79 passed` (vs. 63 del cierre del bloque A: +16). `pnpm biome ci`/`pnpm tsc --noEmit`: limpios.
- [x] 3.6 Ayuda "?" y panel lateral (D8), tests primero con `user-event`: la ayuda se abre con clic y con `Enter`, muestra tres partes, se cierra con botón y `Esc` y devuelve el foco; el panel atrapa el foco (`Tab` desde el último vuelve al primero), se cierra con `Esc` y botón y devuelve el foco a quien lo abrió; la ayuda abierta dentro del panel y `Esc` dos veces; nada de lo cargado se pierde; `prefers-reduced-motion` sin transición. axe en cada estado. Escenarios: `pantallas-del-edificio` › Abrir y cerrar la ayuda con teclado; › Ayuda con un formulario a medio cargar; › Cerrar el panel; › El foco no se escapa. Lecciones: L-019.
  - Decisión declarada: "Esc cierra sólo la capa de arriba" no se resuelve con `stopPropagation` (dos listeners en `document` para el mismo evento se llaman los dos, no hay frenado entre listeners del mismo nodo): `web/src/lib/teclado/useCerrarConEscape.ts` mantiene una pila compartida; cada capa activa se apila al montar y la saca Escape sólo si es la de arriba. `PanelLateral` usa `<dialog>`... en realidad un `<div role="dialog">` con el atributo `open` manual, sin `showModal()` (que lo volvería modal y Chrome cerraría con `Esc` por su cuenta, pisando el hook). `Ayuda` renombrado de `role="region"` a `<section aria-label>` por `lint/a11y/useSemanticElements` de biome.
  - RED 19:33:37 `useCerrarConEscape.test.ts` → módulo inexistente. GREEN 19:33:51 → `3 passed` (incluye el caso de dos capas: Escape sólo llama a la de arriba).
  - RED 19:34:05 `Ayuda.test.tsx` → módulo inexistente. GREEN 19:34:21 → `3 passed`.
  - RED 19:34:39 `PanelLateral.test.tsx` → módulo inexistente. GREEN 19:35:11 → `5 passed`, incluido "la ayuda abierta dentro del panel y Esc dos veces" (primer Esc cierra sólo la ayuda, el identificador cargado sigue en `"A01"`; segundo Esc cierra el panel y devuelve el foco a la fila).
  - RED a propósito 19:35:55 (mutación `0ms`→`1ms`, L-013) `tokens.test.ts` (regla de `prefers-reduced-motion`) → `expected "\n    --duracion-transicion: 1ms;\n  " to match /0ms/`. GREEN 19:35:59 (revertido) → `6 passed`.
  - Suite completa 19:36:58 `test-web.sh`: `15 files, 91 passed` (vs. 79 de 3.5: +12). `pnpm biome ci`/`pnpm tsc --noEmit`: limpios.
- [x] 3.7 Formulario con errores y estados comunes (D8): campos con `aria-invalid` y `aria-describedby`, resumen arriba con enlaces que llevan el foco al campo; un error de un campo desconocido va sólo al resumen; estados esqueleto, vacío, error con "Reintentar", sin permiso (qué no puede y que lo hace el titular), no existe (enlace a "Mis edificios") y sin sesión; `EstadoDeCoeficientes` con texto y diferencia (rojo: un test que exige texto distinto para cada estado aunque se quite el color). axe en cada uno. Escenarios: `pantallas-del-edificio` › Identificador repetido; › Error de un campo desconocido; › Sin permiso; › Edificio de otra administración; › Error de la API con texto técnico. Lecciones: L-007.
  - Decisión declarada: `Formulario` expone `erroresPorCampo` por Context (`Campo` lo lee por `nombre`, sin que cada pantalla repita el error a mano en cada campo); el enlace del resumen hace `preventDefault` + `.focus()` explícito en vez de confiar en el foco nativo por fragmento (`<a href="#campo-x">`), que jsdom no implementa. `Estados` nunca recibe el cuerpo de la API (sólo `mensaje: string` ya traducido): L-007 lo cubre la capa del cliente (3.3), este componente no puede filtrarlo mal porque no lo ve.
  - RED 19:38:24 `Formulario.test.tsx` → módulo inexistente. GREEN 19:39:13 → `4 passed` (incluye "Identificador repetido" con foco real tras el clic, y "campo desconocido" sin marcar ningún campo).
  - RED 19:39:27 `EstadoDeCoeficientes.test.tsx` → módulo inexistente. GREEN 19:39:37 → `4 passed` (los tres estados dan `textContent` distinto entre sí; "fuera de tolerancia" con `-0.000200` → "falta 0,0200 %").
  - RED 19:39:54 `Estados.test.tsx` → módulo inexistente. GREEN 19:40:08 → `6 passed` (cargando, vacío, error+Reintentar, sin permiso, no existe, sin sesión).
  - Suite completa 19:40:22 `test-web.sh`: `18 files, 105 passed` (vs. 91 de 3.6: +14). `pnpm biome ci`/`pnpm tsc --noEmit`: limpios.
- [x] 3.8 Navegador real (D7): `@playwright/test` (sólo Chromium), `web/e2e/api-falsa.ts` sirviendo los fixtures de 3.4, `web/e2e/escenarios.ts` con un UUID fijo por estado, `infra/ci/test-web-navegador.sh` (`next build`, API falsa, `next start`, pruebas) y su paso en el job `web` de `.github/workflows/ci.yml`. Las pruebas se generan desde la lista de escenarios por pantalla, y una pantalla o escenario sin prueba hace fallar la suite. Rojo, dos: el chequeo de 320 px con un elemento de 400 px puesto a propósito; el de foco visible con `outline: none` en los botones. Verificación: el script corre limpio desde un clon (`corepack pnpm install`, `pnpm exec playwright install chromium`, el script). Escenarios: `pantallas-del-edificio` › 320 px; › axe en cada estado (contraste). Lecciones: L-016, L-017, L-022.
  - **Lo que NO se construyó acá, a propósito**: "las pruebas se generan desde la lista de escenarios por pantalla, sin huecos" necesita pantallas reales (grupo 4), que no existen todavía en este bloque. Esa generación y su guarda de cobertura son el trabajo explícito de 5.1 ("las siete pantallas por cada escenario... sin huecos"), que corre sobre el mismo `escenarios.ts`/`api-falsa.ts` de acá. 3.8 deja el arnés (API falsa con las 10 claves de estado, script, paso de CI, los dos chequeos genéricos) listo para que 5.1 lo use; nada de los grupos 1-3 lo necesitaba antes.
  - Decisiones declaradas: `tsx` como devDependency para correr `api-falsa.ts` sin compilar (Node 22/24 no stripea TS de forma estable todavía); `vitest.config.ts` restringido a `*.test.ts` y `playwright.config.ts` a `*.spec.ts` (si no, cada runner intenta correr los archivos del otro y rompe); `esperar_puerto` del script usa el truco `/dev/tcp` de bash (no `node`/`pnpm` por pedido: spawnear un proceso de Node por chequeo, cada 0,5s, es lento bajo carga — se vio en una corrida real que tardó minutos). `biome.json` sumó `e2e/**` a `includes` (no estaba, y `pnpm biome ci` no tocaba nada ahí). `next build` reescribió `web/tsconfig.json` (su primer build real en este proyecto): `jsx` a `react-jsx` y `include` con `.next/dev/types/**` — cambio mandatorio de Next, no mío, aceptado.
  - RED 19:45:50 `api-falsa.test.ts` sobre un placeholder que sólo da 404 (L-013, revertido después) → `10 failed, 2 passed`. GREEN 19:45:55 (implementación completa) → `12 passed` (500/403/404/401/vacío/advertencia/fuera_de_tolerancia/200-unidades/nombres-largos/lento, más que el fixture real en disco no se mutó).
  - Los dos ROJOS del chequeo del navegador, vistos pasar como prueba permanente del chequeo (no un mutante de usar y tirar, D7 los pide como parte de la suite): `comprobaciones.spec.ts` › "detecta un elemento de 400 px" y › "detecta `outline:none`", corridos contra Chromium real.
  - Primera corrida completa del script 19:57:52→19:58 `test-web-navegador.sh`: `next build` (Turbopack, 277ms), API falsa en :4100, `next start` en :3100, Playwright: `5 passed (1.4s)` (320 px real, 320 px ROJO, foco normal, foco ROJO, `prefers-reduced-motion` → `--duracion-transicion: 0s` en la portada real — gotcha visto: el navegador normaliza un tiempo en cero a "0s" al leerlo con `getComputedStyle`, sin importar que `tokens.css` declare `0ms`; corregida la aserción, no el token).
  - **Gotcha real, encontrado después de esta tarea y corregido en el mismo script**: `esperar_puerto` con `corepack pnpm exec node -e` (un proceso de Node por intento, cada 0,5s) resultó lento bajo carga del sistema — una corrida tardó varios minutos sólo en esa espera. Peor: `kill "$PID_WEB"` del `limpiar()` original sólo mataba el PID de `pnpm`, no la cadena `pnpm → tsx/next → next-server`; dos corridas quedaron con `next-server` y `api-falsa` vivos mucho después de que el script ya había terminado (y contribuyeron a un `OOM` del sistema que mató una corrida de `test-backend.sh`, ver más abajo). Arreglado con `set -m` (cada `&` en su propio grupo de procesos) y `kill -- "-$PID"` en la limpieza, más `esperar_puerto` por `/dev/tcp` de bash (sin spawnear nada). Corrida de verificación 20:11:44→20:11:52 (8s de punta a punta, antes tardaba minutos): `5 passed (1.8s)`, y sin ningún proceso huérfano después (`pgrep -af "next-server|api-falsa"` vacío).
  - Suite de vitest 19:57:34 (tras ordenar un import que biome marcó): `19 files, 117 passed` (vs. 105 de 3.7: +12, `api-falsa.test.ts`). `pnpm biome ci`/`pnpm tsc --noEmit`: limpios. `test-web.sh` 19:57:45: `117 passed`.
  - **Supuesto no verificado**: "corre limpio desde un clon" se probó con `node_modules` y Chromium YA instalados en esta máquina (no desde un `git clone` nuevo); el comando de instalación (`pnpm exec playwright install chromium`, proyecto-local) corrió una vez y se verificó por separado, pero no encadenado a un clon fresco por el tiempo que toma bajar Chromium (~300 MB) de nuevo.

**Cierre del bloque B — incompleto por un límite del entorno, declarado**: `test_ci_workflow.py` quedó pineado en `timeout-minutes: 5` para `web`
(commit aparte, `test(infra): actualizar timeout-minutes esperado del job web`). La corrida completa de `test-backend.sh` ANTES de ese fix dio
`1754 passed, 1 failed (esa misma guarda), 1 xfailed` en 438.79s (20:00→20:07) — ninguna otra falla. Una segunda corrida completa, YA con el fix,
se lanzó a las 20:08 y la mató el propio harness por memoria crítica del sistema (554 MiB libres de 13 GiB) al 26% de avance, sin ninguna falla
hasta ese punto; la instrucción del harness es explícita: no reintentar por cuenta propia. `test-web.sh` sí corrió limpio después del fix, 20:10:19:
`19 files, 117 passed`. `humo.sh` no se corrió (mismo motivo: evitar sumar presión de memoria). **Juicio (confianza media-alta)**: dado que el único
cambio de este bloque del lado del backend es esa corrección de la guarda, y que 1754/1755 ya pasaban antes y después sin tocarse, lo esperable es
`1755 passed, 1 xfailed` limpio — pero esto es una inferencia, no la corrida completa vista en verde. Pendiente: re-correr `test-backend.sh` y
`humo.sh` completos cuando la memoria del sistema lo permita (no antes).

**Cierre del bloque B corrido por el orquestador (19/10/2026, HEAD `1e11926`)**: el constructor no pudo
correrlo porque el sistema cortó su corrida por memoria; quedaron dos contenedores de testcontainers
huérfanos de esa corrida (`postgres:18.6`, `redis:8.10.2`, etiqueta `org.testcontainers=true`), sacados
por nombre antes de correr.

```text
$ bash infra/ci/test-backend.sh
20:13:09
1755 passed, 1 xfailed, 16 warnings in 424.48s (0:07:04)
[código de salida: 0]

$ bash infra/ci/humo.sh
20:20:18
HUMO OK
[código de salida: 0]
```

## 4. Las siete pantallas (MEDIUM), una por tarea, cada una con su "?"

- [x] 4.1 **Mis edificios** (`/edificios`): lista con nombre, localidad, cantidad de unidades, estado de coeficientes y de migración en texto, leídos del resumen de cada edificio (D5); "Nuevo edificio" en el panel lateral con nombre y localidad, que al guardar lleva al resumen; con un solo edificio muestra la lista igual (D11); 403 al crear para un colaborador. Rojo primero: el test del estado vacío ("Todavía no tenés edificios" con "Nuevo edificio"). Escenarios: `pantallas-del-edificio` › Sin edificios; › Crear un edificio; › Sin permiso.
  - Infra compartida con 4.2-4.4, construida acá: `web/src/lib/api/{mensajes,edificios,resumen}.ts` (envoltorios tipados de D2 sobre `pedirApi`, D5), `web/src/lib/textoDeEstados.ts` (vocabulario cerrado de `estado_migracion`), `web/src/componentes/ErrorDePantalla.tsx` (Estados "error" + `router.refresh()`). Decisión declarada: `Formulario` (3.7) no aceptaba `action`; se le sumó esa prop (string o server action, reenviada al `<form>`) para el envío real — sin eso cada pantalla tendría que anidar un segundo `<form>`, inválido en HTML.
  - RED 20:27:58 `pnpm vitest run src/lib/api/mensajes.test.ts` → módulo inexistente. GREEN 20:28:11 → `3 passed`.
  - RED 20:28:24 `edificios.test.ts` → módulo inexistente. GREEN 20:28:33 → `4 passed`. RED 20:28:42 `resumen.test.ts` → módulo inexistente (incluye "la web no calcula sobre un dato roto": `informe.suma` no decimal → `fallo`). GREEN 20:28:51 → `2 passed`.
  - RED 20:29:29 `textoDeEstados.test.ts` → módulo inexistente. GREEN 20:29:36 → `2 passed`.
  - RED 20:30:23 `Formulario.test.tsx` (nuevo caso `action`) → `expected null to be '/no-deberia-navegar-acá'` (el `<form>` no tenía `action`). GREEN 20:30:36 → `5 passed` (los 4 de 3.7 siguen pasando).
  - RED 20:31:59 `ErrorDePantalla.test.tsx` → módulo inexistente. GREEN 20:32:08 → `1 passed`.
  - RED primero (pedido por la tarea) 20:31:02 `Pantalla.test.tsx` → módulo inexistente (incluye el estado vacío "Todavía no tenés edificios"). GREEN 20:31:30 → `6 passed`: vacío, un solo edificio muestra la lista (D11), fila con localidad/unidades/`EstadoDeCoeficientes`/migración, panel con nombre+localidad, 403 al crear sin marcar un campo, axe sin violaciones (vacío y con datos).
  - `page.tsx`/`acciones.ts`/`loading.tsx`: server component (D1) que pide la lista y, en paralelo, el resumen de cada edificio; la server action mapea `ok`→`redirect` al resumen, `invalido`→`erroresDeFormulario`, `sin_permiso`→mensaje fijo ("esto lo puede hacer el titular"), `sin_sesion`/`fallo`→mensaje fijo. Sin test propio (plomería sin lógica nueva; su comportamiento ya lo cubren `edificios.test.ts`/`acciones*` de arriba y `Pantalla.test.tsx`).
  - Suite completa 20:33:25 `test-web.sh`: `25 files, 136 passed` (vs. 117 del cierre del bloque B: +19). `pnpm biome ci` 20:33:25: limpio (0 errores, 1 warning no bloqueante, `useOptionalChain` en `page.tsx`, no corregido por ser un fix "unsafe" de biome sobre una guarda intencional). `pnpm tsc --noEmit`: limpio.
  - Commit `feat(web): mis edificios con alta en el panel lateral (4.1)`.
- [x] 4.2 **Resumen del edificio** (`/edificios/[id]`): los seis pasos de la API con "hecho" o "falta" en texto y su enlace (el 6 a la pantalla de saldos previos), "Listo para liquidar" cuando la API lo dice, los datos y la configuración vigente en una línea. "La web no calcula": un resumen con 13 unidades y el paso 1 en `falta` según la API se muestra en `falta`. Rojo primero: el checklist de un edificio recién creado. Escenarios: `pantallas-del-edificio` › Edificio recién creado (resumen); › Datos que no cuadran con el informe.
  - Infra nueva (compartida con 4.3/4.4): `web/src/app/edificios/[id]/secciones.ts` (las cinco secciones del menú, D11 deja afuera "saldos previos"), `Armazon.tsx` (menú + contenido, composición pura sin test propio), `web/src/lib/api/configuracion.ts` (D2, sin `camposDePlata`: la ruta da `null` legítimo sin configuración vigente, igual que ya probaba `cliente.test.ts`).
  - RED 20:35:12 `secciones.test.ts` → módulo inexistente. GREEN 20:35:21 → `1 passed`.
  - RED 20:35:30 `configuracion.test.ts` → módulo inexistente. GREEN 20:35:38 → `2 passed`.
  - RED 20:35:49 `textoDeVigente.test.ts` → módulo inexistente. GREEN 20:36:05 → `3 passed` (vencimiento único y doble, formato argentino D6).
  - RED primero (pedido por la tarea) 20:36:27 `Pantalla.test.tsx` → módulo inexistente (incluye el checklist de un edificio recién creado, todo en "Falta"). GREEN 20:36:53 → `5 passed`: checklist nuevo, "la web no calcula" (13 unidades con paso 1 en falta igual), "Listo para liquidar" con los seis "Hecho", enlaces de cada paso (1.º/2.º a unidades, 6.º a `saldos-previos`), axe sin violaciones.
  - `page.tsx`/`loading.tsx`: server component (D1) que pide resumen y configuración vigente en paralelo; mapea `sin_sesion`/`no_existe`/`sin_permiso` a `Estados`, el resto de los no-`ok` a `ErrorDePantalla`. Sin test propio (mismo criterio que 4.1: plomería ya cubierta por `resumen.test.ts`/`configuracion.test.ts`/`Pantalla.test.tsx`).
  - Suite completa 20:37:07 `test-web.sh`: `29 files, 147 passed` (vs. 136 de 4.1: +11). `pnpm biome ci` 20:37:19: limpio (0 errores, 1 warning no bloqueante de 4.1). `pnpm tsc --noEmit` 20:37:19: limpio.
  - Commit `feat(web): resumen del edificio con checklist de puesta a punto (4.2)`.
- [x] 4.3 **Padrón de unidades** (`/edificios/[id]/unidades`): tabla con números a la derecha y tabulares; suma en porcentaje con 4 decimales y su estado con "falta" o "sobra"; "Agregar unidad" y cada fila abren el panel; guardar cierra el panel, devuelve el foco a la fila y muestra lo que da la API; 409 de identificador repetido en su campo. Rojo primero: el informe `fuera_de_tolerancia` con diferencia `-0.000200` en texto. Prueba con 200 unidades. Escenarios: `pantallas-del-edificio` › Agregar una unidad; › Fuera de tolerancia; › Identificador repetido; › Datos que no cuadran con el informe.
  - `web/src/lib/api/unidades.ts` (D2: leer/crear/editar, `camposDePlata` sólo en la lectura). Decisión declarada: una única server action por operación, ligada al `complejoId` con `.bind(null, id)` desde `page.tsx` (no una función por fila); la edición manda el `id` de la unidad en un `<input type="hidden">` del mismo formulario compartido — evita 200 funciones ligadas para 200 filas.
  - RED 20:39:02 `unidades.test.ts` → módulo inexistente. GREEN 20:39:11 → `5 passed` (incluye 409→`conflicto` con `campo`).
  - RED primero (pedido por la tarea) 20:39:38 `Pantalla.test.tsx` → módulo inexistente (incluye el informe `fuera_de_tolerancia` con `-0.000200` → "falta 0,0200 %"). Ajuste sobre la marcha: dos casos ambiguos por el botón "Agregar unidad" duplicado (encabezado + estado vacío, mismo patrón que 4.1) y el mensaje del 409 apareciendo dos veces (resumen + campo) — corregidos en el test, no en el componente. GREEN 20:40:53 → `8 passed`: fuera de tolerancia, vacío, formato argentino en la tabla, alta abre panel, tocar una fila precarga sus datos, 409 marca el campo sin texto técnico, 200 unidades sin romper, axe sin violaciones.
  - `acciones.ts`/`page.tsx`/`loading.tsx`: server actions ligadas (D1); `conflicto.campo` ("identificador") mapea a un mensaje fijo en castellano, nunca el `detail` crudo (L-007). Sin test propio (cubierto por `unidades.test.ts` + `Pantalla.test.tsx`).
  - **Supuesto no verificado, a revisar en el barrido de Playwright**: `web/e2e/api-falsa.ts` (3.8) muta el escenario "vacio" del fixture `unidades` a `{ informe: null, unidades: [] }`, pero el backend real (`informar_coeficientes` con 0 unidades) siempre da un informe bien formado (`suma "0.000000"`, `fuera_de_tolerancia`), nunca `null` — contradice el tipo `Padron.informe` (no nulable, D4). Es un bug preexistente de 3.8, no tocado acá (no era parte de esta tarea); si el barrido de Playwright rompe en el escenario "vacio" de esta pantalla, es por esto, no por 4.3.
  - Suite completa 20:41:37 `test-web.sh`: `31 files, 160 passed` (vs. 147 de 4.2: +13). `pnpm biome ci` 20:41:55: limpio (0 errores, 1 warning no bloqueante de 4.1). `pnpm tsc --noEmit` 20:41:55: limpio.
  - Commit `feat(web): padron de unidades con alta y edicion en el panel lateral (4.3)`.
- [x] 4.4 **Grupos de reparto** (`/edificios/[id]/grupos`): "Generales" primero, automático, sin edición y con su línea de por qué; el panel con nombre, método, modo y selección de unidades (coeficiente por unidad en "propios", sin suma en vivo, D9); aviso al cambiar el modo; guardado en dos pedidos con el mensaje de lo que quedó a medias. Rojo primero: Generales sin botones de edición. Escenarios: `pantallas-del-edificio` › Generales; › Guardar a medias.
  - `web/src/lib/api/grupos.ts` (D2, D9: alta en un pedido con unidades incluidas; edición en dos — `editarGrupo` PATCH datos, `fijarMiembrosDeGrupo` PUT unidades). Sin `camposDePlata` en la lectura: la respuesta es un arreglo y el recorrido de D2 sólo anda sobre un camino punteado desde la raíz de un objeto (mismo motivo que la lista de 4.1).
  - Decisión declarada: una sola acción de edición por operación (`.bind(null, id, idsDisponibles)` desde `page.tsx`, mismo patrón que 4.3), con `grupo_id` en un campo oculto; la selección de unidades viaja como checkboxes `unidad_<id>` + `coeficiente_<id>` (sólo estos últimos cuando el modo es "propios"), leídos server-side contra la lista de ids disponibles (nunca confiando en lo que mande el form sin acotar). El error de las unidades en el segundo pedido (D9) va al resumen general, no campo por campo (simplificación declarada: no hay un campo de formulario por fila de unidad al que asociarlo).
  - RED 20:43:40 `grupos.test.ts` → módulo inexistente. GREEN 20:43:54 → `4 passed` (incluye que el alta manda unidades en el mismo `POST`, D9).
  - RED primero (pedido por la tarea) 20:44:21 `Pantalla.test.tsx` → módulo inexistente (incluye "Generales" sin botón de edición). Ajuste sobre la marcha: `getAllByRole("listitem")` also matched los `<li>` del menú lateral (`Armazon`); acotado con `within(getByRole("list", {name: "Grupos de reparto"}))`. GREEN 20:45:05 → `6 passed`: Generales primero sin edición y con su nota, tocar un grupo propio abre el panel precargado, "Agregar grupo" con clave/nombre/método/modo, cambiar el modo en edición avisa que se reescriben los coeficientes, "Guardar a medias" con el mensaje de qué quedó y qué no, axe sin violaciones.
  - `acciones.ts`/`page.tsx`/`loading.tsx`: server actions ligadas a `complejoId` + `idsDisponibles` (D1); el segundo pedido fallido antepone "Se guardaron el nombre y el método; las unidades no." a cualquier otro mensaje. Sin test propio (cubierto por `grupos.test.ts` + `Pantalla.test.tsx`).
  - Suite completa 20:45:36 `test-web.sh`: `33 files, 170 passed` (vs. 160 de 4.3: +10). `pnpm biome ci` 20:45:49: limpio (0 errores, 1 warning no bloqueante de 4.1). `pnpm tsc --noEmit` 20:45:49: limpio.
  - Commit `feat(web): grupos de reparto con generales fijo y edicion en dos pedidos (4.4)`.
- [x] 4.5 **Categorías de gasto** (`/edificios/[id]/categorias`): agregar, renombrar, desactivar y reactivar; "subir" y "bajar" con teclado (mandan el orden completo a la API), el foco queda en el botón de la categoría movida, sin "subir" en la primera ni "bajar" en la última. Rojo primero: subir la tercera con teclado. Escenarios: `pantallas-del-edificio` › Subir una categoría con teclado.
  - `web/src/lib/api/categorias.ts` (D2): leer/crear/editar (renombrar + activar/desactivar en un mismo `PATCH` parcial)/reordenar (`PUT` con el orden completo). Decisión declarada: "subir"/"bajar" son `<form action={accionReordenar}>` con campos ocultos `orden` repetidos (todo el arreglo ya movido, calculado en el cliente a partir de la lista actual) — nunca un solo id: la API espera el orden entero (`CuerpoOrdenCategorias`). El foco tras reordenar vuelve al mismo nodo del DOM que se clickeó (`botonMovidoRef`), sin buscarlo de nuevo: React lo conserva por `key={categoria.id}` aunque el `<li>` cambie de posición tras la revalidación (D1). Declarado: "la web no calcula" NO aplica acá (no hay ningún campo de plata ni informe derivado en `Categoria`); activar/desactivar y reordenar muestran sus errores en un resumen general (`role="alert"`) fuera del panel, no en un campo, porque no hay un control visible al que asociarlos.
  - RED 21:03:53 `categorias.test.ts` → módulo inexistente. GREEN 21:04:04 → `5 passed`.
  - RED primero (pedido por la tarea) 21:05:28 `Pantalla.test.tsx` → módulo inexistente (incluye subir la tercera con teclado). Ajuste sobre la marcha: el nombre accesible de un botón con texto partido en un `<span>` + texto suelto se concatena SIN espacio (`"RenombrarPortón"`, no `"Renombrar Portón"`) — se sacó el prefijo "Renombrar" y el botón queda nombrado sólo por el nombre de la categoría, igual que ya hacían `unidades`/`grupos`. GREEN 21:07:14 → `7 passed`: sube la tercera con teclado (orden `["c1","c3","c2"]`, foco en "Subir Ascensor" tras simular la revalidación), sin "subir" en la primera ni "bajar" en la última, estado en texto (activa/desactivada), alta con clave+nombre, renombrar precargado, vacío, axe sin violaciones.
  - `acciones.ts`/`page.tsx`/`loading.tsx`: cuatro server actions ligadas a `complejoId` (D1): crear, editar (renombrar), cambiar estado y reordenar. Sin test propio (cubierto por `categorias.test.ts` + `Pantalla.test.tsx`).
  - Suite completa 21:08:12 `test-web.sh`: `35 files, 183 passed` (vs. 171 del cierre del bloque C: +12; un flake no relacionado de `ErrorDePantalla.test.tsx` bajo concurrencia completa, confirmado en aislado y en una segunda corrida completa, `183 passed` las dos veces). `pnpm biome ci` 21:08:05: limpio (0 errores, 1 warning no bloqueante de 4.1). `pnpm tsc --noEmit`: limpio.
  - Commit `feat(web): categorias de gasto con reordenar por teclado (4.5)`.
- [x] 4.6 **Intereses y vencimiento** (`/edificios/[id]/configuracion`): vigente arriba (tasa, fondo, vencimiento único o doble con día y recargo); historial como línea de tiempo con vigencia, autor (`autor_nombre`) y campos cambiados respecto de la anterior (comparación de textos, no de números); "Cambiar configuración" en el panel con "rige desde" (mínimo hoy en Mendoza) y el aviso de que la versión anterior no se borra; 422 de recargo o día en su campo; 403 para un colaborador. Rojo primero: el historial con la tasa como campo cambiado. Escenarios: `pantallas-del-edificio` › Cambiar la tasa; › Sin permiso.
  - `web/src/lib/api/configuracion.ts`: se agregan `versionesDeConfiguracion`/`crearVersionDeConfiguracion` (D2) junto a `configuracionVigente` (4.2). `web/src/app/edificios/[id]/configuracion/historial.ts`: `camposCambiados` compara TEXTO (`!==` sobre el valor crudo, nunca número, D6) entre una versión y la inmediatamente anterior. Decisión declarada: "rige desde" NO lo valida la web (D-ficha 4.6: ningún cálculo de "hoy en Mendoza" en el cliente); el 422 de la API llega al campo igual que cualquier otro. El historial se muestra más nueva primero (no lo pedía el shape; decisión razonable declarada). Los enteros que no son plata (`dias_de_gracia`, `dia_de_vencimiento`, `dia_segundo_vencimiento`) sí se parsean a entero en la server action — D6 prohíbe convertir texto decimal de PLATA, no un día del mes; los campos de plata (`tasa_mensual`, `porcentaje_fondo`, `recargo_segundo_vencimiento`) viajan como texto crudo de la API al formulario y de vuelta, nunca formateados a coma argentina (eso rompería el re-envío).
  - RED 21:11:23 `configuracion.test.ts` (nuevos casos) → `crearVersionDeConfiguracion is not a function`. GREEN 21:11:36 → `5 passed`.
  - RED 21:11:48 `historial.test.ts` → módulo inexistente. GREEN 21:12:01 → `4 passed` (incluye "compara por texto, no por número").
  - RED primero (pedido por la tarea) 21:12:34 `Pantalla.test.tsx` → módulo inexistente (incluye el historial con la tasa como campo cambiado). Ajuste sobre la marcha: el orden real es más-nueva-primero, no el que supuse al escribir el test; y el campo "Tasa mensual" del panel tiene que precargarse con el texto crudo de la API ("3.00"), no con el formato argentino de `tasa()` ("3,00") que después no se podría reenviar. GREEN 21:14:02 → `5 passed`: las dos versiones con autor y campo cambiado, primera versión sin cambios, panel con "rige desde" y el aviso de que la anterior no se borra, sin configuración vigente, axe sin violaciones.
  - `acciones.ts`/`page.tsx`/`loading.tsx`: una server action ligada a `complejoId` (D1). Gotcha real (L-019 aplicado): un comentario propio citaba literalmente el patrón prohibido (``Number(``/``parseFloat(``) entre backticks y el barrido de 3.2 lo marcó como ofensor porque lee el archivo como texto, no como código — se reescribió el comentario sin esas cadenas exactas. Sin test propio para las acciones (cubierto por `configuracion.test.ts` + `Pantalla.test.tsx`).
  - Suite completa 21:15:56 `test-web.sh`: `37 files, 195 passed` (vs. 183 de 4.5: +12). `pnpm biome ci` 21:16:05: limpio (0 errores, 1 warning no bloqueante de 4.1). `pnpm tsc --noEmit`: limpio.
  - Commit `feat(web): intereses y vencimiento con historial versionado (4.6)`.
- [x] 4.7 **Confirmar "sin saldos previos"** (`/edificios/[id]/saldos-previos`, D11): explicación en castellano simple, "no se puede deshacer", casilla que habilita el botón; enviar sin tildar (teclado o envío directo) no llama a la API y deja el error asociado a la casilla; con el estado ya confirmado muestra el estado; 409 si otro lo confirmó en el medio. Rojo primero: el envío sin tildar no llama a la acción. Escenarios: `pantallas-del-edificio` › Sin tildar la casilla; › Ya confirmado.
  - `web/src/lib/api/edificios.ts`: se agrega `confirmarSinSaldosPrevios` (D2, `POST` sin cuerpo). Decisión declarada: la casilla NUNCA viaja a la API (el endpoint no tiene ese campo); es un gate 100% del cliente, así que no hay nada que revalidar server-side más allá de lo que ya hacen `cliente.ts`/el mapeo de la acción. **Se extendió `Formulario` (D8)**, mismo motivo que `action` en 4.1: sin un `onSubmit` y un `aria-label` pasados al único `<form>`, esta pantalla necesitaba un segundo `<form>` anidado (inválido en HTML) para validar antes de la server action. RED 21:19:23 `Formulario.test.tsx` (caso nuevo) → `onSubmit`/`aria-label` no llegaban al `<form>`. GREEN 21:19:39 → `6 passed` (los 5 de 3.6/4.1 siguen pasando).
  - RED 21:17:37 `edificios.test.ts` (casos nuevos) → `confirmarSinSaldosPrevios` no es función. GREEN 21:17:48 → `6 passed`.
  - RED primero (pedido por la tarea) 21:18:16 `Pantalla.test.tsx` → módulo inexistente (incluye el envío sin tildar). Dos ajustes sobre la marcha: `toBeDisabled` no existe (no hay `@testing-library/jest-dom` instalado en este proyecto) — se usó `.disabled` del elemento nativo; y el mensaje de error aparece dos veces (resumen enlazado + la casilla), igual que el 409 en 4.3 — se usó `findAllByText`. GREEN 21:20:26 → `5 passed`: envío sin tildar no llama a la acción y el foco vuelve a la casilla, tildar habilita el botón y confirma, "no se puede deshacer" explícito, estado ya confirmado sin formulario, axe sin violaciones.
  - `acciones.ts`/`page.tsx`/`loading.tsx`: una server action ligada a `complejoId` (D1); un 409 revalida igual que un `ok` (D11: la pantalla vuelve a pedir el resumen y, si ya no está en `pendiente`, muestra el estado). Sin test propio (cubierto por `edificios.test.ts` + `Pantalla.test.tsx`).
  - Suite completa 21:21:19 `test-web.sh`: `38 files, 203 passed` (vs. 195 de 4.6: +8). `pnpm biome ci` 21:21:12: limpio (0 errores, 1 warning no bloqueante de 4.1). `pnpm tsc --noEmit`: limpio.
  - Commit `feat(web): confirmar sin saldos previos sin modal (4.7)`.

**Cierre del bloque C (4.1-4.4)**: barrido real de las cuatro pantallas nuevas con `test-web-navegador.sh`
(`web/e2e/bloque-c.spec.ts`, 320 px + contenido real contra la API falsa; NO es el generador "sin huecos"
de 5.1, que sigue pendiente). Tres hallazgos reales, los tres arreglados en el mismo barrido:
- **CSS de layout faltante** (D10): nada en `tokens.css` plegaba el menú por debajo de 768 px ni
  acotaba el ancho a 320 px; la tabla del padrón desbordaba la página. Sumado a `tokens.css`: el layout
  `.armazon-del-edificio` (flex columna → fila a 768 px, replegando `.menu-del-edificio__lista` por
  `data-abierto`), `.encabezado-de-pantalla`, `.boton-principal` (el acento terracota, una vez por
  pantalla) y `.padron-de-unidades__scroll` (la tabla scrollea ADENTRO de su contenedor, nunca la
  página entera). De paso, `.sr-only` nunca se había definido desde que `Ayuda.tsx` la usa (3.6): el
  texto "Ayuda" quedaba a la vista en vez de oculto.
- **Bug real en la API falsa de 3.8** (`web/e2e/api-falsa.ts`): el escenario "vacio" mutaba `unidades` a
  `{ informe: null, unidades: [] }`, pero la API real (`informar_coeficientes([])`) nunca da `null` —
  siempre un informe bien formado. `Padron.informe` no es nulable (D4) y `PantallaPadron` rompía al
  leer `informe.estado` de `null` en un navegador real. RED 20:49:52 (`api-falsa.test.ts`, caso nuevo)
  → `expected null to deeply equal {...}`. GREEN 20:50:06 → `13 passed`.
- **`/edificios` se congelaba en build time**: sin segmento dinámico, Next.js la pre-renderizaba en
  `next build` —ANTES de que la API falsa (o la real) estuviera levantada— y `next start` servía para
  siempre esa respuesta congelada ("No pudimos cargar tus edificios."), sin volver a pedir nada en
  ningún request real. Visto fallar 4 veces seguidas en Playwright (no era flaky) antes de encontrar la
  causa. Arreglado con `export const dynamic = "force-dynamic"` en `web/src/app/edificios/page.tsx`;
  las rutas `/edificios/[id]/...` no lo necesitaban (el segmento dinámico ya las vuelve dinámicas).
- Playwright final 20:55:28 `test-web-navegador.sh`: `10 passed (3.5s)` (las 5 de `bloque-c.spec.ts` +
  las 5 genéricas de 3.8). `test-web.sh` 20:55:50: `33 files, 171 passed`. `pnpm biome ci`/`pnpm tsc
  --noEmit`: limpios. Sin procesos huérfanos (`pgrep -fa 'playwright|api-falsa|next'` vacío tras cada
  corrida) y sin contenedores propios en `docker ps`.
- **NO se corrió** `test-backend.sh` ni `humo.sh` (fuera del alcance del bloque C, los corre el
  orquestador) ni el generador "sin huecos" de 5.1 (grupo 5, no asignado a este bloque).

## 5. Barrido en el navegador y `DESIGN.md` (MEDIUM)

- [x] 5.1 Barrido completo con `infra/ci/test-web-navegador.sh`: las siete pantallas por cada escenario de `escenarios.ts` (incluidos nombres de 200 caracteres, identificadores de 40 y 200 unidades) a 320 px y a 1280 px, recorrido de teclado y axe con contraste. Verificación: la salida lista pantallas por escenarios sin huecos y en verde. Escenarios: `pantallas-del-edificio` › 320 px; › axe en cada estado. Lecciones: L-022.
  - `web/e2e/barrido-completo.spec.ts` (L-022: generado con dos `for` sobre `ESCENARIOS` y las pantallas, nunca un caso por línea) + `web/e2e/accesibilidad.ts` (axe inyectado a mano, D7, sin `@axe-core/playwright`) + dos funciones nuevas en `comprobaciones.ts` (`contornoDelElementoEnfocado`, `elFocoVolvioAlCuerpo`). Decisión declarada: "Mis edificios" (`/edificios`) no toma id de edificio (la API falsa sirve siempre `lista.json` sin mirar la URL) — se cubrió aparte (2 pruebas, una por ancho) en vez de forzarla al cruce; las otras seis pantallas × diez escenarios × dos anchos dan 120, más esas 2: **122 pruebas**, listadas explícitamente en la salida de Playwright, sin huecos.
  - RED 21:25:29 `test-web-navegador.sh` (primera corrida real): **122 failed, 10 passed** — axe `region`/`landmark-one-main` en TODAS: `.menu-del-edificio__volver`/`.menu-del-edificio__nombre` (el enlace "Mis edificios" y el nombre del edificio) quedaban fuera de cualquier landmark en `MenuDelEdificio.tsx` (contenedor `<div>`, nunca detectado por los tests de componente en jsdom: esas reglas de axe son de documento completo). Arreglo: el contenedor pasó a ser el propio `<nav aria-label="Menú del edificio">` (anidado con el `<nav aria-label="Secciones del edificio">` de adentro, válido con nombres distintos). "Mis edificios" (4.1) además no tenía NINGÚN `<main>`: su `<div>` raíz pasó a `<main>`.
  - Segunda corrida 21:37:24: **48 failed, 84 passed** — el landmark ya cerró, pero surgieron dos hallazgos más. (1) El recorrido de teclado de 3 `Tab` fallaba en pantallas con menos de tres controles enfocables (p.ej. "sin permiso"/"sin sesión", que por diseño de D8 no llevan ningún enlace): no era foco invisible, era que el recorrido ya había terminado — arreglado en el TEST (`elFocoVolvioAlCuerpo`, corta el recorrido sin fallar cuando el foco ya volvió a `<body>`), no en el producto. (2) Al sacar el ruido del teclado, axe mostró `landmark-one-main`/`page-has-heading-one`/`region` reales en las cuatro variantes de `Estados` que siempre reemplazan la pantalla completa (`error`, `sinPermiso`, `noExiste`, `sinSesion`: ningún `page.tsx` las anida dentro de `ArmazonDelEdificio`) — nunca tenían `<main>` ni `<h1>`. Arreglo en `Estados.tsx`: esas cuatro variantes pasan a `<main>` con su mensaje principal en `<h1>`; "vacio"/"cargando" NO cambian (sí se anidan dentro del `<main>` de `ArmazonDelEdificio`, un segundo `<main>` ahí sería la misma violación al revés).
  - GREEN 21:42:33 `test-web-navegador.sh`: **132 passed (2.8m)** (122 del barrido + 5 de `bloque-c.spec.ts` + 5 de `comprobaciones.spec.ts`, sin retocar). `test-web.sh` 21:45:44: `38 files, 203 passed`. `pnpm biome ci`/`pnpm tsc --noEmit`: limpios. Sin procesos huérfanos (`pgrep -fa 'playwright|chrome-headless|api-falsa|next-server'` vacío tras la corrida) y sin contenedores propios en `docker ps`.
  - **Supuesto no verificado**: el comentario de 4.1 sobre `useOptionalChain` (warning no bloqueante de biome) sigue sin tocar, por ser un fix "unsafe" sobre una guarda intencional — no es parte de este bloque.
  - Commit `test(web): barrido completo del navegador por pantalla y escenario (5.1)`.
- [x] 5.2 `DESIGN.md` con los valores reales: `/impeccable document`, o a mano si el comando no está disponible, con la tipografía, los tokens OKLCH, la escala y los componentes de D8; sin el comentario `SEED`. Verificación: ningún "to be resolved" ni "to be chosen" queda en el archivo (`rg`), y los valores coinciden con `tokens.css`. Escenarios: ninguno (documento).
  - Comando disponible (`/impeccable document`, scan mode). Frontmatter YAML con los cinco colores en OKLCH (doctrina del proyecto, D10: nunca se parte la fuente de verdad a hex) y los cuatro pasos de tipografía; las seis secciones del formato Stitch, en orden y sin renombrar.
  - Gotcha real encontrado documentando: `--tipo-titulo`/`--tipo-titular` estaban declarados en `tokens.css` desde la tarea 3.5 pero NUNCA conectados a ningún selector (`h1`/`h2` quedaban en el tamaño por defecto del navegador). Escribir "el documento dice la verdad" exigía resolverlo, no describirlo como intención. RED 21:48:33 `tokens.test.ts` (caso nuevo) → no hay regla `h1 { font-size: var(--tipo-titular) }`. GREEN 21:48:43 → `7 passed`. Las cuatro razones de contraste de la sección Colors (8,81:1 terracota, 15,90:1 tinta, 6,55:1 grafito, 6,09:1 advertencia, todas contra papel tibio) se calcularon de verdad con `web/src/lib/color/oklch.ts` (`tsx -e`, no a ojo), mismo módulo que ya usa `tokens.test.ts`.
  - Decisión declarada: Componentes documenta también lo que NO tiene estilo propio todavía (`Campo`/`Formulario`, botón secundario) en vez de inventarles una descripción — "no existe una clase propia" es la verdad, no un `[to be resolved]` disfrazado.
  - Verificación 21:54:16: `rg -n "to be resolved|to be chosen|SEED" DESIGN.md` → sin coincidencias; los cinco OKLCH y el `box-shadow` de `DESIGN.md` comparados a mano contra `tokens.css` → idénticos.
  - Suite completa 21:50:29 `test-web.sh`: `38 files, 204 passed` (vs. 203 de 5.1: +1, el caso nuevo de `tokens.test.ts`). `pnpm biome ci`/`pnpm tsc --noEmit`: limpios. Playwright final 21:50:51 `test-web-navegador.sh`: **132 passed (2.8m)**, sin procesos huérfanos ni contenedores propios.
  - Commit `docs(web): DESIGN.md con los valores reales de tokens.css (5.2)`.

## Pulido visual (orquestador, 19/10/2026)

Pasada de `impeccable polish` (registro product) sobre las siete pantallas, contra el shape aprobado
y `DESIGN.md`. Capturas a 1280×800 y 320×640 (normal, vacío, 200 unidades, advertencia, nombres largos,
error 500, 404, panel lateral y "?" abiertos), fuera del árbol versionado:

- Antes: `.git/informes-3b/pulido/antes/` (32 capturas).
- Después: `.git/informes-3b/pulido/despues/` (final) y `despues/iteracion-1/`, `despues/iteracion-2/`.
- Script de captura: `.git/informes-3b/pulido/capturar.mjs` (web :3300, API falsa :4300).

Cambios:

- [x] **Bug del "Hecho" con 0 unidades**: era la API falsa, no el backend. `resumen_edificio`
  (`backend/.../complejos/aplicacion/lectura.py:229`) da `"falta"` con 0 unidades; el escenario
  `vacio` de `web/e2e/api-falsa.ts` sólo pisaba `cantidad_unidades` y dejaba los pasos del fixture.
  Ahora unidades/coeficientes/categorías van en falta y `advertencia` deja coeficientes en hecho
  (lectura.py:230-233). Rojo: 2 casos nuevos en `api-falsa.test.ts`.
- [x] **Menú lateral**: a ≥768 px faltaba `flex-direction: column` (las secciones quedaban en una
  línea). Ahora columna fija de 15rem, sticky, fondo Papel hundido, sección actual con fondo
  Terracota tenue + "▸" + `aria-current`; nombre largo cortado a 3 renglones con `title`.
- [x] **Mis edificios**: lista de movimientos (grilla por renglón, no links azules sueltos), toda la
  fila tocable, el enlace se llama sólo como el edificio (antes su nombre accesible era todo pegado).
- [x] **Resumen**: checklist con renglones, número, estado separado (`data-estado`, "✓ Hecho" en
  Grafito, "○ Falta" en pastilla Terracota tenue), espacio real entre etiqueta y estado.
- [x] **Padrón**: textos a la izquierda y números a la derecha, encabezados Label 600 Grafito,
  identificador como texto de fila (`.boton-enlace`), tipo con su etiqueta ("Departamento"), estado
  de coeficientes como pastilla con ✓/!/✕.
- [x] **Panel lateral y "?"**: hojas fijas al borde derecho (antes caían en el flujo debajo de la
  tabla), "Cerrar" arriba a la derecha, entrada con `opacity` (`@starting-style`).
- [x] **Formularios**: `.formulario`/`.campo` con estilo propio (el gap declarado en DESIGN.md §5),
  error en Terracota con "!", casilla antes del texto, resumen de errores en bloque.
- [x] **Botones**: secundario como base de `button` (`:where()`), `.boton-enlace`, `.boton-icono`,
  hover/active/disabled del principal; el estado vacío repite la acción en secundario (One Voice).
- [x] **Grupos**: nombre en negrita + datos en Grafito, método en castellano ("por coeficiente"),
  renglón editable con "›".
- [x] **Categorías**: acciones calladas (borde Línea), "Desactivar" a la vista y el nombre sólo para
  el lector, subir/bajar en casillas fijas.
- [x] **Intereses y vencimiento**: la vigente como renglones etiqueta/valor (`<dl>`), historial como
  línea de tiempo con fechas dd/mm/aaaa (`formato.fecha`, sin `Date`) y "Primera versión".
- [x] **Saldos previos**: aviso "no se puede deshacer" en Advertencia tenue, casilla en renglón
  tocable, botón deshabilitado visible como tal.
- [x] **Estados**: error/404/403/401 centrados con aire; vacío con borde punteado; esqueleto de carga.
- [x] **Tokens**: 6 nuevos (papel-claro, papel-hundido, linea, terracota-oscura, terracota-tenue,
  advertencia-tenue), 8 pares de contraste nuevos en `tokens.test.ts`; `DESIGN.md` actualizado.
- [x] **Navegador**: `web/e2e/pulido.spec.ts` (4 casos de layout real que jsdom no ve: menú apilado,
  estado separado, panel fijo, alineación del padrón), vistos en rojo contra el build anterior.

## Vuelta de correcciones del rompedor (R3C)

Informe: `.git/informes-3b/rompedor/informe.md`. Orden por severidad (L-021, una
familia por hallazgo).

- [x] R3C-1 (CRÍTICA) + R3C-10 (MEDIA, la causa de que no se viera): `pedirApi`
  (`web/src/lib/api/cliente.ts`) mandaba el cuerpo como string sin `Content-Type`:
  `fetch` ponía `text/plain;charset=UTF-8` y FastAPI, que sólo parsea JSON con
  `application/json`/`+json`, daba 422 en TODA escritura. La API falsa del
  navegador (`web/e2e/api-falsa.ts`) tampoco miraba el método ni el Content-Type,
  así que el barrido completo nunca vio el 422.
  - RED 22:29:38 `vitest run src/lib/api/cliente.test.ts` → `R3C-1 · con cuerpo,
    declara Content-Type: application/json` falla: `Content-Type` es `null`.
  - RED (API falsa, revirtiendo temporalmente el fix para confirmarlo) 22:32:11
    `vitest run e2e/api-falsa.test.ts` → `3 failed`: un POST con `text/plain` da
    200 (esperaba 422), un arreglo válido como JSON da 200 (esperaba 422), y
    `/api/__debug/ultima-escritura` no existe (`SyntaxError: Unexpected end of
    JSON input`).
  - GREEN 22:33:28 `vitest run e2e/api-falsa.test.ts src/lib/api/cliente.test.ts`
    → `2 files, 44 passed`.
  - Backend (contrato de escritura, con identidad inyectada, patrón de
    `tests/integracion/test_contrato_web.py`):
    `backend/tests/integracion/test_contrato_web_escritura.py` nuevo — reusa el
    rojo original del rompedor (22:18:08, `backend/tests/rompedor_3b/`, pegado en
    el informe: `assert 422 == 201` con `text/plain`) y agrega la guarda
    permanente de las dos puntas. GREEN 22:30:16 `uv run pytest
    tests/integracion/test_contrato_web_escritura.py` → `2 passed`.
  - `pnpm biome ci`/`pnpm tsc --noEmit` (sobre los archivos tocados) y `uv run
    ruff check/format --check`/`mypy` sobre el test nuevo: limpios.
  - **Supuesto**: `biome ci` sobre el repo completo sigue en rojo mientras
    `web/src/__rompedor__/` y `web/e2e/rompedor.spec.ts` no se borran (formato
    propio del rompedor, no tocado a propósito: se borran al final del bloque).
  - Commit `fix(web): la escritura declara Content-Type: application/json (R3C-1, R3C-10)`.
- [x] R3C-3 (ALTA): `<form action={fn}>` (`Formulario.tsx`) se resetea solo al
  terminar la acción (React 19), sin importar si vuelve con error; los `Campo`
  son no controlados (`defaultValue`). Un 403/422/409 al guardar vaciaba todo lo
  tipeado — contradice la spec ("sin perder lo cargado").
  - RED 22:34:40 `vitest run src/componentes/Formulario.test.tsx` → `R3C-3 · un
    403/422/409 de la acción no borra lo cargado` falla: `expected '' to be
    'PB-LOCAL'`.
  - Arreglo: `Formulario` captura `new FormData(formulario)` en `onSubmit` (antes
    de que la acción corra) y, en un `useEffect` sobre
    `[erroresPorCampo, erroresDesconocidos]`, repone cada campo que el reset dejó
    vacío con lo capturado.
  - GREEN 22:36:32 `vitest run src/componentes/Formulario.test.tsx` → `7 passed`
    (los 6 casos viejos del componente siguen en verde). El caso ya existente de
    la misma familia en `src/__rompedor__/pantallas.test.tsx` (`unidades/
    Pantalla.tsx` completo) también pasa a verde con este mismo cambio, sin
    tocarlo.
  - `pnpm tsc --noEmit`: limpio (tuvo que tipar `namedItem` con
    `instanceof HTMLInputElement/HTMLTextAreaElement/HTMLSelectElement`, no un
    cast — `RadioNodeList` no es asignable a `HTMLInputElement`).
    `pnpm biome check` sobre los dos archivos: limpio (un
    `useExhaustiveDependencies` suprimido a propósito y declarado: el efecto
    depende de la IDENTIDAD de los errores, no de `hayErrores`, porque dos
    envíos fallidos seguidos dan el mismo `true` y el efecto no volvería a
    correr).
  - Commit `fix(web): un 403/422/409 ya no borra lo cargado en el panel (R3C-3)`.
- [x] R3C-4 (MEDIA): sin `key`, cambiar de fila con el panel abierto sólo cambiaba
  el `defaultValue` de los `Campo` (no controlados) — React no remonta un input ya
  montado, así que un campo ya tocado conservaba lo tipeado para la fila
  anterior, mientras el `unidad_id`/`grupo_id`/`categoria_id` oculto (controlado)
  ya apuntaba a la fila nueva. Mismo patrón en unidades, grupos y categorías.
  - RED (unidades, ya existía) 22:37 `vitest run src/__rompedor__/pantallas.test.tsx`
    → ya en verde con el fix (ver más abajo); el rojo original de este caso quedó
    documentado en el informe del rompedor. RED propio (grupos/categorías, revirtiendo
    el `key` para confirmarlo) 22:38:48 `vitest run .../grupos/Pantalla.test.tsx
    .../categorias/Pantalla.test.tsx` → `2 failed`: el nombre tipeado para la
    primera fila viajaba con el id de la segunda.
  - Arreglo: `<Formulario key={entidadEnEdicion?.id ?? "nueva"}>` en las tres
    `Pantalla.tsx` (unidades, grupos, categorías) — fuerza el remonte completo del
    formulario al cambiar de entidad.
  - Gotcha real escrito el test de categorías: `container.querySelector('input
    [name="categoria_id"]')` a secas matcheaba el hidden de
    activar/desactivar de la PRIMERA fila (mismo `name`, D-ficha 4.5), no el del
    panel — hubo que acotar a `.formulario input[name="categoria_id"]`.
  - GREEN 22:39:48 `vitest run .../categorias/Pantalla.test.tsx
    .../grupos/Pantalla.test.tsx .../unidades/Pantalla.test.tsx` → `3 files, 27
    passed`. `pnpm tsc --noEmit`/`pnpm biome check`: limpios.
  - Commit `fix(web): cambiar de fila con el panel abierto ya no mezcla dos entidades (R3C-4)`.

## 6. Cierre de los grupos 1 a 6

- [ ] 6.1 Corrida de cierre **después de la vuelta de rompedor y auditor y sus arreglos** (L-010), de a uno: `test-backend.sh`, `pnpm biome ci`, `pnpm tsc --noEmit`, `test-web.sh`, `test-web-navegador.sh` y `humo.sh`, con conteos comparados contra 1.1 (L-003) y el commit. Verificación: el informe trae comandos, salida y hora de cada uno. Escenarios: todos los de los grupos 1 a 6. Lecciones: L-003, L-005, L-010.

## 7. Acceso de desarrollo sin login (HIGH): NO CONSTRUIR, espera la firma HIGH de Juani (D-094)

Precondición: la sección "Aprobación" de `proposal.md` firmada por Juani o Alberto, con nombre, fecha y
la respuesta a PR4. Si PR4 se responde distinto de lo propuesto, se corrige D12 y la spec
`acceso-de-desarrollo` antes de empezar. Si no se firma, este grupo no se construye y el change se
archiva sin él.

- [ ] 7.0 **Movida del grupo 2 (bloqueada, ver nota) — la carga del ejemplo.** Carga del edificio de ejemplo en la base (la 7.2 del 3a, D9 del 3a, E6 y E10 firmadas): comando `python -m proptech_core.complejos.aplicacion.ejemplo cargar`, como `proptech_migrador` con el tenant de la administración de ejemplo fijado a propósito, por los mismos casos de uso que la API, todo en una transacción. Tests contra PostgreSQL real, primero en rojo (el comando no existe): primera carga con 13 unidades y la auditoría de crear y confirmar; segunda carga igual sin cambios; segunda carga después de cambiar la tasa en `parametros.yaml` da "ya estaba"; dos cargas en paralelo dejan un solo ejemplo; con una unidad editada falla sin escribir y dice qué difiere; otra administración con datos queda idéntica (comparación fila por fila); sin tenant no escribe nada. Escenarios: `datos-semilla` › Primera carga; › Segunda carga igual; › Cambiar los parámetros no hace fallar la carga; › Dos cargas a la vez; › El ejemplo cambió en la base; › Otras administraciones no se tocan. Lecciones: L-006, L-016.
  - **Por qué está acá y no en el grupo 2**: el constructor la frenó ahí porque `proptech_migrador` no tiene `GRANT` sobre `auditoria` (ownership pasa al rol de arranque en `roles.despues()`; sólo `proptech_app` recibe `SELECT, INSERT`, `src/proptech_core/compartido/roles.py:701-735`), y los casos de uso que D9/E10 pide reusar (`crear_edificio`, `confirmar_sin_saldos_previos`) auditan con `registrar()`, que exige `INSERT`. RED real contra Postgres: `psycopg.errors.InsufficientPrivilege: permission denied for table auditoria` (`uv run pytest tests/integracion/test_ejemplo_casos_de_uso.py -q` → `6 failed, 1 passed`). Decisión del orquestador: el `GRANT INSERT ON auditoria TO proptech_migrador` es un cambio de permisos sobre el log de auditoría — **CRITICAL** — y la decide Juani junto con la firma de este grupo, no el constructor solo.
  - **Ninguno de los grupos 3 a 6 la importa ni la necesita**: las pantallas y la base de test de la web no leen nada de la administración de ejemplo; sólo el recorrido contra la API real de la 7.3 depende de que esté cargada.
  - El trabajo (implementación + 7 tests, `ruff`/`mypy` limpios) está guardado sin commitear en `.git/informes-3b/2.3-wip/` (`ejemplo.py`, `test_ejemplo_casos_de_uso.py`) y el fixture `fabrica_migrador` como patch en `.git/informes-3b/2.3-wip.patch` (contra `backend/tests/integracion/conftest.py`). Se aplica recién junto con el `GRANT` firmado.
- [ ] 7.1 Las guardas, antes que el punto de entrada (D11 del 3a, D12): tests en `tests/infra/` que fallan si la imagen del backend contiene `desarrollo`, si `compose.yaml` lo referencia, si algún archivo del repositorio pone `COMPOSE_FILE` con `desarrollo`, o si `humo.sh` llama a `docker compose` sin `-f compose.yaml`; y uno que verifica 401 sin identidad en la app de producción. Rojo de cada uno sobre una copia que lo viola (L-013). Escenarios: `acceso-de-desarrollo` › La imagen de producción; › Producción sin identidad; › Un archivo que activa el override; › El humo sin archivo explícito. Lecciones: L-019, L-022.
- [ ] 7.2 El punto de entrada: `backend/desarrollo/app_de_desarrollo.py` (fuera de `src/`), que arma `crear_app()` y reemplaza la identidad con la del titular de ejemplo; se niega a arrancar sin la administración de ejemplo o con otra administración en la base (PR4); `infra/compose.desarrollo.yaml` que lo monta y publica la API sólo en `127.0.0.1`. Tests primero de las dos negativas. Escenarios: `acceso-de-desarrollo` › Base sin el ejemplo; › Base con otra administración. Lecciones: L-006, L-016.
- [ ] 7.3 Recorrido contra la API real: con el ejemplo cargado (7.0) y el acceso levantado, las siete pantallas en el navegador a 320 px y a 1280 px, con capturas y el recorrido de teclado, y la corrida de cierre del grupo (`test-backend.sh`, `humo.sh` y `test-web-navegador.sh`). Verificación: el informe trae las capturas, los comandos y su salida. Escenarios: `acceso-de-desarrollo` › Las pantallas contra la API real. Lecciones: L-010.
