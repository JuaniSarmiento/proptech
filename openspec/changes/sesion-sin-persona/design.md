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
- **La web** (`web/src/lib/api/cliente.ts::pedirApi`) es el único cliente de la API: 401 →
  `irAlIngreso(sesion.regreso)`; 403 → `sin_permiso` leyendo `detail.permiso_faltante`. El
  `regreso` sale de `x-proptech-ruta` (`web/src/proxy.ts:14`, ruta + query de la página actual) y lo
  filtra `regresoSeguro` (`web/src/lib/sesion.ts:19-29`), que sólo exige "ruta propia".
- **El ciclo**: `/elegir-administracion` (`page.tsx:14`) pide `/api/sesion` → 401 → `/ingresar?regreso=
  /elegir-administracion?regreso=…` → `<SignIn forceRedirectUrl={destino}>` con la sesión de Clerk
  activa redirige solo a `/elegir-administracion?regreso=<lo anterior>` → otra vuelta, con una capa más
  de codificación por vuelta, hasta 431.
- **El ejemplo** (`complejos/aplicacion/ejemplo.py`) crea administración, persona y asignación con SQL
  directo (líneas 124-142 y 346-350), excepciones declaradas en
  `tests/unitarios/test_fronteras_de_modulos.py:500-512`. La persona nace sin `clerk_usuario_id`; el
  único `UPDATE` de esa columna en el código es el de aceptar una invitación
  (`acceso/aplicacion/invitaciones.py:117-121`).
- **Las e2e** no cargan el widget de Clerk (`web/e2e/prueba.ts` aborta la red hacia Clerk, L-032):
  firman tokens locales y la API falsa (`web/e2e/api-falsa.ts:400-432`) decide por `sub`.

## Goals / Non-Goals

**Goals:**

- Que el ciclo no pueda armarse por **dos** caminos independientes: el contrato (403 distinto del 401)
  y la web (el selector no rebota, el `regreso` no apunta a pantallas de acceso). Cualquiera de los dos,
  solo, ya corta el 431.
- Que el estado "autenticado sin acceso" sea uno solo, con una sola pantalla, sin importar si falta la
  persona o faltan las asignaciones.
- Que entrar con el ejemplo sea un comando repetible, no un `UPDATE` a mano.

**Non-Goals de diseño:**

- No se cambia la verificación del token ni la anti-enumeración de las invitaciones (404 uniforme).
- No se agrega un contador de redirecciones ni estado en cookies para cortar ciclos.
- No se crea un endpoint nuevo: `/api/sesion` sigue siendo la única lectura de la sesión.
- No se le da a la API ninguna forma de saber el email de la cuenta para la pantalla nueva.

## Decisions

### D1 · 403 con `codigo: sin_acceso`, una excepción nueva separada de `IdentidadNoDisponible` (E1)

**Qué**: `acceso/aplicacion/identidad.py` suma `SinAcceso(Exception)`, distinta de
`IdentidadNoDisponible`. `resolver` la lanza sólo cuando **ninguna** de las personas vinculadas a ese
`sub` tiene asignaciones (incluido el caso de cero personas); los rechazos de elección (varias sin
elegir, selector no UUID, administración ajena, persona sin asignación en la elegida **cuando hay otra
con asignación**) siguen siendo `IdentidadNoDisponible`. `consultar` lanza `SinAcceso` cuando la lista
de administraciones queda vacía, en vez de devolver `[]`. En `proptech_api`, un solo traductor convierte
`SinAcceso` en `HTTPException(403, detail={"codigo": "sin_acceso"})`, usado por `identidad_actual` y por
`GET /api/sesion`. Se conservan los efectos de hoy: la línea de log `ingreso_sin_vinculo` sin datos
personales y la fila `ingreso_fallido` de la persona sin asignación (spec "Ingresos auditados").

