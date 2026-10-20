# Actores y Roles

## Actores del sistema

El modelo del MVP es **perfil × alcance** (D-106, Juani, 20/10/2026). La autorización vive en la base;
Clerk sólo autentica y se integra en el 2b (D-107), junto con la gestión de usuarios.

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

El 3a sumó las demás rutas de configuración y el 3b sus siete pantallas. Sin login (2b),
`identidad_actual` sigue dando 401 en producción: las rutas de dominio se prueban con identidad
inyectada. El 2.2a no agregó rutas.

**Lo que queda por decidir** (no se asume "ninguna" sin confirmarlo en el *design* del cambio 2b,
D-039): qué pantallas del portal del vecino o del login quedan accesibles sin sesión (por ejemplo, la
propia pantalla de login); y si un **link firmado** de descarga (D-070: PDF de la expensa,
comprobantes, facturas, con vencimiento entre un minuto y una hora) cuenta como "ruta pública" en el
sentido de este documento o es un mecanismo aparte que no requiere sesión activa pero sí una firma
válida: ese punto tampoco está resuelto todavía y se deja así, sin asumir una respuesta. Se completa
junto con el explore del cambio 2b (login con Clerk del personal y del vecino, D-107). Ya no queda
condicionado por P18 (una cuenta por administración, D-096): el login resuelve siempre dentro de una
sola administración.
