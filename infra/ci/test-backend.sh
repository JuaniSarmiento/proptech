#!/usr/bin/env bash
# Único lugar donde vive el comando de test del backend: lo usan el CI, el
# canario y Juani en su máquina (D7).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../../backend"

uv run pytest
