## Why

El candado del 2a conoce cuatro roles (titular, colaborador con nivel "ver" o "editar", consejo y
vecino) y la matriz de D-096. Alberto trajo los roles que de verdad usa una administración (super
admin, administrador y contador con alcance "principal" o "por edificio", auxiliar, consejo y el vecino
partido en propietario e inquilino), y Juani los cerró el 20/10/2026 en
`openspec/exploraciones/2026-10-20-roles-de-la-empresa-y-login.md` (puntos 1 a 9). El login con Clerk
(2b) sólo va a conectar una identidad con estas asignaciones: si el modelo de roles no cambia antes,
el 2b se construye sobre una matriz que ya no es la del negocio. Por eso este cambio va **antes del
login** y, como el 2a, se prueba entero sin login, con la identidad inyectada.

Cubre: los puntos 3 a 7 de la exploración (perfil por alcance, la regla de emitir y corregir,
propietario e inquilino como atributo de la relación con la unidad, varios propietarios por unidad, el
inquilino que ve sólo ordinarias) y el mapeo de lo existente. Reemplaza la matriz de **D-096** (P23);
mantiene **D-016**, **D-037** en su forma (404 fuera de alcance, 403 con el permiso faltante),
**D-076** (dos capas), **D-096** P18 (una cuenta por administración), **D-099** (selector) y **D-103**.
Regla **R10**. Historias: ninguna se cierra; prepara HU-V1 (2b), el portal (11) y la vista del consejo
(12). El punto 8 (un barrio con sectores es un solo consorcio) no cambia el modelo; los puntos 1, 2 y 9
(Clerk, contraseña del vecino, aviso de privacidad) son del 2b.

## Gobernanza

**Nivel CRITICAL** (D-094 y la ficha 2): es el candado. Un error acá no rompe una pantalla: le da a un
auxiliar o a un inquilino una acción que no le toca, o a una persona por edificio el alcance de toda
la empresa. Además migra filas de `asignacion_rol` con datos de todas las administraciones.

**Se propone y se espera la aprobación escrita y fechada de uno de los dos socios (Juani o Alberto)
antes de construir** (D-094). El constructor no arranca hasta que la sección "Aprobación", al final
de este archivo, tenga el nombre, la fecha y el alcance aprobado escritos por uno de los dos. Ningún
agente completa esa sección. La aprobación incluye las elecciones de diseño E1 a E8: un socio puede
aprobar el cambio y rechazar una de ellas, y entonces el design se corrige antes de construir.

## What Changes

- **Siete perfiles con alcance** (punto 3): super admin (toda la empresa), administrador y contador
  (principal o por edificio), auxiliar y consejo (por edificio), vecino propietario y vecino inquilino
  (por unidad). "Principal" sigue siendo `complejo_id IS NULL`, como el titular de hoy.
- **`asignacion_rol` cambia de forma** (E1, E2): `rol` pasa a `super_admin | administrador | contador
  | auxiliar | consejo | vecino`; se borra `nivel`; se suma `vinculo` (`propietario | inquilino`),
  obligatorio en el vecino y prohibido en el resto; una persona tiene a lo sumo una relación con cada
  unidad. **BREAKING** para todo `INSERT` que use el vocabulario viejo.
- **Migración `0017_roles_de_la_empresa`** que convierte las filas existentes de todas las
  administraciones: titular → super admin; colaborador "editar" → administrador por edificio;
  colaborador "ver" → auxiliar; consejo → consejo; vecino → vecino propietario (E7). Su `downgrade`
  vuelve a la forma de 0016 y **falla ruidoso, sin tocar nada**, si hay filas sin forma vieja: un
  contador, un administrador principal o un vecino inquilino.
- **La matriz nueva** (D-106 propuesta, celda por celda en `design.md`), con la regla de emitir y
  corregir (punto 4): emite el super admin y todo administrador con alcance sobre ese edificio; anular,
  revertir o reimputar pagos, condonar, dar de baja deuda y aceptar alertas bloqueantes, sólo el super
  admin y el administrador principal. Contador, auxiliar y consejo no tienen ninguna acción de
  escritura. Las 16 acciones de `Accion` se quedan con su nombre: no hay vocabulario de auditoría nuevo.
