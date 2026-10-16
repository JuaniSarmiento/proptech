## Why

Después del 2a la base ya tiene el candado, pero un edificio es apenas un nombre: `complejo` tiene
`id`, `administracion_id` y `nombre`, y `unidad` lo mismo más su `complejo_id`. Sin coeficientes, sin
grupos de reparto, sin categorías y sin la configuración de intereses y fondo de reserva, el cambio 4
(`motor-de-cuenta-corriente`) no tiene sobre qué calcular y el camino a M1 se frena. Es la ficha 3 de
`knowledge-base/12_fichas_de_changes.md`: que el administrador cree un edificio y lo configure como
dice su reglamento (**HU-A1**).

Cubre: **R01** (sólo la definición de grupos y la validación de coeficientes, con la tolerancia de
D-082), **R02** (sólo el campo de estado, desactivado, D-030, D-089), **R03** (su configuración, no el
cálculo), **R15** (el porcentaje), **R16** (categorías), **R09** en lo que toca a este cambio (el
estado de migración del edificio, D-082, D-083). Decisiones: D-010, D-013, D-029, D-030, D-031, D-041,
D-042, D-080, D-082, D-083, D-087, D-089, D-094, D-096 y D-098 (la deuda que hereda). Las reglas
propuestas R35, R36 y R39 **no entran**: ninguna se validó.

## Partición: 3a (este cambio) y 3b (las pantallas)

El alcance completo de la ficha (modelo, casos de uso, API, semilla en la base, deuda heredada,
acceso de desarrollo y siete pantallas) pasa largo de las veinte tareas: contado, da unas 23 del
backend más unas 15 del frontend. Se propone partirlo (elección **E1**):

- **3a `configuracion-del-edificio`** (este cambio, HIGH): el modelo, las reglas, los casos de uso, la
  API, la semilla cargada en la base y la deuda del 2a y del 1b con dueño 3. **23 tareas.**
- **3b `pantallas-del-edificio`** (nombre provisional, cambio aparte, propose propio): las pantallas,
  el acceso de desarrollo sin login (**E2**, que se firma acá porque toca el candado) y el
  "terminado" de frontend.

**Por qué así y no al revés**: el 4 necesita el modelo y la configuración versionada, no las
pantallas. Con la partición, el camino crítico a M1 queda `2a → 3a → 4` y el 3b sale de él. Además,
cada pantalla tiene que pasar por un `shape` con Juani antes de implementarse (proceso de impeccable,
`PRODUCT.md`/`DESIGN.md`): esas sesiones no son código y pueden hacerse mientras se construye el 3a
(tarea 8.1). Si el 2b (el login) llega antes que el 3b, el acceso de desarrollo de E2 ni siquiera se
construye. Las piezas tienen perfil de riesgo distinto (plata y aislamiento de un lado, accesibilidad
y diseño del otro), el mismo criterio con que D-097 partió el 2.

### Lo que entra en el 3b, para que se firme sabiendo qué viene

**Pantallas** (superficie del administrador, densa; ninguna del vecino ni del consejo):

1. **Mis edificios**: la lista de edificios del alcance, con su estado de migración, y "Crear edificio".
2. **Resumen del edificio**: qué falta configurar (padrón con la suma fuera de tolerancia, estado de
   migración pendiente) y lo próximo que hay que hacer. Una sola acción principal (principio 3 de
   `PRODUCT.md`).
3. **Padrón de unidades**: alta y edición de unidades, con la suma de coeficientes y su estado tal
   como los devuelve la API.
4. **Grupos de reparto**: método, unidades de cada grupo y su suma.
5. **Categorías de gasto**: crear, renombrar, ordenar y desactivar.
6. **Intereses y fondo de reserva**: la versión vigente, el historial y "Nueva versión".
7. **Confirmar "sin saldos previos"**: una acción irreversible, con confirmación explícita.

**Flujos**: crear un edificio y verlo arrancar con los valores de los parámetros; cargar el padrón
hasta que la suma quede "ok"; armar un grupo parcial; ajustar categorías; cambiar la tasa y ver la
versión anterior en el historial; confirmar "sin saldos previos".

