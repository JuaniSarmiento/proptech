## Context

Ver `proposal.md` (Why y Partición). Lo que condiciona el cómo:

- **Lo que dejó el 2a** (`openspec/changes/archive/2026-10-15-aislamiento-por-administracion/`):
  `complejo` (`id`, `administracion_id`, `nombre`, `UNIQUE (administracion_id, id)`) y `unidad`
  (`id`, `administracion_id`, `complejo_id`, `nombre`, FK compuesta hacia `complejo` y
  `UNIQUE (administracion_id, complejo_id, id)`), ambas con RLS forzada por
  `migraciones/ayudas_rls.py::aislar_por_administracion`; el migrador sin `BYPASSRLS` (E1 del 2a); la
  identidad inyectable (`proptech_api/acceso.py`, 401 en producción); `alcanza` y `puede`
  (`acceso/dominio/permisos.py`); la auditoría de `acceso.aplicacion` con `@accion_sensible`; el
  guardián del catálogo, que ya falla si una tabla con `complejo_id` admite nulos o no tiene la FK
  compuesta (`aislamiento-por-administracion` › Una tabla nueva sin candado).
- **Lo que dejó el 1b**: `parametros.py` (menús y rangos: `Intereses`, `FondoDeReserva`,
  `GrupoDeReparto`, `CategoriaDeGasto`, tipos de unidad) y `semilla.py` (el edificio de ejemplo
  validado, con suma **exacta** de coeficientes y `version: int`). `crear_app()` ya lee los
  parámetros al arrancar y falla si son inválidos.
- **El barrido de rutas del 2a** (`tests/integracion/test_rutas_protegidas.py::_api_routes`) recorre
  sólo los `_IncludedRouter` y filtra `sub.path.startswith("/api")` sobre el router **original**: una
  ruta montada con `include_router(prefix="/api")` tiene un `path` sin `/api` en su router original y
  queda afuera **en silencio**; una agregada con `add_api_route` sobre la app, también. Esa es R6.
- **El 2c está en `main` en paralelo** y toca `infra/compose.yaml` y `humo.sh`; este cambio vive en la
  rama `propose-3-edificio` (P47 sin responder).
- **Frontend**: `web/` es Next 16 con una página vacía, sin Tailwind ni librería de tests de
  componentes. Todo lo de pantallas es del 3b (E1).

## Goals / Non-Goals

**Goals:**

- Que el modelo del edificio quede completo para el cambio 4, con la base frenando cualquier cruce de
  edificio o de administración aunque la aplicación se equivoque.
- Que la configuración que cambia plata sea de sólo agregar, con historia que nadie de la app pueda
  reescribir.
- Cerrar R6 antes de la primera ruta y dejar R11 como propiedad verificada de toda alta futura.
- Dejar firmada (E2) la forma de entrar a las pantallas sin login, aunque se construya en el 3b.

**Non-Goals:**

- Pantallas (3b), cálculos (4, 7), importación (5), motor de reglas (6b).
- Resolver P16, P19, P24 o P33: el design marca qué cambia con cada respuesta, no la elige.
- Bajas de edificios, unidades o grupos.

## Decisions

### D1 · Partición en 3a y 3b (E1)

Ver `proposal.md`. Alternativas descartadas: **un solo cambio** (unas 38 tareas, dos perfiles de
riesgo en la misma aprobación, y el 4 esperando pantallas que no necesita); **tres cambios** (modelo,
API, pantallas): la API sin su modelo no se revisa sola y el costo de cada vuelta de
constructor/rompedor/auditor se paga una vez más sin ganar nada. Revertir la partición cuesta poco:
el 3b se podría sumar como secciones nuevas de este `tasks.md` antes de construir.

### D2 · Modelo de tablas

Todas con `administracion_id NOT NULL`, RLS forzada con `aislar_por_administracion`, y toda tabla que
cuelga de un edificio con `complejo_id NOT NULL` y FK compuesta (convención del 2a, que el guardián ya
exige). Tipos de plata y proporciones en `NUMERIC`, nunca `float`; en Python, `Decimal` construido
desde texto.

