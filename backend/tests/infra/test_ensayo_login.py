"""El ensayo debe verificar la cabeza real tras los dos upgrades restaurados."""

import re
from pathlib import Path

from alembic.script import ScriptDirectory

RAIZ = Path(__file__).resolve().parents[3]


def test_ensayo_verifica_la_cabeza_real_dos_veces() -> None:
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    cabeza = ScriptDirectory(str(RAIZ / "backend/migraciones")).get_current_head()
    revisiones = re.findall(
        r"migrar_restaurada upgrade head[^\n]*\nverificar_revision ([0-9]+)", script
    )
    assert revisiones == [cabeza, cabeza]
