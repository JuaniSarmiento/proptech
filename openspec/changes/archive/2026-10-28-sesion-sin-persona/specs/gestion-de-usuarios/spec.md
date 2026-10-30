## MODIFIED Requirements

### Requirement: Invitar al personal con perfil y alcance

El super admin SHALL poder invitar a una persona con un perfil de personal y su alcance: administrador
o contador, principal o por edificio; auxiliar o consejo, por edificio. El email MUST ser obligatorio y
se guarda en minúsculas. Si la administración ya tiene una persona con ese email, MUST reusarla, sumarle
la asignación y dejarle el nombre recibido en esta invitación, en la misma transacción, esté o no
vinculada a Clerk; si no, MUST crearla. Si la asignación se rechaza (409, 422), el nombre MUST NOT
cambiar. El nombre de una persona que tiene una asignación de super admin MUST NOT cambiar por esta vía
ni por el alta de vecinos, aunque la asignación nueva prospere, y una invitación en una administración
MUST NOT cambiar el nombre de una persona de otra administración con el mismo email. Una asignación que ya existe para esa persona y ese alcance MUST responder 409 nombrando el
campo (RA-5, RR-3). Super admin y vecino MUST NOT poder invitarse por esta vía. Si la persona ya está
vinculada a Clerk, la asignación vale desde ya y no se manda invitación; si no, queda una invitación
pendiente de envío.

#### Scenario: Contador principal

- **WHEN** el super admin invita a un email nuevo como contador con alcance principal
- **THEN** existen la persona, la asignación de contador sin complejo y una invitación pendiente, y una
  fila `invitar_personal`

#### Scenario: Alcance que el perfil no admite

- **WHEN** el super admin invita a un auxiliar o a un consejo con alcance principal
- **THEN** la respuesta es 422 nombrando el alcance y no queda nada escrito

#### Scenario: Reinvitar revoca la anterior

- **WHEN** se vuelve a invitar a una persona sin vínculo con una invitación pendiente, enviada o fallida,
  aunque esté vencida
- **THEN** en una transacción se revoca primero la anterior y se crea la nueva, queda una sola abierta
  y el enlace anterior responde 404 al intentar aceptarlo

#### Scenario: Reinvitar el mismo email con otro nombre

- **WHEN** el super admin invitó a `x@ejemplo.invalid` como "Ana", revocó esa invitación y la vuelve a
  invitar como "Ana María" con otro perfil
- **THEN** `/personal` muestra una sola persona, "Ana María", con las dos asignaciones

#### Scenario: Reinvitar el email del super admin no lo renombra

- **WHEN** el super admin de A invita su propio email, o el de otro super admin de A, con otro nombre y
  un perfil que esa persona todavía no tiene, o lo da de alta como vecino de una unidad
- **THEN** la asignación sigue sus reglas de siempre y el nombre persistido del super admin no cambia

#### Scenario: Reinvitar en una administración no renombra en otra

- **WHEN** A y B tienen cada una una persona con `x@ejemplo.invalid`, y el super admin de A la reinvita
  con otro nombre
- **THEN** el nombre de la persona de A cambia y el de la persona de B no

#### Scenario: El nombre no cambia si la invitación se rechaza

- **WHEN** el super admin reinvita a `x@ejemplo.invalid` como "Otra" con un perfil que esa persona ya
  tiene en ese alcance
- **THEN** la respuesta es 409 con `campo=rol` y el nombre sigue siendo el anterior

#### Scenario: Perfil repetido

- **WHEN** el super admin invita como administrador del edificio A a una persona que ya lo es
- **THEN** la respuesta es 409 con `campo=rol` y no queda nada escrito

#### Scenario: Perfil no invitable

- **WHEN** el cuerpo trae `rol` igual a `super_admin` o `vecino`, o un campo que no corresponde
- **THEN** la respuesta es 422 nombrando el campo, sin repetir el valor

### Requirement: Listar, revocar y quitar