| Tabla | Qué suma | Restricciones |
|---|---|---|
| `complejo` (tarea 3.1) | `localidad TEXT NOT NULL`, `estado_migracion TEXT NOT NULL DEFAULT 'pendiente'` | `CHECK` de los tres estados |
| `unidad` (tarea 3.1) | `identificador`, `tipo`, `piso`, `coeficiente NUMERIC(7,6)`, `superficie_m2 NUMERIC(10,2)`, `estado TEXT NULL` (R02, desactivado) | `UNIQUE (administracion_id, complejo_id, identificador)`; `CHECK coeficiente > 0 AND coeficiente <= 1`; `CHECK superficie_m2 > 0`; `CHECK tipo IN` los cuatro de D-029. `nombre` del 2a pasa a ser `identificador` (renombrado en la migración, con su `downgrade`) |
| `categoria_de_gasto` (tarea 3.3) | `clave`, `nombre`, `orden INT`, `activa BOOL` | `UNIQUE (administracion_id, complejo_id, clave)`; `UNIQUE (administracion_id, complejo_id, lower(nombre))` (índice único) ; `UNIQUE (administracion_id, complejo_id, orden) DEFERRABLE INITIALLY DEFERRED` para reordenar en una transacción |
| `grupo_de_reparto` (tarea 3.2, **P24**) | `clave`, `nombre`, `metodo`, `es_generales BOOL` | `UNIQUE (administracion_id, complejo_id, clave)`; `UNIQUE (administracion_id, complejo_id, id)`; un solo `es_generales` por edificio (índice único parcial) y `CHECK` de que "Generales" es por coeficiente |
| `grupo_unidad` (tarea 3.2, **P24**) | `grupo_id`, `unidad_id` | FK compuesta `(administracion_id, complejo_id, grupo_id)` → grupo y `(administracion_id, complejo_id, unidad_id)` → unidad: **la misma `complejo_id` en las dos FK es lo que hace imposible un miembro de otro edificio**; `UNIQUE (grupo_id, unidad_id)` |
| `configuracion_versionada` (tarea 3.4, **P19, P33**) | `vigente_desde DATE`, `tasa_mensual NUMERIC(4,2)`, `dias_de_gracia SMALLINT`, `forma_de_calculo TEXT`, `porcentaje_fondo NUMERIC(5,2)`, `autor_id`, `creada_en TIMESTAMPTZ` | `UNIQUE (administracion_id, complejo_id, vigente_desde)`; `CHECK` de rangos iguales a `parametros.py`; FK compuesta del autor a `persona`; trigger `BEFORE UPDATE OR DELETE` y `BEFORE TRUNCATE` que rechaza; la app sólo con `SELECT, INSERT` |
| `accion_de_auditoria` (tarea 3.5) | cuatro filas: `crear_edificio`, `crear_version_de_configuracion`, `confirmar_sin_saldos_previos` y `configurar_padron` (esta última es permiso y no se audita, pero el vocabulario es uno solo con `Accion`, como en el 2a) | el vocabulario cerrado del 2a |

"Generales" no guarda sus miembros en `grupo_unidad`: es "todas las unidades del edificio" por
definición (`es_generales`), así una unidad nueva entra sola y no hay forma de que una quede afuera.
Los grupos parciales guardan sus miembros; si P24 dice "coeficientes propios", `grupo_unidad` suma
`coeficiente NUMERIC(7,6)` y la validación de R01 se hace por grupo. Por eso la tarea 3.2 espera a P24.

Una migración por tarea, numerada desde `0005` en el orden en que se construyan (las bloqueadas por
P24, P19 o P33 pueden quedar para el final de la cadena; Alembic sólo exige que cada una apunte a la
anterior).

Alternativa descartada para `tipo`: una tabla de tipos por edificio copiada de los parámetros. D-029
fija los cuatro tipos; si algún día cambian, es una migración, igual que el vocabulario de auditoría.

### D3 · Versionado de la configuración (E4)

