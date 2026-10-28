## Why

Las siete pantallas de configuración del edificio (3b) funcionan, pero un administrador que las usa
por primera vez tropieza: campos que no dicen qué formato esperan, errores que caen en el campo
equivocado o salen con un texto genérico, un grupo que no se puede sacar de uso y una dirección del
edificio que es texto libre. El barrido de QA manual del 23/10/2026 dejó once hallazgos ubicados en
el código y Juani pidió, el 26/10/2026, dos cosas más: la **ubicación** del edificio elegida de
listas oficiales encadenadas y la **cantidad de pisos** del edificio, con el piso de cada unidad
elegido de esa lista. Este cambio junta todo en un solo pulido, antes de que el importador de Excel
(5) fije qué acepta la columna "piso" y antes de que el edificio piloto (15) se cargue de verdad.

Entrada completa, con cada ítem en su archivo y línea:
`openspec/exploraciones/2026-10-26-pulido-de-la-configuracion.md` (26/10/2026, base `main` en
`de3c710`).

Cubre: **HU-A1** (configurar el edificio) y el borde de **HU-A2** (la columna "piso" del importador).
**Reglas**: **R01** (el informe de coeficientes no cambia; sólo su ayuda), **R16** (una categoría se
desactiva, nunca se borra: el grupo pasa a seguir la misma regla). **Decisiones**: **D-016** (alcance
de la auditoría), **D-029** (los cuatro tipos de unidad), **D-040** (fronteras entre módulos),
**D-094** y **D-111** (quién firma), **D-100** (los dos modos de coeficientes), **D-102** y **D-105**
(ayuda y forma de las pantallas), **D-106** (matriz de permisos, que este cambio **no** toca),
**D-108** (el aviso de privacidad sigue en borrador), **D-127** (`/personal` jerárquica, aprobada en
principio y **fuera** de este cambio). Decisión nueva a escribir con la firma: **D-128**, las
respuestas a P61 a P65, P67, P68 y P69, más la fuente y la licencia de Georef.

## Qué queda fuera

| qué | dónde va | por qué |
|---|---|---|
| **B-3** · la invitación abierta con la sesión de otra cuenta (`web/src/app/invitacion/[sobre]/page.tsx:20`; `acceso/aplicacion/invitaciones.py:95-115`) | Change de acceso propio, futuro | Es dominio `acceso`: el arreglo necesita una lectura nueva del email destinatario sin romper la anti-enumeración. Entrar acá subiría el change entero a CRITICAL (P68) |
| **2.3** · el menú y los botones que no se adaptan al rol, en los cinco roles que no son super admin | Change de acceso propio, futuro | Exige que el backend exponga las acciones permitidas de la persona: leer `acceso` y ampliar la sesión (`acceso/aplicacion/sesion.py:17-39`). CRITICAL (P68). **No es un agujero**: el backend sigue siendo la autoridad y frena cada acción con 403 |
| **2.4** · reinvitar el mismo email no actualiza el nombre (`acceso/aplicacion/usuarios.py:42-43`) | Change de acceso propio, futuro | Dominio `acceso`, CRITICAL (P68) |
| **2.5 / P66** · `/personal` jerárquica | Change de acceso propio, futuro | **D-127** la aprueba en principio y la saca explícitamente de este change: cambia la matriz de D-106, que es CRITICAL |
| Los datos legales del aviso de privacidad (responsable, contacto, retención) | Antes de producción, a cargo de Juani | D-108 y la deuda del cierre del 2b. Acá sólo se saca la nota interna filtrada al usuario (G-5) |
| Aceptar coeficientes en porcentaje (`50` por `0.5`) | Ninguno | Cambiaría el contrato y el `CHECK` `ck_unidad_coeficiente`; acá sólo se explica la unidad (G-2) |
| Calles y alturas normalizadas contra Georef | Ninguno por ahora | El dataset de calles es mucho más grande que provincias, departamentos y localidades; calle y número entran como texto libre (P62, E2) |
| Selector de país | Ninguno | Sólo Argentina (P61, E1) |
| Cualquier escritura en `configuracion_versionada`, en la cuenta corriente o en montos | 4b a 4d | Desde el 4a la tabla es del rol de arranque: un `ALTER` acá fallaría con `must be owner`. B-1 y B-2 son de la web, no de la tabla |
| El piso en el importador de Excel | 5 | Este cambio fija el vocabulario que esa columna va a tener que aceptar; no construye el importador |
| Borrar las cuentas de Mailinator del Clerk de desarrollo (P67) | Acción operativa de Emiliano en el panel de Clerk | No toca código ni datos del repo; no es una elección de este change, ya está decidido que se borran — queda afuera de la tabla de Aprobación |

