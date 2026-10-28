## Context

Ver `proposal.md` ("Why") para la motivación y `.git/informes-regresion/02-acceso.md` para el
diagnóstico del bucle. Lo que condiciona el cómo:

- **Dos guardas en la API** (`proptech_api/acceso.py`): `token_de_sesion_actual` verifica el token sin
  red ni base (401 sin SQL si falla) y `identidad_actual` resuelve la persona con
  `acceso/aplicacion/identidad.py::resolver`. Hoy **todo** rechazo de `resolver` es
  `IdentidadNoDisponible` → 401: sin persona (línea 36), varias sin elegir (45-46), selector no UUID
  (51-52), administración ajena (54-55) y persona sin asignación (58-69, con `ingreso_fallido`).
- **`GET /api/sesion`** (`proptech_api/sesion.py`) usa sólo la guarda de token y llama a
  `acceso/aplicacion/sesion.py::consultar`: sin persona → `IdentidadNoDisponible` → 401; con personas
  pero todas sin asignación → **200 con `administraciones: []`** (el `continue` de la línea 26).
- **Quién pide `/api/sesion` en la web**: `elegir-administracion/page.tsx:14` y también
  `web/src/app/layout.tsx:19-20`, que la pide en toda ruta que empieza con `/edificios` o `/personal`
  y la pone en `SesionDePantalla` (contexto de cliente con nombre y administraciones). Esa lista de
  rutas protegidas es el segundo llamador, y nunca puede incluir `/sin-acceso` (AR-8).
- **La web** (`web/src/lib/api/cliente.ts::pedirApi`) es el único cliente de la API: sesión de Clerk
  nula → `irAlIngreso()` (línea 98); 401 → `irAlIngreso(sesion.regreso)`; 403 → `sin_permiso` leyendo
  `detail.permiso_faltante`. El `regreso` sale de `x-proptech-ruta` (`web/src/proxy.ts:14`) y lo
  filtra `regresoSeguro` (`web/src/lib/sesion.ts:19-29`), que sólo exige "ruta propia".
- **Los 403 de hoy**: `{"detail": {"detalle": "sin_permiso", "permiso_faltante": …}}` en
  `complejos.py:95`, `:681` y `personal.py:52` (modelo `Error403` en `proptech_api/errores.py:13-19`),
  y uno con `detail="sin_permiso"` como texto en `complejos.py:265`. No hay hoy ningún discriminador
  declarado: `pedirApi` sólo mira `permiso_faltante`.
- **El ciclo**: `/elegir-administracion` pide `/api/sesion` → 401 → `/ingresar?regreso=
  /elegir-administracion?regreso=…` → `<SignIn forceRedirectUrl={destino}>` con la sesión de Clerk
  activa navega solo a `/elegir-administracion?regreso=<lo anterior>` → otra vuelta, con una capa más
  de codificación por vuelta. QA-2d lo simuló con el `regresoSeguro` real: 82, 127, 178… caracteres,
  más de 8 KB en la vuelta 47.
- **Las e2e** no cargan el widget de Clerk (`web/e2e/prueba.ts:26` aborta la red hacia Clerk, L-032):
  firman tokens locales y la API falsa (`web/e2e/api-falsa.ts:400-432`) decide por `sub`. La arista que
  anida (`/ingresar` → selector) la ejecuta el widget, así que **ninguna e2e puede verla** (QA-1).
- **El ejemplo** (`complejos/aplicacion/ejemplo.py`) crea administración, persona y asignación con SQL
  directo (líneas 124-142 y 346-350), excepciones declaradas en
  `tests/unitarios/test_fronteras_de_modulos.py:500-512`. Los ids fijos `ADMINISTRACION_EJEMPLO_ID` y
  `PERSONA_SUPER_ADMIN_EJEMPLO_ID` viven en `ejemplo.py:64-65`, y `acceso` no puede importar
  `complejos` (`test_acceso_no_importa_complejos`). El único `UPDATE` de `persona.clerk_usuario_id` es
  el de aceptar una invitación (`acceso/aplicacion/invitaciones.py:117-121`).
- **La invitación** (`web/src/app/invitacion/[sobre]/page.tsx:20`) sólo mira si **hay** sesión, no de
  quién es, y `/invitacion/*` se dibuja **sin** `ClerkProvider` (`layout.tsx:18,32`): ahí no hay
  `useUser()`. El backend rechaza con el 404 uniforme (`invitaciones.py:95-115`).
- **Reinvitar** (`acceso/aplicacion/usuarios.py:42-43`): `INSERT … ON CONFLICT (administracion_id,email)
  DO NOTHING`, así que el nombre nuevo se descarta. La misma función la usa el alta de vecinos.
- **La matriz y la auditoría están atadas**: `Accion` es a la vez el permiso y el vocabulario de
  auditoría, y `test_auditoria_tabla.py:550-564` exige que `accion_de_auditoria` en la base sea
  exactamente `Accion ∪ eventos`. Una acción nueva en la matriz es una migración del vocabulario.
- **`/personal`** hoy es binaria: `GET /api/personal` exige `invitar_usuarios_y_asignar_edificios`
  (sólo super admin, `personal.py:34,162-166`) y `listar_personal` (`usuarios.py:215`) devuelve todas
  las personas del tenant con todas sus asignaciones, vecinos incluidos.

## Goals / Non-Goals

**Goals:**

