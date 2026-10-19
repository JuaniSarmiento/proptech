## Context

Ver `proposal.md` (Why y Gobernanza) y el `shape` aprobado
(`openspec/exploraciones/2026-10-19-shape-pantallas-del-edificio.md`), que es la fuente de verdad de la
experiencia. Lo que condiciona el cómo:

- **La web hoy** (`web/`): Next 16.4 con App Router, React 19.3, TypeScript 6, vitest 5 en entorno
  `node`, biome; una página técnica y `/salud-web`. 16 tests. Sin estilos, sin librería de tests de
  componentes, sin axe ni navegador. `infra/ci/test-web.sh` corre sólo `vitest run`; biome y `tsc`
  los corre el job `web` del CI aparte.
- **Cómo llega la web a la API**: Caddy manda `/api/*` a la API y el resto a la web; el servidor de
  Next tiene `PROPTECH_URL_API_INTERNA` (`http://api:8000`) y el navegador nunca la ve. D11 del 3a fijó
  que la web llama a la API **desde el servidor de Next**, igual en desarrollo que en producción.
- **La API del 3a** (`backend/src/proptech_api/complejos.py`, specs ya sincronizadas): todo bajo
  `/api` con identidad; errores **401** → **422 del cuerpo** (`loc`, `msg`, nunca el valor) → **404**
  `{"detail": "no encontrado"}` → **403** `{"detail": {"detalle": "sin_permiso", "permiso_faltante"}}`
  → **409** `{"detail": "conflicto", "campo"}` o **422 semántico**. Montos y proporciones como texto.
  Hasta el 2b, en producción, todo da 401.
- **Lo que la API no da** para el `shape`: los pasos del checklist y "listo para liquidar" (el resumen
  trae sólo estado de migración e informe), los datos del edificio en el resumen, la cantidad de
  unidades por edificio en la lista, y el nombre del autor de una versión (trae `autor_id`).
- **Grupos**: el alta acepta unidades en el mismo pedido; la edición son dos pedidos
  (`PATCH /api/grupos/{id}` y `PUT /api/grupos/{id}/unidades`).

## Goals / Non-Goals

**Goals:**

- Que las siete pantallas cumplan su "Terminado cuando" **sin** el acceso de desarrollo, con pruebas
  que pueden dar rojo.
- Que el contrato entre la web y la API no se separe en silencio.
- Que todo lo que es regla de negocio (incluido qué cuenta como "hecho") viva en la API.

**Non-Goals:**

- Superficie del vecino y del consejo, login, cálculos, Excel.
- Una librería de componentes de terceros: los componentes comunes son pocos y propios.

## Decisions

### D1 · Lectura en el servidor, escritura con server actions

Cada página es un componente de servidor que pide sus datos con el cliente de D2 y se los pasa a un
componente de cliente que dibuja la pantalla. Las altas y ediciones son **server actions** que llaman
a la API con el mismo cliente y devuelven un resultado tipado (`ok` con los datos nuevos, o errores por
campo) que el formulario muestra con `useActionState`. Después de guardar, la acción revalida la ruta
para que la fila y la suma salgan de la API.

| Alternativa | Por qué no |
|---|---|
| `fetch` del navegador a `/api` por Caddy | Contradice D11 del 3a; en `next dev` sin Caddy hace falta un proxy; en el 2b el token tendría que vivir en el navegador |
| Un proxy propio en Next (`/bff/...`) | Una superficie pública más que no aporta nada sobre las server actions |

Costo de revertir: medio. Los componentes de cliente reciben datos y acciones por props, así que
cambiar de dónde vienen no toca las pantallas.

### D2 · Un cliente de la API y un mapa de errores

`web/src/lib/api/` con una función por ruta que usa la web. Lee `PROPTECH_URL_API_INTERNA`, manda el
`x-request-id` de `lib/seguimiento.ts`, y devuelve una unión discriminada: `ok`, `sin_sesion` (401),
`sin_permiso` (403, con el permiso), `no_existe` (404), `conflicto` (409, con el campo), `invalido`
(422, con una lista de `{campo, motivo}` sacada de `loc` sin el primer segmento `body`), `fallo` (5xx,
red o un cuerpo que no se entiende). **Nunca** pasa a la pantalla un texto que vino de la API: los
mensajes en castellano salen de un diccionario por campo y motivo, con uno genérico por defecto (L-007).
Los valores de plata se validan como texto decimal ASCII y, si no lo son, el resultado es `fallo`.

