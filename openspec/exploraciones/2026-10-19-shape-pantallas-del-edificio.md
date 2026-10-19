# Shape: pantallas del edificio (3b)

Brief de diseño de `impeccable shape` para la superficie del administrador del change 3b. Las respuestas
de Juani son del 19/10/2026; el OK del brief queda anotado al final. Precondición del propose del 3b
(ficha 3b en `knowledge-base/12_fichas_de_changes.md`). Se hizo un solo shape para las siete pantallas,
por decisión de Juani, en lugar de una sesión por pantalla.

## 1. Resumen

Siete pantallas para que el administrador configure un edificio desde el navegador, sobre la API del 3a:
mis edificios, resumen, padrón de unidades, grupos de reparto, categorías de gasto, intereses y
vencimiento con fondo de reserva, y confirmar "sin saldos previos". Tienen que reemplazar la planilla con
la que hoy arma el edificio, sin parecerse a una planilla.

## 2. Acción principal

Dejar un edificio **listo para liquidar**: unidades cargadas, coeficientes que suman 100%, grupos,
categorías y vencimiento definidos, y el estado de migración confirmado. Cada pantalla tiene una sola
acción principal en terracota.

## 3. Dirección de diseño

- **Estrategia de color**: Restrained (la de `DESIGN.md`): neutros tibios, un único acento terracota en
  menos del 10% de cada pantalla.
- **Escena**: el administrador, de día, en su oficina iluminada, frente a una pantalla de escritorio,
  cargando un edificio nuevo con el Excel viejo abierto al lado para copiar datos; concentrado, sin
  apuro, pero sin paciencia para lo que no entiende. Tema claro.
- **Referencias**: Mercado Pago (familiaridad, acciones obvias, nada que adivinar) y el home banking
  (Galicia, Brubank): listas de movimientos prolijas, estados claros, importes alineados. Por encima de
  las dos, el North Star de `DESIGN.md`: "El recibo prolijo".
- Probes visuales: omitidos (el entorno no genera imágenes; `DESIGN.md` ya fija la dirección).

## 4. Alcance

- Fidelidad: **listo para usar** (producción), según el "Terminado cuando" de la ficha 3b.
- Amplitud: las siete pantallas más la navegación común.
- Interactividad: componentes reales contra la API del 3a, con el acceso de desarrollo de D11.

## 5. Estructura

**Navegación**: menú lateral fijo a la izquierda dentro de un edificio: Resumen, Unidades, Grupos,
Categorías, Intereses y vencimiento. Arriba del menú, el nombre del edificio y un enlace a "Mis
edificios". La sección actual se marca con texto y forma, no sólo con color. Por debajo de ~768 px el
menú se pliega a un botón "Secciones" que lo despliega; a 320 px no hay scroll horizontal.

**Encabezado de cada pantalla**: título, el botón "?" junto al título (The Always-Help Rule) y, a la
derecha, la acción principal de esa pantalla.

Pantalla por pantalla:

1. **Mis edificios**: lista (no grilla de tarjetas iguales) con nombre, localidad, cantidad de unidades,
   estado de los coeficientes y estado de migración, cada estado con texto. Acción principal: "Nuevo
   edificio" (formulario corto: nombre y localidad; el resto se configura adentro).
2. **Resumen del edificio**: el checklist de puesta a punto, con cada paso en "hecho" o "falta" y su
   enlace: 1. Cargar unidades. 2. Revisar coeficientes (suma 100%). 3. Grupos de reparto. 4. Categorías
   de gasto. 5. Intereses y vencimiento. 6. Confirmar saldos previos. Debajo, los datos del edificio y
   la configuración vigente en una línea. Un edificio con todo hecho muestra "Listo para liquidar".
3. **Padrón de unidades**: tabla con identificador, tipo, piso, superficie y coeficiente; los números
   alineados a la derecha, tabulares, con formato argentino. Arriba de la tabla, la suma de coeficientes
   y su estado según R01 (ok, advertencia, fuera de tolerancia), con texto que dice cuánto falta o
   sobra; **la web no calcula: la suma y el estado vienen de la API**. Acción principal: "Agregar
   unidad". Tocar una fila o "Agregar" abre un **panel lateral** con el formulario (no un modal, no una
   página aparte); guardar cierra el panel, actualiza la fila y la suma. Pensada para 10 a 200 unidades.
4. **Grupos de reparto**: lista de grupos con nombre, método y modo de coeficientes (renormalizado o
   propios), cantidad de unidades y, para los "propios", su estado R01. "Generales" se muestra primero,
   marcado como automático y sin acciones de edición, con una línea que explica por qué. Crear o editar
   un grupo abre el panel lateral: nombre, método, modo y la selección de unidades (con coeficiente por
   unidad si el modo es "propios"). Cambiar el modo avisa en el panel que se reescriben los coeficientes.
5. **Categorías de gasto**: lista ordenada con nombre y estado (activa o desactivada). Agregar, renombrar,
   desactivar y reactivar. Reordenar con botones "subir" y "bajar" operables con teclado (arrastrar, si
   se agrega, es un extra, nunca la única forma).
