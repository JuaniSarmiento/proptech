## Why

Desde el 2a todo endpoint de dominio responde 401 en producción: `identidad_actual`
(`backend/src/proptech_api/acceso.py`) levanta siempre y sólo los tests inyectan una persona. Las siete
pantallas del 3b y los perfiles del 2.2a existen, pero nadie puede entrar a usarlos. Juani decidió el
20/10/2026 cómo se entra (exploración `openspec/exploraciones/2026-10-20-roles-de-la-empresa-y-login.md`,
puntos 1, 2 y 9; D-107): **Clerk sólo autentica**, la autorización sigue en nuestra base, los vecinos
también tienen usuario y contraseña, y la identidad se vincula a `persona` por el id de Clerk, nunca por
el email solo. Y decidió quién da de alta a quién (RA-6, D-107): el super admin invita al personal con
perfil y alcance, y los vecinos se dan de alta desde el padrón con su vínculo y reciben la invitación por
mail. Sin las dos mitades juntas el login no sirve: el vínculo con Clerk nace de una invitación, así que
un login sin gestión de usuarios no deja entrar a nadie.

Cubre: **HU-V1** (entrar al portal; la parte de "ver sus unidades" llega con el 11), regla **R10** (la
administración sale del login), decisiones **D-107** (Clerk sólo para autenticar, vecinos con contraseña,
aviso de privacidad, email y nombre, vínculo por id de Clerk), **D-106** (perfil por alcance; quién
invita), **D-099** (selector de administración después de autenticarse), **D-096** P18 (una cuenta por
administración), **D-036** (la sesión del lado del servidor de Next, con la contradicción que se declara
abajo), **D-076**, **D-016** y **D-094** (gobernanza). Reemplaza el método de **D-097**, como ya dice
D-107. Cierra deuda con dueño 2b: del 2a, R9, V2-7, D-1, D-2 (como restricción declarada) y D-6; del 2c,
la CSP de Next; del 3a, RF-B-4; del 3b, el usuario real en la barra superior; del 2.2a, la revisión
independiente de RR-1 a RR-4 y de las 144 celdas, que queda como blanco explícito del rompedor.

## Gobernanza

**Nivel CRITICAL** (D-094, ficha 2b): es la autenticación. Un error acá le abre la administración de
otro a quien no tiene cuenta, o deja entrar con un token falso, vencido o de otra aplicación. Además toca
la política de RLS de `persona`, el vocabulario de la auditoría y la superficie que Caddy publica.

**Se propone y se espera la aprobación escrita y fechada de uno de los dos socios (Juani o Alberto)
antes de construir** (D-094). El constructor no arranca hasta que la sección "Aprobación", al final de
este archivo, tenga el nombre, la fecha, el alcance aprobado y la respuesta a cada elección E1 a E15.
Ningún agente completa esa sección. Un socio puede aprobar el cambio y rechazar una elección; entonces
el design y las specs se corrigen antes de construir. Una regla nueva que entre después de la firma (una
corrección del rompedor que agregue una restricción de base, un texto o un permiso) lleva su propia firma
(L-029).

**Credenciales**: ningún agente crea la cuenta de Clerk, lee ni escribe claves. Juani crea la cuenta y
carga las claves en `infra/.env` (tarea 8.1, al principio del bloque que la necesita). Ningún test llama
a Clerk.

## What Changes

- **La API verifica el token de sesión de Clerk sin red** (E2): RS256 con la clave pública PEM del
  entorno (`CLERK_JWT_KEY`), `exp` y `nbf` contra un reloj inyectado (5 s de tolerancia), `iss` exacto
  de la instancia, `azp` contra la lista de orígenes autorizados y `sub` con formato de usuario de Clerk; cualquier otra cosa da 401 sin tocar la base. Sin clave configurada, el
  login queda apagado y todo sigue respondiendo 401, como hoy.
- **`identidad_actual` resuelve la persona por el id de Clerk** (E3): columna nueva
  `persona.clerk_usuario_id`, única **por administración** (no global: la misma persona de Clerk puede
  tener una cuenta en dos administraciones, D-096 P18 y D-099), con una política de lectura extra que
  sólo deja ver las filas de la identidad ya verificada. Carga sus asignaciones como hoy. Sin vínculo, o
  sin ninguna asignación vigente, el mismo 401 de hoy, indistinguible.
