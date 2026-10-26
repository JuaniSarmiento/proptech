# Exploración: pulido de la configuración del edificio (3c, C-06c)

> Explore. No se escribió código, no se corrió `openspec new` ni se creó el change: el propose lo
> hace Emiliano Caceres con el stack, siguiendo el método (sección 7). Lo que sigue son hallazgos con
> su lugar en el código y recomendaciones; **nada acá es una decisión tomada**. Las decisiones que
> quedan abiertas están en la sección 6 y en `knowledge-base/10_preguntas_abiertas.md` (P61 a P69).

**Fecha**: 26/10/2026 · **Base**: `main` en `de3c710`
**Disparadores**:

1. El barrido de QA manual del 23/10/2026 (Playwright y sesión real contra el stack local, con los
   cambios 1a a 3b, 2.2a y 2b archivados), que hasta hoy vivía en `CLAUDE.md`/`AGENTS.md`.
2. Dos pedidos nuevos de Juani (26/10/2026): la **ubicación** del edificio con listas encadenadas
   (provincia, departamento, localidad) y la **cantidad de pisos** del edificio, con el piso de cada
   unidad elegido de una lista que sale de esa cantidad.

**Dónde va en el roadmap**: `CHANGES.md` [C-06c], en paralelo al 4a `cimientos-del-libro` y fuera
del camino crítico. Ficha en `knowledge-base/12_fichas_de_changes.md` §3c.

**Cómo se verificó cada referencia**: con `rg -n` sobre `main` (`de3c710`) el 26/10/2026, entre las
10:00 y las 10:10. Las líneas pueden moverse si el 4a se mergea antes (toca `unidades.py` y
`configuracion_versionada`; ver la sección 5). Donde la causa de un bug **no** se confirmó
reproduciéndolo, se dice "hipótesis": el propose la confirma con un test en rojo antes de arreglar.

---

## 1. Qué es el cambio, en castellano llano

Las siete pantallas de configuración del edificio (3b) funcionan, pero un administrador que las usa
por primera vez tropieza: campos que no dicen qué formato esperan, errores que aparecen en el campo
equivocado o con un mensaje genérico, botones que se ven aunque el rol no los pueda usar, y una
dirección del edificio que es un texto libre. Este cambio junta esos tropiezos y los dos pedidos
nuevos de Juani en un solo pulido, **sin tocar plata**: no escribe en la cuenta corriente ni en la
configuración de intereses más allá de cómo se muestran sus errores.

## 2. Hallazgos del QA manual del 23/10/2026

Cada ítem: qué pasa, dónde está, cómo reproducirlo y si es **bug** (el sistema hace algo distinto de
lo que dice su spec o su pantalla) o **decisión** (hay que elegir cómo debería ser).

### 2.1 Bugs

**B-1 · Error genérico al guardar intereses y vencimiento.** *Bug.*
- **Qué pasa**: el QA cargó "Día de vencimiento" fuera de rango (35) y el guardado terminó con "No
  pudimos guardar los datos. Probá de nuevo.", sin señalar el campo.
- **Dónde**: el formulario limita el campo a 1..28 (`web/src/app/edificios/[id]/configuracion/Pantalla.tsx:164-170`,
  `min={1} max={28}`) y la API también (`backend/src/proptech_core/complejos/dominio/configuracion.py:22`,
  `Field(ge=1, le=28)`), así que **el rango real es 1 a 28, no 1 a 31** como anotó el QA. El mensaje
  genérico sale de la última rama de `crearVersionDeConfiguracionAction`
  (`web/src/app/edificios/[id]/configuracion/acciones.ts:98`): la acción maneja `ok`, `invalido`,
  `sin_permiso` y `sin_sesion` (líneas 80 a 93), **pero no `conflicto`** (el 409 que
  `web/src/lib/api/cliente.ts:137-141` devuelve cuando la API responde `Conflicto`). Un "Rige desde"
  repetido llega como 409 (`backend/src/proptech_core/complejos/aplicacion/escritura.py:228`, la
  restricción `uq_configuracion_vigencia` mapeada a `vigente_desde`) y cae en el genérico.