- **El inquilino ve sólo ordinarias** (punto 7): se declara en la spec y se construye ahora sólo el
  atributo y la distinción en el dominio. La lectura de expensas ordinarias y extraordinarias no existe
  todavía (llega con gastos y liquidación, cambios 6 y 7): la regla queda escrita para ellos.
- **El endpoint de asignación** (`POST /api/complejos/{id}/asignaciones`) acepta los perfiles por
  edificio (`administrador | contador | auxiliar | consejo`) y deja de aceptar `nivel` (**BREAKING**,
  422). Sólo lo usa el super admin.
- **La web**: los dos textos de 403 que nombran al "titular de la administración" pasan a nombrar al
  super admin (E8).
- **Lo que no cambia, a propósito**: las políticas de RLS (la base sigue asegurando la administración y
  el alcance por edificio sigue en la aplicación, E2 del 2a), los roles de PostgreSQL, la auditoría y
  sus filas históricas, las fronteras entre módulos.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `autorizacion-por-rol`: perfil por alcance en vez de rol y nivel; la forma de cada asignación; el
  alcance de "principal"; la matriz nueva; propietario e inquilino; la conversión de las asignaciones
  existentes y su vuelta atrás.
- `configuracion-versionada`: crear una versión de configuración deja de ser sólo del titular (E3).
- `edificios-y-unidades`: quién confirma "sin saldos previos" (E4) y la lista de edificios de una
  persona con alcance principal.
- `pantallas-del-edificio`: el estado "sin permiso" nombra al super admin.

## Que intente romper el rompedor

- **La migración que no migra en silencio**: `asignacion_rol` tiene RLS forzada y el migrador no tiene
  `BYPASSRLS` (E1 del 2a). Un `UPDATE` sin tenant toca cero filas y termina con `exit 0`. Que una
  administración quede con el vocabulario viejo, que el `FORCE` no vuelva, que un error a mitad de la
  migración deje la tabla sin `FORCE`.
- **Un alcance principal regalado**: una fila de auxiliar, consejo o vecino con `complejo_id` nulo; un
  administrador por edificio que alcance otro edificio; un contador principal que pueda escribir.
- **La regla de corregir**: un administrador por edificio que anule, revierta, condone, dé de baja o
  acepte una alerta bloqueante en su propio edificio; la misma acción con dos asignaciones (por edificio
  en A y principal en ninguno).
- **Propietario e inquilino**: un vecino sin `vinculo`, un `vinculo` en una fila de personal, la misma
  persona propietaria e inquilina de la misma unidad, un inquilino que vea la unidad de otro.
- **El `downgrade`**: que convierta un contador o un inquilino en algo con más permiso en vez de fallar;
  que falle a medias; que su mensaje traiga un nombre o un email.
- **El cuerpo del endpoint**: `nivel`, `vinculo`, `unidad_id`, `rol: "super_admin"` o `rol: "vecino"`
  tienen que dar 422 nombrando el campo, nunca 500.
