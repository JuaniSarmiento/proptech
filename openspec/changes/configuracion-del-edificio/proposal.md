## Why

Después del 2a la base ya tiene el candado, pero un edificio es apenas un nombre: `complejo` tiene
`id`, `administracion_id` y `nombre`, y `unidad` lo mismo más su `complejo_id`. Sin coeficientes, sin
grupos de reparto, sin categorías y sin la configuración de intereses, vencimiento y fondo de
reserva, el cambio 4 (`motor-de-cuenta-corriente`) no tiene sobre qué calcular y el camino a M1 se
frena. Es la ficha 3 de `knowledge-base/12_fichas_de_changes.md`: que el administrador cree un
edificio y lo configure como dice su reglamento (**HU-A1**).

Cubre: **R01** (la definición de grupos con sus dos modos de coeficientes y el informe de la suma, con
la tolerancia de D-082), **R02** (sólo el campo de estado, desactivado, D-030, D-089), **R03** (su
configuración, no el cálculo, con el día de vencimiento y el doble vencimiento opcional de D-100),
**R15** (el porcentaje), **R16** (categorías), **R09** en lo que toca a este cambio (el estado de
migración del edificio, D-082, D-083). Decisiones: D-010, D-013, D-029, D-030, D-031, D-041, D-042,
D-080, D-082, D-083, D-087, D-089, D-094, D-096, D-098 (la deuda que hereda) y **D-100** (P19, P33 y
P24). Las reglas propuestas R35, R36 y R39 **no entran**: ninguna se validó. **R26** entra sólo como
configuración (D-100: el doble vencimiento con su recargo se guarda acá; lo calcula el 4 o el 7).

Revisado por el arquitecto el 16/10/2026; bloqueantes aplicados con decisiones de Juani (B5, P19, P33).

## Partición: 3a (este cambio) y 3b (las pantallas)

El alcance completo de la ficha (modelo, casos de uso, API, semilla en la base, deuda heredada,
acceso de desarrollo y siete pantallas) pasa largo de las veinte tareas. Se propone partirlo
(elección **E1**):

- **3a `configuracion-del-edificio`** (este cambio, HIGH): el modelo, las reglas, los casos de uso, la
  API, la semilla cargada en la base y la deuda del 2a y del 1b con dueño 3. **24 tareas.**
- **3b `pantallas-del-edificio`** (nombre provisional, cambio aparte, propose propio): los `shape` de
  las siete pantallas con Juani (eran la 8.1 de la primera versión; pasan al 3b como precondición, nota N10 del
  arquitecto), las pantallas, el acceso de desarrollo sin login (**E2**, que se firma acá porque toca
  el candado) y el "terminado" de frontend.

**Por qué así y no al revés**: el 4 necesita el modelo y la configuración versionada, no las
pantallas. Con la partición, el camino crítico a M1 queda `2a → 3a → 4` y el 3b sale de él. Los
`shape` tampoco van en el 3a: atarían el **cierre** del 3a a siete sesiones de diseño y volverían a
meter al 3b en el camino crítico. Si el 2b (el login) llega antes que el 3b, el acceso de desarrollo
de E2 ni siquiera se construye. Las piezas tienen perfil de riesgo distinto (plata y aislamiento de
un lado, accesibilidad y diseño del otro), el mismo criterio con que D-097 partió el 2.

**Tamaño**: aun sin los `shape`, D-100 y los bloqueantes de la revisión suman tres tareas (los modos
de coeficientes de P24, las tablas de sólo agregar de B2 y la tabla de grupos partida en dos) y el 3a
queda en **24**, por encima del "partir pasadas unas veinte" (D-088). Hay dos salidas, y se elige en
**E1**:

- **Recomendada**: mover la 7.2 (el comando que carga el ejemplo en la base, E6) al 3b. Lo único que
  la necesita es el acceso de desarrollo de E2, que vive en el 3b; el 4 no la usa (sus tests arman sus
  propios datos). El 3a queda en 23 y se registra como excepción, igual que el 1c.
- Dejar las 24 en el 3a y registrar la excepción. No se propone partir más: la API sin su modelo no
  se revisa sola (D1).

### Lo que entra en el 3b, para que se firme sabiendo qué viene

