## Why

El 3a dejó el edificio completo en la API, pero sólo se puede configurar con `curl`: el administrador
sigue armando el edificio en la planilla. Es la ficha 3b de `knowledge-base/12_fichas_de_changes.md`:
que el administrador configure su edificio desde el navegador (**HU-A1**, la mitad de las pantallas)
con su ayuda en cada pantalla (**HU-T1**, D-102). Sale del camino crítico a M1 (E1 del 3a), así que se
puede construir en paralelo al 4.

La experiencia ya está decidida: el `shape` de las siete pantallas lo aprobó Juani el 19/10/2026
(`openspec/exploraciones/2026-10-19-shape-pantallas-del-edificio.md`). Este propose no lo rediscute;
lo baja a requisitos verificables, a tareas y a lo poco que la API todavía no da.

Cubre: **HU-A1** (pantallas), **HU-T1**, **R01** (sólo mostrar la suma y su estado como los manda la
API, D-082), **R09** en el estado de migración (D-083), **R16**, la configuración de **R03**, **R15** y
**R26** (D-100). Decisiones: D-042, D-076, D-096 (la matriz que ya existe), D-100, **D-102**, D-103,
D-104 y, para el acceso de desarrollo, D-094 y E2 del 3a. Ninguna regla de plata se calcula acá.

## Gobernanza

**MEDIUM** todo el cambio **salvo el acceso de desarrollo sin login** (D11 del 3a, E2), que es
**HIGH**: toca cómo se saltea la identidad, aunque sea fuera de `src/`. Juani no está para firmar, así
que el cambio se parte en dos:

- **Grupos 1 a 6 (MEDIUM)**: se construyen ya, con checkpoints. Nada de esos grupos depende del acceso
  de desarrollo: las pantallas se prueban con la API simulada (componentes con datos de prueba y un
  cliente de la API probado contra `fetch` simulado), con una API falsa servida desde fixtures para el
  navegador real, y con fixtures que la API real genera con identidad inyectada, como ya hace el
  backend en sus tests (D3 y D4 del design).
- **Grupo 7 (HIGH): "NO CONSTRUIR: espera la firma HIGH de Juani (D-094)"**. El diseño de E2 está
  firmado desde el 16/10/2026; lo que falta es la firma para **construirlo** ahora, con la respuesta a
  PR4 del 3a (cómo se impide cargar el ejemplo en el piloto, de lo que depende su contención). Ver
  "Aprobación" al final.

La carga del ejemplo en la base (la 7.2 del 3a) **no depende del acceso de desarrollo** (es al revés:
el acceso la necesita), así que entra como MEDIUM en el grupo 2. Ya está firmada como diseño (E6 y E10
del 3a, Juani 16/10/2026) y su spec ya está sincronizada (`datos-semilla` › Carga del edificio de
ejemplo en la base).

**Proceso** (decisión de Juani, 19/10/2026): constructor Claude Sonnet con TDD, **una sola vuelta** de
rompedor y auditor Claude Opus; lo que encuentren se arregla sin otra vuelta, salvo un hallazgo
CRÍTICO o ALTO de seguridad. Sin Codex. Rompedor y auditor son de otro modelo que el constructor pero
de la misma familia: es una excepción consciente a L-025, que pide otra familia, y queda escrita.

**Tamaño**: 22 tareas MEDIUM más 3 en el grupo de la firma. Pasa del "partir pasadas unas veinte"
(D-088) porque Juani decidió las siete pantallas en un solo change; se registra como excepción, igual
que el 1c y el 3a. Cada tarea sigue siendo de medio día como mucho.

## What Changes

- **Siete pantallas** de la superficie del administrador, con la navegación común (menú lateral fijo
  que se pliega a "Secciones" por debajo de ~768 px): Mis edificios, Resumen (el checklist de puesta a
  punto), Padrón de unidades, Grupos de reparto, Categorías de gasto, Intereses y vencimiento
  (vigente más historial) y Confirmar "sin saldos previos". Una acción principal en terracota por
  pantalla; formularios en un **panel lateral**, nunca un modal.
- **La ayuda "?"** de cada pantalla con sus tres partes escritas en el mismo change (D-102).
- **Los tokens de `DESIGN.md`**: el constructor elige la tipografía (una sans humanista con números
  tabulares; no Inter ni la del sistema por reflejo) y los valores OKLCH del terracota y los neutros
  dentro de lo que dice `DESIGN.md`, los declara en su informe, y al final `DESIGN.md` queda con los
  valores reales (`/impeccable document` o a mano).
