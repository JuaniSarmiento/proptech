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
- [Shortcodes de Clerk](https://clerk.com/docs/guides/sessions/jwt-templates#shortcodes) y
  [personalización del token de sesión](https://clerk.com/docs/guides/sessions/customize-session-tokens)
  (revisadas el 21/10/2026, RB2b-3): permiten `{{user.primary_email_address}}` y
  `{{user.email_verified}}`, conservando el tipo booleano. Se configuran como `email` y
  `email_verified` en el token de sesión, no en un JWT separado. La aceptación exige el booleano
  `true`; tener sólo `email` no prueba la verificación. La prueba real 8.2 comprueba el par sobre el
  email principal, también con otro email secundario verificado, antes de habilitar el flujo.
- [Claims del token de sesión](https://clerk.com/docs/guides/sessions/session-tokens#default-claims):
  `iss` es la URL del Frontend API de la instancia. D1 exige coincidencia exacta con la configurada.
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
  complejo. El test de fronteras conserva esas reglas y suma que `proptech_api` no importe
  `acceso.adaptadores`, incluido el cliente HTTP de Clerk (RA2b-6).
- El worker importa `acceso.aplicacion` (el caso de uso de envío) y un adaptador nuevo
  `acceso/adaptadores/clerk_http.py` detrás del puerto `ProveedorDeIdentidad` (`acceso/puertos.py`).
  La API no importa el adaptador.
- `compartido.base_de_datos` gana `abrir_sesion_por_identidad(fabrica, clerk_usuario_id)`: fija sólo
  `app.identidad_clerk` (con `set_config(..., true)`), nunca el tenant.
- El reset del pool (`base_de_datos.py:186-196`) limpia `app.administracion_id`,
  `app.identidad_clerk` y `app.invitacion_token`, también después de un `SET` accidental sin `LOCAL`.
  Conserva el manejo de conexión nula o rota. La tarea 3.1 lo prueba con un pool de una conexión.
- **Ninguna FK nueva apunta a `auditoria`** (D-2 del 2a): `invitacion` no la referencia. Queda escrito
  como restricción del esquema en la spec de auditoría al archivar.

## Decisions

### D0 · Un solo change (E1)

Login y gestión de usuarios van juntos aunque sumen 28 tareas y `openspec/config.yaml` pida partir
desde unas veinte. El vínculo con Clerk nace de aceptar una invitación (D6): un change sólo de login no
deja entrar a nadie y no se puede verificar de punta a punta. Se compensa con bloques chicos, cada uno
con su verificación, y con el bloque de UI bloqueado por el `shape`.

**Descartado**: partir en `login` (bloques B a D y F) y `gestion-de-usuarios` (E y G). Se podría probar
el login con vínculos sembrados a mano, pero eso es una puerta de desarrollo más (la que E12 propone
cerrar). **Costo de revertir**: mover los bloques E y G a un change nuevo con su propia firma; nada del
código cambia de forma.

### D1 · La API verifica el token con PyJWT y la clave PEM (E2)

- `acceso/dominio/token.py::verificar_token_de_sesion(token, clave_publica, partes_autorizadas, emisor, ahora)`
  devuelve `TokenVerificado(sub, email | None, email_verificado: bool)` o levanta `TokenInvalido(motivo)` con un
  motivo de una lista cerrada. Pura: recibe `ahora`, no lee el reloj ni el entorno.
- PyJWT **2.15** no recibe un reloj inyectado. `jwt.decode(..., algorithms=["RS256"], issuer=emisor,
  options={"require": ["exp", "nbf", "sub", "azp", "iat", "iss"], "verify_exp": False,
  "verify_nbf": False, "verify_iat": False})` verifica la firma y el emisor. Después se validan
  `exp`, `nbf` e `iat` a mano contra `ahora` UTC inyectado, con `leeway = 5` segundos: son enteros
  Unix (no booleanos ni texto); se rechaza si `ahora >= exp + leeway`, `ahora < nbf - leeway` o
  `iat > ahora + leeway`. No se consulta la hora real ni se simula que pasar `ahora` a PyJWT funciona.
  La tarea 2.1 prueba `ahora = exp - leeway - 1` y `exp - leeway` (válidos, con `nbf` e `iat`
  anteriores), `exp + leeway + 1` (inválido), y el corte real `exp + leeway - 1` (válido) y
  `exp + leeway` (inválido); para `nbf`, `nbf - leeway - 1` (inválido) y `nbf - leeway` (válido).
  `azp` en la lista; `sub` con `^user_[A-Za-z0-9]{1,64}$` (ASCII, coincidencia completa,
  L-008); `sts` igual a `pending` se rechaza aunque hoy no se usen Organizations (*Manual JWT
  verification*). La lista de algoritmos fija cierra `none` y la confusión RS256/HS256.
- El token sale sólo de `Authorization: Bearer <token>`, con exactamente un espacio y un token; la
  cookie `__session` no se lee en la API (la API no está en el origen del navegador, D4).
- Configuración (`compartido/configuracion.py`): `CLERK_JWT_KEY` (PEM de clave pública RSA, opcional) y
  `CLERK_PARTES_AUTORIZADAS` (lista separada por comas de orígenes `https://…` o `http://localhost:…`,
  sin comodines) y `CLERK_EMISOR` (URL exacta del Frontend API de la instancia, obligatoria con clave).
  `iss` ausente o distinto se rechaza aunque la firma y `azp` sean válidos. Sin `CLERK_JWT_KEY`,
  las dos guardas de D3 responden 401 a todo, como hoy, y la API loguea
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
  único **`(clerk_usuario_id, administracion_id)`** (un `NULL` no choca con otro). Ese orden sirve a
  `SELECT id, administracion_id FROM persona WHERE clerk_usuario_id = :sub`, incluso sin tenant.
  3.1 adjunta el `EXPLAIN` real como `proptech_app`, con RLS y datos de dos administraciones.
- Política nueva `persona_por_identidad_clerk` **`FOR SELECT`** sobre `persona`: `USING
  (clerk_usuario_id = nullif(current_setting('app.identidad_clerk', true), '') AND
  nullif(current_setting('app.administracion_id', true), '') IS NULL)`. Las políticas
  permisivas se suman con `OR`: con el tenant fijado se ve lo de siempre; sin tenant y con la identidad
  fijada, sólo las personas de esa identidad, de cualquier administración. `INSERT`, `UPDATE` y `DELETE`
  siguen bajo la política del tenant. Si ambas variables están fijadas, esta política no aporta filas:
  sólo quedan las del tenant. RLS filtra **filas, no columnas**: el rol podría leer todas las columnas
  de las filas visibles; seleccionar sólo dos columnas es una minimización de la consulta.
- El guardián conserva intacta su regla actual para las políticas ordinarias: `current_setting` del
  tenant con dos argumentos en `qual` **y** en `with_check`. Suma una lista blanca exacta de dos tuplas:
  (`public.persona`, `persona_por_identidad_clerk`, `cmd = SELECT`, `PERMISSIVE`, roles `{public}`,
  `qual` completo de este punto, `with_check = NULL`) y (`public.invitacion`, `invitacion_por_token`,
  `cmd = SELECT`, `PERMISSIVE`, roles `{public}`, `qual` completo de D6, `with_check = NULL`). Compara
  la expresión completa devuelta por `pg_get_expr` contra la expresión esperada normalizada por
  PostgreSQL, sin aceptar sólo que contenga `current_setting`. Todo lo demás sigue por la regla
  actual; una política de sólo lectura en otra tabla o con otro `qual` falla nombrando tabla y política.
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
- Hay dos guardas explícitas: `token_de_sesion_actual(request) -> TokenVerificado` verifica D1 sin
  SQL; `identidad_actual(token = Depends(token_de_sesion_actual), …) -> Identidad` resuelve además
  persona, administración y asignaciones. Sólo `GET /api/sesion` y `POST /api/invitaciones/aceptar`
  declaran `Depends(token_de_sesion_actual)` sin exigir persona completa. Nunca entran en
  `_RUTAS_PUBLICAS`, que sigue siendo sólo `/api/salud`.
- `RutaConIdentidad` elige una guarda declarada en la clase de ruta: `_exigir_identidad` para dominio;
  su variante `RutaConTokenVerificado` usa `_exigir_token` con
  `Depends(token_de_sesion_actual)` para esas dos rutas. Ante JSON roto ejecuta esa misma guarda con
  el solver y los overrides antes de entregar el error; para aceptar, con token válido, normaliza ese
  error a 422 como D6. Un cuerpo bien parseado sigue el árbol normal y autentica una sola vez. El
  barrido inspecciona las dos dependencias, verifica la lista exacta de excepciones con token y exige
  **401 y cero SQL** sin token también en ellas, con cuerpo correcto, ausente y roto (tarea 4.4).
- La web guarda la elegida en la cookie `proptech_administracion` (`HttpOnly`, `Secure` en producción,
  `SameSite=Lax`, `Path=/`), escrita por una acción de servidor sólo con un id que vino en `GET
  /api/sesion`. Con una sola administración, la escribe sin mostrar el selector.
- `pedirApi` manda `X-Proptech-Administracion: <id>` desde el servidor. Se lee como **texto**, nunca
  como un parámetro UUID de FastAPI: primero se verifica el token, después se resuelve el vínculo y
  recién entonces se valida el UUID. Un valor no UUID devuelve 401, nunca 422 antes de la identidad.
  Si falta y hay una sola administración, usa esa; si está presente, lo usa sólo si
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

- **Caddy publica sólo `/api/salud`** hacia la API (`handle /api/salud`); después declara
  `handle /api/* { respond 404 }`, con `header X-Proptech-Origen caddy` dentro de ese bloque. El bloque
  de la web queda al final. Toda otra ruta `/api/*` desde afuera responde 404 con esa marca de origen,
  sin pasar a Next ni a FastAPI; el humo comprueba estado y marca. La web llama a la API por la red interna. Un token
  robado por un script en el navegador no tiene ruta para usarse contra la API, y vence en 60 segundos.
  Cierra además RF-B-4 del 3a (un anónimo ya no puede sondear métodos y rutas de la API).
- **CSP estricta con nonce** (D-036 decía que la seguridad depende de ese servidor intermedio): con
  `clerkMiddleware({ contentSecurityPolicy: { strict: true, directives: … } })`, las directivas de *CSP
  headers* y `default-src 'self'`, `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`,
  `form-action 'self'`. Sin `unsafe-eval`. `style-src 'unsafe-inline'` lo exige Clerk; se declara.
  Implementación del constructor (6.2): el SDK fijado conserva `unsafe-inline` en scripts aun con
  `strict`. Se quitan ambas palabras de `script-src` en las CSP de respuesta y de petición hacia
  Next, conservando el nonce automático y `ClerkProvider dynamic`.
- El token nunca se pasa a un componente de cliente ni se escribe en un log de la web; un test recorre el
  HTML de una página autenticada buscándolo.

**Descartado**: una sesión propia `HttpOnly` emitida por el servidor de Next después de canjear el token
de Clerk (un BFF completo): cumple D-036 a la letra, pero hay que construir renovación, revocación y
cierre de sesión propios, que es justo lo que Clerk resuelve; y el `__session` igual existe en el
navegador mientras se usen los componentes de Clerk. **Costo de revertir**: volver a publicar `/api/*`
exige quitar el bloqueo y restaurar el proxy de Caddy; la CSP es una opción del middleware. Pasar más adelante a un BFF con sesión
`HttpOnly` exige construir el canje, la renovación, la revocación y el cierre propios, reemplazar el
uso de la sesión de Clerk en Next y migrar las sesiones abiertas con sus pruebas. Si se firma, al archivar se registra D-108
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
  `invitacion.token_resumen` sólo el SHA-256 y cifra el token en un sobre autenticado AES-256-GCM
  (nonce aleatorio de 12 bytes, versión y vencimiento autenticados). `INVITACIONES_CLAVE_CIFRADO` es
  una clave propia de 32 bytes, sólo de la API, nunca la clave de Clerk. El cifrado usa
  `cryptography` como dependencia directa fijada, sin implementar primitivas propias. El sobre codificado en base64url
  es el mínimo dato de entrega: ARQ recibe los dos ids y ese sobre, nunca el token crudo ni el email.
  El worker lo transporta sin descifrar en
  `redirect_url = <PROPTECH_URL_PUBLICA>/invitacion/<sobre>`. El resumen tampoco se usa como
  credencial. El sobre sigue siendo un secreto de un solo uso: no se loguea, la página no carga
  terceros, responde `Cache-Control: no-store` y `Referrer-Policy: no-referrer`, y limpia la URL al
  terminar. Cifrar evita transportar el token crudo, no elimina el riesgo de copiar el enlace.
- Clerk manda el mail; la persona se registra (en modo *Invite-only*, sólo con invitación, *Restricting
  access*) y vuelve a `/invitacion/<sobre>`. La página del servidor de Next llama a
  `POST /api/invitaciones/aceptar {"token": "<sobre>"}` con el token de sesión. La API autentica,
  valida la forma del cuerpo y recién entonces abre el sobre, comprueba su autenticidad y vencimiento
  y calcula el resumen del token recuperado; el token crudo sólo existe en memoria de la API.
- La API exige `email` no vacío y **`email_verified is True`**, ambos claims firmados del token de
  sesión (fuentes de RB2b-3 en Context). No acepta `"true"`, valores ausentes ni un email secundario
  como prueba del principal. Compara `email.lower()` con el email de la persona, guardado en minúsculas.
  Busca la invitación por `token_resumen` con `invitacion_por_token`, `FOR SELECT`, cuyo `qual` completo
  es `token_resumen = decode(nullif(current_setting('app.invitacion_token', true), ''), 'hex') AND
  nullif(current_setting('app.administracion_id', true), '') IS NULL`. `app.invitacion_token` lleva
  **los 64 caracteres hexadecimales del SHA-256**, nunca el token crudo ni el sobre. La búsqueda
  `SELECT id, administracion_id FROM invitacion WHERE token_resumen = :resumen` usa el único del
  resumen (3.2 adjunta `EXPLAIN` como `proptech_app`). Esta sesión sin tenant se cierra; con la
  `administracion_id` de esa fila abre el tenant y, con `SELECT … FOR UPDATE` sobre la invitación,
  comprueba estado, vencimiento, email igual al de la persona, que la persona no tenga otro vínculo y
  que la identidad no tenga otra persona en esa administración. Escribe el vínculo, marca `aceptada` y
  audita, en una transacción. Se vuelve a comprobar el resumen bajo el bloqueo. Cualquier falla de
  aceptación, incluso sobre alterado o email no verificado: 404 con `{"detail":"no encontrado"}`,
  sin repetir datos y sin escribir. La política por resumen filtra filas, no columnas; con tenant
  fijado no aporta filas ajenas, aunque el resumen corresponda a otra administración.
- **Contrato completo del endpoint** (RB2b-4): sin token de sesión válido, 401 idéntico a D1 antes
  de mirar el cuerpo o ejecutar SQL; con sesión válida y sin `token`, JSON roto, cuerpo de otra forma,
  `token` que no sea texto o campos extra, 422 que nombra el campo sin repetir valores. Con cuerpo
  válido, los rechazos de aceptación son el 404 anterior; éxito, 200 con `{"aceptada":true}`. La
  guarda es la de token sin persona de D3, también para el JSON roto, nunca `identidad_actual`.
- El tenant sale de una fila que la base encontró por un secreto que sólo tiene el invitado, no de lo
  que mande el cliente: no contradice "la administración nunca sale del cliente".

**Descartado**: sólo el token (sin el email): un mail reenviado le daría la cuenta a quien lo reciba.
**Descartado**: el webhook `user.created` con `publicMetadata`: suma una ruta pública firmada con Svix,
entrega sin orden (*Webhooks*) y datos nuestros guardados en Clerk, contra "Clerk guarda sólo email y
nombre". **Costo de revertir**: quitar los dos claims y sus comparaciones; retirar el cifrado exige
reemplazar los enlaces ya enviados. Rotar la clave del sobre invalida los enlaces anteriores: se vuelve
a invitar.

### D7 · El worker habla con Clerk (E8)

- Tabla `invitacion` (0020): `id`, `administracion_id`, `persona_id` (FK compuesta a `persona`),
  `estado` (`pendiente | enviada | aceptada | fallida | revocada`; "vencida" se calcula con `vence`),
  `token_resumen bytea` único, `clerk_invitacion_id text` nulo con `CHECK` de forma `^inv_[A-Za-z0-9]+$`,
  `vence timestamptz NOT NULL`, `creada_por` (FK compuesta a `persona`), `creada_en`; aislada por tenant más la
  política de D6. `ix_invitacion_persona (administracion_id, persona_id)` sirve al historial y al
  listado de personal con su invitación; `uq_invitacion_abierta (administracion_id, persona_id)
  WHERE estado IN ('pendiente','enviada','fallida')` sirve a buscar la invitación abierta y asegura
  una sola por persona. Reinvitar bloquea la persona, revoca primero la anterior y después inserta
  la nueva en la misma transacción (5.2). La vencida sigue ocupando ese único hasta revocarse.
  No se limpian ni purgan invitaciones viejas en este cambio; el historial sigue en la tabla.
- Trabajos ARQ `enviar_invitacion(administracion_id, invitacion_id, sobre)` y
  `revocar_invitacion_en_clerk(administracion_id, invitacion_id)`, con el tenant como argumento
  validado (2a) y la idempotencia del 1c: si la invitación ya no está `pendiente`, no llama a Clerk.
  Reintentos ante 429, 5xx y errores de red; 4xx definitivo → `fallida`. `expiresInDays` igual al
  vencimiento propio (7 días, parámetro en `config/parametros.yaml`), `notify: true`,
  `ignoreExisting: false` (ver Open Questions).
- Retención ARQ (RB2b-7): `_expires=3600` desde el encolado original, reintentos sin renovar ese
  plazo, `job_timeout=30`, `keep_result=0` y sin conservar resultados de fallas. Se borran los datos
  del trabajo al terminar; si nunca corre, expiran a la hora, y un intento ya iniciado puede retenerlos
  hasta 30 s más. Límite total: **3630 s**, no los siete días de la invitación. Se prueba el TTL real
  en Redis y el borrado tras éxito, rechazo y agotamiento, incluidos los reintentos. Logs, resultados
  y excepciones no contienen argumentos, email, token, sobre ni cuerpo de Clerk. Los ids bastan para
  la revocación; no se le manda el sobre. Si expira el trabajo antes de enviarse, la invitación queda
  fallida y se vuelve a invitar; no se reconstruye el token desde su resumen.
- Adaptador `clerk_http.py` con `httpx` (pasa a dependencia directa del backend), base
  `https://api.clerk.com/v1`, `CLERK_SECRET_KEY` como `SecretStr`, plazo de 10 s. Nunca loguea el
  cuerpo de Clerk: sólo el código de estado y un motivo fijo.
- La clave secreta de Clerk vive en el worker y en la web (el SDK de Next la usa, SUPUESTO abajo); **nunca** en
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

**Permiso existente, no supuesto** (RD2b-5, RA2b-3): `proptech_app` ya tiene `INSERT` en
`administracion` (`roles.py` y 0003); la política usa `id`, con el tenant igual al id nuevo. No hace
falta rol ni `GRANT` nuevo. Esto no restringe la creación al comando: **cualquier camino de la API
que use el rol de la aplicación puede fijar un tenant nuevo y crear administraciones**. E11 acepta
ese alcance existente; restringirlo al operador requeriría otra decisión CRITICAL, con su firma.

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

### D14 · Dependencia de Clerk para entrar y renovar (E15)

Si Clerk no responde, nadie puede entrar ni renovar la sesión (unos 60 s): se acepta la dependencia.
La verificación local de un token ya emitido sigue hasta `exp + leeway`; no se extiende su vida ni se
saltea la verificación. **Descartado**: un login propio de respaldo. Su costo es custodiar contraseñas,
recuperación, bloqueo de cuentas, renovación y revocación, además de mantener dos caminos de acceso.
**Costo de revertir**: construir y auditar ese sistema, migrar las cuentas y obtener una nueva firma
CRITICAL; no alcanza con un interruptor de configuración.

## Configuración y secretos

| Variable | Servicio | Secreta | Notas |
|---|---|---|---|
| `CLERK_JWT_KEY` | `api`, `web` | No (clave pública), pero sale del entorno | PEM. Sin ella, login apagado |
| `CLERK_PARTES_AUTORIZADAS` | `api`, `web` | No | Orígenes del sitio, separados por comas |
| `CLERK_EMISOR` | `api` | No | URL exacta del Frontend API de la instancia; obligatoria con clave |
| `INVITACIONES_CLAVE_CIFRADO` | `api` | **Sí** | 32 bytes en base64, `SecretStr`; obligatoria para invitar; nunca Clerk ni ARQ |
| `CLERK_SECRET_KEY` | `worker`, `web` | **Sí** | Servidor de Next y worker (`SecretStr`); nunca en la API ni el navegador; E16 firmada |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `web` (al construir la imagen) | No | Se inyecta como argumento de construcción |
| `PROPTECH_URL_PUBLICA` | `worker`, `web` | No | Base de la dirección de regreso de la invitación |

Todas se leen de `infra/.env`, que carga Juani y nunca entra al repo. `infra/.env.example` y la tabla del
README las nombran sin valores. E16, firmada por Juani el 21/10/2026: los tests y CI usan en Next
una `CLERK_SECRET_KEY` ficticia no válida contra Clerk y claves RSA locales para `jwtKey`. El humo
arranca con login de API apagado (sin `CLERK_JWT_KEY`) y su override de Compose entrega sólo a Next
la secreta ficticia. La clave publicable de prueba es inventada y nunca pertenece a una instancia.

## Lo que Juani hace en Clerk (tarea 8.1)

1. Crear la cuenta y una aplicación en modo desarrollo (la de producción, con dominio propio y DNS, es
   del 15).
2. Sign-up mode **Invite-only**; métodos: email con contraseña y **link por email**; sin proveedores
   sociales; nombre opcional o desactivado (Clerk guarda sólo email y nombre, D-107).
3. Protecciones: bloqueo de cuenta (10 intentos, una hora, o lo que decida).
4. Sessions → Customize session token: `{"email":"{{user.primary_email_address}}",
   "email_verified":"{{user.email_verified}}"}`. Comprobar que el segundo sale booleano, no texto,
   y describe el email principal. No usar una constante `true` ni `unsafe_metadata`.
5. Copiar a `infra/.env`: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWT_KEY`
   (la "JWKS Public Key" en PEM), `CLERK_PARTES_AUTORIZADAS` (por ejemplo `http://localhost`) y
   `CLERK_EMISOR` (URL del Frontend API de esa misma instancia). Generar y cargar también
   `INVITACIONES_CLAVE_CIFRADO`, propia de PropTech; ningún agente la lee ni la escribe.
6. Revisar el precio vigente antes del piloto (D-107).

## Risks / Trade-offs

- [El `__session` es legible desde el navegador] → D4: 60 s de vida, la API no alcanzable desde
  afuera, CSP con nonce. Riesgo residual: un script inyectado puede actuar como la persona **a través de
  la web** mientras dure la página; es el mismo riesgo de cualquier sesión con XSS.
- [Política de lectura por identidad en `persona`] → `FOR SELECT`, sin tenant,
  guardián con lista blanca exacta y ataques de L-020. La consulta minimiza columnas, pero RLS permite
  todas las columnas de las filas visibles; no es una restricción de columnas.
- [La clave pública rota en Clerk] → falla cerrada (401) hasta cargar la nueva; se nota en el primer
  ingreso.
- [Clerk no responde, E15] → nadie puede entrar ni renovar; las sesiones ya emitidas duran unos 60 s
  más, con la tolerancia de D1. Se acepta la dependencia y se descarta un login propio de respaldo
  por el costo de D14. No hay extensión local de la sesión.
- [El sobre de invitación es copiable] → D6: cifrado autenticado, email principal verificado,
  vencimiento y un solo uso; logs sin URL y retención ARQ de hasta 3630 s. La clave propia agrega
  una credencial operativa y rotarla obliga a reinvitar.
- [Bloqueo de cuenta como molestia] → D9.
- [La web sin salida a Internet] → SUPUESTO: `clerkMiddleware` con `jwtKey` no necesita llamar a Clerk
  desde el servidor (el handshake pasa por el navegador, *How Clerk works*). Dato que lo discrimina, en
  la tarea 8.2: con la web sólo en `aplicacion`, el ingreso real funciona y el log de la web no tiene
  ningún error de conexión hacia `clerk`; si aparece, la web necesita una red de salida (decisión de
  Juani).
- [Claves de prueba en CI, E16 firmada] → Next usa una secreta ficticia y `jwtKey` local; el humo
  conserva el login de API apagado y da a Next una publicable inventada y una secreta ficticia.
  La instancia de prueba no existe; el humo debe terminar con la web sana.
- [28 tareas] → D0.
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
   0019 (**primero** borra la política que referencia la columna, después el único y al final la columna).
   El catálogo de 3.3 incluye índices, restricciones y permisos de `invitacion`, y prueba su ausencia
   tras el downgrade y su restitución al volver a subir. Con personas ya vinculadas, volver atrás pierde el
   vínculo: se restaura un respaldo.
3. Caddy: quitar el bloque explícito de 404 y volver al proxy `handle /api/*`.
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


## E16 · La clave secreta de Clerk en el servidor de Next (21/10/2026)

Hallazgo del constructor en 6.1 (`c624735`, `e79c346`): en `@clerk/nextjs` 7.9.19, `clerkMiddleware`
ejecuta `assertKey(secretKey)` antes de `authenticateRequest`, así que exige `CLERK_SECRET_KEY` aun cuando el
token se verifica sin red con `jwtKey`; y la CSP automática (6.2) la genera ese mismo middleware. Contradice
E8 y el supuesto de que el CI y el humo corren sin clave secreta.

Decisión aprobada por Juani el 21/10/2026 (E16, sección Aprobación del proposal, `2212c9e`): el servidor de
Next recibe `CLERK_SECRET_KEY` desde el entorno (nunca el navegador; la API sigue sin tenerla). En tests, CI y
humo se usa una clave de prueba no válida contra Clerk, y la verificación del token sigue siendo sin red con
claves locales. La clave real vive sólo en `infra/.env` (la carga Juani) y en producción. E8 queda: hablan con
Clerk el worker (invitaciones) y el servidor de Next (sesión); la API nunca.


## E17 · Ingreso con Google (21/10/2026)

Pedido de Juani durante la 8.1: sumar Google como forma de ingresar. Se activó en el panel de Clerk de
desarrollo (credenciales compartidas de Clerk; producción necesita las propias, change 15). No cambia el
código del login (el componente de Clerk muestra el botón) ni la regla de aceptación: el email verificado
tiene que coincidir con el de la invitación (E7). Cambia el aviso de privacidad (Clerk recibe también la foto
de perfil de Google). Pendiente de la firma de Juani (E17 en la sección Aprobación del proposal).
