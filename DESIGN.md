---
name: PropTech
description: Administración de consorcios sin Excel, para el administrador y sus vecinos.
colors:
  papel-tibio: "oklch(97% 0.006 75)"
  tinta: "oklch(22% 0.012 55)"
  grafito-suave: "oklch(46% 0.012 55)"
  terracota-de-edificio: "oklch(40% 0.095 35)"
  advertencia: "oklch(48% 0.09 75)"
  papel-claro: "oklch(99% 0.004 75)"
  papel-hundido: "oklch(94.5% 0.008 75)"
  linea: "oklch(89% 0.008 75)"
  terracota-oscura: "oklch(34% 0.085 35)"
  terracota-tenue: "oklch(94% 0.022 50)"
  advertencia-tenue: "oklch(95% 0.03 80)"
typography:
  titular:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.563rem"
    fontWeight: 700
    lineHeight: 1.25
  titulo:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.3
  cuerpo:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.4
rounded:
  sm: "0.25rem"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
components:
  button-primary:
    backgroundColor: "{colors.terracota-de-edificio}"
    textColor: "{colors.papel-tibio}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1rem"
---

# Design System: PropTech

## 1. Overview

**Creative North Star: "El recibo prolijo"**

PropTech se tiene que sentir como un buen recibo de expensas: todo en su lugar, cada importe con su renglón, nada de más. Es una herramienta de trabajo en tema claro, porque sus dos escenas lo piden: el administrador trabaja de día en una oficina iluminada, y el vecino mira el celular en cualquier lado, muchas veces afuera. La calma sale del orden y del espacio, no de la decoración.

El sistema es sobrio: neutros con un apenas de calidez y un único acento terracota, que remite a edificio y a barrio, y que se reserva para lo que importa. El movimiento es contenido: una sola curva de salida en todo el sistema (160ms, `ease-out`, 0ms si `prefers-reduced-motion`), y sólo para confirmar un cambio de estado (abrir un panel), nunca sobre layout. La familiaridad manda: los patrones son los que cualquier argentino ya usa en Mercado Pago o en su home banking.

Rechaza explícitamente al sistema viejo de administración (gris y apretado), a la startup genérica (degradados, tarjetas iguales, números gigantes), al Excel (una grilla donde todo pesa igual) y a la app de banco recargada (banners y mil cosas a la vez).

**Key Characteristics:**
- Tema claro, neutros tibios en OKLCH, un solo acento terracota (`oklch(40% 0.095 35)`).
- Una sola sans humanista (Source Sans 3) con números tabulares en toda la interfaz.
- Escala tipográfica de cuatro pasos con salto 1,25 (label → cuerpo → título → titular).
- Plano por defecto: una sola sombra, reservada a los paneles abiertos.
- Movimiento sólo para confirmar un cambio de estado.

## 2. Colors

Neutros tibios con un único acento terracota de uso escaso. Cinco tokens de base más seis de superficie (pulido visual del 3b, 19/10/2026), y nada más: no hay una familia de verde/rojo para "al día"/"vencido" (The Never Color Alone Rule lo prohíbe por diseño, no por omisión).

### Primary
- **Terracota de edificio** (`oklch(40% 0.095 35)`): el acento. Acción principal de cada pantalla (`.boton-principal`), foco y lo que necesita la atención del usuario. Familia ladrillo, cálida y apagada, nunca un naranja saturado. Contraste sobre Papel tibio: **8,81:1**.

### Neutral
- **Papel tibio** (`oklch(97% 0.006 75)`): fondo de toda la aplicación (`body`), un blanco con un toque cálido, nunca `#fff`.
- **Tinta** (`oklch(22% 0.012 55)`): texto principal, casi negro con el mismo tinte cálido, nunca `#000`. Contraste sobre Papel tibio: **15,90:1**.
- **Grafito suave** (`oklch(46% 0.012 55)`): texto secundario, bordes de paneles y separadores de tabla/historial. Contraste sobre Papel tibio: **6,55:1**.