**Orden de las comprobaciones en `resolver`**: para no cambiar qué se audita ni qué se responde a una
identidad con acceso en otra administración, primero se busca con el selector como hoy; sólo cuando el
resultado es "rechazado" se pregunta si la identidad tiene **alguna** persona con asignación. Esa
pregunta abre una sesión por administración vinculada, igual que ya hace `consultar`: pasa sólo en el
camino de rechazo y la cantidad de administraciones por identidad es chica (D-096).

**Anti-enumeración**: la respuesta depende sólo de las filas vinculadas al `sub` del propio token. No se
lee nada por email, el cuerpo es una constante y no lleva nombres ni cantidades. Lo único que aprende
quien pide es que **su** cuenta no tiene acceso, que es exactamente lo que la pantalla le va a decir.

**Alternativas descartadas**:

- *`/api/sesion` responde 200 con `persona: null` y lista vacía, y las rutas de dominio siguen en 401*:
  arregla el selector pero no las pantallas de dominio, que seguirían mandando a `/ingresar` a una
  cuenta que nunca va a poder entrar; y deja dos formas de decir lo mismo.
- *401 con un código en el cuerpo o una cabecera*: 401 significa "autenticate" para cualquier cliente y
  para Clerk; mezclar los dos sentidos en un mismo código es lo que armó el bucle.
- *404 o 409*: 404 ya significa "no existe o no es tuyo" en las rutas de dominio (2a), y 409 es
  conflicto de escritura. 403 es "sé quién sos y no podés", que es el estado.
- *Distinguir "sin persona" de "persona sin asignación" con dos códigos*: la pantalla es la misma y la
  diferencia le diría a quien pide si alguna vez estuvo vinculado; no aporta nada a la persona.

**Costo de revertir**: medio. El traductor y la excepción se sacan en un commit, pero la web ya
depende del estado `sin_acceso`: revertir exige revertir D4 junto, y el ciclo vuelve salvo por D2/D3.

### D2 · El selector recibe el 401 en vez de redirigir (E2)

**Qué**: `pedirApi` suma una opción `alNoAutenticar: "redirigir" | "devolver"` (por defecto
`"redirigir"`, el comportamiento de hoy). Sólo `elegir-administracion/page.tsx` y su
`elegirAdministracionAction` usan `"devolver"`: con 401 reciben `{ estado: "sin_sesion" }` y la página
muestra "No pudimos validar tu sesión" con un enlace "Cerrar sesión" a `/ingresar?cerrar=1` (el
mecanismo que ya usan `CuentaEnBarra` y la invitación). Ante el 403 `sin_acceso`, `pedirApi` redirige a
`/sin-acceso` en cualquier pantalla, también en el selector.

**Por qué alcanza**: `/elegir-administracion` es el único nodo del ciclo que pide `/api/sesion` con la
sesión de Clerk activa; si ahí un 401 no vuelve a `/ingresar`, el ciclo pierde una arista y no hay
otra forma de cerrarlo. Las pantallas de dominio siguen yendo a `/ingresar` ante un 401, que con
sesión de Clerk termina en el selector (spec "Una pantalla de dominio con varias sin elegir").

**Alternativas descartadas**:

- *Ante todo 401 con sesión de Clerk activa, ir a `/ingresar?cerrar=1`*: corta el ciclo, pero cierra
  la sesión de quien sólo tiene que elegir administración (varias sin elegir, cookie vieja).
- *Dejarlo como hoy y confiar sólo en D3*: sin anidamiento el 431 desaparece, pero el ping-pong sigue
  hasta que el navegador corta con "demasiadas redirecciones".

**Costo de revertir**: bajo. Es una opción con valor por defecto; sacarla vuelve el selector al
comportamiento de hoy.

### D3 · `regresoSeguro` rechaza las pantallas de acceso y los valores largos (E3)

**Qué**: después de la normalización con `new URL` que ya hace, `regresoSeguro` compara el `pathname`
resultante (sin barra final) contra la lista cerrada `/ingresar`, `/registrarse`,
`/elegir-administracion`, `/sin-acceso` y contra cualquier ruta debajo de ellas (`/ingresar/…` es el
`[[...paso]]` de Clerk); si coincide, o si el valor de entrada tiene más de 512 caracteres, devuelve
`/edificios`. Como la comparación es sobre la URL ya normalizada, `/./ingresar` y `/edificios/../ingresar`
caen igual. La función queda idempotente por construcción: su salida nunca es una pantalla de acceso ni
supera el tope.