6. **Intereses y vencimiento** (configuración versionada): arriba, la **configuración vigente** bien clara
   (tasa de interés, fondo de reserva, vencimiento único o doble con su día y su recargo). Debajo, el
   **historial** como línea de tiempo: desde qué fecha rigió cada versión, quién la creó y qué cambió
   respecto de la anterior. "Cambiar configuración" abre el panel lateral con la fecha "rige desde" (hoy
   en Mendoza o después) y avisa que la versión vieja no se borra.
7. **Confirmar "sin saldos previos"**: una sección del resumen o pantalla propia (a decidir al construir,
   ver preguntas abiertas). Explica en castellano simple qué significa (el edificio arranca sin deudas ni
   saldos anteriores) y que **no se puede deshacer**. Una casilla "Entiendo que el edificio arranca sin
   deudas anteriores" habilita el botón de confirmar. Sin modal. Sólo visible mientras el estado es
   "pendiente".

## 6. Estados

En las siete pantallas:
- **Cargando**: esqueleto con la forma del contenido, sin girador a pantalla completa.
- **Vacío**: siempre con el siguiente paso. Mis edificios sin edificios: "Todavía no tenés edificios" con
  "Nuevo edificio". Resumen de un edificio nuevo: el checklist con todo en "falta".
- **Error de carga**: qué pasó en una línea y "Reintentar"; nunca el texto técnico.
- **Error de un formulario**: cada error junto a su campo y asociado por programa; arriba del formulario,
  un resumen que enlaza a cada campo con error. Los mensajes de la API (422) se muestran en castellano
  simple.
- **Guardado**: confirmación breve en el lugar de lo que cambió (la fila, la suma), sin cartel que tape.
- **Sin permiso (403)**: qué no puede hacer y quién sí. **No existe (404)**: "No encontramos este
  edificio" con enlace a Mis edificios.
- **Coeficientes**: ok, advertencia (0,9999 a 1,0001, distinto de 1) y fuera de tolerancia, siempre
  con texto y con el número de la diferencia, nunca sólo con color.

## 7. Interacción

- Todo se opera con teclado, con foco visible; el panel lateral atrapa el foco mientras está abierto, se
  cierra con `Esc` y con un botón visible, y devuelve el foco a la fila o el botón que lo abrió.
- El "?" se abre al tocar o al hacer clic, nunca sólo al pasar el mouse; es un panel con letra del
  tamaño del cuerpo, con las tres partes (¿Para qué sirve esta pantalla? / ¿Qué hago acá? / ¿Y
  después?), y se cierra con botón y `Esc`.
- Movimiento sólo para confirmar un cambio de estado (abrir el panel, actualizar la suma), con curvas
  de salida suaves, y respetando `prefers-reduced-motion`.

## 8. Contenido

- Castellano rioplatense con voseo, sin jerga contable ni técnica.
- Números: coeficientes con 6 decimales, porcentajes y tasas con 2, superficies con 2; formato argentino
  (coma decimal) y números tabulares en toda la interfaz.
- El texto del "?" de cada una de las siete pantallas se escribe en el mismo change que la pantalla.
  Ejemplo para el padrón: "Acá cargás las unidades del edificio y su coeficiente. 1. Revisá que estén
  todas. 2. Fijate que los coeficientes sumen 100%. 3. Si falta o sobra, corregí la unidad que
  corresponda. Con el padrón completo ya podés armar los grupos y liquidar."
- Rangos reales: 1 a 30 edificios por administración; 10 a 200 unidades por edificio; 1 a 10 grupos;
  5 a 25 categorías; decenas de versiones de configuración a lo largo de los años.

## 9. Referencias de impeccable para construir

`reference/product.md`, y las de interacción y formularios, espacio, adaptación a pantallas chicas y
auditoría de accesibilidad (`audit`).

## 10. Preguntas abiertas (las resuelve quien construye y las declara)

- La tipografía: una sola sans humanista con números tabulares, buena en castellano (candidatas: Source
  Sans 3, Fira Sans, Noto Sans; **no** Inter ni la tipografía del sistema por reflejo). Los valores
  OKLCH exactos del terracota y los neutros, dentro de lo que dice `DESIGN.md`.
- "Confirmar sin saldos previos": sección dentro del resumen o pantalla propia (la ficha la cuenta como
  pantalla; el checklist enlaza a ella en cualquier caso).
- Si "Mis edificios" con un solo edificio entra directo a ese edificio o muestra la lista igual.

## Confirmación

Respuestas de Juani en la entrevista del 19/10/2026: las siete juntas; menú lateral fijo; tabla más panel
lateral para el padrón; referencias Mercado Pago y home banking; configuración vigente más historial;
confirmación en la página con casilla; listo para usar; resumen con checklist de pasos pendientes.

OK del brief: **Juani, 19/10/2026** (en la conversación: "aprobado").
