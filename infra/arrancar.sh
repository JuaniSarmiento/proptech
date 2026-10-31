#!/usr/bin/env bash
# Arranque documentado del stack (D7, F-mkdir del 1d): crea la carpeta de
# respaldos del host con el dueño correcto SI FALTA, y recién ahí delega en
# `docker compose up` (con cualquier argumento que se le pase). Reemplaza el
# paso manual `mkdir -p infra/datos-respaldos` del README: Docker, al
# levantar un bind mount cuya carpeta no existe, la crea él mismo como
# root — es justo lo que este script evita, sin tocar nada si la carpeta ya
# existe (D7, "Carpeta ya creada por quien levanta el stack": ni el dueño ni
# el contenido cambian). El servicio `respaldos` conserva su propio error
# JSON para quien corra `docker compose up` pelado, sin pasar por acá.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Lee una clave de `.env` SIN pisar una variable que ya llegó por el
# entorno (quien invoca este script, como el CI o esta misma suite de
# tests, tiene que poder ganarle al valor del archivo — un `source .env`
# liso haría exactamente lo contrario: `.env` siempre gana). `docker
# compose` lee `.env` por su cuenta más abajo; esto es sólo para que ESTE
# script sepa dónde crear la carpeta antes de delegar.
leer_de_env() {
  [ -f .env ] || return 0
  grep -E "^${1}=" .env 2>/dev/null | tail -n1 | cut -d= -f2-
}

CARPETA="${PROPTECH_DIR_RESPALDOS:-$(leer_de_env PROPTECH_DIR_RESPALDOS)}"
CARPETA="${CARPETA:-./datos-respaldos}"
UID_HOST="${PROPTECH_UID:-$(leer_de_env PROPTECH_UID)}"
UID_HOST="${UID_HOST:-$(id -u)}"
GID_HOST="${PROPTECH_GID:-$(leer_de_env PROPTECH_GID)}"
GID_HOST="${GID_HOST:-$(id -g)}"

if [ ! -e "$CARPETA" ]; then
  mkdir -p -- "$CARPETA"
  # Si quien corre este script no es el dueño real (p. ej. un UID distinto
  # pasado a mano), `chown` puede fallar sin privilegios — no es fatal: la
  # carpeta ya quedó creada por ESTE usuario, nunca por root, que es la
  # falla que D7 evita. El propio servicio `respaldos` sigue rechazando con
  # su error JSON si de verdad no puede escribir ahí.
  chown "${UID_HOST}:${GID_HOST}" -- "$CARPETA" 2>/dev/null || true
fi

export PROPTECH_UID="$UID_HOST"
export PROPTECH_GID="$GID_HOST"

exec docker compose "$@"
