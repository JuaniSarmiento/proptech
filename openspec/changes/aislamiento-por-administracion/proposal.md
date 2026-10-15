## Why

Hasta hoy la base de PropTech no tiene ningún candado: un solo rol de PostgreSQL, que nace
superusuario, lo comparten Alembic, la API, el worker y los respaldos, y no hay una sola tabla con
datos de una administración. Antes de que el cambio 3 cargue el primer edificio, cada dato tiene que
pertenecer a una administración y la base tiene que negarse a mostrarlo a otra **aunque el código
tenga un error**: ese es el objetivo de la ficha 2 y la regla **R10**.

Es el cambio **2a**, la primera mitad del cambio 2 `acceso-y-aislamiento`, partido en dos por
**D-097** a partir del explore del 15/10/2026 (`openspec/exploraciones/2026-10-15-acceso-y-aislamiento.md`,
sección 7): el **2a es el candado** (roles de base, Row-Level Security, alcance, permisos y
auditoría) y se prueba entero sin login, con la identidad inyectada en los tests; el **2b es el
login** (contraseña para el personal, link mágico para el vecino, D-097), que depende de este.

Cubre: **R10** (aislamiento entre administraciones y alcance por edificio, con sus tests mínimos);
**D-016** (la administración sale de la identidad, nunca del cliente; auditoría de acciones
sensibles), **D-037** (cuatro roles, 404 fuera de alcance, 403 con el permiso faltante), **D-076**
(dos capas: administración y edificio), **D-082** (tablas mínimas), **D-087** (el plan de RLS de la
ficha 2), **D-091** (M12 y el tenant del worker, deuda del 1c), **D-095** (deuda del 1d), **D-096**
(una cuenta por administración y la matriz de permisos por acción) y **D-097** (la partición).
Historias: ninguna se cierra acá; HU-V1 (la entrada del vecino) es del 2b.

## Gobernanza

**Nivel CRITICAL** (D-094 y la ficha 2): es el control de acceso a los datos de todas las
administraciones. Un error acá no rompe una pantalla: muestra la deuda de un vecino a otra
administración. Además toca roles de la base, la configuración de credenciales de los cinco servicios
que hablan con PostgreSQL y la red de los contenedores.

**Se propone y se espera la aprobación escrita y fechada de uno de los dos socios (Juani o Alberto)
antes de construir** (D-094). El constructor no arranca hasta que la sección "Aprobación", al final
de este archivo, tenga el nombre, la fecha y el alcance aprobado escritos por uno de los dos. Ningún
agente completa esa sección. La aprobación incluye además las tres elecciones de diseño que el explore
dejó abiertas sin bloquear (ver "Aprobación"): un socio puede aprobar el cambio y rechazar una de
ellas, y entonces el design se corrige antes de construir.

## What Changes

- **Tres roles de PostgreSQL con un trabajo cada uno**: el rol de arranque del contenedor
  (`POSTGRES_USER`, superusuario) queda sólo para crear los otros dos y para los respaldos;
  `proptech_migrador` es dueño de las tablas y corre Alembic, sin superusuario ni `BYPASSRLS`;
  `proptech_app` lo usan la API y el worker, sin superusuario, sin `BYPASSRLS` y sin ser dueño de
  nada. La API y el worker **no reciben** la contraseña del rol de arranque.
- **Configuración con un par de credenciales por rol**, y la URL de la base como objeto
  `sqlalchemy.engine.URL` renderizado sólo en el borde (cierra M12, deuda del 1c).
- **Tablas mínimas** (D-082): `administracion`, `complejo`, `unidad`, `persona` (email único por
  administración, D-096) y `asignacion_rol`, todas con `administracion_id NOT NULL`, claves foráneas
  compuestas que impiden colgar una fila de otra administración, RLS activada y **forzada**, y una
  política de lectura y escritura contra `nullif(current_setting('app.administracion_id', true), '')::uuid`.
- **El tenant por transacción**: una `ContextVar` fijada desde la identidad y un evento `after_begin`
  que hace `set_config('app.administracion_id', ..., true)` (equivale a `SET LOCAL`). Sin identidad,
  ninguna consulta corre; sin valor fijado, cero filas, nunca un error.
