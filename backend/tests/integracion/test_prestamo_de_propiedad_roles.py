"""D-115.3, construido por la `0042` (7, H-014): `roles antes` le presta al migrador la propiedad
de `evento_de_emision` sólo mientras la `0042` está pendiente, y `roles despues` se la devuelve al
rol de arranque. Sin la regla, el `ALTER` de la `0042` falla con `must be owner`."""

import pytest

from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


def _dueno(base: BaseDeEdificio, tabla: str) -> str:
    with arranque(base) as c:
        fila = c.execute(
            "SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = to_regclass(%s)",
            (f"public.{tabla}",),
        ).fetchone()
    assert fila is not None
    return str(fila[0])


def test_antes_presta_la_tabla_mientras_la_migracion_esta_pendiente(
    base_para_migraciones: BaseDeEdificio,
) -> None:
    base = base_para_migraciones
    migrador = base.entorno["POSTGRES_MIGRADOR_USER"]
    base.roles("antes")
    base.migrar("upgrade", "0041")
    base.roles("despues")
    assert _dueno(base, "evento_de_emision") == base.contenedor.username

    base.roles("antes")
    assert _dueno(base, "evento_de_emision") == migrador, "con la 0042 pendiente, se presta"
    assert _dueno(base, "movimiento") == base.contenedor.username, (
        "sólo lo que la migración declara"
    )
    base.migrar("upgrade", "head")
    base.roles("despues")
    assert _dueno(base, "evento_de_emision") == base.contenedor.username, "despues la devuelve"

    base.roles("antes")
    assert _dueno(base, "evento_de_emision") == base.contenedor.username, (
        "en la cabeza no se presta"
    )
    base.roles("despues")
