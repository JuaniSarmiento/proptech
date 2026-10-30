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

Toda pantalla que escriba MUST manejar las cinco respuestas del cliente de la API (ok, inválido,
conflicto, sin permiso y sin sesión): una respuesta manejable MUST NOT caer en el mensaje genérico
"No pudimos guardar los datos. Probá de nuevo.", que queda reservado a una falla que la pantalla no
puede explicar. En particular, un 409 de la pantalla de intereses y vencimiento MUST llegar al campo
"rige desde" diciendo que ya hay una versión que rige desde esa fecha, y MUST NOT marcar ningún otro
campo. Un error de la API MUST NOT quedar asociado a un campo que no nombra.

#### Scenario: Identificador repetido

- **WHEN** el administrador guarda una unidad y la API responde 409 con `campo: identificador`
- **THEN** el campo identificador queda marcado como inválido, con un mensaje asociado por programa, y
  el resumen enlaza a ese campo

#### Scenario: Error de un campo desconocido

- **WHEN** la API responde 422 con un `loc` que el formulario no tiene
- **THEN** el error aparece en el resumen y ningún campo queda marcado de más

#### Scenario: Rige desde repetido

- **WHEN** el titular crea una versión de configuración con el mismo "rige desde" que una existente
- **THEN** el campo "rige desde" queda marcado con "Ya hay una versión que rige desde esa fecha", y
  ningún otro campo queda marcado

#### Scenario: Dos errores a la vez en intereses y vencimiento

- **WHEN** el titular manda un "rige desde" repetido junto con un día de vencimiento fuera de rango
- **THEN** cada error cae en su propio campo y "tasa mensual", que es válida, MUST NOT quedar marcada

#### Scenario: Día de vencimiento fuera de rango

- **WHEN** el titular carga un día de vencimiento de 35, tocando el campo o enviando el formulario a
  mano
- **THEN** el rechazo aparece en el campo "día de vencimiento", diciendo el rango válido, y no en otro
  campo

#### Scenario: Toda pantalla que escribe cubre las cinco respuestas

- **WHEN** se revisa cada acción de escritura de la web
- **THEN** cada una tiene su rama para ok, inválido, conflicto, sin permiso y sin sesión, y la suite
  falla si alguna no la tiene

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

### Requirement: Mis edificios

La pantalla SHALL listar (en lista, no en grilla de tarjetas) los edificios del alcance con nombre,
ubicación, cantidad de unidades, estado de los coeficientes y estado de migración, cada estado con
texto, tal como los informa el resumen de cada edificio. Un edificio con la ubicación sin completar MUST
mostrarlo como tal, no en blanco. La acción principal MUST ser "Nuevo edificio", un formulario con
nombre, las tres listas encadenadas de provincia, departamento y localidad, calle y número (opcional),
cantidad de pisos y cantidad de subsuelos. Elegir una provincia MUST cargar sus departamentos y vaciar
la localidad; elegir un departamento MUST cargar sus localidades; cada lista MUST operarse con teclado.

#### Scenario: Sin edificios

- **WHEN** el titular no tiene edificios
- **THEN** ve "Todavía no tenés edificios" y "Nuevo edificio"

#### Scenario: Crear un edificio

- **WHEN** el titular crea un edificio con nombre, ubicación y cantidades de pisos
- **THEN** llega al resumen del edificio nuevo

#### Scenario: Encadenar las listas

- **WHEN** el titular elige la provincia de Mendoza y después cambia de provincia
- **THEN** los departamentos se recargan y el departamento y la localidad que había elegido quedan
  vacíos, sin dejar un trío incoherente

#### Scenario: Elegir la ubicación con teclado

- **WHEN** el titular recorre las tres listas sólo con el teclado
- **THEN** puede elegir provincia, departamento y localidad, con foco visible en cada una

#### Scenario: Edificio migrado sin ubicación

- **WHEN** la lista trae un edificio con la ubicación sin completar
- **THEN** la fila lo dice en texto y enlaza a donde se completa

### Requirement: Resumen del edificio

La pantalla SHALL mostrar el checklist de puesta a punto con los siete pasos de la API, cada uno `hecho`
o `falta` con texto y con un enlace a la pantalla donde se resuelve, y debajo los datos del edificio
(nombre, ubicación completa, calle y número, cantidad de pisos y de subsuelos) y la configuración
vigente en una línea. Si la API dice `listo_para_liquidar`, MUST mostrar "Listo para liquidar". MUST
ofrecer "Editar el edificio", que abre el formulario con los mismos campos del alta ya cargados.

#### Scenario: Edificio recién creado

- **WHEN** el administrador abre el resumen de un edificio recién creado
- **THEN** ve los siete pasos con el estado que dice la API y cada uno enlaza a su pantalla