### D3 · Cómo se prueba sin el acceso de desarrollo

Tres capas, ninguna necesita el grupo 7:

1. **Componentes** (vitest con `jsdom`, `@testing-library/react`, `user-event`): cada pantalla se
   renderiza con datos de prueba y con acciones simuladas (`vi.fn`); un test por estado, por error y
   por interacción de teclado, más axe en cada estado.
2. **Cliente de la API** (vitest en `node`): `fetch` simulado con cada respuesta del contrato de error.
3. **Navegador real** (Playwright, D7): `next build` y `next start` con `PROPTECH_URL_API_INTERNA`
   apuntando a la API falsa.

Los 16 tests de hoy siguen en `node`; el entorno `jsdom` se pide por archivo (o con `projects` de
vitest), nunca cambiando el entorno por defecto.

### D4 · Fixtures del contrato, generados por la API real

El riesgo de probar con datos de prueba es probar contra un contrato inventado (la razón por la que D11
del 3a descartó "datos falsos en la web"). Se cierra así: un test del backend
(`tests/integracion/test_contrato_web.py`) arma un edificio con los casos de uso, llama a cada ruta de
lectura que usa la web con la identidad inyectada (como ya hacen los tests del backend) y compara la
**forma** de cada respuesta (claves y tipos, no los ids ni las fechas) con los fixtures de
`web/src/lib/api/fixtures/*.json`. Los tests de la web y la API falsa usan esos mismos fixtures. Si la
API renombra un campo, falla el test del backend; si la web lee un campo que el fixture no tiene,
falla el de la web. Con un modo `--actualizar` explícito que reescribe los fixtures, para cambios
deliberados del contrato.

Alternativa descartada: MSW con respuestas escritas a mano (mismo problema de deriva, más una
dependencia).

### D5 · La puesta a punto y el autor viven en la API

Que un paso esté "hecho" es una regla de negocio, y "listo para liquidar" más todavía: si la web lo
decidiera, el cambio 7 tendría que volver a decidirlo. Así que `GET /api/complejos/{id}/resumen` suma
`nombre`, `localidad`, `cantidad_unidades`, `pasos` (seis claves fijas con `hecho` o `falta`) y
`listo_para_liquidar`, con los criterios de la spec (`edificios-y-unidades` › Resumen y puesta a punto
del edificio), en una función de `complejos/aplicacion/lectura.py`. Mismo permiso que hoy; ninguna
migración.

**PB1**: el `shape` (§6) dice que un edificio nuevo muestra todo en "falta", pero grupos, categorías y
configuración nacen con los valores de los parámetros (D-042) y la API no sabe si alguien "los revisó".
Se resuelve por los datos (esos tres nacen "hecho") y se le pregunta a Juani: si quiere "falta" hasta
que el administrador los mire, hace falta guardar esa marca, que es otro change.

"Mis edificios" pide el resumen de cada edificio en el servidor, en paralelo (1 a 30 por
administración). Alternativa descartada: sumar esos campos a `GET /api/complejos`, que también usa el
vecino (D-076) y le daría datos de configuración que hoy no ve (B5 del 3a).

`GET /api/complejos/{id}/configuracion/versiones` suma `autor_nombre` con un `JOIN` a `persona` por
la FK compuesta que ya existe (`fk_configuracion_autor`: el autor es siempre de la misma
administración), dentro de la misma sesión con tenant. Quién lo ve: los mismos que hoy ven el historial (titular, colaboradores y consejo). Es el
nombre de quien cambió la tasa del consorcio, información que el consejo tiene derecho a ver; la
alternativa (mostrar "el titular" sin nombre) no distingue entre dos titulares.

### D6 · Números: texto decimal y nada más

`web/src/lib/formato.ts` con funciones puras sobre texto decimal ASCII (validado con una expresión
anclada, L-008): `coeficiente` (6 decimales), `porcentaje`, `tasa` y `superficie` (2), y
`sumaComoPorcentaje` (mueve la coma dos lugares sobre el texto de 6 decimales: `"0.999950"` →
`"99,9950 %"`). Punto de miles y coma decimal por manipulación de texto. **Ni `Number`, ni
`parseFloat`, ni `Intl.NumberFormat` sobre un valor de plata**: un test recorre `web/src` y falla si
aparece cualquiera de los tres en un archivo que importa `formato.ts` o el cliente de la API.

