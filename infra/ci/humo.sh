#!/usr/bin/env bash
# Prueba de humo del stack completo detrás de Caddy (D9, D14).
set -euo pipefail

# D6 (tarea 2.1): pasos con nombre. `paso N "descripción"` reemplaza el
# `echo "--- (N) descripción ---"` suelto de antes; el `trap ... ERR` de
# pasos.sh nombra número, descripción, línea y comando si algo del paso
# falla. Se fuentea con la ruta del script (antes del `cd` de abajo).
# shellcheck source=infra/ci/pasos.sh
source "$(dirname "${BASH_SOURCE[0]}")/pasos.sh"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  echo "infra/.env no existe; generándolo desde .env.example para el CI" >&2
  cp .env.example .env
fi

SENUELO_BACKEND="../backend/.env"
SENUELO_WEB="../web/.env"

# D14: la carpeta de respaldos, el uid y el gid del host se exportan ANTES de
# levantar, así Compose se los pasa al servicio `respaldos` (igual que en el
# README: sin esto, "falta PROPTECH_DIR_RESPALDOS" detendría el `up`). En el
# CI el runner no es 1000: por eso `id -u`/`id -g`, nunca un valor fijo.
CARPETA_RESPALDOS_HUMO="$(mktemp -d)"
export PROPTECH_DIR_RESPALDOS="$CARPETA_RESPALDOS_HUMO"
PROPTECH_UID="$(id -u)"
PROPTECH_GID="$(id -g)"
export PROPTECH_UID
export PROPTECH_GID

# Todo lo que invoca "compose" en este script pasa por acá (L-006): el
# proyecto es siempre `proptech`, sin depender de que `name: proptech` siga
# en compose.yaml (lo que de verdad hace falta para lo destructivo, como
# `down -v`, es que no dependa de un archivo que alguien podría tocar).
compose() {
  docker compose -p proptech "$@"
}

STACK_LEVANTADO=0

limpiar() {
  local estado=$?
  echo "--- limpieza: compose down -v ---"
  # Toda pausa se despausa aunque la verificación que la causó haya fallado
  # (D14): si no, `compose down` igual la baja, pero dejarla pausada hasta
  # entonces es un estado que nadie pidió.
  compose unpause db >/dev/null 2>&1 || true
  compose unpause redis >/dev/null 2>&1 || true
  compose down -v --remove-orphans || true

  if [ "$STACK_LEVANTADO" = "1" ]; then
    # Escenario "Sobrevive al borrado de volúmenes": se verifica DESPUÉS de
    # `down -v` y ANTES de borrar la carpeta temporal. Si no sobrevivió, el
    # humo termina distinto de 0 aunque el resto haya pasado.
    if ! ls "$CARPETA_RESPALDOS_HUMO"/proptech-*.dump >/dev/null 2>&1; then
      echo "ERROR: no sobrevivió ningún backup a 'compose down -v'" >&2
      estado=1
    fi
  fi

  rm -f "$SENUELO_BACKEND" "$SENUELO_WEB"
  rm -rf "$CARPETA_RESPALDOS_HUMO"
  exit "$estado"
}
trap limpiar EXIT

echo "contenido-senuelo-no-es-un-secreto-real" > "$SENUELO_BACKEND"
echo "contenido-senuelo-no-es-un-secreto-real" > "$SENUELO_WEB"

paso 0 "compose up --build -d --wait"
compose up --build -d --wait
STACK_LEVANTADO=1

# Se piden una sola vez y se reusan (en vez de un `printenv` nuevo cada vez
# que hacen falta): el usuario y el nombre de la base en uso no cambian
# durante todo el humo.
USUARIO_DB="$(compose exec -T db printenv POSTGRES_USER)"
BASE_EN_USO="$(compose exec -T db printenv POSTGRES_DB)"

# D11, D12 (tarea 9.1): dos administraciones con dos complejos cada una,
# sembradas con el rol de arranque (bypassea RLS por ser superusuario, sin
# necesitar `set_config`) ANTES de pedir el backup manual más abajo, para
# que ese volcado puntual las tenga adentro.
ADMINISTRACION_HUMO_A="10000000-0000-0000-0000-000000000001"
ADMINISTRACION_HUMO_B="10000000-0000-0000-0000-000000000002"
compose exec -T db psql -U "$USUARIO_DB" -d "$BASE_EN_USO" -v ON_ERROR_STOP=1 <<SQL
insert into administracion (id, nombre) values
  ('$ADMINISTRACION_HUMO_A', 'Administración A del humo'),
  ('$ADMINISTRACION_HUMO_B', 'Administración B del humo');
