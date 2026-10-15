## Why

Hasta hoy la base de PropTech no tiene ningún candado: un solo rol de PostgreSQL, que nace
superusuario, lo comparten Alembic, la API, el worker y los respaldos, y no hay una sola tabla con
datos de una administración. Antes de que el cambio 3 cargue el primer edificio, cada dato tiene que
pertenecer a una administración y la base tiene que negarse a mostrarlo a otra **aunque el código
tenga un error**: ese es el objetivo de la ficha 2 y la regla **R10**.

Es el cambio **2a**, la primera parte del cambio 2 `acceso-y-aislamiento`, partido en tres por
**D-097** a partir del explore del 15/10/2026 (`openspec/exploraciones/2026-10-15-acceso-y-aislamiento.md`,
sección 7) y de la revisión del arquitecto del mismo día: el **2a es el candado** (roles de base,
Row-Level Security, alcance, permisos y auditoría) y se prueba entero sin login, con la identidad
inyectada en los tests; el **2b es el login** (contraseña para el personal, link mágico para el
vecino); el **2c** (`endurecimiento-de-infraestructura`, MEDIUM) se lleva la deuda de
infraestructura que el candado no necesita.

Cubre: **R10** (aislamiento entre administraciones y alcance por edificio, con sus tests mínimos);
**D-016** (la administración sale de la identidad, nunca del cliente; auditoría de acciones
sensibles), **D-021** (los módulos se hablan por `aplicacion`), **D-037** (cuatro roles, 404 fuera de
alcance, 403 con el permiso faltante), **D-076** (dos capas: administración y edificio), **D-082**
(tablas mínimas), **D-087** (el plan de RLS de la ficha 2, con el apartamiento de E5), **D-091** (M12 y
el tenant del worker, deuda del 1c), **D-096** (una cuenta por administración y la matriz de permisos
por acción) y **D-097** (la partición). Historias: ninguna se cierra acá; HU-V1 (la entrada del vecino)
es del 2b.

## Gobernanza

**Nivel CRITICAL** (D-094 y la ficha 2): es el control de acceso a los datos de todas las
administraciones. Un error acá no rompe una pantalla: muestra la deuda de un vecino a otra
administración o a otro vecino. Además toca los roles de la base y las credenciales de los cinco
servicios que hablan con PostgreSQL.

**Se propone y se espera la aprobación escrita y fechada de uno de los dos socios (Juani o Alberto)
antes de construir** (D-094). El constructor no arranca hasta que la sección "Aprobación", al final
de este archivo, tenga el nombre, la fecha y el alcance aprobado escritos por uno de los dos. Ningún
agente completa esa sección. La aprobación incluye además las elecciones de diseño E1 a E5: un socio
puede aprobar el cambio y rechazar una de ellas, y entonces el design se corrige antes de construir.

## What Changes

- **Cuatro roles de PostgreSQL con un trabajo cada uno** (D1): el rol de arranque del contenedor
  (superusuario) sólo crea y repara los otros y es dueño de la auditoría; `proptech_migrador` es dueño
  de las tablas de dominio y corre Alembic; `proptech_app` lo usan la API y el worker, sin
  superusuario, sin `BYPASSRLS` y sin ser dueño de nada; `proptech_respaldo`, sin superusuario, con
  `BYPASSRLS` y `pg_read_all_data`, sólo para `pg_dump`. Ningún servicio permanente tiene la contraseña
  del rol de arranque.
- **Configuración con un par de credenciales por rol**, y la URL de la base como objeto
  `sqlalchemy.engine.URL` renderizado sólo en el borde (cierra M12, deuda del 1c).
- **Tablas mínimas** (D-082): `administracion`, `complejo`, `unidad`, `persona` (email único por
  administración, D-096) y `asignacion_rol`, todas con `administracion_id NOT NULL`, claves foráneas
  compuestas que impiden colgar una fila de otra administración o de otro edificio, RLS activada y
  **forzada**, y una política de lectura y escritura contra
  `nullif(current_setting('app.administracion_id', true), '')::uuid`.
- **El tenant viaja en la sesión** (`session.info`) y un evento `after_begin` lo fija con
  `set_config('app.administracion_id', ..., true)` (equivale a `SET LOCAL`) en cada transacción. Sin
  identidad, ninguna consulta corre; sin valor fijado, cero filas, nunca un error.
- **Identidad inyectable**: una dependencia `identidad_actual` que en producción, hasta el 2b, responde
  siempre 401 sin tocar la base; los tests la reemplazan.
