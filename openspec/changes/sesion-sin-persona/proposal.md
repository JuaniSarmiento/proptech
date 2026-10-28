## Why

Una cuenta de Clerk **válida** (firma, emisor y partes autorizadas correctos) que no tiene ninguna
persona vinculada entra hoy en un bucle `/ingresar` ↔ `/elegir-administracion?regreso=...` que anida
`regreso` en cada vuelta hasta que el servidor corta con **431**. Se reprodujo en vivo el 27/10/2026
y sólo se destrabó vinculando la persona a mano con un `UPDATE persona SET clerk_usuario_id` (L-039).
La causa raíz, a la que llegaron cuatro lecturas independientes del código
(`.git/informes-regresion/02-acceso.md`), es que el sistema no tiene un tercer estado de sesión para
"autenticado en Clerk, sin acceso a ninguna administración": la API responde el **mismo 401** que a un
token inválido (`proptech_api/acceso.py:64-65`, `proptech_api/sesion.py:30-33`), y la web trata todo
401 como "volvé a ingresar" (`web/src/lib/api/cliente.ts:170-171` → `irAlIngreso` en
`web/src/lib/sesion.ts:43-46` → `<SignIn forceRedirectUrl>` de `web/src/app/ingresar/Pantalla.tsx:73,117`,
que con la sesión de Clerk activa redirige solo de vuelta al selector).

Es la única deuda **CRITICAL** viva (D-130) y bloquea sin avisar cualquier recorrido manual que entre
con una cuenta sin vincular, incluido el del edificio de ejemplo, que hoy no vincula ninguna cuenta
(`complejos/aplicacion/ejemplo.py:124-130`, sin `clerk_usuario_id`). Por eso se adelanta en el orden
del roadmap, antes del 5.

Ficha: `knowledge-base/12_fichas_de_changes.md` §2d (C-21 en `CHANGES.md`). Cubre **HU-V1** (entrar al
portal) y **HU-SA1** (el super admin y sus usuarios) en su borde de ingreso. **Decisiones**: **D-021**
(monolito modular: cada módulo escribe sólo sus tablas), **D-094** y **D-111** (quién firma),
**D-096** (una cuenta por administración), **D-112** (guarda de entorno del comando del ejemplo),
**D-127** y **D-128** (lo que el 3c dejó para un change de acceso), **D-130** (este change). Decisiones
nuevas a escribir con la firma, con **número provisorio** porque el 3d (Gianfranco) y el 6 (Emiliano)
corren en paralelo y el número real se asigna al mergear: **D-nueva-1** (contrato del 403
`sin_acceso`), **D-nueva-2** (el `regreso` nunca apunta a una pantalla de acceso y el selector no
rebota al ingreso), **D-nueva-3** (vinculación de una cuenta de desarrollo al ejemplo).

### Corrección al diagnóstico de la regresión

El informe `02-acceso.md` dice que el estado vacío de `elegir-administracion/Pantalla.tsx:64-69`
("Todavía no tenés una administración") es **código muerto** porque el backend devuelve 401 antes.
Leyendo `acceso/aplicacion/sesion.py:17-39`, eso es cierto sólo para la cuenta **sin persona**: una
persona **vinculada** a la que le quitaron todas sus asignaciones recibe hoy `200` con
`administraciones: []` (el `continue` de la línea 26), y ese estado vacío **sí** se dibuja. Lo que no
existe es un test que lo fuerce. Este change unifica los dos casos en la misma respuesta (E1) y los
lleva a la misma pantalla.

## Qué queda fuera

