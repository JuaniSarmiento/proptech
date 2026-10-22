# pantallas-del-edificio Specification

## Purpose
Define las siete pantallas con las que el administrador configura un edificio desde el navegador
(HU-A1, HU-T1), sobre la API del 3a: qué muestra cada una, cómo se opera con teclado y en pantalla
chica, cómo se explica sola y la regla de que la web muestra lo que calcula la API.

## Requirements

### Requirement: La web muestra lo que calcula la API

Toda suma de coeficientes, diferencia, estado de R01, paso de puesta a punto y "listo para liquidar"
SHALL mostrarse tal como lo devuelve la API, sin recalcularlo en la web. Coeficientes, tasas,
porcentajes y superficies MUST tratarse como texto decimal de punta a punta: la web MUST NOT
convertirlos a número de punto flotante en ningún camino.

#### Scenario: Datos que no cuadran con el informe

- **WHEN** las unidades que manda la API suman 0,9 y el informe de la API dice `ok`
- **THEN** la pantalla muestra el estado `ok` con la suma del informe

#### Scenario: Un valor que el punto flotante pierde

- **WHEN** la API manda un coeficiente `"0.100000"` y una suma `"0.999950"`
- **THEN** la pantalla muestra "0,100000" y "99,9950 %", sin redondear

### Requirement: Números tabulares y formato argentino

Coeficientes SHALL mostrarse con 6 decimales; tasas, porcentajes y superficies con 2; la suma y la
diferencia de coeficientes en porcentaje con 4 (el corrimiento exacto de la coma de un valor de 6
decimales). Todos MUST usar coma decimal, punto de miles, números tabulares y, en tablas, alineación a
la derecha.

#### Scenario: Superficie con miles

- **WHEN** la API manda una superficie `"1234.50"`
- **THEN** la pantalla muestra "1.234,50" alineado a la derecha con números tabulares

### Requirement: Navegación común

Dentro de un edificio SHALL haber un menú lateral fijo con Resumen, Unidades, Grupos, Categorías e
Intereses y vencimiento, encabezado por el nombre del edificio y un enlace a "Mis edificios". La
sección actual MUST marcarse con texto o forma además de color, y por programa (`aria-current`). Por
debajo de 768 px de ancho el menú MUST plegarse a un botón "Secciones" que lo despliega con teclado. La
barra superior MUST mostrar el nombre de la persona que entró y la administración en uso, con "Salir"
y, si la persona tiene más de una administración, "Cambiar de administración"; nunca un nombre
inventado ni deducido.

#### Scenario: Sección actual

- **WHEN** el administrador está en el padrón de unidades
- **THEN** "Unidades" está marcada como la página actual por programa y no sólo con color

#### Scenario: Menú plegado

- **WHEN** el ancho es de 320 px y el administrador activa "Secciones" con el teclado
- **THEN** el menú se despliega, se recorre con `Tab` y se cierra con `Esc`

#### Scenario: Quién entró

- **WHEN** una persona entra a una administración
- **THEN** la barra superior muestra su nombre, el de la administración y "Salir", operables con
  teclado, y no muestra el texto fijo "Administración"

#### Scenario: Salir

- **WHEN** la persona activa "Salir"
- **THEN** su sesión de Clerk termina, la cookie de la administración elegida se borra y vuelve a la
  pantalla de ingreso

### Requirement: Cada pantalla tiene su ayuda

Cada una de las siete pantallas SHALL tener un botón "?" junto a su título, con nombre accesible, que
se abre al tocarlo, al hacer clic o con el teclado (nunca sólo al pasar el mouse) y muestra, con letra
del tamaño del cuerpo, tres partes con texto escrito para esa pantalla: "¿Para qué sirve esta
pantalla?", "¿Qué hago acá?" (pasos numerados) y "¿Y después?". MUST cerrarse con un botón visible y
con `Esc`, devolver el foco al "?" y no perder lo cargado en la pantalla (D-102, HU-T1).

#### Scenario: Abrir y cerrar la ayuda con teclado

- **WHEN** el administrador llega al "?" con `Tab`, lo activa con `Enter` y después aprieta `Esc`
- **THEN** ve las tres partes, la ayuda se cierra y el foco vuelve al "?"

#### Scenario: Ayuda con un formulario a medio cargar

- **WHEN** el administrador abre la ayuda con el panel de una unidad a medio cargar y la cierra
- **THEN** lo cargado sigue en el panel

### Requirement: Estados de cada pantalla

Cada pantalla SHALL tener sus estados de carga (un esqueleto con la forma del contenido, sin girador a
pantalla completa), vacío (con el siguiente paso), error de carga (qué pasó en una línea y
"Reintentar", nunca el texto técnico), sin permiso (403: qué no puede hacer y quién sí: el super
admin de la empresa para los permisos de estas pantallas; propietario o inquilino para `informar_pago`), no existe (404: "No encontramos este edificio" con enlace a "Mis edificios") y
sin sesión (401: lleva a la pantalla de ingreso y, después de entrar, vuelve a la misma dirección si es
una dirección propia del sitio). Cada estado MUST poder alcanzarse a pedido, sin tocar el código. Ningún
texto de la web MUST nombrar al "titular" ni al "colaborador".

