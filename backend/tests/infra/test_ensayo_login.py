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


def test_ensayo_usa_un_proyecto_compose_parametrizable() -> None:
    # El ensayo hace `down -v`: se tiene que poder correr en un proyecto aislado,
    # con `proptech` como default para no cambiar a quien lo usa hoy.
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    assert 'PROYECTO_COMPOSE="${PROPTECH_COMPOSE_PROYECTO:-proptech}"' in script
    assert 'compose() { docker compose -p "$PROYECTO_COMPOSE" "$@"; }' in script
    assert "-p proptech " not in script


def test_ensayo_devuelve_la_tabla_protegida_antes_de_migrar() -> None:
    # RB-1 (4a): tras `despues` o tras restaurar con --no-owner, configuracion_versionada
    # no es del migrador y cruzar 0021 falla con `must be owner`. Es el paso 1 del
    # rollback del Migration Plan; no prueba el ensayo entero, que sólo se prueba corriéndolo.
    script = (RAIZ / "infra/ci/ensayo-roles.sh").read_text()
    assert "ALTER TABLE configuracion_versionada OWNER TO" in script
    assert "ALTER FUNCTION fn_configuracion_versionada_bloqueada() OWNER TO" in script
    origen = script.index('devolver_al_migrador "$BASE_ORIGEN"')
    assert origen < script.index("migraciones alembic downgrade 0016")
    restaurada = script.index("devolver_al_migrador proptech_restauracion")
    assert script.index("roles antes") < restaurada
    assert restaurada < script.index("migrar_restaurada upgrade head")
