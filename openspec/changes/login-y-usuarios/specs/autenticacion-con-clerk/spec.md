## Purpose

Define cómo una persona prueba quién es con Clerk y cómo esa identidad se convierte en una persona de
una administración, sin que Clerk decida nunca qué puede ver o hacer (D-107, D-099, D-036).

## ADDED Requirements

### Requirement: El token de sesión se verifica sin red y sin la base

La API SHALL aceptar como identidad sólo un token de sesión de Clerk recibido en el encabezado
`Authorization: Bearer`, firmado con RS256 por la clave pública configurada, vigente según `exp` y
`nbf`, con `azp` igual a uno de los orígenes autorizados configurados y con un `sub` con forma de
usuario de Clerk. Cualquier otro token, uno ausente o un encabezado con más de un token MUST responder
401 sin ejecutar ninguna sentencia SQL y sin llamar a ningún servicio externo. El cuerpo y los
encabezados del 401 MUST ser idénticos en todos los casos, salvo el `X-Request-ID`, y nunca MUST
repetir el token ni el texto de error de la librería que lo verificó.

#### Scenario: Token firmado con otra clave

- **WHEN** llega un token con forma válida firmado con una clave distinta de la configurada
- **THEN** la respuesta es 401 y no se ejecutó ninguna sentencia SQL

#### Scenario: Algoritmo cambiado

- **WHEN** llega un token con `alg` igual a `none`, o con `HS256` firmado usando la clave pública como
  secreto
- **THEN** la respuesta es 401 y no se ejecutó ninguna sentencia SQL

#### Scenario: Token vencido o todavía no válido

- **WHEN** llega un token cuyo `exp` ya pasó, o cuyo `nbf` todavía no llegó
- **THEN** la respuesta es 401, idéntica a la de un pedido sin token

#### Scenario: Token de otra aplicación

- **WHEN** llega un token bien firmado cuyo `azp` no está en la lista de orígenes autorizados, o no
  tiene `azp`
- **THEN** la respuesta es 401

#### Scenario: Login sin configurar

- **WHEN** la API arranca sin clave pública de Clerk configurada y llega cualquier pedido con un token
- **THEN** la respuesta es 401, igual que antes del login, y la API arranca igual

### Requirement: La identidad se vincula por el id de Clerk, una vez por administración

Una persona SHALL quedar vinculada a una identidad de Clerk sólo por el id de usuario de Clerk, nunca
por el email solo. Dentro de una administración, un id de Clerk MUST estar vinculado a lo sumo a una
persona y una persona a lo sumo a un id de Clerk. El mismo id de Clerk MAY estar vinculado a personas de
administraciones distintas (una cuenta por administración, D-096). Con un token válido, la API MUST
resolver la persona vinculada de la administración en uso y cargar sus asignaciones desde la base. Un
token válido sin persona vinculada, o con persona vinculada sin ninguna asignación, MUST responder el
mismo 401 que un pedido sin token.

#### Scenario: Persona vinculada con asignación

- **WHEN** llega un token válido de una identidad vinculada a una persona de A con una asignación de
  administrador por edificio
- **THEN** el pedido se atiende con el tenant de A y las asignaciones de esa persona

#### Scenario: Token válido sin vínculo

- **WHEN** llega un token válido de una identidad de Clerk que no está vinculada a ninguna persona
- **THEN** la respuesta es 401 idéntica a la de un pedido sin token

#### Scenario: Vinculada sin asignación

- **WHEN** llega un token válido de una persona vinculada a la que se le quitó su única asignación
- **THEN** la respuesta es 401 idéntica a la de un pedido sin token

#### Scenario: Dos personas con el mismo id de Clerk

- **WHEN** se intenta vincular en la misma administración un id de Clerk que ya tiene otra persona
- **THEN** la base rechaza la escritura y no queda nada escrito

#### Scenario: La misma identidad en dos administraciones

- **WHEN** un id de Clerk está vinculado a una persona de A y a otra de B
- **THEN** las dos filas existen y cada una sólo se usa con el tenant de su administración

### Requirement: Selector de administración después de autenticarse

Con un token válido, la identidad SHALL poder pedir la lista de las administraciones donde tiene una
persona vinculada con al menos una asignación, con su nombre y el de la persona, y nada de otras
administraciones. Si la lista tiene una sola, la web MUST entrar directo; si tiene varias, MUST mostrar
"¿A cuál querés entrar?" antes de cualquier pantalla de dominio. La administración elegida MUST viajar
del servidor de la web a la API y la API MUST usarla sólo si la identidad verificada tiene ahí una
persona vinculada con asignación; si no, o si la identidad tiene varias y no eligió ninguna, la
respuesta MUST ser el mismo 401.

#### Scenario: Una sola administración