La suma en porcentaje lleva **4 decimales**, no 2: la tolerancia de R01 es ±0,0001 (0,01 %) y una
diferencia de 0,000050 con 2 decimales se vería "100,00 %", que es redondear en pantalla lo que la base
no redondeó (The Tabular Money Rule). Los coeficientes de cada unidad se muestran como fracción con 6
decimales, igual que en el reglamento. La diferencia se muestra como "falta" o "sobra" según su signo,
leído del texto (el primer carácter), no comparando números.

### D7 · El navegador real: Playwright contra una API falsa

`web/e2e/` con Playwright (sólo Chromium), una API falsa en Node (`web/e2e/api-falsa.ts`, un servidor
HTTP sin dependencias) que sirve los fixtures de D4, y `infra/ci/test-web-navegador.sh` que hace
`next build`, levanta la API falsa y `next start`, y corre las pruebas. Se suma como paso del job `web`
del CI, después de `test-web.sh`.

**Estados a pedido sin tocar código**: la API falsa decide la respuesta por el id del edificio. Cada
estado tiene un UUID fijo en `web/e2e/escenarios.ts` (vacío, lento, 500, 403, 404, 401, coeficientes
en advertencia y fuera de tolerancia, 200 unidades, nombres largos). Entrar a
`/edificios/<id-del-escenario>` muestra ese estado en el navegador, y la misma lista alimenta las
pruebas: cada pantalla por cada escenario, **sacados de la lista y no escritos uno por uno** (L-022).

Qué mide cada prueba: a 320 px, `document.documentElement.scrollWidth <= innerWidth`; recorrido con
`Tab` con el foco visible (contorno calculado distinto de `none`); axe (inyectando `axe-core`, sin
`@axe-core/playwright`) con contraste; `prefers-reduced-motion: reduce` emulado. Rojo obligatorio
(L-016): el chequeo de 320 px se ve fallar con un elemento de 400 px de ancho puesto a propósito sobre
una copia.

Alternativas: verificar a mano con un navegador (no deja rastro ni protege de regresiones); jsdom
solo (no calcula layout ni contraste).

### D8 · Componentes comunes, propios

En `web/src/componentes/`: `EncabezadoDePantalla` (título, "?", acción principal), `Ayuda` (un panel
no modal con las tres partes y su texto por props), `PanelLateral` (`<dialog>` no modal con trampa de
foco propia, `Esc`, botón de cerrar y devolución del foco), `Formulario` (resumen de errores enlazado y
campos con `aria-invalid` y `aria-describedby`), `Estados` (esqueleto, vacío, error con "Reintentar",
sin permiso, no existe, sin sesión) y `EstadoDeCoeficientes` (texto más la diferencia, nunca sólo
color). Cada pantalla tiene su texto de ayuda en un archivo al lado (`ayuda.ts`), así cambia en el
mismo commit que la pantalla (The Always-Help Rule).

Sin librería de componentes: son seis piezas, y las de terceros traen un modal por defecto y estilos
que hay que pelear contra `DESIGN.md`.

### D9 · Grupos: dos pedidos y sin suma en vivo

Editar un grupo son dos pedidos a la API (datos y unidades). La acción los hace en ese orden y, si el
segundo falla, devuelve "se guardaron el nombre y el método; las unidades no", con los errores de las
unidades en sus campos. Después revalida, así la lista muestra lo que de verdad quedó. No se suma una
ruta atómica a la API: es un cambio de contrato del 3a para un caso raro.

En el modo "propios" el panel **no** muestra una suma en vivo de los coeficientes que se van cargando:
sería la web calculando R01. Muestra el informe de la API después de guardar, en el panel y en la fila.

### D10 · Tipografía y tokens

El constructor elige una sans humanista con números tabulares, buena en castellano (candidatas del
`shape`: Source Sans 3, Fira Sans, Noto Sans; **no** Inter ni la del sistema por reflejo) y la declara
con el motivo. Se sirve **desde la propia web** (`next/font/local` con los archivos en el repo o un
paquete `@fontsource`), nunca pedida a un tercero en cada visita: la superficie del vecino va a tener
mala señal y el repositorio no carga nada de afuera en tiempo de ejecución.

