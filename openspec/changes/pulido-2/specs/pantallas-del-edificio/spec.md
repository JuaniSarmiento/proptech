## MODIFIED Requirements

### Requirement: Pantalla chica y accesibilidad

Cada pantalla, en cada uno de sus estados, SHALL verse a 320 px de ancho sin scroll horizontal y
MUST NOT tener violaciones de axe (WCAG 2.2 AA), incluido el contraste medido en un navegador real. Los
estados que se miden son, al menos, el feliz, el vacío, el de error de la API y, en las pantallas con
formulario, el formulario con un error de campo: las siete pantallas, no sólo las que hoy lo hacen.

#### Scenario: 320 px

- **WHEN** se abre cualquiera de las siete pantallas a 320 px con un identificador de 40 caracteres y
  un nombre de edificio de 200
- **THEN** el ancho del documento no supera el de la ventana

#### Scenario: axe en cada estado

- **WHEN** se corre axe sobre cada pantalla en cada estado
- **THEN** no hay violaciones

#### Scenario: axe cubre más de un estado en categorías, grupos, configuración y saldos previos

- **WHEN** se corre axe sobre las pantallas de categorías, grupos, intereses y vencimiento y saldos
  previos en su estado feliz y en, al menos, su estado vacío y su estado con un error de campo
- **THEN** ninguno de esos estados tiene violaciones

## ADDED Requirements

### Requirement: La ayuda del resumen describe los siete pasos

La ayuda "?" del resumen del edificio SHALL hablar de los siete pasos de la puesta a punto, nunca de
otra cantidad: su ejemplo y su cierre MUST decir "de 7 pasos" y coincidir con los siete pasos que
muestra la pantalla.

#### Scenario: Ejemplo de la ayuda

- **WHEN** el titular abre la ayuda del resumen de un edificio
- **THEN** el ejemplo habla de un edificio que arranca en "0 de 7 pasos" y de una barra que avanza a
  "2 de 7", y ningún texto de la ayuda dice "de 6"

### Requirement: La raíz del sitio no es un marcador de posición

La ruta `/` SHALL llevar a la persona a un lugar útil en lugar de mostrar un texto de relleno: a quien
tiene sesión, a la lista de sus edificios; a quien no, a la pantalla de ingreso.

#### Scenario: Con sesión

- **WHEN** una persona con sesión abre `/`
- **THEN** llega a `/edificios`

#### Scenario: Sin sesión

- **WHEN** una persona sin sesión abre `/`
- **THEN** llega a `/ingresar`

### Requirement: El día de vencimiento fuera de rango lo frena la aplicación

El día de vencimiento (y el del segundo vencimiento) MUST aceptar de 1 a 28. Un día fuera de ese
rango, como 29, 30 o 31, MUST rechazarse con un error que nombra el campo, aunque el navegador no haya
frenado el envío antes por su validación nativa.

#### Scenario: Día 31

- **WHEN** el titular envía la configuración con el día de vencimiento 31 sin que el navegador frene
  el formulario
- **THEN** el servidor responde 422 y la pantalla marca sólo el campo "Día de vencimiento" con su mensaje