**Pantallas** (superficie del administrador, densa; ninguna del vecino ni del consejo):

1. **Mis edificios**: la lista de edificios del alcance, con su estado de migración, y "Crear edificio".
2. **Resumen del edificio**: qué falta configurar (padrón con la suma fuera de tolerancia, estado de
   migración pendiente) y lo próximo que hay que hacer. Una sola acción principal (principio 3 de
   `PRODUCT.md`).
3. **Padrón de unidades**: alta y edición de unidades, con la suma de coeficientes y su estado tal
   como los devuelve la API.
4. **Grupos de reparto**: método, modo de coeficientes, unidades de cada grupo y su suma.
5. **Categorías de gasto**: crear, renombrar, ordenar y desactivar.
6. **Intereses, vencimiento y fondo de reserva**: la versión vigente, el historial y "Nueva versión".
7. **Confirmar "sin saldos previos"**: una acción irreversible, con confirmación explícita.

**Flujos**: crear un edificio con la configuración de su reglamento (o con los valores de los
parámetros); cargar el padrón hasta que la suma quede "ok"; armar un grupo parcial renormalizado y
otro con coeficientes propios; ajustar categorías; cambiar la tasa y ver la versión anterior en el
historial; confirmar "sin saldos previos".

**Reglas de diseño que aplican** (`PRODUCT.md`, `DESIGN.md`): coeficientes, porcentajes y tasas con
**números tabulares**, alineados a la derecha y con formato argentino (The Tabular Money Rule); el
estado de la suma de R01 y el estado de migración **nunca sólo con color**, siempre con texto (The
Never Color Alone Rule); una sola acción principal en terracota por pantalla (The One Voice Rule);
lo conocido antes que lo novedoso. **El frontend no calcula**: la suma de coeficientes, la diferencia
y su estado vienen de la API (regla dura de `CLAUDE.md`).

**Ninguna pantalla se diseña en este propose.** Cada una pasa por un `shape` con Juani antes de
implementarse; ese trabajo es la precondición del propose del 3b, no una tarea del 3a.

**"Terminado" de frontend**, observable, para cada pantalla del 3b:

- se opera entera con teclado, en un orden que sigue la lectura, con foco visible en todo control
  (WCAG 2.4.7 y 2.4.11: el foco no queda tapado);
- cada error de un campo está asociado a ese campo por programa (`aria-describedby` o equivalente,
  con `aria-invalid`), no sólo por estar al lado, y el 422 de la API llega al campo que corresponde;
- los estados de carga, vacío y error existen y se pueden alcanzar a pedido (un test por estado, y en
  desarrollo una forma de forzar cada uno sin tocar el código);
- a 320 px de ancho no hay scroll horizontal (verificado con un navegador real, no a ojo);
- WCAG 2.2 AA: sin violaciones de axe en cada pantalla y en cada estado, contraste AA, objetivos de al
  menos 24 x 24 px (2.5.8), `prefers-reduced-motion` respetado.

## Gobernanza

**Nivel HIGH** (D-087, D-094, ficha 3): guarda la configuración versionada de intereses, vencimiento y
fondo de reserva, que cambia montos, y suma permisos nuevos a la matriz de D-096. Un error acá no se
ve hasta que el cambio 7 emite con una tasa equivocada o con el padrón de otro edificio.

**Se propone y se espera la aprobación escrita y fechada de uno de los dos socios (Juani o Alberto)
antes de construir** (D-094). El constructor no arranca hasta que la sección "Aprobación", al final
de este archivo, tenga el nombre, la fecha, el alcance aprobado y la respuesta a cada elección E1 a
E10. Ningún agente completa esa sección. Un socio puede aprobar el cambio y rechazar una elección:
entonces se corrige el `design.md` antes de construir.

## What Changes