- **Autorización** en el módulo `acceso`: la matriz de D-096 como función pura; alcance por edificio
  por rol (404, idéntico a "no existe"); permiso por acción (403 con el permiso faltante). Tres
  endpoints mínimos: ver un complejo, ver una unidad y asignar un edificio.
- **Auditoría** (D-016) en `acceso.aplicacion`: tabla `auditoria` con RLS, del rol de arranque (así ni
  el migrador puede tocar su trigger), vocabulario cerrado que es el mismo `Accion` de la matriz,
  detalle con claves permitidas y `request_id`; sólo se agrega y se escribe en la misma transacción
  que la acción. La reusan los cambios 7, 8 y 10b.
- **El worker con tenant**: toda tarea que toque datos de una administración recibe
  `administracion_id` como argumento validado; sin él, falla cerrada sin reintentar.
- **Respaldos completos sin superusuario**: `respaldos` pasa a `proptech_respaldo`; nadie usa
  `--enable-row-security`; el humo verifica que un volcado restaurado trae todas las administraciones.
- **La web fuera de la red de la base** (D-051): la web no alcanza `db` ni `redis`.

## Capabilities

### New Capabilities

- `aislamiento-por-administracion`: roles de la base, tablas con `administracion_id`, RLS forzada,
  el tenant fijado por transacción y qué pasa cuando falta.
- `autorizacion-por-rol`: identidad inyectada, alcance por edificio (404), permiso por acción según
  D-096 (403) y el orden entre los dos.
- `auditoria-de-acciones`: qué se registra, en qué transacción, con qué datos y quién no la puede
  editar ni borrar.

### Modified Capabilities

- `entorno-de-ejecucion`: credenciales por rol y la web fuera de la red de la base.
- `cola-de-trabajos`: las tareas con datos de una administración llevan el tenant validado.
- `respaldos-de-la-base`: el volcado se hace con un rol que ve todas las administraciones y no es
  superusuario.
- `integracion-continua`: el humo verifica el rol de la app y un backup completo.

## Que intente romper el rompedor

Además de lo que ya pide la ficha 2 (ver un edificio de otra administración tipeando la URL, un `SET`
sin `LOCAL` que contagie al pedido siguiente, un colaborador en un edificio no asignado, un vecino
en la unidad de otro):

- **Fuga entre administraciones por un `SET LOCAL` que no se aplicó**: una sesión abierta sin el
  tenant en `session.info`, una conexión del pool que vuelve con el valor de la transacción anterior,
  un `commit` a mitad de pedido que abre otra transacción, una consulta hecha en otro hilo.
- **`current_setting` sin `missing_ok`**, o sin `nullif` antes de castear a `uuid`: tenant ausente y
  tenant vacío tienen que dar lo mismo (cero filas), nunca un 500 en un caso y cero filas en el otro.
  Que una migración futura agregue una política escrita a mano sin el segundo argumento.
- **Un rol con `BYPASSRLS` o superusuario usado por la app**: la API o el worker conectándose como el
  rol de arranque, el migrador o el de respaldo; un `.env` que reusa la misma contraseña; el rol de la
  app dueño de una tabla.
- **Backups incompletos en silencio por usar el rol equivocado**: `respaldos` con `proptech_app` falla
  ruidoso; con `--enable-row-security` sale vacío y en silencio. Que alguien sume esa opción.
- **404 versus 403 filtrando existencia**: un complejo de otra administración y uno que no existe
  responden igual (código, cuerpo y encabezados salvo el `request_id`); un 403 sólo aparece dentro
  del alcance; un id con formato válido de otra administración (L-017).
- **La auditoría que se pueda saltear o editar**: una acción sensible que confirma sin su fila, una
  fila que queda aunque la acción se revierta, `UPDATE`, `DELETE`, `TRUNCATE`, `DISABLE TRIGGER` o
  `NO FORCE ROW LEVEL SECURITY` sobre `auditoria` como app y como migrador, una acción fuera del
  vocabulario, un dato sensible en el detalle.
- **El worker sin tenant**: un trabajo encolado antes de este cambio, uno armado a mano sin
  `administracion_id`, con uno vacío, malformado o de tipo equivocado; dos tareas seguidas en el mismo
  worker donde la segunda hereda el tenant de la primera.
- **El `GRANT` olvidado**: una tabla nueva sin permisos para `proptech_app`, sin RLS forzada o, si
  cuelga de un edificio, sin `complejo_id NOT NULL` con FK compuesta.