**Reglas de diseño que aplican** (`PRODUCT.md`, `DESIGN.md`): coeficientes, porcentajes y tasas con
**números tabulares**, alineados a la derecha y con formato argentino (The Tabular Money Rule); el
estado de la suma de R01 y el estado de migración **nunca sólo con color**, siempre con texto (The
Never Color Alone Rule); una sola acción principal en terracota por pantalla (The One Voice Rule);
lo conocido antes que lo novedoso. **El frontend no calcula**: la suma de coeficientes, la diferencia
y su estado vienen de la API (regla dura de `CLAUDE.md`).

**Ninguna pantalla se diseña en este propose.** Cada una pasa por un `shape` con Juani antes de
implementarse (tarea 8.1 del 3a, sin código; el 3b no arranca sin esos briefs).

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

**Nivel HIGH** (D-087, D-094, ficha 3): guarda la configuración versionada de intereses y fondo de
reserva, que cambia montos, y suma permisos nuevos a la matriz de D-096. Un error acá no se ve hasta
que el cambio 7 emite con una tasa equivocada o con el padrón de otro edificio.

**Se propone y se espera la aprobación escrita y fechada de uno de los dos socios (Juani o Alberto)
antes de construir** (D-094). El constructor no arranca hasta que la sección "Aprobación", al final
de este archivo, tenga el nombre, la fecha, el alcance aprobado y la respuesta a cada elección E1 a
E8. Ningún agente completa esa sección. Un socio puede aprobar el cambio y rechazar una elección:
entonces se corrige el `design.md` antes de construir.

## What Changes

- **Deuda heredada, primero** (L-012, D-098):
  - **R6**: el barrido de rutas protegidas deja de depender de que cada router declare `/api` en su
    propio `prefix`; ve toda ruta de la app, venga por `include_router(prefix=...)`, por
    `add_api_route` o anidada. **Bloquea antes de la primera ruta nueva.**
  - **R11**: el id de un alta lo genera siempre el servidor. Un cuerpo de alta que trae `id`,
    `administracion_id` o `complejo_id` se rechaza con 422 sin escribir nada (**E8**), y un barrido
    lo exige en toda ruta `POST` presente y futura.
  - La fila del 1b con dueño 3 (auditorías del 13/10): `naming_convention`, tipos `Porcentaje` y
    `Superficie`, versión de la semilla como `Literal[1]`, pydantic como dependencia directa, la app
    con `--factory`, el healthcheck de la web contra `127.0.0.1`, `.gitignore` ampliado y el test de
    `chmod` en Windows. (El tope de lectura del YAML ya está hecho: 1 MiB en `cargador_yaml.py`.)
- **Edificio completo**: `complejo` suma `localidad` y el **estado de migración** (`pendiente`,
  `confirmada`, `sin_saldos_previos`, D-083); `unidad` suma identificador único dentro del edificio,
  tipo (los cuatro de D-029), piso, coeficiente, superficie y el estado desactivado de R02.
- **Grupos de reparto** (R01) con su método y sus unidades, siempre del mismo edificio y la misma
  administración (FK compuesta); "Generales" obligatorio, por coeficiente y con todas las unidades.
  La validación de coeficientes con la tolerancia de ±0,0001 se informa siempre y la hace cumplir el
  control antes de emitir del cambio 7 (**E5**).
- **Categorías de gasto** (R16): crear, renombrar, ordenar y desactivar; nunca borrar.
- **Configuración versionada de intereses y fondo de reserva** (R03, R15, D-080): menús cerrados con
  los rangos de `parametros.yaml`, una versión nueva por cambio con fecha de vigencia, fecha de alta y
  autor; las anteriores no se tocan (**E4**).
- **Crear un edificio** copia los valores de `config/parametros.yaml` del momento (D-042): cambiar el
  archivo después no altera edificios existentes.
- **Permisos** nuevos en la matriz de D-096 para configurar (**E3**) y **auditoría** de las tres
  acciones que importan (**E7**), cada una con su migración de vocabulario.
