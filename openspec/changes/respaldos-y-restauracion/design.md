## Context

Ver `proposal.md` (Why). Este cambio es el 1d: nace de partir `cola-logs-y-respaldos` (1c) en dos por
D-087. **D9 (respaldos) se mudó del diseño del 1c sin cambios de fondo** y conserva su número para que
se pueda rastrear; acá se amplía con lo que pidió la auditoría (límite por volcado, validación ASCII
de la configuración y del destino, errores de herramientas fuera del log). D14 (humo ampliado) y D15
(README) son nuevas. D1 a D4, D7, D8, D12, D13 y D16 a D18 viven en el diseño del 1c. D19 (shellcheck
en el CI) es nueva y, con los ajustes a D9, D14 y D15, sale de la tercera auditoría del socio (13/10):
rebase de los MODIFIED (M20), `restaurar.sh` con `-U` y carpeta propia (M21), retención con el reloj
atrasado (M22), rechazo de uid 0 (M23), `shellcheck` (M28) y `down -v` con `-p proptech` (B15). D20 y
D21 son la deuda que el cierre del 1c le asignó a este cambio (D-091): F13 con `salud_degradada`
duplicado, y F7c.

Estado de partida, con el 1c archivado el 14/10 (`openspec/changes/archive/2026-10-14-cola-logs-y-respaldos/`,
commit `ca800d9`):

- `infra/compose.yaml` (proyecto `proptech`): `db` (`postgres:18.6-trixie`, con `log_line_prefix`),
  `migraciones`, `api`, `worker`, `redis`, `web`, `caddy`; redes `borde` e `interna`
  (`internal: true`) y la red de salida propia del worker; ancla de rotación `x-logs` en todos los
  servicios.
- Migración `0002` con `trabajos_hechos`. Comando `python -m proptech_worker.prueba encolar` dentro de
  la imagen del backend. `/api/salud` informa `base` y `cola`, cada verificación en su hilo con
  `PLAZO_VERIFICACION_S = 2.0`, una después de la otra (`backend/src/proptech_api/salud.py`);
  `/salud-web` corta a 2000 ms (`web/src/app/salud-web/route.ts`); Caddy pisa `X-Request-ID`.
- `infra/ci/humo.sh` del 1a, sin cambios en el 1c: levanta con `--wait`, verifica salud, puertos, `db`
  sin mapeo, API y web sin root, imágenes sin `.env`, la home, y la base pausada y detenida.

**Gobernanza HIGH** (proposal.md): no se construye sin la aprobación escrita y fechada de uno de los
dos socios (Juani o Alberto) en la sección "Aprobación" de la propuesta (D-094).

## Rebase sobre el 1c archivado

**Un MODIFIED reemplaza el requisito entero**: lo que el texto vigente tenga y este cambio no copie se
revierte al archivar el 1d, y `openspec validate` no lo detecta (valida la forma, no compara contra el
texto anterior). Por eso cada requisito MODIFIED de este cambio se rehízo el 14/10 partiendo del texto
vigente en `openspec/specs/` (último commit que los tocó: `ca800d9`, el archivo del 1c; árbol en
`297897d`), y se comparó bloque por bloque, del título del requisito al siguiente, con un diff. El
resultado: el texto vigente se conserva entero en los siete requisitos y el 1d sólo agrega, salvo
una oración de "Endpoint de salud" que D20 reemplaza a propósito (ver la tabla). La
verificación de que sigue vigente al archivar está en la tarea 8.1 (a).

