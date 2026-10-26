"""El candado nunca da DELETE a la app, en ningún punto del deploy (E2, DB-11, F1-01, F1-06)."""

import pytest

from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


def _app_puede(base: BaseDeEdificio, permiso: str) -> bool:
    with arranque(base) as c:
        fila = c.execute(
            "SELECT has_table_privilege('proptech_app', 'public.candado_de_cuenta', %s)",
            (permiso,),
        ).fetchone()
    assert fila is not None
    return bool(fila[0])


def test_candado_sin_delete_en_cada_paso_del_deploy(
    base_para_migraciones: BaseDeEdificio,
) -> None:
    base = base_para_migraciones
    # Base nueva: `roles antes` ya corrió en el fixture; ahora la migración crea el candado.
    base.migrar("upgrade", "head")
    pasos = []
    pasos.append(("tras upgrade, antes de despues", _app_puede(base, "DELETE")))
    base.roles("despues")
    pasos.append(("tras despues", _app_puede(base, "DELETE")))
    base.roles("antes")
    pasos.append(("tras un segundo antes", _app_puede(base, "DELETE")))
    base.roles("despues")
    pasos.append(("tras un segundo despues", _app_puede(base, "DELETE")))
    assert [paso for paso, puede in pasos if puede] == []
    # Lo que la app sí necesita para bloquear (E2) sigue en pie.
    assert _app_puede(base, "SELECT") and _app_puede(base, "INSERT")
    assert _app_puede(base, "UPDATE")