Una fila por versión con `vigente_desde`; **sin columna "hasta"**: la vigente para una fecha es la de
mayor `vigente_desde <= fecha`. Con eso la superposición no se puede escribir, y el `UNIQUE` por fecha
resuelve los pedidos simultáneos (uno gana, el otro recibe 409 al traducir `UniqueViolation`). La
primera versión nace con el edificio, vigente desde el día de alta. Una versión nueva exige
`vigente_desde >= hoy` en `America/Argentina/Mendoza`, calculado en el servidor.

- **Alternativa descartada**: rangos `daterange` con `EXCLUDE USING gist` (necesita la extensión
  `btree_gist`, que el rol de la app no puede crear y suma una pieza al rol de arranque) y una fila
  "hasta" que hay que actualizar al crear la siguiente, contradiciendo "sólo agregar".
- **Alternativa descartada**: permitir vigencias retroactivas. Cambiaría lo que debería haber cobrado
  una liquidación ya emitida; si hace falta corregir una tasa pasada, es una corrección (R08) del
  cambio 4 en adelante, no una edición de la configuración.
- **Sólo agregar**, igual que `auditoria` pero sin cambiarle el dueño: el migrador es dueño de la
  tabla (podría desactivar el trigger), la app sólo tiene `SELECT, INSERT`, y el trigger rechaza
  `UPDATE`, `DELETE` y `TRUNCATE` para cualquier rol. Es menos que la auditoría (que es del rol de
  arranque) a propósito: el migrador ya es de confianza equivalente al superusuario sobre sus tablas
  (E1 del 2a), y mover el dueño suma la complejidad de `roles.despues()` sin un riesgo nuevo que la
  justifique. Si Juani prefiere el mismo nivel que la auditoría, se dice al firmar E4.
- **Cómo la usa el 7**: cada liquidación referencia la versión con la que se calculó (historia de
  R03 y R15). El 3a deja la función `configuracion_vigente(complejo_id, fecha)`; qué fecha usa el 7
  (período, emisión o vencimiento) es P34 y es del 4 y el 7.
- **Qué cambia con P19 y P33**: si el piloto usa doble vencimiento, la versión suma el segundo
  vencimiento y el recargo; si el vencimiento es un día fijo del edificio, suma `dia_de_vencimiento`.
  Las dos son columnas nuevas; ninguna cambia las de R03.

### D4 · Cuándo se exige R01 (E5)

La suma de coeficientes se calcula en `complejos.dominio` con `Decimal` y se **informa** en cada
respuesta de unidades y grupos (`suma`, `diferencia`, `estado`), con los bordes de D-082 incluidos.
Cargar el padrón no se bloquea, porque una carga unidad por unidad pasa necesariamente por sumas
parciales que no dan 1. El que bloquea es el control antes de emitir del cambio 7 (R34), que lee el
mismo informe. Alternativa descartada: bloquear cada alta (impide cargar el padrón de a una unidad) o
exigir un "confirmar padrón" en el 3a (un estado más que nadie pidió y que el 5, al importar, tendría
que saltear).

### D5 · Permisos y auditoría (E3, E7)

`Accion` suma `crear_edificio`, `crear_version_de_configuracion`, `confirmar_sin_saldos_previos`
(titular) y `configurar_padron` (titular y colaborador "editar": unidades, grupos y categorías). La
matriz es la misma función pura de D-096; la spec del 2a (› La matriz completa) se extiende con las
filas nuevas. **Crear un edificio no tiene alcance todavía**: se evalúa sólo `puede` con
`complejo_id=None`, que hoy sólo cumple el titular (su asignación no tiene complejo). `puede` hoy
recibe un `UUID` obligatorio: se amplía para aceptar `None` sólo en esa acción, y un test exige que
cualquier otra acción con `None` se niegue.

Las tres acciones de titular se auditan con `@accion_sensible`, en la misma transacción. Unidades,
grupos y categorías no se auditan: se pueden deshacer y todavía no mueven plata. Cuando el 7 emita,
la liquidación guarda la foto de lo que usó (R01, R16). Alternativa descartada: auditar todo
(ruido que entrena a no leer la auditoría) o nada (la versión ya tiene autor, pero crear un edificio y
cerrar el importador son actos que el consejo puede querer ver).

