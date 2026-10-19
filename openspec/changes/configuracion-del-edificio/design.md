## Context

Ver `proposal.md` (Why y Partición). Lo que condiciona el cómo:

- **Lo que dejó el 2a** (`openspec/changes/archive/2026-10-15-aislamiento-por-administracion/`):
  `complejo` (`id`, `administracion_id`, `nombre`, `UNIQUE (administracion_id, id)`) y `unidad`
  (`id`, `administracion_id`, `complejo_id`, `nombre`, FK compuesta hacia `complejo` y
  `UNIQUE (administracion_id, complejo_id, id)`), ambas con RLS forzada por
  `migraciones/ayudas_rls.py::aislar_por_administracion`; el migrador sin `BYPASSRLS` (E1 del 2a); la
  identidad inyectable (`proptech_api/acceso.py`, 401 en producción); `alcanza` y `puede`
  (`acceso/dominio/permisos.py`); la auditoría de `acceso.aplicacion` con `@accion_sensible`; el
  guardián del catálogo (`tests/integracion/test_catalogo_rls.py`), que ya falla si una tabla con
  `complejo_id` admite nulos o no tiene la FK compuesta, y que **exige** `SELECT, INSERT, UPDATE,
  DELETE` para la app en toda tabla con `administracion_id`; el paso de roles (`compartido/roles.py`),
  que en **cada** `antes()` re-otorga esos cuatro permisos a toda tabla de `public` salvo
  `alembic_version`, `auditoria` y `accion_de_auditoria`, y deja `ALTER DEFAULT PRIVILEGES` con los
  cuatro para toda tabla nueva del migrador. Compose corre `roles antes` en cada `up`.
- **Lo que dejó el 1b**: `parametros.py` (menús y rangos: `Intereses`, `FondoDeReserva`,
  `GrupoDeReparto`, `CategoriaDeGasto`, tipos de unidad) y `compartido/semilla.py` (el edificio de
  ejemplo validado, con suma **exacta** de coeficientes y `version: int`). `crear_app()` ya lee los
  parámetros al arrancar y falla si son inválidos.
- **El barrido de rutas del 2a** (`tests/integracion/test_rutas_protegidas.py::_api_routes`) recorre
  sólo los `_IncludedRouter` y filtra `sub.path.startswith("/api")` sobre el router **original**: una
  ruta montada con `include_router(prefix="/api")` tiene un `path` sin `/api` en su router original y
  queda afuera **en silencio**; una agregada con `add_api_route` sobre la app, también. Esa es R6.
- **La migración `0004` lee el enum vivo**: `from proptech_core.acceso.dominio.permisos import Accion`
  y `bulk_insert(... for accion in Accion)`. Cualquier miembro nuevo de `Accion` aparece en 0004 en
  una base armada desde cero (D14).
- **`main` integrado**: la rama `propose-3-edificio` se rebasó sobre `main` el 16/10/2026 (D-099,
  D-100 y el 2c completo, todavía sin archivar). Desde el fork, `main` cambió `proptech_api/app.py`
  (el log de `arranque_fallido`) y `compartido/roles.py` (V3-14); `infra/compose.yaml`, `humo.sh` y el
  CI no cambiaron.
- **D-100** (16/10/2026) resolvió P19, P33 y P24 con "las dos variantes": vencimiento único o doble
  por edificio, día fijo que se puede correr al emitir, y dos modos de coeficientes por grupo
  parcial. Este design las baja al modelo.
- **Frontend**: `web/` es Next 16 con una página vacía, sin Tailwind ni librería de tests de
  componentes. Todo lo de pantallas es del 3b (E1).

## Goals / Non-Goals

**Goals:**

- Que el modelo del edificio quede completo para el cambio 4, con la base frenando cualquier cruce de
  edificio o de administración aunque la aplicación se equivoque.
- Que la configuración que cambia plata sea de sólo agregar, con historia que nadie de la app pueda
  reescribir, y que eso sobreviva a cada `up`.
- Cerrar R6 antes de la primera ruta y dejar R11 como propiedad verificada de toda alta futura.
- Que el vecino vea sólo lo suyo también en las rutas nuevas.
- Dejar firmada (E2) la forma de entrar a las pantallas sin login, aunque se construya en el 3b.

**Non-Goals:**

- Pantallas y sus `shape` (3b), cálculos (4, 7; incluido el recargo del segundo vencimiento y correr
  el vencimiento al emitir), importación (5), motor de reglas (6b).
- Resolver P16: el design marca qué cambiaría, no la elige.
- Bajas de edificios, unidades o grupos.

## Decisions

### D1 · Partición en 3a y 3b (E1)

Ver `proposal.md`. Alternativas descartadas: **un solo cambio** (unas 40 tareas, dos perfiles de
riesgo en la misma aprobación, y el 4 esperando pantallas que no necesita); **tres cambios** (modelo,
API, pantallas): la API sin su modelo no se revisa sola y el costo de cada vuelta de
constructor/rompedor/auditor se paga una vez más sin ganar nada. Los siete `shape` pasan al 3b como
precondición de su propose: dentro del 3a ataban su cierre a siete sesiones de diseño. Revertir la
partición cuesta poco: el 3b se podría sumar como secciones nuevas de este `tasks.md` antes de
construir.

Con D-100 y los bloqueantes de la revisión el 3a queda en 24 tareas. La recomendación es mover la 7.2
(la carga del ejemplo en la base) al 3b, que es el único que la necesita (E2 fija la identidad en el
titular de esa administración), y registrar 23 como excepción a D-088. Se decide al firmar E1.

### D2 · Modelo de tablas

Todas con `administracion_id NOT NULL`, RLS forzada con `aislar_por_administracion`, y toda tabla que
cuelga de un edificio con `complejo_id NOT NULL` y FK compuesta `(administracion_id, complejo_id) →
complejo` (convención del 2a, que el guardián ya exige). Tipos de plata y proporciones en `NUMERIC`,
nunca `float`; en Python, `Decimal` construido desde texto.

