# Exploración: acceso y aislamiento (cambio 2)

> Explore mode. No se escribió código, no se tocó `knowledge-base/`, no se corrió `openspec` CLI y
> no se commiteó nada. Lo que sigue son hallazgos y una recomendación para que decidan Juani y
> Alberto; nada acá es una decisión tomada. El cambio es CRITICAL (D-094): su *propose* necesita
> aprobación escrita de uno de los dos socios antes de escribir código, esta exploración no la
> reemplaza.

**Fecha**: 15/10/2026
**Disparador**: `CHANGES.md` [C-05], próximo en el camino crítico (`1a → 1b → 1c → 1d → 2 → ...`).
Ya no está bloqueado por P18 ni P23 (resueltas el 15/10 en D-096). La propia ficha dice qué falta
decidir acá: "el método de login; dónde vive cada uno de los tres controles".

**Fuentes leídas del repo**: `CLAUDE.md`, `CHANGES.md` §C-05, `knowledge-base/12_fichas_de_changes.md`
§2, `knowledge-base/03_actores_y_roles.md`, `knowledge-base/05_reglas_de_negocio.md` (R10),
`knowledge-base/06_funcionalidades.md` (HU-V1), `knowledge-base/09_decisiones_y_supuestos.md`
(D-009, D-016, D-021, D-036, D-037, D-039, D-076, D-096 completas), `knowledge-base/10_preguntas_abiertas.md`,
`knowledge-base/15_lecciones.md` (L-010 a L-017), las tres exploraciones previas en
`openspec/exploraciones/` (para el formato), y el código real: `backend/src/proptech_core/compartido/base_de_datos.py`,
`configuracion.py`, `conexion_redis.py`, `seguimiento.py`, `backend/src/proptech_worker/tareas.py`,
`backend/migraciones/env.py` y `versions/000*.py`, `infra/compose.yaml`, `infra/.env.example`.
No se usó WebFetch ni WebSearch: todo lo que sigue sale del repo o de semántica estándar de
PostgreSQL (RLS, `current_setting`, roles), marcado como juicio, no como hallazgo del código.

---

## 1. Método de login