**Aviso D-2 del 2a**: ninguna tabla nueva tiene FK hacia `auditoria`, así que la sonda de arranque no
frena. Un test lo verifica (el arranque real con las migraciones nuevas).

### D6 · Contrato de la API y de error

Rutas nuevas en `proptech_api/complejos.py` (o routers hermanos del mismo módulo), **siempre con el
prefijo en el router**, como hoy. Todas dependen de `identidad_actual` y `sesion_con_tenant`. El orden
del 2a se mantiene: cargar, 404 si no existe o no alcanza, 403 si no puede.

| Ruta | Acción |
|---|---|
| `GET /api/complejos` | lista del alcance |
| `POST /api/complejos` | `crear_edificio` |
| `GET /api/complejos/{id}` | (existe) suma localidad, estado de migración y el informe de R01 |
| `POST /api/complejos/{id}/estado-de-migracion/sin-saldos-previos` | `confirmar_sin_saldos_previos` |
| `GET, POST /api/complejos/{id}/unidades`; `PATCH /api/unidades/{id}` | `configurar_padron` |
| `GET, POST /api/complejos/{id}/grupos`; `PATCH /api/grupos/{id}`; `PUT /api/grupos/{id}/unidades` | `configurar_padron` |
| `GET, POST /api/complejos/{id}/categorias`; `PATCH /api/categorias/{id}`; `PUT /api/complejos/{id}/categorias/orden` | `configurar_padron` |
| `GET /api/complejos/{id}/configuracion?fecha=`; `GET, POST /api/complejos/{id}/configuracion/versiones` | `crear_version_de_configuracion` |

Errores: **401** sin identidad (sin tocar la base); **404** `{"detail": "no encontrado"}` idéntico para
inexistente, fuera de alcance y de otra administración; **403** con `permiso_faltante`; **409**
`{"detail": "conflicto", "campo": ...}` para claves, identificadores, nombres y vigencias repetidas, y
transiciones de estado inválidas; **422** con la ruta del campo y el motivo, **nunca el valor**
(L-007): el manejador por defecto de FastAPI devuelve `input` en cada error y se reemplaza para estas
rutas. Montos y proporciones viajan como texto en los dos sentidos.

**Unidades de otro edificio en un grupo**: la aplicación las busca dentro del edificio del grupo, con la
sesión ya filtrada por RLS; si alguna no aparece, 422 con el campo `unidades` y sin decir cuál ni por
qué, así una unidad de otra administración y una de otro edificio dan la misma respuesta. La FK de
`grupo_unidad` es el segundo candado.

### D7 · Ids del servidor (R11, E8)

Los cuerpos de alta heredan de un modelo base con `extra="forbid"` y `strict=True`: `id`,
`administracion_id`, `complejo_id` o cualquier campo no declarado dan 422. Es más estricto que la
asignación del 2a (que acepta e ignora `administracion_id`); no se toca esa ruta acá, para no
mezclar cambios en el candado, y queda anotado como diferencia conocida. Un barrido recorre todas las
rutas `POST` (las mismas que encuentra el barrido de R6) y les manda un cuerpo válido más un `id`:
toda ruta que no dé 422 hace fallar la suite. Alternativa descartada: ignorar el `id` (es lo que el
cliente cree que pasó lo que hace peligroso un silencio; con 422 el error se ve).

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

### D9 · El edificio de ejemplo en la base (E6)

Un comando (`python -m proptech_core.complejos.aplicacion.ejemplo cargar`) que lee la semilla con el
validador del 1b, abre una sesión con el tenant de la **administración de ejemplo** (id fijo en el
código) y, en una sola transacción, crea la administración, su titular de ejemplo (nombre inventado,
sin email), el edificio y lo demás con ids fijos derivados (`uuid5` sobre un espacio de nombres propio
y el identificador de cada cosa). Idempotencia: si la administración de ejemplo existe, compara lo
cargado con la semilla; igual, código 0 y "ya estaba"; distinto, código 1 con lo que difiere y sin
escribir. Dos corridas en paralelo: la segunda choca con la clave primaria de la administración y
reintenta la comparación. Corre como `proptech_migrador` (sin `BYPASSRLS`, E1 del 2a: fija el tenant a
propósito), porque crear una administración no es algo que haga la app.

