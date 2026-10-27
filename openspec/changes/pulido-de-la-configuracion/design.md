## Context

Ver `proposal.md` ("Why") para la motivación y
`openspec/exploraciones/2026-10-26-pulido-de-la-configuracion.md` para cada hallazgo con su archivo y
línea. Lo que importa acá es el estado actual que condiciona el cómo:

- **`complejo`** tiene `nombre` y `localidad`, los dos `TEXT NOT NULL`
  (`backend/migraciones/versions/0005_edificio_y_unidad.py:24-25`). `localidad` quedó **afuera** del
  `CHECK` de texto no vacío a propósito (`0016_textos_no_vacios.py:19-35`); la API la exige de 1 a 200
  caracteres (`proptech_api/complejos.py:113-120`, `CuerpoEdificio`). **No hay `PATCH /complejos/{id}`**:
  la lista de rutas del módulo sólo tiene el `POST` (`proptech_api/complejos.py:236` y alrededores).
- **`unidad.piso`** es `TEXT NOT NULL` sin largo máximo (`0005:39`) y el único control es "sin
  caracteres de control" (`complejos/aplicacion/unidades.py:36`). La migración `0005` lo creó con
  `server_default=""`, así que puede haber filas con el piso vacío.
- **El 4a ya está mergeado a `main`** (`583f2f7`, archivado en `4d5f61d`): ocupa las migraciones `0021`
  y `0022`, hizo que `editar_unidad` audite (recibe `identidad` y `request_id`) en el mismo
  `complejos/aplicacion/unidades.py` que este change toca, y pasó `configuracion_versionada` al rol de
  arranque.
- **Los grupos no tienen columna de estado**; las categorías sí (`activa`, usada en
  `complejos/aplicacion/categorias.py`). "Generales" está protegido contra `DELETE` y contra cambios de
  método, modo y alcance por el trigger de `0011_proteger_generales.py`.
- **La clave** de grupos y categorías valida `^[a-z][a-z0-9_]{0,39}$` con coincidencia completa y sólo
  ASCII, en dos lugares: `complejos/aplicacion/grupos.py:38` y `compartido/parametros.py:37`.
- **El cliente de la API de la web** ya distingue las cinco respuestas (`web/src/lib/api/cliente.ts`:
  401, 404, 403, 409 en `:137-141`, 422 en `:142-159`), pero la acción de intereses y vencimiento no
  tiene rama `conflicto` (`configuracion/acciones.ts:80-98`): todo 409 cae en el genérico.
- **La CSP del 2b es estricta con nonce** y Caddy no publica `/api/*` salvo `/api/salud`: cualquier
  dato que la web necesite tiene que pasar por su servidor, no por un origen nuevo.

## Goals / Non-Goals

**Goals:**

- Que el formato esperado de cada campo esté escrito **antes** del error, y que cada error caiga en su
  campo (specs `pantallas-del-edificio`).
- Que la ubicación y el piso salgan de listas cerradas y que **el servidor** sea la autoridad, contra un
  archivo del repositorio (specs `ubicacion-del-edificio` y `edificios-y-unidades`).
- Migrar lo ya cargado sin inventar ningún valor y con la bajada probada.
- No tocar el dominio `acceso` ni la matriz de permisos: así el change se queda en HIGH.

**Non-Goals de diseño:**

- No se construye un combobox con búsqueda a medida: alcanza con `<select>` nativos (ver D1).
- No se unifica el diccionario de mensajes de error de la web con el vocabulario de Pydantic más allá
  de lo que piden los specs.
- No se toca `configuracion_versionada` (desde el 4a es del rol de arranque: un `ALTER` fallaría con
  `must be owner`), ni la cuenta corriente, ni nada de montos.

## Decisions

### D1 · El dato de Georef vive en el repo, reducido, y se lee en memoria al arrancar

**Qué**: `config/georef/provincias.json`, `departamentos.json` y `localidades.json`, cada registro con
`id`, `nombre` y el id del padre, más `config/georef/LEEME.md` con fuente, fecha de descarga, licencia
(CC BY 4.0, atribución a Georef / datos.gob.ar) y el comando `curl` exacto que lo regenera. Un lector en
`compartido/` los carga una vez al arrancar, los valida (estructura, ids únicos, padres existentes) y
expone tres consultas: provincias, departamentos de una provincia, localidades de un departamento, más
`existe_el_trio(provincia, departamento, localidad)`. La API expone tres rutas de lectura con sesión; la
web las consume desde su servidor, sin abrir un origen nuevo en la CSP. Calle y número es texto libre
(E2) y no hay país (E1).