- **Deuda heredada, primero** (L-012, D-098):
  - **R6**: el barrido de rutas protegidas deja de depender de que cada router declare `/api` en su
    propio `prefix`; ve toda ruta de la app, venga por `include_router(prefix=...)`, por
    `add_api_route` o anidada. **Bloquea antes de la primera ruta nueva.**
  - **R11**: el id de un alta lo genera siempre el servidor. Un cuerpo de alta que trae `id`,
    `administracion_id` o `complejo_id` se rechaza con 422 sin escribir nada (**E8**), y un barrido
    lo exige en toda ruta `POST` presente y futura: falla si una ruta nueva no tiene un cuerpo de
    prueba y verifica que el 422 nombra `id` (L-019).
  - La fila del 1b con dueño 3 (auditorías del 13/10): `naming_convention`, tipos `Porcentaje` y
    `Superficie`, versión de la semilla como `Literal[1]`, pydantic como dependencia directa, la app
    con `--factory`, el healthcheck de la web contra `127.0.0.1`, `.gitignore` ampliado y el test de
    `chmod` en Windows. (El tope de lectura del YAML ya está hecho: 1 MiB en `cargador_yaml.py`.)
- **Edificio completo**: `complejo` suma `localidad` y el **estado de migración** (`pendiente`,
  `confirmada`, `sin_saldos_previos`, D-083); `unidad` suma identificador único dentro del edificio,
  tipo (los cuatro de D-029), piso, coeficiente, superficie y el estado desactivado de R02.
- **Grupos de reparto** (R01) con su método, sus unidades y, para los parciales, **dos modos de
  coeficientes** (D-100, P24): renormalizar los generales entre sus unidades (por defecto) o
  coeficientes propios que suman 1 dentro del grupo. Siempre del mismo edificio y la misma
  administración (FK compuesta); "Generales" obligatorio, por coeficiente y con todas las unidades.
- **R01 se informa y bloquea la emisión, no la carga** (**E5**): la API informa siempre la suma, la
  diferencia y el estado con la tolerancia de ±0,0001; el control antes de emitir del cambio 7 lo hace
  cumplir con una fila nueva en R34 ("Coeficientes fuera de tolerancia", bloqueante duro), que este
  propose deja escrita en `05` y en la ficha 7. La función pura de R01 y el tipo `Coeficiente` viven
  en `compartido`, así la usan el dominio del edificio y la semilla sin crear un ciclo (B1).
- **Categorías de gasto** (R16): crear, renombrar, ordenar y desactivar; nunca borrar.
- **Configuración versionada de intereses, vencimiento y fondo de reserva** (R03, R15, D-080, D-100):
  menús cerrados con los rangos de `parametros.yaml`; un **día fijo de vencimiento del 1 al 28**; el
  vencimiento **único o doble**, y si es doble, el segundo vencimiento y su **recargo en porcentaje**;
  una versión nueva por cambio con fecha de vigencia, fecha de alta y autor; las anteriores no se tocan
  (**E4**). La app no tiene `UPDATE` ni `DELETE` sobre la tabla y eso sobrevive a cada `up` (B2).
- **Crear un edificio** copia los valores de `config/parametros.yaml` del momento (D-042) o acepta en el
  mismo alta la configuración inicial del reglamento, así el primer día no da 409 (**E4**). Cambiar el
  archivo después no altera edificios existentes.
- **Permisos** nuevos en la matriz de D-096 (se modifica la existente, no se suma otra): configurar
  (**E3**) y una acción de **lectura** de la configuración para el personal y el consejo; **el vecino
  ve sólo lo suyo** (B5). **Auditoría** de las tres acciones que importan (**E7**), con su migración de
  vocabulario.
- **API** bajo `/api` para todo lo anterior, con contrato de error explícito (401, 422 del cuerpo, 404,
  403, 409 y 422 semántico).
- **El edificio de ejemplo en la base**: la semilla suma el estado de migración
  (`sin_saldos_previos`) y el modo de cada grupo, el validador usa la misma función de R01 que la API,
  y un comando explícito lo carga en una administración de ejemplo, idempotente sobre lo que sale de
  la semilla (**E6**, **E10**). La 7.2 se recomienda mover al 3b (ver Tamaño).

## Capabilities

### New Capabilities

- `edificios-y-unidades`: alta de un edificio con los valores de los parámetros o con su configuración
  inicial, sus unidades con tipo, coeficiente y superficie, y su estado de migración.
- `grupos-de-reparto`: grupos con método, modo de coeficientes y unidades del mismo edificio, y el
  informe de coeficientes de R01.
- `categorias-de-gasto`: las categorías de cada edificio y su ciclo de vida (crear, renombrar,
  ordenar, desactivar).