## Gobernanza

**HIGH** (D-094, D-111): toca el esquema de `complejo`, de `unidad` y de `grupo_de_reparto`, y migra
datos ya cargados. No toca plata de nadie ni la matriz de permisos, por eso no es CRITICAL; los
cuatro ítems de `acceso` que sí lo serían quedan afuera (P68, E8). **No se construye nada** hasta que
la sección "Aprobación" quede firmada por Juani, Alberto o Emiliano, con nombre, fecha y el alcance.
Una regla nueva que entre después de la firma necesita firma propia (L-029).

## Elecciones ya resueltas antes del propose

Emiliano respondió P61 a P69 el 26/10/2026, en sesión. Van acá como elecciones resueltas, no como
preguntas abiertas; la firma las ratifica y recién entonces se escriben como **D-128**.

1. **P61 · Sólo Argentina.** Sin campo ni selector de país (E1).
2. **P62 · Calle y número como texto libre**, campo nuevo, **sin** validar contra el dataset de
   calles de Georef (E2).
3. **P63 · Los edificios ya cargados arrancan con la ubicación en nulo** y la pantalla la pide; hoy
   no hay datos reales, sólo el ejemplo (E3).
4. **P64 · Los pisos son PB, subsuelos y hasta N pisos sobre PB.** Al menos un subsuelo tiene que
   estar soportado, porque la semilla real ya pone cuatro unidades en `"SS"`
   (`config/semilla/edificio-ejemplo.yaml:7-19`: `C1`, `C2`, `C3` y `B1`), un subsuelo genérico sin
   numerar. El máximo lo fija este propose (E4, con los números en `design.md`).
5. **P65 · La migración mapea los valores conocidos** (`PB`, `SS`, números) al vocabulario nuevo y
   **marca el resto para que el administrador lo corrija a mano** (E5).
6. **P66 · `/personal` jerárquica: aprobada en principio como D-127, fuera de este change** (E8).
7. **P67 · Las cuentas de Mailinator se borran** del Clerk de desarrollo: ya decidido, acción
   operativa de Emiliano en el panel, sin código ni elección de este change. Las direcciones
   literales ya salieron de la deuda viva (`bbd02fb`) porque el repo es público (L-040).
8. **P68 · Los cuatro ítems de acceso quedan afuera**; el change sigue en HIGH y no sube a CRITICAL
   (E8).
9. **P69 · Un grupo se desactiva, no se borra** (igual que las categorías, R16: un grupo borrado
   dejaría gastos huérfanos cuando exista el 6), y **la clave se autogenera desde el nombre** en vez
   de que el administrador la escriba (E6).

## What Changes

- **Ubicación oficial del edificio, de listas encadenadas.** `complejo` suma los ids de Georef de
  provincia, departamento y localidad, más calle y número como texto libre. Las listas se encadenan
  (la provincia filtra los departamentos, el departamento filtra las localidades) y el **backend**
  valida contra el mismo archivo que la coherencia del trío exista: una localidad de otro
  departamento, o un id que no existe, se rechazan aunque la web los mande. El archivo de **Georef**
  (Servicio de Normalización de Datos Geográficos, datos.gob.ar, **CC BY 4.0**) se guarda **reducido
  dentro del repo** (`config/georef/`) con su `LEEME`: fuente, fecha de descarga, licencia y el
  comando que lo regenera. La app **no** consulta Georef en vivo: no abre un origen más en la CSP
  estricta del 2b, no depende de un servicio externo para crear un edificio y los tests quedan
  deterministas.
- **Editar el edificio**, que hoy no existe (`proptech_api/complejos.py` sólo tiene
  `POST /complejos`): sin esa ruta, una ubicación mal elegida no tiene arreglo. La edición queda
  auditada con un evento nuevo.
