## MODIFIED Requirements

### Requirement: Sin identidad no hay acceso ni consultas

Todo endpoint de dominio SHALL exigir una identidad. Sin un token de sesión válido (ausente, mal
formado, con firma, algoritmo, vigencia u origen inválidos), MUST responder 401 sin ejecutar ninguna
consulta a la base. Con un token válido, la identidad MUST resolverse leyendo sólo el vínculo de esa
identidad de Clerk con una persona y sus asignaciones, sin leer ningún dato de dominio. Si la identidad
no tiene, en ninguna administración, una persona vinculada con al menos una asignación, la respuesta
MUST ser el 403 `sin_acceso` de `autenticacion-con-clerk`, con su cuerpo constante. Si la tiene en
alguna, pero no en la administración en uso (persona sin asignación en la elegida, administración
ajena, varias sin elegir, selector que no es UUID), la respuesta MUST ser el mismo 401 que sin
identidad, con el mismo cuerpo y los mismos encabezados salvo el `X-Request-ID`. El 403 `sin_acceso`
prevalece sobre ese 401. Los tests pueden seguir inyectando la identidad. `GET /api/sesion` y
`POST /api/invitaciones/aceptar` MUST exigir la segunda guarda, `token_de_sesion_actual`, sin persona
completa; siguen protegidas y fuera de `_RUTAS_PUBLICAS`, también ante JSON roto. El barrido MUST
comprobar ambas dependencias.

#### Scenario: Pedido sin identidad

- **WHEN** se pide un complejo, una unidad o una asignación sin identidad
- **THEN** la respuesta es 401 y no se ejecutó ninguna sentencia SQL

#### Scenario: Token inválido

- **WHEN** se pide un complejo con un token de sesión vencido o firmado con otra clave
- **THEN** la respuesta es 401, idéntica a la de un pedido sin identidad, y no se ejecutó ninguna
  sentencia SQL

#### Scenario: Token válido sin vínculo

- **WHEN** se pide un complejo con un token válido de una identidad de Clerk sin persona vinculada
- **THEN** la respuesta es el 403 con el cuerpo exacto `{"detail": {"codigo": "sin_acceso"}}`, y no se
  leyó ninguna fila de complejo, unidad ni asignación

#### Scenario: Token válido con acceso en otra administración

- **WHEN** una identidad vinculada con asignación en A y sin asignación en B elige B y pide un complejo
- **THEN** la respuesta es 401, idéntica a la de un pedido sin identidad salvo `X-Request-ID`, y no se
  leyó ninguna fila de complejo de B

### Requirement: Permiso por acción según la matriz de la empresa

Cada acción sensible SHALL estar permitida sólo a los perfiles con alcance que marca esta matriz
(D-106, que reemplaza la de D-096, ampliada por D-127 con `ver_personal`). Una asignación por edificio
cuenta sólo en su complejo; una con alcance principal cuenta en todos los complejos de su
administración. Dentro del alcance y sin el permiso, la respuesta MUST ser 403 con el cuerpo
`{"detail": {"codigo": "sin_permiso", "detalle": "sin_permiso", "permiso_faltante": "<acción>"}}`.
Fuera del alcance, la respuesta MUST ser 404 aunque tampoco tenga el permiso: el alcance se evalúa
primero. Una acción que no está en la matriz MUST negarse. Contador, auxiliar y consejo MUST NOT poder
ninguna acción que escriba. Sin complejo (`complejo_id` nulo) sólo MUST evaluarse `crear_edificio`,
`invitar_usuarios_y_asignar_edificios` y `ver_personal`, las tres acciones de toda la administración:
ninguna otra acción de la matriz MUST evaluarse sin complejo, aunque la asignación sea de alcance
principal.

Columnas: SA, super admin; AP, administrador principal; AE, administrador por edificio; CP, contador
principal; CE, contador por edificio; AX, auxiliar; CO, consejo; VP, vecino propietario; VI, vecino
inquilino.