- `configuracion-versionada`: intereses, vencimiento y fondo de reserva como versiones de sólo
  agregar, con vigencia, autor y fecha.

### Modified Capabilities

- `datos-semilla`: la semilla suma el estado de migración y el modo de los grupos, el validador acepta
  la tolerancia de R01 y un comando carga el edificio de ejemplo en la base (hasta hoy, el comando
  tenía prohibido escribir).
- `autorizacion-por-rol`: el barrido de rutas que no depende del prefijo (R6) y la matriz de D-096
  modificada con los permisos de configuración y de lectura de la configuración.
- `auditoria-de-acciones`: tres acciones nuevas en el vocabulario cerrado.

## Que intente romper el rompedor

Además de lo que ya pide la ficha 3 (coeficientes de un grupo que no suman 1, una unidad repetida,
cambiar la tasa y que se pierda la versión anterior, editar la configuración de otro edificio):

- **Coeficientes que no suman 1** (o 100 %, si la pantalla los muestra en porcentaje): 0,9999 y
  1,0001 dan advertencia (borde incluido); 0,9998 y 1,0002 dan `fuera_de_tolerancia` con la
  diferencia, y el alta igual se guarda; un coeficiente `0`, negativo, con siete decimales, con
  dígitos Unicode o con `\n` al final; un grupo con coeficientes propios que suman 0,8; un miembro con
  coeficiente propio en un grupo renormalizado (por la API y por SQL); cambiar el modo de un grupo con
  miembros por un `UPDATE` directo; la suma calculada en el frontend en vez de leerla de la API.
- **Versiones de configuración superpuestas**: dos versiones con la misma fecha de vigencia, dos
  pedidos simultáneos que crean versión para el mismo día (uno tiene que dar 409), una versión
  retroactiva, un `UPDATE` o `DELETE` de una versión vieja como `proptech_app` y como migrador, el
  mismo `UPDATE` **después de un segundo `up`** y con el trigger deshabilitado sobre una copia, una
  "configuración vigente" consultada para una fecha anterior a la primera versión.
- **Vencimientos**: día 0, 29, 31 o `"10"` como texto; doble vencimiento sin recargo o sin segundo día;
  único con recargo; segundo día igual o anterior al primero; recargo como número JSON.
- **Una unidad de otro edificio o de otra administración**: sumarla a un grupo por su id (formato
  válido, fila que existe, L-017), mover una unidad a otro edificio por `PATCH`, crear un grupo en el
  edificio A con unidades de B, todo por la API **y** por SQL directo como `proptech_app` (la FK
  compuesta tiene que frenarlo aunque la aplicación se equivoque).
- **Lectura**: un vecino que pide el padrón, los grupos, las categorías o la configuración de su
  propio edificio (403) y de otro (404); el vecino que pide su propia unidad (200, como en el 2a).
- **El edificio de ejemplo cargado dos veces**: dos corridas seguidas, dos corridas en paralelo, una
  segunda corrida después de que alguien editó una unidad del ejemplo, una segunda corrida después de
  cambiar `parametros.yaml` (tiene que dar "ya estaba", D-042), el comando sin tenant, el comando con
  un tenant de otra administración.
- **Montos con float**: un coeficiente, una tasa, un porcentaje o una superficie mandados como número
  JSON (`0.1`, `3.5`, `1e-1`) en vez de texto; `NaN`, `Infinity`, `-0`; un `float` que se cuela al
  construir un `Decimal` en el núcleo o al serializar la respuesta.
- **Ids del cliente** (R11): un alta con `id`, `administracion_id` o `complejo_id` en el cuerpo; una
  ruta `POST` nueva agregada con `include_router(prefix=...)` que el barrido no ve (R6); una ruta
  `POST` nueva sin cuerpo de prueba en el barrido.
- **Permisos**: un colaborador "ver" que crea una categoría, un colaborador "editar" que cambia la tasa
  o confirma "sin saldos previos", el consejo o un vecino que escriben algo, un colaborador que crea un
  edificio.
- **El estado de migración**: volver de `sin_saldos_previos` a `pendiente`, confirmarlo dos veces,
  confirmarlo con unidades que ya tienen saldo (cuando exista el 4).