- **Hipótesis** (sin reproducir): el genérico del QA vino del 409 de "Rige desde", no del día 35; un
  35 con una fecha nueva debería dar 422 en `dia_de_vencimiento`. Lo que sí está en el código es que
  **cualquier conflicto de vigencia termina en el mensaje genérico**.
- **Cómo reproducirlo**: en un edificio, "Cambiar configuración" dos veces con el mismo "Rige desde";
  la segunda muestra el genérico. Después, por separado, un día 35 con un "Rige desde" nuevo, para ver
  si el navegador lo frena (el input tiene `max=28`) o si llega a la API.
- **Arreglo esperado**: rama `conflicto` en la acción con un mensaje en el campo `vigente_desde`
  ("Ya hay una versión que rige desde esa fecha"), como ya hacen grupos y categorías
  (`web/src/app/edificios/[id]/grupos/acciones.ts:51`).

**B-2 · Error atribuido al campo equivocado.** *Bug.*
- **Qué pasa**: con un "Rige desde" repetido y un día de vencimiento inválido a la vez, el error
  apareció en "Tasa mensual", que estaba bien.
- **Dónde**: el mapeo de error a campo está en `web/src/lib/api/cliente.ts:142-159` (toma `loc` sin
  el primer segmento) y `web/src/lib/api/mensajes.ts:46-61` (`erroresDeFormulario`); los errores se
  muestran por contexto en `web/src/componentes/Formulario.tsx:46-100`. "Tasa mensual" es el primer
  campo después de "Rige desde" en el formulario (`configuracion/Pantalla.tsx:118-131`).
- **Hipótesis** (sin reproducir): un `loc` que no matchea un campo conocido o un error del validador
  de `tasa_mensual` en modo `before` (`configuracion.py:28-40`) que se dispara con otro dato. No está
  confirmada: el propose arranca por **reproducirlo con un test** (cuerpo con los dos errores, ver qué
  `loc` devuelve la API real) antes de tocar nada.
- **Cómo reproducirlo**: el mismo formulario, "Rige desde" igual a la versión vigente y día 35.

**B-3 · Invitación abierta con la sesión de otra cuenta.** *Bug de UX en dominio de acceso (CRITICAL).*
- **Qué pasa**: si alguien abre el link de invitación con la sesión de **otra** cuenta abierta, ve
  "Este enlace ya no sirve. Pedile a tu administración que te invite de nuevo." y no sabe que el
  problema es la cuenta.
- **Dónde**: la página sólo mira si **hay** sesión (`web/src/app/invitacion/[sobre]/page.tsx:20`,
  `accion={sesion ? ... : null}`), no de quién es. El backend rechaza con `InvitacionNoDisponible`
  cuando el email no coincide o cuando la identidad ya está vinculada a otra persona
  (`backend/src/proptech_core/acceso/aplicacion/invitaciones.py:95-115`, `identidad_ajena`), sin
  distinguir motivos a propósito (anti-enumeración). El texto sale de
  `web/src/app/invitacion/Pantalla.tsx:38`.
- **Cómo reproducirlo**: invitar a A; entrar como B en el mismo navegador; abrir el link de A.
- **Arreglo propuesto por el QA** (no implementado): una lectura que, con el token, devuelva el email
  destinatario sin romper la anti-enumeración, y la pantalla "Esta invitación es para X, estás
  ingresado como Y: cerrá sesión primero". Ya existe un camino parcial: el link de ingreso agrega
  `cerrar=1` cuando hay sesión (`page.tsx:21`). **Toca acceso**: ver la decisión P68.

### 2.2 Gaps de UX y validación