insert into complejo (id, administracion_id, nombre) values
  (gen_random_uuid(), '$ADMINISTRACION_HUMO_A', 'Complejo A1'),
  (gen_random_uuid(), '$ADMINISTRACION_HUMO_A', 'Complejo A2'),
  (gen_random_uuid(), '$ADMINISTRACION_HUMO_B', 'Complejo B1'),
  (gen_random_uuid(), '$ADMINISTRACION_HUMO_B', 'Complejo B2');
SQL
echo "ok: dos administraciones con dos complejos cada una, sembradas con $USUARIO_DB"

paso 1 "GET /api/salud por Caddy, con la cola conectada"
respuesta_salud=$(curl -fsS http://localhost/api/salud)
echo "$respuesta_salud"
echo "$respuesta_salud" | grep -q '"estado":"ok"'
echo "$respuesta_salud" | grep -q '"base":"ok"'
echo "$respuesta_salud" | grep -q '"cola":"ok"'

paso 1b "segundo up sobre el mismo volumen (D2, R1, vuelta 2): un reinicio no tiene que fallar"
# `down` sin `-v`: conserva los volúmenes (datos_postgres, datos_redis), como
# un reinicio real del servidor. Antes de R1, `migraciones` salía con 1 en
# esta segunda corrida (la secuencia IDENTITY de auditoria, ya del rol de
# arranque, no se puede reasignar) y api/worker/respaldos/caddy, que esperan
# `service_completed_successfully`, nunca arrancaban.
compose down
compose up -d --wait
echo "ok: el segundo up terminó con exit 0 y el stack quedó sano de nuevo"

paso 2 "sólo caddy publica puertos"
estado_ps=$(compose ps --format json)
servicios_con_puertos=$(echo "$estado_ps" | python3 -c "
import json, sys
# 'Publishers' incluye también los puertos de EXPOSE sin publicar al host,
# con PublishedPort en 0: sólo cuenta un puerto realmente publicado.
nombres = []
for linea in sys.stdin:
    linea = linea.strip()
    if not linea:
        continue
    datos = json.loads(linea)
    publicadores = datos.get('Publishers') or []
    if any(p.get('PublishedPort') for p in publicadores):
        nombres.append(datos['Service'])
print(','.join(sorted(set(nombres))))
")
echo "servicios con puertos publicados: $servicios_con_puertos"
[ "$servicios_con_puertos" = "caddy" ]

paso 3 "el servicio db no tiene puerto publicado hacia el host"
# No se usa una conexión TCP cruda a 127.0.0.1:5432: en una máquina de
# desarrollo puede haber OTRO PostgreSQL de otro proyecto escuchando ahí, lo
# que daría un falso "accesible" sin que este stack publique nada. Se
# pregunta directamente a este `compose` por el mapeo de puerto del servicio.
mapeo_db=$(compose port db 5432 2>/dev/null || true)
puerto_db_publicado="${mapeo_db##*:}"
if [ -n "$puerto_db_publicado" ] && [ "$puerto_db_publicado" != "0" ]; then
  echo "ERROR: db tiene un mapeo de puerto hacia el host: $mapeo_db" >&2
  exit 1
fi
echo "ok: db no tiene ports publicados (compose port db 5432 = '$mapeo_db')"

paso 3b "redis no tiene puerto publicado hacia el host"
mapeo_redis=$(compose port redis 6379 2>/dev/null || true)
puerto_redis_publicado="${mapeo_redis##*:}"
if [ -n "$puerto_redis_publicado" ] && [ "$puerto_redis_publicado" != "0" ]; then
  echo "ERROR: redis tiene un mapeo de puerto hacia el host: $mapeo_redis" >&2
  exit 1
fi
echo "ok: redis no tiene ports publicados (compose port redis 6379 = '$mapeo_redis')"

paso 3c "redis rechaza un comando sin contraseña (NOAUTH)"
salida_redis_sin_auth=$(compose exec -T redis redis-cli ping 2>&1 || true)
echo "$salida_redis_sin_auth"
echo "$salida_redis_sin_auth" | grep -q "NOAUTH"

paso 3d "la web no alcanza db:5432 ni redis:6379; la api sí (D10, tarea 8.1)"
# Conexión TCP cruda, nunca un ping de aplicación (D10): lo que prueba D10
# es que la RED no llega, no que el servicio del otro lado responda bien.
# `web` corre Node (ya lo usa el healthcheck de Compose); `api`, Python.
conectar_desde_web() {
  compose exec -T web node -e "
    const net = require('node:net');
    const s = net.createConnection({host: '$1', port: $2, timeout: 1500});
    s.on('connect', () => { console.log('CONECTO'); s.destroy(); process.exit(0); });
    s.on('timeout', () => { console.log('NO_CONECTO'); s.destroy(); process.exit(0); });
    s.on('error', () => { console.log('NO_CONECTO'); process.exit(0); });
  "
}
conectar_desde_api() {
  compose exec -T api python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1.5)
try:
    s.connect(('$1', $2))
    print('CONECTO')
except OSError:
    print('NO_CONECTO')
finally:
    s.close()
"
}
resultado_web_db=$(conectar_desde_web db 5432)
resultado_web_redis=$(conectar_desde_web redis 6379)
resultado_api_db=$(conectar_desde_api db 5432)
resultado_api_redis=$(conectar_desde_api redis 6379)
echo "web->db=$resultado_web_db web->redis=$resultado_web_redis api->db=$resultado_api_db api->redis=$resultado_api_redis"
[ "$resultado_web_db" = "NO_CONECTO" ]
[ "$resultado_web_redis" = "NO_CONECTO" ]
[ "$resultado_api_db" = "CONECTO" ]
[ "$resultado_api_redis" = "CONECTO" ]
echo "ok: la web no alcanza db ni redis por la red; la api alcanza las dos"

paso 4 "api, web, worker, migraciones, respaldos, redis y db corren como no root (PID 1)"
# D4 (tarea 3.3, MODIFIED de la requirement principal "Contenedores sin
# privilegios de root"): los siete, no sólo worker/redis/respaldos. Un
# `exec` nuevo (`id -u`) NO alcanza para ninguno: no ve qué usuario es
# de verdad el PID 1 cuando el propio entrypoint de la imagen baja de
# privilegios DESPUÉS de arrancar (gosu en `db`; `setpriv` en `redis`,
# no `gosu` — hallazgo real de la tarea 3.2) — un `exec` nuevo correría
# con el usuario de la IMAGEN, no el que terminó siendo el PID 1 (D14).
# `api`/`web`/`worker` no bajan así (imagen con `USER proptech`, nunca
# root), pero se leen igual por uniformidad con el resto.
uid_pid1() {
  local servicio="$1"
  compose exec -T "$servicio" sh -c "awk '/^Uid:/ {print \$2}' /proc/1/status"
}

uid_pid1_api=$(uid_pid1 api)
uid_pid1_web=$(uid_pid1 web)
uid_pid1_worker=$(uid_pid1 worker)
uid_pid1_respaldos=$(uid_pid1 respaldos)
uid_pid1_redis=$(uid_pid1 redis)
uid_pid1_db=$(uid_pid1 db)
# `migraciones` ya salió (de una sola corrida) para cuando llega este
# paso: D4 dice leer el usuario CONFIGURADO con un `run --no-deps`
# descartable en vez del proceso que ya terminó. Aceptable porque la
# imagen no cambia de usuario en ningún entrypoint propio (backend/
# Dockerfile: `USER proptech`, sin `ENTRYPOINT`) — el usuario del PID 1
# de la corrida real es el mismo que el de este `run` de un vistazo.
uid_pid1_migraciones=$(compose run --rm --no-deps --entrypoint sh migraciones \
  -c "awk '/^Uid:/ {print \$2}' /proc/1/status")
echo "uid pid1: api=$uid_pid1_api web=$uid_pid1_web worker=$uid_pid1_worker" \
  "migraciones=$uid_pid1_migraciones respaldos=$uid_pid1_respaldos" \
  "redis=$uid_pid1_redis db=$uid_pid1_db"
[ "$uid_pid1_api" != "0" ]
[ "$uid_pid1_web" != "0" ]
[ "$uid_pid1_worker" != "0" ]
[ "$uid_pid1_migraciones" != "0" ]
[ "$uid_pid1_respaldos" != "0" ]
[ "$uid_pid1_redis" != "0" ]
[ "$uid_pid1_db" != "0" ]
# `caddy` queda FUERA de este paso a propósito: se queda root (uid 0),
# declarado (D3) — nada que verificar acá, el 3.4 verifica que sus
# capacidades sean sólo NET_BIND_SERVICE.

paso 4b "privilegios y capacidades en el proceso vivo (NoNewPrivs y CapBnd)"
# D3, tarea 3.4: se lee el EFECTO en /proc/1/status, no el YAML (un
# cap_drop que el runtime ignore pasaría igual si sólo se mirara
# compose.yaml, L-018). La lista "justificada" de cada servicio salió de
# probarla en vivo (tarea 3.2): db retiene CHOWN+DAC_OVERRIDE+SETUID+
# SETGID (0xc3) en su PID 1 incluso después de bajar con gosu; caddy
# retiene sólo NET_BIND_SERVICE (0x400, se queda root). redis, en cambio,
# aunque el cap_add le da SETUID/SETGID/SETPCAP para que `setpriv` pueda
# bajar de privilegios, el PID 1 final queda con CapBnd VACÍO (setpriv no
# los retiene como gosu): la lista "vacía salvo db, redis y caddy" de la
# tarea no es cierta para redis en esta imagen (hallazgo real, verificado
# contra el proceso vivo); el valor correcto para redis es 0, igual que
# el resto.
nonewprivs_pid1() {
  compose exec -T "$1" sh -c "awk '/^NoNewPrivs:/ {print \$2}' /proc/1/status"
}

capbnd_pid1() {
  compose exec -T "$1" sh -c "awk '/^CapBnd:/ {print \$2}' /proc/1/status"
}

verificar_privilegios() {
  # Dos lecturas por separado (nunca una sola con las dos líneas juntas,
  # L-016/hallazgo real): el orden de los campos en /proc/[pid]/status
  # NO es "como se pide" sino el del kernel (CapBnd va ANTES que
  # NoNewPrivs); una extracción por posición de línea (en vez de por
  # nombre de campo) asignaría los valores al revés sin que ningún tipo
  # lo avise.
  local servicio="$1" capbnd_esperado="$2" nnp capbnd
  nnp=$(nonewprivs_pid1 "$servicio")
  capbnd=$(capbnd_pid1 "$servicio")
  echo "privilegios $servicio: NoNewPrivs=$nnp CapBnd=$capbnd (esperado $capbnd_esperado)"
  if [ "$nnp" != "1" ]; then
    echo "ERROR: $servicio no tiene NoNewPrivs:1 (tiene '$nnp')" >&2
    exit 1
  fi
  if [ "$capbnd" != "$capbnd_esperado" ]; then
    echo "ERROR: $servicio tiene CapBnd=$capbnd, se esperaba $capbnd_esperado" >&2
    exit 1
  fi
}

verificar_privilegios api 0000000000000000
verificar_privilegios web 0000000000000000
verificar_privilegios worker 0000000000000000
verificar_privilegios respaldos 0000000000000000
verificar_privilegios redis 0000000000000000
verificar_privilegios db 00000000000000c3
verificar_privilegios caddy 0000000000000400
echo "ok: NoNewPrivs y CapBnd correctos en los siete servicios vivos"

paso 5 "las imágenes construidas no contienen .env"
compose run --rm --no-deps --entrypoint sh api -c '[ ! -f /app/.env ]'
compose run --rm --no-deps --entrypoint sh web -c '[ ! -f /app/.env ]'

paso 6 "GET / responde 200 con HTML"
cuerpo_home=$(curl -fsS http://localhost/)
echo "$cuerpo_home" | grep -qi "<html"

paso 7 "request_id: el proxy pisa un valor elegido por el cliente"
# Caddy pisa SIEMPRE X-Request-ID con su propio UUID (Caddyfile), así que un
# valor mandado por el cliente nunca llega tal cual a la API ni a los logs.
# B4-bis (auditor, vuelta 2, L-017): tiene que ser un UUID CANÓNICO (el
# escenario de la spec, `trazabilidad-y-logs` › "Cliente que manda su propio
# número", dice "igual a un UUID que eligió"). Con un valor que no lo es,
# `validar_request_id` (`seguimiento.py`) lo descarta SOLA, sin que Caddy
# tenga que pisar nada: el chequeo pasaría igual aunque Caddy no pisara el
# encabezado, que es exactamente lo que este paso dice probar.
valor_cliente="c0ffee00-dada-4bad-8f00-0d15ea5e1234"
request_id_devuelto=$(curl -fsS -D - -o /dev/null -H "X-Request-ID: $valor_cliente" http://localhost/api/salud \
  | tr -d '\r' | awk -F': ' 'tolower($1)=="x-request-id" {print $2}')
echo "request_id devuelto: $request_id_devuelto"
[ -n "$request_id_devuelto" ]
[ "$request_id_devuelto" != "$valor_cliente" ]
sleep 1  # margen para que la línea del pedido llegue al log antes de leerlo.
if compose logs api | grep -q "$request_id_devuelto"; then
  echo "ok: el request_id devuelto aparece en el log de la API"
else
  echo "ERROR: el request_id devuelto no aparece en el log de la API" >&2
  exit 1
fi

paso 7b "request_id malicioso: no aparece en ningún log"
# curl (como la mayoría de los clientes HTTP modernos) rechaza un salto de
# línea real dentro del valor de un encabezado (de otro modo sería una
# inyección de encabezados); acá se manda lo más parecido que un cliente
# puede mandar de verdad: un `\n` literal (dos caracteres) junto con
# `<script>`, y de todos modos nunca debería sobrevivir porque Caddy pisa
# SIEMPRE el valor (Caddyfile), nunca lo deja pasar.
marcador_malicioso='marcador-malicioso-7f2c\nX-Inyectado: si<script>alert(1)</script>'
curl -fsS -o /dev/null -H "X-Request-ID: ${marcador_malicioso}" \
  http://localhost/api/salud || true
sleep 1
for servicio in caddy api web worker redis respaldos; do
  if compose logs "$servicio" 2>/dev/null | grep -qF "$marcador_malicioso"; then
    echo "ERROR: el valor malicioso apareció en el log de $servicio" >&2
    exit 1
  fi
done
echo "ok: el valor malicioso no aparece en ningún log"

paso 8 "/salud-web devuelve X-Request-ID y aparece en el log de la API"
respuesta_salud_web=$(curl -fsS -D - -o /tmp/salud_web_cuerpo.json http://localhost/salud-web)
request_id_salud_web=$(echo "$respuesta_salud_web" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-request-id" {print $2}')
cat /tmp/salud_web_cuerpo.json
rm -f /tmp/salud_web_cuerpo.json
echo "request_id de /salud-web: $request_id_salud_web"
[ -n "$request_id_salud_web" ]
sleep 1
if compose logs api | grep -q "$request_id_salud_web"; then
  echo "ok: el request_id de /salud-web aparece en el log de la API"
else
  echo "ERROR: el request_id de /salud-web no aparece en el log de la API" >&2
  exit 1
fi

paso 9 "worker: trabajo con un reintento, dentro del stack"
salida_encolar=$(compose exec -T api python -m proptech_worker.prueba encolar --fallar-veces 1)
echo "$salida_encolar"
clave_trabajo=$(echo "$salida_encolar" | awk -F= '/^clave=/ {print $2}')
request_id_trabajo=$(echo "$salida_encolar" | awk -F= '/^request_id=/ {print $2}')
[ -n "$clave_trabajo" ]
[ -n "$request_id_trabajo" ]

trabajo_encontrado=0
for _ in $(seq 1 30); do
  fila=$(compose exec -T db psql -U "$USUARIO_DB" \
    -d "$BASE_EN_USO" -tAc \
    "select 1 from trabajos_hechos where clave = '${clave_trabajo}'" 2>/dev/null || true)
  if [ "$(echo "$fila" | tr -d '[:space:]')" = "1" ]; then
    trabajo_encontrado=1
    break
  fi
  sleep 1
done
[ "$trabajo_encontrado" = "1" ]
echo "ok: el trabajo quedó en trabajos_hechos (clave=$clave_trabajo) en menos de 30s"

if compose logs worker | grep -q "$request_id_trabajo"; then
  if compose logs worker | grep "$request_id_trabajo" | grep -q "reintento_programado"; then
    echo "ok: el request_id del trabajo aparece en el log del worker junto a un reintento"
  else
    echo "ERROR: el request_id del trabajo está en el log del worker pero sin 'reintento_programado'" >&2
    exit 1
  fi
else
  echo "ERROR: el request_id del trabajo no aparece en el log del worker" >&2
  exit 1
fi

paso 9b "la api y el worker conectan como proptech_app, ni superusuario ni BYPASSRLS (D11, tarea 9.1)"
# `pg_stat_activity` filtrado por `application_name` (D8: la API arranca con
# "proptech-api", el worker con "proptech-worker"; dentro de una transacción
# queda "<prefijo>:<request_id>", así que LIKE con el prefijo alcanza a las
# dos formas). Ya hubo pedidos a la API (pasos 1, 6, 7, 8) y un trabajo del
# worker (paso 9) antes de este punto: las dos conexiones existen.
rol_de_conexion() {
  local prefijo="$1"
  compose exec -T db psql -U "$USUARIO_DB" -d "$BASE_EN_USO" -tAc "
    select distinct r.rolname || ',' || r.rolsuper || ',' || r.rolbypassrls
    from pg_stat_activity a join pg_roles r on r.rolname = a.usename
    where a.application_name like '${prefijo}%'
    limit 1
  "
}
rol_api=$(rol_de_conexion "proptech-api" | tr -d '[:space:]')
rol_worker=$(rol_de_conexion "proptech-worker" | tr -d '[:space:]')
echo "api: $rol_api | worker: $rol_worker"
# "true"/"false", no el "t"/"f" de psql (hallazgo real): concatenar un
# booleano con || lo castea a texto con su literal SQL, no con el formato
# de columna de psql.
[ "$rol_api" = "proptech_app,false,false" ]
[ "$rol_worker" = "proptech_app,false,false" ]
echo "ok: api y worker conectan como proptech_app, sin ser superusuario ni BYPASSRLS"

paso 10 "Redis pausado: /api/salud y /salud-web degradados, nunca colgados"
compose pause redis
inicio_ns=$(date +%s%N)
codigo_api_redis_pausado=$(curl -s -o /tmp/salud_redis_pausado.json -w '%{http_code}' http://localhost/api/salud || true)
fin_ns=$(date +%s%N)
duracion_ms=$(( (fin_ns - inicio_ns) / 1000000 ))
cat /tmp/salud_redis_pausado.json
echo "código: $codigo_api_redis_pausado, duración: ${duracion_ms}ms"
[ "$codigo_api_redis_pausado" = "503" ]
grep -q '"cola":"sin_conexion"' /tmp/salud_redis_pausado.json
rm -f /tmp/salud_redis_pausado.json
if [ "$duracion_ms" -ge 4000 ]; then
  echo "ERROR: /api/salud tardó ${duracion_ms}ms con Redis pausado (cota: 4000ms)" >&2
  compose unpause redis
  exit 1
fi

codigo_web_redis_pausado=$(curl -s -o /tmp/salud_web_redis_pausado.json -w '%{http_code}' http://localhost/salud-web || true)
cat /tmp/salud_web_redis_pausado.json
echo "código /salud-web: $codigo_web_redis_pausado"
# F13 (D20): la API responde DENTRO del límite de la web aunque Redis esté
# pausado (plazo total de 1,5s contra el límite de 2s de /salud-web), así
# que /salud-web ve "degradado" (la API contestó) y nunca "sin_conexion".
[ "$codigo_web_redis_pausado" = "503" ]
grep -q '"api":"degradado"' /tmp/salud_web_redis_pausado.json
rm -f /tmp/salud_web_redis_pausado.json
compose unpause redis
echo "ok: Redis pausado -> /api/salud y /salud-web degradados, Redis despausado"

paso 11 "backups: aparece uno solo, se restaura, no toca la base en uso"
dump_aparecio=0
for _ in $(seq 1 24); do
  if ls "$CARPETA_RESPALDOS_HUMO"/proptech-*.dump >/dev/null 2>&1; then
    dump_aparecio=1
    break
  fi
  sleep 5
done
[ "$dump_aparecio" = "1" ]
archivo_dump=$(find "$CARPETA_RESPALDOS_HUMO" -maxdepth 1 -name "proptech-*.dump" | sort | head -n 1)
echo "ok: apareció un backup en menos de 2 minutos: $archivo_dump"

# D11, D12 (tarea 9.1): el backup automático de arriba puede haber corrido
# ANTES de sembrar las dos administraciones (el healthcheck de `respaldos`
# sólo pasa cuando ya hubo un primer ciclo, D9): se pide uno manual
# (`--una-vez`, pensado para esto) y se usa el dump MÁS NUEVO —no
# necesariamente el único— para el resto de las verificaciones de este paso.
compose exec -T respaldos /usr/local/bin/respaldar.sh --una-vez
archivo_dump_reciente=""
for _ in $(seq 1 24); do
  archivo_dump_reciente=$(find "$CARPETA_RESPALDOS_HUMO" -maxdepth 1 -name "proptech-*.dump" | sort | tail -n 1)
  if [ -n "$archivo_dump_reciente" ] && [ "$archivo_dump_reciente" != "$archivo_dump" ]; then
    break
  fi
  sleep 5
done
[ -n "$archivo_dump_reciente" ]
[ "$archivo_dump_reciente" != "$archivo_dump" ]
archivo_dump="$archivo_dump_reciente"
echo "ok: backup manual con las dos administraciones sembradas: $archivo_dump"

# B5 (auditor, vuelta 2, L-016): `respaldos` es un script de bash, nunca usa
# `FormateadorJSON` (D7): contar estos eventos sólo en sus logs es un cero
# GARANTIZADO, no una observación (no es el servicio que F7c esperaba ver).
# `traceback_crudo_descartado` y `mensaje_no_texto` sólo los puede emitir
# `api` o `worker` (los dos usan `configurar_logs`); `salud_degradada` (5.1)
# sólo `api`. Se cuenta en los dos, sumado.
contar_evento() {
  local patron="$1"
  shift
  local total=0 servicio cantidad
  for servicio in "$@"; do
    cantidad=$(compose logs "$servicio" 2>/dev/null | grep -c "$patron" || true)
    total=$(( total + cantidad ))
  done
  echo "$total"
}
cantidad_traceback_crudo=$(contar_evento "traceback_crudo_descartado" api worker)
cantidad_mensaje_no_texto=$(contar_evento "mensaje_no_texto" api worker)
cantidad_salud_degradada=$(contar_evento "salud_degradada" api worker)
echo "traceback_crudo_descartado en logs de api/worker: $cantidad_traceback_crudo"
echo "mensaje_no_texto en logs de api/worker: $cantidad_mensaje_no_texto"
echo "salud_degradada en logs de api/worker: $cantidad_salud_degradada"

# D1/D3 (cambio 2a): `api` ya no tiene las credenciales del migrador (sólo
# las de la app), así que "alembic current" adentro de `api` ya no funciona.
# La revisión en uso se lee directo de `alembic_version`, igual que
# `revision_restaurada` más abajo: el rol de arranque (`db`) puede leerla sin
# depender de qué rol sea dueño de la tabla.
revision_en_uso=$(compose exec -T db psql -U "$USUARIO_DB" \
  -d "$BASE_EN_USO" -tAc "select version_num from alembic_version")
filas_antes=$(compose exec -T db psql -U "$USUARIO_DB" \
  -d "$BASE_EN_USO" -tAc "select count(*) from trabajos_hechos")

bash respaldos/restaurar.sh "$archivo_dump" proptech_restauracion

revision_restaurada=$(compose exec -T db psql -U "$USUARIO_DB" \
  -d proptech_restauracion -tAc "select version_num from alembic_version")
existe_trabajos_hechos=$(compose exec -T db psql -U "$USUARIO_DB" \
  -d proptech_restauracion -tAc "select to_regclass('public.trabajos_hechos') is not null")

echo "revisión en uso=$(echo "$revision_en_uso" | tr -d '[:space:]') revisión restaurada=$(echo "$revision_restaurada" | tr -d '[:space:]')"
[ "$(echo "$revision_restaurada" | tr -d '[:space:]')" = "$(echo "$revision_en_uso" | tr -d '[:space:]')" ]
[ "$(echo "$existe_trabajos_hechos" | tr -d '[:space:]')" = "t" ]

# D11, D12 (tarea 9.1): las dos administraciones sembradas arriba, con dos
# complejos cada una, llegaron en el volcado — contadas con el rol de
# arranque (bypassea RLS, D1), nunca con la app (vería cero: sin tenant).
conteo_complejos_a=$(compose exec -T db psql -U "$USUARIO_DB" -d proptech_restauracion \
  -tAc "select count(*) from complejo where administracion_id = '$ADMINISTRACION_HUMO_A'")
conteo_complejos_b=$(compose exec -T db psql -U "$USUARIO_DB" -d proptech_restauracion \
  -tAc "select count(*) from complejo where administracion_id = '$ADMINISTRACION_HUMO_B'")
echo "conteo por administración en la base restaurada: A=$(echo "$conteo_complejos_a" | tr -d '[:space:]') B=$(echo "$conteo_complejos_b" | tr -d '[:space:]')"
[ "$(echo "$conteo_complejos_a" | tr -d '[:space:]')" = "2" ]
[ "$(echo "$conteo_complejos_b" | tr -d '[:space:]')" = "2" ]

# D11, D12: el volcado se lleva el FORCE y las políticas (son parte del
# esquema, no de los datos) — se verifican en la base restaurada, no en la
# que ya está en uso (que el guardián de la 3.2 ya cubre en los tests).
rls_forzada_administracion=$(compose exec -T db psql -U "$USUARIO_DB" -d proptech_restauracion \
  -tAc "select relforcerowsecurity from pg_class where relname = 'administracion'")
rls_forzada_complejo=$(compose exec -T db psql -U "$USUARIO_DB" -d proptech_restauracion \
  -tAc "select relforcerowsecurity from pg_class where relname = 'complejo'")
politicas_administracion=$(compose exec -T db psql -U "$USUARIO_DB" -d proptech_restauracion \
  -tAc "select count(*) from pg_policies where tablename = 'administracion'")
politicas_complejo=$(compose exec -T db psql -U "$USUARIO_DB" -d proptech_restauracion \
  -tAc "select count(*) from pg_policies where tablename = 'complejo'")
echo "relforcerowsecurity administracion=$(echo "$rls_forzada_administracion" | tr -d '[:space:]')" \
  "complejo=$(echo "$rls_forzada_complejo" | tr -d '[:space:]')" \
  "políticas administracion=$(echo "$politicas_administracion" | tr -d '[:space:]')" \
  "complejo=$(echo "$politicas_complejo" | tr -d '[:space:]')"
[ "$(echo "$rls_forzada_administracion" | tr -d '[:space:]')" = "t" ]
[ "$(echo "$rls_forzada_complejo" | tr -d '[:space:]')" = "t" ]
[ "$(echo "$politicas_administracion" | tr -d '[:space:]')" -gt 0 ]
[ "$(echo "$politicas_complejo" | tr -d '[:space:]')" -gt 0 ]
echo "ok: la base restaurada tiene el FORCE y las políticas de D5, y el conteo por administración (2, 2)"

revision_en_uso_despues=$(compose exec -T db psql -U "$USUARIO_DB" \
  -d "$BASE_EN_USO" -tAc "select version_num from alembic_version")
filas_despues=$(compose exec -T db psql -U "$USUARIO_DB" \
  -d "$BASE_EN_USO" -tAc "select count(*) from trabajos_hechos")
[ "$(echo "$revision_en_uso_despues" | tr -d '[:space:]')" = "$(echo "$revision_en_uso" | tr -d '[:space:]')" ]
[ "$(echo "$filas_despues" | tr -d '[:space:]')" = "$(echo "$filas_antes" | tr -d '[:space:]')" ]
echo "ok: la base en uso no cambió (revisión y filas de trabajos_hechos iguales antes y después)"

compose exec -T db dropdb --if-exists -U "$USUARIO_DB" proptech_restauracion
echo "ok: se borró la base de restauración"

paso 12 "comando de verificación de la semilla, dentro de api"
compose exec -T api python -m proptech_core.compartido.semilla /app/config/semilla/edificio-ejemplo.yaml

paso 13 "base pausada (congelada, no caída) -> 503 degradado, dentro de un tiempo acotado"
# "pause" congela el proceso de postgres (cgroup freezer): a diferencia de "stop", el
# socket de escucha sigue existiendo y el kernel acepta el SYN, pero nadie en el
# contenedor atiende el handshake de la aplicación. Es el caso que `connect_timeout=2`
# (ver `salud.py`) existe para cubrir: sin ese timeout, este escenario colgaría el
# verificador en vez de devolver 503.
compose pause db
inicio_ns=$(date +%s%N)
codigo=$(curl -s -o /tmp/salud_pausada.json -w '%{http_code}' http://localhost/api/salud || true)
fin_ns=$(date +%s%N)
compose unpause db
duracion_ms=$(( (fin_ns - inicio_ns) / 1000000 ))
cat /tmp/salud_pausada.json
echo "código: $codigo, duración: ${duracion_ms}ms"
[ "$codigo" = "503" ]
grep -q '"estado":"degradado"' /tmp/salud_pausada.json
grep -q '"base":"sin_conexion"' /tmp/salud_pausada.json
rm -f /tmp/salud_pausada.json
if [ "$duracion_ms" -ge 4000 ]; then
  echo "ERROR: /api/salud tardó ${duracion_ms}ms con la base pausada (cota: 4000ms)" >&2
  exit 1
fi

paso 14 "base caída -> 503 degradado"
compose stop db
sleep 1
codigo=$(curl -s -o /tmp/salud_degradada.json -w '%{http_code}' http://localhost/api/salud || true)
cat /tmp/salud_degradada.json
echo "código: $codigo"
[ "$codigo" = "503" ]
grep -q '"estado":"degradado"' /tmp/salud_degradada.json
grep -q '"base":"sin_conexion"' /tmp/salud_degradada.json
rm -f /tmp/salud_degradada.json

echo "HUMO OK"
