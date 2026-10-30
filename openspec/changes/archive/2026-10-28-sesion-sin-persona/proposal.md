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
portal) y **HU-SA1** (el super admin y sus usuarios) en su borde de ingreso, y por los cuatro ítems de
acceso que D-130 le asignó, el menú por rol, reinvitar, la invitación con otra cuenta y `/personal`
jerárquica. **Decisiones**: **D-021**
(monolito modular: cada módulo escribe sólo sus tablas), **D-094** y **D-111** (quién firma),
**D-096** (una cuenta por administración), **D-112** (guarda de entorno del comando del ejemplo),
**D-106** (la matriz, que suma `ver_personal`), **D-127** (`/personal` jerárquica aprobada en
principio: es la decisión vigente, D-120 hoy es otra) y **D-128** (lo que el 3c dejó para un change de
acceso), **D-130** (este change y sus cuatro ítems de acceso). Decisiones
nuevas escritas al archivar, con su número real (`09_decisiones_y_supuestos.md`): **D-131** (contrato
del 403 `sin_acceso`, su precedencia sobre la elección y `codigo` como discriminador de todo 403),
**D-132** (el `regreso` nunca apunta a una pantalla de acceso y el selector no rebota al ingreso),
**D-133** (vinculación de una cuenta de desarrollo al ejemplo, con las trabas de entorno y de
instancia de Clerk), **D-134** (las acciones permitidas viajan con la sesión y la web oculta lo
que no se puede, 2.3), **D-135** (`ver_personal`: `/personal` jerárquica en sólo lectura, amplía
D-106 según D-127), **D-136** (reinvitar el mismo email deja el nombre nuevo, 2.4), **D-137**
(la invitación dice con qué cuenta se está, B-3; enmendada el mismo día).

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
| **Gestionar** el personal desde el administrador principal (invitar, revocar y quitar a quienes están por debajo) | Una decisión aparte, sin change asignado | D-127 aprobó "ver" y dejó "gestionar" para que lo decida el change que lo construya; con la recomendación de E11 este change construye sólo "ver" (D13) |
| El rechazo de un Gmail no invitado que cae en la página de Clerk en inglés | Change de acceso propio, nuevo | Es el flujo de Google (E17 del 2b), no el de una cuenta autenticada sin persona |
| La CSP/nonce sin test, SU-01 y el resto de la deuda media del 2b | Sus dueños actuales (D-130) | No tocan el bucle |
| Contar o limitar redirecciones en el proxy | Ninguno | El bucle se corta por construcción (E2, E3); un contador en cookie sería estado nuevo que hay que invalidar y probar aparte |
| Cualquier cambio a la matriz de permisos, a `configuracion_versionada`, a la plata o a las pantallas del 3c | Ninguno | Nada de eso participa del bucle |
| Matar los mutantes M5 a M8 de la comparación de idempotencia del ejemplo (QA-2 del PR #1) | Su dueño actual | Este change toca `ejemplo.py` pero no la comparación; si E7 se aprueba, las tareas del grupo 6 los corren como baseline y no tienen que empeorar |
| La revisión independiente de la matriz de permisos (D-130, 153 celdas, ahora 162) | **Este change, en verify** | D-130 se la dio al rompedor del primer change que toque esa zona, y éste suma `ver_personal` a la matriz |

## Gobernanza

**CRITICAL** (D-094, D-111): toca autenticación, el contrato de `/api/sesion` y de la guarda de
identidad de todas las rutas de dominio, la matriz de permisos (D-106), quién ve `/personal`, la
pantalla de la invitación, y el único camino que escribe `persona.clerk_usuario_id` fuera de aceptar
una invitación. **No se escribe código** hasta que la sección "Aprobación" quede
firmada por Juani, Alberto o Emiliano, con nombre, fecha y la respuesta a cada elección. Una regla
nueva que entre después de la firma necesita firma propia (L-029). El apply no se despacha a un
`role-implementer` suelto (L-048): va a Codex o a un fork del orquestador con el OK en la conversación.

**Piso de revisores obligatorio** (autenticación y datos de usuario): **backend**, **QA**,
**arquitecto** y **DBA**. El DBA entra por el piso (datos de usuario: el vínculo con Clerk y el nombre
de la persona reposan en `persona`) y, con la recomendación de E11, por la migración `00NN` del
vocabulario de auditoría (`ver_personal`). **Frontend** se convoca por capa: una pantalla nueva, el
layout de `/ingresar`, la invitación, el menú y los controles que se ocultan por rol.

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
- **Todo 403 lleva `codigo`** (E1, AR-6): `sin_acceso` o `sin_permiso`, de una lista cerrada; la web
  lee sólo `codigo`.
- **La sesión dice qué puede hacer la persona y la web oculta lo demás** (2.3, D11): `/api/sesion`
  suma, por administración, las acciones permitidas calculadas con la misma matriz que los 403, en
  tres conjuntos cuyo contrato con `puede` es por tipo de acción (de administración o de edificio) y lo
  prueba un test que recorre toda la matriz; la web
  esconde "Personal", "Nuevo edificio", "Agregar unidad" y los controles de escritura que la persona
  no puede usar. La API sigue frenando cada acción.
- **Reinvitar el mismo email deja el nombre nuevo** (2.4, D12), sin cambiar el nombre si la invitación
  se rechaza, y nunca el de un super admin ni el de una persona de otra administración.
- **El administrador principal ve `/personal` en sólo lectura** (2.5/P66, E11, D13): una acción nueva
  `ver_personal` (super admin y administrador principal) con su migración del vocabulario de auditoría
  `00NN`; la API le devuelve sólo al personal por debajo suyo y nunca al super admin.
- **La invitación abierta con otra cuenta lo dice** (B-3, E10, D10): con sesión, la pantalla dice con
  qué cuenta se está y ofrece "Usar otra cuenta"; la API de aceptación no cambia.

## Capabilities

### New Capabilities

Ninguna: la pantalla nueva y el contrato del 403 son parte del ingreso, que ya vive en
`autenticacion-con-clerk`.

### Modified Capabilities

- `autenticacion-con-clerk`: el 403 `sin_acceso` reemplaza al 401 para el token válido sin acceso
  (**BREAKING**) y **prevalece** sobre los rechazos de elección; el selector deja de tener un estado
  vacío y su lista trae las acciones; los ingresos auditados dejan `ingreso_fallido` sólo para la
  persona elegida; requisitos nuevos para `/sin-acceso` (y que no pida la sesión), para el selector
  que no rebota ni con 401 ni con sesión nula, y para el `regreso` (pantallas de acceso y tope de 512
  sobre la salida).
- `autorizacion-por-rol`: "Token válido sin vínculo" pasa de 401 a 403 (**BREAKING**); la matriz suma
  `ver_personal`; el 403 de permiso lleva `codigo`; requisitos nuevos para `codigo` en todo 403, para
  las acciones en la sesión y su coincidencia con `puede`, y para la web que oculta lo que no se puede.
- `gestion-de-usuarios`: "Quitar la única asignación" pasa de 401 al 403 `sin_acceso`
  (**BREAKING**); reinvitar deja el nombre nuevo; el administrador principal lista el personal por
  debajo en sólo lectura; requisitos nuevos para la invitación abierta con otra cuenta.
- `aislamiento-por-administracion`: el selector ajeno de una identidad sin acceso responde el 403
  `sin_acceso` en vez del 401.
- `acceso-de-desarrollo`: requisitos nuevos, la cuenta de Clerk de desarrollo se vincula al ejemplo con
  el comando, sólo con una instancia de desarrollo de Clerk, con una función que sólo conoce al ejemplo,
  sin pisar ni romper con la unicidad, y aguantando dos corridas a la vez; el recorrido con el login
  real pasa a nombrar ese paso.
- `fronteras-de-modulos`: requisito nuevo, la vinculación de desarrollo sólo se importa desde
  `ejemplo.py` (va **siempre**); y el escenario "El código de hoy pasa con sus excepciones" pierde las
  tres excepciones de `complejos/aplicacion/ejemplo.py` (**sólo si se aprueba E7**: si se rechaza, ese
  requisito MODIFIED se borra del delta antes de construir).

## Impact

- **Backend**: `proptech_api/acceso.py` (`identidad_actual`), `proptech_api/sesion.py`,
  `proptech_api/errores.py` (`Error403` con `codigo`), `proptech_api/complejos.py` y
  `proptech_api/personal.py` (los 403 suman `codigo`; `GET /api/personal` exige `ver_personal`),
  `acceso/aplicacion/identidad.py` y `acceso/aplicacion/sesion.py` (`SinAcceso`, precedencia, acciones
  en la sesión), `acceso/dominio/permisos.py` (`ver_personal`, `acciones_permitidas`),
  `acceso/aplicacion/usuarios.py` (nombre al reinvitar, filtro jerárquico de `listar_personal`),
  `complejos/aplicacion/ejemplo.py` (opción `--clerk-usuario`, trabas), un módulo nuevo de
  `acceso/aplicacion/` para la vinculación de desarrollo y los ids fijos del ejemplo, y, con E7, una
  función nueva compartida con `alta_inicial.py` (L-009). **Una migración** con la recomendación de
  E11: `00NN` suma `ver_personal` al vocabulario de auditoría (hoy la cabeza es `0027`); si E6 se
  aprueba con la alternativa, el evento de vinculación entra en la misma. **El que mergea segundo,
  entre este change, el 3d y el 6, renumera** y verifica `alembic heads`.
- **Web**: `lib/api/cliente.ts` (lee `codigo`; `sin_acceso`; `alNoAutenticar: "devolver"` también
  para la sesión nula), `lib/sesion.ts` (`regresoSeguro`), `app/layout.tsx` (lista de rutas
  protegidas, acciones en `SesionDePantalla`), `componentes/SesionDePantalla.tsx` (acciones y
  `permite`), `app/elegir-administracion/` (`page.tsx`, `Pantalla.tsx` sin el estado vacío, y su primer
  archivo de test), `app/ingresar/` (test del ciclo), `app/sin-acceso/` (nueva), `app/invitacion/`
  (B-3), `app/personal/` (sólo lectura, `secciones.ts`), `app/edificios/` (controles por acción),
  `app/tokens.css` (`.pagina-acceso`, `.clerk-proptech`), `lib/test/cinco-respuestas.test.ts`.
- **E2E**: `web/e2e/api-falsa.ts` suma dos identidades (`user_sin_persona`, `user_api_rechaza`) **en
  un bloque propio**, sin tocar las secciones de PATCH/Georef del 3d: resuelve el conflicto el que
  mergee segundo, la misma regla de la migración (AR-7). No se espera al 3d.
- **Documentación**: `README.md` (§"Cómo levantarlo", entrar con el edificio de ejemplo).
- **Sin cambios**: la verificación del token (`acceso/dominio/token.py`), la API de aceptación de
  invitaciones (`invitaciones.py`, sigue con el 404 uniforme), las columnas y tablas del esquema (la
  única migración suma una fila de vocabulario), la CSP, Caddy, el worker.

## Lecciones que aplican (15_lecciones.md)

| lección | cómo la cubre | tarea |
|---|---|---|
| L-034, L-049 | El rojo de cada test cae en la aserción que dice probar (el código de estado o el cuerpo), nunca en un 401 de la guarda ni en un helper; con la excepción nueva existiendo antes del primer rojo. Cada tarea separa los **rojos** (fallan hoy) de las **guardas** (pasan hoy y tienen que seguir pasando), y una guarda nunca se pega como rojo (QA-7) | todas las de código |
| L-035, L-013, L-019 | Cada garantía nueva (cuerpo idéntico en los dos casos sin acceso, precedencia del 403, `codigo` en todo 403, `regreso` sin pantallas de acceso, selector sin rebote, vínculo que no pisa, acciones que coinciden con `puede`, filtro jerárquico, nombre que no cambia si se rechaza) tiene un caso verde real y un mutante dirigido, corrido sobre una copia sin commit y declarado | 2.1 a 2.4, 3.1 a 3.7, 5.1 a 5.3, 7.1 a 7.8 |
| L-017 | La entrada de cada chequeo es la del escenario: el 403, la sesión ampliada y `/api/personal` se prueban por HTTP contra la API con un token firmado de verdad, no llamando al caso de uso | 2.1, 2.2, 7.3, 7.5 |
| L-007, L-008 | El formato de `--clerk-usuario` se valida con coincidencia completa y sólo ASCII, sin `type=` de `argparse`, y ningún mensaje repite el valor rechazado ni el emisor | 5.1 |
| L-009 | La creación de administración, persona y asignación se extrae una vez y la usan sus dos gemelos (`alta_inicial.py` y `ejemplo.py`) | 6.2 |
| L-027 | La API falsa de e2e no inventa respuestas: el 403 `sin_acceso` y el 401 que sale de la API real se copian del contrato de la tarea 2 | 3.7 |
| L-032, L-050 | El doble falso de Clerk de e2e no carga el widget: el anidamiento se prueba con un test de componente del ciclo, y el recorte, la cuenta real sin persona y "dos pestañas" se verifican contra el Clerk de desarrollo real y se declaran como tal; un rojo local del navegador se juzga contra el job `web` del CI | 3.3, 4.1, 8.2 |
| L-026, L-028 | Ningún verde cuenta como "la pantalla se ve bien": `/sin-acceso`, el selector con error, `/ingresar`, la invitación con otra cuenta y `/personal` en sólo lectura se recorren a mano a 320 px, en escritorio y con teclado | 4.1, 8.2 |
| L-039 | La verificación manual escribe, paso por paso, cómo quedó vinculada la cuenta usada, y la repite otra persona siguiendo sólo el `README` | 5.4, 8.2 |
| L-040 | Ninguna dirección ni id de Clerk real entra al repo: el `README` usa `user_XXXXXXXX`, la evidencia nombra dónde está el id y el emisor, no su valor | 5.1, 5.4, 8.2 |
| L-009 | El cálculo de las acciones de la sesión usa la misma `_MATRIZ` que `puede`, nunca una copia, y un test de propiedad compara las dos en todas las celdas | 7.4 |
| L-010, L-031, L-037, L-042 | La corrida de cierre va después de la última vuelta, con el SHA anotado, y se espera el CI del PR | 8.1 |
| L-029, L-048 | Una regla nueva después de la firma necesita firma propia; el apply no va a un `role-implementer` suelto | toda vuelta |

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 28/10/2026): `01` a `16` y `README.md`.