**G-1 · Identificador de unidad sin formato ni máximo visibles.** *Decisión menor (texto de ayuda).*
- El backend lo limita a 1..40 caracteres recortados
  (`backend/src/proptech_core/complejos/aplicacion/unidades.py:33`); el mensaje de largo es "Es muy
  largo." (`web/src/lib/api/mensajes.ts:13`) y no dice el máximo. El QA probó con ~200 caracteres.
- Reproducir: "Agregar unidad" con un identificador de 41 caracteres.
- Propuesta: decir el máximo en el error y un ejemplo en la ayuda ("1A", "PB-2", "Cochera 3").

**G-2 · Coeficiente como fracción, no como porcentaje.** *Decisión menor (texto de ayuda).*
- Se espera un número mayor que 0 y hasta 1 (`backend/migraciones/versions/0005_edificio_y_unidad.py:52`,
  `ck_unidad_coeficiente`); `50` se rechaza y la pantalla no lo explica
  (`web/src/app/edificios/[id]/unidades/Pantalla.tsx`, campo `coeficiente`).
- Propuesta: ayuda "0,5 es la mitad del edificio"; **no** aceptar porcentajes (cambiaría el contrato).

**G-3 · "Clave" de grupos y categorías con mensaje genérico.** *Bug de mensaje; la regla está bien.*
- **Corrección al QA**: el patrón real es `^[a-z][a-z0-9_]{0,39}$` (empieza con letra minúscula,
  sigue con minúsculas, dígitos o **guion bajo**, hasta 40), en
  `backend/src/proptech_core/complejos/aplicacion/grupos.py:38` y
  `backend/src/proptech_core/compartido/parametros.py:37` (categorías). El QA anotó `^[a-z0-9]+$` y
  que el guion bajo se rechaza: el código dice lo contrario. Lo que rechaza es mayúsculas, guion
  medio, empezar con dígito y más de 40.
- El rechazo llega como "Este valor no es válido." (`web/src/lib/api/mensajes.ts:14`) en el campo
  (`grupos/Pantalla.tsx:286`, `categorias/Pantalla.tsx:328`).
- Reproducir: grupo con clave `Pileta`, `pileta-1` o `1pileta`.
- Propuesta: decir la regla en la ayuda y en el error. Decidir (P69 incluye la pregunta) si la clave
  se genera sola desde el nombre, que es lo que un administrador espera.

**G-4 · "Quitar" en Personal sin confirmación.** *Decisión.*
- `web/src/app/personal/Pantalla.tsx:100-124` (`BotonQuitar`) envía apenas se toca; la API
  (`backend/src/proptech_api/personal.py:188`, `DELETE /asignaciones/{id}`) quita la asignación.
  "Saldos previos" sí pide confirmar (`web/src/app/edificios/[id]/saldos-previos/Pantalla.tsx:62`).
- Reproducir: como super admin, `/personal`, "Quitar" sobre cualquier asignación.
- Propuesta: confirmación dentro de la pantalla (el visor no admite `confirm()` nativo en algunos
  entornos y el diseño del 3b ya resuelve confirmaciones en el panel).

**G-5 · `/privacidad` muestra una nota interna.** *Bug de contenido, sin decisión legal.*
- `web/src/app/privacidad/page.tsx:24`: "Borrador pendiente de aprobación de Juani." visible a
  cualquiera, y el test lo exige (`web/src/app/privacidad/page.test.tsx:26`). El aviso entero es
  borrador por decisión de cierre del 2b (D-108, ficha 2b, deuda "aviso de privacidad").
- Propuesta: cambiar la nota por un texto para el usuario ("Este aviso está en revisión") y el test
  con él. **No** completar los datos legales: eso es de Juani antes de producción.

**G-6 · No se puede borrar un grupo.** *Decisión.*
- No hay ruta de borrado: `backend/src/proptech_api/complejos.py` sólo tiene `PATCH /grupos/{id}`
  (línea 414) y `PUT /grupos/{id}/unidades` (línea 427). Las categorías se desactivan (columna
  `activa`), no se borran (R16).