| Requisito | Qué trae el texto vigente (1c, o 1a si el 1c no lo tocó) | Qué agrega el 1d |
|---|---|---|
| `entorno-de-ejecucion` › Arranque completo con un comando | 1c: worker y Redis en el arranque y entre los servicios saludables; la contraseña de Redis como variable obligatoria | El servicio de respaldos en el arranque y entre los saludables; crear la carpeta de respaldos antes del `up`; carpeta y `PROPTECH_UID`/`PROPTECH_GID` como variables obligatorias |
| `entorno-de-ejecucion` › El proxy es la única puerta pública | 1c: Redis y el worker sin puertos; base y Redis en la red sin salida; red de salida propia del worker; escenarios de Redis desde el host y sin contraseña | El servicio de respaldos sin puertos, en la red sin salida y fuera de la red de salida del worker |
| `entorno-de-ejecucion` › Endpoint de salud | 1c: `base` y `cola`; 503 con `sin_conexion` por componente; 2 s por verificación; engine único con pool configurado; log sin el mensaje del driver; siete escenarios | Las dos verificaciones en paralelo con un plazo total de 1,5 s, que **reemplaza** la oración "cada verificación acotada a 2 s" del 1c (F13, D20; es la única oración vigente que no se conserva, y es a propósito); exactamente una línea `salud_degradada` por verificación fallida (D20); tres escenarios nuevos. Los siete del 1c quedan sin cambios |
| `entorno-de-ejecucion` › Configuración sólo por variables de entorno y sin secretos en el repositorio | 1c: contraseña de Redis, `PROPTECH_PARAMETROS`, contraseñas como secreto y cadena armada sólo al conectar; ocho escenarios | Carpeta, usuario, frecuencia, límite y retención de los respaldos como variables; la carpeta de respaldos fuera de git; `.env.example` con las variables de respaldos; escenario "Carpeta de respaldos ignorada" |
| `entorno-de-ejecucion` › Contenedores sin privilegios de root | 1c: el worker y Redis sin root | El servicio de respaldos sin root |
| `integracion-continua` › Prueba de humo del stack detrás del proxy | 1a (el 1c no lo tocó): salud 200 con la base y puertos | Cola, worker con reintento, `request_id` directo y por la web, `/salud-web` degradada con Redis pausado (F13), backup, restauración, `down -v`, comandos destructivos sobre `proptech`; escenarios "Request id malicioso en el humo" y "Redis pausado en el humo" |
| `trazabilidad-y-logs` › Lo que nunca se loguea | 1c: nada de cuerpos, query, encabezados, secretos, texto de excepciones ni de terceros; cinco escenarios | Traceback crudo con valores fijos sin leer su texto y evento fijo para todo mensaje que no es texto (F7c, D21); dos escenarios nuevos |

## Deuda del 1c que recibe este cambio

El cierre del 1c (D-091) le asignó tres ítems. Los tres entran, con su tarea:

| Deuda | Decisión | Tarea |
|---|---|---|
| **F13**: `/salud-web` informa `sin_conexion` con una dependencia congelada, porque `/api/salud` tarda 2,005 s y la web corta a 2,000 s | D20: verificaciones en paralelo con plazo total de 1,5 s | 5.1, de punta a punta en 6.3 |
| **`salud_degradada` duplicado**: dos líneas por pedido colgado, porque el hilo que termina tarde vuelve a loguear | D20: una marca por verificación; loguea sólo el primero que informa | 5.1 |
| **F7c**: el parseo del traceback crudo todavía saca datos a `tipo_error`/`traza` con formas particulares, y un `msg` objeto no excepción usa su `__str__` | D21: no se parsea el texto; valores fijos y evento fijo para todo lo que no es `str` | 5.2 |

**Por qué el dueño es este cambio y no otro (L-012)**: F13 y el duplicado los ejercita por primera vez
el humo ampliado de este cambio (Redis pausado a través del proxy y de la web, 6.3); dejarlos para
después es dejar al humo verificando un comportamiento que se sabe incorrecto. F7c es la única que se
discutió: el primer cambio que mete datos personales en mensajes de excepción es el 2, y ahí el riesgo
pasa a ser real. Se queda en el 1d porque el arreglo es **sacar** código (el parseo) y no sumarlo, cabe
en una tarea de medio día, y el 2 ya es CRITICAL y grande; si se moviera, su dueño sería el 2, antes de
su primera tabla con datos personales.

## Cómo aplica cada lección

Se leyó `knowledge-base/15_lecciones.md` entero (L-001 a L-013).