- **El código que todavía habla del titular**: un `Rol.TITULAR` o un `'colaborador'` que quede en un
  camino real, o un comentario que siga describiendo la matriz vieja.

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-028). Detalle en `design.md` ("Cómo aplica
cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-003 · contar los tests | 1.1 y 7.2 |
| L-005 · verde es todo el workflow | convención de `tasks.md` y 7.2 |
| L-010 · la corrida de cierre va al final | 7.2 |
| L-012 · la deuda al primer cambio que usa la pieza | 4.2 (R5 del 2a, el cuerpo del endpoint que este cambio reescribe) |
| L-013 · mutar sin commit exige copia | convención de `tasks.md`, 3.1, 3.3 y 4.1 |
| L-016 · una observación tiene que poder dar otro resultado | 3.1 a 3.3, 4.1 y 4.3 (como `proptech_app`, con filas en dos administraciones) |
| L-017 · la entrada del escenario | 4.2 y 4.3 (ids válidos y existentes de otro edificio y de otra administración) |
| L-018 · verificar el efecto, no la forma | 3.2 (el `CHECK` se prueba insertando, no leyendo el catálogo) y 3.1 (el `FORCE` se prueba leyendo como la app) |
| L-019 · un test que no puede dar rojo | 2.2 (la matriz escrita a mano, no generada) y cada RED de `tasks.md` |
| L-020 · arreglar un bloqueante puede crear otro | 3.1 (el `NO FORCE` temporal tiene su propio ataque: una migración que falla a mitad) |
| L-022 · comparar el conjunto, no un resumen | 2.2 (las 144 celdas, no un conteo) y 6.1 (el barrido de vocabulario con la lista completa) |
| L-023 · NOT NULL o CHECK rompe fuera de `backend/` | 3.4 (todo `INSERT` a `asignacion_rol` del repositorio entero) |

L-001, L-002, L-006 a L-009, L-011, L-014, L-015, L-021 y L-024 a L-028 no aplican: no hay
dependencias nuevas, configuración, comandos destructivos, gemelos de API y worker, Bash nuevo ni
pantallas nuevas; las dos frases de la web no cambian ninguna combinación de capas.

## Fuera del cambio

- **El login** y todo lo de Clerk (2b): autenticación, contraseña del vecino, link mágico, aviso de
  privacidad, vincular `persona` con el id de Clerk, el selector de D-099.
- **Leer expensas ordinarias y extraordinarias**: la regla del inquilino se construye con gastos y
  liquidación (6 y 7); acá sólo queda escrita.
- **Exportar** (el contador, "luego exportar") y cualquier acción de lectura contable nueva: nacen con
  los módulos que tienen algo que leer (6, 7, 10a, 12).
- **Gestionar usuarios**: invitar personas, dar perfiles con alcance principal o por unidad. Hoy sólo
  existe la asignación por edificio; ver la pregunta abierta en `design.md`.
- **Políticas de base por persona o por edificio** (revertir E2 del 2a): sigue la decisión del 2a.
- **El acceso de desarrollo** (`acceso-de-desarrollo`, en curso y sin firmar): no se toca acá; ver la
  pregunta abierta sobre el orden.

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 20/10/2026): `01_vision_y_objetivos.md`,
`02_descripcion_general.md`, `03_actores_y_roles.md`, `04_modelo_de_datos.md`,
`05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`,
`08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`,
`11_glosario.md`, `12_fichas_de_changes.md`, `13_motor_de_reglas.md`, `14_forma_de_trabajo.md`,
`15_lecciones.md`, `16_proyecto_final.md`, `README.md`. Este propose no edita ninguno: lo hace quien
archiva, salvo que Juani prefiera registrar D-106 al firmar.

- `09_decisiones_y_supuestos.md`: **APPEND**. D-106, la decisión del 20/10/2026 (puntos 1 a 9 de la
  exploración) con la matriz nueva que **reemplaza la de D-096** (P23) y el método de login que
  **reemplaza el de D-097**; D-096 y D-097 llevan la marca "corregida en parte por D-106" en el título.
  Al archivar, las elecciones E1 a E8 tal como las firme el socio.
- `12_fichas_de_changes.md`: **REWRITE**. Ficha nueva para este cambio (entre 2a y 2b); la ficha 2b
  ajustada a Clerk (sólo autenticación, contraseña también para el vecino, vincular por el id de Clerk,
  aviso de privacidad); las fichas 6, 7, 11 y 12 con la regla del inquilino y las lecturas del contador
  y el consejo; la ficha 3b-bis si cambia el orden; la fila R5 de "Deuda del cierre del 2a" según cierre
  la tarea 4.2.
- `03_actores_y_roles.md`: **REWRITE** de "Los cuatro roles del MVP" y de la matriz RBAC.
- `04_modelo_de_datos.md`: **REWRITE** de `asignacion_rol` (columnas, `CHECK`, índice único del vecino)
  y de la descripción de `persona`.