- **WHEN** una identidad vinculada sólo en A entra
- **THEN** la web abre "Mis edificios" de A sin mostrar el selector

#### Scenario: Dos administraciones

- **WHEN** una identidad vinculada en A y en B entra
- **THEN** la web muestra el selector con A y B, y nada de otra administración

#### Scenario: Elegir una administración ajena

- **WHEN** una identidad vinculada sólo en A manda como elegida el id de B, una administración real
- **THEN** la respuesta es 401 y no se lee ningún dato de B

#### Scenario: Varias sin elegir

- **WHEN** una identidad vinculada en A y en B pide un complejo sin administración elegida
- **THEN** la respuesta es 401

### Requirement: Ingresos auditados

Cada vez que una persona entra a una administración (con una sola, al autenticarse; con varias, al
elegirla) SHALL quedar una fila de auditoría `ingreso_exitoso` con esa persona y esa administración.
Un token válido de una persona vinculada sin asignación MUST dejar una fila `ingreso_fallido` en su
administración. Un token válido sin persona vinculada MUST dejar una línea de log con el evento y un
resumen no reversible del id de Clerk, sin email, sin nombre y sin el token. Los intentos con contraseña
equivocada no llegan a la API: los registra y los limita Clerk, y el sistema MUST NOT prometer
auditarlos.

#### Scenario: Ingreso a una administración

- **WHEN** una persona vinculada con asignación en A entra a A
- **THEN** queda exactamente una fila `ingreso_exitoso` con su persona, A y el `request_id`

#### Scenario: Persona sin asignación

- **WHEN** una persona vinculada en A sin ninguna asignación presenta un token válido
- **THEN** queda una fila `ingreso_fallido` en A y la respuesta es 401

#### Scenario: Identidad sin vínculo

- **WHEN** una identidad de Clerk sin vínculo presenta un token válido
- **THEN** no queda ninguna fila de auditoría, el log tiene el evento sin email, sin token y sin el id
  de Clerk en claro, y la respuesta es 401

### Requirement: Límite de intentos por cuenta

El ingreso SHALL limitar los intentos fallidos por cuenta con el bloqueo de Clerk, configurado en su
panel, y MUST NOT bloquear a todas las personas que comparten una IP. Una cuenta bloqueada MUST poder
desbloquearse desde el panel de Clerk.

#### Scenario: Muchos intentos sobre una cuenta

- **WHEN** alguien falla la contraseña de una cuenta más veces que el límite configurado
- **THEN** esa cuenta queda bloqueada por el tiempo configurado y otra cuenta desde la misma IP sigue
  pudiendo entrar

### Requirement: La sesión no sale del servidor más de lo necesario

La API SHALL publicarse hacia afuera sólo en `/api/salud`; toda otra ruta de la API MUST ser alcanzable
sólo desde la red interna, por el servidor de la web. El servidor de la web MUST mandar el token de
sesión a la API desde el servidor, nunca exponerlo en el HTML, en las props de un componente de cliente
ni en un log. La administración elegida MUST guardarse en una cookie `HttpOnly`, `Secure` en producción
y `SameSite=Lax`. Las páginas MUST servirse con una política de seguridad de contenido con nonce por
pedido, sin `unsafe-eval`, que permita sólo los orígenes de Clerk que su documentación exige.

#### Scenario: La API desde afuera

- **WHEN** desde afuera de Caddy se pide `/api/complejos` con un token válido
- **THEN** la respuesta es 404 de Caddy y la API no recibió el pedido

#### Scenario: La salud sigue pública

- **WHEN** desde afuera se pide `/api/salud`
- **THEN** responde como hoy

#### Scenario: El token no está en la página

- **WHEN** una persona autenticada abre cualquier pantalla
- **THEN** ni el HTML ni los datos que recibe el navegador para los componentes de cliente contienen el
  token de sesión ni ninguna clave de Clerk

#### Scenario: Política de contenido

- **WHEN** se pide cualquier página
- **THEN** la respuesta trae una política de seguridad de contenido con un nonce distinto en cada pedido
  y sin `unsafe-eval`

### Requirement: Aviso de privacidad

La web SHALL publicar, sin sesión, un aviso de privacidad conforme a la ley 25.326 que diga qué datos
guarda Clerk (email y nombre), que se transfieren fuera del país, con qué fin, quién es responsable y
cómo ejercer los derechos de acceso, rectificación y supresión. La pantalla de ingreso y la de aceptar
una invitación MUST enlazarlo.

#### Scenario: Aviso sin sesión

- **WHEN** alguien sin sesión abre el aviso de privacidad
- **THEN** lo lee completo, con la transferencia internacional dicha

#### Scenario: Enlace desde el ingreso

- **WHEN** alguien abre la pantalla de ingreso o la de aceptar una invitación
- **THEN** tiene un enlace al aviso de privacidad, operable con teclado