| Lección | Dónde se aplica en este cambio |
|---|---|
| L-001 (apagada, que no responde y lenta, con cota de tiempo) | El volcado contra una base que no responde se corta por `RESPALDO_LIMITE_SEGUNDOS` (D9; 2.3, con `pg_dump` falso que no termina y cota afirmada); la base apagada (2.3) y la lenta dentro del límite (2.3). `/api/salud` con las dos dependencias congeladas, una sola y una lenta dentro del plazo (D20; 5.1). Redis pausado en el humo, por la API y por la web (6.3). |
| L-002 (faltante, vacía, en blanco, tipo, rango; nombra la variable sin el valor) | Configuración de `respaldar.sh` (2.1) y variables de Compose obligatorias (4.2). |
| L-003 (contar tests contra la línea de base) | 1.1 anota la línea de base con el commit; 8.1 compara. |
| L-004 (dos revisores por el mismo camino no son dos) | Los tests de los scripts corren con `pg_dump`, `pg_restore` y `docker` falsos en el `PATH`; el humo corre con los reales. El `request_id` y F13 se verifican en el humo por el proxy, un camino distinto de los tests unitarios del 1c (6.2, 6.3). El rompedor no repite ninguno: ataca por otro camino (un archivo ajeno con nombre parecido en la carpeta, dos ciclos solapados, un reloj del host atrasado, una carpeta que es un symlink, un pedido a `/salud-web` mientras la base se pausa). |
| L-005 (verde es todo el workflow) | Cada tarea cierra con lint, formato, tipos y tests del lado tocado, más `shellcheck` sobre los scripts, que este cambio suma al CI (D19, 4.3); 8.1 corre el workflow entero, con `shellcheck`. |
| L-006 (lo destructivo apunta a `proptech`) | `restaurar.sh` usa siempre `docker compose -p proptech`, valida el destino con la expresión cerrada y rechaza la base en uso (D9; 3.1, 3.2); la retención borra sólo `proptech-*.dump` y nunca el del ciclo en curso (2.4); el humo baja el stack con `-p proptech` (6.1) y borra sólo `proptech_restauracion` y la carpeta temporal que creó (6.4). |
| L-007 (el error de una librería también es una salida) | El log de `respaldar.sh` sólo tiene eventos propios con valores fijos, nunca la salida de `pg_dump` ni `PGPASSWORD` (2.1, 2.3); `restaurar.sh` informa el paso que falló con un mensaje propio, nunca la salida de `docker` o `pg_restore` (3.2); el error tardío de una verificación de salud no llega al log (5.1); el traceback crudo y el `msg` no texto dejan de leerse (D21; 5.2). Cada uno con un test de marcador. |
| L-008 (fullmatch y sólo ASCII) | Enteros de la configuración (2.1), patrón de nombre de la retención (2.4), marca `.ultimo-ok` (2.5) y nombre de la base destino (3.1): expresión sobre el texto entero con `LC_ALL=C`, probada con espacios, tabulaciones, saltos de línea al principio y al final y dígitos no ASCII. F7c (5.2) es la lección llevada al extremo: un texto ajeno que no se puede validar con un patrón confiable no se lee. |
| L-009 (un arreglo en un módulo se prueba en su gemelo) | Los requisitos MODIFIED y su texto vigente son gemelos: se rebasaron (tabla de arriba) y 8.1 verifica que siguen alineados. `respaldar.sh` y `restaurar.sh` son gemelos: los dos fijan `LC_ALL=C` y llevan la misma batería de L-008 (2.1, 3.1). La configuración de `respaldar.sh` recibe las cinco formas de L-002 que ya prueban los arranques de la API y del worker (2.1). Los verificadores de base y de cola de `/api/salud` reciben los mismos casos (5.1). |
| L-010 (la corrida de cierre va después de la última vuelta) | 8.1 es la última tarea, se corre después de la última vuelta de correcciones y se repite si el código cambia después. |
| L-011 (un plazo que abandona un hilo no cancela su transacción) | `respaldar.sh` corta el volcado con `timeout --kill-after`, que mata al proceso; 2.3 verifica que el `pg_dump` falso ya no existe después del corte. En `/api/salud` el plazo abandona el hilo sin cancelarlo (D20): se acepta porque `SELECT 1` y `PING` no tienen efecto, y lo que sí tenía efecto, la línea de log tardía, se elimina (5.1). |
| L-012 (la deuda al primer cambio que usa la pieza) | F13, el duplicado y F7c tienen dueño explícito y su porqué ("Deuda del 1c que recibe este cambio"); lo que sale del alcance de este cambio también tiene dueño ("Fuera del cambio" de la propuesta). |
| L-013 (mutar sin commit exige copia y diff) | Toda verificación que se ve fallar contra algo mutado a propósito (el canario de `shellcheck` en 4.3, la copia de Compose en 6.1, la constante de 6.3) se hace sobre una copia o con una copia previa y un diff, y se dice en el informe. |

## Goals / Non-Goals

**Goals:**