#### Scenario: Editar el edificio desde el resumen

- **WHEN** el administrador abre "Editar el edificio" y cambia la localidad
- **THEN** el formulario llega con los datos actuales, el guardado muestra lo que devuelve la API y el
  paso de ubicación se recalcula

#### Scenario: Un rol sin permiso de configurar

- **WHEN** un contador abre el resumen de un edificio de su alcance
- **THEN** ve el resumen; si usa "Editar el edificio", el error de la API aparece en el resumen del
  formulario, en castellano simple (ocultar la acción por rol queda para el change de acceso)

### Requirement: Padrón de unidades

La pantalla SHALL mostrar una tabla con identificador, tipo, piso, superficie y coeficiente, y arriba
la suma de coeficientes con su estado según R01 (ok, advertencia, fuera de tolerancia) en texto, con
cuánto falta o sobra según la diferencia de la API. "Agregar unidad" y tocar una fila MUST abrir el
panel lateral; guardar MUST cerrar el panel y mostrar la fila y la suma que devuelve la API.

El piso SHALL elegirse de una lista armada con los pisos del edificio (los subsuelos, planta baja y
`1` a N) y MUST NOT ser un campo de texto libre. Una unidad con el piso sin completar (migrada de antes
de este cambio) MUST mostrarse como tal en la tabla y la pantalla MUST decir cuántas hay que corregir.

#### Scenario: Agregar una unidad

- **WHEN** el administrador agrega una unidad y la guarda
- **THEN** el panel se cierra, la fila aparece y la suma se actualiza con el informe que da la API

#### Scenario: Fuera de tolerancia

- **WHEN** el informe de la API dice `fuera_de_tolerancia` con diferencia `-0.000200`
- **THEN** la pantalla dice en texto que falta 0,0200 % para llegar a 100 %, no sólo con color

#### Scenario: Elegir el piso de la lista del edificio

- **WHEN** el administrador abre el panel de una unidad en un edificio de 4 pisos y 1 subsuelo
- **THEN** la lista de pisos ofrece el subsuelo, "PB" y 1 a 4, y nada más

#### Scenario: Unidades con el piso sin completar

- **WHEN** el edificio tiene tres unidades migradas sin piso
- **THEN** la tabla las marca en texto y la pantalla dice que hay tres pisos por completar

### Requirement: Grupos de reparto

La pantalla SHALL listar los grupos con nombre, método, modo de coeficientes, cantidad de unidades y
estado (activo o desactivado), y para los de coeficientes propios su estado de R01 según la API.
"Generales" MUST mostrarse primero, como automático, sin acciones de edición y con una línea que explica
por qué. Crear o editar un grupo MUST abrirse en el panel lateral, con nombre, método, modo y la
selección de unidades (con coeficiente por unidad si el modo es "propios"); cambiar el modo MUST avisar
en el panel que se reescriben los coeficientes. El formulario MUST NOT pedir la clave: se genera desde
el nombre. La pantalla MUST ofrecer "desactivar" y "reactivar" en los grupos parciales, con una línea
que explique que un grupo no se borra para no dejar gastos sin grupo, y MUST NOT ofrecer "borrar".

#### Scenario: Generales

- **WHEN** el administrador abre la pantalla de grupos
- **THEN** "Generales" está primero, marcado como automático y sin botones de edición, tampoco
  "desactivar"

#### Scenario: Guardar a medias

- **WHEN** al editar un grupo se guarda el nombre y falla la lista de unidades
- **THEN** el panel dice qué se guardó y qué no, y la lista muestra lo que dice la API

#### Scenario: Sin campo de clave

- **WHEN** el administrador abre el panel de un grupo nuevo
- **THEN** no hay campo "clave" y la ayuda explica que se genera desde el nombre

#### Scenario: Desactivar un grupo

- **WHEN** el administrador desactiva un grupo parcial
- **THEN** el grupo queda listado como desactivado, con "reactivar", y la lista muestra lo que devuelve
  la API

### Requirement: Categorías de gasto

La pantalla SHALL listar las categorías en orden, con nombre y estado (activa o desactivada), y
permitir agregar, renombrar, desactivar y reactivar. Reordenar MUST hacerse con botones "subir" y
"bajar" operables con teclado; arrastrar, si existe, MUST NOT ser la única forma. El formulario MUST NOT
pedir la clave: se genera desde el nombre.

#### Scenario: Subir una categoría con teclado

- **WHEN** el administrador activa "subir" en la tercera categoría con el teclado
- **THEN** pasa a ser la segunda según la API y el foco queda en su botón "subir"

#### Scenario: Sin campo de clave