No se corre al arrancar ni en el humo de producción. Alternativas descartadas: cargarlo en una
migración (quedaría en toda base, incluida la del piloto); cargarlo en la administración del primer
usuario (mezcla datos inventados con datos reales).

### D10 · Fronteras y quién lee los parámetros

`complejos` suma `dominio/` (coeficientes, versiones, puras y sin base) y casos de uso en
`aplicacion/`. Dirección intacta: `complejos → acceso → compartido`; `acceso` sigue sin importar
`complejos` (lo verifica `test_fronteras_de_modulos.py`). Los parámetros los lee `crear_app()` al
arrancar (ya lo hace) y se guardan en `app.state`; el caso de uso de alta los recibe como argumento,
nunca los relee del disco. Consecuencia: editar `parametros.yaml` sin reiniciar no cambia lo que
copian los edificios nuevos (es lo que D-042 quiere para los existentes; para los nuevos, se reinicia).

### D11 · Cómo se entra a las pantallas sin login, en desarrollo (E2, se construye en el 3b)

El problema: `identidad_actual` da 401 siempre en producción (spec `autorizacion-por-rol` › Sin
identidad no hay acceso ni consultas) y las pantallas del 3b se tienen que poder ver en el navegador
antes del 2b, sin abrir un hueco en el candado ni dejar rastro en producción.

**Propuesta**: un punto de entrada de desarrollo, `backend/desarrollo/app_de_desarrollo.py`, **fuera de
`backend/src/`**, que no se instala con el paquete y no entra en la imagen de producción. Llama a
`crear_app()` y hace exactamente lo que ya hacen los tests: `app.dependency_overrides[identidad_actual]`
con la identidad del titular de la administración de ejemplo (D9). Lo levanta sólo
`infra/compose.desarrollo.yaml`, un archivo aparte que se suma con `-f` y que monta `backend/desarrollo`
y publica la API en `127.0.0.1`. La web no cambia: llama a la API desde el servidor de Next igual que
en producción; en desarrollo la API ya trae la identidad, y en el 2b la web empieza a mandar el token
de la sesión.

Garantías, cada una con su test en el 3b: la imagen de producción no contiene `desarrollo`; la app de
`proptech_api.app` sigue dando 401 sin identidad; `compose.yaml` no referencia nada de desarrollo; el
punto de entrada se niega a arrancar si la base no tiene la administración de ejemplo o si la URL de la
base no es local. El 2b lo borra con el archivo de Compose: no queda una sola línea en `src/`.

| Alternativa | Riesgo | Por qué no |
|---|---|---|
| Variable de entorno (`PROPTECH_IDENTIDAD_DE_DESARROLLO`) leída por `identidad_actual` | **Alto**: el código que saltea la identidad viaja en la imagen de producción; una variable mal puesta abre todo | Un candado que depende de que nadie setee una variable no es un candado |
| Encabezado `X-Persona` que el servidor cree | **Crítico**: la identidad sale del cliente (contradice R10 y D-016) | Es exactamente lo que el 2a prohíbe |
| Datos falsos en la web (sin API) | Bajo para el candado; alto de deriva: las pantallas se prueban contra un contrato inventado | Los 422, 409 y el informe de R01 son justo lo que hay que ver |
| Esperar al 2b | Ninguno técnico | Frena el 3b detrás de P48, que no tiene fecha |
| Un login "de mentira" en la web | Medio: código de sesión que el 2b tiene que reemplazar y que puede quedar | Deja rastro en la web, que es lo que se pidió evitar |

Riesgo que queda con la propuesta: alguien corre `compose.desarrollo.yaml` en el servidor. Mitigación:
la negativa a arrancar fuera de una base local y sin la administración de ejemplo, y que la
administración de ejemplo no existe en la base del piloto (D9). Costo de revertir: borrar un
directorio y un archivo de Compose.

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

### D13 · Deuda del 1b con dueño 3