- **Cantidad de pisos del edificio y piso de la unidad elegido de esa lista.** `complejo` suma los
  pisos sobre planta baja y los subsuelos; `unidad.piso` deja de ser texto libre
  (`0005_edificio_y_unidad.py:39`, `TEXT NOT NULL` sin largo) y pasa a un vocabulario cerrado
  (`SS…`, `PB`, `1` a N) que el backend valida contra el edificio. Bajar la cantidad de pisos con
  unidades cargadas arriba se rechaza **diciendo cuáles**. **BREAKING** para `edificios-y-unidades`:
  un `piso` que hoy se acepta ("Entrepiso", "planta alta") deja de aceptarse.
- **Migración de lo ya cargado** (E3, E5): la ubicación nueva arranca en nulo y la puesta a punto del
  edificio la pide; los pisos conocidos se mapean y los que no se reconocen quedan marcados para
  corregir, sin inventar un valor. Bajada probada sobre una copia con datos.
- **Un grupo se saca de uso desactivándolo**, no borrándolo (E6, R16), con "Generales" protegido
  también en la base, como ya lo protege la migración `0011`.
- **La clave de grupos y categorías se autogenera desde el nombre** (E6): el administrador no la
  escribe más. La regla real (`^[a-z][a-z0-9_]{0,39}$`,
  `complejos/aplicacion/grupos.py:38` y `compartido/parametros.py:37`) queda escrita en la ayuda para
  quien use la API o el importador. **Corrección al QA**: el patrón admite guion bajo; lo que rechaza
  es mayúsculas, guion medio, empezar con dígito y más de 40.
- **Cada error de formulario en su campo, diciendo qué se espera.** El conflicto de "Rige desde"
  (409, `uq_configuracion_vigencia`) deja de caer en el mensaje genérico de
  `configuracion/acciones.ts:98`: se agrega la rama `conflicto` que ya tienen grupos y categorías
  (`grupos/acciones.ts:51`) (B-1). El error atribuido a "Tasa mensual" (B-2) se **reproduce primero
  con un test en rojo** y sólo después se arregla: la causa no está confirmada. El identificador dice
  su máximo y da ejemplos (G-1); el coeficiente dice que es una fracción, no un porcentaje (G-2); la
  clave explica su regla (G-3).
- **"Quitar" en Personal pide confirmación** dentro de la pantalla, como ya hace "Saldos previos"
  (G-4).
- **`/privacidad` deja de mostrar una nota interna** ("Borrador pendiente de aprobación de Juani",
  `web/src/app/privacidad/page.tsx:24`, exigida por su test) y pasa a un texto escrito para el
  usuario. Los datos legales siguen pendientes de Juani (G-5, D-108).

## Capabilities

### New Capabilities

- `ubicacion-del-edificio`: de dónde salen provincia, departamento y localidad (archivo de Georef en
  el repo, con su licencia y su fecha), cómo se encadenan, qué valida el backend y qué se guarda.

### Modified Capabilities

- `edificios-y-unidades`: el edificio lleva su ubicación, su calle y número y su cantidad de pisos y
  subsuelos; se puede editar; `unidad.piso` sale del vocabulario de pisos de su edificio y ya no es
  texto libre (**BREAKING**); la puesta a punto pide la ubicación y los pisos que falten.
- `grupos-de-reparto`: un grupo parcial se desactiva en vez de borrarse y su clave se autogenera
  desde el nombre; "Generales" no se desactiva, tampoco por SQL.
- `categorias-de-gasto`: la clave de una categoría nueva se autogenera desde el nombre.
- `pantallas-del-edificio`: cada error de formulario cae en su campo con lo que se espera (incluido
  el 409 de vigencia); la ayuda de identificador, coeficiente y clave dice la regla; las pantallas de
  edificio incorporan ubicación y pisos; "Quitar" confirma.
- `auditoria-de-acciones`: editar el edificio queda auditado, con los campos cambiados y sin otros
  valores (D-016).
- `datos-semilla`: el edificio de ejemplo trae su ubicación de Georef y su cantidad de pisos y
  subsuelos, y sus unidades un piso del vocabulario nuevo.

## Impact

- **Backend**: `complejos/dominio/` (vocabulario de pisos, ubicación), `complejos/aplicacion/`
  (`escritura.py`, `unidades.py`, `grupos.py`, `categorias.py`, `lectura.py` — la puesta a punto),
  `compartido/` (lector del archivo de Georef y generador de claves), `acceso/dominio/eventos.py`
  (evento nuevo), `proptech_api/complejos.py` (`PATCH /complejos/{id}` y la lectura de las listas de
  ubicación). Migraciones nuevas **a partir de `0025`**: el 4a ya ocupó `0021` y `0022` y está
  mergeado a `main`; nacer con `down_revision` `0020` dejaría dos cabezas en Alembic.