- Que exista siempre un backup reciente de la base fuera de Docker, generado solo, y que cada corrida
  del CI pruebe que se restaura.
- Que ninguna operación de este cambio pueda borrar la base en uso ni archivos ajenos del host.
- Que el humo verifique de punta a punta lo que el 1c verificó por partes.

**Non-Goals:**

- Copia de backups fuera del servidor y cifrado (con el despliegue).
- Restaurar sobre la base en uso.
- Monitoreo o alertas externas.

## Decisions

### D9 · Backups: dónde, cada cuánto, cuánto pueden tardar y cómo salen del contenedor

- **Servicio `respaldos`** en Compose con `image: postgres:18.6-trixie` (el `pg_dump` de la misma
  versión que el servidor; el test exige que sea igual a la de `db`), `entrypoint:
  ["/usr/local/bin/respaldar.sh"]` montado desde `infra/respaldos/respaldar.sh:ro`, red `interna`
  únicamente, sin `ports`, `user: "${PROPTECH_UID:?falta PROPTECH_UID}:${PROPTECH_GID:?falta
  PROPTECH_GID}"`, `HOME=/tmp`, `${PROPTECH_DIR_RESPALDOS:?falta PROPTECH_DIR_RESPALDOS}:/respaldos`
  montado, ancla `x-logs`, y `depends_on` de `db` saludable y de `migraciones` completado (así el
  primer backup ya tiene `alembic_version` y `trabajos_hechos`).
- **Cómo sale sin red**: la red `interna` no tiene salida y no la necesita. El dump viaja de `db` a
  `respaldos` por la red interna (libpq) y queda en `/respaldos`, que es una **carpeta del host**
  montada (bind mount). El archivo existe en el disco del host apenas se escribe; no hay copia por
  red ni puerto abierto. **Por qué bind mount y no un volumen con nombre**: `docker compose down -v`
  borra los volúmenes con nombre (lo hace el propio humo) y se llevaría los backups junto con la base;
  una carpeta del host no la toca.
- **Dónde**: `PROPTECH_DIR_RESPALDOS`. En `.env.example`, `./datos-respaldos` (relativo a `infra/`,
  agregado a `.gitignore`). En el VPS, una ruta fuera del repositorio. Corre con el uid/gid del
  usuario del host para que los archivos sean suyos y no de un uid 999 que el host no conoce.
- **Cada cuánto**: uno al arrancar el servicio y después cada `RESPALDO_INTERVALO_SEGUNDOS`
  (default 86400). Diario alcanza para el volumen del MVP; el de arranque hace que "el backup se
  genera solo" se pueda comprobar en el humo sin esperar un día. **Descartado** cron en el contenedor:
  la imagen de PostgreSQL no lo trae y sumar un paquete por un `sleep` no se justifica.
- **Cuánto puede tardar (L-001, nuevo)**: `pg_dump` corre con `PGCONNECT_TIMEOUT=5` y dentro de
  `timeout --kill-after=5 "$RESPALDO_LIMITE_SEGUNDOS"` (coreutils, viene en la imagen; default 1800,
  rango 5..86400 y menor que el intervalo). Sin esto, una base pausada a mitad del volcado deja al
  servicio colgado para siempre con el `.ultimo-ok` envejeciendo, y el único aviso sería el
  healthcheck un día y medio después. Al cortarse se trata como cualquier falla.
- **Formato y nombre**: `pg_dump --format=custom` a `proptech-AAAAMMDDTHHMMSSZ.dump.parcial`, luego
  `pg_restore --list` sobre el archivo (verifica que se puede leer) y `mv` atómico a `.dump`. `umask
  077`: sólo el dueño lee. Después escribe `.ultimo-ok` con la hora (epoch).
- **Retención**: `RESPALDO_CONSERVAR` (default 14, dos semanas). Se borra lo que excede, más viejo
  primero, **sólo** archivos que cumplen por completo `proptech-[0-9]{8}T[0-9]{6}Z.dump` (no un glob
  `proptech-*.dump`, que también tomaría `proptech-copia-a-mano.dump`), con `LC_ALL=C` para el orden, y
  sólo después de un backup correcto. `.parcial` huérfanos de un ciclo anterior se borran al arrancar.
  **El archivo del ciclo en curso nunca se borra (M22)**: el orden es por nombre y el nombre sale del
  reloj; si el reloj del host atrasa, el backup recién generado ordena como el más viejo y una
  retención ingenua lo borraría, dejando como "último" uno de hace días. La retención excluye ese
  archivo por su nombre exacto y aplica el límite al resto (conserva el nuevo más los
  `RESPALDO_CONSERVAR - 1` más recientes por nombre).