| documento | operación | qué |
|---|---|---|
| `09_decisiones_y_supuestos.md` | **APPEND** (al firmar) | **D-131** a **D-137** (403 `sin_acceso`, precedencia y `codigo`; `regreso` y selector; vinculación de desarrollo y sus trabas; acciones en la sesión; `ver_personal`; nombre al reinvitar; invitación con otra cuenta), y las respuestas a E1 a E11 |
| `09_decisiones_y_supuestos.md` | **APPEND** (al archivar) | Lo que la construcción agregue o corrija; una línea en D-127 que diga qué se construyó ("ver") y qué sigue pendiente ("gestionar"), sin reescribir la decisión fechada |
| `03_actores_y_roles.md` | **REWRITE** (§"RBAC · Matriz de permisos" y §"Rutas públicas") | La matriz suma `ver_personal` (super admin y administrador principal); el administrador principal ve `/personal` en sólo lectura, nunca al super admin; `/sin-acceso` entra en las rutas de la web que no exigen persona, con lo que devuelve la API a un token válido sin acceso |
| `04_modelo_de_datos.md` | **REWRITE** (vocabulario de `accion_de_auditoria`) | Suma `ver_personal` (migración `00NN`), y el evento de vinculación si E6 se aprueba con la alternativa |
| `06_funcionalidades.md` | **REWRITE** (HU-V1 y la de gestión de usuarios) | Una cuenta sin acceso ve una pantalla propia, nunca un error del navegador; el menú y los botones se adaptan al rol; el administrador principal ve su personal |
| `07_flujos_principales.md` | **REWRITE** (flujo de ingreso, invitación y alta de personal) | "Persona vinculada sin asignación recibe 401" pasa a 403 `sin_acceso` y a la pantalla nueva, con la precedencia; la invitación abierta con otra cuenta lo dice; reinvitar deja el nombre nuevo |
| `08_arquitectura_propuesta.md` | **REWRITE** (§seguridad, contrato de errores de la API) | 401 = sin sesión válida o rechazo de elección con acceso en otra; 403 con `codigo` como único discriminador: `sin_acceso` (constante) o `sin_permiso` (con `permiso_faltante`); `/api/sesion` trae las acciones calculadas con la matriz |
| `10_preguntas_abiertas.md` | **REWRITE** | P66 y P68 dejan de apuntar a "2d" como pendiente y dicen qué resolvió el 2d; "gestionar" de D-127 queda como pregunta abierta nueva si E11 se aprueba como se recomienda |
| `11_glosario.md` | **REWRITE** | "cuenta sin acceso", "acciones de la sesión" |
| `12_fichas_de_changes.md` | **REWRITE** | Ficha 2d con el alcance firmado (los cinco ítems del bucle y los cuatro de acceso, D-130); la deuda del PR #1 (vínculo del ejemplo, L-039) se marca saldada cuando la tarea 5.4 la salde; la ficha 3c deja de nombrar el bucle y B-3, 2.3, 2.4 y 2.5 como abiertos; la nota de D-130 sobre la revisión independiente de la matriz se marca absorbida por el verify del 2d |
| `15_lecciones.md` | **APPEND** | Lo que enseñe la construcción; candidatas: "un diagnóstico con cuatro lecturas convergentes también puede estar mal en un detalle" (el estado vacío no era código muerto) y "una acción nueva de la matriz es una migración, porque `Accion` es también el vocabulario de auditoría" |
| `CHANGES.md` | **REWRITE** | Estado de C-21 |
| `01`, `02`, `05`, `13`, `14`, `16`, `README.md` | none | El change no toca la visión, el stack, las reglas de negocio, el motor de reglas, la forma de trabajo ni las fases posteriores |