- **Datos**: `config/georef/` (archivo reducido y su `LEEME`); `config/semilla/edificio-ejemplo.yaml`
  (ubicación y pisos).
- **Web**: `edificios/Pantalla.tsx` y su `ayuda.ts` (alta y edición con ubicación y pisos),
  `edificios/[id]/unidades/`, `grupos/`, `categorias/`, `configuracion/acciones.ts`,
  `personal/Pantalla.tsx`, `privacidad/page.tsx` y su test, `lib/api/mensajes.ts`.
- **Conflicto de merge esperable, chico**: el 4a hizo que `editar_unidad` audite (recibe `identidad`
  y `request_id`) en el mismo `complejos/aplicacion/unidades.py` que este change toca para la
  validación de `piso`. Se rebasa sobre `main` ya mergeado antes de la primera tarea.
- **Sin cambios**: la matriz de permisos (`acceso/dominio/permisos.py`), `configuracion_versionada`,
  la cola, el worker, `compose.yaml` y la CSP.

## Lecciones que aplican (15_lecciones.md)

| lección | cómo la cubre | tarea |
|---|---|---|
| L-034 | El rojo de cada test cae en la aserción que el test dice probar, nunca en un `ImportError` o un 401: cada módulo nuevo existe y devuelve vacío antes del primer rojo | todas las de los grupos 2 a 6 |
| L-035 | Cada garantía nueva (coherencia del trío de ubicación, piso dentro del vocabulario, "Generales" no se desactiva) tiene al menos un caso **verde** real y un mutante dirigido a esa garantía | 2.3, 3.3, 4.2 |
| L-013, L-019 | Los mutantes se corren sobre una copia, sin commit, y se dice en el informe | 2.3, 3.3, 4.2 |
| L-023 | Antes de cerrar cada migración, `rg` en **todo** el repo (no sólo `backend/`) de los `INSERT INTO complejo`, `INSERT INTO unidad` y `INSERT INTO grupo_de_reparto`, incluidos `humo.sh`, la semilla y los fixtures de la web, porque la migración agrega `CHECK` y columnas | 3.4, 4.3 |
| L-002, L-007, L-008 | El archivo de Georef se prueba faltante, vacío, truncado, con un trío incoherente y con otro tipo; la validación de claves y pisos usa coincidencia completa y sólo ASCII; ningún error repite el valor rechazado ni el texto de la librería | 2.1, 3.1, 4.1, 5.4 |
| L-009 | El generador de claves se aplica y se prueba en sus dos usos (grupos y categorías), no en uno solo | 4.4 |
| L-017 | La entrada de cada chequeo nuevo es la del escenario, no una que otra capa ya rechaza (un `piso` inválido se manda por la API, no sólo al dominio) | 3.3 |
| L-026, L-028 | Ningún test verde cuenta como "la pantalla se ve bien": cada pantalla tocada se recorre a mano, y el foco y el `Esc` se prueban con el panel y la confirmación combinados, no por componente suelto | 6.1, 7.1 |
| L-027 | La API falsa de la web no acepta escrituras que la API real rechaza: los fixtures de ubicación y pisos salen del contrato real | 6.2 |
| L-039 | La verificación a mano deja escrito, paso por paso, cómo la cuenta de Clerk usada quedó vinculada a su persona, con comando, rol y base. Salda también la deuda del PR #1 del 3b-bis | 7.1 |
| L-040 | Ninguna dirección de prueba se escribe en el repo ni lleva "admin" en la parte local | 7.1 |
| L-010, L-031, L-037, L-042 | La corrida de cierre va después de la última vuelta, con el SHA anotado, y se espera el CI **del PR** (esta rama sin PR no corre CI) | 7.2 |
| L-029 | Una regla nueva que entre después de la firma necesita firma propia | toda vuelta de correcciones |
| L-038 | Este change no toca la lista de firmantes: D-111 ya está mergeada | — |

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 26/10/2026): `01` a `16` y `README.md`.