- **Lo que la API todavía no da**, en lectura y con los permisos que ya existen:
  - el **resumen** de un edificio suma su nombre, localidad, cantidad de unidades y los **seis pasos
    de puesta a punto** con "hecho" o "falta", más "listo para liquidar": el criterio de cada paso es
    una regla de negocio y vive en la API, no en la web;
  - el **historial** de la configuración suma el **nombre del autor** de cada versión (hoy trae sólo
    `autor_id`).
- **El edificio de ejemplo en la base**: el comando de carga (ex 7.2 del 3a), tal como lo pide la spec
  ya sincronizada.
- **Herramientas de test de la web**: `@testing-library/react`, `@testing-library/user-event`,
  `jsdom` y `axe-core` (con `vitest-axe` si suma), y **Playwright** para el navegador real (320 px,
  teclado, contraste); un script `infra/ci/test-web-navegador.sh` y su paso en el CI.
- **Acceso de desarrollo sin login** (D11 del 3a): **sólo** como grupo de tareas en espera de firma.

**La web no calcula**: la suma de coeficientes, la diferencia, su estado, los pasos de puesta a punto
y "listo para liquidar" vienen de la API. Montos y proporciones viajan como texto y la web sólo los
formatea (coma decimal, punto de miles, números tabulares), nunca con `Number` ni `parseFloat`.

## "Terminado cuando", por pantalla

Cada una de las siete, observable y con su test:

- se opera entera con **teclado**, en el orden de lectura, con **foco visible** en todo control y sin
  quedar tapado (WCAG 2.4.7, 2.4.11); el panel lateral atrapa el foco, se cierra con `Esc` y con un
  botón, y devuelve el foco a lo que lo abrió;
- cada **error** está **asociado a su campo por programa** (`aria-invalid` más `aria-describedby`),
  hay un resumen arriba que enlaza a cada campo, y el 422 o 409 de la API llega al campo que
  corresponde, en castellano simple y sin repetir el valor;
- los estados de **carga, vacío y error** (más 403 y 404) existen y se alcanzan **a pedido**: un test
  por estado y, en el navegador, eligiendo el edificio de la API falsa que da ese estado (D7), sin
  tocar código;
- a **320 px** no hay scroll horizontal, medido en un navegador real;
- **axe sin violaciones** en cada estado (jsdom para estructura y nombres; el navegador real para el
  contraste AA), objetivos de al menos 24 x 24 px, `prefers-reduced-motion` respetado;
- su **"?"** con las tres partes (¿Para qué sirve esta pantalla? / ¿Qué hago acá? / ¿Y después?), que
  se abre al tocar o con teclado y se cierra con botón y `Esc`;
- **la web no calcula** (un test por pantalla con un valor de la API que no cuadra con los datos:
  se muestra el de la API);
- **números tabulares** y **formato argentino**: coeficientes con 6 decimales, porcentajes, tasas y
  superficies con 2, la suma de coeficientes en porcentaje con 4 (D6).

## Capabilities

### New Capabilities

- `pantallas-del-edificio`: las siete pantallas del administrador, la navegación, la ayuda "?", los
  estados, la accesibilidad y la regla de que la web muestra lo que calcula la API.
- `acceso-de-desarrollo`: entrar a las pantallas contra la API real sin login, sólo en desarrollo, sin
  rastro en producción (D11 del 3a). Se escribe ahora; se construye después de la firma.

### Modified Capabilities

- `edificios-y-unidades`: el resumen del edificio informa los datos del edificio y la puesta a punto
  (requisito nuevo).
- `configuracion-versionada`: el historial nombra al autor de cada versión (requisito nuevo).

`datos-semilla` no cambia: la carga del ejemplo ya está en su spec y acá sólo se construye.

## Que intente romper el rompedor

Es un piso, no un techo (L-021):

- **Plata y proporciones**: un coeficiente `"0.0833333333"` o `"1e-1"` que llega de la API (se
  muestra tal cual o se rechaza, nunca se redondea); una suma `"0.999950"` que en porcentaje con 2
  decimales se vería "100,00 %"; un `parseFloat` o `Number` en cualquier camino de un valor de plata
  (un test que lo busca en el código y uno con un valor que `Number` pierde).
- **La web que calcula**: datos de unidades que suman 0,9 con un informe de la API que dice "ok" (tiene
  que mostrar "ok"); un checklist con unidades cargadas y el paso 1 en "falta" según la API.