**Por qué**: la app no depende de un servicio externo para crear un edificio, la CSP del 2b no cambia,
los tests son deterministas y el archivo tiene fecha y licencia auditables. Tamaños medidos el
26/10/2026: reducidos, provincias < 2 KB, departamentos ~20 KB, localidades ~257 KB — se cargan en
memoria sin problema.

**Alternativas descartadas**: consultar `apis.datos.gob.ar` en vivo (dependencia externa en el camino
de alta, un origen más en la CSP, tests no deterministas); guardar las listas en tablas de PostgreSQL
(una migración de 4.000 filas y un dato de referencia que no es del tenant, con RLS de más); validar
también las calles contra Georef (el dataset es mucho más grande; E2 lo descarta).

**Costo de revertir**: bajo. El archivo y el lector se borran; las columnas quedan (ver D2).

### D2 · La ubicación son tres ids nullable con un `CHECK` de "los tres o ninguno", y `localidad` pasa a derivada

**Qué**: `complejo` suma `provincia_id`, `departamento_id`, `localidad_id` (`TEXT`, nullable) y
`calle_y_numero` (`TEXT`, nullable, sin `CHECK` de largo en la base). Un `CHECK` exige que los tres ids
sean nulos o los tres no nulos: la base no puede guardar una ubicación a medias.

**Precisión H-8 (revisión del propose)**: el recorte de bordes y el máximo de 200 caracteres de
`calle_y_numero` viven **sólo en la aplicación** (API), igual que el 1 a 200 de `localidad` hoy — no en
un `CHECK` de la base ni en el trigger `fn_recortar_texto_3a` de `0013` (que sólo recorta `nombre` y
`localidad`, y no se extiende a esta columna nueva). Es la misma elección que ya existe para
`localidad`, no una inconsistencia nueva. La coherencia del trío (que la localidad sea de
ese departamento) la valida la **aplicación** contra el archivo de D1, no la base: meter 4.000 filas de
referencia en PostgreSQL sólo para una FK no se justifica, y la spec lo exige "aunque el pedido venga
armado a mano", que es la capa de la API. `complejo.localidad` **se queda** pero pasa a **nullable y
derivada**: cada vez que se escribe la ubicación, la aplicación copia ahí el nombre de la localidad de
Georef. Así "Mis edificios" y el resumen siguen andando sin resolver ids, y nunca hay dos fuentes en
desacuerdo porque sólo hay un camino de escritura. La API deja de aceptar `localidad` como entrada.

**Alternativas descartadas**: borrar `localidad` en esta migración (rompería la web, el humo y los
fixtures en el mismo paso que agrega las columnas, contra L-023; queda para un change futuro, anotado
como deuda); dejar `localidad` como texto editable en paralelo (dos fuentes de verdad, el problema que
este change viene a cerrar); columnas `NOT NULL` desde ya (imposible con E3: los edificios existentes
no tienen ubicación).

**Costo de revertir**: medio. La bajada borra las cuatro columnas y devuelve `localidad` a `NOT NULL`
con el texto que tenga; un edificio creado después de la migración perdería la ubicación, por eso el
punto de no retorno está escrito en el Migration Plan.

### D3 · El vocabulario de pisos: `PB`, `SS1..SS5`, `1..60`, con `complejo.pisos`/`subsuelos` y `unidad.piso` nullable