### Superficies (pulido 3b)
- **Papel claro** (`oklch(99% 0.004 75)`): fondo de campos y botones secundarios, un escalón más claro que el papel para que el control se lea como control.
- **Papel hundido** (`oklch(94.5% 0.008 75)`): el segundo neutro: menú lateral, filas al pasar el mouse, esqueletos de carga, estados "ok" y "listo".
- **Línea** (`oklch(89% 0.008 75)`): separador de renglones (listas, tabla, historial). Grafito suave queda para bordes de controles (inputs, botones), que sí necesitan 3:1.
- **Terracota oscura** (`oklch(34% 0.085 35)`): `:hover` del botón principal.
- **Terracota tenue** (`oklch(94% 0.022 50)`) y **Advertencia tenue** (`oklch(95% 0.03 80)`): fondos de lo que pide atención (sección actual del menú, paso que falta, "fuera de tolerancia", resumen de errores) y del aviso "no se puede deshacer". Siempre con su texto en Terracota o Advertencia encima, verificados a 4,5:1 en `tokens.test.ts`.

### Estado
- **Advertencia** (`oklch(48% 0.09 75)`): el único color de estado que existe, para "coeficientes entre 0,9999 y 1,0001" (`EstadoDeCoeficientes`). Contraste sobre Papel tibio: **6,09:1**. "Ok" no tiene color propio; "fuera de tolerancia" y un paso que "falta" usan Terracota (el acento ya significa "lo que necesita tu atención"), nunca un rojo. Los tres llevan además su texto y una marca de forma (✓ ! ✕ ○, puesta por CSS con texto alternativo vacío): The Never Color Alone Rule.

### Named Rules
**The One Voice Rule.** El terracota cubre menos del 10% de cualquier pantalla. Si todo es importante, nada lo es.

**The Never Color Alone Rule.** Un estado de plata (al día, debe, vencido, pagado, coeficientes ok/advertencia/fuera de tolerancia) nunca se comunica sólo con color: siempre lleva texto y, si hace falta, un ícono. Vecinos mayores y daltonismo incluidos. Por eso el sistema tiene un solo color de estado (Advertencia), no cuatro.

**The Verified-Not-Eyeballed Rule.** Cada par texto/fondo que la interfaz usa de verdad se verifica por cálculo real (conversión OKLCH → sRGB, `web/src/lib/color/oklch.ts`) en `web/src/app/tokens.test.ts`, nunca a ojo. Los cuatro números de contraste de esta sección salen de esa corrida, no de una estimación.

## 3. Typography

**Body Font:** Source Sans 3 (con `ui-sans-serif, system-ui, sans-serif` de respaldo): una sola sans humanista, cálida y muy legible, con figuras tabulares en sus pesos normales (sin necesitar la variable, más liviana para la superficie del vecino con mala señal). Se sirve desde la propia web vía `@fontsource/source-sans-3`: nunca se pide a un tercero en cada visita.

**Character:** una familia única que trabaja en todos los tamaños, con números tabulares para que los importes queden alineados en columna. Elegida sobre Fira Sans y Noto Sans por esas figuras tabulares nativas y por su legibilidad en cuerpos chicos (Adobe la diseñó para interfaces, no para títulos). Nunca Inter ni la del sistema por reflejo.

### Hierarchy
- **Titular** (700, 1,563rem / 25px, line-height 1,25): el único `h1` de cada pantalla (`EncabezadoDePantalla`), el título que nombra dónde está el administrador.
- **Título** (700, 1,25rem / 20px, line-height 1,3): `h2`, subdivisiones dentro de una pantalla (p. ej. "Historial" en Intereses y vencimiento).
- **Cuerpo** (400, 1rem / 16px, line-height 1,5): el tamaño de `body`, todo el texto corrido, los formularios y las filas de las listas.
- **Label** (400, 0,8rem / 12,8px, line-height 1,4): el paso más chico de la escala, reservado para texto de apoyo (leyendas, ayudas de campo). Ningún componente lo usa todavía: es el próximo paso de la escala cuando haga falta, no un token huérfano inventado para esta ficha.

Salto de 1,25 entre cada paso consecutivo (0,8 → 1 → 1,25 → 1,563), igual en toda la interfaz: el administrador y el vecino comparten la misma escala, sólo cambia la densidad del layout, nunca la tipografía (D-ficha, Design Principle 4).

### Named Rules
**The Tabular Money Rule.** Todo importe, coeficiente, porcentaje o superficie usa números tabulares (`.numero-tabular`, `font-variant-numeric: tabular-nums`), alineados a la derecha, en formato argentino (coma decimal, punto de miles). Nunca se redondea en pantalla lo que no está redondeado en la base, y nunca pasa por `Number`, `parseFloat` ni `Intl.NumberFormat` (texto decimal ASCII de punta a punta, `web/src/lib/formato.ts`).

