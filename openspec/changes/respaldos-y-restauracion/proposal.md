## Why

Un backup que nunca se restauró no es un backup. Hasta este cambio la base de PropTech no tiene
ninguna copia: un `docker compose down -v` equivocado o una migración rota se llevan todo. Antes de
que el cambio 2 cree las primeras tablas con datos de una administración, el sistema tiene que
generar backups solo, dejarlos fuera de Docker y probar en cada corrida del CI que se pueden
restaurar. De paso, el humo del CI se amplía para verificar de punta a punta, a través del proxy, lo
que construyó el 1c (worker, `request_id`, Redis), el README explica cómo levantar y restaurar, y se
cierra la deuda que el cierre del 1c le asignó a este cambio (F13, `salud_degradada` duplicado y F7c,
D-091).

Es el cambio **1d** del roadmap, que nace de partir `cola-logs-y-respaldos` en dos por la auditoría de
Alberto del 13/10 (**D-087**): el 1c quedó con logs, `request_id`, Redis, worker y web; este se queda
con respaldos, restauración, humo y README. Arranca desde la ficha `1d` de `knowledge-base/12_fichas_de_changes.md` y
habilita al cambio 2.

Decisiones que cubre: **D-047 punto 4** en su parte de backups automáticos, **D-087** (la partición,
la gobernanza HIGH y las lecciones L-007 a L-009), **D-043** (criterio de costo: sin servicios
pagos, todo con la imagen de PostgreSQL que ya se usa), **D-090** (la deuda de las auditorías del 13/10
entra en sus tareas), **D-091** (la deuda del cierre del 1c con dueño este cambio) y **D-094** (quién
aprueba un cambio HIGH). Avanza la observación **H46** (restauración de
backup probada) de M3. No toca ninguna regla de negocio (R..) ni historia (HU-..): es infraestructura.

## Gobernanza

**Nivel HIGH.** Tres motivos, los de D-087:

- **Borra bases**: `restaurar.sh` hace `dropdb` de la base destino antes de restaurar. Un destino mal
  validado borra la base en uso.
- **Escribe en el disco del host**: el servicio de respaldos monta una carpeta del host (bind mount)
  y escribe ahí como el usuario del host; un error de ruta o de retención borra archivos fuera de
  Docker.
- **Servicio nuevo** en el stack que se conecta a la base con su contraseña.

**Se propone y se espera la aprobación de uno de los dos socios (Juani o Alberto) antes de
construir** (D-094). El constructor no arranca hasta que la sección "Aprobación", al final de este
archivo, tenga el nombre, la fecha y el alcance aprobado escritos por uno de los dos. Una decisión
delegada (como D-088, en la que Juani delegó las decisiones del 13/10) **no reemplaza esta
aprobación**: delegar cómo se resuelve una auditoría no es aprobar que se construya un cambio HIGH.
Ningún agente completa esa sección.

La aprobación cubre también las dos tareas de deuda del 1c (D20 y D21 en `design.md`): tocan el
endpoint de salud y el formato de los logs de la API, que no son de nivel HIGH por sí mismos, pero se
construyen dentro de este cambio.

## What Changes

- **Backups automáticos de PostgreSQL**: un servicio `respaldos` con la imagen de PostgreSQL hace un
  `pg_dump` al arrancar (después de las migraciones) y después una vez por día, acotado por un límite
  de tiempo, lo deja en una carpeta del host (a salvo de `docker compose down -v`), conserva los
  últimos 14 y figura como no saludable si el último backup está atrasado.
- **Validación de su configuración**: intervalo, retención y límite se validan al arrancar como
  enteros escritos sólo con dígitos ASCII, sin ceros a la izquierda, en rango, y el error nombra la
  variable sin mostrar la contraseña. El script se niega a correr con uid 0. La retención nunca borra el
  backup del ciclo en curso, aunque el reloj del host atrase.
- **Restauración** `infra/respaldos/restaurar.sh`: carga un backup en una base aparte. Valida el
  nombre de la base destino con la expresión cerrada `^proptech_[a-z0-9_]{1,50}$`, rechaza la base en
  uso y apunta siempre al proyecto de Compose `proptech`. Funciona desde cualquier carpeta (hace `cd` a
  `infra/` para encontrar `compose.yaml` y `.env`) y pasa `-U` con el usuario de la base a `dropdb`,
  `createdb` y `pg_restore`.
- **Humo ampliado** (`infra/ci/humo.sh`): Redis sin puertos y con contraseña, worker, Redis y
  respaldos sin root, `request_id` de punta a punta (directo y por la web, y uno malicioso), un
  trabajo del worker con un reintento dentro del stack, Redis pausado, el backup generado solo, su
  restauración, que sobrevive a `docker compose down -v` y el comando de la semilla dentro de la
  imagen. Baja el stack con `docker compose -p proptech down -v`.