#### Scenario: Error de la API con texto técnico

- **WHEN** la API responde 500 con un texto técnico en el cuerpo
- **THEN** la pantalla dice qué pasó en castellano simple, ofrece "Reintentar" y no muestra el texto
  técnico

#### Scenario: Edificio de otra administración

- **WHEN** el administrador abre la dirección de un edificio que la API responde con 404
- **THEN** ve "No encontramos este edificio" con un enlace a "Mis edificios"

#### Scenario: Sin permiso

- **WHEN** un auxiliar o un administrador por edificio intenta una acción que la API responde con 403
- **THEN** ve qué no puede hacer y que lo puede hacer el super admin de la empresa, sin perder lo
  cargado

#### Scenario: Crear un edificio sin permiso

- **WHEN** un administrador intenta crear un edificio y la API responde 403
- **THEN** el formulario dice que no puede crear un edificio y que lo puede hacer el super admin de la
  empresa

#### Scenario: Sin permiso para informar un pago

- **WHEN** una acción responde 403 con `permiso_faltante=informar_pago`
- **THEN** el estado dice que puede hacerlo la persona propietaria o inquilina de la unidad
- **AND** no muestra que lo puede hacer el super admin

#### Scenario: Sesión vencida

- **WHEN** la API responde 401 al abrir el padrón de un edificio
- **THEN** la web lleva a la pantalla de ingreso y, después de entrar, vuelve al padrón

#### Scenario: Regreso a un sitio ajeno

- **WHEN** la dirección de regreso del ingreso apunta a otro dominio o a una dirección que empieza con
  `//`
- **THEN** después de entrar la web abre "Mis edificios" y no sale del sitio

### Requirement: Errores de formulario asociados al campo

Cada error de un formulario SHALL mostrarse junto a su campo y asociado por programa (`aria-invalid` y
`aria-describedby`), con un resumen arriba del formulario que enlaza a cada campo con error. Un 422 de
la API MUST llegar al campo que nombra su `loc`, y un 409 al campo que nombra `campo`, en castellano
simple y sin repetir el valor rechazado. Un error de la API para un campo que el formulario no tiene
MUST mostrarse en el resumen.

#### Scenario: Identificador repetido

- **WHEN** el administrador guarda una unidad y la API responde 409 con `campo: identificador`
- **THEN** el campo identificador queda marcado como inválido, con un mensaje asociado por programa, y
  el resumen enlaza a ese campo

#### Scenario: Error de un campo desconocido

- **WHEN** la API responde 422 con un `loc` que el formulario no tiene
- **THEN** el error aparece en el resumen y ningún campo queda marcado de más

### Requirement: Teclado, foco y panel lateral

Cada pantalla SHALL operarse entera con teclado, en el orden de lectura, con foco visible en todo
control y sin quedar tapado. Los formularios de alta y edición MUST abrirse en un panel lateral (no un
modal ni una página aparte) que atrapa el foco mientras está abierto, se cierra con `Esc` y con un
botón visible, y devuelve el foco a la fila o el botón que lo abrió. Todo objetivo táctil MUST medir al
menos 24 x 24 px y el movimiento MUST respetar `prefers-reduced-motion`.

#### Scenario: Cerrar el panel

- **WHEN** el administrador abre el panel desde una fila y aprieta `Esc`
- **THEN** el panel se cierra y el foco vuelve a esa fila

#### Scenario: El foco no se escapa

- **WHEN** con el panel abierto el administrador aprieta `Tab` desde el último control
- **THEN** el foco vuelve al primer control del panel

### Requirement: Pantalla chica y accesibilidad

Cada pantalla, en cada uno de sus estados, SHALL verse a 320 px de ancho sin scroll horizontal y
MUST NOT tener violaciones de axe (WCAG 2.2 AA), incluido el contraste medido en un navegador real.

#### Scenario: 320 px

- **WHEN** se abre cualquiera de las siete pantallas a 320 px con un identificador de 40 caracteres y
  un nombre de edificio de 200
- **THEN** el ancho del documento no supera el de la ventana

#### Scenario: axe en cada estado

- **WHEN** se corre axe sobre cada pantalla en cada estado
- **THEN** no hay violaciones

### Requirement: Mis edificios

La pantalla SHALL listar (en lista, no en grilla de tarjetas) los edificios del alcance con nombre,
localidad, cantidad de unidades, estado de los coeficientes y estado de migración, cada estado con
texto, tal como los informa el resumen de cada edificio. La acción principal MUST ser "Nuevo edificio",
un formulario corto con nombre y localidad.