- Que el ciclo no pueda armarse por **dos** caminos independientes: el contrato (403 distinto del 401)
  y la web (el selector no rebota, el `regreso` no apunta a pantallas de acceso). Cualquiera de los dos,
  solo, ya corta el 431.
- Que el estado "autenticado sin acceso" sea uno solo, con una sola pantalla, sin importar si falta la
  persona o faltan las asignaciones.
- Que entrar con el ejemplo sea un comando repetible, no un `UPDATE` a mano.
- Cerrar los cuatro ítems de acceso que D-130 le dio al 2d: B-3, 2.3, 2.4 y 2.5/P66.

**Non-Goals de diseño:**

- No se cambia la verificación del token ni la anti-enumeración de las invitaciones (404 uniforme).
- No se agrega un contador de redirecciones ni estado en cookies para cortar ciclos.
- No se crea un endpoint nuevo: `/api/sesion` sigue siendo la única lectura de la sesión, y 2.3 la
  amplía en vez de sumar otra.
- No se le da a la API ninguna forma de saber el email de la cuenta para la pantalla nueva ni para la
  invitación.
- No se mueve la autoridad: la web oculta controles, la API sigue decidiendo cada 403.

## Decisions

### D1 · 403 con `codigo: sin_acceso`, precedencia sobre la elección, y `codigo` como discriminador de todo 403 (E1)

**Qué**: `acceso/aplicacion/identidad.py` suma `SinAcceso(Exception)`, distinta de
`IdentidadNoDisponible`. `consultar` lanza `SinAcceso` cuando no hay personas o cuando la lista de
administraciones queda vacía, en vez de devolver `[]`. En `proptech_api`, un solo traductor convierte
`SinAcceso` en `HTTPException(403, detail={"codigo": "sin_acceso"})`, usado por `identidad_actual` y por
`GET /api/sesion`. Se conservan los efectos de hoy: la línea de log `ingreso_sin_vinculo` sin datos
personales y la fila `ingreso_fallido` de la persona elegida sin asignación.

**Orden de las comprobaciones en `resolver`** (BE-1, AR-1, QA-4), escrito como contrato:

1. Personas vinculadas al `sub`. Si no hay ninguna: log `ingreso_sin_vinculo` y `SinAcceso`, sin mirar
   el selector.
2. Elección, igual que hoy: sin selector y más de una persona, selector que no es UUID o administración
   sin candidata son "rechazo de elección" **sin persona elegida**. Con una persona elegida (la única o
   la del selector) sin asignaciones: fila `ingreso_fallido` en su administración y rechazo.
3. Ante cualquier rechazo del paso 2 se pregunta si **alguna** persona del `sub` tiene asignaciones,
   abriendo una sesión por administración **vinculada** (nunca la del selector si no es una de ellas).
   Si ninguna: `SinAcceso` (403). Si alguna: `IdentidadNoDisponible` (401).