**Qué**: `complejo` suma `pisos` (entero, nullable, 1 a 60) y `subsuelos` (entero, nullable, 0 a 5). Las
dos quedan **nullable**, no `NOT NULL` calculadas de las unidades existentes (ver la corrección DBA-1
más abajo): un edificio sin esos datos todavía es "sin completar", exactamente el mismo tratamiento que
D2 ya da a la ubicación — la puesta a punto lo pide, nadie lo adivina. El vocabulario de un edificio con
`pisos`/`subsuelos` ya completos es, exactamente: `SS1` … `SS<subsuelos>`, `PB`, y `1` … `<pisos>`. `PB`
existe siempre (todo edificio tiene planta baja). Los cuatro tipos de unidad (D-029) eligen de la misma
lista: la semilla ya pone cocheras y baulera en el subsuelo, y no hay motivo de dominio para
restringirlo por tipo. `unidad.piso` pasa a **nullable** (nulo = "sin completar", el marcador de E5) y
gana un `CHECK` de forma, `^(SS[1-5]|PB|[1-9]|[1-5][0-9]|60)$` — el rango 1 a 60 escrito en el propio
patrón, no sólo en el texto de esta decisión — más la validación de aplicación contra el vocabulario
**de su edificio** (que la base sola no puede expresar sin un trigger con lectura cruzada). Bajar
`pisos` o `subsuelos` consulta las unidades que quedarían afuera y devuelve sus identificadores en el
422.

**Corrección DBA-1 (revisión del propose, 26/10/2026)**: la versión anterior de esta decisión hacía
`pisos`/`subsuelos` `NOT NULL`, calculados de las unidades existentes en la misma migración con un
`UPDATE` corrido por el migrador. El DBA encontró que `complejo` tiene RLS **forzada**
(`backend/migraciones/ayudas_rls.py:42-43`) y que `proptech_migrador` corre **sin `BYPASSRLS`**
(`0003_acceso_minimo.py:7-8`): ese `UPDATE` vería **cero filas, sin error**, y el `CHECK NOT NULL`
posterior fallaría sobre las filas reales que el `UPDATE` nunca tocó (el mismo defecto que el 4a ya
documentó como DB-3 en su propio design). La columna nullable + pantalla pide evita el problema de raíz:
no hay ningún `UPDATE` de backfill que necesite leer filas bajo RLS.

**Por qué esos máximos**: 5 subsuelos y 60 pisos son holgados para propiedad horizontal argentina
(Mendoza casi no tiene edificios de más de 30 pisos) y chicos como para que un `<select>` siga siendo
usable. Son números de un `CHECK` y de `parametros.yaml` si se quiere mover: cambiarlos es una
migración de una línea.

**Por qué nullable y no una columna `piso_a_revisar`**: el estado "sin completar" ya tiene dónde
mostrarse (la puesta a punto del edificio, que es el patrón del 3a para "falta algo") y una columna
booleana aparte podría desincronizarse del piso. Nulo es un estado, no un dato inventado — y E5 pide
exactamente eso: marcar, no adivinar.

**Alternativas descartadas**: `piso` como entero con convenciones (`0` = PB, negativos = subsuelos): más
compacto, pero obliga a traducir en cada capa y el `piso` ya viaja como texto en la API y en el Excel;
una tabla `piso` por edificio (tres joins para un dato que es un número y un rango); mantener `piso`
`NOT NULL` con un valor centinela como `"?"` (un dato inventado que puede llegar a una liquidación);
calcular `pisos`/`subsuelos` de las unidades existentes en la misma migración (DBA-1, descartada por el
problema de RLS).

**Costo de revertir**: medio-alto para los pisos, por la migración de datos (ver Migration Plan).

### D9 · El `UPDATE` de migración que toca `complejo`/`unidad` corre sin RLS forzada, con el candado puesto y sacado en la misma transacción

**Qué**: cualquier migración de este change que necesite transformar filas ya existentes de `complejo`
o `unidad` (la única es la de `unidad.piso` en `0024`, ver Migration Plan) sigue el patrón que ya existe
tres veces en el repo (`0012`, `0013`, `0017`, `0018`): `LOCK TABLE unidad IN ACCESS EXCLUSIVE MODE`,
`ALTER TABLE unidad NO FORCE ROW LEVEL SECURITY`, el `UPDATE`, y `ALTER TABLE unidad FORCE ROW LEVEL
SECURITY` antes del commit de la migración — nunca se deja la tabla sin `FORCE` fuera de esa transacción.

**Por qué**: `complejo` y `unidad` tienen RLS forzada y `proptech_migrador` no tiene `BYPASSRLS`
(evidencia del DBA, D3 arriba); sin este candado, cualquier `UPDATE` del migrador afecta cero filas sin
avisar. Es el mismo defecto que el 4a resolvió con DB-3, y la razón por la que D3 evita tener que hacer
esto para `complejo.pisos`/`subsuelos`: sólo queda este único `UPDATE`, el de `unidad.piso`, que sí
necesita tocar filas existentes porque es una transformación real de dato (`SS` → `SS1`), no un cálculo
que se pueda evitar.