- **Fallas**: si `pg_dump` o la verificación fallan o se cortan por el límite, se borra el `.parcial`,
  se loguea `respaldo_fallido` con nivel `error` y se espera al próximo ciclo sin terminar el proceso.
- **Nunca como root (M23)**: lo primero que hace el script, antes de validar nada, es rechazar uid 0
  (`id -u`), con un error que nombra `PROPTECH_UID`. Si alguien pone `PROPTECH_UID=0`, Compose correría
  el servicio como root y los backups (y la retención que borra) quedarían como root en el disco del
  host.
- **Validación de su configuración** (L-002, L-008) al arrancar: el script fija `LC_ALL=C` y valida
  cada entero con `[[ $valor =~ ^[1-9][0-9]{0,6}$ ]]` sobre el valor tal cual llegó (sin recortar),
  antes de usarlo en aritmética. **Sin ceros a la izquierda** porque Bash lee `060` como octal (48) y
  `08` como error; sin signo; a lo sumo 7 dígitos para no desbordar. Después, el rango: intervalo
  60..604800, conservar 1..365, límite 5..86400 y menor que el intervalo; carpeta existente y
  escribible. El error nombra la variable, nunca su valor ni `PGPASSWORD`.
- **Salud**: `respaldar.sh --salud` falla si `.ultimo-ok` no existe, si su contenido no cumple
  `^[0-9]{1,12}$` (validado igual que la configuración) o si es más viejo que 1,5 intervalos;
  healthcheck con `start_period: 120s`.
- **Logs** del script (L-007): líneas JSON con los mismos campos base del 1c (`ts`, `nivel`,
  `servicio:"respaldos"`, `evento`, `componente`), escritas con `printf` y valores fijos (nombre de
  archivo, duración, carpeta, nombre de variable). La salida estándar y de error de `pg_dump` y
  `pg_restore` va a `/dev/null`, nunca al log: puede traer nombres de tablas, valores o la cadena de
  conexión. Se pierde el detalle del error; se acepta, porque el operador puede repetir el volcado a
  mano con `docker compose -p proptech exec db pg_dump` y ver el error ahí.
- **Testeable sin Docker**: `respaldar.sh --una-vez` corre un ciclo y termina. Los tests de pytest lo
  ejecutan con `pg_dump`/`pg_restore` falsos en el `PATH` (que pueden fallar, escribir un marcador en
  su salida de error o dormir) para cubrir nombre, atomicidad, retención, falla, límite y
  configuración inválida.

### D9 (cont.) · Restauración con destino validado

- `infra/respaldos/restaurar.sh <archivo> [base_destino]` corre en el host, fija `LC_ALL=C` y usa
  siempre `docker compose -p proptech` (L-006). Destino por defecto `proptech_restauracion`.
- **Carpeta de trabajo (M21)**: el script resuelve primero la ruta absoluta del archivo de backup y
  después hace `cd` a `infra/` relativo a su propia ubicación, así Compose encuentra `compose.yaml` y
  `.env` (que necesita para interpolar las variables con `:?`) se lo llame desde donde se lo llame.
  **Descartado** `-f infra/compose.yaml` sin `cd`: Compose busca el `.env` en la carpeta del proyecto,
  y depender de `--project-directory` además de `-f` es una opción más para olvidarse.
- **Usuario de la base (M21)**: `docker compose exec` entra como root y `dropdb`, `createdb` y
  `pg_restore` sin `-U` intentan conectarse con el rol `root`, que no existe. El script pide al
  contenedor `printenv POSTGRES_USER` (igual que `POSTGRES_DB`, sin leer el `.env` desde Bash) y lo pasa
  con `-U "$usuario"` a las tres herramientas.