Consecuencias que quedan en el spec: el 403 `sin_acceso` **prevalece** sobre los rechazos de elección
(selector ajeno, no UUID, varias sin elegir); una identidad con dos vínculos sin asignaciones y sin
selector recibe 403 y **ninguna** fila `ingreso_fallido`, porque no se llegó a elegir persona (BE-8:
la fila es de la persona elegida, no de "toda persona sin asignación"). El caso es alcanzable sin
buscarlo: la cookie de la administración es del navegador, no de la cuenta, y una segunda cuenta sin
acceso en el mismo navegador manda el selector de la primera (BE-1). Las specs que hoy dicen 401 para
ese caso se modifican en el mismo change: `autorizacion-por-rol` ("Sin identidad no hay acceso ni
consultas"), `gestion-de-usuarios` ("Quitar la única asignación") y `aislamiento-por-administracion`
("La administración nunca sale del cliente").

**`codigo` es el discriminador de todo 403** (AR-6): todo 403 de la API lleva `detail.codigo` de una
lista cerrada declarada una vez (`sin_acceso`, `sin_permiso`). Los 403 de permiso suman
`"codigo": "sin_permiso"` junto a `detalle` y `permiso_faltante`, que se quedan para no romper a nadie;
el de `complejos.py:265` pasa de texto a ese mismo objeto. `Error403` en `errores.py` se actualiza y
`pedirApi` lee **sólo** `codigo`: `sin_acceso` → `/sin-acceso`; cualquier otro valor, o ninguno →
`sin_permiso` con el permiso que venga o "desconocido". Así 2.3 y lo que venga después suman estados
sin que la web tenga que adivinar por la forma del cuerpo.

**Por qué un solo cuerpo para "sin persona" y "persona sin asignaciones"** (BE-2): porque la pantalla es
una sola y la persona no puede hacer nada distinto en un caso y en otro. **No** es para esconderle a
quien pide si alguna vez estuvo vinculado: los dos caminos no tardan lo mismo (el segundo abre sesiones
y escribe auditoría) ni dejan los mismos rastros internos, y el único que puede medir la diferencia es
el dueño del token, sobre su propia cuenta. El spec promete código, cuerpo y cabeceras iguales, no
tiempos.

**Anti-enumeración**: la respuesta depende sólo de las filas vinculadas al `sub` del propio token. No se
lee nada por email, el cuerpo es una constante y no lleva nombres ni cantidades.

**Alternativas descartadas**:

- *Un tercer estado de sesión en `sesionActual()`*, como proponía la ficha 2d
  (`12_fichas_de_changes.md:320-323`) (AR-5): `sesionActual()` sólo ve a Clerk; no puede saber si hay
  persona sin preguntarle a la API, y el proxy no decide nada (`proxy.ts` sólo pone `x-proptech-ruta`
  y la CSP). Decidir en la web exigiría duplicar en Next la regla que ya vive en `resolver`.
- *`/api/sesion` responde 200 con `persona: null` y lista vacía, y las rutas de dominio siguen en 401*:
  arregla el selector pero no las pantallas de dominio, y deja dos formas de decir lo mismo.
- *401 con un código en el cuerpo o una cabecera*: 401 significa "autenticate" para cualquier cliente y
  para Clerk; mezclar los dos sentidos en un mismo código es lo que armó el bucle.
- *404 o 409*: 404 ya significa "no existe o no es tuyo" (2a) y 409 es conflicto de escritura.
- *El selector manda (401) aunque no haya acceso en ninguna* (opción b de BE-1): deja a la segunda
  cuenta del mismo navegador rebotando contra el 401 de la primera, que es el bucle por otro camino.
- *Reusar `detalle` como discriminador en vez de sumar `codigo`*: `detalle` ya existe, pero hoy viaja
  como texto en un caso y como clave de objeto en otro, y el 403 nuevo nació con `codigo`; tener dos
  nombres para el mismo papel es peor que sumar una clave.

**Costo de revertir**: medio. El traductor y la excepción se sacan en un commit, pero la web ya
depende de `codigo`: revertir exige revertir D4 junto, y el ciclo vuelve salvo por D2/D3. Sacar `codigo`
de los 403 de permiso es inocuo para la web vieja, que nunca lo leyó.

### D2 · El selector recibe el 401 y la sesión nula en vez de redirigir (E2)

**Qué**: `pedirApi` suma una opción `alNoAutenticar: "redirigir" | "devolver"` (por defecto
`"redirigir"`, el comportamiento de hoy). Con `"devolver"`, **los dos** caminos que hoy van a
`/ingresar` devuelven `{ estado: "sin_sesion" }`: el 401 de la API y la sesión de Clerk nula en el
servidor (`if (!sesion) return irAlIngreso()`, `cliente.ts:98`) (QA-2). Sólo
`elegir-administracion/page.tsx` y su `elegirAdministracionAction` usan `"devolver"`; la página muestra
"No pudimos validar tu sesión" con un enlace "Cerrar sesión" a `/ingresar?cerrar=1` (el mecanismo que
ya usan `CuentaEnBarra` y la invitación). Ante el 403 `sin_acceso`, `pedirApi` redirige a `/sin-acceso`
en cualquier pantalla, también en el selector.

**Por qué alcanza**: el selector es el nodo del ciclo que vuelve a `/ingresar` con la sesión de Clerk
activa. Si ahí ni un 401 ni una sesión nula vuelven a `/ingresar`, el ciclo pierde esa arista. Las
pantallas de dominio y el layout siguen yendo a `/ingresar` ante un 401, que con sesión de Clerk termina
en el selector.

**Alternativas descartadas**:

- *Ante todo 401 con sesión de Clerk activa, ir a `/ingresar?cerrar=1`*: corta el ciclo, pero cierra
  la sesión de quien sólo tiene que elegir administración.
- *Dejarlo como hoy y confiar sólo en D3*: sin anidamiento el 431 desaparece, pero el ping-pong sigue
  sin crecer y sin un corte garantizado: la vuelta `/ingresar` → selector es una navegación del cliente
  de Clerk, no un 3xx, y nada asegura que el navegador la cuente como "demasiadas redirecciones"
  (QA-2d, confianza baja-media).
- *`"devolver"` sólo para el 401* (opción b de QA-2): deja la sesión nula como segunda salida al
  ingreso, que ningún test vería.

**Costo de revertir**: bajo. Es una opción con valor por defecto.

### D3 · `regresoSeguro` rechaza las pantallas de acceso y pone el tope sobre la salida (E3)

**Qué**: después de la normalización con `new URL` que ya hace, `regresoSeguro` decodifica las
secuencias `%XX` del `pathname` (con `decodeURIComponent` dentro de un `try`: una secuencia rota da
`/edificios`) y compara el resultado, sin barra final, contra la lista cerrada `/ingresar`,
`/registrarse`, `/elegir-administracion`, `/sin-acceso` y cualquier ruta debajo de ellas
(`/ingresar/…` es el `[[...paso]]` de Clerk). Si coincide, devuelve `/edificios`. El tope de 512 se
aplica **dos veces**: a la entrada (para no normalizar textos enormes) y a la **salida** ya armada
(QA-3), porque `new URL` codifica los caracteres no ASCII y `{`: 111 caracteres de entrada pueden dar
611 de salida, y con el tope sólo en la entrada la segunda pasada daba otro resultado. Con el tope sobre
la salida, normalizar dos veces da lo mismo que una, por construcción.

**Por qué decodificar**: `/%69ngresar` pasa una comparación literal y no se sabe si Next la enruta a
`/ingresar` (QA-2d, SUPUESTO sin verificar). Decodificando, la respuesta no depende de cómo enrute Next.

**Por qué 512**: la ruta propia más larga hoy es `/edificios/<uuid>/grupos/<uuid>` con un query corto,
muy por debajo; 512 deja margen y está lejos de los ~8 KB donde empieza el 431. Los bordes 512 (se
conserva) y 513 (se corta) son casos del spec, para que el mutante `>=` no sobreviva.

**Alternativas descartadas**:

- *Desenvolver el `regreso` anidado y quedarse con el más interno*: recursivo, tiene que decidir cuántas
  capas leer y reabre lo que la lista cerrada cierra en una línea.
- *Sólo el tope de largo*: el ciclo seguiría girando sin crecer.
- *Tope sólo sobre la entrada*: no es idempotente (QA-3).

**Costo de revertir**: bajo, una función pura con sus tests.

### D4 · `/sin-acceso` es una ruta propia que no pide nada a la API (E4)

**Qué**: `web/src/app/sin-acceso/page.tsx` (servidor) comprueba con `auth()` que haya sesión de Clerk;
sin sesión, `redirect("/ingresar")` sin `regreso`. Con sesión, renderiza `Pantalla.tsx` (cliente), que
usa `useUser()` dentro de `<ClerkLoaded>` para leer `primaryEmailAddress`; las dos acciones quedan
**fuera** de `<ClerkLoaded>`, para que existan aunque Clerk no cargue. La pantalla usa los componentes de
siempre (`Armazon publico`, `EncabezadoDePantalla`, `Panel`) y ofrece "Cerrar sesión"
(`/ingresar?cerrar=1`) y "Volver a intentar" (`/elegir-administracion`).

**No pide nada a la API** (QA-5, AR-8): ni la página, ni la pantalla, ni el layout. Si la página llamara
a `pedirApi` para "comprobar", el 403 `sin_acceso` la mandaría a sí misma y se armaría un bucle nuevo.
Por la misma razón la lista de rutas protegidas de `layout.tsx` (`/edificios*`, `/personal*`) nunca
incluye `/sin-acceso`; un test lo fija.

`elegir-administracion/Pantalla.tsx` pierde la rama `administraciones.length === 0`; `page.tsx`, si
alguna vez recibiera una lista vacía (no debería, por D1), redirige a `/sin-acceso`.

**Por qué el email no viene de la API ni del servidor**: el token de Clerk puede no traer el email
(`TokenVerificado.email` es opcional), y hacer que la API lo devuelva en el 403 agregaría un dato
personal a una respuesta constante. `useUser()` usa la sesión que el navegador ya tiene. El oráculo
determinista del test es que `page.tsx` no le pasa ninguna prop de email a `Pantalla` y no llama a
`currentUser` (QA-8), no "el HTML del servidor no trae el email", que depende de cómo se mockee
`ClerkLoaded`.

**Alternativas descartadas**: *un estado dentro de `/elegir-administracion`*, porque las pantallas de
dominio también llegan a este estado y el selector tiene `regreso`, que acá no significa nada; *mostrar
el estado vacío actual*, porque sin el email y sin "Cerrar sesión" la persona no tiene cómo darse cuenta
de que entró con otra cuenta.

**Costo de revertir**: bajo, una ruta nueva y una rama de `pedirApi`.

### D5 · `--clerk-usuario` vincula al `super_admin` del ejemplo, con dos trabas antes de conectarse (E5)

**Qué**: `_main` lee la opción como texto plano (**sin** `type=` ni `choices` de `argparse`, que repiten
el valor rechazado en su error y corren antes de la guarda, BE-7) y, en este orden y antes de crear el
engine:

1. La guarda de D-112 (`PROPTECH_ENTORNO=desarrollo`), como hoy.
2. El formato: `re.fullmatch(r"user_[A-Za-z0-9]{1,64}", valor, flags=re.ASCII)`, el mismo patrón que
   `acceso/dominio/token.py:12` y el `CHECK ck_persona_clerk_usuario_id` de `0019`.
3. **La instancia de Clerk es de desarrollo** (BE-6, opción a, decisión de Juani): `CLERK_EMISOR`
   configurado, con esquema `https`, sin puerto ni ruta, y un host que **termina** en
   `.clerk.accounts.dev`. Se compara con `urllib.parse.urlsplit(...).hostname.endswith(...)`, nunca con
   `in` sobre el texto (que aceptaría `clerk.accounts.dev.otro.invalid`). Sin emisor, se niega.

Ningún mensaje repite el id ni el emisor. Sin `--clerk-usuario`, los pasos 2 y 3 no corren y la carga es
la de hoy.

**Por qué el emisor es la señal**: es lo que la API usa para aceptar o rechazar los tokens del `sub` que
se vincula, así que está atado a lo que se escribe: un vínculo con una instancia de producción sólo
sirve si el emisor es de producción. `PROPTECH_ENTORNO` lo pone el operador (`docker compose exec -e
PROPTECH_ENTORNO=desarrollo …`, la forma que documenta `infra/.env.example:38-40`), y en producción esa sola variable dejaba
un login `super_admin` persistente en el tenant del ejemplo. Señales evaluadas y no elegidas: el prefijo
`sk_test_` de `CLERK_SECRET_KEY` (el comando no la necesita y puede no estar configurada) y la clave
publicable (vive en la web, no en la API). La convención "las instancias de desarrollo de Clerk usan
`*.clerk.accounts.dev`" está respaldada en el repo (fixtures `pk_test_` con ese dominio y la de
producción con `pk_live_` y otro dominio, `web/e2e/configurar-clerk.sh:17-18`, `infra/ci/humo.sh:18`) y
el `CLERK_EMISOR` del entorno local de Juani termina en ese dominio; que Clerk lo garantice para toda
instancia es un **SUPUESTO** que la tarea 5.1 deja anotado con la fuente.