- **El selector de administración** (D-099, E4): `GET /api/sesion` lista las administraciones de la
  identidad; con una sola entra directo; con varias, la web muestra "¿A cuál querés entrar?" y guarda la
  elección en una cookie `HttpOnly`. La API acepta la administración elegida sólo si la identidad
  verificada tiene ahí una persona vinculada: el cliente elige entre las suyas, nunca una ajena.
- **Gestión de usuarios** (RA-6, D-107; quién invita sale de D-106, E6): el super admin invita al
  personal con perfil y alcance (administrador y contador, principal o por edificio; auxiliar y consejo,
  por edificio) y da de alta vecinos desde el padrón con su unidad y vínculo (propietario o inquilino),
  con varios propietarios por unidad y vínculos distintos de una persona. Lista, revoca invitaciones y
  quita asignaciones. La invitación la manda Clerk por mail; la crea el worker (E8), que ya tiene salida
  a Internet, con reintentos e idempotencia.
- **Aceptar la invitación** (E7): un sobre cifrado de un token propio de un solo uso viaja en la dirección
  de regreso de Clerk; el token crudo no viaja en ARQ ni en esa dirección (D6, D7). Al volver, la API
  exige el sobre válido **y** los claims firmados del email principal y `email_verified=true`, con el
  email normalizado a minúsculas igual al de la persona. Sólo entonces escribe `clerk_usuario_id`.
  Nunca se vincula por email solo.
- **Alta inicial de una administración** (E11): comando de operador que crea la administración, su super
  admin y su invitación. `proptech_app` ya tiene `INSERT`: también cualquier camino de la API puede
  crear administraciones; restringirlo sería otra decisión CRITICAL (E11). Sin el alta inicial no hay
  forma de que entre la primera persona.
- **Auditoría de ingresos** (E9, E14): `ingreso_exitoso` al entrar a una administración;
  `ingreso_fallido` cuando hay persona vinculada sin asignación vigente; la gestión de usuarios con sus
  propios eventos. Lo que nunca llega a nuestra base (contraseñas erradas, cuentas bloqueadas) queda en
  Clerk y se declara; un token válido sin vínculo deja una línea de log sin datos personales.
- **Límite de intentos** (E10): el bloqueo por cuenta de Clerk (10 intentos y una hora, configurable en
  su panel), que no bloquea a un edificio entero detrás de una IP compartida.
- **La web**: `@clerk/nextjs` en `proxy.ts` (Next 16) con verificación sin red y orígenes autorizados;
  el cliente de la API manda el token de sesión y la administración elegida desde el servidor; CSP
  estricta con nonce (E5, deuda del 2c); páginas de ingreso, selector, aceptar invitación, aviso de
  privacidad (ley 25.326, transferencia internacional), personal y vecinos del padrón; la barra superior
  muestra el usuario real (deuda del 3b, D-105d). **Las pantallas tienen un `shape` pendiente con Juani**:
  es la tarea bloqueante del bloque de UI (7.0), como en el 3b.
- **Caddy deja de publicar `/api/*`** salvo `/api/salud` (E5): la web llama a la API por la red interna,
  así que un token copiado del navegador no tiene a dónde ir. **BREAKING** para quien llamara a la API de
  afuera: hoy nadie, porque todo responde 401.
- **`acceso-de-desarrollo` se reduce a la carga del ejemplo** (E12): con el login, la puerta sin login
  sobra. Se propone cerrarla y cargar el ejemplo por el mismo camino del alta inicial, sin el `GRANT
  INSERT ON auditoria` al migrador que ese change tenía pendiente de firma.
- **Dependencia de Clerk** (E15): si no responde, nadie puede entrar ni renovar la sesión (unos 60 s).
  Se propone aceptarla; un login propio de respaldo y su costo quedan descartados en D14.
- **Secretos**: las claves de Clerk salen del entorno (`infra/.env`, que carga Juani, nunca en el repo);
  la clave propia de cifrado de invitaciones vive sólo en la API;
  `infra/.env.example` y la tabla de variables del README nombran las variables sin valores.

La revisión deja **28 tareas**: agrega la 4.4 para las dos guardas. La fila E1 conserva el conteo
original de 27 porque la sección de aprobación sólo se amplía con E15; D0 y `tasks.md` llevan el
conteo vigente. Todas las elecciones, incluida E15, siguen pendientes de firma humana.

## Capabilities

### New Capabilities

