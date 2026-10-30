# autenticacion-con-clerk Specification

## Purpose
Define cómo una persona prueba quién es con Clerk y cómo esa identidad se convierte en una persona de
una administración, sin que Clerk decida nunca qué puede ver o hacer (D-107, D-099, D-036).

## Requirements

### Requirement: El token de sesión se verifica sin red y sin la base

La API SHALL aceptar como identidad sólo un token de sesión de Clerk recibido en el encabezado
`Authorization: Bearer`, firmado con RS256 por la clave pública configurada, vigente según `exp` y
`nbf` contra un `ahora` UTC inyectado con tolerancia de 5 s, con `iss` igual a la URL exacta del
Frontend API de la instancia configurada, con `azp` igual a uno de los orígenes autorizados y con un
`sub` con forma de usuario de Clerk. Cualquier otro token, uno ausente o un encabezado con más de un token MUST responder
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

- **WHEN** llega un token con `ahora >= exp + 5`, o con `ahora < nbf - 5`
- **THEN** la respuesta es 401, idéntica a la de un pedido sin token

#### Scenario: Token de otra aplicación

- **WHEN** llega un token bien firmado cuyo `azp` no está en la lista de orígenes autorizados, o no
  tiene `azp`
- **THEN** la respuesta es 401

#### Scenario: Login sin configurar

- **WHEN** la API arranca sin clave pública de Clerk configurada y llega cualquier pedido con un token
- **THEN** la respuesta es 401, igual que antes del login, y la API arranca igual

#### Scenario: Bordes con reloj inyectado

- **WHEN** con `leeway = 5` y los otros tiempos compatibles se verifica el token usando como `ahora`
  `exp - leeway - 1`, `exp - leeway`, `exp + leeway - 1`, `exp + leeway` y `exp + leeway + 1`
- **THEN** los tres primeros son válidos y los dos últimos no, aunque el reloj real indique otra fecha

#### Scenario: Emisor de otra instancia

- **WHEN** el token tiene firma y `azp` válidos, pero `iss` falta o pertenece a otra instancia de Clerk
- **THEN** la respuesta es 401 y no se ejecutó ninguna sentencia SQL

### Requirement: Dos guardas según la ruta

Los endpoints de dominio SHALL exigir `identidad_actual`, que depende de `token_de_sesion_actual`.
Sólo `GET /api/sesion` y `POST /api/invitaciones/aceptar` SHALL exigir el token verificado sin persona
completa mediante `Depends(token_de_sesion_actual)` y `RutaConTokenVerificado`, variante de
`RutaConIdentidad` que usa esa misma guarda ante errores de parseo. Ambas MUST permanecer en el
barrido de rutas protegidas y MUST NOT figurar en `_RUTAS_PUBLICAS`. Sin sesión válida, incluso con
JSON roto o cuerpo ausente, MUST responder 401 y cero SQL antes de cualquier error del cuerpo.

#### Scenario: Dos rutas con token sin persona

- **WHEN** se pide cualquiera de esas dos rutas sin token o con sesión inválida, con cuerpo correcto,
  ausente o JSON roto
- **THEN** responde el mismo 401 y no se ejecutó ninguna sentencia SQL; con token válido sin persona,
  la guarda deja pasar al caso de uso sin exigir un vínculo previo

### Requirement: La identidad se vincula por el id de Clerk, una vez por administración

Una persona SHALL quedar vinculada a una identidad de Clerk sólo por el id de usuario de Clerk, nunca
por el email solo. Dentro de una administración, un id de Clerk MUST estar vinculado a lo sumo a una
persona y una persona a lo sumo a un id de Clerk. El mismo id de Clerk MAY estar vinculado a personas de
administraciones distintas (una cuenta por administración, D-096). Con un token válido, la API MUST
resolver la persona vinculada de la administración en uso y cargar sus asignaciones desde la base.

Un token que no verifica MUST responder 401, sin cuerpo propio y sin ninguna sentencia SQL. Un token
válido cuya identidad no tiene, en **ninguna** administración, una persona vinculada con al menos una
asignación MUST responder **403** con el cuerpo exacto `{"detail": {"codigo": "sin_acceso"}}`, tanto en
`GET /api/sesion` como en cualquier ruta de dominio. Ese 403 MUST ser idéntico, en código, cuerpo y
cabeceras propias de la API (todas salvo `X-Request-ID`), para la identidad sin ninguna persona
vinculada y para la identidad con personas vinculadas pero sin asignaciones; MUST NOT nombrar ni contar
administraciones, MUST NOT depender de que exista una persona o una invitación con el email del token, y
MUST NOT leer la base por email para decidirlo. Ninguna ruta de dominio MUST ejecutar SQL de su caso de
uso antes de devolverlo.