- **Orden**: (1) el archivo existe y es legible; (2) el destino cumple por completo
  `^proptech_[a-z0-9_]{1,50}$` con `[[ ... =~ ... ]]` sobre el valor tal cual llegó; (3) recién
  entonces pregunta la base en uso con `docker compose -p proptech exec -T db printenv POSTGRES_DB` y
  rechaza un destino igual, y pregunta `POSTGRES_USER`; (4) `dropdb --if-exists`, `createdb` y
  `pg_restore --no-owner`, los tres con `-U`, por la
  entrada estándar, cada uno con el nombre como argumento propio de `docker compose exec` (nunca dentro
  de un `sh -c`). Los pasos 1 y 2 no invocan `docker`; el 3 sólo invoca `printenv`. Los tests verifican
  los argumentos y la carpeta de trabajo que recibe el `docker` falso en cada invocación.
- **Por qué la expresión cerrada además del prefijo**: el prefijo solo deja pasar `proptech_x;DROP`,
  espacios, saltos de línea o mayúsculas que PostgreSQL trataría como otro nombre. El máximo de 50
  después del prefijo deja el nombre en 59 caracteres, debajo de los 63 de un identificador de
  PostgreSQL (más largo, PostgreSQL lo trunca y el nombre validado no sería el usado). `LC_ALL=C`
  porque en otras configuraciones regionales `[a-z]` puede incluir mayúsculas o letras acentuadas.
- **Por qué rechazar la base en uso aunque cumpla la expresión**: `POSTGRES_DB` podría llamarse
  `proptech_principal`; la expresión sola la aceptaría y `dropdb` la borraría.
- **Errores (L-007)**: si un paso falla, `restaurar.sh` termina con código distinto de 0 y un mensaje
  propio que nombra el paso (`dropdb`, `createdb`, `pg_restore`); la salida de error de `docker` y de
  las herramientas no se repite. Se acepta perder el detalle por la misma razón que en el respaldo.
- El humo lo corre y compara la revisión de Alembic de la base restaurada con la de la base en uso.

### D14 · Humo ampliado

- `infra/ci/humo.sh` exporta antes de levantar `PROPTECH_DIR_RESPALDOS` (una carpeta temporal creada
  con `mktemp -d`), `PROPTECH_UID=$(id -u)` y `PROPTECH_GID=$(id -g)` (en el CI el runner no es 1000).
- **Limpieza**: el `trap` hace `docker compose -p proptech down -v --remove-orphans` (B15, L-006: el
  `name: proptech` de `compose.yaml` ya lo fija, pero el comando que borra volúmenes no depende de que
  esa línea siga ahí; un test exige `-p proptech` en toda invocación de `docker compose` del humo),
  **después** verifica que el
  `.dump` siga en la carpeta (escenario "Sobrevive al borrado de volúmenes"; si no está, la salida del
  humo es distinta de 0 aunque el resto haya pasado) y recién entonces borra la carpeta temporal. Toda
  pausa (`db`, `redis`) se despausa en la limpieza aunque la verificación falle.
- Verificaciones nuevas, en este orden: (1) salud con `"cola":"ok"`; sólo `caddy` con puertos;
  `docker compose port redis 6379` vacío; usuario no root del proceso principal (PID 1 leído de
  `/proc/1/status`) en `worker`, `redis` y `respaldos`; `redis-cli ping` sin contraseña da `NOAUTH`.
  (2) `request_id`: uno elegido por el cliente vuelve distinto y el devuelto aparece en
  `docker compose logs api`; uno malicioso no aparece en los logs de ningún servicio; `GET /salud-web`
  devuelve un `X-Request-ID` que aparece en el log de la API. (3) Worker: `python -m
  proptech_worker.prueba encolar --fallar-veces 1` dentro de `api` termina con la clave en
  `trabajos_hechos` en menos de 30 s y el `request_id` en los logs del worker con un reintento; Redis
  pausado da 503 `cola: sin_conexion` en menos de 4 s, y `/salud-web` da 503 con `api: degradado`
  (F13 de punta a punta, D20). (4) Respaldos: un `.dump` apareció solo en
  menos de 2 minutos; `restaurar.sh` lo carga en `proptech_restauracion`, la revisión de Alembic
  coincide, existe `trabajos_hechos`, la revisión y las filas de `trabajos_hechos` de la base en uso no
  cambiaron, y se borra la base de restauración. (5) El comando de verificación de la semilla corre
  dentro de `api` con código 0.

### D15 · README

- "Cómo levantarlo" suma: las variables nuevas de `.env.example`, crear la carpeta de respaldos (con
  el usuario del host) antes del primer `docker compose up`, y "Cómo restaurar un backup" con
  `restaurar.sh` y su destino por defecto. Se verifica siguiendo sólo el README en un clon nuevo.
