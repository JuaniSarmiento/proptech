## RENAMED Requirements

- FROM: `### Requirement: Alcance por edificio según el rol`
- TO: `### Requirement: Alcance según el perfil`

- FROM: `### Requirement: Permiso por acción según D-096`
- TO: `### Requirement: Permiso por acción según la matriz de la empresa`

## MODIFIED Requirements

### Requirement: Alcance según el perfil

Dentro de su administración, cada asignación SHALL tener un perfil y un alcance: **principal** (toda
la administración), **por edificio** (un complejo) o **por unidad** (una unidad y el complejo de esa
unidad). El super admin tiene siempre alcance principal; el administrador y el contador, principal o
por edificio; el auxiliar y el consejo, por edificio; el vecino propietario y el vecino inquilino, por
unidad. Una persona SHALL ver los complejos y las unidades que alcanza alguna de sus asignaciones: con
alcance principal, todos los de su administración; por edificio, ese complejo y sus unidades; por
unidad, esa unidad y su complejo. El perfil y el alcance MUST leerse de las asignaciones guardadas en
la base, nunca de lo que diga el pedido.

#### Scenario: Colaborador en un edificio no asignado

- **WHEN** un administrador por edificio (antes, colaborador) pide un complejo de su administración que no tiene asignado
- **THEN** la respuesta es 404

#### Scenario: Vecino en la unidad de otro vecino

- **WHEN** un vecino propietario o inquilino pide una unidad de su mismo complejo que no es suya
- **THEN** la respuesta es 404

#### Scenario: Consejo en otro edificio

- **WHEN** un miembro del consejo pide un complejo distinto del suyo
- **THEN** la respuesta es 404

#### Scenario: Titular

- **WHEN** el super admin (antes, titular) pide cualquier complejo o unidad de su administración
- **THEN** la respuesta es 200 con el dato

#### Scenario: Contador principal

- **WHEN** un contador con alcance principal lista los edificios y pide uno que nadie le asignó
- **THEN** la lista trae todos los edificios de su administración y el pedido responde 200

#### Scenario: Dos asignaciones de la misma persona

- **WHEN** una persona es administrador por edificio en A y auxiliar en B y pide C, de su misma
  administración
- **THEN** la respuesta es 404, y A y B responden 200

### Requirement: Permiso por acción según la matriz de la empresa

Cada acción sensible SHALL estar permitida sólo a los perfiles con alcance que marca esta matriz
(D-106, que reemplaza la de D-096). Una asignación por edificio cuenta sólo en su complejo; una con
alcance principal cuenta en todos los complejos de su administración. Dentro del alcance y sin el
permiso, la respuesta MUST ser 403 con el nombre del permiso faltante. Fuera del alcance, la respuesta
MUST ser 404 aunque tampoco tenga el permiso: el alcance se evalúa primero. Una acción que no está en
la matriz MUST negarse. Contador, auxiliar y consejo MUST NOT poder ninguna acción que escriba. Sin
complejo (`complejo_id` nulo, al crear un edificio) sólo MUST evaluarse el permiso `crear_edificio`:
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
  alcance de la asignación
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

#### Scenario: Colaborador asigna un edificio

- **WHEN** un administrador por edificio (antes, colaborador "editar") intenta asignar un edificio a una persona en un complejo que
  tiene asignado
- **THEN** la respuesta es 403 con el permiso faltante `invitar_usuarios_y_asignar_edificios`

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

### Requirement: La base sostiene la forma de cada asignación

La base SHALL rechazar, también por SQL como `proptech_app`, toda asignación que no tenga la forma de
su perfil: super admin sin complejo ni unidad; administrador y contador sin unidad, con o sin complejo;
auxiliar y consejo con complejo y sin unidad; vecino con complejo, unidad y vínculo. El vínculo
(`propietario` o `inquilino`) MUST existir sólo en el vecino. Un perfil fuera de la lista MUST
rechazarse. Una persona MUST tener a lo sumo una relación con cada unidad. Una persona MUST tener
también a lo sumo una asignación de rol de personal (super admin, administrador, contador o auxiliar)
por alcance, incluido el alcance principal (RA-5): no impide, además, que esa misma persona sea
consejo o vecino, que son asignaciones de otro tipo.

#### Scenario: Alcance principal regalado

- **WHEN** como `proptech_app` se inserta un auxiliar, un consejo o un vecino sin complejo
- **THEN** la base rechaza la escritura

#### Scenario: Super admin atado a un edificio

- **WHEN** como `proptech_app` se inserta un super admin con complejo
- **THEN** la base rechaza la escritura

#### Scenario: Vecino sin vínculo o personal con vínculo