## 4. Elevation

Plano por defecto. No hay capas de sombra ambiental ni tarjetas elevadas: la profundidad se marca con un borde fino (`1px solid` Grafito suave) y, en un solo caso, una sombra que confirma un cambio de estado.

### Shadow Vocabulary
- **Panel abierto** (`box-shadow: 0 2px 8px oklch(22% 0.012 55 / 15%)`): la única sombra del sistema. La llevan el panel lateral y el panel de ayuda, y sólo existen en el DOM mientras están abiertos (`PanelLateral`/`Ayuda` devuelven `null` cerrados): la sombra nunca convive con el estado "cerrado", así que no hace falta una transición de sombra.

### Named Rules
**The Flat-By-Default Rule.** Ninguna lista, fila o tabla lleva sombra ni tarjeta: una fila es un renglón con un borde inferior fino (`.padron-de-unidades td`, `.historial-de-configuracion__fila`), nunca una tarjeta elevada. La sombra se reserva para lo que de verdad flota por encima del resto (un panel abierto), nunca para decorar una lista.

## 5. Components

### Buttons
- **Shape:** sin bordes redondeados pronunciados, apenas un quiebre (`border-radius: 0.25rem` / 4px).
- **Primary (`.boton-principal`):** fondo Terracota de edificio, texto Papel tibio, sin borde, `padding: 0.5rem 1rem`, `font-weight: 600`. Una sola por pantalla (The One Voice Rule): la acción principal de `EncabezadoDePantalla`, "Guardar" de cada panel, "Confirmar".
- **Secundario (base de `button`, con `:where()` para especificidad cero):** fondo Papel claro, borde `1px` Grafito suave, texto Tinta, `font-weight: 600`. "Cerrar", "Reintentar", "Secciones". En listas largas (Categorías) baja un escalón más: borde Línea y texto Grafito, para que nueve "Desactivar" no compitan con la acción principal.
- **Enlace de fila (`.boton-enlace`):** un `<button>` que abre el panel lateral pero se lee como texto de la fila (identificador del padrón, nombre de un grupo o categoría): sin caja, subrayado al pasar.
- **Ícono (`.boton-icono`):** 2rem cuadrado, "subir"/"bajar" con `aria-label`; "subir" siempre en la primera casilla y "bajar" en la segunda.
- **Estado vacío:** repite la acción principal pero en estilo secundario (The One Voice Rule: el terracota ya está en el encabezado).

### Panels (señal del sistema)
- **Panel lateral (`.panel-lateral`):** hoja `position: fixed` pegada al borde derecho, `min(28rem, 100vw)` de ancho y scroll propio; fondo Papel tibio, borde izquierdo `1px` Grafito suave, la única sombra del sistema; entra con `opacity` vía `@starting-style`. "Cerrar" arriba a la derecha. `<div role="dialog" aria-modal="false">`, NUNCA `<dialog>` con `showModal()` (eso lo volvería modal de verdad y rompería el `Esc` propio). Atrapa el foco mientras está abierto, se cierra con un botón visible o `Esc`, devuelve el foco a quien lo abrió. Es donde viven TODOS los formularios de alta/edición del sistema: nunca una página aparte, nunca un modal bloqueante.
- **Ayuda "?" (`.ayuda__panel`):** mismo tratamiento visual que el panel lateral (comparten la regla CSS), por encima de él (`z-index`) si se abre adentro. El botón "?" es un círculo de 1,75rem con borde Grafito suave. The Always-Help Rule: toda pantalla, del administrador y del vecino, lleva un botón "?" junto a su título, con las tres partes fijas (¿Para qué sirve esta pantalla? / ¿Qué hago acá? / ¿Y después?). Se abre al tocar o hacer clic (nunca sólo al pasar el mouse), tiene nombre accesible y se cierra con botón visible o `Esc`.

### Navigation
- **Menú del edificio (`MenuDelEdificio`):** `<nav aria-label="Menú del edificio">` con el enlace "Mis edificios", el nombre del edificio y, adentro, un segundo `<nav aria-label="Secciones del edificio">` con la lista de secciones. La sección actual se marca con `aria-current="page"` Y con una marca de forma (`▸`), nunca sólo con color. Por debajo de 768px se pliega a un botón "Secciones" (operable con teclado, cierra con `Esc`); desde 768px el menú queda fijo a la izquierda (`flex: 0 0 15rem`, `position: sticky`, fondo Papel hundido) con las secciones apiladas en columna, y el contenido a la derecha (máx. 68rem). La sección actual lleva además fondo Terracota tenue. Un nombre de edificio largo se corta a tres renglones (`line-clamp`) con el nombre completo en `title`.