- **Identidad inyectable**: una dependencia `identidad_actual` que en producción, hasta el 2b,
  responde siempre 401 sin tocar la base; los tests la reemplazan. La sesión de base depende
  explícitamente de ella, así ninguna consulta corre antes de fijar el tenant.
- **Autorización**: la matriz de D-096 como función pura del dominio `acceso`; alcance por edificio
  por rol (404 fuera de alcance, idéntico a "no existe"); permiso por acción (403 con el permiso
  faltante). Tres endpoints mínimos para probarlo: ver un complejo, ver una unidad y asignar un
  edificio (la única acción de la matriz que es del módulo `acceso`).
- **Auditoría** (D-016): tabla `auditoria` con RLS, vocabulario cerrado de acciones, detalle con
  claves permitidas y sin datos sensibles, `request_id`; sólo se agrega (ni el dueño la edita) y se
  escribe en la misma transacción que la acción, con un helper que reusan los cambios 7, 8 y 10b.
- **El worker con tenant**: toda tarea que toque datos de una administración recibe
  `administracion_id` como argumento validado; sin él, falla cerrada sin reintentar.
- **Respaldos completos**: `respaldos` sigue con el rol de arranque, y el humo verifica que el
  volcado restaurado trae las filas de todas las administraciones.
- **Endurecimiento de infraestructura** (deuda con dueño "2"): cabeceras de seguridad en Caddy,
  sin `Via` ni `X-Powered-By`, respuestas a HEAD revisadas, volúmenes de Caddy, la web fuera de la
  red de la base, contenedores sin privilegios nuevos ni capacidades de más y PID 1 no root probado
  servicio por servicio, CI también en los pull requests con límite de tiempo y gitleaks fijado por
  digest, tabla de variables del README, y el humo con el resto de F7 y las dos dependencias
  congeladas a la vez.

## Capabilities

### New Capabilities

- `aislamiento-por-administracion`: roles de la base, tablas con `administracion_id`, RLS forzada,
  el tenant fijado por transacción y qué pasa cuando falta.
- `autorizacion-por-rol`: identidad inyectada, alcance por edificio (404), permiso por acción según
  D-096 (403) y el orden entre los dos.
- `auditoria-de-acciones`: qué se registra, en qué transacción, con qué datos y quién no la puede
  editar ni borrar.

### Modified Capabilities

- `entorno-de-ejecucion`: credenciales por rol, la web fuera de la red de la base, cabeceras del
  proxy y contenedores endurecidos.
- `cola-de-trabajos`: las tareas con datos de una administración llevan el tenant validado.
- `respaldos-de-la-base`: el volcado se hace con un rol que ve todas las administraciones.
- `integracion-continua`: CI en pull requests con límite de tiempo, gitleaks por digest y el humo con
  roles, cabeceras, backup completo, el resto de F7 y la doble congelada.

## Que intente romper el rompedor

Además de lo que ya pide la ficha 2 (ver un edificio de otra administración tipeando la URL, un `SET`
sin `LOCAL` que contagie al pedido siguiente, un colaborador en un edificio no asignado, un vecino
en la unidad de otro):

- **Fuga entre administraciones por un `SET LOCAL` que no se aplicó**: una sesión que se abre antes
  de fijar el tenant, una conexión del pool que vuelve con el valor de la transacción anterior, un
  `commit` a mitad de pedido que abre otra transacción sin el evento, un hilo (L-015) que pierde la
  `ContextVar`.
- **`current_setting` sin `missing_ok`**, o sin `nullif` antes de castear a `uuid`: tenant ausente y
  tenant vacío tienen que dar lo mismo (cero filas), nunca un 500 en un caso y cero filas en el otro.
  Que una migración futura agregue una política escrita a mano sin el segundo argumento.
- **Un rol con `BYPASSRLS` o superusuario usado por la app**: la API o el worker conectándose como
  el rol de arranque o como el migrador; un `.env` que reusa la misma contraseña; el rol de la app
  dueño de una tabla (el dueño sin `FORCE` saltea la política).
- **Backups incompletos en silencio por usar el rol equivocado**: `respaldos` con `proptech_app`
  devolvería un volcado vacío o de una sola administración que igual se restaura sin error.
- **404 versus 403 filtrando existencia**: un complejo de otra administración y uno que no existe
  tienen que responder igual (código, cuerpo y encabezados salvo el `request_id`); un 403 sólo puede
  aparecer dentro del alcance; un id con formato válido de otra administración (L-017), no uno
  malformado que ya rechaza otra capa.