- **WHEN** como `proptech_app` se inserta un vecino sin vínculo, o un administrador con vínculo
- **THEN** la base rechaza la escritura

#### Scenario: Perfil desconocido

- **WHEN** como `proptech_app` se inserta una asignación con perfil `titular`, `colaborador` o
  cualquier otro fuera de la lista
- **THEN** la base rechaza la escritura

#### Scenario: Propietaria e inquilina de la misma unidad

- **WHEN** como `proptech_app` se inserta, para una persona que ya es propietaria de una unidad, una
  segunda relación con esa unidad
- **THEN** la base rechaza la escritura

#### Scenario: Dos roles de personal en el mismo alcance

- **WHEN** como `proptech_app` se inserta, para una persona que ya es administrador, contador, auxiliar
  o super admin en un alcance (un edificio, o el alcance principal), una segunda fila de rol de
  personal en ese mismo alcance
- **THEN** la base rechaza la escritura, y esto vale también cuando las dos filas tienen `complejo_id`
  nulo (alcance principal)

### Requirement: Propietario e inquilino de una unidad

Ser propietario o inquilino SHALL ser un atributo de la relación entre una persona y una unidad, no de
la persona: una misma persona MUST poder ser propietaria de una unidad e inquilina de otra, y una
unidad MUST poder tener varios propietarios, cada uno con su cuenta. Todos los propietarios y el
inquilino de una unidad MUST ver esa unidad e informar pagos de ella. El inquilino MUST ver sólo las
expensas ordinarias de su unidad, y el propietario todas: este cambio no construye la lectura de
expensas (no existe hasta los cambios 6 y 7), así que esa parte MUST cumplirse desde el primer cambio
que exponga expensas, con la distinción que este cambio deja en cada asignación.

#### Scenario: Dos propietarios de la misma unidad

- **WHEN** dos personas distintas son propietarias de la misma unidad y cada una pide esa unidad
- **THEN** las dos reciben 200 y las dos pueden informar un pago de esa unidad

#### Scenario: Propietaria de una unidad e inquilina de otra

- **WHEN** una persona es propietaria de la unidad 1 e inquilina de la unidad 2 del mismo complejo
- **THEN** ve las dos unidades, y su vínculo con cada una es el que tiene guardado esa relación

#### Scenario: El inquilino y las expensas extraordinarias

- **WHEN** existe la lectura de expensas y el inquilino de una unidad pide las expensas de esa unidad
- **THEN** recibe sólo las ordinarias, mientras el propietario de la misma unidad recibe ordinarias y
  extraordinarias

### Requirement: Las asignaciones existentes pasan a los perfiles nuevos

Al aplicar este cambio, cada asignación existente de toda administración SHALL convertirse: titular a
super admin; colaborador "editar" a administrador por edificio; colaborador "ver" a auxiliar del mismo
edificio; consejo a consejo; vecino a vecino propietario de la misma unidad. Ninguna fila MUST quedar
con el vocabulario anterior y la tabla MUST seguir con RLS habilitada y forzada al terminar. Volver
atrás MUST devolver cada fila a su forma anterior y, si existe alguna asignación sin forma anterior
(un contador, un administrador principal o un vecino inquilino), MUST fallar sin cambiar nada y sin
nombrar a ninguna persona.

#### Scenario: Conversión en dos administraciones

- **WHEN** hay asignaciones de cada forma anterior en dos administraciones y se aplica el cambio
- **THEN** leídas como `proptech_app` con el tenant de cada una, todas tienen su perfil nuevo y ninguna
  quedó con el vocabulario anterior

#### Scenario: La tabla sigue aislada

- **WHEN** termina la conversión, o falla a mitad
- **THEN** `asignacion_rol` tiene RLS habilitada y forzada, y con el tenant de A no se ve ninguna fila
  de B

#### Scenario: Una relación repetida frena la conversión

- **WHEN** antes de aplicar el cambio una persona tiene dos asignaciones de vecino sobre la misma unidad
- **THEN** la conversión falla sin cambiar nada, con un mensaje que no nombra a la persona

#### Scenario: Volver atrás sin datos nuevos

- **WHEN** sólo hay asignaciones con forma anterior y se vuelve atrás
- **THEN** cada fila recupera su rol y su nivel anteriores y el esquema queda igual que antes del
  cambio

#### Scenario: Volver atrás con un contador o un inquilino

- **WHEN** existe un contador, un administrador principal o un vecino inquilino y se vuelve atrás
- **THEN** la vuelta atrás falla, dice cuántas filas de cada tipo lo impiden sin nombrar a nadie, y
  ninguna fila ni el esquema cambian
