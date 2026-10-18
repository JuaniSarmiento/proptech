<!-- SEED: re-run /impeccable document once there's code to capture the actual tokens and components. -->
---
name: PropTech
description: Administración de consorcios sin Excel, para el administrador y sus vecinos.
---

# Design System: PropTech

## 1. Overview

**Creative North Star: "El recibo prolijo"**

PropTech se tiene que sentir como un buen recibo de expensas: todo en su lugar, cada importe con su renglón, nada de más. Es una herramienta de trabajo en tema claro, porque sus dos escenas lo piden: el administrador trabaja de día en una oficina iluminada, y el vecino mira el celular en cualquier lado, muchas veces afuera. La calma sale del orden y del espacio, no de la decoración.

El sistema es sobrio: neutros con un apenas de calidez y un único acento terracota, que remite a edificio y a barrio, y que se reserva para lo que importa. El movimiento es contenido: sólo cambios de estado, porque nada tiene que distraer de los números ni pesar con mala señal. La familiaridad manda: los patrones son los que cualquier argentino ya usa en Mercado Pago o en su home banking.

Rechaza explícitamente al sistema viejo de administración (gris y apretado), a la startup genérica (degradados, tarjetas iguales, números gigantes), al Excel (una grilla donde todo pesa igual) y a la app de banco recargada (banners y mil cosas a la vez).

**Key Characteristics:**
- Tema claro, neutros tibios, un solo acento terracota.
- Una sans humanista con números tabulares en toda la interfaz.
- Dos densidades del mismo lenguaje: compacta para el administrador, amplia para el vecino.
- Movimiento sólo para confirmar un cambio de estado.

## 2. Colors

Neutros tibios con un único acento terracota de uso escaso; los valores exactos se resuelven al implementar.

### Primary
- **Terracota de edificio** ([to be resolved during implementation]): el acento. Acción principal de cada pantalla, foco y lo que necesita la atención del usuario. Familia ladrillo, cálida y apagada, nunca un naranja saturado.

### Neutral
- **Papel tibio** ([to be resolved during implementation]): fondo de la aplicación, un blanco con un toque cálido, nunca `#fff`.
- **Tinta** ([to be resolved during implementation]): texto principal, casi negro con el mismo tinte cálido, nunca `#000`.
- **Grafito suave** ([to be resolved during implementation]): texto secundario, bordes y separadores.

### Named Rules
**The One Voice Rule.** El terracota cubre menos del 10% de cualquier pantalla. Si todo es importante, nada lo es.

**The Never Color Alone Rule.** Un estado de plata (al día, debe, vencido, pagado) nunca se comunica sólo con color: siempre lleva texto y, si hace falta, un ícono. Vecinos mayores y daltonismo incluidos.

## 3. Typography

**Body Font:** [font pairing to be chosen at implementation]: una sola sans humanista, cálida y muy legible.

**Character:** una familia única que trabaja en todos los tamaños, con números tabulares para que los importes queden alineados en columna.

### Hierarchy
- **Headline, Title, Body, Label:** [scale to be resolved at implementation], con un salto de al menos 1.25 entre niveles. La superficie del vecino usa un cuerpo de texto más grande que la del administrador.

### Named Rules
**The Tabular Money Rule.** Todo importe usa números tabulares, alineados a la derecha en columnas, con el formato argentino ($ 12.500,00). Nunca se redondea en pantalla lo que no está redondeado en la base.

## 4. Elevation

Plano por defecto. La profundidad se marca con capas de tono y bordes finos, no con sombras; una sombra aparece sólo como respuesta a un estado, como un menú abierto.

## 5. Components

### Ayuda de pantalla ("?")

**The Always-Help Rule.** Toda pantalla, del administrador y del vecino, lleva un botón "?" de ayuda,
siempre en el mismo lugar (junto al título de la pantalla). Es un pedido de Alberto (17/10/2026) y es
obligatorio: **una pantalla sin su "?" no está terminada.**

Al tocarlo se abre una explicación didáctica de esa pantalla, en castellano simple y sin jerga
contable, con tres partes:

1. **¿Para qué sirve esta pantalla?** Qué le resuelve a quien la usa.
2. **¿Qué hago acá?** Los pasos, numerados y cortos.
3. **¿Y después?** Qué pasa con lo que cargó o a dónde sigue.

Ejemplo, configuración del edificio: "Acá cargás los datos del edificio: sus unidades, el coeficiente de
cada una y cómo se cobran las expensas. 1. Revisá que estén todas las unidades. 2. Fijate que los
coeficientes sumen 100%. 3. Elegí el día de vencimiento. Con esto armado ya podés liquidar las
expensas del mes."

Cómo se comporta:
- Se abre **al tocar o al hacer clic**, nunca sólo al pasar el mouse (en el celular no hay mouse).
- Es un panel con letra del tamaño del cuerpo de texto, no un globito chico; se cierra con un botón
  visible y con `Esc`.
- Es operable con teclado, tiene nombre accesible ("Ayuda: para qué sirve esta pantalla") y foco
  visible (WCAG 2.2 AA).
- El texto vive junto a la pantalla, en el mismo cambio que la construye: si la pantalla cambia, su
  ayuda cambia en el mismo commit.

## 6. Do's and Don'ts

### Do:
- **Do** poner en cada pantalla su "?" de ayuda, con las tres partes escritas (The Always-Help Rule).
- **Do** dejar en cada pantalla una sola acción principal en terracota.
- **Do** mostrar cada importe en números tabulares, alineado a la derecha y con formato argentino.
- **Do** acompañar todo estado de plata con texto, nunca sólo con color.
- **Do** cumplir WCAG 2.2 AA, con letra grande y objetivos táctiles grandes en la superficie del vecino.
- **Do** respetar `prefers-reduced-motion`, y animar sólo cambios de estado con curvas de salida suaves.

### Don't:
- **Don't** parecer un sistema viejo de administración: pantallas grises, tablas apretadas, estética de programa de escritorio de los 2000.
- **Don't** parecer una startup genérica: degradados, grillas de tarjetas idénticas, números gigantes de marketing.
- **Don't** convertir una pantalla en Excel: una grilla infinita donde todo pesa lo mismo y nada guía la mirada.
- **Don't** recargar como una app de banco: banners, promociones y demasiadas cosas compitiendo a la vez.
- **Don't** usar `#000`, `#fff`, texto con degradado, bordes laterales de color como acento, ni modales como primera opción.
- **Don't** usar un naranja saturado en lugar del terracota apagado.