#### Scenario: Sin edificios

- **WHEN** el titular no tiene edificios
- **THEN** ve "Todavía no tenés edificios" y "Nuevo edificio"

#### Scenario: Crear un edificio

- **WHEN** el titular crea un edificio con nombre y localidad
- **THEN** llega al resumen del edificio nuevo

### Requirement: Resumen del edificio

La pantalla SHALL mostrar el checklist de puesta a punto con los seis pasos de la API, cada uno `hecho`
o `falta` con texto y con un enlace a la pantalla donde se resuelve, y debajo los datos del edificio y
la configuración vigente en una línea. Si la API dice `listo_para_liquidar`, MUST mostrar "Listo para
liquidar".

#### Scenario: Edificio recién creado

- **WHEN** el administrador abre el resumen de un edificio recién creado
- **THEN** ve los seis pasos con el estado que dice la API y cada uno enlaza a su pantalla

### Requirement: Padrón de unidades

La pantalla SHALL mostrar una tabla con identificador, tipo, piso, superficie y coeficiente, y arriba
la suma de coeficientes con su estado según R01 (ok, advertencia, fuera de tolerancia) en texto, con
cuánto falta o sobra según la diferencia de la API. "Agregar unidad" y tocar una fila MUST abrir el
panel lateral; guardar MUST cerrar el panel y mostrar la fila y la suma que devuelve la API.

#### Scenario: Agregar una unidad

- **WHEN** el administrador agrega una unidad y la guarda
- **THEN** el panel se cierra, la fila aparece y la suma se actualiza con el informe que da la API

#### Scenario: Fuera de tolerancia

- **WHEN** el informe de la API dice `fuera_de_tolerancia` con diferencia `-0.000200`
- **THEN** la pantalla dice en texto que falta 0,0200 % para llegar a 100 %, no sólo con color

### Requirement: Grupos de reparto

La pantalla SHALL listar los grupos con nombre, método, modo de coeficientes y cantidad de unidades, y
para los de coeficientes propios su estado de R01 según la API. "Generales" MUST mostrarse primero,
como automático, sin acciones de edición y con una línea que explica por qué. Crear o editar un grupo
MUST abrirse en el panel lateral, con nombre, método, modo y la selección de unidades (con coeficiente
por unidad si el modo es "propios"); cambiar el modo MUST avisar en el panel que se reescriben los
coeficientes.

#### Scenario: Generales

- **WHEN** el administrador abre la pantalla de grupos
- **THEN** "Generales" está primero, marcado como automático y sin botones de edición

#### Scenario: Guardar a medias

- **WHEN** al editar un grupo se guarda el nombre y falla la lista de unidades
- **THEN** el panel dice qué se guardó y qué no, y la lista muestra lo que dice la API

### Requirement: Categorías de gasto

La pantalla SHALL listar las categorías en orden, con nombre y estado (activa o desactivada), y
permitir agregar, renombrar, desactivar y reactivar. Reordenar MUST hacerse con botones "subir" y
"bajar" operables con teclado; arrastrar, si existe, MUST NOT ser la única forma.

#### Scenario: Subir una categoría con teclado

- **WHEN** el administrador activa "subir" en la tercera categoría con el teclado
- **THEN** pasa a ser la segunda según la API y el foco queda en su botón "subir"

### Requirement: Intereses y vencimiento

La pantalla SHALL mostrar arriba la configuración vigente (tasa, fondo de reserva, vencimiento único
o doble con su día y su recargo) y debajo el historial como línea de tiempo: desde qué fecha rigió cada
versión, quién la creó y qué campos cambiaron respecto de la anterior. "Cambiar configuración" MUST
abrir el panel lateral con la fecha "rige desde" (hoy en Mendoza o después) y avisar que la versión
anterior no se borra.

#### Scenario: Cambiar la tasa

- **WHEN** el titular crea una versión con otra tasa vigente desde mañana
- **THEN** el historial muestra las dos versiones, la nueva con su autor y la tasa como campo cambiado

### Requirement: Confirmar "sin saldos previos"

Una pantalla propia SHALL explicar en castellano simple que el edificio arranca sin deudas ni saldos
anteriores y que no se puede deshacer, y el botón de confirmar MUST habilitarse sólo al tildar "Entiendo
que el edificio arranca sin deudas anteriores", sin modal. Mientras el estado no sea `pendiente`, MUST
mostrar el estado actual en lugar del formulario.

#### Scenario: Sin tildar la casilla

- **WHEN** el titular intenta confirmar sin tildar la casilla, con el teclado o enviando el formulario
- **THEN** no se manda nada a la API y el error queda asociado a la casilla

#### Scenario: Ya confirmado

- **WHEN** el edificio ya está en `sin_saldos_previos`
- **THEN** la pantalla muestra el estado y no ofrece confirmar