**La vinculación**: `cargar()` recibe `clerk_usuario: str | None` y, dentro de la misma transacción con
el tenant de ejemplo, después de crear o comparar el ejemplo, llama a la función de vinculación de
desarrollo de `acceso.aplicacion`. Esa función:

- **sólo acepta** la administración y la persona fijas del ejemplo (BE-5 a, AR-4): los ids
  `ADMINISTRACION_EJEMPLO_ID` y `PERSONA_SUPER_ADMIN_EJEMPLO_ID` se mudan a un módulo de `acceso`
  (`acceso` no puede importar `complejos`) y `ejemplo.py` los importa de ahí; con cualquier otro id la
  función se niega sin escribir.
- **sólo puede importarse desde `complejos/aplicacion/ejemplo.py`** (BE-5 b, AR-4 a): regla nueva por
  lista permitida en el test de fronteras, del mismo estilo que D-116, con mutantes (un import desde
  `proptech_api/sesion.py` y otro desde `acceso/aplicacion/invitaciones.py`).
- **comprueba la unicidad antes de escribir** (BE-3): si otra persona de la administración de ejemplo ya
  tiene ese `sub` (el mismo chequeo `identidad_ajena` de `invitaciones.py:105-115`), termina con un
  mensaje propio, sin traceback y sin el id. Hoy `crear_engine` no usa `hide_parameters` y `_main` sólo
  captura `EjemploDistinto`: un `IntegrityError` imprimiría `[parameters: ('user_…', …)]`.