**Alternativas descartadas**: hacer el `UPDATE` sin el candado (DBA-1, falla en silencio); migrar los
datos desde la aplicación en vez de desde Alembic (mueve el problema de RLS a otro lado sin resolverlo,
y pierde la propiedad de que la migración sea reproducible con `downgrade`/`upgrade`).

**Costo de revertir**: el mismo que `0024` (ver Migration Plan); este patrón no agrega costo propio, es
la forma correcta de pagar el costo que `0024` ya tenía.

### D4 · El grupo se desactiva con una columna `activo`, y el trigger de `0011` se amplía

**Qué**: `grupo_de_reparto` suma `activo BOOLEAN NOT NULL DEFAULT true` (igual que `categoria_de_gasto.activa`,
R16). `PATCH /grupos/{id}` acepta `activo`; no se agrega ninguna ruta de borrado. El trigger
`fn_grupo_generales_protegido` de `0011` suma `activo` a las columnas que protege para "Generales", así
que desactivarlo falla también por SQL. La desactivación queda auditada con el `editar_grupo` que el 4a
ya instaló. La puesta a punto y la lectura de grupos disponibles filtran por `activo`.

**La clave se autogenera** con una función pura en `compartido/` (minúsculas, NFKD sin tildes, lo que no
es `[a-z0-9]` → `_` colapsado y sin bordes, prefijo garantizado por letra, recorte a 40, desempate
`_2`, `_3`…). La usan **los dos** llamadores, grupos y categorías (L-009): se prueba en los dos, no en
uno. La API sigue aceptando `clave` explícita porque la semilla y `parametros.yaml` la traen, y el
importador del 5 la va a necesitar; lo que cambia es que el formulario deja de pedirla.

**Alternativas descartadas**: borrar el grupo de verdad (dejaría gastos huérfanos en el 6, contra R16 y
E6); un `estado` de texto con varios valores (no hay un tercer estado que nombrar); generar la clave en
la web (dos implementaciones del mismo slug, y la API seguiría aceptando cualquier cosa).

**Costo de revertir**: bajo. La columna se borra y el formulario vuelve a pedir la clave.

### D5 · Editar el edificio reusa `configurar_padron` y audita con un evento nuevo

**Qué**: `PATCH /complejos/{complejo_id}` con el patrón ya establecido del módulo:
`_edificio_autorizado(... Accion.CONFIGURAR_PADRON)` (404 fuera de alcance, 403 sin permiso, en ese
orden, D7 del 2a), cuerpo `CuerpoDeEdicion` (un campo puede faltar, ninguno puede ser `null`), y
auditoría con `EventoDelPadron.EDITAR_EDIFICIO`, que suma una fila al vocabulario de
`accion_de_auditoria` en una migración (el mismo mecanismo que el 4a usó en `0022`). El detalle guarda
el edificio y los **nombres** de los campos cambiados, nunca otros valores (D-016). Un pedido que no
cambia nada no deja registro, igual que el resto del padrón.

**Por qué reusar `configurar_padron` y no crear una acción nueva**: quien puede cambiar las unidades,
los grupos y las categorías de un edificio es exactamente quien tiene que poder corregir su localidad y
sus pisos; una acción nueva obligaría a tocar `_MATRIZ` en `acceso/dominio/permisos.py`, que es cambiar
D-106 y sube el change a CRITICAL (P68, E8). Con esta elección, `03_actores_y_roles.md` no cambia.

**Alternativas descartadas**: una acción `editar_edificio` propia en la matriz (CRITICAL, y D-106 no
distingue hoy "configurar el padrón" de "editar los datos del edificio"); reusar `CREAR_EDIFICIO` (sólo
super admin: un administrador no podría corregir su propio edificio).

**Costo de revertir**: bajo. La ruta se borra; el evento de auditoría queda en el vocabulario (la
tabla sólo se agrega).

### D6 · B-2 se reproduce antes de arreglarse, y si no se reproduce se cierra con la evidencia