- Propuesta: **desactivar**, igual que las categorías, porque cuando existan gastos (6) un grupo
  borrado dejaría gastos huérfanos. Ver P69.

### 2.3 El menú no se adapta al rol (los cinco roles que no son super admin)

*Decisión de diseño con trabajo de backend.*
- **Qué pasa**: Administrador (los dos alcances), Contador, Auxiliar y Consejo ven "Personal" y
  "Nuevo edificio"; Contador ve además "Agregar unidad" y todo el menú del edificio. Al usarlos, el
  backend los frena (403) con un mensaje claro. No es un agujero: la autoridad es el backend.
- **Dónde**: el menú de la administración es fijo (`web/src/app/personal/secciones.ts:9-18`), igual
  que "Nuevo edificio" (`web/src/app/edificios/Pantalla.tsx:84` y `:105`) y "Agregar unidad"
  (`web/src/app/edificios/[id]/unidades/Pantalla.tsx:134`). La web **no tiene de dónde saber los
  permisos**: la sesión que devuelve el backend trae sólo nombre y administraciones
  (`backend/src/proptech_core/acceso/aplicacion/sesion.py:17-39`).
- **La matriz** no se copia acá: vive en D-106 (`knowledge-base/09_decisiones_y_supuestos.md`) y en
  `knowledge-base/03_actores_y_roles.md`, y en código en `_MATRIZ`
  (`backend/src/proptech_core/acceso/dominio/permisos.py:121-138`). El QA la cotejó el 23/10 contra
  D-106 y coincide; las dos asimetrías (Administrador de un edificio no confirma "sin saldos previos";
  Contador sólo lee) son diseño, no hallazgos.
- **Reproducir**: entrar con cada uno de los cinco roles y mirar el menú y los botones.
- **Propuesta**: el backend expone las acciones permitidas de la persona (por administración y por
  edificio) y la web oculta lo que no puede usar; el backend sigue siendo la autoridad. Exponer
  permisos es leer `acceso`: ver P68.

### 2.4 Reinvitar el mismo email con otro rol

*Decisión en dominio de acceso (CRITICAL).*
- **Qué pasa**: si se invita de nuevo a un email que ya tiene `persona` (aunque la invitación vieja
  esté revocada), se suma otra asignación sobre la misma persona y el nombre nuevo se ignora.
- **Dónde**: `backend/src/proptech_core/acceso/aplicacion/usuarios.py:42-43`
  (`INSERT ... ON CONFLICT (administracion_id,email) DO NOTHING`).
- **Reproducir**: invitar `x@ejemplo.com` como "Ana", revocar, invitar el mismo email como "Ana
  María" con otro rol; `/personal` muestra "Ana" con dos asignaciones.
- **Opciones**: actualizar el nombre (pisa un nombre que quizás cargó otra persona) o avisar en la
  pantalla de invitación que ese email ya existe y con qué nombre. Ver P68.

### 2.5 `/personal` jerárquica (sugerencia de Emiliano, 23/10/2026)

*Pregunta abierta para Juani, NO decidida.*
- Hoy es binaria: sólo el super admin ve y gestiona el personal
  (`permisos.py:131`, `INVITAR_USUARIOS_Y_ASIGNAR_EDIFICIOS` sólo `_SA`; `personal.py:162-166`).
  Un Administrador de cualquier alcance recibe "No podés ver el personal de la administración. Esto lo
  puede hacer el super admin de la empresa."
- La sugerencia: que el Administrador de toda la empresa vea y gestione a los que están por debajo
  (Contador, Auxiliar, Consejo, administradores de un edificio), nunca al super admin.
- Es cambiar D-106 (acceso, CRITICAL). Se registra como **P66**; si Juani dice que sí, es una
  decisión nueva (D-NNN) y, por tamaño y gobernanza, conviene un change propio de acceso, no este.

### 2.6 Lo que el QA confirmó que NO es bug