- **escribe con un `UPDATE` condicional** (BE-4): `UPDATE persona SET clerk_usuario_id = :sub WHERE id
  = :persona AND (clerk_usuario_id IS NULL OR clerk_usuario_id = :sub)` y mira `rowcount`: 0 filas es
  "ya está vinculado a otra cuenta", sin pisar. Leer y después escribir dejaba que dos corridas a la vez
  leyeran las dos `NULL` y la segunda pisara a la primera.

La salida dice "vinculado", "ya estaba vinculado", "ya está vinculado a otra cuenta" o "esa cuenta ya
está vinculada a otra persona del ejemplo", sin ids. El `README` suma "Entrar con el edificio de
ejemplo": crear la cuenta en el Clerk de desarrollo, copiar su id del panel (Users → la cuenta → User
ID), correr el comando y entrar; con `user_XXXXXXXX` como marcador (L-040).

**Alternativas descartadas**: *un comando aparte `ejemplo vincular`*, porque duplica la guarda, la
conexión y el tenant fijo; *pisar el vínculo si es distinto*, porque un id mal copiado dejaría afuera
sin aviso a quien ya entraba; *crear una invitación y aceptarla*, porque exige el worker y el mail de
Clerk; *duplicar la guarda de entorno dentro de la función* (BE-5 c, AR-4 b), porque acopla `acceso` a
`PROPTECH_ENTORNO`; *capturar `IntegrityError` con un mensaje fijo* en vez del chequeo previo, porque
el chequeo previo da un mensaje que dice qué pasó y no depende del formato de error del driver.

**Costo de revertir**: bajo, una opción del comando, una regla del test de fronteras y su sección del
`README`.

### D6 · La vinculación de desarrollo no se audita (E6)

**Qué**: no se agrega un evento a `accion_de_auditoria` por la vinculación. El control son las dos
trabas de D5 (entorno e instancia de desarrollo), la función que sólo conoce al ejemplo y la salida del
comando.

**Por qué**: la vinculación sólo puede escribir el `super_admin` del ejemplo de una instancia de
desarrollo de Clerk; no hay un actor distinto del operador que corre el comando, ni un tenant real
afectado. El costo de la migración ya no es el argumento principal: si E11 se aprueba como se recomienda,
el change ya tiene una migración del vocabulario (`ver_personal`, D13), y sumar un evento ahí costaría
casi lo mismo. Se recomienda no auditar porque no hay qué reconstruir después con esa fila.

**Alternativa**: evento `vincular_identidad_de_desarrollo` en la misma migración `00NN` de D13 (o en una
propia si E11 no se aprueba así), con su escenario en `auditoria-de-acciones`. **Costo de revertir** la
recomendación: agregar el evento después cuesta una migración de una línea.

### D7 · La escritura de `acceso` del ejemplo pasa a `acceso.aplicacion` (E7)

**Qué**: `acceso/aplicacion/alta_inicial.py` ya hace lo mismo que `ejemplo.py:124-151` con otra
fuente de ids. Se extrae una función de `acceso.aplicacion` que, en una sesión ya abierta con el tenant
puesto, crea la administración, la persona `super_admin` y su asignación con ids opcionales dados y
registra `alta_inicial`; la usan `alta_inicial.crear` (sin ids) y `ejemplo.cargar` (con los ids fijos y
el `ON CONFLICT DO NOTHING` que hoy da la idempotencia de la carrera). La vinculación de D5 es otra
función de `acceso.aplicacion`. El `INSERT INTO administracion` de `cargar()` se mueve con la primera.
Salen las tres excepciones de `ejemplo.py` del test de fronteras.

**Por qué recomendado**: D5 obliga a escribir `persona` desde el comando del ejemplo. Hacerlo con SQL
en `complejos` agrandaría la violación de D-021 justo en el código CRITICAL que se está tocando. La
función compartida además aplica L-009: el alta inicial y el ejemplo dejan de poder divergir en el
tramo administración, persona y asignación (la invitación y las validaciones siguen siendo propias de
cada uno, AR-2d).

