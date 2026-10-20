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
  control: "0.375rem"
  panel: "0.75rem"
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
- **Panel abierto** (`box-shadow: 0 2px 8px oklch(22% 0.012 55 / 15%)`): la única sombra del sistema. La lleva sólo el panel lateral flotante, que existe en el DOM únicamente mientras está abierto (`PanelLateral` devuelve `null` cerrado). La ayuda acoplada, los paneles de contenido y el panel lateral en variante `ancho` son planos: no flotan, empujan o están en el flujo.

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
- **Ícono con texto:** "Subir"/"Bajar" de Categorías, "Cerrar" y "Ayuda" llevan su ícono de línea y su palabra al lado; ningún botón es sólo un ícono.

### Panels (señal del sistema)
- **Panel de contenido (`Panel`, `.panel`; enmienda del 20/10/2026):** `<section>` con su `h2` como nombre accesible y una línea gris que dice para qué sirve (`.panel__descripcion`). Fondo Papel claro, borde `1px` Línea, esquinas de `0.75rem`, plano (sin sombra). Cada pantalla arma un panel principal y una columna de apoyo (`.disposicion`, `.disposicion__lateral`) que van lado a lado cuando el CONTENIDO mide 60rem o más (container query sobre `<main>`, no media query: con la ayuda acoplada la columna de apoyo baja sola); apilada, la columna de apoyo reparte sus paneles en el ancho. Intereses y vencimiento usa `.disposicion--mitades` (vigente e historial lado a lado). Nunca una grilla de paneles iguales: cada panel tiene contenido distinto.
- **Panel lateral (`.panel-lateral`):** hoja `position: fixed` pegada al borde derecho, `min(28rem, 100vw)` de ancho y scroll propio; fondo Papel claro, borde izquierdo `1px` Grafito suave, la única sombra del sistema; entra con `opacity` vía `@starting-style`. "Cerrar" (con ícono X y texto) arriba a la derecha. `<div role="dialog" aria-modal="false">`, NUNCA `<dialog>` con `showModal()`. Atrapa el foco mientras está abierto, incluyendo los controles de la ayuda acoplada de esa pantalla en el ciclo de Tab (el resto queda afuera), se cierra con un botón visible o `Esc`, devuelve el foco a quien lo abrió. Es donde viven los formularios de alta/edición: nunca una página aparte, nunca un modal bloqueante. **Variante `ancho`** (`.panel-lateral--ancho`): el mismo componente en el flujo de la pantalla, a todo el ancho del contenido, plano, con los campos en columnas (`auto-fill, minmax(14rem, 1fr)`); para formularios largos (Cambiar configuración), que en 28rem quedaban en una columna angosta.
- **Ayuda (`Ayuda`, `.ayuda__panel`; enmienda del 20/10/2026):** botón con ícono y la palabra "Ayuda" (pastilla con borde Línea; abierta, Terracota tenue con `aria-expanded="true"`). Desde 1024px el panel se ACOPLA a la derecha debajo de la barra superior (`--ancho-ayuda: 22rem`) y EMPUJA el contenido (`.armazon:has(.ayuda__panel) .armazon__cuerpo { padding-right }`), no lo tapa; un panel lateral abierto después se corre a su izquierda. Por debajo de 1024px cae en el flujo, a todo el ancho, debajo del renglón del título. Queda abierta mientras se trabaja; abrirla no mueve el foco (el siguiente `Tab` entra al panel); se cierra con el mismo botón, con "Cerrar" o con `Esc`, y el foco vuelve al botón; si hay un panel lateral abierto, vuelve adentro del formulario. Partes: ¿Para qué sirve esta pantalla? / ¿Qué hago acá? (pasos numerados en círculos) / Un ejemplo (bloque Papel hundido) / ¿Y después?. The Always-Help Rule sigue igual.

