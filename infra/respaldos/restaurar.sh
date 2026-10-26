#!/usr/bin/env bash
# Restaura un backup de PostgreSQL en una base aparte, nunca sobre la base en
# uso (D9). Corre `docker compose -p proptech` (L-006; ver PROPTECH_COMPOSE_PROYECTO) y encuentra
# `infra/` por su propia ubicación, sea cual sea la carpeta desde la que se
# lo llame (M21). Uso: restaurar.sh <archivo> [base_destino]
set -euo pipefail
export LC_ALL=C

error_salir() {
  echo "error: $1" >&2
  exit 1
}

ARCHIVO_ARG="${1:-}"
# `${2:-default}` trataría un destino pasado como texto vacío igual que uno
# NO pasado, y lo reemplazaría en silencio por el default: con `$#` se
# distingue "no vino el argumento" de "vino, y es la cadena vacía".
if [ "$#" -ge 2 ]; then
  DESTINO="$2"
else
  DESTINO="proptech_restauracion"
fi

# (1) El archivo existe y es legible. No invoca docker todavía.
if [ ! -f "$ARCHIVO_ARG" ] || [ ! -r "$ARCHIVO_ARG" ]; then
  error_salir "el archivo de backup no existe o no se puede leer: $ARCHIVO_ARG"
fi

# Ruta absoluta ANTES de cambiar de carpeta (M21): el argumento puede ser
# relativo a la carpeta desde la que se llamó al script, no a infra/.
ARCHIVO_ABSOLUTO="$(cd "$(dirname -- "$ARCHIVO_ARG")" && pwd)/$(basename -- "$ARCHIVO_ARG")"

# (2) El destino cumple la expresión cerrada, sobre el texto entero, con
# caracteres ASCII (L-008). Todavía no invoca docker.
if [[ ! "$DESTINO" =~ ^proptech_[a-z0-9_]{1,50}$ ]]; then
  error_salir "DESTINO: '$DESTINO' no cumple el patrón de un nombre de base válido"
fi

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$INFRA_DIR"

# PROPTECH_COMPOSE_PROYECTO: sólo para el ensayo aislado (ensayo-roles.sh), que
# la exporta; sin ella, siempre `proptech` (L-006).
compose() {
  docker compose -p "${PROPTECH_COMPOSE_PROYECTO:-proptech}" "$@"
}

# (3) Recién acá se invoca docker: primero la base en uso (un solo
# printenv), y se rechaza un destino que coincida con ella aunque cumpla la
# expresión (por ejemplo, POSTGRES_DB=proptech_principal).
base_en_uso="$(compose exec -T db printenv POSTGRES_DB)"
if [ "$DESTINO" = "$base_en_uso" ]; then
  error_salir "DESTINO: '$DESTINO' es la base en uso, no se puede restaurar sobre ella"
fi

usuario="$(compose exec -T db printenv POSTGRES_USER)"

# (4) dropdb, createdb y pg_restore, los tres con -U, el nombre como
# argumento propio (nunca dentro de un `sh -c`). La salida de las
# herramientas no llega a ningún mensaje propio (L-007).
if ! compose exec -T db dropdb --if-exists -U "$usuario" "$DESTINO" >/dev/null 2>/dev/null; then
  error_salir "dropdb: falló al borrar la base destino"
fi

if ! compose exec -T db createdb -U "$usuario" "$DESTINO" >/dev/null 2>/dev/null; then
  error_salir "createdb: falló al crear la base destino"
fi

if ! compose exec -T db pg_restore --no-owner -U "$usuario" -d "$DESTINO" \
      < "$ARCHIVO_ABSOLUTO" >/dev/null 2>/dev/null; then
  error_salir "pg_restore: falló al restaurar el backup"
fi
