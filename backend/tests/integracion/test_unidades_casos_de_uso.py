"""Padrón con texto estricto y errores sin filtrar existencia (5.2)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.parametros import leer_parametros
from proptech_core.complejos.aplicacion import escritura

from .test_crear_edificio import (
    DEPARTAMENTO_ID,
    GEOREF,
    LOCALIDAD_ID,
    PARAMETROS,
    PROVINCIA_ID,
    reloj,
)

pytestmark = pytest.mark.integracion
DATOS = {
    "identificador": "1A",
    "tipo": "departamento",
    "piso": "1",
    "coeficiente": "0.100000",
    "superficie_m2": "60.00",
}


def crear(sesion: Session, identidad: Identidad) -> UUID:
    return escritura.crear_edificio(
        sesion,
        identidad,
        nombre="Ficticio",
        provincia_id=PROVINCIA_ID,
        departamento_id=DEPARTAMENTO_ID,
        localidad_id=LOCALIDAD_ID,
        georef=GEOREF,
        parametros=leer_parametros(str(PARAMETROS)),
        reloj=reloj,
        request_id=uuid4(),
    )


def test_alta_edicion_e_informe(sesion_edificio: Session, identidad_edificio: Identidad) -> None:
    from proptech_core.complejos.aplicacion import unidades

    edificio = crear(sesion_edificio, identidad_edificio)
    unidad = unidades.crear_unidad(
        sesion_edificio, identidad_edificio, complejo_id=edificio, datos=DATOS, request_id=uuid4()
    )
    padron = unidades.listar_unidades(sesion_edificio, edificio)
    assert padron["unidades"] == [{"id": unidad, "complejo_id": edificio, **DATOS}]
    assert padron["informe"] == {
        "suma": "0.100000",
        "diferencia": "-0.900000",
        "estado": "fuera_de_tolerancia",
    }
    unidades.editar_unidad(
        sesion_edificio,
        unidad_id=unidad,
        cambios={"coeficiente": "1", "superficie_m2": "62.5"},
        request_id=uuid4(),
        identidad=identidad_edificio,
    )
    padron = unidades.listar_unidades(sesion_edificio, edificio)
    assert padron["informe"]["estado"] == "ok"
    assert padron["unidades"][0]["superficie_m2"] == "62.50"
    assert (
        sesion_edificio.execute(
            text("SELECT estado FROM unidad WHERE id=:id"), {"id": unidad}
        ).scalar_one()
        is None
    )


def test_repetida_es_conflicto_solo_en_su_edificio(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion import unidades
    from proptech_core.complejos.aplicacion.errores import Conflicto

    a, b = crear(sesion_edificio, identidad_edificio), crear(sesion_edificio, identidad_edificio)
    unidades.crear_unidad(
        sesion_edificio, identidad_edificio, complejo_id=a, datos=DATOS, request_id=uuid4()
    )
    with pytest.raises(Conflicto) as error:
        unidades.crear_unidad(
            sesion_edificio, identidad_edificio, complejo_id=a, datos=DATOS, request_id=uuid4()
        )
    assert error.value.campo == "identificador"
    unidades.crear_unidad(
        sesion_edificio, identidad_edificio, complejo_id=b, datos=DATOS, request_id=uuid4()
    )
    assert len(unidades.listar_unidades(sesion_edificio, a)["unidades"]) == 1
    assert len(unidades.listar_unidades(sesion_edificio, b)["unidades"]) == 1


@pytest.mark.parametrize(
    "cambios",
    [
        {"complejo_id": uuid4()},
        {"administracion_id": uuid4()},
        {"coeficiente": 0.1},
        {"superficie_m2": 60.5},
        {"superficie_m2": "0"},
        {"tipo": "quincho"},
    ],
)
def test_edicion_rechazada_no_cambia_la_unidad(
    sesion_edificio: Session, identidad_edificio: Identidad, cambios: dict[str, object]
) -> None:
    from proptech_core.complejos.aplicacion import unidades
    from proptech_core.complejos.aplicacion.errores import EntradaInvalida

    edificio = crear(sesion_edificio, identidad_edificio)
    unidad = unidades.crear_unidad(
        sesion_edificio, identidad_edificio, complejo_id=edificio, datos=DATOS, request_id=uuid4()
    )
    if "complejo_id" in cambios:
        cambios = {"complejo_id": crear(sesion_edificio, identidad_edificio)}
    antes = unidades.listar_unidades(sesion_edificio, edificio)
    with pytest.raises(EntradaInvalida):
        unidades.editar_unidad(
            sesion_edificio,
            unidad_id=unidad,
            cambios=cambios,
            request_id=uuid4(),
            identidad=identidad_edificio,
        )
    assert unidades.listar_unidades(sesion_edificio, edificio) == antes


def test_unidad_de_otra_administracion_es_igual_a_inexistente(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion import unidades
    from proptech_core.complejos.aplicacion.errores import NoEncontrado

    edificio = crear(sesion_edificio, identidad_edificio)
    unidad = unidades.crear_unidad(
        sesion_edificio, identidad_edificio, complejo_id=edificio, datos=DATOS, request_id=uuid4()
    )
    sesion_edificio.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(uuid4())}
    )
    errores = []
    for id_unidad in (unidad, uuid4()):
        with pytest.raises(NoEncontrado) as error:
            unidades.editar_unidad(
                sesion_edificio,
                unidad_id=id_unidad,
                cambios={"identificador": "2B"},
                request_id=uuid4(),
                identidad=identidad_edificio,
            )
        errores.append(str(error.value))
    assert errores == ["no encontrado", "no encontrado"]