| Tabla | Qué suma | Restricciones |
|---|---|---|
| `complejo` (tarea 3.1) | `localidad TEXT NOT NULL`, `estado_migracion TEXT NOT NULL DEFAULT 'pendiente'` | `CHECK` de los tres estados |
| `unidad` (tarea 3.1) | `identificador`, `tipo`, `piso`, `coeficiente NUMERIC(7,6)`, `superficie_m2 NUMERIC(10,2)`, `estado TEXT NULL` (R02, desactivado) | `UNIQUE (administracion_id, complejo_id, identificador)`; `CHECK coeficiente > 0 AND coeficiente <= 1`; `CHECK superficie_m2 > 0`; `CHECK tipo IN` los cuatro de D-029. `nombre` del 2a pasa a ser `identificador` (renombrado en la migración, con su `downgrade`) |
| `grupo_de_reparto` (tarea 3.2) | `clave`, `nombre`, `metodo`, `es_generales BOOL` | `UNIQUE (administracion_id, complejo_id, clave)`; `UNIQUE (administracion_id, complejo_id, id)`; un solo `es_generales` por edificio (índice único parcial) y `CHECK` de que "Generales" es por coeficiente |
| `grupo_unidad` (tarea 3.2) | `grupo_id`, `unidad_id` | FK compuesta `(administracion_id, complejo_id) → complejo` (la que exige el guardián, nota N9 a), `(administracion_id, complejo_id, grupo_id)` → grupo y `(administracion_id, complejo_id, unidad_id)` → unidad: **la misma `complejo_id` en las tres FK es lo que hace imposible un miembro de otro edificio**; `UNIQUE (grupo_id, unidad_id)` |
| modo de coeficientes (tarea 3.3, D-100, P24) | `grupo_de_reparto.modo_de_coeficientes TEXT NOT NULL DEFAULT 'renormalizado'`; `grupo_unidad.modo_de_coeficientes TEXT NOT NULL` y `grupo_unidad.coeficiente NUMERIC(7,6) NULL` | ver D15 |
| `categoria_de_gasto` (tarea 3.4) | `clave`, `nombre`, `orden INT`, `activa BOOL` | `UNIQUE (administracion_id, complejo_id, clave)`; `UNIQUE (administracion_id, complejo_id, lower(nombre))` (índice único); `UNIQUE (administracion_id, complejo_id, orden) DEFERRABLE INITIALLY DEFERRED` para reordenar en una transacción |
| `configuracion_versionada` (tarea 3.6) | `vigente_desde DATE`, `tasa_mensual NUMERIC(4,2)`, `dias_de_gracia SMALLINT`, `forma_de_calculo TEXT`, `porcentaje_fondo NUMERIC(5,2)`, `dia_de_vencimiento SMALLINT`, `modalidad_de_vencimiento TEXT`, `dia_segundo_vencimiento SMALLINT NULL`, `recargo_segundo_vencimiento NUMERIC(5,2) NULL`, `autor_id`, `creada_en TIMESTAMPTZ` | `UNIQUE (administracion_id, complejo_id, vigente_desde)`; `CHECK` de rangos iguales a `parametros.py`; el `CHECK` de coherencia del vencimiento (D3); FK compuesta del autor a `persona`; trigger `BEFORE UPDATE OR DELETE` y `BEFORE TRUNCATE` que rechaza; tabla de sólo agregar en el paso de roles (D16) |
| `accion_de_auditoria` (tarea 3.7) | cinco filas: `crear_edificio`, `crear_version_de_configuracion`, `confirmar_sin_saldos_previos`, `configurar_padron` y `ver_configuracion_del_edificio` (las dos últimas son permisos y no se auditan, pero el vocabulario es uno solo con `Accion`, como en el 2a) | el vocabulario cerrado del 2a; la migración las inserta con una lista literal (D14) |

"Generales" no guarda sus miembros en `grupo_unidad`: es "todas las unidades del edificio" por
definición (`es_generales`), así una unidad nueva entra sola y no hay forma de que una quede afuera.
Los grupos parciales guardan sus miembros, con o sin coeficiente propio según su modo (D15).

**Índices** (KB 04 los dejaba "a decidir en el design del cambio 3"): los `UNIQUE` de la tabla cubren
las consultas de este cambio. `unidad (administracion_id, complejo_id, identificador)` sirve la lista
del padrón y el conflicto de identificador; `grupo_de_reparto (administracion_id, complejo_id, clave)`
la lista de grupos; `grupo_unidad (grupo_id, unidad_id)` los miembros de un grupo;
`categoria_de_gasto (administracion_id, complejo_id, orden)` la lista ordenada;
`configuracion_versionada (administracion_id, complejo_id, vigente_desde)` la vigente para una fecha
(`ORDER BY vigente_desde DESC LIMIT 1`). Ninguna consulta nueva recorre una tabla que crece sin
índice; el plan de cada una lo revisa el DBA en verify.

Una migración por tarea, numerada desde `0005` en el orden de `tasks.md`.

Alternativa descartada para `tipo`: una tabla de tipos por edificio copiada de los parámetros. D-029
fija los cuatro tipos; si algún día cambian, es una migración, igual que el vocabulario de auditoría.
Para que el `CHECK` y `parametros.yaml` no sean dos fuentes de verdad que se separan, la lectura de
los parámetros (`parametros.py`) rechaza un tipo de unidad que no esté entre los cuatro de D-029, con
la misma constante que usa la migración (tarea 2.3, nota N9 c).

### D3 · Versionado de la configuración (E4, E9)

Una fila por versión con `vigente_desde`; **sin columna "hasta"**: la vigente para una fecha es la de
mayor `vigente_desde <= fecha`. Con eso la superposición no se puede escribir, y el `UNIQUE` por fecha
resuelve los pedidos simultáneos (uno gana, el otro recibe 409 al traducir `UniqueViolation`). La
primera versión nace con el edificio, vigente desde el día de alta, con **la configuración que traiga
el alta** o, si no trae, la de los parámetros (nota N3: así el administrador que crea el edificio con
la tasa de su reglamento no recibe 409 ni tiene que fijarla "desde mañana"). Una versión nueva exige
`vigente_desde >= hoy` en `America/Argentina/Mendoza`, calculado en el servidor.

- **Alternativa descartada**: rangos `daterange` con `EXCLUDE USING gist` (necesita la extensión
  `btree_gist`, que el rol de la app no puede crear y suma una pieza al rol de arranque) y una fila
  "hasta" que hay que actualizar al crear la siguiente, contradiciendo "sólo agregar".
- **Alternativa descartada**: permitir vigencias retroactivas. Cambiaría lo que debería haber cobrado
  una liquidación ya emitida; si hace falta corregir una tasa pasada, es una corrección (R08) del
  cambio 4 en adelante, no una edición de la configuración.
- **Alternativa descartada para el primer día** (N3): varias versiones el mismo día y vale la de mayor
  `creada_en`. Cambia el `UNIQUE` y vuelve ambiguo "la vigente para una fecha"; aceptar la
  configuración en el alta cuesta un campo opcional.
- **Sólo agregar**, igual que `auditoria` pero sin cambiarle el dueño: el migrador es dueño de la
  tabla (podría desactivar el trigger), la app sólo tiene `SELECT, INSERT` **y los conserva así en
  cada `up`** (D16), y el trigger rechaza `UPDATE`, `DELETE` y `TRUNCATE` para cualquier rol. Son dos
  capas de verdad: la de permisos se prueba sola con el trigger deshabilitado sobre una copia. Dueño =
  rol de arranque, como `auditoria`, queda descartado: el migrador ya es de confianza equivalente al
  superusuario sobre sus tablas (E1 del 2a) y cada cambio de estructura tendría que pasar por el paso
  de roles. Si Juani prefiere el mismo nivel que la auditoría, se dice al firmar E4.