**Por qué 512**: la ruta propia más larga hoy es `/edificios/<uuid>/grupos/<uuid>` con un query corto,
muy por debajo; 512 deja margen y está lejos de los ~8 KB donde empieza el 431.

**Alternativas descartadas**:

- *Desenvolver el `regreso` anidado y quedarse con el más interno*: conserva la intención original, pero
  es recursivo, tiene que decidir cuántas capas leer y vuelve a abrir el problema que la lista cerrada
  cierra en una línea. El destino por defecto es aceptable: la persona ya estaba en el ingreso.
- *Sólo el tope de largo*: el ciclo seguiría girando sin crecer.

**Costo de revertir**: bajo, una función pura con sus tests.

### D4 · `/sin-acceso` es una ruta propia y el email sale de Clerk en el navegador (E4)

**Qué**: `web/src/app/sin-acceso/page.tsx` (servidor) comprueba con `auth()` que haya sesión de Clerk;
sin sesión, `redirect("/ingresar")` sin `regreso`. Con sesión, renderiza `Pantalla.tsx` (cliente), que
usa `useUser()` dentro de `<ClerkLoaded>` para leer `primaryEmailAddress`. La pantalla usa los
componentes de siempre (`Armazon publico`, `EncabezadoDePantalla`, `Panel`) y ofrece "Cerrar sesión"
(`/ingresar?cerrar=1`) y "Volver a intentar" (`/elegir-administracion`). No pide nada a la API.
`elegir-administracion/Pantalla.tsx` pierde la rama `administraciones.length === 0`; `page.tsx`, si
alguna vez recibiera una lista vacía (no debería, por D1), redirige a `/sin-acceso` en vez de dibujar un
selector vacío. `/sin-acceso` se suma a las rutas que no exigen persona en `03_actores_y_roles.md`.

**Por qué el email no viene de la API**: el token de Clerk puede no traer el email
(`TokenVerificado.email` es opcional), y hacer que la API lo devuelva en el 403 agregaría un dato
personal a una respuesta que hoy es constante. Leerlo con `currentUser()` en el servidor exigiría la
clave secreta de Clerk y una llamada de red por pedido; `useUser()` usa la sesión que el navegador ya
tiene.

**Alternativas descartadas**: *un estado dentro de `/elegir-administracion`*, porque las pantallas de
dominio también tienen que llegar a este estado y el selector tiene `regreso`, que acá no significa
nada; *mostrar el estado vacío actual*, porque dice "Pedile a tu administración que te invite" a una
cuenta que tal vez entró con el email equivocado: sin el email y sin "Cerrar sesión" la persona no
tiene cómo darse cuenta.

**Costo de revertir**: bajo, una ruta nueva y una rama de `pedirApi`.

### D5 · `--clerk-usuario` vincula al `super_admin` del ejemplo, con la guarda primero (E5)

**Qué**: `_main` lee la opción, corre la guarda de D-112 **antes** (como hoy) y valida el id con
`re.fullmatch(r"user_[A-Za-z0-9]{1,64}", valor, flags=re.ASCII)`, el mismo patrón que
`acceso/dominio/token.py:12` y que el `CHECK ck_persona_clerk_usuario_id` de `0019`, antes de crear el
engine. `cargar()` recibe `clerk_usuario: str | None` y, dentro de la misma transacción con el tenant
de ejemplo, después de crear o comparar el ejemplo, llama a la función de vinculación de `acceso` (D7):
si `clerk_usuario_id` es nulo lo escribe; si es igual no hace nada; si es otro lanza un error propio y
la transacción entera se deshace. La salida dice "vinculado", "ya estaba vinculado" o "ya está vinculado
a otra cuenta", sin repetir ids. El `README` suma en "Cómo levantarlo" la sección "Entrar con el
edificio de ejemplo": crear la cuenta en el Clerk de desarrollo, copiar su id desde el panel de Clerk
(Users → la cuenta → User ID), correr el comando con `PROPTECH_ENTORNO=desarrollo` y entrar; con
`user_XXXXXXXX` como marcador, nunca un id real (L-040).

