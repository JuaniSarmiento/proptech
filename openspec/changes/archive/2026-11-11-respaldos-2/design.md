## Context

Ver `proposal.md` (Why) para la motivación. Lo que importa acá es el estado del código que se toca:

- `infra/respaldos/respaldar.sh` (276 líneas, Bash con `set -euo pipefail`) corre como PID 1 del
  servicio `respaldos`, con la imagen `postgres:18.6-trixie` y el UID/GID del host. Tiene tres modos:
  continuo (default), `--una-vez` y `--salud`. La retención (`aplicar_retencion`, `:88-128`) arma la
  lista con un glob, la filtra con el patrón `^proptech-[0-9]{8}T[0-9]{6}Z\.dump$` y la ordena con
  `sort`, es decir **por nombre**, que es por el reloj del host al momento de crear el archivo.
- `logear` (`:61-70`) imprime JSON a stdout; `error_salir` (`:13-16`) imprime `echo "error: $1"` a
  stderr, en texto plano. Son las dos únicas salidas del script.
- El modo continuo es `ciclo_backup || true` seguido de `while true; do sleep ...; ciclo_backup || true;
  done` (`:270-274`). No hay ningún `trap`, y `sleep` corre en primer plano.
- `infra/respaldos/restaurar.sh` (73 líneas) valida archivo y destino, resuelve `infra/` por
  `BASH_SOURCE`, corre `docker compose -p "${PROPTECH_COMPOSE_PROYECTO:-proptech}"` y hace
  `dropdb`/`createdb`/`pg_restore` dentro del contenedor `db`. Ahí termina: nada apunta la aplicación
  a la base restaurada.
- `backend/src/proptech_api/salud.py` corre las dos verificaciones en hilos con un plazo total
  (`PLAZO_TOTAL_SALUD_S`) y usa `_informar_una_sola_vez(lock, informado, ...)` para que la línea
  `salud_degradada` salga una sola vez por dependencia y pedido. Quien **primero** llega (el
  vencimiento del plazo o el hilo que termina con error) escribe; el otro no escribe nada. La falla F6
  es el caso en que **ninguno** llega antes de que la respuesta 503 se devuelva.
- `POSTGRES_DB` vive en `infra/.env` y la consumen `api`, `worker`, `migraciones` y `respaldos`. No hay
  ningún otro lugar donde la aplicación diga a qué base se conecta.
- Restricciones que no se negocian: los siete servicios corren con PID 1 no root (2c); la carpeta de
  respaldos es un bind mount del host para sobrevivir a `docker compose down -v` (1d, D9); ningún
  mensaje propio repite la salida de una herramienta ajena (L-007); toda validación de texto es
  fullmatch ASCII (L-008); nada de `GRANT` nuevos ni cambios de rol (eso es C-29).

## Goals / Non-Goals

**Goals:**

- Que la retención no dependa del reloj del host ni del orden alfabético, y que garantice una ventana
  de recuperación en días además de una cantidad de archivos.
- Que el servicio tenga una sola forma de salida: una línea JSON por evento, siempre.
- Que apagar el stack no implique matar el servicio de respaldos a los 10 segundos.
- Que F6 quede cerrado con un hecho: arreglado con un test que lo fuerza de forma determinista, o
  descartado con la ráfaga corrida, su cantidad de intentos y su salida pegada.
- Que exista una herramienta ejecutada (no sólo documentada) para conmutar la aplicación a una base
  restaurada, con tres verificaciones que la frenan antes de tocar nada.
- Que el escenario "volcado con el rol equivocado" se pruebe con `pg_dump` real.

**Non-Goals de diseño** (además del "Qué queda fuera" del proposal):

- No se rediseña el formato del log ni el esquema de eventos: F8 adopta el que `logear` ya emite.
- No se cambia el nombre de los archivos de backup ni su patrón: el nombre sigue siendo informativo;
  lo que deja de hacerse es **ordenar** por él.
- No se toca `restaurar.sh` más allá de lo que la conmutación necesite reutilizar.
- No se agrega ninguna dependencia nueva: todo con lo que ya hay en la imagen de Postgres y en el
  entorno de tests.

## Decisions

### D1 · La antigüedad de un backup se lee del sistema de archivos, no del nombre (F4)

