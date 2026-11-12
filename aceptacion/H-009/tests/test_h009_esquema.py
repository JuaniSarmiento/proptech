"""H-009 · C13 (vocabulario): la acción `confirmar_saldos_iniciales` en el vocabulario de
auditoría y en la matriz de permisos (E6: sólo super admin y administrador principal)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from ._h009 import ACCION, Mundo

pytestmark = pytest.mark.integracion


def test_c13_la_accion_esta_en_el_vocabulario_y_en_la_matriz(mundo: Mundo) -> None:
    nombres = {f[0] for f in mundo.filas("SELECT nombre FROM accion_de_auditoria")}
    assert ACCION in nombres, "falta confirmar_saldos_iniciales en accion_de_auditoria (0038)"
    from proptech_core.acceso.dominio import permisos

    assert ACCION in {a.value for a in permisos.Accion}, "falta la acción en `Accion`"
    accion = permisos.Accion(ACCION)
    edificio = uuid4()

    def puede(rol: str, complejo: object, unidad: object = None, vinculo: object = None) -> bool:
        asignacion = permisos.Asignacion(rol, complejo, unidad, vinculo)  # type: ignore[arg-type]
        return permisos.puede([asignacion], accion, edificio)

    assert puede("super_admin", None)
    assert puede("administrador", None)
    assert not puede("administrador", edificio), "el administrador por edificio no confirma (E6)"
    assert not puede("contador", None)
    assert not puede("auxiliar", edificio)
    assert not puede("consejo", edificio)
    assert not puede("vecino", edificio, uuid4(), "propietario")
    assert not puede("vecino", edificio, uuid4(), "inquilino")