### Navigation
- **Barra superior (`Armazon`, `.barra-superior`; enmienda del 20/10/2026):** `<header>` fijo arriba (`--alto-barra: 3.5rem`), fondo Papel claro: la marca (logo Terracota de 2rem + "PropTech"), la miga "Mis edificios › <edificio>" (`<nav aria-label="Estás en">`, el edificio con `aria-current` y cortado a un renglón con `title`) y, a la derecha, el usuario. La API todavía no expone quién inició sesión: se muestra "Administración", nunca un nombre inventado. A menos de 640px la marca queda en el logo y la miga muestra sólo el edificio. Todas las pantallas del administrador, Mis edificios incluida, usan este armazón.
- **Menú del edificio (`MenuDelEdificio`):** un `<nav aria-label="Secciones del edificio">` con dos grupos titulados ("El edificio": Resumen, Unidades, Grupos; "Configuración": Categorías, Intereses y vencimiento), cada grupo un `<ul>` nombrado por su título. Cada sección lleva un ícono de línea de `lucide-react` (18px, trazo 1,75, `aria-hidden`) con su texto al lado, nunca sólo el ícono. La sección actual: `aria-current="page"`, fondo Terracota tenue, texto e ícono Terracota y la marca "›" (nunca sólo color). Por debajo de 768px se pliega a "Secciones" (teclado y `Esc`); desde 768px queda fijo a la izquierda (`--ancho-menu: 16rem`, sticky debajo de la barra, fondo Papel claro) y el contenido ocupa TODO el resto del ancho (sin máximo).

### Lists
- **Filas con ícono (`FilaConIcono`, `.lista-de-filas`; enmienda del 20/10/2026):** como "Últimas actividades" de Mercado Pago: ícono de línea en un círculo de 2,5rem (borde Línea; `data-tono="atencion"` Terracota tenue, `"listo"` Papel hundido), título en 600, una línea gris que explica y, a la derecha, el estado, el número o las acciones (que bajan debajo del texto cuando el panel mide menos de 20rem, salvo en las listas compactas de apoyo). Renglones separados por una Línea fina, nunca tarjetas. `.lista-de-filas--tocable`: toda la fila se toca (el enlace o botón del título se estira con `::after`) y se resalta en Papel hundido, pero el nombre accesible es sólo el título. Las usan el checklist del resumen, grupos, categorías, historial y los paneles de apoyo.
- **Mis edificios (`.lista-de-edificios`):** a todo el ancho, una fila por edificio con ícono, nombre y localidad, y cada dato con su rótulo: Unidades, Coeficientes, Saldos previos y Puesta a punto (mini barra "N de 6 pasos"); "›" al final y toda la fila se toca.
- **Barra de progreso (`BarraDeProgreso`):** "N de 6 pasos" en texto y `role="progressbar"` con sus valores; pista Papel hundido de 0,5rem y relleno Terracota con `transform: scaleX` (nunca `width`). Sólo CUENTA pasos que la API ya marcó.
- **Estado vacío (`Estados tipo="vacio"`):** un dibujo simple en SVG inline (edificio de línea con una ventana punteada en Terracota), el mensaje en Título, el próximo paso en gris y la acción en estilo secundario al lado.
- **Renglones etiqueta/valor (`.renglones`, un `<dl>`):** la configuración vigente de Intereses y vencimiento como un recibo: etiqueta en Grafito a la izquierda, valor en 600 a la derecha.
- **Historial como línea de tiempo (`.historial-de-configuracion`):** cada versión es un renglón con un borde inferior fino, sin tarjeta; "rige desde", autor y los campos que cambiaron respecto de la versión anterior, de más nueva a más vieja.

### Data Table
- **Padrón de unidades (`.padron-de-unidades`):** `border-collapse: collapse`, textos a la izquierda y números a la derecha (`.padron-de-unidades .numero-tabular`), encabezados en Label 600 Grafito con borde inferior Grafito, celdas con borde inferior Línea, fila resaltada al pasar, `white-space: nowrap`. El contenedor (`.padron-de-unidades__scroll`) scrollea horizontalmente PARA SÍ MISMO (`overflow-x: auto`): una tabla de 5 columnas y hasta 200 filas nunca empuja el ancho de la página entera a 320px.

### Inputs / Fields
- **`.formulario` / `.campo`** (pulido 3b): etiqueta arriba en 600, control de 2,5rem de alto a todo el ancho, fondo Papel claro, borde Grafito suave; con error, borde Terracota y el mensaje debajo en Terracota con "!". La casilla va antes de su texto, en un renglón Papel hundido que es todo zona para tocar. El resumen de errores es un bloque Terracota tenue con borde Terracota.
- **Campos decimales:** se editan como texto con coma decimal y sin separador de miles, conservando todos los decimales; teclado decimal en móvil. Las acciones convierten la coma a punto para la API, sin cálculo ni redondeo. También aceptan punto al escribir.
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