`aplicar_retencion` sigue filtrando por el patrón de nombre (es lo que protege a un archivo ajeno,
L-006), pero ordena por **tiempo de modificación**: para cada candidato que pasa el patrón se obtiene
`stat -c %Y`, se arma `<mtime> <nombre>` y se ordena numéricamente. El archivo del ciclo en curso se
sigue excluyendo por nombre exacto antes de ordenar, que es la protección que ya existe.

- **Alternativa descartada: `ls -t`.** Más corto, pero obliga a parsear la salida de `ls`, que es
  exactamente lo que L-007 y la convención del script evitan; y su orden depende de la configuración
  regional y de la implementación.
- **Alternativa descartada: `find -printf '%T@ %p\n'`.** Funciona en la imagen (GNU find), pero `find`
  recorrería la carpeta sin el filtro por patrón ya aplicado y habría que re-filtrar la salida; con
  `stat` el filtro vive en un solo lugar.
- **Alternativa descartada: no ordenar y comparar de a pares con `[ a -nt b ]`.** Correcto pero
  cuadrático y mucho más difícil de leer para algo que `sort -n` resuelve.
- **Por qué no "arreglar el nombre"** (usar un reloj monotónico o un contador en el nombre): cambiaría
  el patrón de nombre que la spec, el humo y `restaurar.sh` ya conocen, y seguiría atando el orden a un
  dato escrito por el productor en vez de al hecho observable.

### D2 · "14 copias" se resuelve con cantidad **más** un piso por días, no reemplazándola

`RESPALDO_CONSERVAR` sigue siendo la cantidad. Se agrega `RESPALDO_CONSERVAR_DIAS` (default 14,
validado con la misma `validar_entero` de L-008, rango 1..365): dentro de esa ventana nunca se borra el
backup correcto **más nuevo de cada día**. El día de un backup se calcula de su mtime
(`date -u -d "@$mtime" +%Y%m%d`), por la misma razón que D1.

- **Alternativa descartada: reemplazar la cantidad por una retención puramente temporal.** Un bucle de
  reinicios con el intervalo bajo podría llenar el disco: la cantidad es el techo que protege el disco
  y no se puede perder.
- **Alternativa descartada: sólo documentar que "14 copias no son 14 días".** Es la opción más barata y
  cumple la letra de la spec de hoy, pero deja al piloto con una ventana de recuperación que depende de
  cuántas veces se reinició el stack. El 15 va a necesitar la ventana, no la nota al pie.
- **Default que no cambia el comportamiento observable**: con 14 y 14, un stack que genera un backup
  por día se comporta exactamente como hoy; la diferencia aparece sólo con muchos backups por día, que
  es el caso que la deuda describe.
