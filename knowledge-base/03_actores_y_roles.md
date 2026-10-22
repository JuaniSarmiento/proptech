# Actores y Roles

## Actores del sistema

El modelo del MVP es **perfil × alcance** (D-106, Juani, 20/10/2026). La autorización vive en la base;
Clerk sólo autentica, desde el cambio 2b `login-y-usuarios` (archivado 22/10/2026, D-107, D-108),
junto con la gestión de usuarios.

| Perfil | Alcance | Qué hace |
|---|---|---|
| **Super admin** | Toda la administración | Opera y configura; crea edificios e invita al personal con perfil y alcance |
| **Administrador principal** | Toda la administración | Opera y configura todos sus edificios; puede ejecutar las correcciones reservadas |
| **Administrador por edificio** | Los edificios asignados | Opera y configura, emite y confirma pagos en esos edificios |
| **Contador** | Principal o por edificio | Sólo lectura de lo contable; luego exporta, cuando el módulo lo ofrezca |
| **Auxiliar** | Por edificio | Sólo lectura del edificio |
| **Consejo** | Su edificio | Sólo lectura de gastos, liquidaciones, comprobantes, morosidad y configuración |
| **Vecino propietario** | Sus unidades | Ve ordinarias y extraordinarias e informa pagos |
| **Vecino inquilino** | Sus unidades | Ve sólo ordinarias e informa pagos |

Propietario o inquilino es un atributo de la relación persona-unidad. Una persona puede tener varios
vínculos en distintos edificios y administraciones (D-099), con un solo vínculo por unidad. Varios
propietarios de una unidad tienen cuentas propias, ven la cuenta completa y cualquiera informa un
pago. Hay un solo perfil de personal por persona y alcance, principal incluido (RA-5), y una sola
asignación de consejo por persona y edificio (RR-3). Consejo único no significa un solo consejero
por edificio.

### Cómo nace cada perfil (2b, D-107)

- **Alta inicial** (D-108, E11): un comando de operador (nunca la API) crea la primera
  administración, su super admin y su invitación; es el único camino para que entre la primera
  persona de una administración nueva.
- **Personal** (administrador, contador, auxiliar, consejo): el super admin invita desde
  `/personal` con perfil y alcance; el worker crea la invitación en Clerk y la envía por mail
  (reintentos e idempotencia).
- **Vecinos**: el super admin los da de alta desde el padrón del edificio (vínculo propietario o
  inquilino, varios propietarios por unidad); la invitación la manda Clerk por mail.
- **Aceptación**: un token propio de un solo uso viaja junto al `__clerk_ticket` de Clerk en la
  dirección de regreso; la API exige ese token **y** el email verificado de Clerk igual al de la
  persona (normalizado a minúsculas sólo ASCII, R2B-3) antes de escribir `persona.clerk_usuario_id`.
  Nunca se vincula por email solo.
- **Ingreso con Google** (D-108, E17): también disponible, sólo por invitación; el email verificado
  de Google tiene que coincidir con el de la invitación.

### Las dos capas de aislamiento (D-076)

- **Administración** (el tenant): el cliente que paga PropTech. Todo dato pertenece a una
  administración; ninguna consulta, archivo, caché o proceso devuelve datos de otra. Sale de la
  identidad autenticada, nunca de un parámetro del cliente (R10).
- **Alcance por edificio**: super admin, administrador principal y contador principal alcanzan todos
  los edificios de su administración. Los perfiles por edificio alcanzan sólo los asignados; el
  vecino, sus unidades. Fuera de alcance responde 404; dentro del alcance pero sin permiso, 403 con
  el permiso faltante (D-037). El alcance principal no concede escritura al contador.

## RBAC · Matriz de permisos (D-106, reemplaza la matriz de D-096)

SA: super admin; AP: administrador principal; AE: administrador por edificio; CP/CE: contador principal
o por edificio; AX: auxiliar; CO: consejo; VP/VI: vecino propietario o inquilino. Cada permiso se
comprueba dentro del alcance de la asignación. Las 16 acciones conservan su nombre en el dominio.