`naming_convention` en la `MetaData` de SQLAlchemy (para que los nombres de constraints de las
migraciones nuevas sean deterministas; las del 2a ya los nombran a mano); `Porcentaje` y `Superficie`
en `compartido`, con el mismo patrón ASCII y `fullmatch` que `Dinero` (L-008), usados por la API, la
semilla y los parámetros (L-009); `Semilla.version: Literal[1]`; `pydantic` declarado en
`pyproject.toml` con el rango que ya resuelve `uv.lock`; la app con `--factory` (`app.py` deja de
crear la app al importarse) y el healthcheck de la web contra `127.0.0.1` en vez de `localhost`;
`.gitignore` ampliado; el test de `chmod` salteado en Windows. Las dos de Compose van en la tarea 2.4,
**después de integrar el 2c**, que toca el mismo archivo.

## Cómo aplica cada lección

Resumen en `proposal.md`. Detalle de las que cambian cómo se escribe una tarea:

- **L-016 y L-017**: todo test de aislamiento conecta como `proptech_app`, y "de otro edificio" u "otra
  administración" es siempre un UUID de una fila que existe.
- **L-018**: el "sólo agregar" de la configuración se prueba intentando `UPDATE`, `DELETE` y
  `TRUNCATE` de verdad, como app y como migrador; el trigger en el catálogo no alcanza.
- **L-019 y L-013**: R6 y R11 son barridos; se ven fallar sobre una copia con la ruta que no deberían
  dejar pasar, antes del arreglo.
- **L-020**: cambiar el barrido de R6 no puede perder ninguna ruta de hoy: la lista resultante se
  compara entera.
- **L-021**: la lista de "Que intente romper el rompedor" es un piso.

## Risks / Trade-offs

- [P24, P19 o P33 sin responder] → el 3a no se puede cerrar entero. Mitigación: el orden de
  `tasks.md` deja primero todo lo que no depende de ellas; el cambio no se archiva con tareas
  bloqueadas marcadas.
- [El 2c y este cambio tocan `compose.yaml`] → conflicto al integrar. Mitigación: lo de Compose va
  en una sola tarea (2.4), después de integrar el 2c; P47 define cómo se integra.
- [Renombrar `unidad.nombre` a `identificador`] → los tests del 2a que insertan unidades con `nombre`
  se rompen. Mitigación: la tarea 3.1 los actualiza en la misma pasada y la línea de base de 1.1 dice
  cuántos eran.
- [Zona horaria] → "hoy" en Mendoza depende de `tzdata` en la imagen. Mitigación: un test fija el
  reloj en las 23:30 y las 00:30 de Mendoza y verifica la fecha; si la imagen no tiene `tzdata`, el
  test falla en el CI, no en producción.
- [`puede` con `complejo_id=None`] → abrir el permiso sin alcance a otras acciones por error.
  Mitigación: sólo `crear_edificio` lo acepta, con un test por cada otra acción.
- [El migrador puede desactivar el trigger de la configuración] → aceptado en E4 (mismo nivel de
  confianza que E1 del 2a); si se rechaza, la tabla pasa al rol de arranque como `auditoria`.
- [El manejador de 422 reemplazado] → otra ruta que dependa del cuerpo por defecto. Mitigación: se
  aplica a todas las rutas de dominio y un test lo exige con un marcador en el valor (L-007).

## Migration Plan

- Cinco migraciones nuevas (`0005` en adelante) encadenadas desde `0004`, cada una con `downgrade` que vuelve a la forma anterior.
  En la tarea 9.1 se ejercita **sobre una copia con datos** (el edificio de ejemplo cargado):
  `upgrade head`, `downgrade 0004`, `upgrade head`, con conteos iguales y `/api/salud` en 200.
- La de la tarea 3.1 agrega columnas `NOT NULL` a `complejo` y `unidad`: hoy no hay datos reales; para las filas de
  tests se usan valores por defecto en la migración y se quitan los `DEFAULT` al final.
- Despliegue: no hay. Hasta el 2b, las rutas nuevas responden 401 en producción.
- Rollback del código: volver al commit anterior y `alembic downgrade 0004`.

## Open Questions

Ninguna que este design pueda diferir: P16, P19, P24, P33 y P47 cambian tablas o tareas y están en
`proposal.md` con su decisor. Ninguna se da por resuelta acá.