Los tokens van como variables CSS en `web/src/app/tokens.css`: terracota, papel tibio, tinta y
grafito suave en OKLCH, más los de estado (ok, advertencia, fuera de tolerancia) siempre acompañados
de texto. El constructor declara los valores y un test verifica, con la conversión OKLCH a sRGB, que
tinta sobre papel y el texto sobre terracota llegan a 4,5:1 (el navegador real lo vuelve a medir con
axe). Al final, `DESIGN.md` queda con los valores reales y sin el comentario `SEED`.

### D11 · Las otras dos preguntas del `shape`

- **Confirmar "sin saldos previos" es una pantalla propia** (`/edificios/[id]/saldos-previos`): la
  ficha la cuenta como pantalla, tiene su "?" propio y el paso 6 del checklist enlaza ahí. No va en el
  menú lateral: se llega desde el resumen.
- **"Mis edificios" con un solo edificio muestra la lista igual**: entrar directo esconde "Nuevo
  edificio" y hace que la misma dirección muestre cosas distintas según cuántos edificios haya.

### D12 · El acceso de desarrollo (grupo 7, espera la firma)

Es D11 del 3a sin cambios, más la respuesta propuesta a PR4: el punto de entrada se niega a arrancar si
la base tiene alguna administración que no sea la de ejemplo. Así la contención (identidad fija más
RLS) no depende de que nadie corra la carga en el piloto: en el piloto hay administraciones reales y el
punto de entrada no arranca. No cambia el comando de carga ni su spec. Las guardas de D11 del 3a
(imagen sin `desarrollo`, 401 en producción, `compose.yaml` sin referencias, ningún `COMPOSE_FILE` con
`desarrollo`, `humo.sh` con `-f compose.yaml`) se escriben **antes** que el punto de entrada y se ven
fallar contra una copia que las viola.

Nada de los grupos 1 a 6 lo importa ni lo necesita: si no se firma, el change se archiva sin el grupo
7 y la ficha lo pasa al 2b o a un change propio.

## Cómo aplica cada lección

Resumen en `proposal.md`. Las que cambian cómo se escribe una tarea:

- **L-019**: cada herramienta nueva se ve fallar antes de confiar en ella: axe con un botón sin nombre,
  el chequeo de 320 px con un ancho fijo, el test de "sin `Number`" con un `parseFloat` puesto a
  propósito, el contrato con un campo renombrado. En una copia o un commit local que se descarta
  (L-013).
- **L-022**: las pruebas del navegador recorren pantallas por escenarios desde una lista única; un
  escenario nuevo sin prueba hace fallar la suite.
- **L-023**: lo que cambia en la API (2.1, 2.2) se busca con `rg` en `web/`, `infra/` y los fixtures
  antes de cerrar la tarea.
- **L-007**: ningún texto de la API llega a la pantalla; un test con un marcador en `detail` y en `msg`
  lo prueba en el cliente.

## Risks / Trade-offs

- [Server actions como superficie pública] → cualquiera puede invocarlas. Mitigación: no deciden
  nada, sólo reenvían a la API, que exige identidad y permiso; hasta el 2b dan 401 como el resto.
- [Fixtures y API se separan] → D4 los ata con un test de cada lado.
- [Playwright pesa en el CI] → sólo Chromium, con caché de navegadores; si el job pasa de unos minutos
  se evalúa correrlo sólo en `main`. Es la única forma de medir 320 px y contraste.
- [`next build` necesita la tipografía] → servida desde el repo (D10), sin red en el build.
- ["Mis edificios" pide el resumen de cada edificio] → hasta 30 pedidos por carga;
  aceptable para el rango real, y si molesta se suma una ruta de lista para roles con
  permiso de lectura.
- [Mismo modelo de familia revisando] → excepción a L-025 decidida por Juani; el auditor la tiene que
  nombrar en su veredicto.
- [El grupo 7 sin firma] → las pantallas no se ven contra la API real antes del 2b. Mitigación: D4 y
  D7; el riesgo que queda es de comportamiento real (tiempos, datos grandes), no de contrato.

## Migration Plan

Sin migraciones. Las dos respuestas de la API suman campos, no los quitan. La web nueva se publica
como el resto; hasta el 2b sus pantallas muestran el estado "sin sesión" en producción, porque la API
da 401. Rollback: volver al commit anterior; no hay datos que deshacer, salvo el ejemplo cargado en una
base de desarrollo (no se carga en producción).

## Open Questions

- **PB1**: ver D5. No cambia tareas: sólo el texto del resumen si Juani prefiere otra cosa (y entonces
  es otro change).
- **PR4 del 3a**: ver D12. Se responde al firmar el grupo 7.