- **Nota de plataforma (M28)**: los scripts de `infra/` son de Bash; en Windows corren en WSL2 o en Git
  Bash, no en PowerShell ni en `cmd`.

### D19 · `shellcheck` en el CI (M28)

- Este cambio suma dos scripts de Bash que borran bases y archivos (`restaurar.sh`, `respaldar.sh`) y
  amplía `humo.sh`. El CI suma un paso de `shellcheck` con versión fijada (como toda herramienta del
  CI) sobre todos los `*.sh` de `infra/`, y falla ante cualquier hallazgo. Es parte del cambio, no
  condicionado: antes decía "si el CI lo corre", y no lo corría.
- Un canario (una copia de un script con una variable sin comillas) se ve fallar antes de dejar el
  paso. La versión exacta y la forma de correrlo (imagen oficial o paquete del runner) se fijan en el
  apply.

### D20 · `/api/salud` con plazo total y una sola línea por falla (F13 y `salud_degradada` duplicado)

- **El problema (F13)**: hoy las dos verificaciones corren una después de la otra, cada una con su
  plazo de 2 s. Con una dependencia congelada, `/api/salud` tarda 2 s más lo que tarde la otra (2,005 s
  medidos en el cierre del 1c) y la web, que corta a 2,000 s, informa `"api": "sin_conexion"` cuando la
  API sí contestó, con un 503 que la web tendría que mostrar como `"degradado"`. Con las dos
  congeladas, la API tarda 4 s.
- **Decisión**: las dos verificaciones arrancan juntas, cada una en su hilo, y comparten un plazo total
  `PLAZO_TOTAL_SALUD_S = 1.5` contado desde que arranca la primera. Vencido el plazo, la que no terminó
  es `sin_conexion`. La respuesta llega en 1,5 s más lo que tarda armarla, aunque las dos estén
  congeladas, y deja medio segundo de margen contra los 2 s de la web para el salto por la red interna.
  Se agrega una tercera dependencia sin tocar este cálculo: el tiempo es el de un plazo, no la suma.
- **Alternativa descartada: subir la cota de la web** (por ejemplo, a 5 s). Descartada porque (1) toca
  el contrato de `/salud-web` del 1c (el límite de 2 s y el escenario "corta a los 2 segundos"), con un
  requisito MODIFIED más en `trazabilidad-y-logs` y su riesgo de rebase; (2) deja el acoplamiento: la
  cota de la web tiene que ser mayor que la suma de los plazos de la API, y cada verificador nuevo la
  vuelve a romper sin que ningún test de la web se entere; (3) un chequeo de salud de 5 s es lento para
  quien lo consume. Revertir la elegida cuesta poco: una constante y volver al orden secuencial.
- **Lo que cambia para una dependencia lenta**: una base o un Redis que tardan entre 1,5 y 2 s, que
  hoy dan `ok`, pasan a `sin_conexion`. Se acepta: para un chequeo de salud, 1,5 s ya es una
  dependencia que no está sana. `test_ataque_salud_cola_lenta.py` se revisa contra el plazo nuevo.
- **Una sola línea por falla**: hoy, cuando vence el plazo, el pedido loguea `salud_degradada` con
  `TimeoutError`, y si después el hilo abandonado termina con un error, loguea otra línea (dos por
  pedido colgado). Cada verificación lleva una marca protegida con un lock: informa (y loguea) sólo el
  primero que llega, el plazo o el hilo; el que llega segundo no escribe nada. El hilo tardío tampoco
  pone su resultado en ningún lado que alguien lea.
- **L-011**: el plazo abandona el hilo, no lo cancela; la conexión que tomó del pool sigue ocupada
  hasta que el hilo termina, y `pool_timeout` acota la espera de los pedidos siguientes (como en el
  1c). Se acepta porque `SELECT 1` y `PING` no tienen ningún efecto que pueda confirmarse tarde; lo
  único con efecto era la línea de log tardía, que deja de existir.

### D21 · Los tracebacks crudos y los mensajes que no son texto no se leen (F7c)