**Riesgo**: la idempotencia del ejemplo depende de que el `INSERT INTO administracion … ON CONFLICT DO
NOTHING RETURNING id` siga siendo lo primero de la transacción. La función extraída devuelve si ganó la
carrera; los 10 tests de `test_ejemplo_casos_de_uso.py` (incluido "dos cargas a la vez") son el
baseline, y los mutantes M5 a M8 de QA-2 se corren antes y después para mostrar que no empeoran.

**Alternativas descartadas**:

- *Dejarlo como deuda y escribir sólo la vinculación en `acceso.aplicacion`*: más chico, pero deja el
  ejemplo con SQL de `acceso` en dos lugares y la excepción del test viva.
- *Mover `ejemplo.py` a una raíz de composición* (AR-5 del PR #1, que D-116 del 26/10/2026 dejó
  "para cuando se toque ese archivo", y este change es el que lo toca) (AR-2): se descarta porque en
  composición el test de fronteras sólo vigila las tablas del libro, así que mover el archivo
  **escondía** el SQL de `acceso` del escaneo en vez de sacarlo; además el comando seguiría siendo dueño
  de escrituras de `acceso` que `alta_inicial.py` ya hace. Si más adelante se quisiera ese camino, el
  costo es una mudanza de archivo más un cambio de spec, porque el delta de `fronteras-de-modulos` fija
  `complejos/aplicacion/ejemplo.py` como ubicación sin excepción: **costo de revertir hacia AR-5**,
  medio (mover el archivo, la ruta `python -m proptech_core.complejos.aplicacion.ejemplo` que
  documentan `infra/.env.example:36` y el `README`, y el escenario del spec).

**Costo de revertir** la recomendación: medio, una extracción con dos llamadores.

### D8 · El recuadro de Clerk se reproduce antes de arreglarse, y el rojo inyecta el ancho mínimo (E9)

**Qué**: con el Clerk de desarrollo real, se abre `/ingresar` a 320 px y a 1280 px y se registra, con
captura: el ancho del contenido de `.panel` dentro de `.pagina-acceso` (`tokens.css:1779-1792`, con
`container-type: inline-size` desde la línea 821), el ancho de `.cl-cardBox` y si hay desbordamiento.
La hipótesis (≈248 px disponibles a 320 contra un mínimo de Clerk de ~350 px) se confirma o se descarta
con esos números. Si no se reproduce, la tarea se cierra con las capturas y las medidas, sin tocar CSS.

**El oráculo automático** (QA-6): "sin desplazamiento horizontal" no discrimina, porque sin el widget
el panel sólo tiene el aviso de espera, y un recorte no produce scroll. El rojo en e2e inyecta con
`page.evaluate`, dentro de `.panel`, un bloque del ancho mínimo medido en 4.1 para `.cl-cardBox`, a
320 px **y a 1280 px**, y afirma que su borde derecho queda dentro del área de contenido del panel y que
`panel.scrollWidth <= panel.clientWidth`. Hoy tiene que fallar si la hipótesis es cierta.

**Alternativa descartada**: tocar CSS a ciegas con la hipótesis; es la misma regla que B-2 del 3c.
**Costo de revertir**: bajo, CSS.

### D9 · Los cuatro ítems de acceso quedan dentro del 2d (E8)

**Qué**: B-3, 2.3, 2.4 y 2.5/P66 se construyen en este change, como asignó D-130 el 28/10/2026, con
requisitos, specs y tareas propias (D10 a D13, grupo 7 de `tasks.md`). No se crea ningún change nuevo.

**Por qué**: los cuatro son dominio `acceso`, CRITICAL, y comparten firmante, revisores obligatorios y
superficie con el bucle: 2.3 amplía `/api/sesion`, que este change estabiliza, y su respuesta tiene que
convivir con el 403 `sin_acceso`; B-3 es la misma pantalla de invitación que el ingreso; 2.5 cambia la
matriz que el 403 de permiso nombra. Partirlos dejaba un change CRITICAL sin ficha, número ni firmante
que dependía de éste (AR-3), y a B-3, que es un defecto del ingreso, vivo hasta entonces.

**Alternativa descartada**: sacarlos a un change de acceso propio (lo que proponía la versión anterior
de este propose). **Costo** de esa alternativa: un segundo ciclo CRITICAL completo (propose, revisores,
firma, verify) sobre los mismos archivos (`sesion.py`, `cliente.ts`, `permisos.py`), con el riesgo de
volver a abrir `/api/sesion` en otra dirección después de firmado este contrato. **Costo de revertir**
esta decisión: medio; el grupo 7 de tareas es separable, pero las specs de `autorizacion-por-rol` y
`gestion-de-usuarios` ya se escribieron juntas.

**Tamaño**: el change pasa de 19 a 30 tareas, por encima de las "unas veinte" de `openspec/config.yaml`,
que dice que un cambio así se parte. Juani decidió no partirlo en changes (decisión del 28/10/2026); lo
que sí se hace es construirlo en dos vueltas con su PR cada una, dentro del mismo change (ver
`tasks.md`). Queda escrito para el firmante.

### D10 · B-3: la invitación dice con qué cuenta se está, sin leer el destinatario (E10)