| Acción | SA | AP | AE | CP | CE | AX | CO | VP | VI |
|---|---|---|---|---|---|---|---|---|---|
| Cargar gastos y preparar liquidación | Sí | Sí | Sí | No | No | No | No | No | No |
| Emitir y distribuir liquidación | Sí | Sí | Sí | No | No | No | No | No | No |
| Anular liquidación | Sí | Sí | No | No | No | No | No | No | No |
| Confirmar pago informado | Sí | Sí | Sí | No | No | No | No | No | No |
| Revertir o reimputar pago | Sí | Sí | No | No | No | No | No | No | No |
| Condonar intereses | Sí | Sí | No | No | No | No | No | No | No |
| Dar de baja deuda | Sí | Sí | No | No | No | No | No | No | No |
| Aceptar alertas no bloqueantes | Sí | Sí | Sí | No | No | No | No | No | No |
| Aceptar alertas bloqueantes | Sí | Sí | No | No | No | No | No | No | No |
| Invitar usuarios y asignar edificios | Sí | No | No | No | No | No | No | No | No |
| Informar pago | No | No | No | No | No | No | No | Sí | Sí |
| Crear edificio | Sí | No | No | No | No | No | No | No | No |
| Crear versión de configuración | Sí | Sí | Sí | No | No | No | No | No | No |
| Confirmar sin saldos previos | Sí | Sí | No | No | No | No | No | No | No |
| Configurar padrón | Sí | Sí | Sí | No | No | No | No | No | No |
| Ver configuración del edificio | Sí | Sí | Sí | Sí | Sí | Sí | Sí | No | No |

Contador, auxiliar y consejo no escriben. Las lecturas contables se construyen con sus módulos (6,
7, 10a y 12). El inquilino sólo ve ordinarias, también al descargar comprobantes: el 2.2a construyó
el vínculo y el dominio; los cambios 6, 7 y 11 deben aplicar ese filtro.

**P20 sigue abierta**: D-106 fija quién ejecuta una condonación (super admin o administrador principal),
pero falta decidir si un monto exige además la aprobación del consejo. R41 sigue siendo propuesta;
la baja de deuda, si se valida, queda reservada a esos mismos perfiles.

## Rutas públicas

Dos sondas de orquestación siguen sin necesitar sesión porque no exponen datos de ningún complejo ni
unidad:

- `GET /api/salud` (`backend/src/proptech_api/salud.py`): informa si la API, la base y la cola
  responden (`{"estado", "base", "cola"}`); 503 si alguna está degradada. Existe desde el cambio 1a/1c.
- `GET /salud-web` (`web/src/app/salud-web/route.ts`): el equivalente del lado de Next.js. Existe desde
  el cambio 1c.

Estas dos rutas **no son una decisión de negocio sobre qué queda público**: son endpoints técnicos
que no tienen por qué pasar por el login, igual que cualquier healthcheck de Compose.

**Desde el cierre del 2a (15/10/2026)** existen, entre otras, estas rutas de dominio
(`backend/src/proptech_api/complejos.py`), y las tres **exigen identidad** (`Depends(identidad_actual)`)
y sesión con tenant (`Depends(sesion_con_tenant)`): ninguna es pública.

- `GET /complejos/{complejo_id}`: 404 si no existe o está fuera de alcance (indistinguible entre los
  dos casos, D-037).
- `GET /unidades/{unidad_id}`: mismo criterio de 404.
- `POST /complejos/{complejo_id}/asignaciones`: sólo el super admin; 403 con
  `permiso_faltante` si falta el permiso. Desde el 2.2a acepta `administrador`, `contador`, `auxiliar`
  o `consejo` por edificio. Rechaza `nivel`, `vinculo` y `unidad_id` con 422; duplicar el perfil da 409
  (RR-1). R5 del 2a se cerró en la tarea 4.2.

El 3a sumó las demás rutas de configuración y el 3b sus siete pantallas. El 2.2a no agregó rutas.

**Desde el cierre del 2b (22/10/2026, D-107, D-108), el login está construido y `identidad_actual`
resuelve la persona real por el token de Clerk** (ya no inyectada salvo en tests):

- **Caddy deja de publicar `/api/*`** salvo `/api/salud` (`infra/Caddyfile`): un token copiado del
  navegador no tiene a dónde ir desde afuera; toda la API es interna a la red de Compose.
  **BREAKING** respecto de antes del 2b, sin efecto real porque nadie llamaba a la API desde afuera.
- **Rutas de la web sin sesión** (`web/src/proxy.ts`): `/ingresar`, `/registrarse`,
  `/elegir-administracion`, `/invitacion/[sobre]` y `/privacidad` (aviso de privacidad, borrador,
  tarea 7.2 pendiente de aprobación). Cualquier otra ruta sin sesión redirige a `/ingresar`.
- **El vínculo con la API nunca pasa por el cliente**: el servidor de Next manda el token de sesión y
  la administración elegida; `X-Proptech-Administracion` se valida después del token y del vínculo,
  nunca antes.
- Los **links firmados de D-070** (PDF, comprobantes, facturas) no entraron en el 2b; el design deja
  escrito que no reemplazan la sesión. Los arma el cambio 7.

Ya no queda condicionado por P18 (una cuenta por administración, D-096): el vínculo con Clerk es
único **por administración**, así que la misma persona de Clerk puede tener cuenta en dos
administraciones distintas (D-108).