**Precedencia**: el 403 `sin_acceso` MUST prevalecer sobre los rechazos de elección. Una identidad sin
acceso en ninguna administración recibe el 403 `sin_acceso` aunque además mande un selector de
administración ajeno, un selector que no es UUID o ninguno teniendo varias personas vinculadas. Los
rechazos de elección (administración ajena, varias sin elegir, selector que no es UUID, persona sin
asignación en la elegida) responden 401 **sólo** cuando la identidad tiene acceso en alguna otra
administración.

#### Scenario: Persona vinculada con asignación

- **WHEN** llega un token válido de una identidad vinculada a una persona de A con una asignación de
  administrador por edificio
- **THEN** el pedido se atiende con el tenant de A y las asignaciones de esa persona

#### Scenario: Token válido sin vínculo

- **WHEN** llega a `GET /api/sesion` y a `GET /api/complejos` un token válido de una identidad de Clerk
  que no está vinculada a ninguna persona
- **THEN** las dos respuestas son 403 con el cuerpo exacto `{"detail": {"codigo": "sin_acceso"}}` y
  ninguna es 401

#### Scenario: Vinculada sin asignación

- **WHEN** llega un token válido de una persona vinculada en A a la que se le quitó su única asignación,
  y la identidad no está vinculada en ninguna otra administración
- **THEN** la respuesta es 403 con el mismo cuerpo, byte a byte, y las mismas cabeceras salvo
  `X-Request-ID`, que la del escenario "Token válido sin vínculo"

#### Scenario: Sin acceso con un selector ajeno

- **WHEN** una identidad sin ninguna persona vinculada, y otra identidad vinculada en A sin
  asignaciones, mandan cada una `X-Proptech-Administracion` con el id de B, una administración real
- **THEN** las dos respuestas son el 403 `sin_acceso` y no se leyó ninguna fila de B

#### Scenario: Sin acceso con un selector que no es UUID

- **WHEN** una identidad sin acceso en ninguna administración manda `X-Proptech-Administracion:
  no-es-uuid`
- **THEN** la respuesta es el 403 `sin_acceso`, nunca 401 ni 422

#### Scenario: Dos vínculos sin asignaciones y sin selector

- **WHEN** una identidad vinculada en A y en B, sin asignaciones en ninguna de las dos, pide un complejo
  sin administración elegida
- **THEN** la respuesta es el 403 `sin_acceso` y no queda ninguna fila `ingreso_fallido` ni en A ni en B

#### Scenario: Token inválido sigue siendo 401

- **WHEN** llega a `GET /api/sesion` un pedido sin token, con un token firmado con otra clave, vencido o
  de otra aplicación
- **THEN** la respuesta es 401, nunca 403, y no se ejecutó ninguna sentencia SQL

#### Scenario: El 403 no depende del email

- **WHEN** la administración A tiene una persona sin vincular con el email `x@ejemplo.invalid` y una
  invitación enviada a ese email, y llega un token válido, sin vínculo, cuyo email es
  `x@ejemplo.invalid`
- **THEN** la respuesta es idéntica, en código, cuerpo y cabeceras salvo `X-Request-ID`, a la de un
  token válido sin vínculo con otro email, y no nombra a A

#### Scenario: Acceso en otra administración no es "sin acceso"

- **WHEN** una identidad vinculada en A sin asignaciones y en B con una asignación pide `GET /api/sesion`
- **THEN** la respuesta es 200 con B en la lista y sin A

#### Scenario: Dos personas con el mismo id de Clerk

- **WHEN** se intenta vincular en la misma administración un id de Clerk que ya tiene otra persona
- **THEN** la base rechaza la escritura y no queda nada escrito

#### Scenario: La misma identidad en dos administraciones

- **WHEN** un id de Clerk está vinculado a una persona de A y a otra de B
- **THEN** las dos filas existen y cada una sólo se usa con el tenant de su administración

### Requirement: Selector de administración después de autenticarse