- `autenticacion-con-clerk`: verificación del token de sesión, vínculo persona e identidad de Clerk,
  selector de administración, auditoría de ingresos, límite de intentos, superficie expuesta (CSP y
  rutas que publica Caddy) y aviso de privacidad.
- `gestion-de-usuarios`: alta inicial de una administración, invitación del personal con perfil y
  alcance, alta de vecinos desde el padrón, envío por el worker, aceptación de la invitación, listado,
  revocación y baja de asignaciones, y sus pantallas.

### Modified Capabilities

- `autorizacion-por-rol`: "Sin identidad no hay acceso ni consultas" deja de decir que la identidad de
  producción falta siempre; un token inválido sigue sin tocar la base y un token válido sin vínculo da el
  mismo 401.
- `aislamiento-por-administracion`: "La administración nunca sale del cliente" admite el selector de
  D-099, acotado a las administraciones de la identidad verificada; "Toda tabla de una administración
  está aislada por la base" admite la política de lectura por identidad verificada.
- `auditoria-de-acciones`: "Vocabulario cerrado" suma eventos de acceso que no son permisos de la matriz.
- `pantallas-del-edificio`: "Navegación común" (la barra superior muestra quién entró y "Salir") y
  "Estados de cada pantalla" (sin sesión lleva al ingreso).

## Que intente romper el rompedor

- **El token**: firmado con otra clave, con `alg: none` o `HS256` usando la clave pública como secreto,
  vencido por un segundo fuera de la tolerancia, con `nbf` futuro fuera de ella, de otra aplicación (`azp` ajeno o ausente), sin `sub`, con un
  `sub` que no tiene forma de usuario de Clerk, con espacios o dos tokens en el encabezado. Cada uno 401
  sin ninguna sentencia SQL. Probar además `iss` de otra instancia y los bordes exactos del reloj
  inyectado de D1.
- **El vínculo**: una identidad de Clerk vinculada en A que pide B poniendo el id de B en el encabezado
  del selector; la misma identidad en A y en B sin elegir; una persona con asignación vencida o quitada;
  dos personas de la misma administración con el mismo `clerk_usuario_id`; la política de lectura por
  identidad usada para escribir; el valor de esa variable de sesión que sobreviva a la transacción.
- **La invitación**: reusada, vencida, revocada, de otra administración, aceptada con otra cuenta de
  Clerk cuyo email no coincide, aceptada dos veces en paralelo, aceptada por una identidad que ya tiene
  otra persona en esa administración; un email coincidente sin verificar; un sobre alterado; un token
  crudo en ARQ o en la URL, o un sobre que aparezca en un log; el TTL de ARQ y su borrado tras una falla.
- **Quién invita**: un administrador principal, un contador o un vecino que invite; un super admin que
  invite a alguien con alcance principal de auxiliar o de consejo; un perfil duplicado (RA-5) o un
  consejo duplicado (RR-3) por invitación; un vecino dado de alta en la unidad de otra administración
  con un UUID real.
- **El navegador**: el token de sesión o la clave secreta en el HTML, en una prop de un componente
  cliente o en un log; `/api/complejos` alcanzable desde afuera de Caddy; la CSP sin nonce o con
  `unsafe-eval`; la cookie de la administración sin `HttpOnly`.
- **La auditoría y los logs**: un email, un token, un `sub` de Clerk sin resumir o el texto de un error de
  Clerk en el detalle o en el log (L-007).