| documento | operación | qué |
|---|---|---|
| `09_decisiones_y_supuestos.md` | **APPEND** (al firmar) | **D-128**: las respuestas a P61 a P65, P67, P68 y P69, la fuente y la licencia de Georef (CC BY 4.0, archivo guardado en el repo y no consultado en vivo), el vocabulario de pisos con sus máximos y el criterio de migración de lo ya cargado |
| `09_decisiones_y_supuestos.md` | **APPEND** (al archivar) | Lo que la construcción agregue: el evento de auditoría nuevo, la autogeneración de claves y el grupo desactivable, si se firman con cambios |
| `04_modelo_de_datos.md` | **REWRITE** | `complejo` con ubicación (ids de Georef), calle y número, pisos y subsuelos; `unidad.piso` acotado al vocabulario; `grupo_de_reparto` con su columna de activo; vocabulario de `accion_de_auditoria` con el evento nuevo |
| `06_funcionalidades.md` | **REWRITE** | HU-A1 (configurar el edificio: ubicación, pisos y editar) y HU-A2 (qué acepta la columna "piso" del importador) |
| `05_reglas_de_negocio.md` | **REWRITE** | R16: la regla "se desactiva, nunca se borra" pasa a cubrir también los grupos de reparto. Por respuesta a preguntas abiertas, como permite D-089; nada de R42 en adelante |
| `11_glosario.md` | **REWRITE** | "ubicación del edificio", "piso", "subsuelo", "clave" (autogenerada) |
| `10_preguntas_abiertas.md` | **REWRITE** | Cerrar P61, P62, P63, P64, P65, P67, P68 y P69 con su respuesta; P66 queda cerrada por D-127 y apuntando al change de acceso futuro; sumar, en su lugar, los cuatro ítems de acceso que quedan afuera con el change que los va a tomar |
| `12_fichas_de_changes.md` | **REWRITE** | Ficha 3c con el alcance firmado y la deuda de su cierre; la deuda del PR #1 (3b-bis, recorrido a 320 px y con teclado sin capturas) se marca saldada cuando la tarea 7.1 la salde |
| `03_actores_y_roles.md` | none | La edición del edificio reusa `configurar_padron` (E9, D5): la matriz de D-106 no cambia y no se toca el dominio `acceso` |
| `08_arquitectura_propuesta.md` | **REWRITE** (§"La web") | L-051: D7 deja de ser sólo el arreglo puntual de tres campos y queda escrita como convención transversal — todo campo con un límite o un patrón lo expresa en una constante, antes de que falle, no sólo en el mensaje de error |
| `CHANGES.md`, `CLAUDE.md`, `AGENTS.md` | **REWRITE** | Estado del 3c; y los hallazgos de QA del 23/10 que hoy viven en `CLAUDE.md`/`AGENTS.md` salen de ahí: los que entran quedan en los specs y los que no, en `10_preguntas_abiertas.md` y en la ficha |
| `15_lecciones.md` | **APPEND** | Lo que enseñe la construcción |
| `01`, `02`, `07`, `08`, `13`, `14`, `16`, `README.md` | none | El 3c no cambia la visión, el stack (el archivo de Georef es un dato, no una dependencia nueva), los flujos de punta a punta, la arquitectura, el motor de reglas, la forma de trabajo ni las fases posteriores |

## Aprobación

