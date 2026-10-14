## Context

Ver `proposal.md` (Why). Este cambio es el 1d: nace de partir `cola-logs-y-respaldos` (1c) en dos por
D-087. **D9 (respaldos) se mudó del diseño del 1c sin cambios de fondo** y conserva su número para que
se pueda rastrear; acá se amplía con lo que pidió la auditoría (límite por volcado, validación ASCII
de la configuración y del destino, errores de herramientas fuera del log). D14 (humo ampliado) y D15
(README) son nuevas. D1 a D4, D7, D8, D12, D13 y D16 a D18 viven en el diseño del 1c. D19 (shellcheck
en el CI) es nueva y, con los ajustes a D9, D14 y D15, sale de la tercera auditoría del socio (13/10):
rebase de los MODIFIED (M20), `restaurar.sh` con `-U` y carpeta propia (M21), retención con el reloj
atrasado (M22), rechazo de uid 0 (M23), `shellcheck` (M28) y `down -v` con `-p proptech` (B15).

Estado de partida esperado, con el 1c archivado:

- `infra/compose.yaml` (proyecto `proptech`): `db` (`postgres:18.6-trixie`, con `log_line_prefix`),
  `migraciones`, `api`, `worker`, `redis`, `web`, `caddy`; redes `borde` e `interna`
  (`internal: true`); ancla de rotación `x-logs` en todos los servicios.
- Migración `0002` con `trabajos_hechos`. Comando `python -m proptech_worker.prueba encolar` dentro de
  la imagen del backend. `/api/salud` informa `base` y `cola`; `/salud-web` existe; Caddy pisa
  `X-Request-ID`.
- `infra/ci/humo.sh` del 1a, sin cambios en el 1c: levanta con `--wait`, verifica salud, puertos, `db`
  sin mapeo, API y web sin root, imágenes sin `.env`, la home, y la base pausada y detenida.
- Las specs `entorno-de-ejecucion` e `integracion-continua` ya tienen el texto que dejó el 1c; los
  requisitos MODIFIED de este cambio parten de ese texto y le suman los respaldos. **Un MODIFIED
  reemplaza el requisito entero**: lo que el 1c haya sumado y este cambio no copie se revierte al
  archivar el 1d, y `openspec validate` no lo detecta (valida la forma, no compara contra el texto
  anterior). Por eso la tarea 0.1, después de archivar el 1c, compara requisito por requisito el texto
  archivado con el de este cambio y pega el diff. Al 14/10 este cambio ya copia lo que la tercera
  auditoría sumó al 1c en esos requisitos (la red de salida del worker y las contraseñas como secreto).

**Si el 1c no está archivado** cuando arranque el constructor, este cambio no empieza: depende de su
worker, su comando de prueba y su `request_id` para el humo, y de su texto de las specs.

**Gobernanza HIGH** (proposal.md): no se construye sin la aprobación escrita y fechada de uno de los dos socios (Juani o Alberto) en la propuesta (D-094).

## Cómo aplica cada lección

| Lección | Dónde se aplica en este cambio |
|---|---|
| L-001 (apagada, que no responde y lenta, con cota de tiempo) | El volcado contra una base que no responde se corta por `RESPALDO_LIMITE_SEGUNDOS` (D9; tarea 2.3, con `pg_dump` falso que no termina y cota afirmada); la base apagada (2.3) y la lenta dentro del límite (2.3). Redis pausado en el humo con la cota de 4 s (5.3). |
| L-002 (faltante, vacía, en blanco, tipo, rango; nombra la variable sin el valor) | Configuración de `respaldar.sh` (2.1) y variables de Compose obligatorias (4.2). |
| L-003 (contar tests contra la línea de base) | 1.1 anota la línea de base; 7.1 compara. |
| L-004 (dos revisores por el mismo camino no son dos) | Los tests de los scripts corren con `pg_dump`, `pg_restore` y `docker` falsos en el `PATH`; el humo corre con los reales. El rompedor no repite ninguno de los dos: ataca por otro camino (un archivo ajeno con nombre parecido en la carpeta, dos ciclos solapados, un reloj del host atrasado, una carpeta que es un symlink). |
| L-005 (verde es todo el workflow) | Cada tarea cierra con lint, formato, tipos y tests del lado tocado, más `shellcheck` sobre los scripts, que este cambio suma al CI (D19, 4.3); 7.1 corre el workflow entero. |
| L-006 (lo destructivo apunta a `proptech`) | `restaurar.sh` usa siempre `docker compose -p proptech`, valida el destino con la expresión cerrada y rechaza la base en uso (D9; 3.1, 3.2); la retención borra sólo `proptech-*.dump` y nunca el del ciclo en curso (2.4); el humo baja el stack con `-p proptech` (5.1) y borra sólo `proptech_restauracion` y la carpeta temporal que creó (5.4). |
| L-007 (el error de una librería también es una salida) | El log de `respaldar.sh` sólo tiene eventos propios con valores fijos, nunca la salida de `pg_dump` ni `PGPASSWORD` (2.1, 2.3); `restaurar.sh` informa el paso que falló con un mensaje propio, nunca la salida de `docker` o `pg_restore` (3.2). Cada uno con un test de marcador. |
| L-008 (fullmatch y sólo ASCII) | Enteros de la configuración (2.1), marca `.ultimo-ok` (2.5) y nombre de la base destino (3.1): expresión sobre el texto entero con `LC_ALL=C`, probada con espacios, tabulaciones, saltos de línea al principio y al final y dígitos no ASCII. |
| L-009 (un arreglo en un módulo se prueba en su gemelo) | Los requisitos MODIFIED de este cambio y su texto archivado por el 1c son gemelos: 0.1 los compara. `respaldar.sh` y `restaurar.sh` son gemelos (dos scripts de Bash que validan entrada externa): los dos fijan `LC_ALL=C` y llevan la misma batería de L-008 (2.1, 3.1). La configuración de `respaldar.sh` recibe las mismas cinco formas de L-002 que ya prueban los arranques de la API y del worker (2.1). |

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
  pausado da 503 `cola: sin_conexion` en menos de 4 s. (4) Respaldos: un `.dump` apareció solo en
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
- [Reversión silenciosa de los requisitos del 1c al archivar el 1d] → Tarea 0.1: diff requisito por
  requisito contra los specs archivados, pegado en la tarea.
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