Se deja para que nadie lo vuelva a investigar: editar una unidad funciona; una unidad puede estar en
varios grupos (R01); "Armar los grupos de reparto" marca "falta" si un grupo distinto de "Generales"
no tiene unidades, a propósito (`backend/src/proptech_core/complejos/aplicacion/lectura.py:204-221`);
el alcance por rol y edificio lo respeta el backend en todos los casos probados.

**Sin probar**: propietario e inquilino (el portal llega en el 11) y todo lo de plata (4 a 7).

## 3. Pedido nuevo: la ubicación del edificio

### 3.1 Cómo se guarda hoy

- `complejo` tiene `nombre` y `localidad`, los dos `TEXT NOT NULL`
  (`backend/migraciones/versions/0005_edificio_y_unidad.py:24-25`; `04_modelo_de_datos.md:186`).
  **No hay provincia, departamento, calle ni número**: la ayuda sugiere usar el nombre como dirección
  ("Alsina 123" en Godoy Cruz, `web/src/app/edificios/ayuda.ts:14`).
- `localidad` quedó **afuera** del `CHECK` de texto no vacío, a propósito y para que decida Juani
  (`0016_textos_no_vacios.py:19-35`); la API la exige de 1 a 200 caracteres
  (`backend/src/proptech_api/complejos.py:113-120`, `CuerpoEdificio`).
- La pantalla la pide como texto libre (`web/src/app/edificios/Pantalla.tsx:176-177`).
- **No existe editar un edificio**: hay `POST /complejos` pero ningún `PATCH /complejos/{id}`
  (`backend/src/proptech_api/complejos.py:236`, lista de rutas). Hoy, una localidad mal cargada no se
  corrige desde la pantalla.
- La semilla usa `localidad: "Mendoza"` (`config/semilla/edificio-ejemplo.yaml:4`), que además es
  ambigua (Mendoza es provincia y es la Ciudad de Mendoza, departamento Capital).

### 3.2 Fuente de datos propuesta

**Georef**, el Servicio de Normalización de Datos Geográficos del Estado (datos.gob.ar, hoy bajo la
Secretaría de Innovación Pública). Es la fuente oficial de provincias, departamentos, municipios y
localidades, armada sobre IGN, BAHRA e INDEC, con ids estables (código INDEC: provincia `50` es
Mendoza).

- **Licencia**: Creative Commons Atribución 4.0 (términos de uso de Georef,
  `https://datosgobar.github.io/georef-ar-api/terms/`): uso libre, también comercial, citando la
  fuente. La atribución va en el archivo de datos y en el README.
- **Descarga**: archivos completos en JSON o CSV, `https://apis.datos.gob.ar/georef/api/{provincias,departamentos,localidades}.json`
  (redirigen a `infra.datos.gob.ar/georef/`).
- **Tamaños medidos** (26/10/2026, 10:05, `curl -sL` y `jq`):

  | archivo | registros | completo | reducido a `id, nombre, padre` |
  |---|---|---|---|
  | provincias | 24 | 5 KB | menos de 2 KB |
  | departamentos | 529 (18 de Mendoza) | 127 KB | unos 20 KB |
  | localidades | 4.028 en el archivo completo (4.037 según la API paginada) | 1,45 MB | 257 KB (47 KB comprimido); sólo Mendoza: 206 localidades, 13 KB |

  La diferencia 4.028 / 4.037 entre el archivo y la API es de la fuente; el propose fija **qué
  versión** se guarda y con qué fecha.
- **Guardada dentro del repo, no consultada en vivo**: un archivo reducido (por ejemplo
  `config/georef/` con provincias, departamentos y localidades, y un `LEEME` con fuente, fecha de
  descarga, licencia y el comando que lo regenera). Motivos: la app no depende de un servicio
  externo para crear un edificio; la CSP estricta del 2b no tiene que abrir otro origen; los tests
  son deterministas. La API de Georef se usa **sólo** para regenerar el archivo, a mano.
