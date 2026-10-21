## Context

Ver `proposal.md` (Why) y las fuentes que no se rediscuten acá: la exploración
`openspec/exploraciones/2026-10-20-roles-de-la-empresa-y-login.md` (puntos 1, 2 y 9), D-107, D-106,
D-099, D-096 (P18), D-036 y D-094, y la ficha 2b de `knowledge-base/12_fichas_de_changes.md`. Estado del
código al 21/10/2026 (HEAD `fc2a4c9`, árbol limpio):

- **`proptech_api/acceso.py`**: `identidad_actual()` levanta 401 siempre, sin tocar la base;
  `sesion_con_tenant` depende de ella y abre la sesión con `identidad.administracion_id`;
  `RutaConIdentidad` resuelve la identidad antes de entregar un error de parseo del cuerpo (D6 del 3a,
  RF-B-2). `Identidad` (`acceso/dominio/identidad.py`) es sólo `(administracion_id, persona_id)`.
- **`acceso/aplicacion/autorizacion.py`**: `existe_persona` y `cargar_asignaciones` (lee `rol,
  complejo_id, unidad_id, vinculo`, ya filtrado por RLS). La matriz de D-106 vive en
  `acceso/dominio/permisos.py` y no cambia en este diseño.
- **`persona`** (0003): `id`, `administracion_id`, `nombre`, `email` nulo, `CHECK email = lower(email)`,
  únicos `(administracion_id, id)` y `(administracion_id, email)`, aislada con
  `aislar_por_administracion` (política `persona_por_administracion` sobre `app.administracion_id`).
- **`auditoria`** (0004): `administracion_id` y `persona_id` `NOT NULL`, `accion` contra
  `accion_de_auditoria`, sólo agregar, dueña el rol de arranque. `registrar()` valida el detalle por
  acción con Pydantic (`extra="forbid"`). `@accion_sensible` guarda un caso por `Accion` en un `dict`:
  el segundo caso con la misma acción pisa al primero sin aviso (V2-7 del 2a).
- **El guardián del catálogo** (`tests/integracion/test_catalogo_rls.py`) exige que **todas** las
  políticas de una tabla tengan `current_setting` de dos argumentos en `qual` y en `with_check`: una
  política `FOR SELECT` (sin `with_check`) hoy lo hace fallar.
- **El barrido de rutas** (`_barrido_de_rutas.py` y `test_rutas_protegidas.py`) exige 401 sin SQL en
  toda ruta no pública; la lista pública explícita es `/api/salud`.
- **Infra**: la API y la web están sólo en la red `aplicacion` (`internal: true`): no salen a
  Internet. El worker es el único con salida (`salida_worker`, M18). Caddy publica `/api/*` hacia la API
  y el resto hacia la web. `infra/.env.example` tiene los nombres de las variables; el README, la tabla
  única de variables (2c).
- **Web**: Next 16.4, React 19.3; el servidor llama a la API por `PROPTECH_URL_API_INTERNA`
  (`lib/api/cliente.ts::pedirApi`), que ya traduce 401 a `sin_sesion`. No hay `proxy.ts` ni
  dependencia de Clerk.

**Lo que dice la documentación vigente de Clerk** (consultada el 21/10/2026; cada decisión de abajo
cita la página que la respalda):