**Qué**: `invitacion/[sobre]/page.tsx` (servidor), cuando hay sesión, lee el email del claim firmado del
token de sesión (`auth().sessionClaims`, el mismo token que la API acepta en
`POST /api/invitaciones/aceptar`, que exige `token.email`) y se lo pasa a `PantallaInvitacion`. Con
sesión la pantalla dice "Estás ingresado como <email>" antes de "Aceptar e ingresar" y ofrece "Usar otra
cuenta" (el enlace con `cerrar=1` que la página ya arma, `page.tsx:21`). Si la aceptación falla con
sesión, el mensaje cambia a "Este enlace no sirve con la cuenta <email>. Si la invitación es para otro
email, usá otra cuenta; si es para ésta, pedile a tu administración que te invite de nuevo." Sin claim de
email, los textos no nombran ningún email. La API **no cambia**.

**Por qué el servidor y no `useUser()`**: `/invitacion/*` se dibuja sin `ClerkProvider` a propósito
(`layout.tsx:18,32`); el claim ya está en el servidor sin red ni clave secreta.

**Alternativas descartadas** (son las opciones de E10):

- *(c) Una lectura nueva que, con el sobre, devuelva el email destinatario (enmascarado o no)*, como
  proponía el QA del 3c: abre una superficie nueva de la API que tiene que mantener la anti-enumeración
  del 404 uniforme, para darle a la persona un dato que ya tiene en su bandeja (el mail de la
  invitación).
- *(b) Avisar que hay una sesión abierta sin decir de quién*: más simple, pero no le dice a la persona
  lo único que le falta saber, que es con qué cuenta entró.

**Costo de revertir**: bajo, dos textos y una prop.

### D11 · 2.3: las acciones permitidas viajan con la sesión y la web oculta lo que no se puede

**Qué**: una función pura nueva en `acceso/dominio/permisos.py`, `acciones_permitidas(asignaciones)`,
devuelve tres conjuntos: `administracion` (acciones evaluadas sin complejo: `crear_edificio`,
`invitar_usuarios_y_asignar_edificios`, `ver_personal`), `todos_los_edificios` (las que una asignación
principal permite en cualquier edificio) y `por_edificio` (por cada `complejo_id` de una asignación por
edificio o por unidad, las que suma ahí). Se calcula **con `_MATRIZ`**, la misma que usa `puede`, y un
test de propiedad compara, para las nueve columnas, cada acción y un edificio propio y otro ajeno, la
respuesta de `acciones_permitidas` contra `puede`. `consultar` ya carga las asignaciones de cada
administración (`sesion.py:25`); suma `acciones` a cada elemento de la lista. El 403 `sin_acceso` no
cambia.

En la web, `DatosDeSesion` (`componentes/SesionDePantalla.tsx`) suma `acciones` por administración, y
una función `permite(sesion, accion, complejoId?)` decide; sin sesión en el contexto, `permite` da
`false` (se oculta la escritura, nunca se muestra de más). Se ocultan: "Personal" en
`seccionesDeLaAdministracion()` (con `ver_personal`), "Nuevo edificio" (`edificios/Pantalla.tsx:84,105`,
con `crear_edificio`), "Agregar unidad" (`unidades/Pantalla.tsx:134`, con `configurar_padron`) y los
controles de escritura de las pantallas del edificio, cada uno con la acción que su ruta exige
(`configurar_padron`, `crear_version_de_configuracion`, `confirmar_sin_saldos_previos`), y los de
`/personal` (con `invitar_usuarios_y_asignar_edificios`). Las secciones de lectura del menú del edificio
siguen, porque leer es alcance y no permiso.

**Por qué en `/api/sesion` y no un endpoint nuevo**: es la única lectura de la sesión, el layout ya la
pide en cada pantalla protegida, y sumar una ruta duplicaría la guarda y el barrido.

**Alternativas descartadas**: *copiar la matriz en la web*, porque dos copias divergen y la de la web
nadie la prueba contra la de la API; *una lista plana de acciones sin edificio*, porque un administrador
por edificio vería "Agregar unidad" en edificios ajenos; *que la web pruebe la acción y oculte al
recibir 403*, porque muestra el control hasta que alguien lo toca.

**Costo de revertir**: bajo; la clave nueva es aditiva y la web vuelve a mostrar todo.

### D12 · 2.4: reinvitar el mismo email deja el nombre nuevo

**Qué**: `_persona_bloqueada` (`usuarios.py:37-51`) pasa de `ON CONFLICT … DO NOTHING` a `ON CONFLICT
(administracion_id, email) DO UPDATE SET nombre = EXCLUDED.nombre`, dentro del `begin_nested()` que ya
envuelve toda el alta: si la asignación después da 409 o 422, el savepoint se deshace y el nombre no
cambia. Vale para la persona vinculada y la no vinculada, y para el alta de vecinos, que usa la misma
función y cuyo spec ya dice "las reglas de reuso de la persona son las del personal".

**Por qué**: sólo el super admin invita, así que el nombre que pisa es el que cargó otro super admin de
la misma administración, y el último dato cargado es el que la persona que invita tiene a la vista.

**Alternativa descartada**: *avisar en la pantalla que ese email ya existe y con qué nombre* (la otra
opción de la exploración del 3c): exige una lectura nueva por email desde la web para el alta, que es
justo el tipo de lectura que este change evita.

**Costo de revertir**: bajo, una cláusula SQL.

### D13 · 2.5/P66: `/personal` jerárquica en sólo lectura para el administrador principal (E11)