- **Fronteras**: un import de `complejos` agregado a `compartido` (el test de fronteras tiene que
  fallar).

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-021). Detalle en `design.md` ("Cómo aplica
cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-003 · contar los tests | 1.1 y 8.1 |
| L-005 · verde es todo el workflow | convención de `tasks.md` y 8.1 |
| L-006 · lo destructivo apunta a un nombre del proyecto | 7.2 (la carga del ejemplo sólo toca la administración de ejemplo) |
| L-007 · el error de una librería es una salida | 2.2, 6.1 a 6.3 (un 422 no repite el valor rechazado) |
| L-008 · coincidencia completa y sólo ASCII | 2.3 (`Porcentaje`, `Superficie`), 4.1 (`Coeficiente`), 5.2 (identificador de unidad) |
| L-009 · el arreglo se prueba en el gemelo | 2.3, 4.1 y 7.1 (el validador de la semilla y la API usan la misma función de R01, que vive en `compartido`) |
| L-010 · la corrida de cierre va al final | 8.1 |
| L-012 · la deuda al primer cambio que usa la pieza | 2.1 a 2.4 |
| L-013 · mutar sin commit exige copia | convención de `tasks.md`; 2.1, 2.2, 3.5, 3.6, 4.1 |
| L-016 · una observación tiene que poder dar otro resultado | 3.1 a 3.7 y 5.x (como `proptech_app`, nunca como superusuario) |
| L-017 · la entrada del escenario | 5.3 y 6.2 (ids válidos de filas que existen en otro edificio u otra administración) |
| L-018 · verificar el efecto, no la forma | 3.5 (los permisos de sólo agregar se prueban con dos `up` y el trigger deshabilitado sobre una copia, no leyendo `pg_class`), 3.6 (la versión se intenta editar de verdad), 3.2 y 3.3 (las FK compuestas se prueban insertando, no leyendo `pg_constraint`) |
| L-019 · un test que no puede dar rojo | 2.1, 2.2 (el barrido falla si falta un cuerpo de prueba) y 4.1 (la frontera `compartido ↛ complejos` se ve fallar) |
| L-020 · arreglar un bloqueante puede crear otro | 2.1 (cambiar el barrido no puede dejar afuera las rutas de hoy), 3.5 (la excepción del guardián no puede aceptar cualquier tabla) |
| L-021 · la instrucción del auditor acota lo que los demás miran | sección de arriba: es un piso, no un techo |

L-001, L-011, L-014 y L-015 no aplican: este cambio no suma dependencias que puedan congelarse, ni
plazos sobre operaciones con efecto, ni Bash con `|| true`, ni hilos. L-002 y L-004 aplican como en
todo cambio (configuración rota de muchas formas; otro camino para verificar) y no tienen tarea propia.

## Preguntas abiertas

**P19, P24 y P33 están resueltas (D-100, 16/10/2026)** y ya no bloquean ninguna tarea: las 24 están
libres desde la aprobación. D-100 queda "pendiente de contrastar con el reglamento del piloto": si
Alberto confirma una sola variante, sólo se elige en la configuración; el modelo no cambia.

| Pregunta | Qué toca | Decide |
|---|---|---|
| **P16** · La parte de las unidades del consorcio (R39) | Nada del 3a: R39 es propuesta y queda fuera. Si se valida antes de construir, entra la marca "del consorcio" en `unidad` | Alberto |
| **P47** · Ramas o turnos con dos desarrolladores | No bloquea el código, sí la integración. La rama ya tiene `main` (rebase del 16/10, con D-099, D-100 y el 2c). Lo que choca con `main` no es Compose ni el humo ni el CI, que no cambiaron desde el fork, sino `backend/src/proptech_api/app.py` (2.4 lo cambia; `main` le sumó el log de `arranque_fallido`) y `backend/src/proptech_core/compartido/roles.py` (3.5 lo cambia; `main` le sumó V3-14) | Juani y Alberto |
| **P42** · Validar los valores de plata | No bloquea (R01 y R03 se construyen "a validar"): los defaults y los rangos del vencimiento pueden cambiar después | Alberto (presentar el contador) |

Preguntas nuevas de la revisión, que no bloquean tareas pero conviene responder antes de construir
(detalle en `design.md`, Open Questions): **PR1** la auditoría del padrón que edita un colaborador;
**PR2** un trigger para las transiciones del estado de migración; **PR3** qué grupos parciales de
`parametros.yaml` se crean con el edificio y dónde queda el `habilitados: false` de R02; **PR4** cómo se
impide correr la carga del ejemplo en el piloto.

## Fuera del cambio

- **Las pantallas** (3b, E1), con sus `shape` previos, y el acceso de desarrollo sin login (E2), que se
  firma acá y se construye en el 3b.
- **Carga masiva desde Excel** (5), **cálculos** (4 y 7, incluido el recargo del segundo vencimiento),
  el **motor de reglas** (6b).
- **Correr el vencimiento al emitir** una liquidación puntual (D-100, P33): es del cambio 7, que lo
  registra; está anotado en su ficha. Acá se guarda el día fijo.
- **Que una liquidación emitida no cambie** al cambiar la tasa: se prueba en el 7, que es el que emite
  (HU-A1). Acá se prueba que la versión anterior queda intacta.
- **R02 activa** (barrios, v1.2), **R35**, **R36** y **R39** (propuestas sin validar).
- **Borrar** un edificio, una unidad o un grupo: no hay baja en el 3a. Una unidad mal cargada se
  corrige con una edición mientras el edificio no tenga liquidaciones.
- **El login** (2b) y **quién lee la auditoría**.

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 16/10/2026): `01_vision_y_objetivos.md`,
`02_descripcion_general.md`, `03_actores_y_roles.md`, `04_modelo_de_datos.md`,
`05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`,
`08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`,
`11_glosario.md`, `12_fichas_de_changes.md`, `13_motor_de_reglas.md`, `14_forma_de_trabajo.md`,
`15_lecciones.md`, `16_proyecto_final.md`, `README.md`.