- **API** bajo `/api` para todo lo anterior, con contrato de error explícito (401, 404, 403, 409 y 422).
- **El edificio de ejemplo en la base**: la semilla suma el estado de migración
  (`sin_saldos_previos`), el validador se alinea con R01 y con la respuesta a P24, y un comando
  explícito lo carga en una administración de ejemplo, idempotente (**E6**).
- **Shape de las pantallas del 3b** con Juani, sin código (tarea 8.1).

## Capabilities

### New Capabilities

- `edificios-y-unidades`: alta de un edificio con los valores de los parámetros, sus unidades con
  tipo, coeficiente y superficie, y su estado de migración.
- `grupos-de-reparto`: grupos con método y unidades del mismo edificio, y la validación de
  coeficientes de R01.
- `categorias-de-gasto`: las categorías de cada edificio y su ciclo de vida (crear, renombrar,
  ordenar, desactivar).
- `configuracion-versionada`: intereses y fondo de reserva como versiones de sólo agregar, con
  vigencia, autor y fecha.

### Modified Capabilities

- `datos-semilla`: la semilla suma el estado de migración, el validador acepta la tolerancia de R01 y
  un comando carga el edificio de ejemplo en la base (hasta hoy, el comando tenía prohibido escribir).
- `autorizacion-por-rol`: el barrido de rutas que no depende del prefijo (R6) y los permisos de
  configuración que se suman a la matriz de D-096.
- `auditoria-de-acciones`: tres acciones nuevas en el vocabulario cerrado.

## Que intente romper el rompedor

Además de lo que ya pide la ficha 3 (coeficientes de un grupo que no suman 1, una unidad repetida,
cambiar la tasa y que se pierda la versión anterior, editar la configuración de otro edificio):

- **Coeficientes que no suman 1** (o 100 %, si la pantalla los muestra en porcentaje): 0,9999 y
  1,0001 se aceptan con advertencia (borde incluido); 0,9998 y 1,0002 se rechazan con la diferencia;
  un coeficiente `0`, negativo, con siete decimales, con dígitos Unicode o con `\n` al final; un
  grupo parcial cuando P24 esté respondida; la suma calculada en el frontend en vez de leerla de la
  API.
- **Versiones de configuración superpuestas**: dos versiones con la misma fecha de vigencia, dos
  pedidos simultáneos que crean versión para el mismo día (uno tiene que dar 409), una versión
  retroactiva, un `UPDATE` o `DELETE` de una versión vieja como `proptech_app` y como migrador, una
  "configuración vigente" consultada para una fecha anterior a la primera versión.
- **Una unidad de otro edificio o de otra administración**: sumarla a un grupo por su id (formato
  válido, fila que existe, L-017), mover una unidad a otro edificio por `PATCH`, crear un grupo en el
  edificio A con unidades de B, todo por la API **y** por SQL directo como `proptech_app` (la FK
  compuesta tiene que frenarlo aunque la aplicación se equivoque).
- **El edificio de ejemplo cargado dos veces**: dos corridas seguidas, dos corridas en paralelo, una
  segunda corrida después de que alguien editó una unidad del ejemplo, el comando sin tenant, el
  comando con un tenant de otra administración.
- **Montos con float**: un coeficiente, una tasa, un porcentaje o una superficie mandados como número
  JSON (`0.1`, `3.5`, `1e-1`) en vez de texto; `NaN`, `Infinity`, `-0`; un `float` que se cuela al
  construir un `Decimal` en el núcleo o al serializar la respuesta.
- **Ids del cliente** (R11): un alta con `id`, `administracion_id` o `complejo_id` en el cuerpo; una
  ruta `POST` nueva agregada con `include_router(prefix=...)` que el barrido no ve (R6).
- **Permisos**: un colaborador "ver" que crea una categoría, un colaborador "editar" que cambia la tasa
  o confirma "sin saldos previos", el consejo o un vecino que escriben algo, un colaborador que crea un
  edificio.