- **Listas encadenadas**: provincia, después departamento (sólo los de esa provincia), después
  localidad (sólo las de ese departamento). Se completan tocando; con teclado, cada lista es un
  `<select>` (o un combobox accesible si son largas: Buenos Aires tiene 135 departamentos).
- **Qué valida el backend**: que el trío exista y sea coherente (la localidad pertenece al
  departamento, y éste a la provincia), contra el mismo archivo. La web no es la autoridad.
- **Qué se guarda en `complejo`**: los **ids** de Georef (más el nombre para mostrar, o el nombre se
  resuelve desde el archivo). Guardar sólo texto repetiría el problema de hoy.

### 3.3 Decisiones abiertas de la ubicación

- **P61 · ¿Sólo Argentina?** El mercado es Mendoza y el producto es para propiedad horizontal
  argentina; la recomendación es sí, sin campo país.
- **P62 · Calle y número**: ¿se agregan como texto libre (Georef también normaliza calles, pero el
  archivo es mucho más grande), o el nombre del edificio sigue haciendo de dirección? ¿Piso y depto
  del edificio no aplican?
- **P63 · Los edificios ya cargados**: tienen `localidad` en texto libre. Opciones: (a) migración que
  deja la ubicación nueva en nulo y la pantalla pide completarla; (b) intentar mapear el texto a un id
  de Georef y dejar en nulo lo que no matchea; (c) obligatoria desde ya, frenando el alta. Hoy no hay
  datos reales (sólo el ejemplo y lo que se cargó a mano en desarrollo), así que el costo es bajo.
  Va junto con la pregunta de si `localidad` texto se borra o queda.
- También: **editar el edificio** (falta la ruta) entra en este cambio si la ubicación se puede
  corregir; si no, una ubicación mal elegida no tiene arreglo.

## 4. Pedido nuevo: la cantidad de pisos

### 4.1 Cómo es hoy

- `complejo` **no tiene** cantidad de pisos.
- `unidad.piso` es `TEXT NOT NULL` sin largo máximo (`0005_edificio_y_unidad.py:39`;
  `backend/src/proptech_core/complejos/aplicacion/unidades.py:36`, sólo sin caracteres de control) y
  la pantalla lo pide como texto libre (`web/src/app/edificios/[id]/unidades/Pantalla.tsx:316`).
- La semilla mezcla números y siglas: `piso: "PB"` para el local `L-PB`, `"1"` a `"4"` para los
  departamentos y `"SS"` para las cocheras `C1` a `C3` y la baulera `B1`
  (`config/semilla/edificio-ejemplo.yaml:7-19`).
- Los tipos de unidad son cuatro: departamento, cochera, baulera y local
  (`backend/src/proptech_core/compartido/tipos_de_unidad.py`, D-029).
- El importador de Excel (5) trae "piso" como columna (HU-A2, `06_funcionalidades.md:72`): lo que se
  decida acá fija qué acepta esa columna.

### 4.2 Propuesta

- `complejo` suma la cantidad de pisos sobre planta baja (entero, con mínimo y máximo) y, si se
  decide, la cantidad de subsuelos.
- El piso de la unidad se elige de una lista que se arma con eso: subsuelos (por ejemplo "SS1",
  "SS2"), "PB" y "1" a N. El backend valida que el piso esté en la lista del edificio.
- Reducir el número de pisos con unidades cargadas arriba se rechaza con un error que diga cuáles.

### 4.3 Decisiones abiertas de los pisos

- **P64 · Qué pisos existen**: ¿planta baja siempre? ¿subsuelos, cuántos como máximo y cómo se
  nombran? ¿entrepiso, terraza? ¿Cocheras, bauleras y locales eligen de la misma lista (la semilla
  pone las cocheras en "SS")? ¿Cuál es el máximo de pisos (Mendoza tiene pocos edificios de más de 30;
  un tope de 60 sobra)?