Gobernanza HIGH (D-094, D-111). La completa, **a mano**, Juani, Alberto o Emiliano, con nombre, fecha
y alcance. **Ningún agente la escribe.** Cada elección tiene su alternativa descartada y el costo de
revertir en `design.md`.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Sólo Argentina | Sin campo ni selector de país; el archivo de Georef se guarda reducido en `config/georef/` con su `LEEME` (fuente, fecha, licencia CC BY 4.0, comando que lo regenera) y la app nunca consulta Georef en vivo (D1) | Sí |
| E2 · Calle y número | Texto libre, campo nuevo, sin validar contra el dataset de calles de Georef (D1) | Sí |
| E3 · Edificios ya cargados | La ubicación nueva arranca en nulo, la puesta a punto la pide y la pantalla de edición la completa; `complejo.localidad` deja de ser un campo de entrada (D2, Migration Plan) | Sí |
| E4 · Vocabulario de pisos y sus máximos | `PB` siempre; subsuelos y pisos sobre PB con el máximo que fija `design.md` (5 subsuelos `SS1`-`SS5`, 60 pisos sobre PB); los cuatro tipos de unidad eligen de la misma lista (D3) | Sí, con el tope en 60 pisos / 5 subsuelos — generoso para el mercado de Mendoza y barato de mover si hiciera falta (un `CHECK` de una línea) |
| E5 · Migración de `unidad.piso` | Se mapean los valores conocidos (`PB`, `SS`, números) y el resto queda **marcado para corregir**, sin inventar un valor; bajada probada sobre una copia con datos (D3, Migration Plan) | Sí |
| E6 · Grupos y claves | Un grupo parcial se desactiva, nunca se borra (R16), con "Generales" protegido también en la base; la clave de grupos y categorías se autogenera desde el nombre y sale del formulario, y la API sigue aceptándola explícita para la semilla y el importador (D4) | Sí, desactivar siempre — incluso un grupo que nunca tuvo unidades. No se agrega un segundo mecanismo de borrado real: hoy el módulo de gastos (6) no existe, así que "nunca tuvo gastos" no distingue nada todavía; se revisa de nuevo cuando el 6 exista |
| E8 · Lo que no entra | Los cuatro ítems de `acceso` (B-3, menú por rol, reinvitar, `/personal` jerárquica de D-127) van a un change de acceso propio; el 3c se queda en HIGH (P68) | Sí |
| E9 · Permiso de editar el edificio | La elección del `design.md` entre reusar la acción del padrón o crear una acción nueva, y qué roles la tienen (D5) | Sí, reusar `CONFIGURAR_PADRON` — no se toca la matriz D-106, el change se queda en HIGH |
| E10 · Reproducir antes de arreglar B-2 | El error atribuido a "Tasa mensual" se reproduce con un test en rojo antes de tocar código; si el test sale verde, el hallazgo se cierra como "no reproducible" con la evidencia pegada, en vez de arreglar a ciegas (D6) | Sí |

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| Emiliano Caceres | 26/10/2026 | E1 a E6 y E8 a E10 completas, tal como quedaron en esta tabla (E7 no es una elección de este change: la decisión de borrar las cuentas de Mailinator ya está tomada y es acción operativa de Emiliano en Clerk, fuera de alcance de código) |

### E11 · Dueño de las funciones al restaurar (elección nueva, posterior a la firma de Emiliano, L-029)

Problema (ensayo de roles en la integración con el 4b): restaurar un respaldo (`pg_restore --no-owner`)
deja las funciones a nombre del rol de arranque, y la 0027 hace `CREATE OR REPLACE` de
`fn_grupo_generales_protegido`: falla con `must be owner of function`. Decisión: `roles antes`
reasigna también las funciones del esquema `public` al migrador, como ya hace con tablas y
secuencias; `roles despues` devuelve al rol de arranque las funciones de las tablas protegidas
(4a/4b) y el chequeo verifica ese dueño por el efecto. Descartado: (b) que la 0027 cree una función
nueva (arreglo local, el problema vuelve en la próxima migración) y (c) dejarlo como deuda.
Revertir: quitar la reasignación de funciones en `antes` (la de `despues` se conserva).

| Firmante | Fecha | Alcance aprobado |
|---|---|---|
| Juani | 27/10/2026 | E11 tal como está escrita arriba |

### Enmienda E11 · Las funciones protegidas nunca pasan al migrador (RE11-01, RE11-02)

El rompedor mostró que reasignar al migrador TODAS las funciones de `public` en `roles antes` abre una
ventana: mientras dura la migración, el migrador puede reemplazar la función que bloquea una tabla
protegida por una que llama a una auxiliar suya, y después de `roles despues` desactivar el bloqueo
cambiando sólo la auxiliar, con el chequeo de arranque en verde. Corrección: `roles antes` reasigna
al migrador sólo las funciones que NO pertenecen a triggers de las tablas protegidas
(`TABLAS_DE_SOLO_AGREGAR`); las de las tablas protegidas quedan siempre del rol de arranque. Además, el
chequeo verifica que ninguna función de un trigger protegido sea del migrador, en ningún momento.
Reemplaza a "reasigna también las funciones del esquema public" de E11. Descartado: dejar E11 tal como
estaba (rompe la garantía de sólo agregar del 4a/4b).

| Firmante | Fecha | Alcance aprobado |
|---|---|---|
| Juani | 27/10/2026 | Enmienda E11 tal como está escrita arriba |