- **El filtro por edificio de la aplicación** (E2): como no lo respalda la base, es el blanco natural
  para ver la unidad de otro vecino o el edificio de otro consejo.

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-017). Detalle en `design.md` ("Cómo aplica
cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-002 · configuración rota de muchas formas | 2.1 (cada par de credenciales: faltante, vacío, en blanco) |
| L-003 · contar los tests | 1.1 y 10.1 |
| L-004 · otro camino | design.md: los tests de integración entran por la sesión; el guardián por el catálogo; el humo, por el proxy y por `psql`; el rompedor, por un tercero |
| L-005 · verde es todo el workflow | convención de `tasks.md` y 10.1 |
| L-006 · lo destructivo apunta a `proptech` | 2.2 (el paso de roles sólo toca los roles y el esquema del proyecto), 9.1 (la restauración en `proptech_restauracion`) |
| L-007 · el error de una librería es una salida | 2.1 y 2.2 (ninguna contraseña en errores ni logs), 6.2 (el detalle de auditoría sin datos sensibles), 7.1 (el valor rechazado no se loguea) |
| L-008 · coincidencia completa y sólo ASCII | 2.1 (nombres de rol), 7.1 (el `administracion_id` de una tarea) |
| L-009 · el arreglo se prueba en el gemelo | 4.1 y 7.1 (el tenant en la API y en el worker con la misma batería), 2.1 (las clases de configuración) |
| L-010 · la corrida de cierre va al final | 10.1 |
| L-011 · un plazo no cancela la transacción | 6.2 (la auditoría y el efecto se confirman o se revierten juntos, del lado de la base) |
| L-012 · la deuda al primer cambio que usa la pieza | design.md ("Deuda que recibe este cambio" y el reparto con el 2b y el 2c) |
| L-013 · mutar sin commit exige copia | convención de `tasks.md`, 2.2, 3.2, 5.1, 6.2 y 9.1 |
| L-015 · hilos y contexto | 4.1 y 7.1 (el tenant viaja en la sesión, no en una `ContextVar`, D4) |
| L-016 · una observación tiene que poder dar otro resultado | 3.1 y 6.1 (los tests conectan como `proptech_app`, nunca como superusuario), 9.1 (el volcado con el rol equivocado se ve fallar) |
| L-017 · la entrada del escenario | 3.1, 5.2 y 5.3 (ids con formato válido de otra administración) |

L-001 y L-014 no aplican al 2a: no suma dependencias que puedan congelarse ni pasos nuevos en Bash con
`|| true` (los del humo nuevo llevan su chequeo explícito igual). Las aplica el 2c.

## Fuera del cambio

- **El login en sí** (2b, D-097): contraseña del personal, link mágico del vecino, envío del mail,
  límite de intentos, auditoría de ingresos, CSP en Next y la pantalla de login. Bloqueado por **P48**.
- **El endurecimiento que el candado no necesita** (2c, D-097): cabeceras de Caddy, `Via`,
  `X-Powered-By`, HEAD, volúmenes de Caddy, CI en pull requests con límite de tiempo y gitleaks por
  digest, el resto de F7 y la doble congelada en el humo, PID 1 no root servicio por servicio,
  `no-new-privileges` y capacidades, y la tabla de variables del README.
- **Las acciones sensibles de otros módulos**: se auditan con `acceso.aplicacion` cuando existan (7, 8,
  10b).
- **Quién lee la auditoría**: este cambio no expone ningún endpoint para leerla.
- **Restaurar sobre la base en uso** y recuperar los dueños después de una restauración real: riesgo
  con dueño el cambio 15 (design, "Frontera de la restauración").
- **Dependabot**: pasa al cambio 15 (E4).
- **Configuración completa del edificio** (3), **unificar cuentas** (v1.1, D-096) y **pantallas** (11,
  12).

## Knowledge Base Impact

Archivos de `knowledge-base/` (listado del directorio, 15/10/2026): `01_vision_y_objetivos.md`,
`02_descripcion_general.md`, `03_actores_y_roles.md`, `04_modelo_de_datos.md`,
`05_reglas_de_negocio.md`, `06_funcionalidades.md`, `07_flujos_principales.md`,
`08_arquitectura_propuesta.md`, `09_decisiones_y_supuestos.md`, `10_preguntas_abiertas.md`,
`11_glosario.md`, `12_fichas_de_changes.md`, `13_motor_de_reglas.md`, `14_forma_de_trabajo.md`,
`15_lecciones.md`, `16_proyecto_final.md`, `README.md`.

- `09_decisiones_y_supuestos.md`: **APPEND**. D-097 (la partición y el login) ya está, agregada en este
  propose. Al archivar, una decisión con las elecciones de código del 2a (cuatro roles, política,
  tablas, tenant en la sesión, auditoría en `acceso` y no en `compartido` como listaba D-021) y E1 a E5
  tal como las firme el socio.
- `12_fichas_de_changes.md`: **REWRITE** de la ficha 2 (ya partida en 2a, 2b y 2c en este propose; al
  archivar, cierre y tareas del 2a) y de las filas de deuda que resuelve.
- `04_modelo_de_datos.md`: **REWRITE** de `administracion`, `complejo`, `unidad`, `persona` y
  `asignacion_rol` de "planificada" a existentes, `auditoria` y `accion_de_auditoria` nuevas, y la
  convención de `complejo_id NOT NULL` con FK compuesta.
- `03_actores_y_roles.md`: **REWRITE** de "Rutas públicas" (los tres endpoints nuevos exigen identidad).
- `08_arquitectura_propuesta.md`: **REWRITE** de la tabla de variables (credenciales por rol), de la
  sección de seguridad (cuatro roles, redes) y de las fronteras entre módulos (`complejos` → `acceso`,
  auditoría en `acceso`).
- `02_descripcion_general.md`: **REWRITE** del estado de la arquitectura (RLS vigente, roles).
- `10_preguntas_abiertas.md`: **REWRITE**. P48 ya está, agregada en este propose.
- `15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar; lo escribe quien archiva.
- `05_reglas_de_negocio.md`: none. R10 no cambia: este cambio la cumple.
- `01`, `06`, `07`, `11`, `13`, `14`, `16` y `README.md`: none.
- Fuera de `knowledge-base/`: `CHANGES.md` y `CLAUDE.md`/`AGENTS.md` (**REWRITE**, ya hecho en este
  propose; al archivar, marcar el 2a).

## Impact

- **Backend**: `proptech_core/compartido/configuracion.py`, `base_de_datos.py`, `roles.py` (nuevo);
  `proptech_core/acceso/` (dominio con la matriz y el alcance, `aplicacion/auditoria.py`, adaptadores) y
  `proptech_core/complejos/` (tablas mínimas y su lectura); `proptech_api` con la identidad, la sesión
  con tenant y tres endpoints; `proptech_worker` con el decorador de tenant; `migraciones/env.py` y las
  migraciones 0003 (tablas mínimas y RLS) y 0004 (auditoría y su vocabulario).
- **Infra**: `infra/compose.yaml` (credenciales y redes), `infra/.env.example`, `infra/ci/humo.sh`,
  `README.md` (sólo las variables nuevas; la tabla completa es del 2c).
- **Configuración nueva**: `POSTGRES_MIGRADOR_USER`/`_PASSWORD`, `POSTGRES_APP_USER`/`_PASSWORD`,
  `POSTGRES_RESPALDO_USER`/`_PASSWORD`.
- **Contrato de la API**: tres endpoints nuevos, que hasta el 2b responden 401 en producción.
- **Dependencias nuevas**: ninguna.

## Aprobación

Gobernanza CRITICAL (D-094). La completa, a mano, uno de los dos socios. Ningún agente la escribe.

Elecciones de diseño (detalle en `design.md`). Juani aprobó el 15/10/2026 aplicar la revisión del
arquitecto que les dio esta forma; eso **no** es la aprobación del cambio: cada una se firma igual acá.

| Elección | Propuesta del design | Aprobada (sí / no, con motivo) |
|---|---|---|
| E1 · `proptech_migrador` sin `BYPASSRLS` | Sin `BYPASSRLS`. El migrador es de confianza equivalente al superusuario sobre sus tablas (como dueño puede quitar el `FORCE`); no se le da `BYPASSRLS` para obligar a que una migración que siembre datos fije su tenant a propósito (D2) | |
| E2 · Alcance por edificio en la aplicación | En la aplicación, con tests por rol; la base asegura la administración. Riesgo, costo de revertir y convención `complejo_id NOT NULL` en D6 | |
| E3 · `trabajos_hechos` sin `administracion_id` | Sin columna: es técnica; las claves de idempotencia de las tareas con tenant llevan el `administracion_id` adentro (D8) | |
| E4 · Dependabot fuera del 2a | Pasa al cambio 15 | |
| E5 · Cuatro roles en vez de los dos de D-087 | Se suman el rol de arranque como dueño de la auditoría y `proptech_respaldo` (sin superusuario, `BYPASSRLS` y `pg_read_all_data`) para que `respaldos` deje de tener la contraseña del superusuario (D1) | |

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
