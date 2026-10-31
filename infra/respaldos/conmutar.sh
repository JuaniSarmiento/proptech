#!/usr/bin/env bash
# Conmuta la aplicación a una base ya restaurada (D6): verifica, contra la
# base destino misma, que (1) existe y acepta conexión, (2) su revisión de
# Alembic es exactamente la cabeza del repositorio (derivada, nunca escrita
# a mano) y (3) sus tablas de negocio conservan Row-Level Security forzada
# y las MISMAS políticas que la base en uso (comparación de contenido, no de
# cantidad, L-018). Recién si las tres pasan reescribe `POSTGRES_DB` en
# `infra/.env` (con resguardo en `.env.anterior`) y levanta los servicios
# que se conectan a la base. Nunca borra ni modifica la base anterior.
# Uso: conmutar.sh <base_destino>
set -euo pipefail
export LC_ALL=C

error_salir() {
  echo "error: $1" >&2
  exit 1
}

DESTINO="${1:-}"

# (1) El destino cumple la expresión cerrada, igual que `restaurar.sh`
# (L-006, L-008). Todavía no invoca docker.
if [[ ! "$DESTINO" =~ ^proptech_[a-z0-9_]{1,50}$ ]]; then
  error_salir "DESTINO: '$DESTINO' no cumple el patrón de un nombre de base válido"
fi

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# CONMUTAR_INFRA_DIR: SÓLO para los tests (nunca en producción): sin esto,
# un test que llega a reescribir `.env` lo haría sobre el `infra/.env` REAL
# del checkout, con sus contraseñas (hallazgo real al escribir la primera
# versión de los tests: dos corridas dejaron `infra/.env` con
# `POSTGRES_DB=proptech_restaurada` de verdad, ver tasks.md 8.3).
INFRA_DIR="$(cd "${CONMUTAR_INFRA_DIR:-$SCRIPT_DIR/..}" && pwd)"
cd "$INFRA_DIR"

# PROPTECH_COMPOSE_PROYECTO: sólo para el ensayo aislado, igual que
# `restaurar.sh` (L-006, L-047).
compose() {
  docker compose -p "${PROPTECH_COMPOSE_PROYECTO:-proptech}" "$@"
}

# (2) Recién acá se invoca docker: la base en uso (un solo printenv), y se
# rechaza un destino que coincida con ella aunque cumpla la expresión.
base_en_uso="$(compose exec -T db printenv POSTGRES_DB)"
if [ "$DESTINO" = "$base_en_uso" ]; then
  error_salir "DESTINO: '$DESTINO' es la base en uso, no se puede conmutar sobre ella"
fi

usuario="$(compose exec -T db printenv POSTGRES_USER)"

psql_en() {
  local base="$1"
  shift
  compose exec -T db psql -U "$usuario" -d "$base" -tAc "$1"
}

# Verificación 1: la base existe y acepta conexión.
if ! psql_en "$DESTINO" "SELECT 1" >/dev/null 2>/dev/null; then
  error_salir "verificación 1 (existencia): '$DESTINO' no existe o no acepta conexión"
fi

# Verificación 2: la revisión de Alembic de la base destino coincide con la
# cabeza del repositorio. La cabeza se DERIVA preguntándole a Alembic
# (`compose run`, sin tocar ninguna base), nunca se escribe a mano: una
# cabeza fija quedaría vieja en el próximo change y el chequeo pasaría a
# mentir (la misma deuda que tuvo `ensayo-roles.sh`, D7 del 6).
cabeza_cruda="$(compose run --rm --no-deps --entrypoint '' migraciones alembic heads 2>/dev/null)" \
  || error_salir "verificación 2 (migraciones): no se pudo derivar la cabeza de Alembic"
cabeza="$(printf '%s\n' "$cabeza_cruda" | awk '{print $1}' | head -n1)"
if [ -z "$cabeza" ]; then
  error_salir "verificación 2 (migraciones): no se pudo derivar la cabeza de Alembic"
fi

revision_destino="$(psql_en "$DESTINO" "SELECT version_num FROM alembic_version" 2>/dev/null | tr -d '[:space:]')" \
  || true
if [ "$revision_destino" != "$cabeza" ]; then
  error_salir "verificación 2 (migraciones): '$DESTINO' está en '${revision_destino:-ninguna}', se esperaba la cabeza '$cabeza'"
fi

# Verificación 3: Row-Level Security forzada y las MISMAS políticas que la
# base en uso, tabla por tabla — el EFECTO en el catálogo (L-018), no una
# línea del compose ni el nombre de una política. Se compara contra la base
# en uso (que ya está operando, y por lo tanto ya pasó este mismo control
# alguna vez) en vez de contra una lista fija de tablas escrita a mano: así
# el chequeo no queda viejo cuando un change futuro agregue una tabla de
# negocio nueva.
consulta_rls="SELECT t.tablename, t.rowsecurity, t.forcerowsecurity, coalesce(string_agg(p.polname || '|' || p.polcmd || '|' || coalesce(p.qual::text,'') || '|' || coalesce(p.with_check::text,''), ';' ORDER BY p.polname), '') FROM pg_tables t LEFT JOIN pg_policy p ON p.polrelid = (quote_ident(t.schemaname)||'.'||quote_ident(t.tablename))::regclass WHERE t.schemaname='public' GROUP BY 1,2,3 ORDER BY 1"

politicas_base_en_uso="$(psql_en "$base_en_uso" "$consulta_rls" 2>/dev/null)" \
  || error_salir "verificación 3 (seguridad de filas): no se pudo leer la base en uso"
politicas_destino="$(psql_en "$DESTINO" "$consulta_rls" 2>/dev/null)" \
  || error_salir "verificación 3 (seguridad de filas): no se pudo leer '$DESTINO'"

if [ "$politicas_base_en_uso" != "$politicas_destino" ]; then
  error_salir "verificación 3 (seguridad de filas): '$DESTINO' no conserva la misma Row-Level Security/políticas que la base en uso"
fi

# Las tres verificaciones pasaron: recién ACÁ se toca algo.
if [ -f .env ]; then
  cp -p .env .env.anterior
fi

if [ -f .env ]; then
  # Reemplaza sólo la línea de POSTGRES_DB, línea por línea: las demás
  # (incluidas las contraseñas) quedan byte a byte idénticas.
  tmp_env="$(mktemp)"
  awk -v destino="$DESTINO" '
    BEGIN { reemplazado = 0 }
    /^POSTGRES_DB=/ { print "POSTGRES_DB=" destino; reemplazado = 1; next }
    { print }
    END { if (!reemplazado) print "POSTGRES_DB=" destino }
  ' .env > "$tmp_env"
  mv -- "$tmp_env" .env
else
  error_salir "conmutación: falta infra/.env; no hay POSTGRES_DB para reemplazar"
fi

export POSTGRES_DB="$DESTINO"
if ! compose up -d --no-deps api worker respaldos >/dev/null 2>/dev/null; then
  error_salir "conmutación: docker compose up falló al levantar los servicios; infra/.env.anterior conserva el valor previo"
fi

# Verificación final: la API responde. Si no, se informa sin deshacer solo
# (D6: revertir es decisión de quien opera, con .env.anterior a mano).
sleep 2
if ! compose exec -T api python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/salud', timeout=5)" >/dev/null 2>/dev/null; then
  error_salir "conmutación: la base quedó en '$DESTINO' pero GET /api/salud no respondió 200; infra/.env.anterior conserva el valor previo"
fi

echo "conmutado a '$DESTINO' (antes: '$base_en_uso'); infra/.env.anterior conserva el valor previo"
