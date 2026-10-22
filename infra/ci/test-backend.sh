#!/usr/bin/env bash
# Único lugar donde vive el comando de test del backend: lo usan el CI, el
# canario y Juani en su máquina (D7). Sin argumentos corre la suite
# completa (comportamiento sin cambios). Con argumentos, se los pasa a
# pytest tal cual: el canario los usa para apuntar sólo al archivo del
# test roto y no repetir toda la suite (OPS-2), pero el camino que
# ejercita (este mismo script, el mismo `set -euo pipefail`, el mismo
# `uv run pytest`) es idéntico al que corre el paso normal del CI.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../../backend"

uv run pytest "$@"
