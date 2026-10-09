#!/usr/bin/env bash
# El canario: escribe un test roto a propósito, corre el script de test
# correspondiente y exige que termine distinto de 0 (D7). Si el script de
# test devolviera 0 con el test roto, este script también sale con error.
set -euo pipefail

LADO="${1:-}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$LADO" != "backend" ] && [ "$LADO" != "web" ]; then
  echo "uso: $0 <backend|web>" >&2
  exit 2
fi

if [ "$LADO" = "backend" ]; then
  ARCHIVO_ROTO="$RAIZ/../backend/tests/unitarios/test_canario_roto.py"
  SCRIPT_DE_TEST="$RAIZ/ci/test-backend.sh"
else
  ARCHIVO_ROTO="$RAIZ/../web/src/canario-roto.test.ts"
  SCRIPT_DE_TEST="$RAIZ/ci/test-web.sh"
fi

limpiar() {
  rm -f "$ARCHIVO_ROTO"
}
trap limpiar EXIT

if [ "$LADO" = "backend" ]; then
  cat > "$ARCHIVO_ROTO" <<'EOF'
def test_canario_roto_a_proposito() -> None:
    assert False, "canario: este test está roto a propósito"
EOF
else
  cat > "$ARCHIVO_ROTO" <<'EOF'
import { expect, it } from "vitest";

it("canario roto a propósito", () => {
  expect(1).toBe(2);
});
EOF
fi

echo "--- canario ($LADO): corriendo $SCRIPT_DE_TEST con un test roto a propósito ---"
if bash "$SCRIPT_DE_TEST"; then
  echo "ERROR: el canario esperaba que el script de test fallara y terminó en 0" >&2
  exit 1
fi

echo "CANARIO OK ($LADO): el script de test terminó distinto de 0 con el test roto"