El super admin SHALL poder listar las personas de su administración con sus asignaciones y el estado de
su invitación (pendiente, enviada, aceptada, fallida, revocada, vencida), revocar una invitación no
aceptada y quitar una asignación. El administrador principal SHALL poder listar, sin revocar ni quitar,
sólo al personal que está por debajo suyo (D-127): las personas con al menos una asignación y cuyas
asignaciones son todas de administrador por edificio, contador, auxiliar o consejo, con esas
asignaciones. Una persona sin ninguna asignación MUST NOT aparecer. Ese filtro MUST
aplicarse en la API, nunca en la web: la respuesta al administrador principal MUST NOT contener ninguna
persona que tenga una asignación de super admin, de administrador principal o de vecino, ni su id, ni
su nombre, ni su email. Quien no tiene `ver_personal` MUST recibir 403 con ese permiso faltante. Quitar
una asignación MUST cortar ese acceso en el próximo pedido de esa persona, sin esperar a que venza su
sesión de Clerk. Un super admin MUST NOT poder quitarse su propia última asignación de super admin.

#### Scenario: Quitar la única asignación

- **WHEN** el super admin quita la única asignación de un auxiliar que tiene una sesión abierta y no
  está vinculado en otra administración
- **THEN** el próximo pedido de ese auxiliar responde el 403 `sin_acceso`

#### Scenario: Quitar la asignación de una administración, con acceso en otra

- **WHEN** el super admin de A quita la única asignación en A de una persona cuya identidad tiene
  asignación en B, y esa persona pide algo con A elegida
- **THEN** la respuesta es 401

#### Scenario: El administrador principal lista el personal

- **WHEN** un administrador principal de A pide `GET /api/personal`, y A tiene un super admin, otro
  administrador principal, un contador por edificio, un auxiliar y un vecino
- **THEN** la respuesta trae sólo al contador y al auxiliar, y el cuerpo no contiene el id, el nombre ni
  el email del super admin, del otro administrador principal ni del vecino

#### Scenario: Una persona sin asignaciones no aparece para el administrador principal

- **WHEN** A tiene una persona a la que se le quitó su última asignación (que era de super admin o de
  vecino), y un administrador principal de A pide `GET /api/personal`
- **THEN** la respuesta no contiene el id, el nombre ni el email de esa persona

#### Scenario: El administrador principal no gestiona

- **WHEN** un administrador principal intenta invitar, revocar una invitación o quitar una asignación
- **THEN** la respuesta es 403 con `invitar_usuarios_y_asignar_edificios` y no queda nada escrito

#### Scenario: Un administrador por edificio pide el personal

- **WHEN** un administrador por edificio pide `GET /api/personal`
- **THEN** la respuesta es 403 con el permiso faltante `ver_personal`

#### Scenario: Revocar una invitación enviada

- **WHEN** el super admin revoca una invitación enviada
- **THEN** la invitación queda revocada, Clerk recibe el pedido de revocación en segundo plano y su
  token ya no se puede aceptar

#### Scenario: El último super admin

- **WHEN** el único super admin intenta quitarse su asignación de super admin
- **THEN** la respuesta es 409 y la asignación sigue

### Requirement: Pantallas de gestión de usuarios

La web SHALL ofrecer al super admin una pantalla de personal (lista, invitar con perfil y alcance,
revocar, quitar) y, dentro del padrón de cada unidad, el alta de vecinos con su vínculo y el estado de
su invitación, más una pantalla para aceptar una invitación. Al administrador principal le SHALL
ofrecer la misma pantalla de personal en sólo lectura, con la lista que le devuelve la API. Cada
pantalla MUST seguir el `shape` acordado con Juani antes de construirse y las reglas comunes de
`pantallas-del-edificio` (ayuda, estados, errores asociados al campo, teclado, 320 px). Quien no es
super admin MUST NOT ver los controles de invitar, revocar ni quitar, y quien no tiene `ver_personal`
MUST NOT ver "Personal" en el menú.