D-039 dejó la pregunta abierta explícitamente ("Clerk para el personal y enlace mágico para
vecinos, según Alberto, no se decidió en esa charla"). D-096 ya resolvió *con quién* entra cada
login (una cuenta por administración) pero no *cómo* se autentica. Separo personal de vecino
porque son perfiles de riesgo y de uso distintos: el personal (sobre todo el titular) va a manejar
plata más adelante; el vecino entra una vez por mes a mirar su expensa (HU-V2) y es, textual de
HU-V1, "como vecino, quiero entrar desde el celular con mi email": ni la propia historia de usuario
menciona una contraseña.

### 1.1 Opciones para el personal (titular, colaborador, consejo)

| Opción | Costo de construir | Riesgos | Qué implica para P18/D-096 |
|---|---|---|---|
| **Contraseña propia** (hash con `argon2` o `bcrypt`, endpoint FastAPI, sesión via cookie del servidor de Next, D-036) | Bajo. Librería de hashing + un endpoint + validación de fuerza mínima. Sin reset self-service por mail (ver 1.3), el costo queda bajo porque no hay que construir el envío de mails todavía. | Reutilización de contraseñas entre sitios; fuerza bruta (mitigado por la sección 4); si se pierde la contraseña y no hay reset self-service, cae en soporte manual (hoy sólo Juani, P13). | Ninguno nuevo: el login pide administración + email + contraseña, coherente con D-096. |
| **Clerk** (como propone Alberto) | Medio-alto: es una dependencia SaaS nueva, con su SDK en el servidor de Next y su propio modelo de "Organization" para mapear administraciones. Ahorra construir hashing y sesiones, pero no ahorra nada del lado de RLS/tenant (igual hay que mapear la organización de Clerk a `administracion_id` en cada pedido). | Manda emails de personal (titular, colaboradores) a un tercero en EE.UU.: suma una pata a P12 (inscripción ante la AAIP) antes de tener respuesta. Choca con el criterio de costo del proyecto (D-043: "ante dos opciones equivalentes, la que no cobra licencia ni uso"): con pocos usuarios por administración (titular + algunos colaboradores + consejo), construir contraseña propia es más barato que pagar un SaaS pensado para volumen. | El concepto "Organization" de Clerk calza con administración, pero sigue sin resolver a qué organización entra un login si el email se repite entre administraciones (ver 1.4): Clerk no resuelve esa parte gratis. |
| **Enlace mágico por mail** | Medio: necesita el mismo envío de mails que el vecino (ver 1.3), más generar y validar un token de un solo uso con vencimiento corto. | Depende de la bandeja de entrada: si el mail de un titular está comprometido, el enlace mágico es la llave completa sin segundo factor. Para quien va a anular pagos y cerrar liquidaciones (D-037), es un riesgo más alto que para un vecino que sólo lee su deuda. | Mismo problema de 1.4 que las otras dos. |

**Recomendación (de los socios, no tomada)**: contraseña propia para el personal, sin reset
self-service por mail en este cambio (reset asistido, ver 1.3). Argumento: D-043 ya fija el
criterio de costo contra un SaaS cuando hay una alternativa equivalente, el volumen de usuarios por
administración es chico (no hace falta SSO ni gestión enterprise de Clerk todavía), y evita sumarle
a P12 una transferencia de datos personales a un tercero antes de tener esa pregunta resuelta.
Clerk queda como opción a reabrir si en v1.1 aparecen más administradores grandes con equipos
propios de IT que lo pidan.

### 1.2 Opción para el vecino

El vecino es el usuario menos técnico del sistema y entra con poca frecuencia (HU-V2: una vez por
mes a ver la expensa). Acá el costo no está en construir el login sino en el soporte: cada
contraseña olvidada es un trabajo de Juani (P13, hoy el único soporte).

| Opción | Costo de construir | Riesgos | Para el MVP con P18 (una cuenta por administración) |
|---|---|---|---|
| **Enlace mágico por mail** | Medio: exige poder mandar un mail transaccional (ver 1.3, el mismo problema que el personal). No hay contraseña que gestionar, que es justo lo que pide la HU-V1 ("con mi email"). | El vecino puede reenviar o reenviarse el enlace sin querer a otra persona (riesgo bajo, vencimiento corto lo acota). Depende 100% de que el mail llegue: si cae en spam, el vecino no puede entrar y es un ticket de soporte igual, sólo que de "no me llegó el mail" en vez de "me olvidé la contraseña". | Si el mismo email tiene cuenta en dos administraciones, el enlace tiene que resolver a cuál entra (ver 1.4): no es un problema del método, es un problema del dato. |
| **Contraseña con reset asistido** (el titular la restablece desde su panel, sin que el vecino la autogestione por mail) | Bajo: mismo endpoint que el del personal, más una acción de "restablecer" para el titular/colaborador con permiso. Cero dependencia de envío de mails en este cambio. | Más fricción para el vecino (tiene que acordarse una contraseña nueva) y más carga para el titular (es quien resetea). Para un piloto de un solo edificio es manejable; no escala bien a muchas administraciones chicas sin personal de soporte propio. | Mismo punto 1.4. |

**Recomendación (de los socios, no tomada)**: entre las dos, el enlace mágico es la que mejor
encaja con la HU-V1 tal como está escrita y con el perfil del usuario (no técnico, uso mensual, sin
nada crítico de plata que confirme él mismo, D-017: el vecino informa, nunca confirma). El costo
real no es el mecanismo del enlace sino construir el envío de mails antes de tiempo (ver 1.3), así
que la recomendación de login depende de cómo se resuelva esa pregunta.

### 1.3 El problema que cruza a las dos opciones: el envío de mails no existe todavía

`knowledge-base/12_fichas_de_changes.md` §13 dice textual que el "puerto de email con su adaptador"
es scope del cambio 13 `avisos-por-email` (C-18), que depende de los cambios 8 y 10b y está lejos
en el camino crítico. Confirmado en el código: `backend/src/proptech_worker/` sólo tiene
`tareas.py`, `ajustes.py` y `prueba.py`, ninguno manda mail. Si el método elegido (para personal o
para vecino) usa enlace mágico, el cambio 2 necesita, sin estar en su scope declarado hoy, una
versión mínima de "mandar un mail" antes de que exista el puerto completo del cambio 13 (con
reintentos, idempotencia y plantillas, que ese cambio sí promete).

Esto es justo lo que evita la opción de contraseña con reset asistido: cero dependencia de mail en
este cambio, a costa de la fricción de la sección 1.2. Es la decisión que más cambia el costo real
del cambio 2, y por eso la marco aparte en la sección 6 como pregunta que bloquea.

### 1.4 La pregunta que ninguna de las tres opciones resuelve sola

D-096 fija "una cuenta por administración" y dice textual que "la unicidad del usuario es por
administración y no global": el mismo email puede repetirse en dos administraciones distintas. Pero
ni D-096 ni D-076 dicen **cómo elige el login a cuál administración entra** cuando eso pasa. Sin
una administración explícita en la URL (un *slug* por administración, por ejemplo
`/ingresar/<slug>`), un login con sólo email+contraseña podría encontrar cero, una o más de una
fila que matchea ese email, y ahí hay que elegir: ¿se pide la administración antes del email
(un selector o un slug en la URL), o se resuelve después (el sistema encuentra varias cuentas y las
muestra para elegir)? Es justamente la pregunta que la propia ficha del cambio 2 dice que falta
resolver en este explore ("dónde vive cada uno de los tres controles"), y no hay nada en el código
ni en las decisiones que la responda todavía. La marco como bloqueante en la sección 6.

---

## 2. Aislamiento con Row-Level Security

### 2.1 El patrón ya existe en el código, para otra cosa

`base_de_datos.py::registrar_application_name` ya hace, para `application_name`, exactamente lo que
el plan de D-087 pide para el tenant: un listener `after_begin` sobre la `sessionmaker` que corre
`SELECT set_config('<clave>', :valor, true)` (el `true` final es `SET LOCAL`, válido sólo durante
esa transacción) leyendo una `ContextVar` (`request_id_actual`, en `seguimiento.py`). La
recomendación más barata para este cambio es literalmente copiar esa forma: una nueva `ContextVar`
(`administracion_id_actual`), fijada por una dependencia de FastAPI después de validar el login
(y por el worker, ver 2.3), leída por un segundo listener `after_begin` (o el mismo, ampliado) que
hace `SELECT set_config('app.administracion_id', :valor, true)`.

Dos diferencias importantes respecto del patrón de `request_id`, que conviene dejar escritas en el
*design* para que no se copie el patrón equivocado:

- **`request_id` ausente genera uno nuevo** (`con_seguimiento_de_tarea`, en `seguimiento.py`): es
  intencional, porque un `request_id` es sólo para rastrear logs, no para decidir seguridad.
  **`administracion_id` ausente tiene que ser un error duro** (o, como mínimo, "cero filas"), nunca
  generar un valor cualquiera: eso es precisamente el candado que D-087 pide ("sin valor fijado, una
  consulta no devuelve nada").
- `request_id_actual` se fija una vez por pedido o por tarea. `administracion_id_actual` tiene que
  estar fijado **antes de la primera consulta de esa transacción**, lo que depende del orden en que
  FastAPI resuelve las dependencias: si la dependencia de sesión no depende explícitamente
  (`Depends(...)`) de la dependencia de autenticación, no hay garantía de que la segunda corra antes
  de abrir la sesión. Es un caso borde real para el rompedor (sección 5), no una suposición mía
  sobre cómo anda FastAPI hoy en este repo (no hay ningún endpoint de dominio todavía).

### 2.2 El candado de la base: `current_setting` necesita `missing_ok`

Esto es semántica estándar de PostgreSQL, no algo que leí en el código (no hay policies todavía):
`current_setting('app.administracion_id')` **sin** el segundo argumento levanta un error si esa
variable nunca se fijó en la sesión, en vez de devolver `NULL`. Si la policy se escribe así, un
error de otra capa (una conexión reusada sin tenant fijado, una query de mantenimiento, el propio
health check) tira un 500 en vez de las "cero filas" que pide D-087 como candado de cierre. La forma
que sí da "cero filas, nunca error" es `current_setting('app.administracion_id', true)`, y conviene
además envolverla en `nullif(..., '')` antes de castear a `uuid`, porque castear una cadena vacía a
`uuid` también levanta error (`invalid input syntax for type uuid`) en vez de devolver `NULL`. Sin
ese `nullif`, "fijar el tenant con una cadena vacía" y "no fijarlo" se comportan distinto (una
levanta error, la otra da cero filas), cuando D-087 pide que las dos se comporten igual.

### 2.3 Dos roles de base, y lo que eso rompe hoy

Hoy existe **un solo rol de PostgreSQL** (`infra/.env`: `POSTGRES_USER=proptech`), compartido por
Alembic (`migraciones/env.py`, vía `ConfiguracionBaseDeDatos`), la API y el worker (vía
`Configuracion`, que hereda de la misma clase base) y el servicio `respaldos` (`infra/compose.yaml`,
`PGUSER`). Ese usuario, al ser el `POSTGRES_USER` del contenedor oficial de Postgres, nace
superusuario: hoy nada hace de candado porque todo corre con permiso para saltearse cualquier
policy. El plan de D-087 (`proptech_migrador` dueño de las tablas, `proptech_app` sin privilegios ni
`BYPASSRLS` para la API y el worker) implica, además de las policies en sí:

- **`configuracion.py` necesita dos pares de credenciales**, no uno: hoy `_ConfiguracionBaseDeDatosBase`
  y `_ConfiguracionBase` leen las mismas variables `POSTGRES_USER`/`POSTGRES_PASSWORD` para
  Alembic y para la API/worker. Hace falta un par nuevo (por ejemplo `POSTGRES_APP_USER`/
  `POSTGRES_APP_PASSWORD`) y decidir cuál de los dos roles usa cada clase.
- **`infra/compose.yaml` necesita crear los dos roles nuevos** sin tocar el rol existente: un script
  de inicialización (`docker-entrypoint-initdb.d`) que corra `CREATE ROLE` para `proptech_migrador`
  y `proptech_app`, idealmente idempotente (un `DO $$ ... IF NOT EXISTS ... $$` contra `pg_roles`,
  porque `CREATE ROLE IF NOT EXISTS` no existe en PostgreSQL).
- **`respaldos` (cambio 1d/C-04) tiene que seguir usando el rol original**, no `proptech_app`. Esto
  es juicio mío sobre semántica de PostgreSQL, no algo que haya leído confirmado en el repo: con
  `FORCE ROW LEVEL SECURITY` activa, un rol sin `BYPASSRLS` (como tiene que ser `proptech_app`) y
  sin ser superusuario sólo ve lo que su `SET LOCAL` le permite; `pg_dump` corrido con ese rol, sin
  `--enable-row-security`, falla o (peor, con `--enable-row-security`) vuelca sólo lo visible para
  el tenant fijado en ese momento, nunca toda la base. El servicio de backups tiene que seguir
  usando el rol superusuario original (que sigue existiendo, nadie lo borra) para que el volcado siga
  siendo completo. Es un riesgo silencioso: si alguien "simplifica" las credenciales de `respaldos`
  para que use `proptech_app` por prolijidad, los backups quedan vacíos o truncados sin que ningún
  chequeo del 1d lo note (el humo del 1d valida que el archivo existe y se puede restaurar, no que
  tiene todas las administraciones).
- **`proptech_migrador`, al ser dueño de las tablas, también queda sujeto a `FORCE ROW LEVEL SECURITY`**
  (otra vez, semántica estándar de Postgres: `FORCE` aplica incluso al dueño, a diferencia del modo
  sin forzar). Si alguna migración necesita insertar datos de **más de una** administración en la
  misma corrida (las "tablas mínimas" de este mismo cambio: administración, complejo, unidad,
  persona, asignación por rol), esa migración se topa con la misma policy que el resto. Dos salidas:
  darle `BYPASSRLS` a `proptech_migrador` (más simple, razonable porque ese rol no es alcanzable
  desde la web, sólo desde el pipeline de deploy) o hacer que cada migración de semilla fije su
  propio `SET LOCAL` antes de insertar. Queda como pregunta abierta en la sección 6.

### 2.4 El worker: el tenant viaja como argumento validado, no como `ContextVar` heredada

`backend/src/proptech_worker/tareas.py` ya tiene el patrón exacto para esto: `_ArgumentosTareaDePrueba`
valida `fallar_veces` con Pydantic en modo estricto antes de tocar la cola, siguiendo el contrato de
`encolar` (D2 del 1c). `administracion_id` tiene que sumarse como otro argumento validado así, para
toda tarea que lea o escriba datos de una administración (la deuda de D-091 que la ficha del cambio
2 hereda del 1c, sobre `trabajos_hechos`). El decorador `con_seguimiento_de_tarea` es el molde para
uno nuevo que fije `administracion_id_actual` antes de correr la tarea: **L-015** (un
`threading.Thread` no hereda `ContextVar`, sólo `asyncio.to_thread` copia el contexto) ya obliga a
que todo el código de base del worker siga pasando por `asyncio.to_thread` como hoy
(`_registrar_en_un_hilo`), nunca por un `threading.Thread` manual, o la `ContextVar` del tenant se
pierde exactamente igual que se hubiera perdido el `request_id` sin ese cuidado.

### 2.5 El aislamiento por edificio es un candado más débil que el de administración, y vale la pena decirlo así

D-076 separa dos capas: administración (tenant, con RLS) y edificio (alcance por rol, D-037). El
plan de RLS de D-087 sólo describe una policy a nivel `administracion_id`. El alcance por edificio
(el colaborador ve sólo sus edificios asignados) no tiene, en lo que leí, una policy de base
equivalente: depende de que el código de aplicación filtre bien por la tabla de asignaciones. Esto
importa porque el objetivo declarado del cambio es "que cada persona entre y vea sólo lo suyo,
**aunque el código tenga un error**": esa garantía es fuerte para la administración (gracias a RLS,
un error de código no alcanza para cruzar administraciones) pero más débil para el edificio (un
error de código ahí sí podría mostrar un edificio no asignado, porque no hay una policy de base
que lo frene). Reforzar también el alcance por edificio con una segunda policy (contra una tabla de
asignaciones rol-edificio, vía otro `current_setting` con la identidad del usuario) es más caro y
puede no entrar en esta primera vuelta; lo dejo como pregunta abierta en la sección 6, no como algo
que dé por descontado que se hace.

---

## 3. Auditoría de acciones sensibles

D-016 pide auditoría por identidad y "en la misma transacción" que la acción que registra (ficha
§2). La mayoría de las acciones sensibles de la matriz de D-096 (emitir, confirmar/revertir pago,
condonar, dar de baja) pertenecen a módulos que todavía no existen (`liquidacion`, `pagos`,
`cuenta_corriente`, cambios 7, 8, 10b): este cambio no las audita porque todavía no pasan. Lo que sí
le toca a este cambio, porque es su propio dominio (`acceso`), es:

- **Login exitoso y login fallido** (forense para fuerza bruta, además del límite de la sección 4).
- **Invitar usuarios y asignar edificios** (la única fila de la matriz de D-096 que es, literalmente,
  una acción del módulo `acceso`: "Sí" para titular, "No" para el resto).
- Cualquier alta de las "tablas mínimas" que crea este cambio (persona, asignación por rol).

Propongo (no decidido) una tabla `auditoria` con `administracion_id` (con su propia policy de RLS,
para que un colaborador o consejo de una administración no pueda leer la auditoría de otra), actor,
acción (de un vocabulario cerrado, no texto libre), entidad afectada, detalle en JSON **sin
contraseñas ni datos sensibles**, `request_id` (para cruzar con los logs JSON del 1c) y marca de
tiempo. "En la misma transacción" quiere decir: la escritura de la acción y su fila de auditoría se
confirman o se revierten juntas, nunca una sin la otra; conviene un helper reusable (parecido a
`ejecutar_una_vez` de `idempotencia.py`) para que los cambios futuros (7, 8, 10b) no reinventen el
mecanismo, sólo agreguen sus propias acciones al vocabulario. Quién puede **leer** la auditoría
(¿sólo el titular?) no está definido en ningún documento que haya leído: lo dejo nombrado, sin
resolverlo acá porque no bloquea el diseño del mecanismo en sí.

---

## 4. Límite de intentos en el login

Redis ya está disponible (`conexion_redis.py`), pero sólo hay un cliente **síncrono**
(`cliente_redis_sincrono`, para el verificador de `/api/salud`) y los `RedisSettings` de ARQ. Un
endpoint de login en FastAPI (async) necesita un cliente **asíncrono** (`redis.asyncio.Redis`), que
hoy no existe en el repo: es una pieza chica para sumar, reusando `redis_host`/`redis_port`/
`redis_password` de `Configuracion`.

**Clave del contador**: no alcanza con limitar sólo por cuenta (no frena a alguien probando muchos
emails) ni sólo por IP (un edificio entero puede estar detrás de la misma IP de su wifi/NAT; un
límite sólo por IP bloquearía a vecinos honestos entre sí). Recomiendo combinar las dos: un límite
más estricto por identificador de cuenta (email + administración o el *slug* que resuelva 1.4) y uno
más laxo por IP, como contención extra contra *credential stuffing* distribuido, no como reemplazo
del primero.

**Qué pasa si Redis está caído**: es una pregunta real, no un detalle. Fallar cerrado (negar todo
login mientras Redis no responde) convierte una caída de un componente no crítico para los datos en
una caída total del acceso, con un impacto peor que el riesgo que se quiere mitigar. Fallar abierto
(dejar pasar sin contar intentos, con una advertencia en el log) mantiene el sistema disponible a
costa de perder el candado de fuerza bruta mientras dure la caída. El propio `/api/salud` ya trata a
Redis como "degradado", no como caída dura del sistema, lo que sugiere fallar abierto es coherente
con cómo el resto del sistema ya trata a Redis, pero lo dejo como decisión explícita en la sección 6
en vez de asumirla.

---

## 5. Riesgos y casos borde (para el rompedor)

De la ficha, ya nombrados (no los repito en detalle, sólo los cito): ver un edificio de otra
administración por URL o `tenant_id`; consultar sin fijar el tenant; un `SET` sin `LOCAL` que
contagie el tenant al pedido siguiente del mismo pool; un colaborador entrando a un edificio no
asignado; un vecino abriendo pantallas del personal; fuerza bruta contra el login.

Nuevos, de esta exploración:

- **El `GRANT` olvidado en una migración nueva**: si una migración crea una tabla y nadie le otorga
  permisos a `proptech_app` (ni existe un `ALTER DEFAULT PRIVILEGES` que lo automatice), la API no
  puede leer su propia tabla nueva. No es un agujero de seguridad, es una caída total de esa
  funcionalidad, y conviene que el rompedor la pruebe explícitamente desde la primera vuelta.
- **El backup corriendo con el rol equivocado**: si en algún momento (este cambio o uno futuro)
  alguien cambia las credenciales de `respaldos` a `proptech_app` "para unificar", el volcado deja
  de ser completo sin que ningún chequeo existente lo note (ver 2.3).
- **`current_setting` sin `missing_ok`, o sin `nullif` antes de castear a `uuid`**: un tenant no
  fijado o fijado con cadena vacía tienen que dar el mismo resultado (cero filas), nunca un error
  500 en un caso y cero filas en el otro (ver 2.2).
- **El orden de las dependencias de FastAPI**: una consulta que corre antes de que la dependencia de
  autenticación haya fijado `administracion_id_actual`, si la dependencia de sesión no depende
  explícitamente de la de autenticación (ver 2.1).
- **Una tarea del worker sin `administracion_id` validado** (un trabajo viejo encolado antes de este
  cambio, o armado a mano): tiene que fallar cerrado, nunca ejecutar "sin tenant" ni inventar uno
  (ver 2.1, a diferencia del patrón de `request_id`).
- **El rompedor prueba el aislamiento con un identificador con formato válido mal etiquetado**
  (L-017): un `administracion_id`/edificio que sea un UUID válido pero de otra administración, no
  un valor malformado que ya rechaza la validación de Pydantic/FastAPI antes de llegar a la base.
  Probarlo con un valor inválido no prueba la policy de RLS, prueba otra capa.
- **El límite de intentos golpeando a todo un edificio por IP compartida** (ver sección 4): varios
  vecinos detrás del mismo NAT de wifi no se tienen que bloquear entre sí.
- **El rollback de una acción también tiene que deshacer su fila de auditoría**: si la escritura
  falla, no puede quedar un registro de auditoría de algo que nunca pasó (ver sección 3).
- **El login eligiendo la cuenta equivocada cuando el mismo email existe en dos administraciones**
  (ver 1.4): mientras no esté resuelto, es un caso que el rompedor no puede ni probar todavía porque
  el comportamiento esperado no está definido.

---

## 6. Preguntas abiertas nuevas

Sólo las que bloquean avanzar al *design* de este cambio:

1. **¿Cómo elige el login a qué administración entra cuando el mismo email tiene cuenta en más de
   una?** (sección 1.4). Sin esto no se puede terminar de diseñar el formulario de login de ninguno
   de los dos perfiles. **Decisor sugerido**: Juani y Alberto (es parte del "método de login" que la
   propia ficha pide resolver en este explore).
2. **¿Se adelanta en este cambio un envío de mail mínimo (para enlace mágico o invitación), o el
   login evita el mail por completo hasta el cambio 13?** (sección 1.3). Define si la recomendación
   de 1.1/1.2 es viable tal cual o si hay que ajustarla a contraseña con reset asistido para los dos
   perfiles. **Decisor sugerido**: Juani y Alberto (cambia el alcance y el orden del roadmap).

No bloquean el *design*, pero quedan nombradas para resolverlas ahí, no asumidas: si
`proptech_migrador` tiene `BYPASSRLS` para sembrar datos de varias administraciones (2.3); si el
alcance por edificio se refuerza con una segunda policy de RLS o queda sólo en la aplicación (2.5);
si el límite de intentos falla abierto o cerrado cuando Redis no responde (sección 4); quién puede
leer la tabla de auditoría (sección 3).

---

## 7. Partición: ¿conviene dividir el cambio 2?

Sí, lo recomiendo, con el mismo criterio que partió el cambio 1 en 1a-1d: piezas con perfil de
riesgo distinto se revisan mejor por separado.

- **2a `aislamiento-con-rls`**: los dos roles de base, las policies, `SET LOCAL` en la API y el
  worker, las tablas mínimas (administración, complejo, unidad, persona, asignación por rol),
  404/403 por alcance, el mecanismo de auditoría (tabla + helper). Es el núcleo de seguridad, se
  puede construir y probar por completo con fixtures que simulan un tenant ya autenticado, **sin
  que exista ningún login real todavía**. Es la parte que mejor se beneficia de un ciclo completo
  de constructor/rompedor/auditor sin que la discusión de "qué método de login" lo frene ni lo
  distraiga.
- **2b `login-y-sesion`**: el método elegido en la sección 1 (formulario, hashing o enlace mágico,
  sesión del lado de Next.js por D-036), el límite de intentos de la sección 4 y la auditoría de
  login exitoso/fallido sobre la tabla que ya dejó 2a. Depende de 2a (necesita el modelo de roles y
  el candado de RLS para resolver a qué administración entra cada login).

La razón de fondo para partirlo: 2a es irreductiblemente crítico y testeable de punta a punta sin
pantallas ni decisiones de producto; 2b mezcla una decisión más de costo/producto (contraseña vs
Clerk vs enlace mágico, y la pregunta del mail de la sección 1.3) con la implementación en sí, y
conviene que esa discusión no retrase ni se mezcle con la aprobación del candado de datos. Las dos
partes siguen siendo CRITICAL (D-094): ninguna se construye sin la aprobación escrita de un socio.

---

## Para Juani y Alberto, resumen de 10 líneas

- Recomendación de login: **contraseña propia** para el personal (no Clerk, por costo D-043 y por
  no sumarle a P12 un tercero que reciba emails del personal) y **enlace mágico** para el vecino (es
  lo que pide HU-V1 tal cual está escrita), pero los dos dependen de resolver si este cambio
  construye un envío de mail mínimo o si se evita el mail del todo con reset/alta asistida por el
  titular. **Esto queda como decisión de ustedes, no está tomada.**
- Nuevo hallazgo que bloquea: **no hay forma definida de elegir a qué administración entra un login
  cuando el mismo email tiene cuenta en dos** (D-096 lo permite, nadie definió el mecanismo).
- El patrón de `SET LOCAL` para RLS ya existe en el código para `application_name`: se puede copiar
  casi literal para el tenant, con dos gotchas de PostgreSQL (`missing_ok` y `nullif` antes de
  castear a `uuid`) y uno de arquitectura (dos roles de base nuevos, que tocan `configuracion.py`,
  `compose.yaml` y hay que cuidar que `respaldos` **no** pase a usarlos).
- Recomiendo partir el cambio en **2a (el candado de RLS, testeable sin login)** y **2b (el método
  de login en sí)**, igual que se partió el cambio 1.