## Aprobación

Gobernanza **CRITICAL** (D-094, D-111). La completa, **a mano**, Juani, Alberto o Emiliano, con nombre,
fecha y alcance. **Ningún agente la escribe.** Cada elección tiene su alternativa descartada y el costo
de revertir en `design.md` (D1 a D13).

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Contrato del token válido sin acceso | **403** con cuerpo fijo `{"detail": {"codigo": "sin_acceso"}}`, idéntico en código, cuerpo y cabeceras (salvo `X-Request-ID`) para "sin persona" y "persona sin ninguna asignación en ninguna administración", en `/api/sesion` y en toda ruta de dominio; sin consulta por email. **Prevalece** sobre los rechazos de elección (selector ajeno, no UUID, varias sin elegir), que siguen en 401 sólo para quien tiene acceso en otra; `ingreso_fallido` sólo para la persona elegida. **Todo 403 lleva `codigo`** (`sin_acceso` o `sin_permiso`) y la web lee sólo `codigo` (D1) | Sí |
| E2 · El selector no rebota al ingreso | `/elegir-administracion` ante un 401 **o una sesión de Clerk nula en el servidor** muestra "No pudimos validar tu sesión" con "Cerrar sesión", sin redirigir; las pantallas de dominio y su layout siguen yendo a `/ingresar` ante un 401 (D2) | Sí |
| E3 · `regreso` normalizado | `regresoSeguro` nunca devuelve `/ingresar`, `/registrarse`, `/elegir-administracion` ni `/sin-acceso` (con o sin query, también con `%XX`) ni un valor de entrada **o de salida** de más de 512 caracteres: cae a `/edificios`. Normalización **y** tope, no uno solo (D3) | Sí |
| E4 · Pantalla sin acceso | Ruta propia `/sin-acceso`, sin `regreso`, con el email de Clerk leído en el navegador, "Cerrar sesión" y "Volver a intentar", **sin pedir nada a la API** ni figurar entre las rutas protegidas del layout; reemplaza al estado vacío del selector (D4) | Sí |
| E5 · Vincular una cuenta al ejemplo | `ejemplo cargar --clerk-usuario user_…`, sólo con `PROPTECH_ENTORNO=desarrollo` **y** un `CLERK_EMISOR` de instancia de desarrollo validado como URL completa (`https`, host que termina en `.clerk.accounts.dev`, sin usuario ni contraseña, sin query ni fragmento, sin puerto o 443, ruta vacía o `/`); formato validado antes de conectarse, sin `argparse` que repita el valor; función de vinculación que sólo conoce al ejemplo y sólo se importa desde `ejemplo.py`; chequeo previo de unicidad; `UPDATE` condicional envuelto en un `except IntegrityError` sobre `uq_persona_clerk_administracion` con el mismo mensaje fijo, sin el id (la carrera residual); mismo id = no hace nada; otro id = se niega sin escribir; documentado en el `README` y repetido por otra persona (D5) | Sí |
| E6 · ¿Auditar la vinculación de desarrollo? | **No**: las dos trabas de D5 y la función que sólo conoce al ejemplo son el control, y no hay actor ni tenant real que reconstruir. Alternativa: evento `vincular_identidad_de_desarrollo` en la misma migración `00NN` de E11 (D6) | Sí |
| E7 · `ejemplo.py` sin SQL en tablas de `acceso` (D-021) | **Incluirlo**: se extrae una función de `acceso.aplicacion` compartida con `alta_inicial.py` y salen las tres excepciones del test de fronteras. Alternativas descartadas: dejarlo como deuda; mover `ejemplo.py` a una raíz de composición (AR-5/D-116), que escondía el SQL del escaneo en vez de sacarlo (D7) | Sí |
| E8 · Alcance de acceso pendiente: dentro del 2d | B-3, 2.3, 2.4 y 2.5/P66 se construyen **en este change**, como dice D-130 (decisión de Juani del 28/10/2026), con sus requisitos, specs y el grupo 7 de tareas; el change queda en ~30 tareas, por encima de las ~20 de `config.yaml`, y se construye en dos tandas con PR propio dentro del mismo change (no se parte el change). Alternativa descartada: sacarlos a otro change, con el costo de un segundo ciclo CRITICAL sobre los mismos archivos (D9) | Sí |
| E9 · Recuadro de Clerk | Reproducir primero en navegador real a 320 px y 1280 px, con capturas y la medida del ancho disponible; el rojo automático inyecta un bloque del ancho mínimo medido en el panel, a 320 y a 1280; arreglar sólo lo que se reproduzca; si no se reproduce, se cierra con esa evidencia (D8) | Sí |
| E10 · B-3: cómo se dice que la invitación se abrió con otra cuenta | **(a)** Con sesión, la pantalla dice "Estás ingresado como <email del claim del token>" y ofrece "Usar otra cuenta"; si la aceptación falla, el mensaje dice que el enlace no sirve con esa cuenta. **Si el token no trae el claim de email**, los dos textos van en forma genérica, sin nombrar ningún email, con las mismas acciones; si el claim viaja se comprueba con Clerk real (8.2 e). La API no cambia y nunca se muestra el email destinatario. Alternativas: (b) avisar que hay una sesión sin decir de quién; (c) una lectura nueva del destinatario por el sobre (D10) | Sí |
| E11 · `/personal` jerárquica (D-127): qué se construye | **Sólo ver**: el administrador principal ve, en sólo lectura, a las personas con **al menos una** asignación y cuyas asignaciones son **todas** de administrador por edificio, contador, auxiliar o consejo (una persona sin asignaciones no aparece); nunca al super admin, a otro administrador principal ni a un vecino, con el filtro en la API, en Python con la misma regla que la matriz (si el padrón crece, se acota en SQL con `EXISTS`). Acción nueva `ver_personal` (super admin y administrador principal) con migración `00NN` del vocabulario de auditoría y DBA convocado. "Gestionar" (invitar, revocar, quitar a los de abajo) queda para una decisión aparte. Alternativas: también gestionar; incluir a pares o mostrar sólo las asignaciones de abajo; un permiso fuera de la matriz sin migración (D13) | Sí |
| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| Juani | 28/10/2026 | E1 a E11 tal como están en esta sección |

### Enmienda E10 · "Usar otra cuenta" vuelve a la invitación, no a /ingresar (verificación 8.2 e)

En la verificación con el Clerk de desarrollo real, una invitación para una persona que todavía no tiene
cuenta, abierta con otra sesión, llevó por "Usar otra cuenta" a `/ingresar` con el ticket: Clerk
respondió "This invitation refers to a non-existing identification" y, al intentar con Google, cayó en la
página hospedada de Clerk, que volvió a `/invitacion/…` **sin** `__clerk_ticket`. Corrección: "Usar otra
cuenta" cierra la sesión y vuelve a la **misma pantalla de la invitación** con su `__clerk_ticket`, que ya
ofrece ingresar o crear cuenta. Reemplaza a "cierra la sesión y conserva `__clerk_ticket` hasta el
ingreso" de E10 y de la tarea 8.2 (e); el resto de E10 queda igual (nunca se muestra el email
destinatario). Descartado: dejarlo como deuda (un invitado nuevo se traba en un error en inglés).

| Firmante | Fecha | Alcance aprobado |
|---|---|---|
| Juani | 28/10/2026 | Enmienda E10 tal como está escrita arriba |