- **Errores**: un 422 con `loc` de un campo que el formulario no tiene; un 422 con una lista de
  errores; un 409 de identificador repetido; un 500 con texto técnico (nunca se muestra); la API caída
  o lenta; un 401 (hasta el 2b es lo que da producción); HTML en un `detail`.
- **Teclado y foco**: abrir el panel, abrir el "?" adentro, `Esc` dos veces; guardar y que el foco
  vuelva a la fila; el menú plegado a 320 px; subir la primera categoría o bajar la última.
- **Pantalla chica**: 320 px con un identificador de 40 caracteres, un nombre de edificio de 200, una
  tasa de doble vencimiento y 200 unidades.
- **Lo irreversible**: confirmar "sin saldos previos" sin tildar la casilla (por teclado y por envío
  directo del formulario), dos veces seguidas, o con el estado ya confirmado.
- **Grupos**: el modo "propios" con un método que no es coeficiente; editar "Generales"; guardar el
  nombre y que falle la lista de unidades (dos pedidos, D9).
- **El contrato**: un campo que la API renombra y la web sigue leyendo con el nombre viejo (los
  fixtures de la API real tienen que hacer fallar el test de la web, D4).
- **El ejemplo cargado dos veces**: los seis escenarios de la spec, como en la 7.2 del 3a.

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` (L-001 a L-025). Detalle en `design.md` ("Cómo aplica cada
lección").

| Lección | Tareas |
|---|---|
| L-003 · contar los tests | 1.1 y 6.1 |
| L-005 · verde es todo el workflow | convención de `tasks.md` (biome, tsc y tests) y 6.1 |
| L-006 · lo destructivo apunta a un nombre del proyecto | 2.3 (sólo la administración de ejemplo) |
| L-007 · el error de una librería es una salida | 3.3 (nunca se muestra el texto técnico ni el valor rechazado) |
| L-009 · el arreglo se prueba en el gemelo | 3.2 y 3.4 (el formato y el contrato, contra los fixtures que da la API real) |
| L-010 · la corrida de cierre va al final | 6.1 |
| L-016 · una observación tiene que poder dar otro resultado | 3.8 (el chequeo de 320 px se ve fallar con un ancho fijo puesto a propósito) |
| L-017 · la entrada del escenario | 3.4 y 3.8 (los datos de prueba tienen la forma que da la API real, no una inventada) |
| L-019 · un test que no puede dar rojo | 3.1 (axe se ve fallar con un botón sin nombre) y cada pantalla |
| L-022 · comparar el conjunto completo | 3.8 y 5.1 (todas las pantallas por todos los estados, sacados de una lista única) |
| L-023 · lo que está fuera de `backend/` | 2.1, 2.2 y 3.4 (la web consume lo que cambia la API) |
| L-024 · cada vuelta de arreglos es código sin mirada | proceso: los arreglos de la única vuelta los mira el auditor |
| L-025 · otra familia de modelo | excepción decidida por Juani, escrita en Gobernanza |

L-001, L-002, L-004, L-008, L-011 a L-015, L-018, L-020 y L-021 aplican como en todo cambio o no tienen
superficie acá (sin migraciones, sin hilos, sin plazos sobre operaciones con efecto).

## Preguntas abiertas

Ninguna bloquea los grupos 1 a 6. Las que el constructor decide y declara (shape, §10) están cerradas
en `design.md` (D5, D10, D11) para que no se decidan a la pasada.

| Pregunta | Qué toca | Decide |
|---|---|---|
| **PB1** · Un edificio nuevo muestra "falta" en todo el checklist (shape, §6), pero grupos, categorías y configuración nacen con los valores de los parámetros (D-042). D5 resuelve por los datos: esos tres pasos nacen "hecho" | El texto del resumen; no cambia tareas | Juani |
| **PR4 del 3a** · Cómo se impide cargar el ejemplo en el piloto | Sólo el grupo 7 (la contención del acceso de desarrollo) | Juani, al firmar |
| **P47** · Ramas o turnos con dos desarrolladores | La integración, no el código | Juani y Alberto |

## Fuera del cambio

- **El login** (2b) y toda pantalla del vecino o del consejo; las del vecino van con su propia
  densidad (principio 4 de `PRODUCT.md`).
- **Cálculos** de cualquier tipo en la web; **carga masiva desde Excel** (5).
- **Borrar** edificios, unidades, grupos o categorías (la API no tiene baja).
- **Arrastrar** para reordenar categorías: si se agrega, es un extra, nunca la única forma.
- **Construir el acceso de desarrollo** sin la firma del grupo 7.
- Cambiar permisos, la matriz de D-096 o el contrato de error de la API (D6 del 3a).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 19/10/2026): `01` a `16` y `README.md`.

- `06_funcionalidades.md`: **REWRITE** al archivar: los criterios de HU-A1 que dependen de pantallas
  pasan a cumplidos y HU-T1 nombra las siete pantallas con su "?".
- `08_arquitectura_propuesta.md`: **REWRITE** al archivar: la web (lectura en el servidor, escritura
  con server actions, el cliente de la API, los fixtures del contrato) y, si se firma el grupo 7, el
  punto de entrada de desarrollo y el migrador como credencial de la carga del ejemplo.
- `02_descripcion_general.md`: **REWRITE** al archivar: el stack de la web suma las herramientas de
  test, Playwright y la tipografía elegida.
- `04_modelo_de_datos.md`: **REWRITE** al archivar, sólo la sección de la semilla: el ejemplo ya se
  carga en la base.
- `12_fichas_de_changes.md`: **REWRITE** al archivar: el cierre del 3b, y si el grupo 7 queda sin
  firmar, que pasa al 2b o a un change propio.
- `09_decisiones_y_supuestos.md`: **APPEND** al archivar: una decisión con las elecciones de este
  propose (D1 a D11 del design) y la respuesta a PB1; otra con la firma o no del grupo 7.
- `10_preguntas_abiertas.md`: **REWRITE** al archivar si se responde PB1, PR4 o P47.
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor; lo escribe quien archiva.
- `01`, `03`, `05`, `07`, `11`, `13`, `14`, `16` y `README.md`: **none**. No cambia ningún rol,
  permiso, regla, flujo ni término: las pantallas muestran lo que el 3a ya definió.
- Fuera de `knowledge-base/`: `DESIGN.md` (**REWRITE** en la tarea 5.2, con los tokens reales);
  `CHANGES.md` (**REWRITE** al archivar).

## Impact

- **Web**: `web/src/app/` suma las rutas del administrador (`/edificios` y `/edificios/[id]/...`), el
  layout con el menú, `loading`, `error` y `not-found`; `web/src/lib/` suma el formato argentino, el
  cliente de la API del lado del servidor y los componentes comunes (ayuda, panel lateral,
  formulario con errores, estados). `web/vitest.config.ts` suma el entorno `jsdom` sin mover los 16
  tests de hoy, que siguen en `node`.
- **Backend**: `proptech_api/complejos.py` y `complejos/aplicacion/lectura.py` (resumen e historial,
  sólo lectura, sin migraciones ni permisos nuevos); el comando de carga del ejemplo en
  `complejos/aplicacion/`; un test que genera los fixtures del contrato.
- **Infra**: `infra/ci/test-web-navegador.sh` y un paso en `.github/workflows/ci.yml`. El grupo 7, si se
  firma, suma `backend/desarrollo/` e `infra/compose.desarrollo.yaml`.
- **Dependencias nuevas** (sólo de desarrollo de la web): `@testing-library/react`,
  `@testing-library/user-event`, `jsdom`, `axe-core`, `vitest-axe` (opcional), `@playwright/test`; y la
  tipografía, servida desde la propia web (D10). Ninguna dependencia de producción del backend.
- **Contrato de la API**: dos respuestas suman campos (`/resumen` y `/configuracion/versiones`); nada
  se renombra ni se quita.

## Aprobación

Gobernanza HIGH (D-094), **sólo para el grupo 7** de `tasks.md` (acceso de desarrollo sin login). Los
grupos 1 a 6 son MEDIUM y no la necesitan. La completa, a mano, Juani o Alberto. Ningún agente la
escribe.

| Elección | Propuesta | Aprobada (sí / no, con motivo) |
|---|---|---|
| Construir ahora el acceso de desarrollo de E2 (D11 del 3a, design D12 de este cambio) | Sí, tal como lo firmó E2: punto de entrada fuera de `src/`, `compose.desarrollo.yaml` aparte, identidad fija del titular de ejemplo, con sus seis guardas en test. Alternativa: no construirlo y esperar al 2b (las pantallas igual quedan probadas con la API falsa y los fixtures) | |
| PR4 del 3a · Cómo se impide cargar el ejemplo en el piloto | Que el punto de entrada de desarrollo se niegue a arrancar si la base tiene alguna administración que no sea la de ejemplo (no cambia el comando de carga ni su spec). Alternativas: sacar el comando de la imagen; dejarlo escrito | |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
