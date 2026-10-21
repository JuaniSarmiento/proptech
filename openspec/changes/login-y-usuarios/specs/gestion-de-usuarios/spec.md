## Purpose

Define cómo nace cada cuenta de una administración: el alta inicial de su super admin, la invitación
del personal con perfil y alcance, el alta de los vecinos desde el padrón, la aceptación de la
invitación que vincula la identidad de Clerk y la baja del acceso (RA-6, D-106, D-107).

## ADDED Requirements

### Requirement: Alta inicial de una administración

Un operador del sistema SHALL poder crear, con un comando fuera de la web, una administración nueva con
su primera persona como super admin y una invitación para ella. El comando MUST escribir con el rol de
la aplicación y el tenant de la administración nueva, MUST dejar una fila de auditoría `alta_inicial`
cuyo actor es esa persona, y MUST NOT tocar ninguna otra administración. Repetirlo con el mismo email
sobre una administración que ya tiene super admin MUST fallar sin escribir nada.

#### Scenario: Primera administración

- **WHEN** el operador corre el alta inicial con un nombre de administración, un nombre y un email
- **THEN** existen la administración, la persona con una asignación de super admin, una invitación
  pendiente de envío y una fila `alta_inicial`, y ninguna otra administración cambió

#### Scenario: Datos inválidos

- **WHEN** el operador corre el alta inicial con un email sin forma de email o un nombre vacío
- **THEN** el comando termina con error nombrando el campo, sin repetir el valor, y no escribe nada

### Requirement: Sólo el super admin invita y da de alta

Invitar personal, dar de alta un vecino, revocar una invitación y quitar una asignación SHALL exigir el
permiso `invitar_usuarios_y_asignar_edificios` de la matriz de D-106 (sólo el super admin). Sin el
permiso, dentro del alcance, MUST responder 403 con ese permiso; fuera del alcance, 404. Cada operación
MUST dejar su fila de auditoría en la misma transacción, con la persona destinataria y sin el email.

#### Scenario: Un administrador principal invita

- **WHEN** un administrador principal intenta invitar personal o dar de alta un vecino
- **THEN** la respuesta es 403 con `invitar_usuarios_y_asignar_edificios` y no queda nada escrito

#### Scenario: Un vecino da de alta a otro

- **WHEN** un vecino propietario intenta dar de alta a otra persona en su unidad
- **THEN** la respuesta es 403 y no queda nada escrito

#### Scenario: Unidad de otra administración

- **WHEN** el super admin de A da de alta un vecino en una unidad de B, con su UUID real
- **THEN** la respuesta es 404 y no queda nada escrito

### Requirement: Invitar al personal con perfil y alcance

El super admin SHALL poder invitar a una persona con un perfil de personal y su alcance: administrador
o contador, principal o por edificio; auxiliar o consejo, por edificio. El email MUST ser obligatorio y
se guarda en minúsculas. Si la administración ya tiene una persona con ese email, MUST reusarla y
sumarle la asignación; si no, MUST crearla. Una asignación que ya existe para esa persona y ese alcance
MUST responder 409 nombrando el campo (RA-5, RR-3). Super admin y vecino MUST NOT poder invitarse por
esta vía. Si la persona ya está vinculada a Clerk, la asignación vale desde ya y no se manda invitación;
si no, queda una invitación pendiente de envío.

#### Scenario: Contador principal

- **WHEN** el super admin invita a un email nuevo como contador con alcance principal
- **THEN** existen la persona, la asignación de contador sin complejo y una invitación pendiente, y una
  fila `invitar_personal`

#### Scenario: Alcance que el perfil no admite

- **WHEN** el super admin invita a un auxiliar o a un consejo con alcance principal
- **THEN** la respuesta es 422 nombrando el alcance y no queda nada escrito

#### Scenario: Perfil repetido

- **WHEN** el super admin invita como administrador del edificio A a una persona que ya lo es
- **THEN** la respuesta es 409 con `campo=rol` y no queda nada escrito

#### Scenario: Perfil no invitable

- **WHEN** el cuerpo trae `rol` igual a `super_admin` o `vecino`, o un campo que no corresponde
- **THEN** la respuesta es 422 nombrando el campo, sin repetir el valor

### Requirement: Alta de vecinos desde el padrón

El super admin SHALL poder dar de alta en una unidad a una persona con nombre, email y vínculo
(`propietario` o `inquilino`). Una unidad MAY tener varios propietarios y una persona MAY tener vínculos
con varias unidades, con vínculos distintos. La misma persona con dos vínculos en la misma unidad MUST
responder 409. Las reglas de reuso de la persona y de la invitación son las del personal.

#### Scenario: Dos propietarios de una unidad

- **WHEN** el super admin da de alta a dos personas distintas como propietarias de la misma unidad
- **THEN** existen las dos asignaciones de vecino propietario y dos invitaciones pendientes