**Qué** (con la recomendación de E11): una acción nueva `ver_personal` en `Accion` y en `_MATRIZ`, con
`_SA` y `_AP`, evaluada sin complejo. `GET /api/personal` exige `ver_personal`; las rutas que escriben
(invitar, alta de vecino, revocar, quitar) siguen exigiendo `invitar_usuarios_y_asignar_edificios`, sólo
super admin. `listar_personal` recibe las asignaciones de quien pide: para el super admin devuelve lo
de hoy; para el administrador principal, **filtra en la API** a las personas cuyas asignaciones son
**todas** de administrador por edificio, contador, auxiliar o consejo. Nunca aparece una persona con
una asignación de super admin, de administrador principal (pares) o de vecino, ni su id, nombre o email.
La web muestra `/personal` en sólo lectura a quien no tiene `invitar_usuarios_y_asignar_edificios`.

**Por qué una acción nueva y una migración**: `Accion` es a la vez el permiso y el vocabulario de
auditoría, y `test_auditoria_tabla.py:550-564` exige que coincidan con la base: la acción nueva es una
migración `00NN` (número provisorio; hoy la cabeza es `0027`) que suma `ver_personal` a
`accion_de_auditoria`, con su bajada. Eso convoca al **DBA**.

**Por qué sólo ver**: D-127 aprobó "ver" y dejó "gestionar" pendiente "si el change de acceso que la
construya lo decide". Gestionar toca `invitaciones.py`, el alta y la regla de quién puede quitar a
quién (incluido "no quitarle la última asignación de super admin" a nadie), que es una superficie
CRITICAL más grande; queda para una decisión aparte.

**Alternativas descartadas**:

- *Una función `puede_ver_personal` fuera de `Accion`*: evita la migración, pero deja un permiso fuera
  de la matriz, que ni `test_permisos.py` (`_MATRIZ_A_MANO`) ni D11 verían; dos fuentes de verdad.
- *Filtrar en la web*: la respuesta de la API llevaría los datos del super admin al servidor de Next y
  al navegador; D-127 dice "nunca ve".
- *Mostrar a la persona con sólo sus asignaciones de abajo* (en vez de excluirla si tiene alguna
  arriba): revela que existe y su email, que es "ver hacia arriba" por otro camino.

**Costo de revertir**: medio: la migración tiene bajada, pero sacar `ver_personal` de `Accion` toca la
matriz, su test a mano, D11 y el menú.

## Risks / Trade-offs

- [Un cliente que dependa de "todo rechazo es 401"] → El único cliente de la API es el servidor de
  Next; `pedirApi` se cambia en el mismo change. Las e2e y la API falsa se actualizan desde el contrato
  real (L-027).
- [Tests que afirman 401 para "token válido sin vínculo"] → Son el **rojo** de las tareas 2.1 y 2.2,
  incluido `test_personal_api.py:144-170` (quitar la única asignación), que pasa a 403 y suma el caso
  con acceso en otra administración (401).
- [`resolver` hace más consultas en el camino de rechazo] → Una sesión por administración vinculada,
  sólo cuando ya se va a rechazar; el camino feliz no cambia.
- [La matriz cambia] → D-130 dejó la revisión independiente de la matriz (153 celdas, ahora 162) para
  "el rompedor del primer change que toque esa zona": éste la toca (`ver_personal`), así que el verify
  la absorbe y la nombra.
- [Choque en `web/e2e/api-falsa.ts` con el 3d y el 6] → El 2d agrega sus identidades en un bloque
  propio, sin editar las secciones de PATCH/Georef del 3d; resuelve el conflicto el que mergee segundo,
  igual que con la migración `00NN`. No espera al 3d (AR-7).
- [Migración `00NN` en paralelo con el 3d y el 6] → El que mergea segundo renumera y verifica
  `alembic heads`.
- [El widget de Clerk no carga en e2e] → El anidamiento se prueba con el test de componente del ciclo
  (tarea 3.3); "dos pestañas" y "entrar por el ingreso" se verifican a mano contra el Clerk de desarrollo
  (L-032) y se declaran como tal.
- [Tamaño] → 30 tareas en un change (D9).

## Migration Plan

Con la recomendación de E11 **hay una migración**: `00NN` suma `ver_personal` al vocabulario de
`accion_de_auditoria`, con bajada que la quita (falla sin modificar datos si alguna fila de `auditoria`
la usara; no debería, porque ver no se audita), probada sobre una copia con datos. El despliegue es el
de siempre (migrar, después imagen nueva de API y web juntas) y el rollback es bajar `00NN` y volver a
la imagen anterior. API y web tienen que salir juntas: una web vieja con una API nueva lee
`permiso_faltante` como hoy y trata el 403 `sin_acceso` como `sin_permiso` (pantalla de error, sin
bucle) e ignora `acciones`; una web nueva con una API vieja no recibe `codigo` ni `acciones` (muestra
`sin_permiso` "desconocido" en los 403 y oculta toda escritura, D11), pero D2 y D3 ya cortan el ciclo.
Ninguna combinación arma el 431.

Si E6 se aprueba con la alternativa, el evento de vinculación entra en la misma `00NN`. **El que mergea
segundo** entre este change, el 3d y el 6 renumera y verifica que `alembic heads` devuelva una sola
cabeza.

## Open Questions

Ninguna que cambie specs o tareas sin firma: las decisiones abiertas son las elecciones E1 a E11 de
`proposal.md`. Si E11 se responde distinto de la recomendación ("gestionar" también, u otra definición
de "por debajo"), los deltas de `autorizacion-por-rol` (fila `ver_personal`) y de `gestion-de-usuarios`
("Listar, revocar y quitar") se reescriben antes de construir.
