#!/usr/bin/env bash
# Único lugar donde vive el comando de test de la web (D7).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../../web"

corepack pnpm@12.10.1 vitest run