- **`shellcheck` en el CI** sobre todos los scripts de Bash de `infra/`, con versión fijada.
- **`/api/salud` con plazo total (F13)**: las verificaciones de la base y de la cola corren en
  paralelo con un plazo total de 1,5 s, así una dependencia congelada no hace que `/salud-web` (que
  corta a 2 s) informe la API como sin conexión. Cada verificación fallida deja **una sola** línea
  `salud_degradada`, aunque el hilo abandonado termine después.
- **Tracebacks crudos sin leer (F7c)**: un mensaje que ya llega como traceback en texto se registra con
  valores fijos (`tipo_error: "desconocido"`, `traza` vacía) sin parsear nada; todo mensaje que no es
  texto, con un evento fijo.
- **Rebase de los requisitos MODIFIED** sobre los specs que dejó el 1c archivado: hecho el 14/10,
  requisito por requisito, con la tabla en `design.md`; la última tarea verifica que siga vigente.
- **README**: variables nuevas, cómo crear la carpeta de respaldos y cómo restaurar un backup.

## Capabilities

### New Capabilities

- `respaldos-de-la-base`: cuándo se genera un backup, dónde queda, cuánto puede tardar, cuántos se
  conservan, qué valida al arrancar, cómo se restaura, qué destino acepta la restauración y cómo se
  prueba.

### Modified Capabilities

- `entorno-de-ejecucion`: el arranque incluye el servicio de respaldos y la carpeta del host; ese
  servicio también sin root, sin puertos y en la red sin salida; la configuración suma las variables
  de respaldos y la carpeta queda fuera de git. (Requisitos que el 1c ya modificó: este cambio parte
  de su texto archivado.)
  El endpoint de salud corre sus verificaciones en paralelo con un plazo total y loguea una sola
  línea por falla.
- `integracion-continua`: el humo cubre worker, `request_id` de punta a punta, Redis pausado (por la
  API y por la web), respaldos y restauración; el CI corre `shellcheck` sobre los scripts de Bash.
- `trazabilidad-y-logs`: un traceback crudo se registra con valores fijos sin leer su texto, y un
  mensaje que no es texto, con un evento fijo.