| Acción | SA | AP | AE | CP | CE | AX | CO | VP | VI |
|---|---|---|---|---|---|---|---|---|---|
| `cargar_gastos_y_preparar_liquidacion` | Sí | Sí | Sí | No | No | No | No | No | No |
| `emitir_y_distribuir_liquidacion` | Sí | Sí | Sí | No | No | No | No | No | No |
| `anular_liquidacion` | Sí | Sí | No | No | No | No | No | No | No |
| `confirmar_pago_informado` | Sí | Sí | Sí | No | No | No | No | No | No |
| `revertir_o_reimputar_pago` | Sí | Sí | No | No | No | No | No | No | No |
| `condonar_intereses` | Sí | Sí | No | No | No | No | No | No | No |
| `dar_de_baja_deuda` | Sí | Sí | No | No | No | No | No | No | No |
| `aceptar_alertas_no_bloqueantes` | Sí | Sí | Sí | No | No | No | No | No | No |
| `aceptar_alertas_bloqueantes` | Sí | Sí | No | No | No | No | No | No | No |
| `invitar_usuarios_y_asignar_edificios` | Sí | No | No | No | No | No | No | No | No |
| `ver_personal` | Sí | Sí | No | No | No | No | No | No | No |
| `informar_pago` | No | No | No | No | No | No | No | Sí | Sí |
| `crear_edificio` | Sí | No | No | No | No | No | No | No | No |
| `crear_version_de_configuracion` | Sí | Sí | Sí | No | No | No | No | No | No |
| `confirmar_sin_saldos_previos` | Sí | Sí | No | No | No | No | No | No | No |
| `configurar_padron` | Sí | Sí | Sí | No | No | No | No | No | No |
| `ver_configuracion_del_edificio` | Sí | Sí | Sí | Sí | Sí | Sí | Sí | No | No |

Crear un edificio, que todavía no tiene alcance, MUST evaluar sólo el permiso y sólo con asignaciones
de alcance principal: sin él, 403 con el permiso faltante. El vecino MUST NOT poder leer la
configuración del edificio: ve sólo sus unidades y el complejo de cada una.

#### Scenario: La matriz completa

- **WHEN** se evalúa cada acción de la matriz para cada una de las nueve columnas, en un complejo del
  alcance de la asignación (y sin complejo para las tres acciones de toda la administración)
- **THEN** el resultado coincide celda por celda con la matriz

#### Scenario: Una asignación por edificio en otro complejo

- **WHEN** se evalúa cualquier acción de la matriz para una asignación por edificio, en un complejo
  distinto del suyo
- **THEN** el resultado es "no", para todas las acciones

#### Scenario: El administrador por edificio emite pero no anula

- **WHEN** se evalúan, para un administrador por edificio en su complejo, emitir la liquidación y
  después anularla
- **THEN** emitir está permitido y anular no

#### Scenario: El administrador principal corrige en cualquier edificio

- **WHEN** se evalúan anular, revertir un pago, condonar, dar de baja una deuda y aceptar una alerta
  bloqueante para un administrador principal en un complejo que nadie le asignó
- **THEN** las cinco están permitidas

#### Scenario: El administrador principal ve el personal pero no invita

- **WHEN** se evalúan, sin complejo, `ver_personal` e `invitar_usuarios_y_asignar_edificios` para un
  administrador principal
- **THEN** ver el personal está permitido e invitar no

#### Scenario: Colaborador asigna un edificio

- **WHEN** un administrador por edificio (antes, colaborador "editar") intenta asignar un edificio a una persona en un complejo que
  tiene asignado
- **THEN** la respuesta es 403 con `codigo` `sin_permiso` y el permiso faltante
  `invitar_usuarios_y_asignar_edificios`

#### Scenario: Sin permiso y fuera de alcance

- **WHEN** un administrador por edificio intenta asignar un edificio en un complejo que no tiene
  asignado
- **THEN** la respuesta es 404, no 403

#### Scenario: Titular asigna un edificio

- **WHEN** el super admin (antes, titular) asigna un complejo de su administración a una persona de su administración
  como administrador, contador, auxiliar o consejo