#### Scenario: Propietaria de una e inquilina de otra

- **WHEN** el super admin da de alta a la misma persona como propietaria de la unidad 1 e inquilina de
  la unidad 2
- **THEN** la persona es una sola, con dos asignaciones y una sola invitación pendiente

#### Scenario: Propietaria e inquilina de la misma unidad

- **WHEN** el super admin da de alta como inquilina a una persona que ya es propietaria de esa unidad
- **THEN** la respuesta es 409 y no queda nada escrito

### Requirement: La invitación la manda Clerk, en segundo plano

Una invitación pendiente SHALL enviarse fuera del pedido que la creó, por el proceso de trabajos en
segundo plano, pidiéndole a Clerk que mande su mail de invitación con una dirección de regreso que
lleva un token propio de un solo uso. El envío MUST ser idempotente (un trabajo repetido sobre una
invitación ya enviada no vuelve a llamar a Clerk) y MUST reintentarse ante una falla transitoria de Clerk. Una falla definitiva MUST
dejar la invitación como fallida, visible para el super admin. Ni el email, ni el token, ni el cuerpo de
la respuesta de Clerk MUST aparecer en un log ni en la auditoría. La base MUST guardar sólo un resumen
no reversible del token.

#### Scenario: Envío exitoso

- **WHEN** el proceso en segundo plano toma una invitación pendiente y Clerk responde bien
- **THEN** la invitación queda enviada, con el id de la invitación de Clerk guardado

#### Scenario: Reintento tras una caída

- **WHEN** Clerk responde 503 dos veces y después bien
- **THEN** la invitación queda enviada después del tercer intento, con un solo id de Clerk guardado

#### Scenario: Trabajo repetido

- **WHEN** el proceso en segundo plano recibe otra vez el trabajo de una invitación ya enviada
- **THEN** no llama a Clerk y la invitación sigue enviada con el mismo id

#### Scenario: Rechazo definitivo

- **WHEN** Clerk responde 422 por un email que rechaza
- **THEN** la invitación queda fallida, sin reintentos, y el log no tiene el email ni el cuerpo de Clerk

### Requirement: Aceptar una invitación vincula la identidad

Una persona autenticada en Clerk SHALL poder aceptar una invitación presentando su token de un solo uso.
La aceptación MUST exigir que la invitación exista, esté enviada, no esté vencida, revocada ni
aceptada, que el email verificado por Clerk coincida con el de la persona invitada, que la persona no
esté vinculada a otro id de Clerk y que la identidad no esté vinculada a otra persona de esa
administración. Si todo se cumple, MUST escribir el vínculo, marcar la invitación aceptada y dejar una
fila `aceptar_invitacion`, todo en una transacción. Cualquier falla MUST responder el mismo 404, sin
decir cuál condición falló, y no escribir nada. Dos aceptaciones simultáneas del mismo token MUST dejar
un solo vínculo.

#### Scenario: Aceptación correcta

- **WHEN** la persona invitada se registra en Clerk con el email de la invitación y vuelve con el token
- **THEN** su persona queda vinculada a su id de Clerk, la invitación queda aceptada y puede entrar

#### Scenario: Otro email

- **WHEN** alguien autenticado en Clerk con otro email presenta un token válido ajeno
- **THEN** la respuesta es 404 y no se vincula nada

#### Scenario: Token reusado o vencido

- **WHEN** se presenta un token ya aceptado, revocado o vencido
- **THEN** la respuesta es 404, igual que con un token inventado

#### Scenario: Dos aceptaciones a la vez

- **WHEN** dos pedidos aceptan el mismo token al mismo tiempo
- **THEN** uno vincula y el otro responde 404, y queda una sola fila `aceptar_invitacion`

### Requirement: Listar, revocar y quitar

El super admin SHALL poder listar las personas de su administración con sus asignaciones y el estado de
su invitación (pendiente, enviada, aceptada, fallida, revocada, vencida), revocar una invitación no
aceptada y quitar una asignación. Quitar una asignación MUST cortar ese acceso en el próximo pedido de
esa persona, sin esperar a que venza su sesión de Clerk. Un super admin MUST NOT poder quitarse su
propia última asignación de super admin.

#### Scenario: Quitar la única asignación

- **WHEN** el super admin quita la única asignación de un auxiliar que tiene una sesión abierta
- **THEN** el próximo pedido de ese auxiliar responde 401

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
su invitación, más una pantalla para aceptar una invitación. Cada pantalla MUST seguir el `shape`
acordado con Juani antes de construirse y las reglas comunes de `pantallas-del-edificio` (ayuda,
estados, errores asociados al campo, teclado, 320 px). Quien no es super admin MUST NOT ver los
controles de invitar ni de quitar.

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