## Lecciones que aplican

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-013). El detalle está en `design.md` ("Cómo
aplica cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-001 · dependencia apagada, que no responde y lenta | 2.3 (base que no responde durante el volcado, cortada por el límite; lenta dentro del límite), 5.1 (`/api/salud` con dependencias congeladas y lentas), 6.3 (Redis pausado en el humo, por la API y por la web, despausado siempre) |
| L-002 · configuración rota de muchas formas | 2.1 (intervalo, retención y límite: faltante, vacía, en blanco, tipo y rango), 4.2 (Compose sin la carpeta ni el usuario) |
| L-003 · contar los tests | 1.1 (línea de base con el commit) y 8.1 (comparación) |
| L-004 · otro camino, no el mismo | design.md: los tests de los scripts usan herramientas falsas en el `PATH`; el humo usa las reales y llega por el proxy (6.2, 6.3). El rompedor ataca por un tercer camino (por ejemplo, la carpeta con un archivo ajeno con nombre parecido, o dos ciclos que se pisan) |
| L-005 · verde es todo el workflow | convención de `tasks.md` (con `shellcheck`), 4.3 (`shellcheck` en el CI, con canario), 6.5 y 8.1 |
| L-006 · lo destructivo apunta a `proptech` | 3.1 y 3.2 (destino validado y `-p proptech`), 2.4 (retención que borra sólo `proptech-*.dump` y nunca el del ciclo en curso), 6.1 (`down -v` con `-p proptech`), 6.4 (el humo borra sólo `proptech_restauracion`) |
| L-007 · el error de una librería también es una salida | 2.1 (la contraseña nunca en el error), 2.3 (la salida de `pg_dump` nunca en el log), 3.2 (la salida de `docker` y `pg_restore` nunca en el mensaje de `restaurar.sh`), 5.1 (el error tardío de una verificación no llega al log), 5.2 (el traceback crudo no se lee) |
| L-008 · `fullmatch` y sólo ASCII | 2.1 (enteros con dígitos ASCII, sin espacios, tabulaciones, saltos de línea ni ceros a la izquierda), 2.4 (patrón de nombre), 2.5 (la marca del último backup), 3.1 (el nombre de la base destino), 5.2 (un texto ajeno que no se puede validar no se lee) |
| L-009 · el arreglo de un módulo se prueba en su gemelo | design.md (los requisitos MODIFIED rebasados sobre su texto vigente) y 8.1 (sigue vigente), 2.1 y 3.1 (los dos scripts con la misma batería de L-008 y `LC_ALL=C`), 2.1 (las cinco formas de L-002 que ya prueba el arranque de la API y del worker), 5.1 (los verificadores de base y de cola con los mismos casos) |
| L-010 · la corrida de cierre va después de la última vuelta | 8.1, última tarea, repetida si el código cambia después |
| L-011 · un plazo que abandona un hilo no cancela su transacción | 2.3 (el corte mata al `pg_dump`, verificado), 5.1 (el hilo abandonado de `/api/salud` no tiene efecto y no vuelve a loguear) |
| L-012 · la deuda al primer cambio que usa la pieza | design.md ("Deuda del 1c que recibe este cambio"), 5.1 y 5.2; "Fuera del cambio" nombra el dueño de lo que no entra |
| L-013 · mutar sin commit exige copia y diff | convención de `tasks.md`, 4.3 (canario sobre una copia), 6.1 (copia de Compose), 6.3 (la constante de 5.1) |

## Fuera del cambio

- **Cola, logs, `request_id`, worker y `/salud-web`**: los construyó el cambio 1c
  (`cola-logs-y-respaldos`), archivado el 14/10. De su deuda, este cambio toma sólo F13, el duplicado
  de `salud_degradada` y F7c; el resto conserva el dueño que le dio D-091: F2c, F12b y
  `repr(RedisSettings)` al cambio 7; M12 a medias al cambio 2; F3b a quien suba FastAPI.
- **Copia de los backups fuera del servidor y cifrado** (Alberto: "copias cifradas todos los días,
  guardadas fuera del servidor"): dueño, el cambio 15 (`piloto-en-paralelo`), el primero con datos
  reales en un servidor y el que ya tiene el despliegue en la tabla de deuda del roadmap (L-012).
- **Restauración sobre la base en uso**: nunca por este procedimiento; si algún día hace falta, es un
  procedimiento manual aparte con su propia decisión.
- **Backups de Redis**: Redis persiste en su volumen con `appendonly` (1c); sus trabajos son
  reconstruibles y no se respaldan.
- **Monitoreo o alertas externas** de backups atrasados: el servicio queda no saludable y eso alcanza
  hasta el despliegue (mismo dueño, cambio 15).
- **Cambiar el contrato de `/salud-web`** (su límite de 2 s): descartado en D20.

## Knowledge Base Impact

- `knowledge-base/09_decisiones_y_supuestos.md`: **APPEND**. Una decisión con las elecciones de este
  cambio (backups diarios con `pg_dump` en formato custom desde la imagen de PostgreSQL, carpeta del
  host por bind mount, 14 copias, límite por volcado, destino de restauración con expresión cerrada;
  `/api/salud` con plazo total de 1,5 s; tracebacks crudos sin parsear) y que el 1d quedó en 20
  tareas (corrige el número de D-090).
- `knowledge-base/12_fichas_de_changes.md`: **REWRITE** de la ficha 1d (20 tareas, estado, cierre) y
  de las tres filas de la tabla "Deuda del cierre del 1c" que este cambio resuelve (F13,
  `salud_degradada` duplicado y F7c).
- `knowledge-base/08_arquitectura_propuesta.md`: **REWRITE** de "Planificadas (cambio 1d ...)" a
  variables vigentes, si el cambio se archiva con las mismas variables.
- `knowledge-base/02_descripcion_general.md`: **REWRITE** de la mención del servicio de respaldos como
  futuro.
- `knowledge-base/15_lecciones.md`: **APPEND** de lo que proponga el auditor al cerrar; lo escribe el
  orquestador al archivar, no este cambio.
- `CHANGES.md`: **REWRITE** del estado de C-04 (marcarlo `[x]`) y de su "Leer antes" (L-001 a L-013).
- `CLAUDE.md` (raíz, no es `knowledge-base/`): **REWRITE** de la línea "Próximo".
- `knowledge-base/11_glosario.md`: none. "Respaldo y restauración" ya está.
- `knowledge-base/05_reglas_de_negocio.md` y `knowledge-base/06_funcionalidades.md`: none. No cambia
  ninguna regla ni historia.

## Impact

- **Infra**: `infra/compose.yaml` (servicio `respaldos`), `infra/respaldos/respaldar.sh`,
  `infra/respaldos/restaurar.sh`, `infra/.env.example`, `infra/ci/humo.sh`, `.gitignore`, `README.md`,
  el workflow del CI (paso de `shellcheck`).
- **Tests**: `backend/tests/infra/test_respaldos.py`, `backend/tests/infra/test_restaurar.py`,
  `backend/tests/infra/test_compose.py`.
- **Configuración nueva**: `PROPTECH_DIR_RESPALDOS`, `PROPTECH_UID`/`PROPTECH_GID`,
  `RESPALDO_INTERVALO_SEGUNDOS`, `RESPALDO_CONSERVAR`, `RESPALDO_LIMITE_SEGUNDOS`.
- **Dependencias nuevas**: ninguna en el código (usa la imagen `postgres:18.6-trixie` que ya está en
  Compose). En el CI, `shellcheck` con versión fijada.
- **Contrato**: ninguno de la API ni de la web.

## Aprobación

Gobernanza HIGH (D-087, D-094). La completa, a mano, uno de los dos socios. Ningún agente la escribe.

| Socio (Juani o Alberto) | Fecha | Alcance aprobado |
|---|---|---|
| Juani | 14/10/2026 | Todo el 1d tal como está en esta propuesta, incluidas las tareas 5.1 y 5.2 (salud y logs) |