- **La auditoría que se pueda saltear o editar**: una acción sensible que confirma sin su fila, una
  fila que queda aunque la acción se revierta, un `UPDATE`, `DELETE` o `TRUNCATE` sobre `auditoria`
  (como app y como migrador), una acción fuera del vocabulario, un dato sensible en el detalle.
- **El worker sin tenant**: un trabajo encolado antes de este cambio, uno armado a mano sin
  `administracion_id`, con uno vacío, malformado o de tipo equivocado; dos tareas seguidas en el mismo
  worker donde la segunda hereda el tenant de la primera.
- **El `GRANT` olvidado**: una tabla nueva sin permisos para `proptech_app` o sin RLS forzada.

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-017). Detalle en `design.md` ("Cómo aplica
cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-001 · dependencia que no responde | 9.2 (base y Redis congeladas a la vez) |
| L-002 · configuración rota de muchas formas | 2.1 (cada par de credenciales: faltante, vacío, en blanco) |
| L-003 · contar los tests | 1.1 y 11.1 |
| L-004 · otro camino | design.md: los tests de integración entran por la sesión; el humo, por el proxy y por `psql`; el rompedor, por un tercero (pool, hilos, catálogo) |
| L-005 · verde es todo el workflow | convención de `tasks.md`, 8.3 y 11.1 |
| L-006 · lo destructivo apunta a `proptech` | 2.2 (el arranque de roles sólo toca los dos roles del proyecto), 9.1 (la restauración en `proptech_restauracion`) |
| L-007 · el error de una librería es una salida | 2.1 y 2.2 (ninguna contraseña en errores ni logs), 6.2 (el detalle de auditoría sin datos sensibles), 7.1 (el valor rechazado no se loguea) |
| L-008 · coincidencia completa y sólo ASCII | 2.1 (nombres de rol), 7.1 (el `administracion_id` de una tarea) |
| L-009 · el arreglo se prueba en el gemelo | 4.1 y 7.1 (el tenant en la API y en el worker con la misma batería), 2.1 (las dos clases de configuración) |
| L-010 · la corrida de cierre va al final | 11.1 |
| L-011 · un plazo no cancela la transacción | 6.2 (la auditoría y el efecto se confirman o se revierten juntos, del lado de la base) |
| L-012 · la deuda al primer cambio que usa la pieza | design.md ("Deuda que recibe este cambio" y el reparto con el 2b) |
| L-013 · mutar sin commit exige copia | convención de `tasks.md`, 3.2 y 8.2 |
| L-014 · `set -e` dentro de `||` | 9.2 (cada paso del humo con su chequeo explícito) |
| L-015 · hilos y `ContextVar` | 4.1 y 7.1 (el tenant llega a cada hilo con su propia copia de contexto) |
| L-016 · una observación tiene que poder dar otro resultado | 8.2 (PID 1 no root con el rojo visto en cada servicio), 9.1 (el conteo de filas por administración) |
| L-017 · la entrada del escenario | 3.1, 5.2 y 5.3 (ids con formato válido de otra administración) |

## Fuera del cambio

- **El login en sí** (2b, D-097): formulario y sesión del personal con contraseña, link mágico del
  vecino, envío del mail que necesita el link, límite de intentos en Redis, auditoría de login
  exitoso y fallido, CSP en Next y la pantalla de login. Bloqueado por **P48** (a qué administración
  entra un email que tiene cuenta en dos).
- **Las acciones sensibles de otros módulos** (emitir, confirmar o revertir pagos, condonar, dar de
  baja): se auditan con el helper de este cambio cuando existan (7, 8, 10b).
- **Quién lee la auditoría**: este cambio no expone ningún endpoint para leerla.
- **Dependabot**: no lo necesita el candado ni el login; pasa al cambio 15, junto con las imágenes
  fijadas por digest que Dependabot mantendría (L-012). Lo confirma el socio que apruebe.
- **Configuración completa del edificio** (3): las tablas mínimas sólo tienen lo que el acceso
  necesita.
- **Unificar cuentas de dos administraciones** (v1.1, D-096).
- **Pantallas** del portal (11) y del consejo (12).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 15/10/2026): `01_vision_y_objetivos.md`,
`02_descripcion_general.md`, `03_actores_y_roles.md`, `04_modelo_de_datos.md`,
`05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`,
`08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`,
`11_glosario.md`, `12_fichas_de_changes.md`, `13_motor_de_reglas.md`, `14_forma_de_trabajo.md`,
`15_lecciones.md`, `16_proyecto_final.md`, `README.md`.

