from pathlib import Path


def test_script_elige_perfil_ci() -> None:
    script = Path(__file__).resolve().parents[3] / "infra/ci/test-backend.sh"
    assert 'export HYPOTHESIS_PROFILE="${HYPOTHESIS_PROFILE:-ci}"' in script.read_text()