- **Lo que quedó del 2.2a**: repetir los ataques de base de RR-1 a RR-4 (0018, `escritura.py`,
  `auditoria.py`, `Estados.tsx`) y cotejar las 144 celdas del test de permisos contra D-106 con
  identidades reales, antes de que el login les dé uso.

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-031). Detalle en `design.md` ("Cómo aplica
cada lección").

| Lección | Tareas |
|---|---|
| L-001 · una dependencia que no responde | 5.4 (Clerk falso que no responde, con plazo de 10 s) |
| L-002 · la configuración se rompe de muchas formas | 2.2 (clave PEM ausente, vacía, mal formada, con otro algoritmo; orígenes con espacios o comodines) |
| L-003 · contar los tests | 1.1 y 9.2 |
| L-005 · verde es todo el workflow | convención de `tasks.md` y 9.2 |
| L-007 · el mensaje de una librería también es una salida | 2.1 (el error de PyJWT nunca llega a la respuesta ni al log) y 5.3 (el cuerpo de error de Clerk) |
| L-009 · el gemelo de API y worker | 2.2 y 5.3 (la configuración de Clerk la leen los dos con las mismas reglas) |
| L-010 y L-031 · la corrida de cierre va al final y sobre el último commit | 9.2 |
| L-012 · la deuda al primer cambio que usa la pieza | 4.3 (R9, V2-7, D-1, D-6) y 6.2 (CSP, RF-B-4) |
| L-013 · mutar sin commit exige copia | convención de `tasks.md`, 2.1, 3.1, 4.1 |
| L-016 y L-017 · observaciones que pueden dar otro resultado, con la entrada del escenario | 3.1, 3.2, 4.1, 5.2, 5.4 (como `proptech_app`, dos administraciones, UUID reales ajenos) |
| L-018 · el efecto, no la forma | 3.1 (la política se prueba leyendo y escribiendo como la app, no leyendo `pg_policies`) |
| L-019 · un test que no puede dar rojo | cada RED de `tasks.md`; 4.3 (V2-7) |
| L-020 · arreglar un bloqueante puede crear otro | 3.1 (la política nueva tiene su propio ataque: escribir por ella) |
| L-022 · comparar el conjunto | 3.3 (catálogo antes y después) y 9.2 (la lista de rutas del barrido entera) |
| L-023 · NOT NULL o CHECK rompe fuera de `backend/` | 3.3 (todo `INSERT` a `persona` del repositorio, incluido `humo.sh`) |
| L-024 y L-025 · cada vuelta es código nuevo; el constructor no se revisa | "Que intente romper el rompedor" y la vuelta del rompedor sobre cada bloque |
| L-026 · mirar las pantallas | 7.1 a 7.4, cada una cerrada con capturas en navegador real |
| L-027 · la API falsa valida como la real | 7.1 a 7.4 (método, `Content-Type`, forma del cuerpo y encabezados de sesión) y 5.3 (el Clerk falso del worker) |
| L-028 · combinaciones de capas | 7.3 y 7.4 (panel lateral + ayuda + menú en las pantallas nuevas) |
| L-029 · la firma no cubre correcciones | sección "Aprobación" y convención de `tasks.md` |
| L-030 · el brief separa orden de permisos | convención de `tasks.md` ("Qué resuelve el constructor") |

L-004, L-006, L-011, L-014, L-015 y L-021 no tienen una tarea propia en este propose: las revisiones
independientes las cubre el ciclo de trabajo; no hay comandos destructivos nuevos ni Bash nuevo más
que el humo. L-008 sí aplica al id de Clerk (2.1); L-001, al envío (5.4), que usa red aunque la
verificación de la API no la use.

## Fuera del cambio

- **El portal del vecino** (11) y la vista del consejo (12): el vecino entra y ve el estado vacío del
  portal; lo que ve de sus unidades llega con el 11.
- **El puerto de email propio** (13): las invitaciones las manda Clerk; recordatorios y avisos, no.
- **Doble factor**: Clerk lo ofrece; activarlo para el personal es una decisión aparte (pregunta abierta).
- **Sincronizar borrados con Clerk**: quitar la última asignación corta el acceso en el próximo pedido,
  pero no borra el usuario de Clerk; borrarlo queda para el 15 o para una decisión de Juani.
- **Links firmados de D-070**: los arma el 7; este cambio sólo fija que no reemplazan la sesión.
- **Costo de Clerk**: se verifica en su página antes del piloto (15), como dice D-107.
- **P12 para la base de negocio** (inscripción ante la AAIP): sigue abierta.
- **Webhooks de Clerk**: no se usan (E7, E9); si un cambio posterior los necesita, entran con su firma.

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 21/10/2026): `01_vision_y_objetivos.md`,
`02_descripcion_general.md`, `03_actores_y_roles.md`, `04_modelo_de_datos.md`,
`05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`,
`08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`,
`11_glosario.md`, `12_fichas_de_changes.md`, `13_motor_de_reglas.md`, `14_forma_de_trabajo.md`,
`15_lecciones.md`, `16_proyecto_final.md`, `README.md`. Este propose no edita ninguno: lo hace quien
archiva.