- **P65 · Las unidades existentes**: tienen `piso` en texto libre. Opciones: migración que mapea los
  valores conocidos ("PB", "SS", números) y deja el resto marcado para corregir; o el campo nuevo
  convive con el texto hasta que el administrador corrija. Hoy no hay datos reales.

## 5. Qué toca cada ítem y quién lo revisa

| ítem | backend | web | base | gobernanza propia |
|---|---|---|---|---|
| B-1, B-2 errores de intereses | quizás (si B-2 es del `loc`) | sí | no | HIGH (pantalla de configuración) |
| B-3 invitación con otra cuenta | sí (lectura nueva) | sí | no | **CRITICAL** (acceso) |
| G-1, G-2, G-3 ayudas y mensajes | no (o mensajes) | sí | no | baja |
| G-4 confirmar "Quitar" | no | sí | no | baja |
| G-5 nota de privacidad | no | sí | no | baja |
| G-6 desactivar grupo | sí | sí | sí (columna `activo` o similar) | HIGH |
| 2.3 menú por rol | sí (exponer permisos) | sí | no | **CRITICAL** (acceso) |
| 2.4 reinvitar | sí | sí | no | **CRITICAL** (acceso) |
| 2.5 `/personal` jerárquica | sí | sí | quizás | **CRITICAL** (cambia D-106) |
| 3 ubicación | sí (validación, editar edificio) | sí | sí (columnas, migración de existentes) | HIGH |
| 4 pisos | sí | sí | sí (columna, migración de `piso`) | HIGH |

**Gobernanza propuesta del change: HIGH**, porque toca esquema (`complejo`, `unidad`, grupos) y
migra datos existentes. **Los ítems marcados CRITICAL (acceso) suben el change entero a CRITICAL si
entran**; la recomendación es dejarlos afuera, en un change de acceso propio, y que Juani lo decida
(P68).

**Revisores** (de a uno, en verify, cada uno con su "terminado" de `~/.claude/CLAUDE.md`):
**QA** siempre; **DBA** (migraciones con bajada probada sobre una copia con datos, índice si se
filtra por ubicación); **frontend** (teclado, foco visible, error asociado al campo, 320 px sin
scroll horizontal); **backend** (contrato de error de cada endpoint nuevo: editar edificio y, si
entra, la lectura de permisos). Arquitecto sólo si entra algo de acceso (frontera `acceso`/`web`).

**Choques con el 4a** (`change/cimientos-del-libro`, propose en revisión):
- **Migraciones**: el 4a usa `0021` y `0022`. Las del pulido no pueden nacer con el mismo número ni
  con `down_revision` `0020`: Alembic quedaría con dos cabezas. Se numeran después de que el 4a se
  mergee (o se acuerda el orden con quien lo construye) y se rebasan.
- **`unidades.py`**: el 4a hace que `editar_unidad` audite (recibe `identidad` y `request_id`). El
  pulido toca la validación de `piso` en el mismo archivo: conflicto de merge esperable, chico.
- **Auditoría**: si el pulido audita "editar edificio", suma un evento al vocabulario de
  `accion_de_auditoria`, que el 4a también amplía en `0022`.
- **`configuracion_versionada`**: el 4a la pasa al rol de arranque. El pulido **no** debe alterar esa
  tabla (B-1 y B-2 son de la web); si lo necesitara, después del 4a falla con `must be owner`.

## 6. Decisiones que le quedan a Juani

Registradas en `knowledge-base/10_preguntas_abiertas.md`:

- **P61** ubicación: ¿sólo Argentina?
- **P62** ubicación: ¿calle y número libres, o el nombre sigue siendo la dirección?
- **P63** ubicación: ¿qué pasa con los edificios ya cargados y con `localidad` texto?
- **P64** pisos: planta baja, subsuelos, cocheras y locales, el máximo.
- **P65** pisos: migración de las unidades existentes.
- **P66** `/personal` jerárquica (cambia D-106).
- **P67** las dos cuentas de Mailinator de BE-7 en el Clerk de desarrollo: ¿se borran?
- **P68** los ítems de acceso (B-3, 2.3, 2.4): ¿entran al pulido (sube a CRITICAL) o van a un change
  de acceso propio?