| qué | dónde va | por qué |
|---|---|---|
| **B-3** · la invitación abierta con la sesión de otra cuenta (`web/src/app/invitacion/[sobre]/page.tsx:20`) | Change de acceso propio, nuevo (E8) | La ficha 2d lo lista, pero el alcance acordado con Juani para este propose son los cinco ítems del bucle; B-3 necesita una lectura nueva del email destinatario sin romper la anti-enumeración y duplicaría el tamaño de un change CRITICAL |
| **2.3** · el menú y los botones que no se adaptan al rol | Change de acceso propio, nuevo (E8) | Exige que la sesión exponga las acciones permitidas de la persona: amplía el contrato de `/api/sesion` en otra dirección. No es un agujero: el backend frena cada acción con 403 |
| **2.4** · reinvitar el mismo email no actualiza el nombre (`acceso/aplicacion/usuarios.py:42-43`) | Change de acceso propio, nuevo (E8) | Independiente del bucle |
| **2.5 / P66** · `/personal` jerárquica (D-127) | Change de acceso propio, nuevo (E8) | Cambia la matriz de D-106 |
| El rechazo de un Gmail no invitado que cae en la página de Clerk en inglés | Change de acceso propio, nuevo | Es el flujo de Google (E17 del 2b), no el de una cuenta autenticada sin persona |
| La CSP/nonce sin test, SU-01 y el resto de la deuda media del 2b | Sus dueños actuales (D-130) | No tocan el bucle |
| Contar o limitar redirecciones en el proxy | Ninguno | El bucle se corta por construcción (E2, E3); un contador en cookie sería estado nuevo que hay que invalidar y probar aparte |
| Cualquier cambio a la matriz de permisos, a `configuracion_versionada`, a la plata o a las pantallas del 3c | Ninguno | Nada de eso participa del bucle |
| Matar los mutantes M5 a M8 de la comparación de idempotencia del ejemplo (QA-2 del PR #1) | Su dueño actual | Este change toca `ejemplo.py` pero no la comparación; si E7 se aprueba, las tareas del grupo 6 los corren como baseline y no tienen que empeorar |

## Gobernanza

**CRITICAL** (D-094, D-111): toca autenticación, el contrato de `/api/sesion` y de la guarda de
identidad de todas las rutas de dominio, y el único camino que escribe `persona.clerk_usuario_id`
fuera de aceptar una invitación. **No se escribe código** hasta que la sección "Aprobación" quede
firmada por Juani, Alberto o Emiliano, con nombre, fecha y la respuesta a cada elección. Una regla
nueva que entre después de la firma necesita firma propia (L-029). El apply no se despacha a un
`role-implementer` suelto (L-048): va a Codex o a un fork del orquestador con el OK en la conversación.

**Piso de revisores obligatorio** (autenticación): **backend**, **QA** y **arquitecto**. **DBA**
sólo si se aprueba E6 tal como está la alternativa (evento de auditoría nuevo con migración): con la
recomendación de E6 el change no agrega migraciones, ni columnas, ni hace reposar datos nuevos (escribe
una columna que ya existe, `persona.clerk_usuario_id`, y sólo en desarrollo). **Frontend** se convoca
por capa: hay una pantalla nueva y un cambio de layout en `/ingresar`.

## What Changes

- **La API distingue "token inválido" de "token válido sin acceso"** (E1). Un token que no verifica
  sigue siendo **401** sin cuerpo propio y sin SQL. Un token que verifica pero cuya identidad no tiene
  **ninguna** persona vinculada con al menos una asignación, en **ninguna** administración, recibe
  **403** con el cuerpo fijo `{"detail": {"codigo": "sin_acceso"}}`, en `GET /api/sesion` y en toda
  ruta de dominio. Es el **mismo cuerpo, byte a byte**, para "sin persona" y para "persona sin
  asignaciones", no consulta nada por email y no nombra ninguna administración: la respuesta sólo dice
  algo sobre la cuenta que la pide. Los problemas de elección (administración ajena, varias sin
  elegir, selector que no es UUID) siguen en 401 como hoy. **BREAKING** para el contrato de
  `autenticacion-con-clerk`: los escenarios "Token válido sin vínculo" y "Vinculada sin asignación"
  pasan de 401 a 403.
- **La web muestra "Tu cuenta no tiene acceso todavía" en vez de redirigir** (E4). Ruta propia
  `/sin-acceso`: dice el email con el que entró (lo lee de Clerk en el navegador, nunca de la API),
  tiene "Cerrar sesión" y "Volver a intentar". Cubre también el caso de "0 administraciones", que deja
  de existir como estado del selector.
- **El bucle no puede volver a armarse** (E2, E3). `/elegir-administracion`, el único nodo del ciclo,
  ante un 401 con la sesión de Clerk activa **no** vuelve a `/ingresar`: muestra "No pudimos validar
  tu sesión" con "Cerrar sesión". Y `regresoSeguro` nunca devuelve una pantalla de acceso
  (`/ingresar`, `/registrarse`, `/elegir-administracion`, `/sin-acceso`) ni un valor de más de
  512 caracteres: cae al destino por defecto. Con las dos cosas, `regreso` no se anida aunque una
  sola de las dos fallara.
- **El edificio de ejemplo puede vincular una cuenta** (E5): `ejemplo cargar --clerk-usuario user_…`,
  sólo con `PROPTECH_ENTORNO=desarrollo` (D-112), valida el formato antes de conectarse, vincula al
  `super_admin` de ejemplo, es idempotente con el mismo id y se niega sin escribir nada si ya está
  vinculado a otro. El paso a paso queda escrito en el `README` y lo repite otra persona sin ayuda
  (cierra L-039 y la deuda del PR #1 a cargo de Emiliano).
- **El recuadro de Clerk en `/ingresar` deja de verse recortado** a 320 px y en escritorio (E9),
  **reproducido primero** en un navegador real con capturas y la medida del ancho disponible; si no se
  reproduce, se cierra con esa evidencia en vez de tocar CSS a ciegas.
- **`ejemplo.py` deja de escribir SQL en tablas de `acceso`** (E7, **elección**: se puede dejar como
  deuda). La creación de la administración de ejemplo, de su persona y de su asignación, y la
  vinculación nueva, pasan por funciones de `acceso.aplicacion`, y las tres excepciones de
  `complejos/aplicacion/ejemplo.py` salen del test de fronteras.

## Capabilities

### New Capabilities

Ninguna: la pantalla nueva y el contrato del 403 son parte del ingreso, que ya vive en
`autenticacion-con-clerk`.

### Modified Capabilities

- `autenticacion-con-clerk`: el 403 `sin_acceso` reemplaza al 401 para el token válido sin acceso
  (**BREAKING**); el selector deja de tener un estado vacío; los ingresos auditados responden 403 en
  los dos casos sin acceso; requisitos nuevos para la pantalla `/sin-acceso`, para el selector que no
  rebota al ingreso y para el `regreso` que nunca apunta a una pantalla de acceso.
- `acceso-de-desarrollo`: requisito nuevo, la cuenta de Clerk de desarrollo se vincula al ejemplo con
  el comando, de forma repetible; el recorrido con el login real pasa a nombrar ese paso.
- `fronteras-de-modulos`: el escenario "El código de hoy pasa con sus excepciones" pierde las tres
  excepciones de `complejos/aplicacion/ejemplo.py`. **Sólo si se aprueba E7**: si se rechaza, este
  delta se borra antes de construir.

## Impact

- **Backend**: `proptech_api/acceso.py` (`identidad_actual`), `proptech_api/sesion.py`,
  `acceso/aplicacion/identidad.py` y `acceso/aplicacion/sesion.py` (una excepción nueva, separada de
  `IdentidadNoDisponible`), `complejos/aplicacion/ejemplo.py` (opción `--clerk-usuario`) y, con E7,
  una función nueva en `acceso/aplicacion/` compartida con `alta_inicial.py` (L-009). **Sin
  migraciones** con la recomendación de E6; si E6 se aprueba con la alternativa, una migración del
  vocabulario de auditoría con número provisorio `00NN` (hoy la cabeza es `0027`): **el que mergea
  segundo, entre este change, el 3d y el 6, renumera** y verifica `alembic heads`.
- **Web**: `lib/api/cliente.ts` (estado nuevo `sin_acceso` y una opción para que el selector reciba
  el 401 en vez de redirigir), `lib/sesion.ts` (`regresoSeguro`), `app/elegir-administracion/`
  (`page.tsx`, `Pantalla.tsx` sin el estado vacío, y su primer archivo de test), `app/sin-acceso/`
  (nueva), `app/tokens.css` (`.pagina-acceso`, `.clerk-proptech`), `lib/test/cinco-respuestas.test.ts`
  (documenta el estado nuevo).
- **E2E**: `web/e2e/api-falsa.ts` suma dos identidades (`user_sin_persona`, `user_api_rechaza`).
  **Choque esperable con el 3d**, que toca el mismo archivo y sube primero su parte (D-130): este
  change rebasa sobre esa parte antes de la tarea 3.6.
- **Documentación**: `README.md` (§"Cómo levantarlo", entrar con el edificio de ejemplo).
- **Sin cambios**: la verificación del token (`acceso/dominio/token.py`), la matriz de permisos, el
  esquema, la CSP, Caddy, el worker.

## Lecciones que aplican (15_lecciones.md)

| lección | cómo la cubre | tarea |
|---|---|---|
| L-034, L-049 | El rojo de cada test cae en la aserción que dice probar (el código de estado o el cuerpo), nunca en un 401 de la guarda ni en un helper; con la excepción nueva existiendo antes del primer rojo | 2.1, 2.2, 2.3, 3.1 a 3.5, 5.1 |
| L-035, L-013, L-019 | Cada garantía nueva (cuerpo idéntico en los dos casos sin acceso, `regreso` sin pantallas de acceso, selector sin rebote, vínculo que no pisa) tiene un caso verde real y un mutante dirigido, corrido sobre una copia sin commit y declarado | 2.1 a 2.3, 3.1 a 3.6, 5.1 |
| L-017 | La entrada de cada chequeo es la del escenario: el 403 se prueba por HTTP contra la API con un token firmado de verdad, no llamando al caso de uso | 2.1, 2.2 |
| L-007, L-008 | El formato de `--clerk-usuario` se valida con coincidencia completa y sólo ASCII, y ningún mensaje repite el valor rechazado | 5.1 |
| L-009 | La creación de administración, persona y asignación se extrae una vez y la usan sus dos gemelos (`alta_inicial.py` y `ejemplo.py`) | 6.2 |
| L-027 | La API falsa de e2e no inventa respuestas: el 403 `sin_acceso` y el 401 que sale de la API real se copian del contrato de la tarea 2 | 3.6 |
| L-032, L-050 | El doble falso de Clerk de e2e no carga el widget: el recorte del recuadro y la cuenta real sin persona se verifican contra el Clerk de desarrollo real y se declaran como tal; un rojo local del navegador se juzga contra el job `web` del CI | 4.1, 7.2 |
| L-026, L-028 | Ningún verde cuenta como "la pantalla se ve bien": `/sin-acceso`, el selector con error y `/ingresar` se recorren a mano a 320 px, en escritorio y con teclado | 4.1, 7.2 |
| L-039 | La verificación manual escribe, paso por paso, cómo quedó vinculada la cuenta usada, y la repite otra persona siguiendo sólo el `README` | 5.3, 7.2 |
| L-040 | Ninguna dirección ni id de Clerk real entra al repo: el `README` usa `user_XXXXXXXX` y la evidencia nombra dónde está el id, no su valor | 5.3, 7.2 |
| L-010, L-031, L-037, L-042 | La corrida de cierre va después de la última vuelta, con el SHA anotado, y se espera el CI del PR | 7.1 |
| L-029, L-048 | Una regla nueva después de la firma necesita firma propia; el apply no va a un `role-implementer` suelto | toda vuelta |

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 28/10/2026): `01` a `16` y `README.md`.

| documento | operación | qué |
|---|---|---|
| `09_decisiones_y_supuestos.md` | **APPEND** (al firmar) | **D-nueva-1** a **D-nueva-3** con su número real al mergear: el 403 `sin_acceso` y su cuerpo fijo; el `regreso` sin pantallas de acceso y el selector que no rebota; la vinculación de desarrollo y su guarda. Y las respuestas a E6 a E8 |
| `09_decisiones_y_supuestos.md` | **APPEND** (al archivar) | Lo que la construcción agregue o corrija |
| `03_actores_y_roles.md` | **REWRITE** (§"Rutas públicas") | Suma `/sin-acceso` a las rutas de la web que no exigen persona; dice qué devuelve la API con token válido sin acceso |
| `07_flujos_principales.md` | **REWRITE** (flujo de ingreso, paso 4 y casos de error) | "Persona vinculada sin asignación recibe 401" pasa a 403 `sin_acceso` y a la pantalla nueva; suma el caso "cuenta sin persona" y "la API rechaza un token que Clerk da por bueno" |
| `08_arquitectura_propuesta.md` | **REWRITE** (§seguridad, contrato de errores de la API) | 401 = sin sesión válida; 403 con `permiso_faltante` = sesión sin ese permiso; 403 con `codigo: sin_acceso` = sesión válida sin ninguna administración |
| `06_funcionalidades.md` | **REWRITE** (HU-V1) | Criterio de aceptación nuevo: una cuenta sin acceso ve una pantalla propia, nunca un error del navegador |
| `11_glosario.md` | **REWRITE** | "cuenta sin acceso" |
| `10_preguntas_abiertas.md` | **REWRITE** | B-3, 2.3, 2.4 y 2.5/P66 apuntan al change de acceso nuevo que decida E8, ya no a "2d" |
| `12_fichas_de_changes.md` | **REWRITE** | Ficha 2d con el alcance firmado; ficha nueva para lo que E8 deje afuera; la deuda del PR #1 (vínculo del ejemplo, L-039) se marca saldada cuando la tarea 5.3 la salde; la ficha 3c deja de nombrar el bucle como abierto |
| `15_lecciones.md` | **APPEND** | Lo que enseñe la construcción; candidata: "un diagnóstico con cuatro lecturas convergentes también puede estar mal en un detalle" (el estado vacío no era código muerto) |
| `CHANGES.md` | **REWRITE** | Estado de C-21 |
| `04_modelo_de_datos.md` | none (con la recomendación de E6) | No hay migración ni columna nueva. Si E6 se aprueba con la alternativa: **REWRITE** del vocabulario de `accion_de_auditoria` |
| `01`, `02`, `05`, `13`, `14`, `16`, `README.md` | none | El change no toca la visión, el stack, las reglas de negocio, el motor de reglas, la forma de trabajo ni las fases posteriores |

## Aprobación

Gobernanza **CRITICAL** (D-094, D-111). La completa, **a mano**, Juani, Alberto o Emiliano, con nombre,
fecha y alcance. **Ningún agente la escribe.** Cada elección tiene su alternativa descartada y el costo
de revertir en `design.md`.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Contrato del token válido sin acceso | **403** con cuerpo fijo `{"detail": {"codigo": "sin_acceso"}}`, idéntico byte a byte para "sin persona" y "persona sin ninguna asignación en ninguna administración", en `/api/sesion` y en toda ruta de dominio; sin consulta por email ni nombres de administración. Los problemas de elección siguen en 401 (D1) | |
| E2 · El selector no rebota al ingreso | `/elegir-administracion` ante un 401 con sesión de Clerk activa muestra "No pudimos validar tu sesión" con "Cerrar sesión", sin redirigir; las pantallas de dominio siguen yendo a `/ingresar` ante un 401 (D2) | |
| E3 · `regreso` normalizado | `regresoSeguro` nunca devuelve `/ingresar`, `/registrarse`, `/elegir-administracion` ni `/sin-acceso` (con o sin query) ni un valor de más de 512 caracteres: cae a `/edificios`. Normalización **y** tope, no uno solo (D3) | |
| E4 · Pantalla sin acceso | Ruta propia `/sin-acceso`, sin `regreso`, con el email de Clerk leído en el navegador, "Cerrar sesión" y "Volver a intentar"; reemplaza al estado vacío del selector (D4) | |
| E5 · Vincular una cuenta al ejemplo | `ejemplo cargar --clerk-usuario user_…`, sólo con `PROPTECH_ENTORNO=desarrollo`; formato validado antes de conectarse; mismo id = no hace nada; otro id ya vinculado = se niega sin escribir; documentado en el `README` y repetido por otra persona (D5) | |
| E6 · ¿Auditar la vinculación de desarrollo? | **No**: sin evento nuevo ni migración; la guarda de D-112 es el control y el comando lo dice por salida estándar. Alternativa: evento `vincular_identidad_de_desarrollo` con migración provisoria `00NN` y DBA convocado (D6) | |
| E7 · `ejemplo.py` sin SQL en tablas de `acceso` (D-021) | **Incluirlo**: la vinculación nueva tiene que escribir `persona` igual, y hacerlo desde `complejos` agrandaría la violación justo en el código CRITICAL que se toca; se extrae una función de `acceso.aplicacion` compartida con `alta_inicial.py` y salen las tres excepciones del test de fronteras. Alternativa: dejarlo como deuda y escribir sólo la vinculación en `acceso` (D7) | |
| E8 · Lo que la ficha 2d lista y no entra | B-3, 2.3, 2.4 y 2.5/P66 van a un change de acceso nuevo con su propia ficha; el 2d se queda en los cinco ítems del bucle | |
| E9 · Recuadro de Clerk | Reproducir primero en navegador real a 320 px y 1280 px, con capturas y la medida del ancho disponible; arreglar sólo lo que se reproduzca; si no se reproduce, se cierra con esa evidencia (D8) | |

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
