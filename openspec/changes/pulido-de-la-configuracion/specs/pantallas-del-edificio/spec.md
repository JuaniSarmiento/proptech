# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
