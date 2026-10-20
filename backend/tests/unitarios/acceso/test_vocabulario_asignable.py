"""D7/RA-4: la API, el CHECK real de 0017 y el dominio sostienen el mismo vocabulario."""

import re
from importlib import import_module
from typing import get_args
from unittest.mock import MagicMock

import pytest

from proptech_api.complejos import CuerpoAsignacion
from proptech_core.acceso.dominio.permisos import Rol


def test_literal_check_y_enum_coinciden(monkeypatch: pytest.MonkeyPatch) -> None:
    migracion = import_module("migraciones.versions.0017_roles_de_la_empresa")
    operaciones = MagicMock()
    monkeypatch.setattr(migracion, "op", operaciones)
    migracion.upgrade()
    checks = [
        llamada.args[2]
        for llamada in operaciones.create_check_constraint.call_args_list
        if llamada.args[:2] == ("ck_asignacion_rol_rol_valido", "asignacion_rol")
    ]
    assert len(checks) == 1
    roles_base = set(re.findall(r"'([^']+)'", checks[0]))
    roles_dominio = {rol.value for rol in Rol}
    assert roles_base == roles_dominio

    # Esta ruta siempre tiene edificio y nunca unidad (D7).
    excluidos = {Rol.SUPER_ADMIN.value, Rol.VECINO.value}
    asignables_dominio = roles_dominio - excluidos
    asignables_base = roles_base - excluidos
    asignables_api = set(get_args(CuerpoAsignacion.model_fields["rol"].annotation))
    assert asignables_api == asignables_base == asignables_dominio