- *Manual JWT verification* (`https://clerk.com/docs/guides/sessions/manual-jwt-verification`): el token
  llega en la cookie `__session` (mismo origen) o en `Authorization` (otro origen); se verifica con la
  clave pública (JWKS de la Backend API, `/.well-known/jwks.json` del Frontend API o la "JWKS Public
  Key" en PEM del panel, `CLERK_JWT_KEY`, verificación sin red); hay que validar RS256, firma, `exp`,
  `nbf` y que `azp` sea uno de los orígenes conocidos; con Organizations sin cuentas personales,
  rechazar `sts = pending`.
- *How Clerk works* (`https://clerk.com/docs/guides/how-clerk-works/overview`): `__client` es
  `HttpOnly` en el dominio del Frontend API; `__session` **no es `HttpOnly`** ("must be able to be
  accessed by client-side SDKs"), vive 60 segundos y se renueva cada 50; en apps con servidor, el
  vencimiento se resuelve con un *handshake* por redirección del navegador, sin llamada de servidor a
  servidor.
- *clerkMiddleware* (`https://clerk.com/docs/reference/nextjs/clerk-middleware`): en Next 16 el archivo
  es `proxy.ts`; opciones `jwtKey` (verificación sin red) y `authorizedParties`;
  `createRouteMatcher()` está **deprecado** a favor de chequear la autorización junto al recurso.
- *CSP headers* (`https://clerk.com/docs/guides/secure/best-practices/csp-headers`): `script-src` con el
  Frontend API, `https://challenges.cloudflare.com` y `https://*.protect.clerk.com`; `connect-src` con el
  Frontend API y `https://*.protect.clerk.com:*`; `img-src https://img.clerk.com`; `worker-src 'self'
  blob:`; `style-src 'unsafe-inline'`; `frame-src` con Cloudflare y `*.protect.clerk.com`;
  `clerkMiddleware` ofrece `contentSecurityPolicy` con `strict: true` y nonce por pedido en `x-nonce`.
- *User lockout* (`https://clerk.com/docs/guides/secure/user-lockout`): bloqueo **por cuenta**, no por
  IP; 10 intentos y una hora por defecto en instancias nuevas desde el 06/07/2026 (mínimo 5);
  desbloqueo desde el panel o por la Backend API.
- *Invitations* (`https://clerk.com/docs/guides/users/inviting`) y *createInvitation*
  (`https://clerk.com/docs/reference/backend/invitations/create-invitation`): `POST /v1/invitations` con
  `emailAddress`, `redirectUrl`, `publicMetadata`, `notify` (por defecto `true`), `ignoreExisting` (por
  defecto `false`), `expiresInDays` (por defecto 30); al entrar por el link, el email queda verificado;
  revocar no impide registrarse por otro lado.
- *Restricting access* (`https://clerk.com/docs/guides/secure/restricting-access`): en modo
  *Invite-only* nadie se registra sin invitación válida.
- *Webhooks* (`https://clerk.com/docs/guides/development/webhooks/overview`): eventos de usuario, sesión
  e invitación, firmados con Svix, entrega "al menos una vez" y **sin orden garantizado**; no hay evento
  de intento de ingreso fallido.
- *Customize session tokens* (`https://clerk.com/docs/guides/sessions/customize-session-tokens`): se
  suman claims desde el panel (por ejemplo, el email principal), con un límite de 1,2 KB.
- *Sign-up and sign-in options*
  (`https://clerk.com/docs/guides/configure/auth-strategies/sign-up-sign-in-options`): contraseña, código
  por email, link por email (el "link mágico") y passkeys, activables desde el panel.

## Goals / Non-Goals

**Goals:**

- Que una persona invitada pueda entrar a su administración y a su alcance con Clerk, y que ninguna otra
  forma de token, vínculo o encabezado le abra otra cosa.
- Que la base siga decidiendo toda autorización: Clerk sólo dice "este es el usuario `user_…` y verificó
  este email".
- Que el super admin pueda dar de alta y de baja al personal y a los vecinos sin pedirle nada a un
  programador, salvo la primera persona de una administración nueva.
- Que todo esto se pruebe sin llamar a Clerk: tokens firmados con claves locales y un Clerk falso que
  valida como el real.

**Non-Goals:**

- Ninguna celda nueva en la matriz de D-106 (E6).
- Ningún webhook de Clerk, ninguna Organization de Clerk, ningún rol ni metadato de Clerk usado para
  autorizar.
- Doble factor, borrado de usuarios en Clerk, portal del vecino (11), puerto de email propio (13).

## Cómo aplica cada lección

La tabla del proposal dice qué tarea cubre cada lección. Lo que cambia el diseño:

- **L-016 y L-017**: los tests de la política nueva y de la resolución de la identidad corren como
  `proptech_app`, con personas vinculadas en **dos** administraciones (incluida la misma identidad en
  las dos) y con UUID reales de la otra administración, nunca con textos que FastAPI ya rechaza.
- **L-018 y L-020**: la política de lectura por identidad se prueba por su efecto (leer y fallar al
  escribir como la app) y tiene su ataque propio: usarla para escribir, y que el valor de la variable de
  sesión sobreviva a la transacción.
- **L-007**: ningún mensaje de PyJWT, de `httpx` ni de Clerk llega a una respuesta, a la auditoría ni a
  un log; el log nombra el motivo con un código fijo (`token_vencido`, `firma_invalida`, …).
- **L-009**: la API y el worker leen la configuración de Clerk con el mismo módulo y las mismas reglas.
- **L-027**: el Clerk falso del worker valida método, ruta, `Authorization: Bearer`, `Content-Type` y la
  forma del cuerpo como la Backend API real; la API falsa de la web, los encabezados de sesión.
- **L-026 y L-028**: cada pantalla nueva se cierra mirándola en un navegador real a 320 y 1280 px, con
  las combinaciones de capas que tenga.
- **L-029 y L-030**: la convención de `tasks.md` separa lo que el constructor resuelve solo (orden,
  redacción, nombres internos) de lo que vuelve a Juani (un permiso, una restricción de base, un texto
  de pantalla nuevo, una variable de entorno nueva).

## Fronteras

- `acceso` gana dos casos de uso (resolver la identidad, aceptar una invitación) y la gestión de
  usuarios. **Frontera cruzada que ya existe** (RA-4 del 2.2a): `complejos/aplicacion/escritura.py`
  escribe `asignacion_rol`. La gestión nueva vive en `acceso/aplicacion/usuarios.py` y **no** importa
  `complejos`: para dar de alta un vecino recibe `complejo_id` y `unidad_id` ya resueltos por la API
  (que compone los dos módulos), y la FK compuesta de `asignacion_rol` frena una unidad de otro
  complejo. El test de fronteras sigue igual.
- El worker importa `acceso.aplicacion` (el caso de uso de envío) y un adaptador nuevo
  `acceso/adaptadores/clerk_http.py` detrás del puerto `ProveedorDeIdentidad` (`acceso/puertos.py`).
  La API no importa el adaptador.
- `compartido.base_de_datos` gana `abrir_sesion_por_identidad(fabrica, clerk_usuario_id)`: fija sólo
  `app.identidad_clerk` (con `set_config(..., true)`), nunca el tenant.
- **Ninguna FK nueva apunta a `auditoria`** (D-2 del 2a): `invitacion` no la referencia. Queda escrito
  como restricción del esquema en la spec de auditoría al archivar.

## Decisions

### D0 · Un solo change (E1)

Login y gestión de usuarios van juntos aunque sumen 27 tareas y `openspec/config.yaml` pida partir
desde unas veinte. El vínculo con Clerk nace de aceptar una invitación (D6): un change sólo de login no
deja entrar a nadie y no se puede verificar de punta a punta. Se compensa con bloques chicos, cada uno
con su verificación, y con el bloque de UI bloqueado por el `shape`.

**Descartado**: partir en `login` (bloques B a D y F) y `gestion-de-usuarios` (E y G). Se podría probar
el login con vínculos sembrados a mano, pero eso es una puerta de desarrollo más (la que E12 propone
cerrar). **Costo de revertir**: mover los bloques E y G a un change nuevo con su propia firma; nada del
código cambia de forma.

### D1 · La API verifica el token con PyJWT y la clave PEM (E2)

- `acceso/dominio/token.py::verificar_token_de_sesion(token, clave_publica, partes_autorizadas, ahora)`
  devuelve `TokenVerificado(sub, email_verificado | None)` o levanta `TokenInvalido(motivo)` con un
  motivo de una lista cerrada. Pura: recibe `ahora`, no lee el reloj ni el entorno.
- `jwt.decode(..., algorithms=["RS256"], options={"require": ["exp", "nbf", "sub", "azp", "iat"]},
  leeway=5)`; `azp` en la lista; `sub` con `^user_[A-Za-z0-9]{1,64}$` (ASCII, coincidencia completa,
  L-008); `sts` igual a `pending` se rechaza aunque hoy no se usen Organizations (*Manual JWT
  verification*). La lista de algoritmos fija cierra `none` y la confusión RS256/HS256.
- El token sale sólo de `Authorization: Bearer <token>`, con exactamente un espacio y un token; la
  cookie `__session` no se lee en la API (la API no está en el origen del navegador, D4).
- Configuración (`compartido/configuracion.py`): `CLERK_JWT_KEY` (PEM de clave pública RSA, opcional) y
  `CLERK_PARTES_AUTORIZADAS` (lista separada por comas de orígenes `https://…` o `http://localhost:…`,
  sin comodines). Sin `CLERK_JWT_KEY`, `identidad_actual` responde 401 a todo, como hoy, y la API loguea
  una vez `login_sin_configurar` al arrancar: así el humo y el CI arrancan sin claves. Una clave
  presente pero inválida (no PEM, no RSA, menor a 2048 bits) **no deja arrancar** (L-002).
- Dependencia nueva: `pyjwt[crypto]` con versión fijada.

**Descartado**: el SDK `clerk-backend-api` (`authenticate_request`, *clerk-sdk-python*). Hace lo mismo
pero arrastra `httpx` y la Backend API a la API, y su verificación depende de su versión. **Descartado**:
JWKS remoto con caché: obliga a darle salida a Internet a la API, que hoy no tiene. **Costo de
revertir**: cambiar el cuerpo de `verificar_token_de_sesion`; los tests (claves locales) siguen.
**Costo aceptado**: si Clerk rota la clave de la instancia, hay que cargar la nueva en `infra/.env` y
reiniciar; mientras tanto todo responde 401 (falla cerrada).

### D2 · El vínculo: `persona.clerk_usuario_id`, único por administración (E3)

- Migración `0019_vinculo_con_clerk`: columna `clerk_usuario_id text` nula, `CHECK` con la forma de D1,
  único `(administracion_id, clerk_usuario_id)` (un `NULL` no choca con otro). El índice sirve también a
  la búsqueda por identidad.
- Política nueva `persona_por_identidad_clerk` **`FOR SELECT`** sobre `persona`: `USING
  (clerk_usuario_id = nullif(current_setting('app.identidad_clerk', true), ''))`. Las políticas
  permisivas se suman con `OR`: con el tenant fijado se ve lo de siempre; sin tenant y con la identidad
  fijada, sólo las personas de esa identidad, de cualquier administración. `INSERT`, `UPDATE` y `DELETE`
  siguen bajo la política del tenant.
- El guardián del catálogo acepta exactamente estas políticas extra (nombre, tabla, `FOR SELECT`,
  `current_setting` de dos argumentos en `qual`, `with_check` nulo) y falla con cualquier otra.
- Resolver la identidad (`acceso/aplicacion/identidad.py::resolver`): con `abrir_sesion_por_identidad`
  lee `SELECT id, administracion_id FROM persona` (sólo esas dos columnas); elige la administración
  (D3); cierra esa sesión y abre la del tenant para `cargar_asignaciones`. Si no hay asignaciones, 401.

**"Única" acotada**: la ficha y el pedido dicen "columna nueva, única". Global contradice D-096 P18 y
D-099 (una cuenta por administración: la misma identidad de Clerk tiene una persona en A y otra en B).
Se propone única por administración y se declara como contradicción resuelta, a firmar en E3.

**Descartado**: una tabla directorio sin tenant (`identidad_clerk(clerk_usuario_id, administracion_id,
persona_id)`): sería la primera tabla con datos de una administración fuera de la RLS por tenant.
**Descartado**: una función `SECURITY DEFINER`: su dueño tendría que tener `BYPASSRLS` (hoy sólo
`proptech_respaldo`) o ser superusuario. **Costo de revertir**: `downgrade` de 0019 (borra la política,
el índice y la columna); sin datos reales, gratis; con personas vinculadas, se pierde el vínculo y hay
que volver a invitar.

### D3 · El selector y la administración elegida (E4)

- `GET /api/sesion` (con token, sin tenant): `{"persona": {"nombre"}, "administraciones": [{"id",
  "nombre"}]}` sólo de las administraciones donde la persona vinculada tiene al menos una asignación.
  Leer `administracion.nombre` exige el tenant de cada una: se abre una transacción por administración
  vinculada (son pocas; una persona típica tiene una).
- La web guarda la elegida en la cookie `proptech_administracion` (`HttpOnly`, `Secure` en producción,
  `SameSite=Lax`, `Path=/`), escrita por una acción de servidor sólo con un id que vino en `GET
  /api/sesion`. Con una sola administración, la escribe sin mostrar el selector.
- `pedirApi` manda `X-Proptech-Administracion: <id>` desde el servidor. La API: si la identidad tiene
  una sola administración, usa esa e **ignora** el encabezado; si tiene varias, usa el encabezado sólo si
  es una de las suyas; si no, 401. Nunca se lee un dato de la administración pedida antes de comprobar
  que es suya (la comprobación usa la lista que dio la política por identidad).
- `POST /api/sesion/ingreso` registra `ingreso_exitoso` (D8). La web lo llama una vez al fijar la
  administración (selector o entrada directa).

**Descartado**: Organizations de Clerk con "organización activa" en el token: resuelve el selector, pero
pone la pertenencia a una administración en Clerk, y la ficha dice "no delegar autorización a roles de
Clerk". **Descartado**: una sesión propia emitida por Next con la administración adentro (ver D4).
**Costo de revertir**: el encabezado y la cookie son dos puntos; la regla de "sólo si es suya" sigue.

### D4 · El token en el navegador, contra D-036 (E5)

**Contradicción**: D-036 dice "el servidor de Next guarda el token de sesión (el navegador nunca lo
ve)". Con Clerk, `__session` **no es `HttpOnly`** y lo leen los SDK del navegador (*How Clerk works*).
No se puede cumplir D-036 a la letra usando el SDK de Clerk en la web.

Se propone aceptarlo y compensar:

- **Caddy publica sólo `/api/salud`** hacia la API (`handle /api/salud`); toda otra ruta `/api/*` desde
  afuera responde 404 de Caddy. La web llama a la API por la red interna (como ya hace). Un token
  robado por un script en el navegador no tiene ruta para usarse contra la API, y vence en 60 segundos.
  Cierra además RF-B-4 del 3a (un anónimo ya no puede sondear métodos y rutas de la API).
- **CSP estricta con nonce** (D-036 decía que la seguridad depende de ese servidor intermedio): con
  `clerkMiddleware({ contentSecurityPolicy: { strict: true, directives: … } })`, las directivas de *CSP
  headers* y `default-src 'self'`, `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`,
  `form-action 'self'`. Sin `unsafe-eval`. `style-src 'unsafe-inline'` lo exige Clerk; se declara.
- El token nunca se pasa a un componente de cliente ni se escribe en un log de la web; un test recorre el
  HTML de una página autenticada buscándolo.

**Descartado**: una sesión propia `HttpOnly` emitida por el servidor de Next después de canjear el token
de Clerk (un BFF completo): cumple D-036 a la letra, pero hay que construir renovación, revocación y
cierre de sesión propios, que es justo lo que Clerk resuelve; y el `__session` igual existe en el
navegador mientras se usen los componentes de Clerk. **Costo de revertir**: volver a publicar `/api/*`
es una línea de Caddy; la CSP es una opción del middleware. Si se firma, al archivar se registra D-108
y D-036 lleva la marca "corregida en parte por D-108".

### D5 · Quién invita: sólo el super admin (E6)

El pedido dice "quién puede invitar sale de la matriz de D-106", y la matriz sólo le da
`invitar_usuarios_y_asignar_edificios` al super admin. Invitar personal, dar de alta vecinos, revocar y
quitar usan ese permiso. Orden de siempre: complejo o unidad → alcance (404) → permiso (403) → cuerpo.

**Tensión declarada**: el padrón lo opera todo administrador del edificio (`configurar_padron`), pero no
podrá dar de alta a sus vecinos. **Descartado**: una acción nueva `dar_de_alta_vecinos` para SA, AP y AE.
Es una celda nueva de la matriz, que reabre D-106; si Juani la quiere, es otra elección. **Costo de
revertir**: una fila de la matriz, su test de 144 a 153 celdas y el permiso de dos rutas.

### D6 · Aceptar la invitación: token propio + email verificado (E7)

- Al crear una invitación, la API genera 32 bytes aleatorios (`secrets.token_urlsafe(32)`), guarda en
  `invitacion.token_resumen` el SHA-256 y entrega el token **sólo** al trabajo de envío (por argumento
  del trabajo, que vive en Redis hasta que se envía; los logs de ARQ van sin argumentos desde el 1c). El worker arma `redirectUrl = <PROPTECH_URL_PUBLICA>/invitacion/<token>`.
- Clerk manda el mail; la persona se registra (en modo *Invite-only*, sólo con invitación, *Restricting
  access*) y vuelve a `/invitacion/<token>`. La página del servidor de Next llama a
  `POST /api/invitaciones/aceptar {"token"}` con el token de sesión.
- La API: verifica el token de sesión (D1); exige el claim `email` (claim personalizado con el email
  principal, *Customize session tokens*). SUPUESTO: en modo *Invite-only* el email principal de quien se
  registra por el link es el invitado, que Clerk da por verificado (*Invitations*); se verifica en la
  tarea 8.2. Busca la invitación por `token_resumen` con una política de lectura por resumen de
  token (`invitacion_por_token`, `FOR SELECT`, misma forma que D2, sobre `app.invitacion_token`); con la
  `administracion_id` de esa fila abre el tenant y, con `SELECT … FOR UPDATE` sobre la invitación,
  comprueba estado, vencimiento, email igual al de la persona, que la persona no tenga otro vínculo y
  que la identidad no tenga otra persona en esa administración. Escribe el vínculo, marca `aceptada` y
  audita, en una transacción. Toda falla: el mismo 404.
- El tenant sale de una fila que la base encontró por un secreto que sólo tiene el invitado, no de lo
  que mande el cliente: no contradice "la administración nunca sale del cliente".

**Descartado**: sólo el token (sin el email): un mail reenviado le daría la cuenta a quien lo reciba.
**Descartado**: el webhook `user.created` con `publicMetadata`: suma una ruta pública firmada con Svix,
entrega sin orden (*Webhooks*) y datos nuestros guardados en Clerk, contra "Clerk guarda sólo email y
nombre". **Costo de revertir**: el claim de email se quita del panel y se borra una comparación.

### D7 · El worker habla con Clerk (E8)

- Tabla `invitacion` (0020): `id`, `administracion_id`, `persona_id` (FK compuesta a `persona`),
  `estado` (`pendiente | enviada | aceptada | fallida | revocada`; "vencida" se calcula con `vence`),
  `token_resumen bytea` único, `clerk_invitacion_id text` nulo con `CHECK` de forma `^inv_[A-Za-z0-9]+$`,
  `vence timestamptz`, `creada_por` (FK compuesta a `persona`), `creada_en`; aislada por tenant más la
  política de D6. Una sola invitación no aceptada ni revocada por persona (índice único parcial): invitar
  de nuevo revoca la anterior.
- Trabajos ARQ `enviar_invitacion(administracion_id, invitacion_id, token)` y
  `revocar_invitacion_en_clerk(administracion_id, invitacion_id)`, con el tenant como argumento
  validado (2a) y la idempotencia del 1c: si la invitación ya no está `pendiente`, no llama a Clerk.
  Reintentos ante 429, 5xx y errores de red; 4xx definitivo → `fallida`. `expiresInDays` igual al
  vencimiento propio (7 días, parámetro en `config/parametros.yaml`), `notify: true`,
  `ignoreExisting: false` (ver Open Questions).
- Adaptador `clerk_http.py` con `httpx` (pasa a dependencia directa del backend), base
  `https://api.clerk.com/v1`, `CLERK_SECRET_KEY` como `SecretStr`, plazo de 10 s. Nunca loguea el
  cuerpo de Clerk: sólo el código de estado y un motivo fijo.
- La clave secreta vive en el worker y en la web (el SDK de Next la usa, SUPUESTO abajo); **nunca** en
  la API.

**Descartado**: que la API llame a Clerk dentro del pedido: le daría salida a Internet y haría depender
el 201 de un tercero. **Costo de revertir**: mover la llamada; el puerto queda igual.

### D8 · Qué se audita y qué no se puede (E9)

- `ingreso_exitoso`: `POST /api/sesion/ingreso`, actor la persona, entidad `persona`, detalle vacío.
- `ingreso_fallido`: en `identidad_actual`, cuando la persona vinculada no tiene asignaciones; actor la
  persona, en su administración, detalle `{"motivo": "sin_asignacion"}`, en una transacción propia
  confirmada antes de responder 401.
- Token válido sin vínculo: no hay administración ni persona (las columnas son `NOT NULL`), así que va a
  un log `ingreso_sin_vinculo` con `sub_resumen` (los primeros 12 caracteres hexadecimales del SHA-256
  del `sub`) y el `request_id`.
- Contraseña equivocada, cuenta bloqueada, link mágico vencido: pasan entre el navegador y Clerk y no
  llegan a la API (*How Clerk works*). Clerk no ofrece webhook de intento fallido (*Webhooks*). Quedan
  en Clerk; el sistema no promete auditarlos.

**Descartado**: una tabla de intentos sin tenant (otra excepción a la RLS para datos sin dueño).
**Costo de revertir**: borrar los dos valores del vocabulario con una migración (sólo si no hay filas).

### D9 · Límite de intentos (E10)

El de Clerk, por cuenta (*User lockout*): Juani lo deja en 10 intentos y una hora o lo ajusta en el
panel. Cumple "sin bloquear a todo un edificio" porque no es por IP. **Riesgo declarado**: alguien que
conoce el email de un vecino puede bloquearle la cuenta una hora; se desbloquea desde el panel.
**Descartado**: un límite propio por IP en Caddy (necesita un módulo que la imagen no trae) o en la API
(los intentos no pasan por la API). **Costo de revertir**: configuración del panel.

### D10 · Alta inicial (E11)

`python -m proptech_core.acceso.aplicacion.alta_inicial --administracion <nombre> --nombre <nombre>
--email <email>`, corrido por el operador con `docker compose run --rm api …`. Usa `proptech_app`
(las credenciales de la API), genera el id de la administración en el servidor, fija ese tenant y en
una transacción crea `administracion`, `persona`, `asignacion_rol` (`super_admin`), `invitacion` y la
fila `alta_inicial` (actor: la persona creada, porque el operador no es una persona del sistema); después
encola el envío. Falla sin escribir si el email o el nombre no pasan la validación de D-104.

**Supuesto a verificar en la tarea 5.1**: que `proptech_app` pueda insertar en `administracion` con el
tenant igual al id nuevo (la política es por `id`, `aislar_por_administracion(columna="id")`). Si no
tiene `INSERT` sobre esa tabla, la tarea frena y vuelve a Juani: sumar ese permiso es CRITICAL.

**Descartado**: correrlo como `proptech_migrador` (necesita `GRANT INSERT ON auditoria`, la firma
pendiente de `acceso-de-desarrollo`). **Costo de revertir**: borrar un comando.

### D11 · `acceso-de-desarrollo` (E12)

Con el login, la puerta sin login sobra y es una puerta más que puede llegar a producción. Se propone:
cerrar el acceso de desarrollo (no construir `backend/desarrollo/`, ni `compose.desarrollo.yaml`) y
reducir el change a la carga del ejemplo, reescrita sobre el camino de D10 (como `proptech_app` con el
tenant de la administración de ejemplo, con su super admin), sin `GRANT INSERT ON auditoria` al
migrador. Para recorrer las pantallas con el ejemplo, se entra con Clerk de desarrollo. La tarea 9.1
reescribe los artefactos de ese change; ese change sigue necesitando su propia firma.

**Descartado**: mantenerlo como está (dos caminos para entrar y un `GRANT` CRITICAL que ya no hace
falta). **Costo de revertir**: el change sigue en `openspec/changes/`; volver a su versión es `git`.

### D12 · Pantallas: Clerk prearmado para ingresar (E13)

`/ingresar` y `/registrarse` usan `<SignIn/>` y `<SignUp/>` de `@clerk/nextjs` con
`@clerk/localizations` en castellano y `appearance` con los tokens de `DESIGN.md`; contraseña, link por
email y recuperación los resuelve Clerk. Son nuestras: el selector, aceptar invitación, el aviso de
privacidad, la barra superior, personal y vecinos del padrón. Todas esperan el `shape` (tarea 7.0).

**Descartado**: un formulario propio con `useSignIn`: más código sobre la parte más sensible y sin
ganancia para el vecino. **Costo de revertir**: reemplazar dos páginas.

### D13 · Vocabulario de auditoría (E14)

`accion_de_auditoria` (migración 0020) suma `ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`,
`invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion` y
`quitar_asignacion`. En el dominio son `EventoDeAcceso`, separado de `Accion` (que sigue siendo la
matriz): `registrar()` acepta los dos. Cada uno con su modelo de detalle (`persona_id` destinataria,
`asignacion_id`, `rol` y `alcance` donde corresponda; nunca email). **V2-7**: `@accion_sensible` pasa a
fallar al registrar un segundo caso con la misma acción o evento, y el test que no podía dar rojo
(`test_auditoria_transaccion.py:416`) se reescribe para verlo rojo.

**Descartado**: sumar los ocho a `Accion`: agrega ocho filas "No" a la matriz y mezcla qué se puede
hacer con qué pasó. **Costo de revertir**: mover valores de un enum a otro; la base no cambia.

## Configuración y secretos

| Variable | Servicio | Secreta | Notas |
|---|---|---|---|
| `CLERK_JWT_KEY` | `api`, `web` | No (clave pública), pero sale del entorno | PEM. Sin ella, login apagado |
| `CLERK_PARTES_AUTORIZADAS` | `api`, `web` | No | Orígenes del sitio, separados por comas |
| `CLERK_SECRET_KEY` | `worker`, `web` | **Sí** | `SecretStr` en el worker; nunca en la API |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `web` (al construir la imagen) | No | Se inyecta como argumento de construcción |
| `PROPTECH_URL_PUBLICA` | `worker`, `web` | No | Base de la dirección de regreso de la invitación |

Todas se leen de `infra/.env`, que carga Juani y nunca entra al repo. `infra/.env.example` y la tabla del
README las nombran sin valores. El CI y el humo arrancan sin `CLERK_JWT_KEY` ni `CLERK_SECRET_KEY` (login
apagado) y con una clave publicable de prueba con forma válida e inventada, que no es secreta (SUPUESTO
abajo).

## Lo que Juani hace en Clerk (tarea 8.1)

1. Crear la cuenta y una aplicación en modo desarrollo (la de producción, con dominio propio y DNS, es
   del 15).
2. Sign-up mode **Invite-only**; métodos: email con contraseña y **link por email**; sin proveedores
   sociales; nombre opcional o desactivado (Clerk guarda sólo email y nombre, D-107).
3. Protecciones: bloqueo de cuenta (10 intentos, una hora, o lo que decida).
4. Sessions → Customize session token: claim `email` con el email principal.
5. Copiar a `infra/.env`: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWT_KEY`
   (la "JWKS Public Key" en PEM) y `CLERK_PARTES_AUTORIZADAS` (por ejemplo `http://localhost`).
6. Revisar el precio vigente antes del piloto (D-107).

## Risks / Trade-offs

- [El `__session` es legible desde el navegador] → D4: 60 s de vida, la API no alcanzable desde
  afuera, CSP con nonce. Riesgo residual: un script inyectado puede actuar como la persona **a través de
  la web** mientras dure la página; es el mismo riesgo de cualquier sesión con XSS.
- [Política de lectura por identidad en `persona`] → `FOR SELECT`, sólo `id` y `administracion_id` en
  la consulta, guardián que acepta exactamente esa política, ataques de L-020.
- [La clave pública rota en Clerk] → falla cerrada (401) hasta cargar la nueva; se nota en el primer
  ingreso.
- [Bloqueo de cuenta como molestia] → D9.
- [La web sin salida a Internet] → SUPUESTO: `clerkMiddleware` con `jwtKey` no necesita llamar a Clerk
  desde el servidor (el handshake pasa por el navegador, *How Clerk works*). Dato que lo discrimina, en
  la tarea 8.2: con la web sólo en `aplicacion`, el ingreso real funciona y el log de la web no tiene
  ningún error de conexión hacia `clerk`; si aparece, la web necesita una red de salida (decisión de
  Juani).
- [Sin claves en el CI] → el login apagado responde 401 como hoy; la web arranca con una clave publicable
  de prueba. SUPUESTO: `@clerk/nextjs` arranca con una clave publicable con forma válida aunque la
  instancia no exista; dato que lo discrimina: `humo.sh` en verde con la web sana.
- [27 tareas] → D0.
- [Las pruebas de navegador con sesión] → SUPUESTO: Playwright arma una sesión de prueba poniendo un
  `__session` firmado con la clave local (la misma que recibe `jwtKey` en la corrida de prueba) y un
  `__client_uat` coherente, sin llamar a Clerk. Dato que lo discrimina, en la tarea 6.1: una página
  autenticada abre sin redirigir al *handshake*. Si redirige, **no** se agrega ninguna variable que
  saltee la sesión (sería la puerta que E12 cierra): vuelve a Juani.

## Migration Plan

1. Con la aprobación firmada, construir por bloques. `alembic upgrade head` corre 0019 y 0020 en el
   arranque, como siempre.
2. **Rollback**: `downgrade` de 0020 (borra `invitacion`, su política y los ocho valores del vocabulario;
   falla ruidoso si hay filas de auditoría con esos valores, porque la auditoría no se puede borrar) y de
   0019 (borra la política, el índice y la columna). Con personas ya vinculadas, volver atrás pierde el
   vínculo: se restaura un respaldo.
3. Caddy: revertir `handle /api/salud` a `handle /api/*`.
4. **Supuesto declarado (RD-2 del 2.2a, sigue en pie)**: no hay producción ni datos reales. El ensayo de
   0019/0020 sobre la copia restaurada del humo (tarea 3.3) usa los mismos pasos que el 2.2a.

## Open Questions

- **Una invitación a un email que ya tiene usuario en Clerk** (el vecino con unidades en dos
  administraciones, o el administrador que también es vecino). Con `ignoreExisting: false` Clerk
  rechaza crearla; con `true` la crea, pero no está documentado si el link lleva a registrarse (y falla
  porque el usuario existe) o a ingresar. Dato que lo discrimina, en la tarea 8.2: invitar en la
  instancia de desarrollo a un email ya registrado y ver a qué pantalla lleva el link. Si lleva a
  ingresar y vuelve a la dirección de regreso, alcanza con `ignoreExisting: true`; si no, hace falta
  otro camino (mostrar las invitaciones pendientes después de ingresar, con el token igual de un solo
  uso), que vuelve a Juani antes de construirse.
- **Doble factor para el personal**: Clerk lo ofrece; activarlo es una decisión de producto.
- **Borrar el usuario de Clerk** cuando se le quita la última asignación en todas sus administraciones.
- **El texto legal del aviso de privacidad**: el constructor arma un borrador con lo que exige la ley
  25.326; lo aprueba Juani antes de publicarlo (tarea 7.2).