### Lists
- **Listas de fila (`.lista-de-edificios`, `.grupos-de-reparto`, `.categorias-de-gasto`, `.resumen__checklist`):** mismo patrón de lista de movimientos de home banking: `<ul>`/`<ol>` sin viñetas, renglones separados por una Línea fina, nunca una tarjeta. En Mis edificios cada renglón es una grilla (nombre y localidad, unidades a la derecha, estados, "›") y toda la fila se toca, pero el enlace se llama sólo como el edificio (`::after` estirado). El checklist del resumen marca cada paso con `data-estado` (hecho: Grafito con ✓; falta: pastilla Terracota tenue con ○) y su texto.
- **Renglones etiqueta/valor (`.renglones`, un `<dl>`):** la configuración vigente de Intereses y vencimiento como un recibo: etiqueta en Grafito a la izquierda, valor en 600 a la derecha.
- **Historial como línea de tiempo (`.historial-de-configuracion`):** cada versión es un renglón con un borde inferior fino, sin tarjeta; "rige desde", autor y los campos que cambiaron respecto de la versión anterior, de más nueva a más vieja.

### Data Table
- **Padrón de unidades (`.padron-de-unidades`):** `border-collapse: collapse`, textos a la izquierda y números a la derecha (`.padron-de-unidades .numero-tabular`), encabezados en Label 600 Grafito con borde inferior Grafito, celdas con borde inferior Línea, fila resaltada al pasar, `white-space: nowrap`. El contenedor (`.padron-de-unidades__scroll`) scrollea horizontalmente PARA SÍ MISMO (`overflow-x: auto`): una tabla de 5 columnas y hasta 200 filas nunca empuja el ancho de la página entera a 320px.

### Inputs / Fields
- **`.formulario` / `.campo`** (pulido 3b): etiqueta arriba en 600, control de 2,5rem de alto a todo el ancho, fondo Papel claro, borde Grafito suave; con error, borde Terracota y el mensaje debajo en Terracota con "!". La casilla va antes de su texto, en un renglón Papel hundido que es todo zona para tocar. El resumen de errores es un bloque Terracota tenue con borde Terracota.
- **Foco:** `:focus-visible` global, `2px solid` Terracota con `outline-offset: 2px`.

## 6. Do's and Don'ts

### Do:
- **Do** poner en cada pantalla su "?" de ayuda, con las tres partes escritas (The Always-Help Rule).
- **Do** dejar en cada pantalla una sola acción principal en terracota (`oklch(40% 0.095 35)`, `.boton-principal`).
- **Do** mostrar cada importe en números tabulares, alineado a la derecha y con formato argentino.
- **Do** acompañar todo estado de plata o de coeficientes con texto, nunca sólo con color (hoy sólo existe un color de estado: Advertencia).
- **Do** cumplir WCAG 2.2 AA: los cinco tokens de color verificados a 4,5:1 o más contra Papel tibio, foco siempre visible, panel lateral con trampa de foco propia.
- **Do** respetar `prefers-reduced-motion` (`--duracion-transicion` pasa a 0ms) y animar sólo `opacity` en los paneles, nunca una propiedad de layout.
- **Do** usar el panel lateral para todo alta/edición; nunca una página aparte para un formulario que cabe en un panel.

### Don't:
- **Don't** parecer un sistema viejo de administración: pantallas grises, tablas apretadas, estética de programa de escritorio de los 2000.
- **Don't** parecer una startup genérica: degradados, grillas de tarjetas idénticas, números gigantes de marketing.
- **Don't** convertir una pantalla en Excel: una grilla infinita donde todo pesa lo mismo y nada guía la mirada.
- **Don't** recargar como una app de banco: banners, promociones y demasiadas cosas compitiendo a la vez.
- **Don't** usar `#000`, `#fff`, texto con degradado, bordes laterales de color como acento, ni modales (`<dialog>` con `showModal()`) como primera opción.
- **Don't** usar un naranja saturado en lugar del terracota apagado, ni inventar una familia de colores de estado (verde/rojo) que el sistema deliberadamente no tiene.
- **Don't** envolver una fila o una lista en una tarjeta con sombra: Plano por defecto, la única sombra es la del panel abierto.