- `04_modelo_de_datos.md`: **REWRITE** al archivar. `complejo` y `unidad` completas;
  `grupo_de_reparto` (con su modo), sus miembros, `categoria_de_gasto` y `configuracion_versionada`
  (con el vencimiento) pasan de "planificadas" a existentes, con sus columnas reales y los índices que
  sirven cada consulta; el ERD "Existente hoy"; la sección de la semilla.
- `05_reglas_de_negocio.md`: **REWRITE**, en parte **ya hecho en este propose** (B4): R01 dice que la
  carga no se rechaza, que se informa la suma y su estado y que la emisión se bloquea, con los dos
  modos de grupo de D-100; R34 suma la fila "Coeficientes fuera de tolerancia" (bloqueante duro,
  cambio 7) y la nombra entre los controles duros. Al archivar: R03 (día de vencimiento, único o
  doble) y R26 (pasa de "pendiente" a configuración de D-100).
- `07_flujos_principales.md`: **REWRITE**, **ya hecho en este propose**: el caso de error de
  coeficientes del flujo 1 (se informa, no se rechaza; bloquea la emisión) y el "Pendiente" de P19 y
  P24, resueltas.
- `12_fichas_de_changes.md`: **REWRITE**, **ya hecho en este propose**: fichas 3a y 3b (la partición,
  los `shape` al 3b, 24 tareas, sin bloqueos) y ficha 7 (el control de coeficientes de R34 y correr el
  vencimiento al emitir). Al archivar: el cierre del 3a y las filas de deuda que resuelve (R6, R11, la
  fila del 1b).
- `10_preguntas_abiertas.md`: **REWRITE**, **ya hecho en este propose**: el resumen ya no nombra a P19,
  P24 y P33 como bloqueantes del 3. Al archivar, si se responde alguna de P16, P47 o PR1 a PR4.
- `03_actores_y_roles.md`: **REWRITE** al archivar: la matriz de permisos (las acciones de
  configuración de E3 y la de lectura de B5) y las rutas.
- `09_decisiones_y_supuestos.md`: **APPEND** al archivar: una decisión con las elecciones de código
  del 3a y E1 a E10 tal como las firme el socio; otra con la matriz de D-096 modificada (E3 y la
  lectura de la configuración, B5); y otra con la partición en 3a y 3b si se aprueba E1.