Con un token válido, la identidad SHALL poder pedir la lista de las administraciones donde tiene una
persona vinculada con al menos una asignación, con su nombre, el de la persona y las acciones que esa
persona puede hacer en cada una (requisito "Las acciones permitidas viajan con la sesión" de
`autorizacion-por-rol`), y nada de otras administraciones. La lista MUST tener al menos una
administración: sin ninguna, la respuesta es el 403 `sin_acceso` del requisito anterior y la web MUST
NOT mostrar un selector vacío. Si la lista tiene una sola, la web MUST entrar directo; si tiene varias,
MUST mostrar "¿A cuál querés entrar?" antes de cualquier pantalla de dominio. La administración elegida
MUST viajar del servidor de la web a la API y la API MUST usarla sólo si la identidad verificada tiene
ahí una persona vinculada con asignación. Si no, o si la identidad tiene varias y no eligió ninguna, la
respuesta MUST ser 401 cuando la identidad tiene acceso en alguna administración, y el 403 `sin_acceso`
cuando no lo tiene en ninguna (precedencia del requisito anterior). El encabezado
`X-Proptech-Administracion` MUST leerse como texto y validarse como UUID sólo después del token y del
vínculo; un no UUID MUST responder 401 a una identidad con acceso, el 403 `sin_acceso` a una sin
acceso, y nunca 422.

#### Scenario: Una sola administración

- **WHEN** una identidad vinculada sólo en A entra
- **THEN** la web abre "Mis edificios" de A sin mostrar el selector

#### Scenario: Dos administraciones

- **WHEN** una identidad vinculada en A y en B entra
- **THEN** la web muestra el selector con A y B, y nada de otra administración

#### Scenario: Cero administraciones

- **WHEN** una identidad vinculada en A, cuya única asignación se quitó, abre `/elegir-administracion`
- **THEN** la web termina en la pantalla "Tu cuenta no tiene acceso todavía" y en ningún momento
  muestra un selector vacío

#### Scenario: Elegir una administración ajena

- **WHEN** una identidad vinculada con asignación sólo en A manda como elegida el id de B, una
  administración real
- **THEN** la respuesta es 401 y no se lee ningún dato de B

#### Scenario: Varias sin elegir

- **WHEN** una identidad vinculada con asignación en A y en B pide un complejo sin administración
  elegida
- **THEN** la respuesta es 401

#### Scenario: Selector con texto que no es UUID

- **WHEN** un pedido manda `X-Proptech-Administracion: no-es-uuid` sin token de sesión
- **THEN** responde 401 con cero SQL; con el token válido de una identidad con acceso también responde
  401, nunca 422

### Requirement: Ingresos auditados

Cada vez que una persona entra a una administración (con una sola, al autenticarse; con varias, al
elegirla) SHALL quedar una fila de auditoría `ingreso_exitoso` con esa persona y esa administración.
Cuando la API llega a elegir **una** persona (la única vinculada, o la de la administración del
selector) y esa persona no tiene ninguna asignación, MUST quedar una fila `ingreso_fallido` en su
administración, responda después 401 o 403. Cuando no llega a elegir ninguna (varias sin selector,
selector ajeno o que no es UUID), MUST NOT quedar ninguna fila `ingreso_fallido`. Un token válido sin
persona vinculada MUST dejar una línea de log con el evento y un resumen no reversible del id de Clerk,
sin email, sin nombre y sin el token. Los intentos con contraseña equivocada no llegan a la API: los
registra y los limita Clerk, y el sistema MUST NOT prometer auditarlos.

#### Scenario: Ingreso a una administración

- **WHEN** una persona vinculada con asignación en A entra a A
- **THEN** queda exactamente una fila `ingreso_exitoso` con su persona, A y el `request_id`

#### Scenario: Persona sin asignación

- **WHEN** una persona vinculada en A sin ninguna asignación, y sin vínculo en otra administración,
  presenta un token válido en una ruta de dominio
- **THEN** queda exactamente una fila `ingreso_fallido` en A y la respuesta es el 403 `sin_acceso`

#### Scenario: Identidad sin vínculo

- **WHEN** una identidad de Clerk sin vínculo presenta un token válido en una ruta de dominio
- **THEN** no queda ninguna fila de auditoría, el log tiene el evento sin email, sin token y sin el id
  de Clerk en claro, y la respuesta es el 403 `sin_acceso`

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
- **THEN** la respuesta es 404 con `X-Proptech-Origen: caddy`, armada por el bloque explícito de Caddy,
  y ni Next ni la API recibieron el pedido

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

### Requirement: Dependencia de Clerk para entrar y renovar

Si Clerk no responde, el sistema SHALL impedir nuevos ingresos y renovaciones. Un token ya emitido
MAY seguir verificándose sin red hasta `exp + 5`, unos 60 s más; MUST NOT extenderse localmente ni
ofrecerse un login propio de respaldo (E15).

#### Scenario: Clerk no responde