- **WHEN** el administrador agrega una categoría
- **THEN** no hay campo "clave" y la ayuda explica que se genera desde el nombre

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

### Requirement: Cada campo con formato propio dice qué se espera antes de equivocarse

Todo campo cuyo valor válido no sea obvio SHALL decir qué se espera **antes** del error, en un texto de
ayuda junto al campo y en la ayuda "?" de la pantalla, y su mensaje de error MUST nombrar el límite o la
regla concreta en lugar de un texto genérico. MUST cubrir al menos: el identificador de unidad (máximo
de caracteres y ejemplos "1A", "PB-2", "Cochera 3"), el coeficiente (una fracción entre 0 y 1, con
"0,5 es la mitad del edificio", nunca un porcentaje) y la clave de grupos y categorías cuando se la
carga por API. El texto del límite MUST salir de una constante de la web, no del texto que devuelve la
API, para no mostrar nunca el mensaje de una librería (L-007).

#### Scenario: Identificador demasiado largo

- **WHEN** el administrador guarda una unidad con un identificador de 41 caracteres
- **THEN** el error junto al campo dice el máximo real de caracteres, no sólo "Es muy largo."

#### Scenario: Ayuda del identificador

- **WHEN** el administrador abre el panel de una unidad
- **THEN** el campo identificador muestra el formato esperado con ejemplos, sin tener que equivocarse
  primero

#### Scenario: Coeficiente cargado como porcentaje

- **WHEN** el administrador carga el coeficiente `50`
- **THEN** el campo dice, antes y después del rechazo, que se espera una fracción entre 0 y 1 y que
  "0,5 es la mitad del edificio"

#### Scenario: Clave inválida por API

- **WHEN** la API rechaza una clave `Pileta`, `pileta-1` o `1pileta`
- **THEN** el mensaje dice la regla de la clave, no "Este valor no es válido."

### Requirement: "Quitar" en Personal pide confirmación

Quitar una asignación de una persona SHALL pedir una confirmación explícita dentro de la pantalla antes
de mandar nada a la API, con el nombre de la persona y el alcance que se le quita, y MUST poder
confirmarse y cancelarse con el teclado, con el foco visible y devuelto al botón "Quitar" si se cancela.
MUST NOT usar un diálogo nativo del navegador.

#### Scenario: Quitar y cancelar con teclado

- **WHEN** el super admin llega a "Quitar" con `Tab`, lo activa, y cancela con `Esc`
- **THEN** no se mandó nada a la API, la asignación sigue y el foco volvió a "Quitar"

#### Scenario: Quitar y confirmar

- **WHEN** el super admin confirma la advertencia
- **THEN** la asignación se quita y la lista muestra lo que devuelve la API

#### Scenario: Sin diálogo nativo

- **WHEN** se busca un `confirm()` del navegador en la pantalla de personal
- **THEN** no hay ninguno

### Requirement: El aviso de privacidad no muestra notas internas

La página pública de privacidad MUST NOT mostrar notas de trabajo interno ni nombres de quien tiene que
aprobarla. Mientras el aviso siga en borrador (D-108), SHALL decirlo con un texto escrito para el
usuario, y las secciones que faltan completar MUST describirse como pendientes sin nombrar a nadie del
equipo.

#### Scenario: Sin la nota interna

- **WHEN** cualquier persona abre la página de privacidad
- **THEN** no aparece ninguna nota de aprobación interna ni ningún nombre del equipo

#### Scenario: El aviso sigue siendo un borrador

- **WHEN** cualquier persona abre la página de privacidad
- **THEN** ve, en castellano simple, que el aviso está en revisión y qué secciones faltan

### Requirement: La ayuda del resumen describe los siete pasos

La ayuda "?" del resumen del edificio SHALL hablar de los siete pasos de la puesta a punto, nunca de
otra cantidad: su ejemplo y su cierre MUST decir "de 7 pasos" y coincidir con los siete pasos que
muestra la pantalla.

#### Scenario: Ejemplo de la ayuda

- **WHEN** el titular abre la ayuda del resumen de un edificio
- **THEN** el ejemplo habla de un edificio recién creado que arranca en "4 de 7 pasos" (ubicación,
  grupos, categorías e intereses y vencimiento ya hechos al crearlo) y de una barra que, después de
  cargar las unidades (con su piso) y sus coeficientes, queda en "6 de 7", y ningún texto de la
  ayuda dice "de 6"
- **AND** esos números son los que da hoy el cálculo real de pasos de la puesta a punto
  (`lectura.py`, fijado por `test_resumen_puesta_a_punto.py::test_edificio_recien_creado`); el test
  de la ayuda exige sólo el texto, y la sincronía automática con ese cálculo queda como deuda

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
