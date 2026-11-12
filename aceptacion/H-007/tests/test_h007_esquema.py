"""H-007 · C18 (parte de esquema y vocabulario): `importacion` con RLS forzada y la acción
nueva en el
vocabulario de auditoría y en la matriz de permisos (E6)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from ._h007 import Mundo, aceptada, importar, padron

pytestmark = pytest.mark.integracion

ACCION = "importar_padron_y_saldos"


def _tabla_existe(m: Mundo) -> None:
    assert m.uno("SELECT to_regclass('importacion') IS NOT NULL"), (
        "falta la tabla importacion (0036)"
    )


def test_c18_importacion_con_rls_forzada(mundo: Mundo) -> None:
    _tabla_existe(mundo)
    fila = mundo.filas(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'importacion'"
    )
    assert fila == [(True, True)], f"importacion necesita RLS activada y forzada: {fila}"


def test_c18_otra_administracion_no_ve_la_importacion(mundo: Mundo) -> None:
    cuerpo = aceptada(importar(mundo, mundo.torre, padron()))
    assert (
        mundo.uno("SELECT count(*) FROM importacion WHERE id = %s", (cuerpo["importacion_id"],))
        == 1
    )
    assert (
        mundo.uno(
            "SELECT count(*) FROM importacion WHERE id = %s",
            (cuerpo["importacion_id"],),
            admin=mundo.admin_b,
        )
        == 0
    ), "la administración B ve la importación de A"


def test_c18_la_accion_esta_en_el_vocabulario_y_en_la_matriz(mundo: Mundo) -> None:
    nombres = {f[0] for f in mundo.filas("SELECT nombre FROM accion_de_auditoria")}
    assert ACCION in nombres, "falta importar_padron_y_saldos en accion_de_auditoria"
    from proptech_core.acceso.dominio import permisos

    assert ACCION in {a.value for a in permisos.Accion}, "falta la acción en `Accion`"
    accion = permisos.Accion(ACCION)
    edificio, otro = uuid4(), uuid4()

    def puede(rol: str, complejo: object, unidad: object = None, vinculo: object = None) -> bool:
        asignacion = permisos.Asignacion(rol, complejo, unidad, vinculo)  # type: ignore[arg-type]
        return permisos.puede([asignacion], accion, edificio)

    assert puede("super_admin", None)
    assert puede("administrador", None)
    assert puede("administrador", edificio)
    assert not puede("administrador", otro)
    assert not puede("contador", None)
    assert not puede("contador", edificio)
    assert not puede("auxiliar", edificio)
    assert not puede("consejo", edificio)
    assert not puede("vecino", edificio, uuid4(), "propietario")
    assert not puede("vecino", edificio, uuid4(), "inquilino")