- `11_glosario.md`: **REWRITE** de "Administrador titular" y "Colaborador" (pasan a super admin,
  administrador, contador y auxiliar, con alcance), "Vecino" (propietario o inquilino de una unidad) y
  una nota de que "titular", en specs y decisiones anteriores al 20/10/2026, es el super admin.
- `05_reglas_de_negocio.md`: **REWRITE** sólo si alguna regla nombra al titular o al colaborador como
  dueño de una acción (R41 lo hace): se cambia el actor, no la regla.
- `06_funcionalidades.md` y `07_flujos_principales.md`: **REWRITE** de los actores donde digan titular o
  colaborador; ninguna historia cambia de alcance.
- `10_preguntas_abiertas.md`: **REWRITE**. P12 se cierra para la autenticación (punto 9); se suman las
  preguntas abiertas de `design.md` que Juani no responda al firmar.
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar.
- `01`, `02`, `08`, `13`, `14`, `16` y `README.md`: none. No cambian la visión, el stack, la
  arquitectura, el motor de reglas, el método ni el proyecto final.
- Fuera de `knowledge-base/`: `CHANGES.md` (**REWRITE**, fila nueva antes de C-05b) y `CLAUDE.md`/
  `AGENTS.md` si nombran los roles (**REWRITE**).

## Impact

- **Backend**: `proptech_core/acceso/dominio/permisos.py` (perfiles, alcance, matriz, `puede`,
  `alcanza`), `acceso/aplicacion/autorizacion.py` (`cargar_asignaciones` con `vinculo`),
  `complejos/aplicacion/escritura.py` (asignar sin `nivel`), `proptech_api/complejos.py` (cuerpo de la
  asignación); migración nueva `0017_roles_de_la_empresa.py`.
- **Tests**: unos 21 archivos usan el vocabulario viejo (`backend/tests/unitarios/acceso/` y
  `backend/tests/integracion/`, incluido `conftest.py`).
- **Web**: `web/src/componentes/Estados.tsx`, `web/src/app/edificios/acciones.ts` y sus tests.
- **Contrato de la API**: el cuerpo de `POST /api/complejos/{id}/asignaciones` (**BREAKING**). Hasta el
  2b todo endpoint responde 401 en producción, así que nadie lo llama hoy.
- **Datos**: la migración reescribe las filas de `asignacion_rol` de todas las administraciones. Hoy no
  hay datos reales (no hubo piloto).
- **Dependencias nuevas**: ninguna. **Infra**: ninguna.

## Aprobación

Gobernanza CRITICAL (D-094). La completa, a mano, uno de los dos socios. Ningún agente la escribe.

Elecciones de diseño (detalle en `design.md`). Los puntos 1 a 9 de la exploración ya los decidió Juani
el 20/10/2026; estas son las elecciones que la exploración no fijó, más una (E3) que contradice una
spec vigente.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · Perfil y alcance en `asignacion_rol` | `rol` con seis valores, el alcance se deduce de `complejo_id` y `unidad_id` (sin columna `alcance`), `nivel` se borra (D1) | |
| E2 · Propietario o inquilino | Columna `vinculo` en la fila del vecino, una relación por persona y unidad (D2) | |
| E3 · Configuración versionada | Crear una versión de intereses y vencimiento la puede el super admin y **todo administrador** del edificio; hoy es sólo del titular (punto 3: "configuración") (D4) | |
| E4 · Confirmar "sin saldos previos" | Super admin y administrador principal, como dar de baja una deuda (D4) | |
| E5 · Crear edificios y asignar | Sólo el super admin (punto 3: "edificios, usuarios y roles") (D4) | |
| E6 · Lectura de la configuración | Contador, auxiliar y consejo leen la configuración del edificio de su alcance (D4) | |
| E7 · Filas existentes y vuelta atrás | El vecino de hoy pasa a propietario; el `downgrade` falla ruidoso con un contador, un administrador principal o un inquilino (D5) | |
| E8 · Texto de la web | "Esto lo puede hacer el super admin de la empresa." (D8) | |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