- Esta decisión se escribe en `knowledge-base/09_decisiones_y_supuestos.md` (APPEND), con la
  alternativa descartada: es la respuesta pedida por la ficha 1e ("decidir si se documenta o se
  cambia").

### D3 · El apagado se maneja con `trap` más `& wait`, no sólo con `trap` (F5)

Un `trap ... TERM INT` solo no alcanza: Bash **no** ejecuta el handler mientras espera un comando en
primer plano, así que un `sleep 86400` se comería la señal hasta terminar. El modo continuo pasa a
lanzar la espera en segundo plano (`sleep "$RESPALDO_INTERVALO_SEGUNDOS" & wait "$!"`), que sí es
interrumpible, y el volcado largo (`timeout ... pg_dump`) también corre con `& wait "$!"` guardando su
PID. El handler: marca que hay que salir, mata al hijo si hay uno, borra el `.parcial` del ciclo en
curso, emite su evento JSON y sale con 0.

- Cuidado explícito con L-014: el handler y todo lo que corre bajo `ciclo_backup || true` se escriben
  con `if !` explícito; nada confía en `set -e` ahí adentro.
- `wait` devuelve >128 cuando lo interrumpe una señal: ese código **no** se confunde con una falla de
  `pg_dump`. El ciclo distingue "interrumpido por señal" de "el volcado falló" y no escribe
  `respaldo_fallido` ni `.ultimo-fallo` por un apagado pedido (un apagado no es una falla de backup, y
  marcarlo como tal dejaría el servicio no saludable al volver).
- **Alternativa descartada: `STOPSIGNAL`/`stop_grace_period` más corto en Compose.** Apaga más rápido
  pero sigue matando el proceso: el `.parcial` quedaría, que es justo lo que F5 quiere evitar.
- **Alternativa descartada: un `tini`/`dumb-init` como PID 1.** Resuelve la cosecha de hijos, no la
  interrupción de `sleep`, y agrega un binario al servicio para nada.

### D4 · Todas las salidas pasan por `logear`; `error_salir` deja de ser un `echo` (F8)

`logear` gana un parámetro de flujo para poder escribir a stderr sin cambiar el esquema, y
`error_salir` pasa a llamarlo con nivel `error`, un evento propio (`arranque_rechazado`,
`configuracion_invalida`, `carpeta_no_escribible`) y los pares que ya nombra hoy (la variable o la
carpeta). Los fatales siguen yendo a stderr (no se cambia qué flujo usa cada cosa, sólo su formato), y
el código de salida no cambia. El test transversal recorre **todas** las líneas de los cuatro modos y
exige que cada una se parsee como JSON: es el único que puede atrapar una salida nueva en texto plano
que alguien agregue después (L-019 — un test por caso no vigila el caso que todavía no existe).

### D5 · F6 se cierra con un test determinista, no con una ráfaga más grande

La ráfaga del rompedor del 1d reprodujo F6 1 de 18 veces. Repetirla es el **primer** paso (y su salida
se pega, con la cantidad de intentos, como pide L-016), pero no puede ser la evidencia del arreglo: un
test que falla 1 de 18 veces es un test que no vigila.

El arreglo propuesto cierra la ventana por construcción, no por suerte: al armar la respuesta, por
cada dependencia que se va a informar como `sin_conexion` se pasa por el mismo
`_informar_una_sola_vez` (con su lock y su bandera) **antes** de devolver el 503. Si el hilo tardío ya
escribió, la bandera está puesta y no se escribe nada; si no escribió, la línea sale ahí. "Ni cero ni
dos" queda garantizado por la bandera que ya existe, sin un lock nuevo ni un orden nuevo entre hilos.

El test se escribe forzando el orden (el verificador devuelve `False` sin haber informado, simulando
exactamente la carrera perdida), de modo que da rojo de forma determinista con el código de hoy. La
ráfaga queda igual como prueba de humo, no como el test del arreglo.

- Si la ráfaga **no** reprodujera F6 y el análisis mostrara que la ventana no existe, el cierre es por
  escrito con el comando, los intentos y la salida — pero el test determinista de arriba decide: si da
  rojo contra el código de hoy, la ventana existe, se reprodujo o no.

### D6 · `conmutar.sh`: verificar contra la base, después tocar `.env`, después levantar

Herramienta nueva, hermana de `restaurar.sh` y con su misma forma (resuelve `infra/` por
`BASH_SOURCE`, corre `docker compose -p "${PROPTECH_COMPOSE_PROYECTO:-proptech}"`, valida el destino
con la misma expresión cerrada, nunca repite la salida de una herramienta). Orden de pasos:

1. Validar el nombre del destino (fullmatch ASCII) y que **no** sea la base en uso. Nada de docker
   todavía.
2. Verificación 1 — la base existe y acepta conexión.
3. Verificación 2 — la revisión de migraciones de la base destino (`alembic_version`) es exactamente la
   cabeza del repositorio. La cabeza se **deriva** (se le pregunta a Alembic), nunca se escribe a mano
   en el script: una cabeza escrita a mano queda vieja en el próximo change y el chequeo pasa a
   mentir (es la deuda que `ensayo-roles.sh` ya tuvo, D7 del 6).
4. Verificación 3 — las tablas de negocio tienen RLS **forzada** y sus políticas presentes. Se mira el
   efecto en el catálogo (`relrowsecurity`, `relforcerowsecurity`, las políticas por tabla), no una
   línea del compose (L-018). Se compara el **contenido** de las políticas, no su cantidad (es el
   hallazgo C2V2-3 que el C-23 arrastra; acá se nace cumpliéndolo).
5. Recién si las tres pasan: copia de resguardo de `infra/.env` (`.env.anterior`, con el valor
   anterior de `POSTGRES_DB` adentro), reemplazo de `POSTGRES_DB` por el destino, y
   `docker compose up -d --no-deps` de los servicios que se conectan a la base.
6. Verificación final: `GET /api/salud` responde 200. Si no, el script lo informa con código distinto
   de 0 y dice cómo volver (el `.env.anterior` y el comando), sin deshacer solo: revertir la base a la
   que estaba sirviendo es una decisión de quien opera, no del script.

La base anterior **no** se borra ni se toca. El script no corre migraciones: si la revisión no
coincide, falla y lo dice; migrar una base restaurada es otra operación, con otra decisión detrás.

- **Alternativa descartada: una variable nueva (`POSTGRES_DB_ACTIVA`) en vez de reescribir
  `POSTGRES_DB`.** Dejaría dos fuentes para el mismo dato y una pregunta nueva en cada servicio sobre
  cuál gana. Reescribir el único lugar donde hoy vive el nombre de la base es más chico y más
  auditable.
- **Alternativa descartada: documentar el procedimiento en el README sin script.** L-043: un
  procedimiento que no se ejecuta no se sabe si funciona; y acá el costo de equivocarse es apuntar la
  aplicación a una base equivocada con el libro de movimientos adentro.
- **Alternativa descartada: conmutar con un alias o un `search_path` dentro de Postgres.** Más
  invisible, y esconde en la base una decisión que tiene que verse en el entorno.

### D7 · La carpeta del host se crea desde el arranque documentado, no con un contenedor root

Docker crea la carpeta faltante de un bind mount **como root**: eso es lo que hoy deja al servicio
reiniciando en bucle cuando alguien olvida el `mkdir`. Tres caminos posibles y el que se elige:

- **Elegido**: el arranque documentado pasa a ser un script propio en `infra/` que crea la carpeta con
  el UID/GID del host (si falta) y delega en `docker compose up`. El README deja de pedir un `mkdir` y
  pide ese comando; el humo y el CI usan el mismo camino, así que se ejecuta de verdad (L-043). El
  servicio conserva su error JSON nombrando la carpeta para el caso de quien corra `docker compose up`
  a mano.
- **Descartado: un servicio de init con `user: "0:0"` que haga `mkdir` y `chown`.** Es el único camino
  que hace funcionar `docker compose up` pelado, pero mete un contenedor root en un stack cuyo 2c
  exige PID 1 no root en los siete servicios, y obligaría a modificar ese requisito en un change HIGH
  de respaldos. **Si el firmante prefiere esa garantía al costo de abrir esa puerta, es un cambio de
  scope**: hay que modificar el requisito de `entorno-de-ejecucion` sobre contenedores sin privilegios
  de root y declararlo en la firma. Mientras la firma no diga eso, vale el camino elegido.
- **Descartado: montar `infra/` entero en el contenedor de respaldos** para que el script cree la
  subcarpeta él mismo. Funcionaría (el padre ya existe, así que Docker no lo crea como root), pero le
  da al servicio con credenciales de la base acceso de escritura a `.env` y a todo `infra/`. Peor
  trueque que el problema que resuelve.

**Límite declarado**: con el camino elegido, `docker compose up` ejecutado a mano, sin el script, sigue
pudiendo crear la carpeta como root. Lo que cambia es que el camino documentado y el camino del CI ya
no dependen de que alguien se acuerde, y que la falla es una línea JSON que nombra la carpeta en vez de
un bucle de reinicios mudo.

### D8 · El volcado con el rol equivocado se prueba con `pg_dump` real y reemplaza al test con binario falso

El test nuevo es de integración (base real en Docker, como el resto de
`backend/tests/integracion/`): configura el ciclo con las credenciales de `proptech_app`, lo corre y
exige volcado fallido, carpeta sin `.dump` ni `.parcial`, el evento en JSON sin la salida de `pg_dump`
y `--salud` en rojo. El test con `FAKE_PG_DUMP_FALLA` para ese escenario **se reemplaza**, no se
duplica: no distingue un rol realmente rechazado de un compose bien escrito (L-019). Los demás usos de
herramientas falsas en `test_respaldos.py` (que prueban el manejo de una falla, no el rechazo del rol)
se quedan como están.

Se agrega además el caso "un rol filtrado no produce un backup aparentemente válido": es la forma en
que esta falla duele de verdad (un `.dump` vacío sin error), y el `pg_restore --list` que el ciclo ya
hace es lo que lo atrapa.

## Risks / Trade-offs

- **`stat -c %Y` es GNU** → la imagen del servicio es Debian (`postgres:18.6-trixie`) y los tests
  corren con coreutils GNU en el CI y en Git Bash. Se declara como supuesto y el test de retención
  corre el script de verdad, así que un entorno sin `stat` GNU da rojo en el CI, no en producción.
- **El mtime se puede tocar** (`touch`) y no es más "verdad" que el nombre en términos absolutos →
  pero es el dato que el propio sistema de archivos escribe al crear el archivo, no uno que el
  productor elige; para el caso real (reloj del host atrasado) discrimina, y eso es lo que F4 pide.
- **D2 puede conservar más archivos que `RESPALDO_CONSERVAR`** si hay muchos días con un solo backup →
  el techo del disco se corre. Mitigación: la ventana por días está acotada (1..365) y el escenario
  "backups más viejos que la ventana" exige que esos sí se borren; el default reproduce el
  comportamiento de hoy.
- **El `trap` con `& wait` cambia la forma del bucle principal**, que es el código más probado del 1d →
  Mitigación: los tests de retención, de falla de volcado y de salud del 1d se corren sin modificar
  antes y después del cambio (red de seguridad con su línea base pegada), y el apagado tiene sus tres
  escenarios propios.
- **Un apagado durante un volcado sale con 0 y sin `respaldo_fallido`** → alguien podría leer un
  apagado como un ciclo exitoso. Mitigación: el evento de apagado es propio y distinto, y la marca del
  último backup correcto **no** se actualiza.
- **F6 puede no reproducirse con la ráfaga** y quedar la duda de si el arreglo arregló algo →
  Mitigación: el test determinista de D5 es el juez; si da rojo contra el código de hoy, la ventana
  existía.
- **`conmutar.sh` reescribe `infra/.env`**, un archivo con contraseñas → Mitigación: sólo reemplaza la
  línea de `POSTGRES_DB`, deja `.env.anterior` con permisos iguales al original, y ningún valor de
  contraseña pasa por un mensaje ni por el log. El test verifica que las otras líneas del archivo
  quedan idénticas byte a byte.
- **Conmutar a una base restaurada que pasó las tres verificaciones pero tiene datos atrasados** sigue
  siendo posible → es inherente a restaurar un backup, no un defecto del script. Mitigación honesta:
  el script informa qué base queda activa y de qué archivo venía, y el README dice en una línea que la
  ventana de datos perdidos es la que separa el backup del incidente. Las métricas y alertas que
  acortan esa ventana son del 15 (OPS-3).
- **Esto toca el vecindario de datos CRITICAL sin ser un change CRITICAL** → Mitigación: las tres
  verificaciones previas, la prohibición de borrar la base anterior, la firma HIGH antes del apply y la
  regla de que cualquier necesidad de tocar código de `cuenta_corriente` o `pagos` saca ese pedazo del
  change.
- **Mezcla de dos capacidades en un change** (`respaldos-de-la-base` y `entorno-de-ejecucion` por F6) →
  F6 es la única parte que no es de respaldos y entra por ser deuda del mismo cierre (1d). Es una tarea
  acotada con su propio test; si creciera, sale al C-23 o al C-29 según de qué resulte ser.

## Migration Plan

No hay migraciones de base ni cambios de esquema. Los pasos de despliegue:

1. `RESPALDO_CONSERVAR_DIAS` entra en `infra/.env.example` y en la tabla de variables del README, con
   default 14. Un `.env` existente sin la variable arranca igual (el compose la pasa con default), así
   que no hay paso obligatorio para quien ya tiene el stack levantado.
2. La carpeta de respaldos existente no se toca: el arranque nuevo sólo la crea si falta.
3. Los backups ya generados siguen siendo válidos: el patrón de nombre no cambia y la retención nueva
   los ordena por mtime, que ya tienen.
4. **Rollback**: revertir el commit. No queda estado persistente nuevo salvo `.env.anterior`, que lo
   crea `conmutar.sh` sólo si alguien lo corre, y la variable nueva, que al faltar vuelve al default.
5. `conmutar.sh` no se corre en producción como parte del despliegue: se ensaya en el cierre (o en el
   humo) contra una base restaurada de prueba, con comandos y salida pegados.

## Open Questions

- **¿`docker compose up` pelado tiene que funcionar sin el script de arranque?** Es la pregunta de D7 y
  la contesta el firmante HIGH: si la respuesta es sí, hay que modificar el requisito de contenedores
  sin root de `entorno-de-ejecucion` y el scope crece. Se puede contestar al firmar, sin cambiar las
  specs ya escritas si la respuesta es no (el camino elegido).
- **¿La conmutación se ensaya en el humo del CI o sólo en el cierre?** Ensayarla en el humo es mejor
  (se ejecuta en cada corrida), pero suma minutos a un job que ya tuvo problemas de tiempo (L-044). Se
  decide al escribir la tarea, midiendo el paso: si suma más de un minuto, va al cierre con su
  evidencia. No cambia ninguna spec ni el resto de las tareas.