- **WHEN** Clerk deja de responder mientras hay un token de sesión ya emitido
- **THEN** no se puede entrar ni renovar, y el token deja de admitirse al llegar a `exp + 5`

### Requirement: Pantalla de cuenta sin acceso

Ante el 403 `sin_acceso`, desde cualquier pantalla, la web SHALL llevar a la persona a `/sin-acceso`,
sin `regreso`. La pantalla MUST titularse "Tu cuenta no tiene acceso todavía", MUST mostrar el email
principal de la sesión de Clerk (leído de Clerk en el navegador, nunca de la API ni de una prop del
servidor) si existe, MUST ofrecer "Cerrar sesión" y "Volver a intentar" y MUST NOT redirigir sola. Sin
sesión de Clerk MUST llevar a `/ingresar`.

#### Scenario: Cuenta de Clerk sin persona abre una pantalla de dominio

- **WHEN** una persona con sesión de Clerk válida y sin ninguna persona vinculada abre `/edificios`
- **THEN** termina en `/sin-acceso` en a lo sumo tres navegaciones, ve "Tu cuenta no tiene acceso
  todavía", y ninguna respuesta de la cadena es 431 ni lleva un `regreso` anidado

#### Scenario: Cuenta de Clerk sin persona entra por el ingreso

- **WHEN** esa misma persona completa el ingreso en `/ingresar` con el Clerk de desarrollo real
- **THEN** termina en `/sin-acceso`, no vuelve a `/ingresar`

#### Scenario: Cerrar sesión desde la pantalla sin acceso

- **WHEN** la persona elige "Cerrar sesión" en `/sin-acceso`
- **THEN** su sesión de Clerk se cierra y ve el formulario de `/ingresar`

#### Scenario: Volver a intentar después de que la vinculan

- **WHEN** después de ver `/sin-acceso` la persona queda vinculada con una asignación en A y elige
  "Volver a intentar"
- **THEN** entra a "Mis edificios" de A

#### Scenario: Una cuenta sin acceso acepta su invitación

- **WHEN** una cuenta sin acceso en ninguna administración abre su invitación de A, con su email, y la
  acepta
- **THEN** la aceptación responde 200, la persona de A queda vinculada y la web la lleva al selector, no
  a `/sin-acceso`

#### Scenario: Clerk sin email principal

- **WHEN** Clerk no informa un email principal para la sesión
- **THEN** la pantalla dice el mismo título y las mismas dos acciones, sin un email vacío ni "undefined"

#### Scenario: Sin sesión de Clerk

- **WHEN** se abre `/sin-acceso` sin sesión de Clerk
- **THEN** la web lleva a `/ingresar`

### Requirement: La pantalla sin acceso no pide la sesión

Al dibujarse, `/sin-acceso` SHALL NOT pedir nada a la API, ni `GET /api/sesion` ni ninguna otra ruta,
ni desde la página ni desde el layout de la web, cuya lista de rutas protegidas MUST NOT incluir nunca
`/sin-acceso`. Así un 403 `sin_acceso` no puede volver a llevar a la misma pantalla.

#### Scenario: La pantalla sin acceso no pide la sesión

- **WHEN** se dibuja `/sin-acceso` con una sesión de Clerk activa
- **THEN** no se hizo ningún pedido a la API, ni desde la página ni desde el layout

### Requirement: La pantalla sin acceso se usa con teclado y a 320 px

`/sin-acceso` SHALL ser operable sólo con teclado, con foco visible en cada acción, y MUST verse sin
desplazamiento horizontal a 320 px y en escritorio.

#### Scenario: Recorrer la pantalla con teclado

- **WHEN** la persona recorre `/sin-acceso` con Tab
- **THEN** llega a "Cerrar sesión" y a "Volver a intentar", cada una con foco visible, y las activa con
  Enter

#### Scenario: Pantalla angosta

- **WHEN** se abre `/sin-acceso` con un ancho de 320 px
- **THEN** el documento no tiene desplazamiento horizontal y el análisis automático de accesibilidad no
  informa violaciones

### Requirement: El selector no rebota al ingreso

`/elegir-administracion` SHALL NOT redirigir a `/ingresar` cuando `GET /api/sesion` responde 401 ni
cuando el servidor de la web no obtiene una sesión de Clerk utilizable (sin usuario o sin token): MUST
mostrar ahí "No pudimos validar tu sesión" con "Cerrar sesión". Las pantallas de dominio y su layout
MUST seguir llevando a `/ingresar` ante un 401. Ante el 403 `sin_acceso`, el selector MUST llevar a
`/sin-acceso`.