- `09_decisiones_y_supuestos.md`: **APPEND**. D-108 con las elecciones E1 a E15 tal como las firme el
  socio, incluida la que **ajusta D-036** (el `__session` de Clerk es legible desde el navegador; se
  compensa con 60 segundos de vida, Caddy sin `/api/*` público y CSP; D-036 lleva la marca "corregida en
  parte por D-108") y la que acota "única" del vínculo a "única por administración". Un supuesto SU-01
  si al archivar sigue sin verificarse cómo se comporta una invitación a un email que ya tiene usuario
  en Clerk (design, Open Questions).
- `02_descripcion_general.md`: **REWRITE** de integraciones externas (Clerk: qué guarda, qué no, quién
  lo llama) y de las dependencias nuevas (`pyjwt[crypto]`, `cryptography`, `@clerk/nextjs` y
  `@clerk/localizations`).
- `03_actores_y_roles.md`: **REWRITE** de "Rutas públicas" (`/ingresar`, `/privacidad`, la aceptación
  de invitaciones; `/api/*` deja de publicarse) y de cómo nace cada perfil (invitación, alta inicial).
- `04_modelo_de_datos.md`: **REWRITE** de `persona` (`clerk_usuario_id`, unicidad por administración,
  la política de lectura por identidad) y la tabla nueva `invitacion`.
- `06_funcionalidades.md`: **REWRITE** de HU-V1 (qué cubre el 2b y qué el 11) y las historias de
  gestión de usuarios del super admin, si no existen.
- `07_flujos_principales.md`: **REWRITE** con los flujos de ingreso, selector, invitación y aceptación,
  con sus casos de error.
- `08_arquitectura_propuesta.md`: **REWRITE** de la sección de seguridad (verificación sin red, CSP,
  superficie de Caddy, dónde vive cada clave) y de la tabla de variables de entorno.
- `10_preguntas_abiertas.md`: **REWRITE**. Las preguntas de `design.md` que Juani no responda al firmar
  (doble factor del personal, borrado en Clerk, invitación a un email existente).
- `11_glosario.md`: **REWRITE**: "invitación", "vínculo con Clerk", "alta inicial", "selector".
- `12_fichas_de_changes.md`: **REWRITE** de la ficha 2b (estado, cierre), de la ficha 3b-bis
  (`acceso-de-desarrollo` reducido, sin `GRANT`, si se firma E12) y de las tablas de deuda: filas del 2a
  (R9, V2-7, D-1, D-2, D-6), del 2c (CSP), del 3a (RF-B-4), del 3b (barra superior) y del 2.2a que este
  cambio cierre.
- `14_forma_de_trabajo.md`: **REWRITE** sólo si el cierre cambia el método (por ejemplo, la verificación
  real con Clerk como paso humano fijo antes de archivar un cambio de acceso).
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar.
- `01`, `05`, `13`, `16` y `README.md`: none. No cambian la visión, las reglas de negocio, el motor de
  reglas ni el proyecto final; ninguna regla R nombra el método de ingreso.
- Fuera de `knowledge-base/`: `CHANGES.md` (**REWRITE**, C-05b a archivado), `CLAUDE.md`/`AGENTS.md`
  (**REWRITE** del estado), `README.md` del repo (**REWRITE** de la tabla de variables, tarea 6.3) y
  `openspec/changes/acceso-de-desarrollo/` (**REWRITE** si se firma E12, tarea 9.1).

## Impact

- **Backend**: `proptech_core/acceso/dominio/` (verificación del token, eventos de acceso),
  `acceso/aplicacion/` (resolver la identidad, invitaciones, aceptación, alta inicial),
  `compartido/base_de_datos.py` (sesión con identidad verificada antes del tenant),
  `compartido/configuracion.py` (variables de Clerk), `proptech_api/acceso.py` (`identidad_actual`
  real), routers nuevos de sesión, personal, vecinos e invitaciones, `proptech_worker` (tarea de envío),
  migraciones `0019` y `0020`. Las dos rutas sin persona completa usan una guarda de token verificado
  y siguen en el barrido protegido, nunca en `_RUTAS_PUBLICAS` (4.4).
- **Web**: `proxy.ts`, `lib/api/cliente.ts` (encabezados de sesión), páginas nuevas, barra superior.
- **Infra**: `Caddyfile` (sólo `/api/salud` público), `compose.yaml` (variables de Clerk por servicio),
  `infra/.env.example`, `humo.sh` (sin claves reales: el login apagado no rompe el arranque).
- **Dependencias nuevas**: `pyjwt[crypto]` 2.15 y `cryptography` para los sobres (API), `@clerk/nextjs` y `@clerk/localizations`
  (web), con versión fijada. El worker ya tiene `httpx` disponible sólo como dependencia de desarrollo;
  pasa a dependencia directa si lo usa el adaptador (design D7).
- **Servicio externo**: Clerk (cuenta a cargo de Juani). Ningún test ni CI lo llama.
- **Contrato**: `/api/*` deja de ser alcanzable desde afuera de Caddy salvo `/api/salud` (**BREAKING**).
- **Datos**: columna nueva en `persona` y tabla nueva `invitacion`; hoy no hay datos reales (RD-2 del
  2.2a, supuesto que sigue en pie).

## Aprobación

Gobernanza CRITICAL (D-094). La completa, a mano, uno de los dos socios. Ningún agente la escribe.

Los puntos 1, 2 y 9 de la exploración y D-107 ya los decidió Juani; estas son las elecciones que no
fijaron, cada una con su alternativa descartada y el costo de revertir en `design.md`.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Un solo change | Login y gestión de usuarios en un change de 27 tareas, aunque la regla de `config.yaml` pide partir desde unas veinte: sin invitación no hay vínculo y el login solo no deja entrar a nadie (D0) | Sí, Juani 21/10/2026 |
| E2 · Verificar el token | PyJWT con la clave pública PEM del entorno, sin red ni SDK de Clerk en la API (D1) | Sí, Juani 21/10/2026 |
| E3 · El vínculo | `persona.clerk_usuario_id` único por administración, con una política de lectura extra por identidad verificada (D2) | Sí, Juani 21/10/2026 |
| E4 · El selector | La administración elegida viaja en un encabezado de Next a la API y vale sólo si la identidad tiene persona vinculada ahí; cookie `HttpOnly` en la web (D3) | Sí, Juani 21/10/2026 |
| E5 · El token en el navegador | Aceptar el `__session` legible de Clerk (60 s) contra D-036 y compensar con Caddy sin `/api/*` público y CSP estricta con nonce (D4) | Sí, Juani 21/10/2026 |
| E6 · Quién invita | Sólo el super admin, al personal y a los vecinos (la matriz de D-106 tal cual) (D5) | Sí, Juani 21/10/2026 |
| E7 · Aceptar la invitación | Token propio de un solo uso en la dirección de regreso de Clerk, más el email verificado de Clerk igual al de la persona (D6) | Sí, Juani 21/10/2026 |
| E8 · Quién habla con Clerk | El worker crea y revoca las invitaciones; la clave secreta vive en el worker y en la web, nunca en la API (D7) | Sí, Juani 21/10/2026 |
| E9 · Qué se audita | `ingreso_exitoso` al entrar; `ingreso_fallido` con persona vinculada sin asignación; el resto en Clerk y en un log sin datos personales (D8) | Sí, Juani 21/10/2026 |
| E10 · Límite de intentos | El bloqueo por cuenta de Clerk (10 intentos, una hora), sin límite propio por IP (D9) | Sí, Juani 21/10/2026 |
| E11 · Alta inicial | Comando de operador como `proptech_app` con el tenant nuevo fijado; el actor de la auditoría es el super admin creado (D10) | Sí, Juani 21/10/2026 |
| E12 · `acceso-de-desarrollo` | Cerrar el acceso sin login y cargar el ejemplo por el camino de E11, sin `GRANT INSERT ON auditoria` al migrador (D11) | Sí, Juani 21/10/2026 |
| E13 · Pantallas de Clerk | Componentes prearmados de Clerk en castellano, con la apariencia de `DESIGN.md`, para ingresar y registrarse; el resto, nuestras (D12) | Sí, Juani 21/10/2026 |
| E14 · Vocabulario de auditoría | Eventos de acceso que no son permisos: `ingreso_exitoso`, `ingreso_fallido`, `alta_inicial`, `invitar_personal`, `dar_de_alta_vecino`, `aceptar_invitacion`, `revocar_invitacion`, `quitar_asignacion` (D13) | Sí, Juani 21/10/2026 |
| E15 · Dependencia de Clerk | Si Clerk no responde, nadie puede entrar ni renovar la sesión (unos 60 s): se acepta la dependencia (D14) | Sí, Juani 21/10/2026 |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| Juani | 21/10/2026 | Todo el change login-y-usuarios tal como está en esta propuesta, con E1 a E15 aprobadas |