- **THEN** la asignación queda guardada con ese perfil y la persona pasa a ver ese complejo
- **AND** el detalle de auditoría incluye `complejo_id`, `rol`, `alcance`, `persona_id` de la
  destinataria y `asignacion_id` de la fila creada; la columna `persona_id` conserva al actor

#### Scenario: Perfil de personal repetido en un edificio

- **WHEN** el super admin asigna administrador, auxiliar o contador a una persona que ya tiene
  un perfil de personal en ese edificio
- **THEN** recibe 409 `{"detail":"conflicto","campo":"rol"}`, sin filas nuevas de asignación ni auditoría

#### Scenario: Asignar a una persona de otra administración

- **WHEN** el super admin de A intenta asignar un complejo a una persona de B (id con formato válido)
- **THEN** la respuesta es 404 y no queda nada escrito

#### Scenario: Cuerpo de la asignación con el vocabulario viejo o fuera de lo asignable

- **WHEN** el super admin manda una asignación con `nivel`, con `vinculo`, con `unidad_id`, o con un
  perfil `super_admin`, `vecino`, `titular` o `colaborador`
- **THEN** la respuesta es 422 nombrando el campo, no 500, y no queda nada escrito

#### Scenario: Un colaborador crea un edificio

- **WHEN** un administrador, por edificio o principal, intenta crear un edificio
- **THEN** la respuesta es 403 con el permiso faltante y no se crea nada

#### Scenario: Un colaborador "ver" crea una categoría

- **WHEN** un auxiliar del edificio (antes, colaborador "ver") intenta crear una categoría
- **THEN** la respuesta es 403 con el permiso faltante

#### Scenario: El contador no escribe

- **WHEN** un contador principal intenta editar una unidad, crear una categoría o crear una versión de
  configuración en cualquier edificio de su administración
- **THEN** cada respuesta es 403 con el permiso faltante y nada cambia

#### Scenario: El consejo edita una unidad de su edificio

- **WHEN** el consejo del edificio intenta editar una unidad de ese edificio
- **THEN** la respuesta es 403 con el permiso faltante y la unidad no cambia

#### Scenario: El consejo lee el padrón

- **WHEN** el consejo del edificio pide el padrón de unidades de ese edificio
- **THEN** la respuesta es 200 con las unidades y el informe de coeficientes

#### Scenario: El vecino pide la configuración de su edificio

- **WHEN** un vecino propietario o inquilino pide el padrón, los grupos, las categorías, el resumen o
  la configuración del complejo donde tiene su unidad
- **THEN** la respuesta es 403 con el permiso faltante `ver_configuracion_del_edificio` y no trae
  ningún dato de otras unidades

#### Scenario: El vecino pide la configuración de otro edificio

- **WHEN** un vecino pide el padrón de un complejo de su administración donde no tiene unidades
- **THEN** la respuesta es 404, no 403

#### Scenario: El vecino ve su unidad

- **WHEN** un vecino propietario o inquilino pide su propia unidad
- **THEN** la respuesta es 200 con su identificador, tipo, piso, coeficiente y superficie, como texto

## ADDED Requirements

### Requirement: Todo 403 se distingue por `codigo`

Todo 403 de la API SHALL llevar en `detail` la clave `codigo`, el único discriminador que la web lee
para decidir qué significa. Sus valores MUST salir de una lista cerrada declarada una vez en el código:
`sin_acceso` (cuerpo constante, sin otras claves) y `sin_permiso` (con `permiso_faltante`). La clave
`detalle` MAY seguir, sin que la web dependa de ella. Un 403 sin `codigo`, o con
uno desconocido, la web MUST tratarlo como `sin_permiso` "desconocido", nunca como `sin_acceso`.

#### Scenario: Ningún 403 sin código

- **WHEN** el barrido de rutas protegidas provoca un 403 en cada ruta que puede devolverlo, con la
  identidad que lo dispara
- **THEN** cada cuerpo tiene `detail.codigo` y su valor está en la lista cerrada

