"""Quién descarga qué de la expensa (7, H-015, D-106, P39): la regla pura, sin base."""

from uuid import uuid4

import pytest

from proptech_core.acceso.dominio.permisos import Asignacion, Rol
from proptech_core.liquidacion.aplicacion.documentos import puede_pedir_el_enlace
from proptech_core.liquidacion.aplicacion.errores import NoEncontrado, SinPermiso

EDIFICIO, UNIDAD, OTRA = uuid4(), uuid4(), uuid4()


def _pide(asignaciones: list[Asignacion], variante: str = "completa", visible: bool = True) -> None:
    puede_pedir_el_enlace(
        asignaciones,
        complejo_id=EDIFICIO,
        unidad_id=UNIDAD,
        variante_del_documento=variante,
        visible_para_el_consejo=visible,
    )


def _vecino(vinculo: str, unidad: object = UNIDAD, complejo: object = EDIFICIO) -> Asignacion:
    return Asignacion(Rol.VECINO, complejo, unidad, vinculo)  # type: ignore[arg-type]


@pytest.mark.parametrize("variante", ["completa", "sin_extraordinaria"])
def test_el_personal_con_ver_liquidaciones_pide_las_dos(variante: str) -> None:
    for rol, complejo in (
        (Rol.SUPER_ADMIN, None),
        (Rol.ADMINISTRADOR, None),
        (Rol.ADMINISTRADOR, EDIFICIO),
        (Rol.CONTADOR, EDIFICIO),
    ):
        _pide([Asignacion(rol, complejo)], variante)


def test_el_auxiliar_no_pide_ninguna() -> None:
    with pytest.raises(SinPermiso):
        _pide([Asignacion(Rol.AUXILIAR, EDIFICIO)])


def test_el_consejo_pide_sólo_de_lo_distribuido() -> None:
    consejo = [Asignacion(Rol.CONSEJO, EDIFICIO)]
    _pide(consejo, visible=True)
    with pytest.raises(NoEncontrado):
        _pide(consejo, visible=False)


def test_el_propietario_pide_las_dos_y_el_inquilino_sólo_la_sin_extraordinaria() -> None:
    _pide([_vecino("propietario")], "completa")
    _pide([_vecino("propietario")], "sin_extraordinaria")
    _pide([_vecino("inquilino")], "sin_extraordinaria")
    with pytest.raises(SinPermiso):
        _pide([_vecino("inquilino")], "completa")


def test_quien_es_propietario_de_la_unidad_aunque_sea_inquilino_de_otra_pide_la_completa() -> None:
    _pide([_vecino("inquilino", OTRA), _vecino("propietario")], "completa")
    with pytest.raises(SinPermiso):
        _pide([_vecino("propietario", OTRA), _vecino("inquilino")], "completa")


def test_un_vecino_de_otra_unidad_o_de_otro_edificio_no_ve_que_exista() -> None:
    with pytest.raises(NoEncontrado):
        _pide([_vecino("propietario", OTRA)])
    with pytest.raises(NoEncontrado):
        _pide([_vecino("propietario", UNIDAD, uuid4())])


def test_sin_ninguna_asignacion_no_ve_que_exista() -> None:
    with pytest.raises(NoEncontrado):
        _pide([])