**Qué**: la primera tarea de ese grupo es un test que manda a la **API real** un cuerpo con "rige desde"
repetido y día de vencimiento inválido a la vez, y afirma a qué campo llega cada error. Si el test
muestra el error en "tasa mensual", ahí está el bug y se arregla. Si sale verde, el hallazgo se cierra
como **no reproducible** con el comando, la salida y la hora pegados en el informe, y el test queda como
fijación. No se toca `cliente.ts:142-159` ni `mensajes.ts:46-61` a ciegas.

**Por qué**: la exploración marca B-2 como **hipótesis sin reproducir**. Arreglar un mapeo de errores
por conjetura es cambiar la ruta de todos los errores de la web por un caso que nadie vio dos veces
(L-017: la entrada del chequeo es la del escenario).

**Alternativas descartadas**: asumir que el `loc` no matchea y reescribir el mapeo; descartar el
hallazgo sin probarlo.

### D7 · El límite de cada campo lo dice la web desde su propia constante, con error explícito y asociado — no una burbuja nativa

**Qué**: el máximo del identificador, el rango del coeficiente y la regla de la clave se escriben como
constantes de la web, usadas a la vez en el texto de ayuda, en el mensaje de error **y en la validación
previa al envío**. El diccionario `mensajes.ts` no cambia de contrato: sigue traduciendo un `type` de
Pydantic a castellano, sin leer nada más de la respuesta de la API (L-007).

**Corrección F4 (revisión del propose, 26/10/2026)**: la versión anterior decía "usadas en el
`maxLength`/`pattern` del input" — eso apoya la validación previa al envío en atributos nativos del
HTML, que producen una burbuja del navegador **no asociada al campo** (sin `aria-describedby`, con texto
de la plataforma, no del diccionario de mensajes), justo lo que el criterio de frontend pide evitar. La
validación previa al envío usa el `error` explícito que `Campo`/`Formulario` ya aceptan
(`web/src/componentes/Formulario.tsx:140-150`, con precedente real en saldos-previos): el `onSubmit` de
`Formulario` corre la constante contra el valor **antes** de llamar a la server action y, si falla,
pone el mismo `error` que pondría el 422 — mismo mensaje, mismo campo, mismo `aria-describedby`,
corra donde corra la validación. `maxLength`/`pattern` pueden seguir puestos como ayuda adicional del
navegador (autocompletado, teclado numérico), pero nunca son el único mecanismo que informa el error.

**Por qué**: pasar el límite desde el `ctx` de Pydantic sería ampliar lo que la web lee de la API justo
donde L-007 pide lo contrario. El costo es que las constantes se pueden desincronizar del backend: se
cubre con un test que compara el máximo de la web contra el del contrato de la API (el esquema OpenAPI
que la web ya consume para sus tipos).

**Alternativas descartadas**: leer `ctx.max_length` del 422; dejar el mensaje genérico y poner el máximo
sólo en la ayuda (el QA se topó justamente con el mensaje, no con la ayuda); apoyarse sólo en
`maxLength`/`pattern` nativos (F4, descartada por la burbuja no asociada).

**Generalización (L-047)**: esta regla no es específica de estos tres campos. La tarea 5.6 la escribe
como convención en `knowledge-base/08_arquitectura_propuesta.md` §"La web" para que cualquier campo
nuevo, en esta pantalla o en otra, la siga sin que haga falta que un QA la vuelva a encontrar rota.

### D8 · Las listas encadenadas son tres `<select>` nativos, con el encadenado en el servidor de Next, cableados con el mismo contrato que `Campo`

**Qué**: tres `<select>` nativos, más el de piso (D3) — cuatro en total. Cambiar la provincia recarga
los departamentos y **vacía** el departamento y la localidad, para que no quede un trío incoherente en
la pantalla. La carga de cada lista pasa por el servidor de Next (que ya guarda el token, D-036), no por
una llamada del navegador a la API.

**Corrección F1 (revisión del propose, 26/10/2026)**: `Campo` hoy sólo sabe renderizar `<input>`
(`Formulario.tsx:156-161`); de los 9 `<select>` que ya existen en pantallas reales, 8 están sin `id`,
`aria-invalid` ni `aria-describedby`. Este change agrega `Campo` con `as="select"` (o un
`CampoDeLista` que reusa `idDelCampo` y el resto del contrato de `Campo`), para que los cuatro
`<select>` nuevos asocien su error programáticamente igual que cualquier `<input>` — en vez de repetir
el patrón mayoritario que ya está roto.