#### Scenario: El 403 de permiso lleva su código

- **WHEN** un auxiliar intenta crear una categoría en su edificio
- **THEN** la respuesta es 403 con `codigo` `sin_permiso` y `permiso_faltante` `configurar_padron`

#### Scenario: Un 403 sin código en la web

- **WHEN** la web recibe un 403 cuyo cuerpo no trae `codigo`, o trae un valor que no conoce
- **THEN** lo muestra como "sin permiso" con el permiso "desconocido" y no redirige a `/sin-acceso`

### Requirement: Las acciones permitidas viajan con la sesión

`GET /api/sesion` SHALL devolver, en cada administración de la lista, las acciones que la persona
vinculada ahí puede hacer, en tres conjuntos: `administracion` (acciones sin complejo),
`todos_los_edificios` (permitidas en cualquier edificio por una asignación principal) y `por_edificio`
(para cada edificio con asignación por edificio o por unidad, las permitidas ahí además de las
anteriores). Ampliar la sesión MUST NOT cambiar el 403 `sin_acceso`, que sigue sin ninguna clave más.

#### Scenario: El super admin

- **WHEN** el super admin de A pide `GET /api/sesion`
- **THEN** A trae en `administracion` `crear_edificio`, `invitar_usuarios_y_asignar_edificios` y
  `ver_personal`, y en `todos_los_edificios` todas las acciones de la matriz con complejo que su columna
  permite

#### Scenario: Un contador por edificio

- **WHEN** un contador del edificio E de A pide `GET /api/sesion`
- **THEN** A trae `administracion` y `todos_los_edificios` vacíos y en `por_edificio` sólo E, con
  `ver_configuracion_del_edificio`

#### Scenario: El 403 sin acceso no cambia

- **WHEN** una identidad sin acceso pide `GET /api/sesion` con la sesión ampliada
- **THEN** el cuerpo sigue siendo exactamente `{"detail": {"codigo": "sin_acceso"}}`

### Requirement: Las acciones de la sesión coinciden con los 403

Las acciones de la sesión SHALL calcularse en la API con la misma matriz y las mismas asignaciones que
`puede` usa para responder 403, nunca guardadas aparte. Para toda acción y todo edificio, "está en
`administracion`" (sin complejo) o "está en `todos_los_edificios` o en `por_edificio` de ese edificio"
(con complejo) MUST coincidir con `puede`.

#### Scenario: Las acciones coinciden con los 403

- **WHEN** se compara, para cada una de las nueve columnas, cada acción y cada edificio (el propio y
  uno ajeno), lo que dice la sesión contra `puede`
- **THEN** coinciden en todas las celdas

### Requirement: La web oculta lo que la persona no puede usar

La web SHALL mostrar cada control que dispara una acción de la matriz ("Personal" en el menú de la
administración, "Nuevo edificio", "Agregar unidad" y los controles de escritura del edificio y de
`/personal`) sólo si la sesión dice que esa acción está permitida ahí. Las secciones de sólo lectura
MUST seguir visibles. Ocultar MUST NOT reemplazar al chequeo de la API. Sin acciones de sesión, la web
MUST ocultar todo control de escritura.

#### Scenario: Un contador abre un edificio

- **WHEN** un contador del edificio E abre el padrón de E
- **THEN** ve las unidades sin "Agregar unidad" ni ningún control de edición, y el menú de la
  administración no muestra "Personal"

#### Scenario: Un administrador por edificio

- **WHEN** un administrador del edificio E abre la lista de edificios y el padrón de E
- **THEN** no ve "Nuevo edificio" y sí ve "Agregar unidad" en E

#### Scenario: El control oculto pedido a mano

- **WHEN** un contador manda a mano el pedido de crear una unidad en E
- **THEN** la respuesta sigue siendo 403 con `codigo` `sin_permiso` y nada cambia

#### Scenario: Sin acciones en la sesión

- **WHEN** una pantalla del edificio se dibuja sin acciones de sesión disponibles
- **THEN** no muestra ningún control de escritura