- `06_funcionalidades.md`: **REWRITE** al archivar: HU-A1 deja de decir que queda un único vencimiento
  (D-100); sus criterios se cierran entre el 3a (los datos) y el 3b (las pantallas).
- `08_arquitectura_propuesta.md`: **REWRITE** al archivar: "Fronteras entre módulos" (`complejos` con
  `dominio/` propio, R01 en `compartido`, `compartido ↛ complejos`, quién lee los parámetros) y
  "Seguridad" (el barrido de rutas sin depender del prefijo; las tablas de sólo agregar en el paso de
  roles).
- `11_glosario.md`: **REWRITE** si hace falta sumar "estado de migración", "versión de configuración"
  y "modo de coeficientes" (verificar al archivar si ya están).
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar; lo escribe quien archiva.
- `01`, `02`, `13`, `14`, `16` y `README.md`: **none**. Ninguno describe algo que este cambio
  modifique.
- Fuera de `knowledge-base/`: `CHANGES.md` (**REWRITE**, ya hecho en este propose: C-06 partido en
  C-06a y C-06b, los `shape` en el 3b). `CLAUDE.md`/`AGENTS.md`: **none** en este propose, para no
  chocar con el 2c que los toca en `main`; al archivar, marcar el 3a.

## Impact

- **Backend**: `proptech_core/compartido/` (`Porcentaje`, `Superficie`, `Coeficiente`, la función pura
  de R01, `naming_convention`, semilla, `roles.py` con las tablas de sólo agregar);
  `proptech_core/complejos/` suma `dominio/` (versiones, modos de grupo) y casos de uso en
  `aplicacion/`; `proptech_core/acceso/dominio/permisos.py` (acciones y matriz) y
  `acceso/aplicacion/auditoria.py` (modelos de detalle nuevos); `proptech_api/complejos.py` y routers
  nuevos del mismo módulo; `proptech_api/app.py` (`--factory`).
- **Migraciones**: siete nuevas desde `0005` (edificio y unidad completos, grupos, modo de
  coeficientes, categorías, configuración versionada, vocabulario de auditoría) y `0004` congelada con
  una lista literal (no cambia nada en una base existente). Cada `downgrade` se ejercita sobre una
  base sin auditoría nueva; con auditoría nueva, el rollback es restaurar un respaldo.
- **Tests**: `tests/integracion/test_rutas_protegidas.py` (R6), un barrido de altas (R11),
  `test_fronteras_de_modulos.py` (`compartido ↛ complejos`), `test_catalogo_rls.py` (las tablas de
  sólo agregar), los de cada tabla y caso de uso contra PostgreSQL real como `proptech_app`.
- **Infra**: `infra/compose.yaml` y `backend/Dockerfile` (`--factory`, healthcheck de la web), sólo en
  la tarea 2.4.
- **Configuración**: `config/parametros.yaml` suma el vencimiento (día por defecto, modalidad y rango
  del recargo); `config/semilla/edificio-ejemplo.yaml` suma `estado_migracion` y el modo de cada grupo.
  Ninguna variable de entorno nueva.
- **Contrato de la API**: endpoints nuevos bajo `/api`, todos con identidad; hasta el 2b responden 401
  en producción, igual que los del 2a. `GET /api/unidades/{id}` del 2a cambia `nombre` por
  `identificador`.
- **Dependencias nuevas**: ninguna (pydantic ya está, sólo pasa a declararse directa).

## Aprobación

Gobernanza HIGH (D-094). La completa, a mano, uno de los dos socios. Ningún agente la escribe.