**Corrección F2**: el `<select>` de piso **siempre** tiene una opción vacía ("Elegí un piso", sin
`value`, deshabilitada si el navegador la deja seleccionar) cuando `unidad.piso` es `NULL` (la unidad
migrada sin completar, D3). Un `<select>` no controlado sin esa opción selecciona la primera de la
lista al abrir el panel y guardaría ese valor sin que nadie lo haya elegido — exactamente el dato
inventado que E5 prohíbe. Lo mismo aplica a provincia/departamento/localidad cuando la ubicación del
edificio es nula (E3): arrancan en la opción vacía, nunca en la primera real.

**Corrección F3**: cada lista encadenada tiene su propio estado `cargando`/`error` (no existe hoy
precedente de fetch-on-interaction en la web; los `loading.tsx` actuales son de ruta, no de un `onChange`
dentro de un panel ya abierto). Mientras una lista carga, queda deshabilitada con el componente
`Estados tipo="cargando"` visible junto a ella; si la carga falla, `Estados tipo="error"` con un botón
para reintentar, sin perder lo que ya se eligió en las listas anteriores de la cadena.

**Corrección F5**: `tokens.css` suma `.campo select[aria-invalid="true"]` con la misma regla que ya
tiene `.campo input[aria-invalid="true"]` — hoy el estilo de inválido sólo existe para `input`.

**Por qué nativo**: 135 departamentos en el peor caso (Buenos Aires) y 206 localidades en Mendoza son
manejables en un `<select>`; un combobox a medida es foco, teclado y lector de pantalla propios, el tipo
de cosa que L-028 dice que falla al combinarse con el panel lateral. Si el recorrido manual muestra que
una lista es inusable, el combobox accesible queda como deuda del cierre, no como alcance.

**Alternativas descartadas**: un combobox con búsqueda desde el arranque (más superficie de
accesibilidad sin evidencia de que haga falta); mandar las tres listas completas a la pantalla (1,45 MB
sin reducir, y la reducción igual son ~257 KB en cada carga); dejar el cableado de `Campo` como está y
que cada pantalla arme su propio `<select>` suelto (F1, descartada por repetir el patrón ya roto).

### D10 · La confirmación de "Quitar" en Personal (G-4) usa el diálogo de `PanelLateral`, no el patrón inline de saldos-previos

**Qué**: la tarea 6.4 cablea la confirmación con `PanelLateral` (`role="dialog"`,
`useCerrarConEscape`, trampa de foco, `devolverFocoA` — ya existe y se usa en otras pantallas,
`PanelLateral.tsx:25,31,45,54,57,85,111`), no copiando el patrón inline-con-casilla de
`saldos-previos/Pantalla.tsx`.

**Corrección F6**: el escenario de G-4 exige cancelar con `Esc` y que el foco vuelva al botón "Quitar"
(`specs/pantallas-del-edificio/spec.md`, escenario de confirmación). El patrón de saldos-previos es
inline con casilla y **no tiene `Esc`** — si la tarea 6.4 lo copiara sin más, el escenario no se podría
cumplir. `PanelLateral` ya resuelve `Esc` y devolución de foco, así que es el mecanismo correcto acá.

**Alternativas descartadas**: copiar el patrón de saldos-previos (F6, no tiene `Esc`); un `confirm()`
nativo del navegador (ya descartado por la exploración original de G-4, no es accesible ni consistente
con el resto de la web).

## Risks / Trade-offs

- **La migración de `unidad.piso` pierde información si el mapeo es flojo** → el mapeo sólo acepta
  valores exactos después de recortar (`PB`, `pb`, `SS`, `ss`, y enteros de 1 a 60); todo lo demás queda
  **nulo**, nunca convertido a la fuerza. La migración anota en su docstring qué mapea, y un test la
  corre contra una tabla sembrada con `PB`, `SS`, `""`, `"4"`, `"Entrepiso"`, `"1°"` y `" 2 "` y afirma
  el resultado de cada uno.
- **El `CHECK` nuevo rompe fuera de `backend/`** (L-023) → antes de cerrar cada migración, `rg` en el
  repo entero de `INSERT INTO complejo`, `INSERT INTO unidad` y `INSERT INTO grupo_de_reparto`,
  incluidos `infra/ci/humo.sh`, la semilla, los comandos y los fixtures de la web. El `rg` solo **ya
  falló una vez** en `0016` (un `server_default` no es texto buscable como un literal de seed): por eso
  las tareas 3.4 y 4.3 corren además `test_rls_edificio.py::test_downgrade_a_0004_y_upgrade_conservan_la_unidad_del_2a`,
  que atraviesa las migraciones nuevas con un complejo "viejo" de verdad.