#### Scenario: Invitar desde la pantalla

- **WHEN** el super admin invita a un contador por edificio desde la pantalla de personal
- **THEN** la lista muestra a la persona con su perfil, su edificio y la invitación pendiente, sin
  recargar a mano

#### Scenario: Error asociado al campo

- **WHEN** el super admin invita con un email inválido
- **THEN** el error queda asociado al campo email por programa y el foco va a ese campo

#### Scenario: Un administrador abre el padrón

- **WHEN** un administrador por edificio abre el padrón de su edificio
- **THEN** ve las unidades sin el control de dar de alta vecinos

#### Scenario: El administrador principal abre Personal

- **WHEN** un administrador principal abre `/personal`
- **THEN** ve la lista de su personal por debajo, sin "Invitar", "Revocar" ni "Quitar", y la ayuda dice
  que la gestión la hace el super admin

## ADDED Requirements

### Requirement: La invitación abierta con otra cuenta lo dice

Cuando la persona abre `/invitacion/<sobre>` con una sesión de Clerk abierta, la pantalla SHALL decir
con qué cuenta está ingresada (el email del claim firmado de su token, leído en el servidor de la web)
antes de aceptar, y ofrecer "Usar otra cuenta", que cierra la sesión y lleva al ingreso con `regreso` a
la misma invitación. Si la aceptación falla con sesión, el mensaje MUST decir que el enlace no sirve
con esa cuenta y repetir "Usar otra cuenta". Sin sesión, la pantalla queda como hoy.

#### Scenario: Abrir la invitación con la sesión de otra cuenta

- **WHEN** A fue invitada y, en el mismo navegador, está ingresada la cuenta de B, que abre el enlace de
  A
- **THEN** la pantalla dice que está ingresada como el email de B y ofrece "Aceptar e ingresar" y "Usar
  otra cuenta"

#### Scenario: Usar otra cuenta

- **WHEN** B elige "Usar otra cuenta"
- **THEN** su sesión de Clerk se cierra y ve el formulario de `/ingresar` con `regreso` a la misma
  invitación y el mismo `__clerk_ticket`, el enlace que hoy ya arma la página con `cerrar=1`

### Requirement: Sin claim de email la invitación no nombra ninguno

Si el token de sesión no trae el claim de email, los textos de la invitación con sesión SHALL usar su
forma genérica, antes de aceptar y cuando la aceptación falla, sin nombrar ningún email (ni vacío ni
"undefined"), con las mismas acciones.

#### Scenario: Token sin email

- **WHEN** el token de sesión no trae el claim de email
- **THEN** la pantalla dice que hay una sesión abierta sin nombrar ningún email, sin un texto vacío ni
  "undefined", y ofrece las mismas acciones

#### Scenario: Aceptación fallida sin claim de email

- **WHEN** el token de sesión no trae el claim de email y la aceptación falla
- **THEN** el mensaje dice, sin nombrar ningún email, que el enlace no sirve con la cuenta con la que
  ingresó, y ofrece "Usar otra cuenta"

### Requirement: Decir la cuenta no abre una lectura del destinatario

Para B-3, la API de aceptación SHALL quedar como está: el mismo 404 `{"detail":"no encontrado"}` ante
todo rechazo, sin decir qué condición falló. La web MUST NOT pedir ni mostrar el email destinatario de
la invitación, ni tomar el email que muestra de la URL.

#### Scenario: Aceptar con la cuenta equivocada

- **WHEN** B acepta la invitación de A
- **THEN** la API responde el mismo 404 `{"detail":"no encontrado"}` de hoy, no vincula nada, y la
  pantalla dice que el enlace no sirve con la cuenta de B y ofrece "Usar otra cuenta"

#### Scenario: El email no sale de la URL

- **WHEN** se abre `/invitacion/<sobre>` con un parámetro de query que trae un email
- **THEN** la pantalla no muestra ese email