**Por qué en la misma transacción**: si la vinculación falla, no queda un ejemplo a medias ni una
vinculación sin ejemplo. **Por qué no pisar**: un id mal copiado dejaría afuera, sin aviso, a quien ya
estaba entrando; para cambiar de cuenta se borra la base de desarrollo, que es el estado normal de esa
base.

**Alternativas descartadas**: *un comando aparte `ejemplo vincular`*, porque duplica la guarda, la
conexión y el tenant fijo; *pisar el vínculo si es distinto*, por lo de arriba; *crear una invitación
y aceptarla*, porque exige el worker, el mail de Clerk y el flujo completo de 2b para algo que es sólo
de desarrollo.

**Costo de revertir**: bajo, una opción del comando y su sección del `README`.

### D6 · La vinculación de desarrollo no se audita (E6)

**Qué**: no se agrega un evento a `accion_de_auditoria`; el comando no escribe en `auditoria` por la
vinculación. El control es la guarda de D-112, que impide correrlo fuera de desarrollo, y la salida del
comando.

**Por qué**: el vocabulario de auditoría vive en la base (`0027_editar_edificio.py:23` es el último que
lo amplió): un evento nuevo es una migración más, con número provisorio que choca con el 3d y el 6, y
convoca al DBA a un change que no tiene otra razón para tocar el esquema. En producción el comando no
corre.

**Alternativa**: evento `vincular_identidad_de_desarrollo` con su migración `00NN` (provisoria, la
renumera el que mergea segundo) y su escenario en `auditoria-de-acciones`. **Costo de revertir** la
recomendación: agregar la migración después cuesta lo mismo que ahora.

### D7 · La escritura de `acceso` del ejemplo pasa a `acceso.aplicacion` (E7)

**Qué**: `acceso/aplicacion/alta_inicial.py` ya hace lo mismo que `ejemplo.py:124-151` con otra
fuente de ids. Se extrae una función de `acceso.aplicacion` que, en una sesión ya abierta con el tenant
puesto, crea la administración, la persona `super_admin` y su asignación con ids opcionales dados y
registra `alta_inicial`; la usan `alta_inicial.crear` (sin ids) y `ejemplo.cargar` (con los ids fijos y
el `ON CONFLICT DO NOTHING` que hoy da la idempotencia de la carrera). La vinculación de D5 es otra
función de `acceso.aplicacion` que recibe la sesión, la persona y el id. El `INSERT INTO administracion`
de `cargar()` se mueve con la primera. Salen las tres excepciones de `ejemplo.py` del test de fronteras.

**Por qué recomendado**: D5 obliga a escribir `persona` desde el comando del ejemplo. Hacerlo con SQL
en `complejos` agrandaría la violación de D-021 justo en el código CRITICAL que se está tocando, y la
excepción del test dice desde el 3a "pendiente mover a composición". La función compartida además
aplica L-009: el alta inicial y el ejemplo dejan de poder divergir.

**Riesgo**: la idempotencia del ejemplo depende de que el `INSERT INTO administracion … ON CONFLICT DO
NOTHING RETURNING id` siga siendo lo primero de la transacción. La función extraída devuelve si ganó la
carrera; los 10 tests de `test_ejemplo_casos_de_uso.py` (incluido "dos cargas a la vez") son el
baseline, y los mutantes M5 a M8 de QA-2 se corren antes y después para mostrar que no empeoran.

**Alternativa**: dejarlo como deuda y escribir sólo la vinculación en `acceso.aplicacion`. Es más
chico, pero deja el ejemplo con SQL de `acceso` en dos lugares distintos y la excepción del test viva.
**Costo de revertir**: medio, una extracción con dos llamadores.

### D8 · El recuadro de Clerk se reproduce antes de arreglarse (E9)