- **Conflicto de merge con el 4a en `unidades.py`** → el 4a ya está en `main`: la rama se rebasa sobre
  `main` **antes** de la primera tarea, no al final.
- **El archivo de Georef envejece** (altas y bajas de localidades) → el `LEEME` fija la fecha y el
  comando; un edificio ya guardado conserva sus ids aunque el archivo se regenere. Si un id guardado
  desaparece de una versión nueva del archivo, la lectura muestra el id sin nombre en vez de fallar: la
  validación estricta corre al **escribir**, no al leer.
- **`localidad` derivada puede quedar vieja si alguien escribe la ubicación por SQL** → la única forma
  de escribir la ubicación es el camino de la aplicación (alta y edición); un test afirma que después de
  editar la ubicación, `localidad` coincide con el nombre de Georef.
- **Los máximos (5 subsuelos, 60 pisos) pueden ser chicos para un caso real** → son un `CHECK` y un
  rango de la API; subirlos es una migración de una línea, sin migrar datos.
- **El recorrido manual es la única evidencia de que las pantallas se ven bien** (L-026) → la tarea de
  verificación pide capturas a 1280 px y 320 px, el recorrido entero con teclado y, escrito paso por
  paso, cómo la cuenta de Clerk usada quedó vinculada a su persona (L-039): eso salda además la deuda
  del PR #1 del 3b-bis.

## Migration Plan

Tres migraciones, **a partir de `0023`** (el 4a ya ocupó `0021` y `0022` en `main`; nacer con
`down_revision` `0020` dejaría dos cabezas en Alembic). En este orden:

1. **`0023` · ubicación del edificio**: agrega `provincia_id`, `departamento_id`, `localidad_id`,
   `calle_y_numero` (nullable) y el `CHECK` "los tres o ninguno"; pasa `complejo.localidad` a nullable.
   Los edificios existentes quedan con la ubicación **nula** (E3), sin ningún `UPDATE` de backfill — no
   hace falta tocar filas existentes para agregar columnas nullable. **Bajada**: `LOCK TABLE complejo IN
   ACCESS EXCLUSIVE MODE`, `ALTER TABLE complejo NO FORCE ROW LEVEL SECURITY`, `UPDATE complejo SET
   localidad = '' WHERE localidad IS NULL` (D9 — `''` es un valor legal de esa columna desde `0005`,
   documentado en `0016_textos_no_vacios.py`; **no** se lee `config/georef/` para esto, evita acoplar
   una migración histórica a un archivo que va a cambiar de contenido con el tiempo), `ALTER TABLE
   complejo FORCE ROW LEVEL SECURITY`, borra las cuatro columnas y el `CHECK`, y devuelve `localidad` a
   `NOT NULL`.
2. **`0024` · pisos del edificio y de la unidad**: agrega `complejo.pisos` (nullable, 1 a 60) y
   `complejo.subsuelos` (nullable, 0 a 5), **sin calcularlos de las unidades existentes** (D3,
   corrección DBA-1) — quedan en `NULL`, "sin completar", igual que la ubicación de `0023`. Después pasa
   `unidad.piso` a nullable y, con el candado de D9 (`LOCK TABLE unidad IN ACCESS EXCLUSIVE MODE` →
   `NO FORCE ROW LEVEL SECURITY` → `UPDATE` → `FORCE ROW LEVEL SECURITY`), mapea los valores conocidos
   (`PB` → `PB`, `SS` → `SS1`, un entero de 1 a 60 → ese número, todo lo demás y el vacío → `NULL`) y
   recién entonces agrega el `CHECK` de forma `^(SS[1-5]|PB|[1-9]|[1-5][0-9]|60)$`. **Bajada**: con el
   mismo candado de D9, `UPDATE unidad SET piso = '' WHERE piso IS NULL` (vuelve al `server_default=""`
   original de `0005`, no se inventa `PB` ni ningún otro valor con significado), borra el `CHECK` y
   devuelve `piso` a `NOT NULL`; borra las dos columnas del edificio (que ya eran nullable, sin dato que
   perder). La bajada de `unidad.piso` **pierde** qué filas estaban marcadas "sin completar" (vuelven a
   `''`, indistinguibles de un dato viejo vacío): es el punto de no retorno de esta migración.
