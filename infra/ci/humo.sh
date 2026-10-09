#!/usr/bin/env bash
# Prueba de humo del stack completo detrás de Caddy (D9).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  echo "infra/.env no existe; generándolo desde .env.example para el CI" >&2
  cp .env.example .env
fi

SENUELO_BACKEND="../backend/.env"
SENUELO_WEB="../web/.env"

limpiar() {
  local estado=$?
  echo "--- limpieza: docker compose down -v ---"
  docker compose down -v --remove-orphans || true
  rm -f "$SENUELO_BACKEND" "$SENUELO_WEB"
  exit "$estado"
}
trap limpiar EXIT

echo "contenido-senuelo-no-es-un-secreto-real" > "$SENUELO_BACKEND"
echo "contenido-senuelo-no-es-un-secreto-real" > "$SENUELO_WEB"

echo "--- docker compose up --build -d --wait ---"
docker compose up --build -d --wait

echo "--- (1) GET /api/salud por Caddy ---"
respuesta_salud=$(curl -fsS http://localhost/api/salud)
echo "$respuesta_salud"
echo "$respuesta_salud" | grep -q '"estado":"ok"'
echo "$respuesta_salud" | grep -q '"base":"ok"'

echo "--- (2) sólo caddy publica puertos ---"
estado_ps=$(docker compose ps --format json)
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

echo "--- (3) el servicio db no tiene puerto publicado hacia el host ---"
# No se usa una conexión TCP cruda a 127.0.0.1:5432: en una máquina de
# desarrollo puede haber OTRO PostgreSQL de otro proyecto escuchando ahí, lo
# que daría un falso "accesible" sin que este stack publique nada. Se
# pregunta directamente a este `compose` por el mapeo de puerto del servicio.
mapeo_db=$(docker compose port db 5432 2>/dev/null || true)
puerto_db_publicado="${mapeo_db##*:}"
if [ -n "$puerto_db_publicado" ] && [ "$puerto_db_publicado" != "0" ]; then
  echo "ERROR: db tiene un mapeo de puerto hacia el host: $mapeo_db" >&2
  exit 1
fi
echo "ok: db no tiene ports publicados (docker compose port db 5432 = '$mapeo_db')"

echo "--- (4) api y web corren como no root ---"
uid_api=$(docker compose exec -T api id -u)
uid_web=$(docker compose exec -T web id -u)
echo "uid api=$uid_api uid web=$uid_web"
[ "$uid_api" != "0" ]
[ "$uid_web" != "0" ]

echo "--- (5) las imágenes construidas no contienen .env ---"
docker compose run --rm --no-deps --entrypoint sh api -c '[ ! -f /app/.env ]'
docker compose run --rm --no-deps --entrypoint sh web -c '[ ! -f /app/.env ]'

echo "--- (6) GET / responde 200 con HTML ---"
cuerpo_home=$(curl -fsS http://localhost/)
echo "$cuerpo_home" | grep -qi "<html"

echo "--- (7) base pausada (congelada, no caída) -> 503 degradado, dentro de un tiempo acotado ---"
# "pause" congela el proceso de postgres (cgroup freezer): a diferencia de "stop", el
# socket de escucha sigue existiendo y el kernel acepta el SYN, pero nadie en el
# contenedor atiende el handshake de la aplicación. Es el caso que `connect_timeout=2`
# (ver `salud.py`) existe para cubrir: sin ese timeout, este escenario colgaría el
# verificador en vez de devolver 503.
docker compose pause db
inicio_ns=$(date +%s%N)
codigo=$(curl -s -o /tmp/salud_pausada.json -w '%{http_code}' http://localhost/api/salud || true)
fin_ns=$(date +%s%N)
docker compose unpause db
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

echo "--- (8) base caída -> 503 degradado ---"
docker compose stop db
sleep 1
codigo=$(curl -s -o /tmp/salud_degradada.json -w '%{http_code}' http://localhost/api/salud || true)
cat /tmp/salud_degradada.json
echo "código: $codigo"
[ "$codigo" = "503" ]
grep -q '"estado":"degradado"' /tmp/salud_degradada.json
grep -q '"base":"sin_conexion"' /tmp/salud_degradada.json
rm -f /tmp/salud_degradada.json

echo "HUMO OK"