- **El estado de migración**: volver de `sin_saldos_previos` a `pendiente`, confirmarlo dos veces,
  confirmarlo con unidades que ya tienen saldo (cuando exista el 4).

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-021). Detalle en `design.md` ("Cómo aplica
cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-003 · contar los tests | 1.1 y 9.1 |
| L-005 · verde es todo el workflow | convención de `tasks.md` y 9.1 |
| L-006 · lo destructivo apunta a un nombre del proyecto | 7.2 (la carga del ejemplo sólo toca la administración de ejemplo) |
| L-007 · el error de una librería es una salida | 2.2, 6.1 a 6.3 (un 422 no repite el valor rechazado) |
| L-008 · coincidencia completa y sólo ASCII | 2.3 (`Porcentaje`, `Superficie`), 4.1 (coeficientes), 5.2 (identificador de unidad) |
| L-009 · el arreglo se prueba en el gemelo | 2.3 y 7.1 (el validador de la semilla y el de la API comparten tipos y tolerancia) |
| L-010 · la corrida de cierre va al final | 9.1 |
| L-012 · la deuda al primer cambio que usa la pieza | 2.1 a 2.4 |
| L-013 · mutar sin commit exige copia | convención de `tasks.md`; 2.1, 2.2, 3.4 |
| L-016 · una observación tiene que poder dar otro resultado | 3.1 a 3.5 y 5.x (como `proptech_app`, nunca como superusuario) |
| L-017 · la entrada del escenario | 5.3 y 6.2 (ids válidos de filas que existen en otro edificio u otra administración) |
| L-018 · verificar el efecto, no la forma | 3.4 (la versión se intenta editar de verdad, no se mira el trigger en el catálogo), 3.2 (la FK compuesta se prueba insertando, no leyendo `pg_constraint`) |
| L-019 · un test que no puede dar rojo | 2.1 y 2.2 (el barrido se ve fallar con una ruta montada con prefijo) |
| L-020 · arreglar un bloqueante puede crear otro | 2.1 (cambiar el barrido no puede dejar afuera las rutas de hoy) |
| L-021 · la instrucción del auditor acota lo que los demás miran | sección de arriba: es un piso, no un techo |

L-001, L-011, L-014 y L-015 no aplican: este cambio no suma dependencias que puedan congelarse, ni
plazos sobre operaciones con efecto, ni Bash con `|| true`, ni hilos. L-002 y L-004 aplican como en
todo cambio (configuración rota de muchas formas; otro camino para verificar) y no tienen tarea propia.

## Preguntas abiertas que bloquean

No se dan por resueltas. Bloquean **tareas puntuales**, no el arranque: el constructor puede empezar
por lo que no depende de ninguna. De las 23 tareas, 12 están libres (1.1, sección 2, 3.1, 3.3, 3.5,
5.2, 5.4, 8.1 y el cierre 9.1), 4 tienen una parte bloqueada (4.1, 6.2, 6.3 y 7.1) y 7 están bloqueadas
enteras (3.2, 3.4, 5.1, 5.3, 5.5, 6.1 y 7.2).

| Pregunta | Qué bloquea | Decide |
|---|---|---|
| **P24** · Coeficientes de grupos parciales: propios por unidad o los generales renormalizados | 3.2, 4.1 (grupos parciales), 5.3, 6.2 (grupos), 7.1: la forma de la tabla de miembros y el validador de la semilla, cuyos grupos Ascensor y Cocheras hoy no suman 1 | Alberto (según el reglamento del piloto), con Juani |
| **P19** · Doble vencimiento con recargo escalonado (R26) en vez del vencimiento único de R03 | 3.4, 5.5 y la parte de configuración de 6.3; por arrastre 5.1, 6.1 y 7.2, porque crear un edificio crea su primera versión | Alberto |
| **P33** · El vencimiento: día fijo del edificio o cargado al emitir | Las mismas que P19: si la configuración versionada guarda el día de vencimiento | Alberto, con Juani |

Sobre P19 y P33 hay un dato que puede servirle a Juani para decidir si espera: cualquiera de las dos
respuestas posibles **suma** campos a la configuración (un segundo vencimiento y su recargo, un día de
vencimiento) y no cambia los de R03, que es vigente. Construir 3.4 con R03 tal cual y agregar una
migración aditiva cuando lleguen las respuestas es posible; **no se propone hacerlo sin que Juani lo
decida**, porque la ficha las marca como bloqueantes del 3.
| **P16** · La parte de las unidades del consorcio (R39) | Nada del 3a: R39 es propuesta y queda fuera. Si se valida antes de construir, entra la marca "del consorcio" en `unidad` | Alberto |
| **P47** · Ramas o turnos con dos desarrolladores | No bloquea el código, sí la integración: este cambio vive en la rama `propose-3-edificio` mientras el 2c avanza en `main`, y los dos tocan `compose.yaml` (tarea 2.4). Hace falta acordar el mecanismo antes de integrar | Juani y Alberto |
| **P42** · Validar los valores de plata | No bloquea (R01 y R03 se construyen "a validar"): los defaults pueden cambiar después | Alberto (presentar el contador) |

## Fuera del cambio

- **Las pantallas** (3b, E1), con su `shape` previo, y el acceso de desarrollo sin login (E2), que se
  firma acá y se construye en el 3b.
- **Carga masiva desde Excel** (5), **cálculos** (4 y 7), el **motor de reglas** (6b).
- **Que una liquidación emitida no cambie** al cambiar la tasa: se prueba en el 7, que es el que emite
  (HU-A1). Acá se prueba que la versión anterior queda intacta.
- **R02 activa** (barrios, v1.2), **R35**, **R36** y **R39** (propuestas sin validar), **R26** (salvo
  que P19 la confirme antes de construir, y entonces se reabre el design).
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

- `04_modelo_de_datos.md`: **REWRITE**. `complejo` y `unidad` completas; `grupo_de_reparto`, sus
  miembros, `categoria_de_gasto` y `configuracion_versionada` pasan de "planificadas" a existentes, con
  sus columnas reales; el ERD "Existente hoy"; la sección de la semilla (estado de migración, carga
  en la base, validador alineado).
- `03_actores_y_roles.md`: **REWRITE** de la matriz de permisos (las acciones de configuración de E3)
  y de las rutas (los endpoints nuevos exigen identidad).
- `09_decisiones_y_supuestos.md`: **APPEND**. Al archivar, una decisión con las elecciones de código
  del 3a y E1 a E8 tal como las firme el socio, y otra con la partición en 3a y 3b si se aprueba E1.
- `12_fichas_de_changes.md`: **REWRITE**. La ficha 3 ya queda partida en 3a y 3b en este propose; al
  archivar, el cierre del 3a y las filas de deuda que resuelve (R6, R11, la fila del 1b).
- `05_reglas_de_negocio.md`: **none**, salvo que P24, P19 o P33 se respondan antes de construir: en ese
  caso, **REWRITE** de R01 (grupos parciales) o R03 (vencimiento). R01, R03, R15 y R16 no cambian: este
  cambio las cumple.
- `06_funcionalidades.md`: **none** en el 3a. HU-A1 no cambia; sus criterios se cierran entre el 3a
  (los datos) y el 3b (las pantallas).
- `08_arquitectura_propuesta.md`: **REWRITE** de "Fronteras entre módulos" (`complejos` con `dominio/`
  propio, quién lee los parámetros) y de "Seguridad" (el barrido de rutas sin depender del prefijo).
- `10_preguntas_abiertas.md`: **REWRITE**, sólo si alguna de P16, P19, P24, P33 o P47 se responde
  durante el cambio.
- `11_glosario.md`: **REWRITE** si hace falta sumar "estado de migración" y "versión de
  configuración" (verificar al archivar si ya están).
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar; lo escribe quien archiva.
- `01`, `02`, `07`, `13`, `14`, `16` y `README.md`: **none**. Ninguno describe algo que este cambio
  modifique.
- Fuera de `knowledge-base/`: `CHANGES.md` (**REWRITE**, ya hecho en este propose: C-06 partido en
  C-06a y C-06b). `CLAUDE.md`/`AGENTS.md`: **none** en este propose, para no chocar con el 2c que los
  toca en `main`; al archivar, marcar el 3a.

## Impact

- **Backend**: `proptech_core/complejos/` suma `dominio/` (coeficientes, versiones) y casos de uso en
  `aplicacion/`; `proptech_core/acceso/dominio/permisos.py` (acciones y matriz);
  `proptech_core/compartido/` (`Porcentaje`, `Superficie`, `naming_convention`, semilla);
  `proptech_api/complejos.py` y routers nuevos del mismo módulo; `proptech_api/app.py` (`--factory`).
- **Migraciones**: cinco nuevas desde `0005` (edificio y unidad completos, categorías, grupos,
  configuración versionada, vocabulario de auditoría), cada una con su `downgrade` ejercitado.
- **Tests**: `tests/integracion/test_rutas_protegidas.py` (R6), un barrido de altas (R11), los de cada
  tabla y caso de uso contra PostgreSQL real como `proptech_app`.
- **Infra**: `infra/compose.yaml` (`--factory`, healthcheck de la web), sólo en la tarea 2.4 y después
  de integrar el 2c.
- **Configuración**: `config/semilla/edificio-ejemplo.yaml` suma `estado_migracion`. Ninguna variable
  de entorno nueva.
- **Contrato de la API**: endpoints nuevos bajo `/api`, todos con identidad; hasta el 2b responden 401
  en producción, igual que los del 2a.
- **Dependencias nuevas**: ninguna (pydantic ya está, sólo pasa a declararse directa).

## Aprobación

Gobernanza HIGH (D-094). La completa, a mano, uno de los dos socios. Ningún agente la escribe.

Elecciones de diseño (detalle y alternativas en `design.md`):

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Partir el 3 en 3a (backend) y 3b (pantallas) | Sí: el 3a son 23 tareas y es lo único que necesita el 4; el 3b va con propose propio, después de los `shape` || |
| E2 · Cómo se entra a las pantallas sin login, en desarrollo | Un punto de entrada de desarrollo **fuera del paquete instalado** (`backend/desarrollo/`), que arma la misma app y reemplaza la identidad con la del titular de la administración de ejemplo, igual que hacen los tests; sólo lo levanta un `compose.desarrollo.yaml` aparte, con el puerto atado a `127.0.0.1`. La imagen de producción no lo contiene (un test lo verifica) y la app de producción sigue dando 401. El 2b lo borra entero. Se construye en el 3b. Alternativas y riesgos en el design, D11 || |
| E3 · Quién configura | Crear un edificio, cambiar intereses o fondo de reserva y confirmar "sin saldos previos": **sólo el titular** (cambian plata o son irreversibles). Unidades, grupos y categorías: titular y colaborador "editar". Consejo y vecino: nada || |
| E4 · Cómo se versiona la configuración | Una fila por versión con fecha de vigencia, sin fecha "hasta" (la siguiente la cierra), una sola versión por fecha (único en la base), nunca retroactiva (vigencia desde hoy, en hora de Mendoza), y de sólo agregar: la app no tiene `UPDATE` ni `DELETE` y un trigger los rechaza || |
| E5 · Cuándo se exige R01 | Cargar el padrón unidad por unidad no se bloquea por la suma; la API informa siempre la suma, la diferencia y si es "ok", "advertencia" o "fuera de tolerancia". El que bloquea es el control antes de emitir del cambio 7 (R34) || |
| E6 · El edificio de ejemplo en la base | En una administración de ejemplo propia, con ids fijos escritos en el código (no son secretos), sólo por un comando explícito, nunca al arrancar. Correrlo otra vez no duplica: si ya está igual, no hace nada y lo dice; si alguien lo cambió, falla sin tocar nada. No se corre en producción || |
| E7 · Qué se audita | Tres acciones: crear un edificio, crear una versión de configuración y confirmar "sin saldos previos". Unidades, grupos y categorías no (son reversibles y no mueven plata todavía) || |
| E8 · Un alta que trae `id` | Se rechaza con 422 (cuerpo estricto) sin escribir nada, a diferencia de la asignación del 2a, que ignora `administracion_id` || |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