3. **`0025` · grupo desactivable y evento de auditoría**: agrega `grupo_de_reparto.activo`
   (`NOT NULL DEFAULT true`), amplía el trigger de `0011` para proteger `activo` en "Generales" y suma
   `editar_edificio` al vocabulario de `accion_de_auditoria`. **Bajada**: borra la columna; restaura
   `fn_grupo_generales_protegido` con el cuerpo **textual** de `0011_proteger_generales.py:35-56`
   (`CREATE OR REPLACE FUNCTION`, incluido `LANGUAGE plpgsql SET search_path = ''`) — "restaura" acá
   significa repetir ese cuerpo exacto en la bajada, no una frase suelta — y quita la fila del
   vocabulario (si ya hay auditorías con ese evento, la bajada falla a propósito: la auditoría sólo se
   agrega, mismo mecanismo que `0022`; ver Punto de no retorno).

**Ninguna migración necesita índice nuevo** (revisión DBA, 26/10/2026): las consultas que el change
agrega en runtime —unidades con `piso IS NULL` por edificio (tarea 3.8), grupos filtrados por `activo`
(tarea 4.5)— filtran por `(administracion_id, complejo_id)` y entran por el prefijo de
`uq_unidad_identificador` / `uq_grupo_complejo_id`, que ya existen. Las tareas 3.5 y 3.8 pegan el
`EXPLAIN` real que confirma esto antes de cerrarse, con la misma disciplina que el 4a dejó escrita para
`uq_configuracion_vigencia` en su propio design — no alcanza con la conclusión sin el plan debajo.

**El candado de D9 es necesario sólo para el `UPDATE` de `unidad.piso` en `0024`** (subida y bajada):
es la única transformación real de datos existentes de este change. `0023` y la subida de `0024` no
tocan ninguna fila — por eso evitan el problema de raíz en vez de pagarlo.

**Probado sobre una copia con datos** (requisito de la ficha 3c): subida, bajada y subida otra vez
sobre una base sembrada con el edificio de ejemplo más filas armadas a mano con los casos de borde del
mapeo de `piso` y con `localidad` en texto libre que no matchea nada — y el mismo recorrido de
`test_rls_edificio.py::test_downgrade_a_0004_y_upgrade_conservan_la_unidad_del_2a` (baja a `0004`, inserta
un complejo "viejo" sin ubicación ni pisos, sube a `head`) para confirmar que la guarda de L-023 no se
conforma sólo con el `rg` de `INSERT INTO complejo`/`INSERT INTO unidad` (esa guarda, sola, ya falló una
vez en `0016` por esta misma razón).

**Punto de no retorno**: dos, no uno. (a) La primera corrección manual de un piso o de una ubicación
hecha en la pantalla nueva — desde ahí, la bajada de `0024` pierde el marcador de "sin completar" y la
de `0023` pierde la ubicación cargada; a partir de ese momento se vuelve atrás restaurando un respaldo
(change 1d), no con `downgrade`. (b) La primera vez que se audita `editar_edificio` (evento nuevo de
`0025`) — desde ahí, `downgrade` de `0025` falla a propósito en vez de borrar auditoría (mismo mecanismo
que `0022` del 4a); volver atrás después de ese punto también es restaurar un respaldo.

**Orden de despliegue**: migraciones primero (son compatibles con el código viejo: todo lo nuevo es
nullable o tiene default), después la API, después la web. La semilla se actualiza junto con la API.

## Open Questions

- **El tope de 5 subsuelos y 60 pisos** (D3) sale de lo que se ve en Mendoza, no de un dato de Alberto.
  Si aparece un edificio real que no entra, es un `CHECK` de una línea; no cambia los specs ni las
  tareas.
- **Si el `<select>` de 135 departamentos resulta incómodo** en el recorrido manual (D8), el combobox
  accesible queda como deuda del cierre. No cambia el contrato de la API ni los specs.
- **Cuándo se borra `complejo.localidad`** (D2): queda como deuda anotada para el primer change que
  toque el módulo después de este. No bloquea nada acá.