- `09_decisiones_y_supuestos.md`: **APPEND**. Ya se agregó D-097 (la partición y el login) en este
  propose. Al archivar, una decisión con las elecciones de código del 2a (roles, política, tablas,
  auditoría, tenant del worker) y las tres elecciones de la sección "Aprobación" tal como las firme
  el socio.
- `12_fichas_de_changes.md`: **REWRITE** de la ficha 2 (partida en 2a y 2b en este propose; al
  archivar, cierre y tareas del 2a) y de las filas de deuda que este cambio resuelve en las tres
  tablas de deuda.
- `04_modelo_de_datos.md`: **REWRITE** de `administracion`, `complejo`, `unidad`, `persona` y
  `asignacion_rol` de "planificada" a existentes con sus columnas mínimas, y `auditoria` nueva.
- `03_actores_y_roles.md`: **REWRITE** de "Rutas públicas" (los tres endpoints nuevos exigen
  identidad) y de la mención de las capas como planificadas.
- `08_arquitectura_propuesta.md`: **REWRITE** de la tabla de variables (credenciales por rol) y de
  la sección de seguridad (redes, cabeceras, roles).
- `02_descripcion_general.md`: **REWRITE** del estado de la arquitectura (RLS vigente, roles).
- `10_preguntas_abiertas.md`: **REWRITE**. Ya se agregó P48 en este propose; al archivar, nada salvo
  que el constructor encuentre otra.
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar; lo escribe quien archiva.
- `05_reglas_de_negocio.md`: none. R10 no cambia: este cambio la cumple.
- `01`, `06`, `07`, `11`, `13`, `14`, `16` y `README.md`: none. No cambian objetivos, historias,
  flujos, glosario, motor, forma de trabajo ni fases.
- Fuera de `knowledge-base/`: `CHANGES.md` (**REWRITE** de C-05, ya partido en este propose) y
  `CLAUDE.md`/`AGENTS.md` (**REWRITE** de "Estado" y "Próximo", ya hecho en este propose; al archivar,
  marcar el 2a).

## Impact

- **Backend**: `proptech_core/compartido/configuracion.py`, `base_de_datos.py`, un módulo nuevo de
  arranque de roles y otro de auditoría; `proptech_core/acceso/` y `proptech_core/complejos/` con
  dominio, aplicación y adaptadores mínimos; `proptech_api` con la identidad, la sesión con tenant y
  tres endpoints; `proptech_worker` con el decorador de tenant; `migraciones/env.py` y las
  migraciones 0003 (tablas mínimas y RLS) y 0004 (auditoría).
- **Infra**: `infra/compose.yaml`, `infra/Caddyfile`, `infra/.env.example`, `infra/ci/humo.sh`,
  `.github/workflows/ci.yml`, `web/next.config.*`, `README.md`.
- **Configuración nueva**: `POSTGRES_MIGRADOR_USER`, `POSTGRES_MIGRADOR_PASSWORD`,
  `POSTGRES_APP_USER`, `POSTGRES_APP_PASSWORD`.
- **Contrato de la API**: tres endpoints nuevos, que hasta el 2b responden 401 en producción.
- **Dependencias nuevas**: ninguna.

## Aprobación

Gobernanza CRITICAL (D-094). La completa, a mano, uno de los dos socios. Ningún agente la escribe.

Elecciones de diseño que el explore dejó abiertas y este propose resuelve (detalle en `design.md`).
El socio marca cada una como aprobada o rechazada:

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · `proptech_migrador` con o sin `BYPASSRLS` | **Sin** `BYPASSRLS`; una migración que siembre datos fija su propio `SET LOCAL` (D2) | |
| E2 · Alcance por edificio en la base o en la aplicación | **En la aplicación**, con tests por rol; la base asegura sólo la administración (D6) | |
| E3 · `trabajos_hechos` con o sin `administracion_id` | **Sin**: es técnica, no guarda datos de una administración (D8) | |
| E4 · Dependabot fuera del 2a | Pasa al cambio 15 | |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
