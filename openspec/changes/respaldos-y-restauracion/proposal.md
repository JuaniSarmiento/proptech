## Why

Un backup que nunca se restauró no es un backup. Hasta este cambio la base de PropTech no tiene
ninguna copia: un `docker compose down -v` equivocado o una migración rota se llevan todo. Antes de
que el cambio 2 cree las primeras tablas con datos de una administración, el sistema tiene que
generar backups solo, dejarlos fuera de Docker y probar en cada corrida del CI que se pueden
restaurar. De paso, el humo del CI se amplía para verificar de punta a punta, a través del proxy, lo
que construyó el 1c (worker, `request_id`, Redis) y el README explica cómo levantar y restaurar.

Es el cambio **1d** del roadmap, que nace de partir `cola-logs-y-respaldos` en dos por la auditoría de
Alberto del 13/10 (**D-087**): el 1c quedó con logs, `request_id`, Redis, worker y web; este se queda
con respaldos, restauración, humo y README. Arranca desde la ficha `1d` de `conocimiento/roadmap.md` y
habilita al cambio 2.

Decisiones que cubre: **D-047 punto 4** en su parte de backups automáticos, **D-087** (la partición,
la gobernanza HIGH y las lecciones L-007 a L-009) y **D-043** (criterio de costo: sin servicios
pagos, todo con la imagen de PostgreSQL que ya se usa). Avanza la observación **H46** (restauración de
backup probada) de M3. No toca ninguna regla de negocio (R..) ni historia (HU-..): es infraestructura.

## Gobernanza

**Nivel HIGH.** Tres motivos, los de D-087:

- **Borra bases**: `restaurar.sh` hace `dropdb` de la base destino antes de restaurar. Un destino mal
  validado borra la base en uso.
- **Escribe en el disco del host**: el servicio de respaldos monta una carpeta del host (bind mount)
  y escribe ahí como el usuario del host; un error de ruta o de retención borra archivos fuera de
  Docker.
- **Servicio nuevo** en el stack que se conecta a la base con su contraseña.

**Se propone y se espera la aprobación de Juani antes de construir.** El constructor no arranca hasta
que la línea de abajo tenga la fecha y la firma escritas por Juani. Una decisión delegada (como D-088,
en la que Juani delegó las decisiones del 13/10) **no reemplaza esta aprobación**: delegar cómo se
resuelve una auditoría no es aprobar que se construya un cambio HIGH. Ningún agente completa esta
línea.

- Aprobación de Juani: **pendiente**, con fecha y firma escrita por Juani.

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
- **Rebase de los requisitos MODIFIED** sobre los specs que deja el 1c archivado, comparados requisito
  por requisito antes de construir (un MODIFIED reemplaza el requisito entero).
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
- `integracion-continua`: el humo cubre worker, `request_id` de punta a punta, Redis pausado,
  respaldos y restauración; el CI corre `shellcheck` sobre los scripts de Bash.

## Lecciones que aplican

Se leyó `conocimiento/lecciones.md` entero (L-001 a L-009). El detalle está en `design.md` ("Cómo
aplica cada lección"); en resumen:

| Lección | Tareas |
|---|---|
| L-001 · dependencia apagada, que no responde y lenta | 2.3 (base que no responde durante el volcado, cortada por el límite; lenta dentro del límite), 5.3 (Redis pausado en el humo, despausado siempre) |
| L-002 · configuración rota de muchas formas | 2.1 (intervalo, retención y límite: faltante, vacía, en blanco, tipo y rango), 4.2 (Compose sin la carpeta ni el usuario) |
| L-003 · contar los tests | 1.1 (línea de base) y 7.1 (comparación) |
| L-004 · otro camino, no el mismo | design.md: los tests de los scripts usan herramientas falsas en el `PATH`; el humo usa las reales. El rompedor ataca por un tercer camino (por ejemplo, la carpeta con un archivo ajeno con nombre parecido, o dos ciclos que se pisan) |
| L-005 · verde es todo el workflow | convención de `tasks.md` (con `shellcheck`), 4.3 (`shellcheck` en el CI, con canario) y 7.1 |
| L-006 · lo destructivo apunta a `proptech` | 3.1 y 3.2 (destino validado y `-p proptech`), 2.4 (retención que borra sólo `proptech-*.dump` y nunca el del ciclo en curso), 5.1 (`down -v` con `-p proptech`), 5.4 (el humo borra sólo `proptech_restauracion`) |
| L-007 · el error de una librería también es una salida | 2.1 (la contraseña nunca en el error), 2.3 (la salida de `pg_dump` nunca en el log), 3.2 (la salida de `docker` y `pg_restore` nunca en el mensaje de `restaurar.sh`) |
| L-008 · `fullmatch` y sólo ASCII | 2.1 (enteros con dígitos ASCII, sin espacios, tabulaciones, saltos de línea ni ceros a la izquierda), 2.5 (la marca del último backup), 3.1 (el nombre de la base destino) |
| L-009 · el arreglo de un módulo se prueba en su gemelo | 0.1 (los requisitos MODIFIED contra su texto archivado), 2.1 y 3.1 (los dos scripts con la misma batería de L-008 y `LC_ALL=C`), 2.1 (las cinco formas de L-002 que ya prueba el arranque de la API y del worker) |

## Fuera del cambio

- **Cola, logs, `request_id`, worker y `/salud-web`**: cambio 1c (`cola-logs-y-respaldos`), que tiene
  que estar archivado antes de empezar este.
- **Copia de los backups fuera del servidor y cifrado** (Alberto: "copias cifradas todos los días,
  guardadas fuera del servidor"): se decide con el despliegue al VPS.
- **Restauración sobre la base en uso**: nunca por este procedimiento; si algún día hace falta, es un
  procedimiento manual aparte con su propia decisión.
- **Backups de Redis**: Redis persiste en su volumen con `appendonly` (1c); sus trabajos son
  reconstruibles y no se respaldan.
- **Monitoreo o alertas externas** de backups atrasados: el servicio queda no saludable y eso alcanza
  hasta el despliegue.

## Knowledge Base Impact

- `conocimiento/decisiones.md`: **APPEND**. Una decisión con las elecciones de este cambio (backups
  diarios con `pg_dump` en formato custom desde la imagen de PostgreSQL, carpeta del host por bind
  mount, 14 copias, límite por volcado, destino de restauración con expresión cerrada).
- `conocimiento/roadmap.md`: **REWRITE** de la ficha 1d (marcarla ✅).
- `conocimiento/glosario.md`: **APPEND** de "respaldo (backup)" y "restauración", si no están.
- `conocimiento/lecciones.md`: lo propone el auditor al cerrar; este cambio no lo escribe.
- `conocimiento/reglas-de-negocio.md` y `conocimiento/mvp.md`: none. No cambia ninguna regla ni
  historia.

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