- **Cómo la usa el 7**: cada liquidación referencia la versión con la que se calculó (historia de
  R03 y R15). El 3a deja la función `configuracion_vigente(complejo_id, fecha)`; qué fecha usa el 7
  (período, emisión o vencimiento) es P34 y es del 4 y el 7.
- **El vencimiento (D-100, P19 y P33)**:
  - `dia_de_vencimiento SMALLINT NOT NULL CHECK (dia_de_vencimiento BETWEEN 1 AND 28)` (decisión de
    Juani: del 1 al 28, así existe en todos los meses, febrero incluido). Es el día **fijo** del
    edificio; correrlo en una liquidación puntual (un feriado, un ajuste) lo hace el cambio 7 al
    emitir, con registro, y no toca esta configuración.
  - `modalidad_de_vencimiento TEXT NOT NULL CHECK IN ('unico', 'doble')`.
  - Si es doble, el segundo vencimiento es **otro día fijo del mismo mes** (`dia_segundo_vencimiento`)
    y el recargo es **un porcentaje** (`recargo_segundo_vencimiento NUMERIC(5,2)`, decisión de Juani).
    **Elección E9** (es de producto): día fijo del mismo mes, posterior al primero y hasta el 28.
    Alternativa: un desplazamiento en días desde el primero (`dias_hasta_segundo_vencimiento`), que
    puede caer en el mes siguiente y obliga a definir qué pasa al correr el primero. Se propone el día
    fijo porque es como lo escriben los reglamentos y la boleta ("1.er vencimiento 10, 2.º
    vencimiento 20").
  - **`CHECK` de coherencia**, en la base:
    `(modalidad_de_vencimiento = 'unico' AND dia_segundo_vencimiento IS NULL AND recargo_segundo_vencimiento IS NULL)
     OR (modalidad_de_vencimiento = 'doble' AND dia_segundo_vencimiento IS NOT NULL
         AND recargo_segundo_vencimiento IS NOT NULL
         AND dia_segundo_vencimiento > dia_de_vencimiento AND dia_segundo_vencimiento <= 28
         AND recargo_segundo_vencimiento > 0)`,
    más el rango del recargo que fijen los parámetros.
  - `parametros.yaml` y `Parametros` suman `vencimiento: { dia: 10, modalidad: unico }` y el rango
    del recargo (por defecto de 0,01 a 20,00); son valores **a validar (P42)** y se copian al crear el
    edificio (D-042), como el resto. El recargo se aplica en el 4 o el 7; acá sólo se guarda.

### D4 · Cuándo se exige R01 (E5)

La suma de coeficientes la calcula una **función pura de `compartido`** (D10) con `Decimal` y se
**informa** en cada respuesta del padrón y de los grupos (`suma`, `diferencia`, `estado`), con los
bordes de D-082 incluidos. Cargar el padrón no se bloquea, porque una carga unidad por unidad pasa
necesariamente por sumas parciales que no dan 1. El que bloquea es el control antes de emitir del
cambio 7: este propose suma a R34 la fila **"Coeficientes fuera de tolerancia"**, bloqueante **duro**
(no se acepta con registro), con dueño el 7, y la anota en su ficha. Así R01 tiene quién la haga
cumplir desde que se firma E5, y no sólo cuando alguien se acuerde. R01 en `05` se reescribe en este
mismo propose ("la carga no se rechaza; se informa la suma y su estado; la emisión se bloquea").

Se informan "Generales" y cada grupo con modo `propios` (D15). Un grupo `renormalizado` no tiene suma
que informar: sus coeficientes salen de dividir los generales por la suma del grupo.

Alternativa descartada: bloquear cada alta (impide cargar el padrón de a una unidad) o exigir un
"confirmar padrón" en el 3a (un estado más que nadie pidió y que el 5, al importar, tendría que
saltear).

### D5 · Permisos, lectura y auditoría (E3, E7, B5)

`Accion` suma `crear_edificio`, `crear_version_de_configuracion`, `confirmar_sin_saldos_previos`
(titular), `configurar_padron` (titular y colaborador "editar": unidades, grupos y categorías) y
`ver_configuracion_del_edificio` (titular, colaborador "ver", colaborador "editar" y consejo; **el
vecino no**, decisión de Juani: "el vecino ve sólo lo suyo"). La matriz es la misma función pura de
D-096, y la spec se **modifica** en su requisito existente (`autorizacion-por-rol` › Permiso por
acción según D-096), no se suma una matriz aparte (nota N6 a): al archivar queda una sola. Al archivar
va una decisión nueva en `09` con la matriz modificada.

**Crear un edificio no tiene alcance todavía**: se evalúa sólo `puede` con `complejo_id=None`, que hoy
sólo cumple el titular (su asignación no tiene complejo). `puede` hoy recibe un `UUID` obligatorio:
se amplía para aceptar `None` sólo en esa acción, y un test exige que cualquier otra acción con `None`
se niegue.

**Lectura**: los `GET` de configuración (padrón, resumen, grupos, categorías, configuración vigente y
versiones) exigen `ver_configuracion_del_edificio`, con el orden del 2a: un vecino que pide la
configuración del complejo de su unidad está dentro del alcance (`alcanza` lo deja, D-076) y recibe
**403** con el permiso faltante; uno que pide la de otro complejo recibe **404**. El vecino sigue
viendo sus unidades por `GET /api/unidades/{id}` del 2a (con el coeficiente de su unidad, que es suyo)
y el complejo de cada una por `GET /api/complejos/{id}` (nombre y localidad, sin el estado de
migración ni el informe de R01, que pasan al resumen). Sin esta acción, el patrón de hoy (cargar →
`alcanza` → 200) le daba a un vecino el padrón entero con los coeficientes de todos.

Alternativas descartadas para la lectura (B5): el padrón público dentro del edificio (lo conocen los
copropietarios, pero contradice "sus unidades" de la spec vigente y la decisión de Juani); filtrar las
listas por rol (el vecino ve sólo sus filas): duplica lo que ya hace `GET /api/unidades/{id}` y deja
una lista cuyo contenido depende de quién pregunta, más difícil de probar.

**Auditoría**: las tres acciones de titular se auditan con `@accion_sensible`, en la misma
transacción. Unidades, grupos y categorías no se auditan: se pueden deshacer y todavía no mueven
plata. Cuando el 7 emita, la liquidación guarda la foto de lo que usó (R01, R16). Alternativa
descartada: auditar todo (ruido que entrena a no leer la auditoría) o nada (la versión ya tiene autor,
pero crear un edificio y cerrar el importador son actos que el consejo puede querer ver). Queda
abierta PR1: los coeficientes tienen peso legal y lo que cambia un colaborador en el padrón no deja
rastro hasta que el 7 saque la foto.

**Dónde vive la forma del detalle** (nota N7): los modelos de detalle nuevos (`complejo_id`; para una
versión, `complejo_id` y `vigente_desde`, nunca la tasa ni el recargo) se suman a
`_MODELOS_DE_DETALLE` de `acceso/aplicacion/auditoria.py`, central como en el 2a. No es un ciclo
(`complejos → acceso`), pero `acceso` pasa a conocer la forma del detalle de acciones de `complejos`,
y después de 7, 8 y 10b. Alternativa descartada por ahora: un registro que llena cada módulo al
importarse; suma un mecanismo para tres modelos. Se revisa si el 7 suma más de un puñado.

**Aviso D-2 del 2a**: ninguna tabla nueva tiene FK hacia `auditoria`, así que la sonda de arranque no
frena. Un test lo verifica (el arranque real con las migraciones nuevas).

### D6 · Contrato de la API y de error

Rutas nuevas en `proptech_api/complejos.py` (o routers hermanos del mismo módulo), **siempre con el
prefijo en el router**, como hoy. Todas dependen de `identidad_actual` y `sesion_con_tenant`.

| Ruta | Acción |
|---|---|
| `GET /api/complejos` | lista del alcance (id, nombre, localidad; también para el vecino, D-076) |
| `POST /api/complejos` | `crear_edificio` (acepta la configuración inicial, E4) |
| `GET /api/complejos/{id}` | (existe) suma `localidad`; el alcance de hoy |
| `GET /api/complejos/{id}/resumen` | `ver_configuracion_del_edificio`: estado de migración e informe de R01 |
| `POST /api/complejos/{id}/estado-de-migracion/sin-saldos-previos` | `confirmar_sin_saldos_previos` |
| `GET /api/complejos/{id}/unidades` | `ver_configuracion_del_edificio` |
| `POST /api/complejos/{id}/unidades`; `PATCH /api/unidades/{id}` | `configurar_padron` |
| `GET /api/complejos/{id}/grupos` | `ver_configuracion_del_edificio` |
| `POST /api/complejos/{id}/grupos`; `PATCH /api/grupos/{id}`; `PUT /api/grupos/{id}/unidades` | `configurar_padron` |
| `GET /api/complejos/{id}/categorias` | `ver_configuracion_del_edificio` |
| `POST /api/complejos/{id}/categorias`; `PATCH /api/categorias/{id}`; `PUT /api/complejos/{id}/categorias/orden` | `configurar_padron` |
| `GET /api/complejos/{id}/configuracion?fecha=`; `GET /api/complejos/{id}/configuracion/versiones` | `ver_configuracion_del_edificio` |
| `POST /api/complejos/{id}/configuracion/versiones` | `crear_version_de_configuracion` |

`GET /api/unidades/{id}` del 2a cambia `nombre` por `identificador` en su respuesta (nota N9 d): es un
cambio de contrato, no sólo de tests, y nadie lo consume todavía (la web está vacía).

**Orden de los errores**: FastAPI valida el esquema del cuerpo después de las dependencias,
pero parsea JSON antes. `RutaConIdentidad` intercepta los errores de ese parser y resuelve sólo
la identidad con el solver de FastAPI antes de entregarlos (también el 400 de bytes inválidos).
En el camino que parsea bien, la resolución habitual se ejecuta una sola vez. Así se conserva
el orden **401** (sin identidad, sin tocar la base) → **422 del cuerpo** → **404** →
**403** → **409** o **422 semántico**. El 422 del cuerpo no filtra existencia (no depende de ningún
dato), pero ningún test espera un 403 con un cuerpo inválido. **404** `{"detail": "no encontrado"}`
idéntico para inexistente, fuera de alcance y de otra administración; **403** con
`permiso_faltante`; **409** `{"detail": "conflicto", "campo": ...}` para claves, identificadores,
nombres y vigencias repetidas, y transiciones de estado inválidas; **422** con la ruta del campo y el
motivo, **nunca el valor** (L-007): el manejador por defecto de FastAPI devuelve `input` en cada error
y se reemplaza para estas rutas. Montos y proporciones viajan como texto en los dos sentidos.

**Unidades de otro edificio en un grupo**: la aplicación las busca dentro del edificio del grupo, con la
sesión ya filtrada por RLS; si alguna no aparece, 422 con el campo `unidades` y sin decir cuál ni por
qué, así una unidad de otra administración y una de otro edificio dan la misma respuesta. La FK de
`grupo_unidad` es el segundo candado.

### D7 · Ids del servidor (R11, E8)

Los cuerpos de alta heredan de un modelo base con `extra="forbid"` y `strict=True`: `id`,
`administracion_id`, `complejo_id` o cualquier campo no declarado dan 422. Es más estricto que la
asignación del 2a (que acepta e ignora `administracion_id`); no se toca esa ruta acá, para no
mezclar cambios en el candado, y queda anotado como diferencia conocida. Los cuerpos de `PATCH` y
`PUT` usan el mismo modelo base y los cubren sus propios escenarios (mover una unidad por la API); el
barrido es de altas.

**El barrido** recorre todas las rutas `POST` (las mismas que encuentra el barrido de R6) y les manda
un cuerpo válido más un `id`, desde un diccionario de **cuerpos de prueba por ruta** (nota N8):

- una ruta `POST` sin cuerpo de prueba en el diccionario **hace fallar la suite** nombrándola; nunca
  se saltea (L-019: un barrido que saltea lo que no conoce nunca da rojo);
- el 422 tiene que **nombrar `id`** en la ruta del error, no cualquier campo: si no, un cuerpo de
  prueba mal armado pasaría por otro error del cuerpo;
- se excluyen, con el motivo escrito en el test, la asignación del 2a (ignora `administracion_id`, ver
  arriba) y `POST .../sin-saldos-previos` (no lleva cuerpo).

Alternativa descartada: ignorar el `id` (es lo que el cliente cree que pasó lo que hace peligroso un
silencio; con 422 el error se ve).

### D8 · R6: el barrido que no depende del prefijo

El barrido deja de leer el router original de cada `_IncludedRouter` y pasa a mirar la **ruta
efectiva**: el `path` con el que la app de verdad responde, armado por FastAPI con el prefijo de
inclusión incluido. Tiene que contemplar rutas directas de la app (`APIRoute` en `app.routes`) y
routers anidados. Para ver el rojo antes del arreglo: sobre una copia del test (L-013), una app de
prueba con un router sin prefijo montado con `include_router(prefix="/api")` y una ruta fuera de la
lista; el barrido de hoy pasa en verde (ese es el defecto) y el nuevo falla nombrándola. La lista de
hoy (tres rutas del 2a más `/api/salud`) tiene que salir idéntica (L-020).

Si la versión fijada de FastAPI no expone la ruta efectiva sin atributos internos, se arma recorriendo
`app.routes` y concatenando prefijos, con un test que falla si FastAPI cambia esa estructura (mismo
criterio que F3b del 1c).

El barrido no filtra por `/api`: la lista pública es explícita (salud, OpenAPI y documentación
de la raíz). Recorre subapps `Mount` con sus prefijos, HTTP y WebSocket; una ruta HEAD sin GET
es independiente. Un montaje opaco o un tipo desconocido falla nombrando su ubicación efectiva.
HEAD sólo se omite cuando comparte objeto y dependencias con GET.

### D9 · El edificio de ejemplo en la base (E6, E10)

Un comando (`python -m proptech_core.complejos.aplicacion.ejemplo cargar`) que lee la semilla con el
validador del 1b, abre una sesión con el tenant de la **administración de ejemplo** (id fijo en el
código) y, en una sola transacción, crea la administración, su titular de ejemplo (nombre inventado,
sin email), el edificio y lo demás con ids fijos derivados (`uuid5` sobre un espacio de nombres propio
y el identificador de cada cosa), **llamando a los mismos casos de uso que la API** (E10).

**Idempotencia, sólo sobre lo que sale de la semilla** (nota N5, D-042): si la administración de
ejemplo existe, compara las unidades (identificador, tipo, piso, coeficiente, superficie), los grupos
(clave, método, modo, miembros y coeficientes propios) y el estado de migración. **No compara** la
configuración versionada ni las categorías, que vienen de `parametros.yaml`: si se compararan,
cambiar el archivo haría que `cargar` saliera con 1 para siempre en toda base con el ejemplo, que es
justo lo contrario de D-042 (los edificios existentes no cambian). Igual: código 0 y "ya estaba";
distinto: código 1 con lo que difiere y sin escribir. Dos corridas en paralelo: la segunda choca con
la clave primaria de la administración y reintenta la comparación.

**Con qué credencial** (nota N5): corre como `proptech_migrador` (sin `BYPASSRLS`, E1 del 2a: fija el
tenant a propósito). Es un **consumidor nuevo** de esa credencial, y se suma a la tabla de
consumidores del migrador en `08` al archivar. Alternativa descartada: correrlo como la app, que
también podría (tiene `INSERT` sobre `administracion` y la política por `id` frena lo demás); se
descarta porque crear una administración no es un camino de la app, y dejarlo en la credencial de la
app lo convertiría en uno que cualquier bug del servidor podría tomar. Es una política, no un límite
técnico, y así queda escrito.

**Auditoría** (E10): como usa los casos de uso, audita `crear_edificio` y
`confirmar_sin_saldos_previos` con el titular de ejemplo como persona y un `request_id` propio del
comando (`ejemplo-cargar-` seguido de un UUID nuevo por corrida). Consecuencia, escrita en el Migration
Plan: una base con el ejemplo cargado ya no baja con `downgrade`.

No se corre al arrancar ni en el humo de producción. "No se corre en el piloto" hoy no lo frena nada
técnico: el comando está en la imagen (PR4). Alternativas descartadas: cargarlo en una migración
(quedaría en toda base, incluida la del piloto); cargarlo en la administración del primer usuario
(mezcla datos inventados con datos reales).

### D10 · Fronteras y quién lee los parámetros (B1)

Dirección: `complejos → acceso → compartido`, y `complejos → compartido`. `compartido` **no importa
ningún módulo de dominio**.

- **R01 vive en `compartido`**: la función pura de la suma, la diferencia y el estado con la tolerancia
  (`compartido/coeficientes.py`) y el tipo `Coeficiente` (texto decimal ASCII, hasta 6 decimales,
  `fullmatch`, al lado de `Porcentaje` y `Superficie`). La usan `complejos.dominio` (el informe de la
  API) y `compartido/semilla.py` (el validador). Es lo que hace cumplir L-009 de verdad (el gemelo es
  la misma función) **sin** la arista `compartido → complejos` que la tarea 7.1 original creaba: con
  la semilla en `compartido` y el dominio en `complejos`, "usar el mismo dominio" cerraba el ciclo
  `compartido → complejos → acceso → compartido`.
- **El test de fronteras** suma `compartido ↛ complejos` y, en general, que `compartido` no importe
  ningún módulo de dominio (`acceso`, `complejos` ni los que vengan). Hoy sólo prueba `compartido ↛
  acceso` y `acceso ↛ complejos`, así que el ciclo entraba en verde. El rojo se ve sobre una copia con
  un import de `complejos` agregado a `compartido` (L-013).
- Alternativas descartadas: mudar la semilla a `complejos` (toca el comando del 1b y su spec, y la
  semilla también describe parámetros); pasarle al validador de la semilla la función por argumento
  (una indirección que nadie más necesita).
- `complejos.dominio` suma lo propio del edificio: versiones, modos de grupo y su coherencia.
- `acceso` sigue sin importar `complejos` (lo verifica `test_fronteras_de_modulos.py`).
- Los parámetros los lee `crear_app()` al arrancar (ya lo hace) y se guardan en `app.state`; el caso
  de uso de alta los recibe como argumento, nunca los relee del disco. Consecuencia: editar
  `parametros.yaml` sin reiniciar no cambia lo que copian los edificios nuevos (es lo que D-042 quiere
  para los existentes; para los nuevos, se reinicia).

### D11 · Cómo se entra a las pantallas sin login, en desarrollo (E2, se construye en el 3b)

El problema: `identidad_actual` da 401 siempre en producción (spec `autorizacion-por-rol` › Sin
identidad no hay acceso ni consultas) y las pantallas del 3b se tienen que poder ver en el navegador
antes del 2b, sin abrir un hueco en el candado ni dejar rastro en producción.

**Propuesta**: un punto de entrada de desarrollo, `backend/desarrollo/app_de_desarrollo.py`, **fuera de
`backend/src/`**, que no se instala con el paquete y no entra en la imagen de producción (el
`Dockerfile` copia sólo `src`, `migraciones` y `alembic.ini`). Llama a `crear_app()` y hace exactamente
lo que ya hacen los tests: `app.dependency_overrides[identidad_actual]` con la identidad del titular de
la administración de ejemplo (D9). Lo levanta sólo `infra/compose.desarrollo.yaml`, un archivo aparte
que se suma con `-f`, que monta `backend/desarrollo` y publica la API en `127.0.0.1`. **Nunca se puede
llamar `compose.override.yaml`**: Compose lo carga solo. La web no cambia: llama a la API desde el
servidor de Next igual que en producción; en desarrollo la API ya trae la identidad, y en el 2b la web
empieza a mandar el token de la sesión.

**El riesgo que queda, escrito** (nota N4): `humo.sh` usa `docker compose -p proptech` sin `-f`, y
Compose lee `COMPOSE_FILE` de `infra/.env`. Si alguien pone ahí
`COMPOSE_FILE=compose.yaml:compose.desarrollo.yaml`, el servidor levanta el override. La negativa a
arrancar "si la URL de la base no es local", que proponía la primera versión, **no distingue nada**:
bajo Compose el host es `db` en desarrollo y en el servidor; se saca. **La contención real es otra**:
la identidad está fija en el titular de la **administración de ejemplo**, y la RLS forzada no le deja
ver ni escribir ninguna otra administración. Eso depende de que la carga del ejemplo no se corra en el
piloto (PR4).

Garantías, cada una con su test en el 3b: la imagen de producción no contiene `desarrollo`; la app de
`proptech_api.app` sigue dando 401 sin identidad; `compose.yaml` no referencia nada de desarrollo;
**ningún archivo del repositorio pone `COMPOSE_FILE` con `desarrollo`** y `humo.sh` pasa `-f
compose.yaml` explícito (el chequeo barato de N4); el punto de entrada se niega a arrancar si la base
no tiene la administración de ejemplo. No abre un hueco en el candado del 2a: no toca
`identidad_actual` ni `src/`. El 2b lo borra con el archivo de Compose: no queda una sola línea en
`src/`.

| Alternativa | Riesgo | Por qué no |
|---|---|---|
| Variable de entorno (`PROPTECH_IDENTIDAD_DE_DESARROLLO`) leída por `identidad_actual` | **Alto**: el código que saltea la identidad viaja en la imagen de producción; una variable mal puesta abre todo | Un candado que depende de que nadie setee una variable no es un candado |
| Encabezado `X-Persona` que el servidor cree | **Crítico**: la identidad sale del cliente (contradice R10 y D-016) | Es exactamente lo que el 2a prohíbe |
| Datos falsos en la web (sin API) | Bajo para el candado; alto de deriva: las pantallas se prueban contra un contrato inventado | Los 422, 409 y el informe de R01 son justo lo que hay que ver |
| Esperar al 2b | Ninguno técnico | Frena el 3b detrás del 2b, que todavía no tiene propose |
| Un login "de mentira" en la web | Medio: código de sesión que el 2b tiene que reemplazar y que puede quedar | Deja rastro en la web, que es lo que se pidió evitar |

Costo de revertir: borrar un directorio y un archivo de Compose.

### D12 · El frontend del 3b (sin diseño de pantallas)

Las pantallas y flujos están en `proposal.md`. Lo que el 3b tiene que respetar y que este design
puede fijar sin hacer el `shape`:

- **La web no calcula**: muestra `suma`, `diferencia` y `estado` como los manda la API. Si la pantalla
  muestra coeficientes en porcentaje, la conversión es de presentación (multiplicar por 100 un texto
  decimal con aritmética decimal, nunca `Number`), y el `shape` decide si se muestra así.
- **La plata y las proporciones como texto** de punta a punta: la web nunca hace `parseFloat` de un
  coeficiente, una tasa o un porcentaje; formatea el texto (coma decimal, punto de miles).
- **Herramientas que el 3b va a necesitar y hoy no están**: una librería de tests de componentes,
  axe para accesibilidad y un navegador real para el ancho de 320 px y el teclado. Se eligen en el
  propose del 3b (criterio de costo de D-043), no acá.
- **Los tokens de `DESIGN.md` están sin resolver** ("to be resolved during implementation"): el 3b
  los fija y re-corre `impeccable document`.
- **Los `shape`**: una sesión de `impeccable shape` por pantalla, con `PRODUCT.md` y `DESIGN.md` como
  contexto, que deja un brief en `openspec/exploraciones/` con la acción principal, los estados
  (carga, vacío, error), cómo se muestran los coeficientes (fracción o porcentaje) y qué texto
  acompaña cada estado de plata, con el OK de Juani escrito con fecha. Es la precondición del propose
  del 3b.

### D13 · Deuda del 1b con dueño 3

`naming_convention` en la `MetaData` de SQLAlchemy (para que los nombres de constraints de las
migraciones nuevas sean deterministas; las del 2a ya los nombran a mano); `Porcentaje` y `Superficie`
en `compartido`, con el mismo patrón ASCII y `fullmatch` que `Dinero` (L-008), usados por la API, la
semilla y los parámetros (L-009); `Semilla.version: Literal[1]`; `pydantic` declarado en
`pyproject.toml` con el rango que ya resuelve `uv.lock`; la app con `--factory` (`app.py` deja de
crear la app al importarse) y el healthcheck de la web contra `127.0.0.1` en vez de `localhost`;
`.gitignore` ampliado; el test de `chmod` salteado en Windows. Lo de infraestructura va en la tarea
2.4, que choca con `main` en `app.py` (ver Context), no en Compose.

### D14 · Agregar acciones sin romper una base armada desde cero (nota N1)

`0004` hace `bulk_insert(... for accion in Accion)` con el enum **vivo**: en una base vacía, un
`upgrade` desde `base` inserta en 0004 las acciones que todavía no existían cuando se escribió, y el
`INSERT` de la migración de vocabulario del 3a choca con la clave primaria.

**Decisión**: se congela `0004` con la **lista literal** de las acciones del 2a, y la migración de
vocabulario del 3a inserta su lista literal, sin `ON CONFLICT`. Ninguna migración importa `Accion`.
Un test arma una base vacía, corre `upgrade head` y exige que `accion_de_auditoria` sea exactamente
`{a.value for a in Accion}`: falla si alguien suma un miembro a `Accion` sin su migración, o una
migración sin su miembro. Editar 0004 no cambia nada en una base existente (ya corrió y su resultado es
el mismo); sólo deja de depender del código de hoy. Cada cambio que sume acciones sigue el mismo
patrón.

Alternativa descartada: `ON CONFLICT DO NOTHING` en la migración nueva. Tapa la colisión en vez de
sacarla, y su `downgrade` borraría filas que en una base nueva insertó 0004.

### D15 · Dos modos de coeficientes por grupo (D-100, P24)

`grupo_de_reparto.modo_de_coeficientes` es `renormalizado` (por defecto: los coeficientes generales
divididos por la suma del grupo) o `propios` (cada miembro lleva su coeficiente y suman 1 dentro del
grupo, con la tolerancia de R01). La coherencia padre e hijo **no la puede hacer un `CHECK`**, y la
regla es de las que el Goal pide que frene la base. **Decisión**: repetir el modo en la tabla de
miembros con una FK compuesta, como recomienda el arquitecto, y no un trigger.

- `grupo_de_reparto`: `modo_de_coeficientes TEXT NOT NULL DEFAULT 'renormalizado' CHECK IN
  ('renormalizado', 'propios')`; `UNIQUE (administracion_id, complejo_id, id, modo_de_coeficientes)`;
  `CHECK (modo_de_coeficientes = 'renormalizado' OR metodo = 'coeficiente')` (un grupo por superficie
  o partes iguales no tiene coeficientes propios); `CHECK (NOT es_generales OR modo_de_coeficientes =
  'renormalizado')` ("Generales" usa los coeficientes de las unidades, que son los suyos).
- `grupo_unidad`: `modo_de_coeficientes TEXT NOT NULL`, `coeficiente NUMERIC(7,6) NULL`; la FK hacia
  el grupo pasa a ser `(administracion_id, complejo_id, grupo_id, modo_de_coeficientes) →
  grupo_de_reparto (administracion_id, complejo_id, id, modo_de_coeficientes)` con `ON UPDATE
  CASCADE`; `CHECK ((modo_de_coeficientes = 'propios') = (coeficiente IS NOT NULL))`; `CHECK
  (coeficiente IS NULL OR (coeficiente > 0 AND coeficiente <= 1))`.
- **Cambiar el modo de un grupo con miembros** reescribe los miembros: como el `CHECK` no es
  diferible, un `UPDATE` del modo en el grupo cascadea a los miembros y choca con su `CHECK` (la base
  lo frena, que es lo buscado). El caso de uso lo hace en una transacción: borra los miembros, cambia
  el modo y los vuelve a insertar con la forma nueva (`PUT /api/grupos/{id}/unidades` lleva el modo y,
  si es `propios`, el coeficiente de cada miembro).
- **El informe**: un grupo `propios` se informa como "Generales" (suma, diferencia y estado); el
  control de R34 del 7 los mira a todos.
- **La semilla**: el formato `grupos:` suma `modo` (opcional, por defecto `renormalizado`) y, si es
  `propios`, el coeficiente de cada miembro. Hoy Ascensor suma 0,80 de los generales: queda
  `renormalizado` y sigue válida sin tocar sus números.

Alternativas descartadas: un trigger que verifique el modo del padre en cada `INSERT` o `UPDATE` de un
miembro (hace lo mismo con código procedural que hay que probar aparte y que un `ALTER TABLE ...
DISABLE TRIGGER` del migrador apaga); sólo la aplicación (contradice el Goal). Con la FK compuesta, el
test es insertar de verdad un miembro con coeficiente en un grupo renormalizado y cambiar el modo por
SQL con miembros, como `proptech_app` (L-018).

### D16 · Tablas de sólo agregar en el paso de roles (B2)

El problema: el `GRANT SELECT, INSERT` de una migración **no sobrevive al primer `up`**. Los `ALTER
DEFAULT PRIVILEGES` del migrador le dan `UPDATE, DELETE` a la app en toda tabla nueva, y en cada
`antes()` `_otorgar_permisos_explicitos_a_la_app` re-otorga los cuatro permisos a toda tabla de
`public` salvo las excluidas. Además el guardián del 2a **exige** los cuatro permisos a toda tabla con
`administracion_id`, así que la tabla con `SELECT, INSERT` lo haría fallar. Es el mismo defecto que el
2a pagó con `auditoria` (L-018: el `GRANT` "documenta la intención, pero no basta", `ayudas_rls.py`).

**Decisión** (opción a): generalizar lo de `auditoria`.

- `roles.py` suma una lista explícita `_TABLAS_DE_SOLO_AGREGAR` (hoy, `configuracion_versionada`).
  `antes()` las saltea en `_otorgar_permisos_explicitos_a_la_app`, igual que a `auditoria`, y
  `despues()` corre `REVOKE UPDATE, DELETE, TRUNCATE` y `GRANT SELECT, INSERT` a la app sobre cada una
  (el `REVOKE` deshace lo que regalaron los `DEFAULT PRIVILEGES`).
- **El guardián del 2a se ajusta**: acepta una tabla de esa lista **sólo** con exactamente `SELECT,
  INSERT` para la app (ni más ni menos), y **sólo** si además el trigger rechaza de verdad (caja negra:
  un `UPDATE` como app sobre una fila de prueba falla con el error del trigger, L-018). Una tabla con
  `administracion_id` que no está en la lista sigue necesitando los cuatro permisos: la excepción no
  puede volverse una puerta para cualquier tabla (L-020).
- **El test corre dos `up`** (`roles antes`, migraciones, `roles despues`, dos veces seguidas) y
  después, sobre una copia (L-013), deshabilita el trigger y prueba `UPDATE` y `DELETE` como app: los
  dos dan "permission denied". Así se ve la capa de permisos sola. El rojo se ve antes del arreglo: con
  el `roles.py` de hoy, el segundo `up` le devuelve `UPDATE` a la app.

Alternativas descartadas: asumir que la única capa es el trigger (E4 se firmaría describiendo dos
capas cuando hay una); dueño = rol de arranque (D3).

`roles.py` cambió en `main` (V3-14); la rama ya lo tiene desde el rebase del 16/10.

## Cómo aplica cada lección

Resumen en `proposal.md`. Detalle de las que cambian cómo se escribe una tarea:

- **L-016 y L-017**: todo test de aislamiento conecta como `proptech_app`, y "de otro edificio" u "otra
  administración" es siempre un UUID de una fila que existe.
- **L-018**: el "sólo agregar" de la configuración se prueba intentando `UPDATE`, `DELETE` y
  `TRUNCATE` de verdad, como app y como migrador, después de dos `up`, y la capa de permisos sola con
  el trigger deshabilitado sobre una copia; el trigger o el `GRANT` en el catálogo no alcanzan. Las FK
  compuestas y la coherencia del modo se prueban insertando.
- **L-019 y L-013**: R6, R11 y la frontera `compartido ↛ complejos` se ven fallar sobre una copia con
  lo que no deberían dejar pasar, antes del arreglo. El barrido de R11 falla si falta un cuerpo de
  prueba.
- **L-020**: cambiar el barrido de R6 no puede perder ninguna ruta de hoy (la lista se compara entera),
  y la excepción del guardián para las tablas de sólo agregar no puede aceptar cualquier tabla.
- **L-021**: la lista de "Que intente romper el rompedor" es un piso.

Escenarios que, por cómo están construidos, son guardas de regresión y no pueden dar rojo contra el
código de la línea de base de la forma que piden los demás (nota N11), con lo que se hace en cada uno:

- "Una unidad nueva entra a Generales": es cierto por construcción (`es_generales`). Se escribe igual,
  como guarda de regresión, y el rojo se ve sobre una copia donde "Generales" guarda miembros.
- "Dos pedidos simultáneos": por la API es candidato a test inestable. La garantía real es el `UNIQUE`
  de 3.6, que se prueba con dos transacciones concurrentes en la base; en la API se prueba de forma
  determinista que un `UniqueViolation` se traduce a 409 sin auditoría.
- "Volver atrás: no existe ruta": verifica la forma (la lista de rutas), no el efecto. Que la base
  frene una transición inválida aunque la app se equivoque es PR2.

## Risks / Trade-offs

- [D-100 sin contrastar con el reglamento del piloto] → si el piloto usa algo que ninguna variante
  cubre, hay migración. Mitigación: las variantes son columnas opcionales y modos con `CHECK`; sumar
  una tercera es aditivo.
- [El 2c y este cambio tocan `app.py` y `roles.py`] → conflicto al integrar. Mitigación: la rama se
  rebasó sobre `main` el 16/10; si `main` vuelve a tocarlos antes de 2.4 o de 3.5, se rebasa antes de
  esa tarea. P47 define cómo se integra.
- [Renombrar `unidad.nombre` a `identificador`] → los tests del 2a que insertan unidades con `nombre`
  se rompen y el contrato de `GET /api/unidades/{id}` cambia. Mitigación: la tarea 3.1 los actualiza en
  la misma pasada y la línea de base de 1.1 dice cuántos eran.
- [Zona horaria] → "hoy" en Mendoza depende de `tzdata` en la imagen. Mitigación: un test fija el
  reloj en las 23:30 y las 00:30 de Mendoza y verifica la fecha; si la imagen no tiene `tzdata`, el
  test falla en el CI, no en producción.
- [`puede` con `complejo_id=None`] → abrir el permiso sin alcance a otras acciones por error.
  Mitigación: sólo `crear_edificio` lo acepta, con un test por cada otra acción.
- [El migrador puede desactivar el trigger de la configuración] → aceptado en E4 (mismo nivel de
  confianza que E1 del 2a); si se rechaza, la tabla pasa al rol de arranque como `auditoria`.
- [La excepción del guardián] → una tabla agregada a `_TABLAS_DE_SOLO_AGREGAR` sin trigger. Mitigación:
  el guardián exige el trigger de verdad (caja negra), no su nombre.
- [El manejador de 422 reemplazado] → otra ruta que dependa del cuerpo por defecto. Mitigación: se
  aplica a todas las rutas de dominio y un test lo exige con un marcador en el valor (L-007).
- [`COMPOSE_FILE` en `infra/.env`] → el override de desarrollo en el servidor (D11). Mitigación: el
  test del 3b y la contención por RLS e identidad fija.

## Migration Plan

- Siete migraciones nuevas (`0005` en adelante) encadenadas desde `0004`, cada una con `downgrade` que
  vuelve a la forma anterior, más `0004` congelada con su lista literal (D14).
- La de la tarea 3.1 agrega columnas `NOT NULL` a `complejo` y `unidad`: hoy no hay datos reales; para
  las filas de tests se usan valores por defecto en la migración y se quitan los `DEFAULT` al final.
- **El `downgrade` vale sólo para una base sin auditoría nueva.** En cuanto existe una fila de
  auditoría con una acción del 3a (`crear_edificio`, `crear_version_de_configuracion` o
  `confirmar_sin_saldos_previos`), el `downgrade` de la migración de vocabulario no puede borrar esas
  acciones: `fk_auditoria_accion` no tiene `ON DELETE` (es `RESTRICT`) y `auditoria` rechaza `DELETE` y
  `TRUNCATE` para todo rol (D9 del 2a). Falla ruidoso y la base queda como estaba. Cargar el ejemplo
  ya deja esas filas (E10).
- **Desde el cambio 3, el rollback es restaurar un respaldo**, como avisaba el design del 2a ("desde el
  cambio 3, con edificios cargados, ya no: un rollback pasa a ser restaurar un backup, no un
  `downgrade`"). Rollback del código: volver al commit anterior **y restaurar el respaldo del 1d**
  tomado antes de subir. El `downgrade` queda para una base de desarrollo o de tests sin edificios
  creados.
- En la tarea 8.1 se ejercita: (1) sobre una copia **sin auditoría nueva** (las tablas del 2a con
  datos, sin edificios del 3a): `upgrade head`, `downgrade 0004`, `upgrade head`, con conteos iguales
  y `/api/salud` en 200; (2) sobre una copia **con el ejemplo cargado**: `downgrade 0004` falla en la
  migración de vocabulario, los conteos quedan iguales, y la restauración del respaldo del 1d devuelve
  la base al estado anterior a subir. Las dos con comandos y salida.
- Despliegue: no hay. Hasta el 2b, las rutas nuevas responden 401 en producción.

## Open Questions

P19, P24 y P33 se resolvieron en D-100 y están bajadas a D3 y D15. P16 y P47 siguen en
`proposal.md` con su decisor. Preguntas nuevas de la revisión del arquitecto, que este design no
decide porque son decisiones nuevas y no correcciones:

- **PR1 · ¿Se audita lo que cambia un colaborador en el padrón?** (nota N6 b) Los coeficientes tienen
  peso legal (reglamento) y E7 los deja sin rastro hasta que el 7 saque la foto; la mitad "lo revisa
  el titular" del principio de D-096 queda sin registro. Opciones: auditar `configurar_padron` sólo
  sobre coeficientes; auditarlo entero; dejarlo así. Decide: Juani o Alberto. No bloquea tareas: si se
  decide auditarlo, cambia 3.7 y 5.2.
- **PR2 · ¿Un trigger para las transiciones del estado de migración?** (nota N9 b) La app tiene
  `UPDATE` sobre `complejo`, así que volver de `sin_saldos_previos` a `pendiente` por SQL hoy lo frena
  sólo la API. Un trigger lo cerraría en la base, como pide el Goal. Costo: una tarea chica o crecer
  3.1. Decide: Juani.
- **PR3 · ¿Qué grupos parciales de `parametros.yaml` se crean con el edificio?** (nota N9 e) Ascensor,
  Cocheras y Servicios centrales tienen `alcance: a_elegir`. Opciones: crearlos vacíos con el
  edificio (modo `renormalizado`) o sólo "Generales" y que el administrador los arme. Y dónde queda el
  `habilitados: false` de R02 por edificio (hoy, `unidad.estado` nulo). La spec hoy dice sólo
  "Generales". Decide: Juani o Alberto.
- **PR4 · ¿Cómo se impide correr la carga del ejemplo en el piloto?** (nota N5 d) El comando está en la
  imagen y nada técnico lo frena; de eso depende la contención de E2. Opciones: que se niegue si la
  base tiene alguna administración que no sea la de ejemplo; sacarlo de la imagen (como el punto de
  entrada de E2); dejarlo escrito. Decide: Juani. Si la 7.2 pasa al 3b, se responde allá.