- **P69** grupos y claves: ¿desactivar grupos en vez de borrarlos? ¿la clave se genera sola desde el
  nombre?

## 7. Para Emiliano: cómo arrancar

1. **Rama propia** desde `main` actualizado: `change/pulido-de-la-configuracion`. Nunca sobre `main`;
   el cierre es un PR (L-037, L-038).
2. **Leer antes**: esta exploración; `CHANGES.md` [C-06c]; la ficha §3c de
   `knowledge-base/12_fichas_de_changes.md`; `knowledge-base/15_lecciones.md` entero (en especial
   L-029, L-034, L-035, L-038, L-039 y L-040); el design del 3b
   (`openspec/changes/archive/2026-10-20-pantallas-del-edificio/`); `DESIGN.md` y `PRODUCT.md`
   (impeccable manda en toda pantalla); y el propose del 4a para ver el formato vigente.
3. **Respuestas de Juani primero**: P61 a P65 y P68 cambian el alcance. Sin respuesta, el proposal
   las lista como elecciones (E1, E2, ...) para que se firmen con el resto.
4. **`/opsx:propose pulido-de-la-configuracion`**, pasándole esta exploración como entrada. El
   proposal declara gobernanza HIGH (o CRITICAL si P68 mete acceso), la sección
   `## Knowledge Base Impact` y la de lo que queda fuera.
5. **Aprobación**: la sección "Aprobación" del `proposal.md` la firma, a mano, con nombre y fecha,
   **Juani, Alberto o Emiliano** (D-094, D-111). Emiliano puede firmar su propio change; ningún agente
   la completa. Una regla que entre después de la firma necesita firma propia (L-029).
6. **Revisores de a uno** sobre el propose (frontend y DBA como mínimo), sin que uno vea el informe
   del otro; después, construir.
7. **TDD con el rojo pegado**: cada tarea pega en su informe el comando, la salida del test en rojo y
   la hora, y el rojo tiene que caer en la aserción que el test dice probar (L-034), no en un
   `ImportError`. Backend con `bash infra/ci/test-backend.sh <archivos>`; web con
   `bash infra/ci/test-web.sh`.
8. **Verificación en el navegador**: cada pantalla tocada, a 1280 y 320 px y entera con teclado, con
   capturas guardadas y el paso exacto de cómo la cuenta de Clerk usada quedó vinculada a su persona
   (L-039). Esto salda también la deuda del PR #1 (ficha 3b-bis: recorrido a 320 px y con teclado sin
   capturas).
9. **Verify** con QA, DBA, frontend y backend (sección 5); **archivar** y abrir el PR. No se mergea
   sin revisión.

## Knowledge Base Impact

Anticipado para el propose. **REWRITE** = el documento describe el estado nuevo; **APPEND** =
historia fechada.

| documento | operación | qué |
|---|---|---|
| `04_modelo_de_datos.md` | REWRITE | `complejo` con ubicación y pisos; `unidad.piso` acotado; grupo desactivable si entra |
| `05_reglas_de_negocio.md` | REWRITE | sólo si la ubicación o los pisos pasan a ser regla con tests mínimos (por respuesta a P61 a P65, D-089) |
| `06_funcionalidades.md` | REWRITE | HU-A1 y HU-A2 (la columna piso del Excel) |
| `09_decisiones_y_supuestos.md` | APPEND | respuestas a P61 a P69; fuente y licencia de Georef |
| `10_preguntas_abiertas.md` | REWRITE | cerrar las P que se respondan |
| `12_fichas_de_changes.md` | REWRITE | ficha 3c y la deuda de su cierre |
| `15_lecciones.md` | APPEND | lo que enseñe |
| `CHANGES.md`, `CLAUDE.md`, `AGENTS.md` | REWRITE | estado del 3c |