- **El problema**: cuando un mensaje de log ya llega como un traceback formateado en texto (Starlette
  en `lifespan.startup.failed`), el formatter del 1c lo reemplaza por `traceback_crudo_descartado`
  pero sigue parseando ese texto para sacar `tipo_error` (la última línea con forma de nombre de
  excepción) y `traza` (las líneas `File "..."`). El rompedor del 1c mostró formas particulares en las
  que ese parseo saca datos del mensaje a esos campos. Además, un `msg` que no es texto ni excepción se
  convierte con su `__str__`, que puede devolver cualquier cosa.
- **Decisión (la recomendación del rompedor)**: no parsear el texto. Un traceback crudo da siempre
  `evento: traceback_crudo_descartado`, `tipo_error: "desconocido"` y `traza: []`. El evento se decide
  por `type(record.msg) is str` (una subclase de `str` puede redefinir `__str__`): si es exactamente
  texto, como hasta ahora; si es una excepción, `excepcion_como_mensaje` con el tipo y la traza del
  objeto (sin cambios, D-091); cualquier otra cosa, `mensaje_no_texto`, sin más campos. Se borran
  `_tipo_de_traceback_crudo`, `_traza_de_traceback_crudo` y sus patrones.
- **Alternativa descartada: endurecer el parseo** con más patrones. Descartada porque cada vuelta del
  1c cerró una forma y el rompedor encontró otra: un texto ajeno no se puede validar con un patrón
  confiable (L-008), así que lo seguro es no leerlo (L-007).
- **Lo que se pierde**: el tipo de error de un fallo de arranque que llega como traceback crudo. Se
  acepta: el proceso igual termina con su código, el operador lo reproduce a mano, y el arranque de la
  API y del worker ya valida la configuración con errores propios antes de llegar a ese camino.

## Risks / Trade-offs

- [Backups en el mismo disco que la base] → Protegen de un error humano o una migración rota, no de
  perder el servidor. La copia fuera del servidor y el cifrado se deciden con el despliegue; hasta
  entonces no hay datos reales (el piloto no empezó).
- [El bind mount escribe en el disco del host] → El servicio corre con el uid/gid del usuario del
  host, no como root, y la retención sólo borra nombres que cumplen la expresión completa de los
  backups. Una carpeta mal configurada (por ejemplo, `$HOME`) no pierde archivos ajenos, pero se
  llenaría de backups: el README pide una carpeta propia.
- [`dropdb` en `restaurar.sh`] → Destino validado con expresión cerrada, comparado con la base en
  uso y siempre en el proyecto `proptech`, con un test por cada rechazo. Es el motivo principal del
  nivel HIGH.
- [Reversión silenciosa de los requisitos del 1c al archivar el 1d] → Rebase hecho el 14/10 con la
  tabla de "Rebase sobre el 1c archivado"; la tarea 8.1 (a) verifica al cerrar que `openspec/specs/` no
  cambió desde entonces y, si cambió, se rehace.
- [El plazo total de 1,5 s marca como caída una dependencia lenta entre 1,5 y 2 s] → Se acepta (D20);
  para un chequeo de salud ya no está sana.
- [Sin el parseo, un fallo de arranque por traceback crudo pierde su tipo de error] → Se acepta (D21);
  el humo anota si aparece algún caso real (6.4).
- [El 1d suma código del backend que no es de respaldos (D20, D21)] → Son la deuda que el cierre del
  1c le asignó (D-091), dos tareas acotadas, y quedan dentro de la aprobación HIGH de este cambio.
- [Ocultar la salida de `pg_dump` y `pg_restore` dificulta el diagnóstico] → Se acepta (L-007); el
  evento propio dice qué paso falló y el operador puede repetirlo a mano.
- [El uid/gid del host como usuario del servicio] → En el CI el runner no es 1000; el humo exporta
  `PROPTECH_UID` y `PROPTECH_GID` antes de levantar.
- [Un backup diario puede perder hasta un día de datos] → Suficiente para el MVP sin datos reales;
  se revisa con el despliegue y el piloto.

## Migration Plan

- Al actualizar una copia local existente: copiar las variables nuevas de `.env.example` a `.env` y
  crear la carpeta de respaldos. Compose nombra la que falte.
- Para volver atrás: revertir el commit y `docker compose -p proptech down -v`. La carpeta de respaldos
  del host queda; se borra a mano si se quiere.
- Sin migraciones de base.

## Open Questions

Ninguna que cambie las specs o las tareas. Pendientes de la etapa de despliegue: destino y cifrado de
la copia fuera del servidor.
