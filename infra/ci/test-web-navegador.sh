#!/usr/bin/env bash
# Navegador real contra una API falsa (D7, tarea 3.8): `next build`, la API
# falsa de 3.4/3.8 y `next start`, y recién ahí Playwright (sólo Chromium).
# Corre limpio desde un clon: sólo necesita `corepack pnpm install` y
# `pnpm exec playwright install chromium` antes (no está acá porque CI y un
# clon local lo cachean distinto; el paso del job `web` en ci.yml lo hace).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../../web"

PUERTO_API_FALSA="${PROPTECH_PUERTO_API_FALSA:-4100}"
PUERTO_WEB="${PROPTECH_PUERTO_WEB:-3100}"
export PROPTECH_PUERTO_API_FALSA="$PUERTO_API_FALSA"
export PROPTECH_URL_API_INTERNA="http://127.0.0.1:${PUERTO_API_FALSA}"
export PROPTECH_URL_WEB="http://127.0.0.1:${PUERTO_WEB}"

PID_API_FALSA=""
PID_WEB=""

limpiar() {
  [ -n "$PID_WEB" ] && kill "$PID_WEB" 2>/dev/null || true
  [ -n "$PID_API_FALSA" ] && kill "$PID_API_FALSA" 2>/dev/null || true
}
trap limpiar EXIT

esperar_puerto() {
  local puerto="$1"
  local intentos=0
  until corepack pnpm@12.10.1 exec node -e "
    fetch('http://127.0.0.1:${puerto}/').catch(() => process.exit(1))
  " >/dev/null 2>&1; do
    intentos=$((intentos + 1))
    if [ "$intentos" -ge 50 ]; then
      echo "nadie contesta en :${puerto} después de 25s" >&2
      exit 1
    fi
    sleep 0.5
  done
}

corepack pnpm@12.10.1 build

corepack pnpm@12.10.1 exec tsx e2e/api-falsa.ts &
PID_API_FALSA=$!
esperar_puerto "$PUERTO_API_FALSA"

PORT="$PUERTO_WEB" corepack pnpm@12.10.1 start &
PID_WEB=$!
esperar_puerto "$PUERTO_WEB"

corepack pnpm@12.10.1 exec playwright test