Elecciones de diseño (detalle y alternativas en `design.md`):

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Partir el 3 en 3a (backend) y 3b (pantallas) | Sí. El 3a son 24 tareas y es lo único que necesita el 4; los siete `shape` y las pantallas van al 3b, con propose propio. Se recomienda además mover la 7.2 (carga del ejemplo en la base) al 3b: el 3a queda en 23 y se registra como excepción a D-088, como el 1c || |
| E2 · Cómo se entra a las pantallas sin login, en desarrollo | Un punto de entrada de desarrollo **fuera del paquete instalado** (`backend/desarrollo/`), que arma la misma app y reemplaza la identidad con la del titular de la administración de ejemplo, igual que hacen los tests; sólo lo levanta un `compose.desarrollo.yaml` aparte (nunca `compose.override.yaml`, que Compose carga solo), con el puerto atado a `127.0.0.1`. La imagen de producción no lo contiene y la app de producción sigue dando 401. Riesgo escrito: si alguien pone `COMPOSE_FILE` con ese archivo en `infra/.env`, el servidor lo levanta; la contención real es la RLS forzada más la identidad fija en la administración de ejemplo, y un test del 3b falla si algún archivo del repo pone `COMPOSE_FILE` con `desarrollo`. El 2b lo borra entero. Se construye en el 3b. D11 || |
| E3 · Quién configura y quién lee la configuración | Se modifica la matriz de D-096 que ya existe. Crear un edificio, cambiar intereses, vencimiento o fondo de reserva, y confirmar "sin saldos previos": **sólo el titular**. Unidades, grupos y categorías: titular y colaborador "editar". **Leer** el padrón, los grupos, las categorías y la configuración: titular, colaboradores ("ver" y "editar") y consejo. **El vecino ve sólo lo suyo** (decisión de Juani): sus unidades, como en el 2a; pedir la configuración de su edificio le da 403 y la de otro, 404 || |
| E4 · Cómo se versiona la configuración | Una fila por versión con fecha de vigencia, sin fecha "hasta" (la siguiente la cierra), una sola versión por fecha (único en la base), nunca retroactiva (vigencia desde hoy, en hora de Mendoza), y de sólo agregar: la app no tiene `UPDATE` ni `DELETE` (y no los recupera en el siguiente `up`) y un trigger los rechaza. El alta del edificio acepta la configuración inicial del reglamento (si no viene, la de los parámetros), así el primer día no hace falta una segunda versión || |
| E5 · Cuándo se exige R01 | Cargar el padrón no se bloquea por la suma; la API informa siempre la suma, la diferencia y si es "ok", "advertencia" o "fuera de tolerancia". La emisión del cambio 7 se bloquea con un control duro nuevo de R34, "Coeficientes fuera de tolerancia", ya escrito en `05` y en la ficha 7 || |
| E6 · El edificio de ejemplo en la base | En una administración de ejemplo propia, con ids fijos escritos en el código (no son secretos), sólo por un comando explícito, nunca al arrancar. Correrlo otra vez no duplica: compara sólo lo que sale de la semilla (no lo que viene de `parametros.yaml`, D-042); si ya está igual, no hace nada y lo dice; si alguien lo cambió, falla sin tocar nada. No se corre en el piloto (PR4: hoy no lo frena nada técnico) || |
| E7 · Qué se audita | Tres acciones: crear un edificio, crear una versión de configuración y confirmar "sin saldos previos". Unidades, grupos y categorías no (son reversibles y no mueven plata todavía; PR1 pregunta si el padrón debería) || |
| E8 · Un alta que trae `id` | Se rechaza con 422 (cuerpo estricto) sin escribir nada, a diferencia de la asignación del 2a, que ignora `administracion_id`. Un barrido lo exige en toda ruta de alta, falla si una ruta nueva no tiene cuerpo de prueba y verifica que el 422 nombra `id` || |
| E9 · Cómo se fija el segundo vencimiento (D-100, P19) | Cada edificio guarda en su configuración un **día fijo de vencimiento del 1 al 28** (por defecto el 10, a validar, P42) y elige vencimiento **único** o **doble**. Si es doble, el segundo vencimiento es **otro día fijo del mismo mes, posterior al primero y hasta el 28**, y el recargo es **un porcentaje** (de 0,01 a 20,00, a validar, P42). Alternativa: el segundo como "N días después del primero". El cálculo del recargo es del 4 y el 7 || |
| E10 · La carga del ejemplo y la auditoría | La carga del ejemplo usa los mismos casos de uso que la API, así que **audita** crear el edificio y confirmar "sin saldos previos", con el titular de ejemplo como persona y un `request_id` propio del comando. Consecuencia: una base con el ejemplo cargado ya no baja con `downgrade` (se restaura un respaldo, B3). Alternativa: cargarlo sin auditar, por SQL directo, y perder que el ejemplo pase por las mismas reglas que un edificio real || |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