#### Scenario: La API rechaza un token que Clerk da por bueno

- **WHEN** la sesión de Clerk es válida en la web pero la API responde 401 a `GET /api/sesion` (por
  ejemplo, la API tiene otra clave de verificación)
- **THEN** `/elegir-administracion` muestra "No pudimos validar tu sesión" con "Cerrar sesión", la URL
  sigue siendo `/elegir-administracion` y no hubo ninguna redirección a `/ingresar`

#### Scenario: El selector sin sesión utilizable

- **WHEN** el servidor de la web abre `/elegir-administracion` y la sesión de Clerk no trae usuario o no
  entrega token
- **THEN** la pantalla muestra "No pudimos validar tu sesión" con "Cerrar sesión" y no redirige a
  `/ingresar`

#### Scenario: Una pantalla de dominio con varias sin elegir

- **WHEN** una identidad vinculada con asignación en A y en B, sin administración elegida, abre
  `/edificios`
- **THEN** pasa por `/ingresar` una vez y termina en el selector con A y B

#### Scenario: Dos pestañas a la vez

- **WHEN** una persona con sesión de Clerk válida y sin persona vinculada abre `/ingresar` en dos
  pestañas a la vez, con el Clerk de desarrollo real
- **THEN** las dos terminan en `/sin-acceso` y ninguna respuesta de ninguna de las dos es 431

### Requirement: El regreso nunca apunta a una pantalla de acceso

El destino `regreso` SHALL ser siempre una ruta propia que no sea una pantalla de acceso. Un valor
cuya ruta, ya normalizada como URL y con sus secuencias `%XX` decodificadas, es `/ingresar`,
`/registrarse`, `/elegir-administracion` o `/sin-acceso` (o una ruta debajo de ellas), o uno que no es
ruta propia, MUST reemplazarse por `/edificios`. Normalizar dos veces MUST dar lo mismo que una. Las
rutas de `/invitacion/` MUST conservarse.

#### Scenario: El regreso trae el selector con su propio regreso

- **WHEN** llega `regreso=/elegir-administracion?regreso=%2Fedificios`
- **THEN** el destino es `/edificios`

#### Scenario: El regreso apunta al ingreso

- **WHEN** llega `regreso=/ingresar?regreso=/edificios` o `regreso=/sin-acceso`
- **THEN** el destino es `/edificios`

#### Scenario: El regreso disfrazado de otra forma

- **WHEN** llega `regreso=/ingresar/`, `regreso=/./elegir-administracion`,
  `regreso=/edificios/../ingresar` o `regreso=/%69ngresar`
- **THEN** el destino es `/edificios`

#### Scenario: El regreso de una invitación se conserva

- **WHEN** llega `regreso=/invitacion/abc`
- **THEN** el destino es `/invitacion/abc`

#### Scenario: Normalizar dos veces

- **WHEN** se normaliza cualquier valor de una lista que incluye las entradas de hoy, entradas no ASCII,
  entradas con `{` y entradas de 511 a 513 caracteres, y después se normaliza el resultado
- **THEN** los dos resultados son iguales

#### Scenario: El ciclo del ingreso no anida el regreso

- **WHEN** se encadenan 50 vueltas de "el selector manda al ingreso con su ruta como `regreso`" y "el
  ingreso con sesión de Clerk vuelve al destino de `forceRedirectUrl`", partiendo de `/edificios`
- **THEN** el largo de la URL es el mismo en todas las vueltas y ninguna URL tiene un `regreso` dentro
  de otro

### Requirement: El regreso tiene un tope de 512 caracteres

`regreso` SHALL reemplazarse por `/edificios` si el valor de entrada tiene más de 512 caracteres o si
su salida normalizada pasaría de 512. Un valor de exactamente 512 que cumple lo demás MUST conservarse.
El tope MUST mirar la salida, para que la normalización siga siendo idempotente aunque `new URL`
codifique caracteres no ASCII o `{`.

#### Scenario: El regreso en el borde del tope

- **WHEN** llega un `regreso` de 512 caracteres y otro de 513, los dos empezando con `/edificios/` y sólo
  con caracteres ASCII que `new URL` no recodifica
- **THEN** el de 512 se conserva tal cual y el de 513 da `/edificios`

#### Scenario: La salida normalizada pasa el tope

- **WHEN** llega `regreso=/edificios/` seguido de 100 `ñ` (111 caracteres de entrada, más de 512 una vez
  codificados)
- **THEN** el destino es `/edificios`, y normalizar ese resultado otra vez da `/edificios`
