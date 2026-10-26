"""Categorías propias del edificio y orden completo atómico (5.4)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad

from .test_unidades_casos_de_uso import crear

pytestmark = pytest.mark.integracion


def test_crear_renombrar_desactivar_y_reactivar_sin_tocar_otro_edificio(
    sesion_edificio: Session,
    identidad_edificio: Identidad,
) -> None:
    from proptech_core.complejos.aplicacion import categorias

    a, b = crear(sesion_edificio, identidad_edificio), crear(sesion_edificio, identidad_edificio)
    antes_b = categorias.listar_categorias(sesion_edificio, b)
    nueva = categorias.crear_categoria(
        sesion_edificio,
        identidad_edificio,
        complejo_id=a,
        datos={"clave": "seguridad_nocturna", "nombre": "Seguridad nocturna"},
    )
    lista_a = categorias.listar_categorias(sesion_edificio, a)
    assert lista_a[-1]["id"] == nueva
    assert lista_a[-1]["nombre"] == "Seguridad nocturna"
    assert lista_a[-1]["activa"] is True
    limpieza = next(c for c in lista_a if c["nombre"] == "Limpieza")
    categorias.editar_categoria(
        sesion_edificio,
        identidad_edificio,
        categoria_id=limpieza["id"],
        cambios={"nombre": "Limpieza y residuos"},
        request_id=uuid4(),
    )
    assert (
        next(
            c for c in categorias.listar_categorias(sesion_edificio, a) if c["id"] == limpieza["id"]
        )["nombre"]
        == "Limpieza y residuos"
    )
    categorias.editar_categoria(
        sesion_edificio,
        identidad_edificio,
        categoria_id=nueva,
        cambios={"activa": False},
        request_id=uuid4(),
    )
    inactiva = next(c for c in categorias.listar_categorias(sesion_edificio, a) if c["id"] == nueva)
    assert inactiva["activa"] is False
    assert inactiva["nombre"] == "Seguridad nocturna"
    assert nueva not in [
        c["id"] for c in categorias.listar_categorias(sesion_edificio, a, solo_activas=True)
    ]
    categorias.editar_categoria(
        sesion_edificio,
        identidad_edificio,
        categoria_id=nueva,
        cambios={"activa": True},
        request_id=uuid4(),
    )
    assert nueva in [
        c["id"] for c in categorias.listar_categorias(sesion_edificio, a, solo_activas=True)
    ]
    assert categorias.listar_categorias(sesion_edificio, b) == antes_b


def test_clave_y_nombre_repetidos_no_cambian_nada(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion import categorias
    from proptech_core.complejos.aplicacion.errores import Conflicto

    edificio = crear(sesion_edificio, identidad_edificio)
    antes = categorias.listar_categorias(sesion_edificio, edificio)
    for datos, campo in (
        ({"clave": "otra", "nombre": "limpieza"}, "nombre"),
        ({"clave": antes[0]["clave"], "nombre": "Distinto"}, "clave"),
    ):
        with pytest.raises(Conflicto) as error:
            categorias.crear_categoria(
                sesion_edificio, identidad_edificio, complejo_id=edificio, datos=datos
            )
        assert error.value.campo == campo
    with pytest.raises(Conflicto) as error:
        categorias.editar_categoria(
            sesion_edificio,
            identidad_edificio,
            categoria_id=antes[-1]["id"],
            cambios={"nombre": "LIMPIEZA"},
            request_id=uuid4(),
        )
    assert error.value.campo == "nombre"
    assert categorias.listar_categorias(sesion_edificio, edificio) == antes


def test_reordenar_incluye_tambien_inactivas(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion import categorias

    edificio = crear(sesion_edificio, identidad_edificio)
    antes = categorias.listar_categorias(sesion_edificio, edificio)
    categorias.editar_categoria(
        sesion_edificio,
        identidad_edificio,
        categoria_id=antes[0]["id"],
        cambios={"activa": False},
        request_id=uuid4(),
    )
    orden = [c["id"] for c in reversed(antes)]
    categorias.reordenar_categorias(
        sesion_edificio, identidad_edificio, complejo_id=edificio, orden=orden, request_id=uuid4()
    )
    despues = categorias.listar_categorias(sesion_edificio, edificio)
    assert [c["id"] for c in despues] == orden
    assert [c["orden"] for c in despues] == list(range(len(orden)))


@pytest.mark.parametrize("error_orden", ["omitida", "repetida", "ajena", "otra_administracion"])
def test_orden_invalido_no_modifica_nada(
    sesion_edificio: Session, identidad_edificio: Identidad, error_orden: str
) -> None:
    from uuid import uuid4

    from sqlalchemy import text

    from proptech_core.complejos.aplicacion import categorias
    from proptech_core.complejos.aplicacion.errores import EntradaInvalida

    a, b = crear(sesion_edificio, identidad_edificio), crear(sesion_edificio, identidad_edificio)
    antes = categorias.listar_categorias(sesion_edificio, a)
    ajena = categorias.listar_categorias(sesion_edificio, b)[0]["id"]
    if error_orden == "otra_administracion":
        admin, persona = uuid4(), uuid4()
        sesion_edificio.execute(
            text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(admin)}
        )
        sesion_edificio.execute(
            text("INSERT INTO administracion (id,nombre) VALUES (:id,'Inventada')"), {"id": admin}
        )
        sesion_edificio.execute(
            text(
                "INSERT INTO persona (id,administracion_id,nombre) "
                "VALUES (:id,:admin,'Persona ficticia')"
            ),
            {"id": persona, "admin": admin},
        )
        c = crear(sesion_edificio, Identidad(admin, persona))
        ajena = categorias.listar_categorias(sesion_edificio, c)[0]["id"]
        sesion_edificio.execute(
            text("SELECT set_config('app.administracion_id', :id, true)"),
            {"id": str(identidad_edificio.administracion_id)},
        )
    orden: list[UUID] = [c["id"] for c in reversed(antes)]
    if error_orden == "omitida":
        orden.pop()
    elif error_orden == "repetida":
        orden[-1] = orden[0]
    else:
        orden[-1] = ajena
    with pytest.raises(EntradaInvalida) as error:
        categorias.reordenar_categorias(
            sesion_edificio, identidad_edificio, complejo_id=a, orden=orden, request_id=uuid4()
        )
    assert error.value.campo == "orden"
    assert categorias.listar_categorias(sesion_edificio, a) == antes