**Qué**: con el Clerk de desarrollo real, se abre `/ingresar` a 320 px y a 1280 px y se registra, con
captura: el ancho del contenido de `.panel` dentro de `.pagina-acceso` (`tokens.css:1779-1792`, con
`container-type: inline-size` desde la línea 821), el ancho de `.cl-cardBox` y si hay desbordamiento
(`scrollWidth > clientWidth`). La hipótesis de código (≈248 px disponibles a 320 contra un mínimo de
Clerk de ~350 px) se confirma o se descarta con esos números. Si se confirma, el arreglo esperable es
que a anchos chicos el panel de acceso no agregue relleno lateral alrededor del widget y que
`.clerk-proptech` y `cardBox` acepten `min-width: 0` y `width: 100%`, y se vuelve a medir. Si no se
reproduce, la tarea se cierra con las capturas y las medidas, sin tocar CSS. La prueba automática
posible, sin el widget en e2e, es sobre el contenedor: a 320 px `/ingresar` no tiene desplazamiento
horizontal y el ancho de contenido del panel es al menos el mínimo medido.

**Alternativa descartada**: tocar CSS a ciegas con la hipótesis; es la misma regla que B-2 del 3c
(D6 de `pulido-de-la-configuracion`): reproducir primero ubicó la causa real antes de tocar código. **Costo de revertir**: bajo, CSS.

## Risks / Trade-offs

- [Un cliente que dependa de "todo rechazo es 401"] → El único cliente de la API es el servidor de
  Next (Caddy no publica `/api/*`, spec "La API desde afuera"); `pedirApi` se cambia en el mismo
  change. Las e2e y la API falsa se actualizan desde el contrato real (L-027).
- [El barrido de rutas protegidas o algún test existente afirma 401 para "token válido sin vínculo"]
  → Esos tests son el **rojo** de la tarea 2.1 y 2.2: se cambian a 403 en el test antes que en el
  código, y se listan en el informe.
- [`resolver` hace más consultas en el camino de rechazo] → Una sesión por administración vinculada,
  sólo cuando ya se va a rechazar; el camino feliz no cambia.
- [El 403 de `sin_acceso` y el de `permiso_faltante` comparten código] → Se distinguen por la clave
  del cuerpo; `pedirApi` lee `codigo` antes que `permiso_faltante`, y un 403 sin ninguna de las dos
  sigue siendo `sin_permiso` "desconocido" como hoy. Tiene un mutante propio (tarea 3.1).
- [Choque en `web/e2e/api-falsa.ts` con el 3d] → El 3d sube primero su parte (D-130); la tarea 3.6
  arranca con un rebase sobre `main` y no edita las secciones de PATCH/Georef del 3d.
- [El widget de Clerk no carga en e2e] → El recorte y la cuenta real sin persona se verifican a mano
  contra el Clerk de desarrollo (L-032) y se declaran como verificación manual, con capturas.
- [Dos pestañas a la vez] → Ninguna escritura depende del orden: la pantalla nueva no escribe, y el
  selector sólo escribe la cookie de la administración elegida, como hoy.

## Migration Plan

Con la recomendación de E6 **no hay migración**: el despliegue es el de siempre (imagen nueva de API y
web juntas) y el rollback es volver a la imagen anterior, sin datos que deshacer. API y web tienen que
salir juntas: una web vieja con una API nueva trataría el 403 `sin_acceso` como `sin_permiso`
(pantalla de error, sin bucle); una web nueva con una API vieja sigue recibiendo el 401 de hoy, pero
D2 y D3 ya cortan el ciclo. Ninguna de las dos combinaciones arma el 431.

Si E6 se aprueba con la alternativa: migración del vocabulario de auditoría con número provisorio
`00NN`, bajada probada sobre una copia con datos, y **el que mergea segundo** entre este change, el 3d y
el 6 renumera y verifica que `alembic heads` devuelva una sola cabeza.

## Open Questions

Ninguna que cambie specs o tareas: las decisiones abiertas son las elecciones E1 a E9 de `proposal.md`, y se
cierran con la firma.
