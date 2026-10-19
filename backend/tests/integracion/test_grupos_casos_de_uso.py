"""Grupos parciales, modo propio y Generales dinámico (5.3)."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.complejos.aplicacion import unidades

from .test_unidades_casos_de_uso import DATOS, crear

pytestmark = pytest.mark.integracion


def alta_unidad(
    sesion: Session, identidad: Identidad, edificio: UUID, identificador: str = "1A"
) -> UUID:
    return unidades.crear_unidad(
        sesion, identidad, complejo_id=edificio, datos={**DATOS, "identificador": identificador}
    )


def test_nueva_unidad_entra_en_generales(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion import grupos

    edificio = crear(sesion_edificio, identidad_edificio)
    assert grupos.listar_grupos(sesion_edificio, edificio)[0]["unidades"] == []
    unidad = alta_unidad(sesion_edificio, identidad_edificio, edificio)
    generales = grupos.listar_grupos(sesion_edificio, edificio)[0]
    assert generales["unidades"] == [{"unidad_id": unidad, "coeficiente": "0.100000"}]
    assert generales["informe"]["suma"] == "0.100000"


def test_renormalizado_y_propios_con_informe_y_cambio_de_modo(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion import grupos

    edificio = crear(sesion_edificio, identidad_edificio)
    una = alta_unidad(sesion_edificio, identidad_edificio, edificio)
    otra = alta_unidad(sesion_edificio, identidad_edificio, edificio, "1B")
    grupo = grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos={"clave": "ascensor", "nombre": "Ascensor", "metodo": "coeficiente"},
        miembros=[{"unidad_id": una}, {"unidad_id": otra}],
    )
    leido = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo)
    assert leido["modo_de_coeficientes"] == "renormalizado"
    assert leido["informe"] is None
    assert all(u["coeficiente"] is None for u in leido["unidades"])
    grupos.fijar_unidades(
        sesion_edificio,
        grupo_id=grupo,
        modo="propios",
        miembros=[
            {"unidad_id": una, "coeficiente": "0.4"},
            {"unidad_id": otra, "coeficiente": "0.4"},
        ],
    )
    leido = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo)
    assert leido["informe"] == {
        "suma": "0.800000",
        "diferencia": "-0.200000",
        "estado": "fuera_de_tolerancia",
    }
    assert leido["modo_de_coeficientes"] == "propios"
    assert [u["coeficiente"] for u in leido["unidades"]] == ["0.400000", "0.400000"]
    grupos.editar_grupo(sesion_edificio, grupo_id=grupo, cambios={"nombre": "Cocheras"})
    grupos.fijar_unidades(
        sesion_edificio,
        grupo_id=grupo,
        modo="propios",
        miembros=[
            {"unidad_id": una, "coeficiente": "0.5"},
            {"unidad_id": otra, "coeficiente": "0.5"},
        ],
    )
    leido = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo)
    assert leido["nombre"] == "Cocheras"
    assert leido["informe"]["estado"] == "ok"
    grupos.fijar_unidades(
        sesion_edificio, grupo_id=grupo, modo="renormalizado", miembros=[{"unidad_id": una}]
    )
    leido = next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo)
    assert leido["modo_de_coeficientes"] == "renormalizado"
    assert leido["unidades"] == [{"unidad_id": una, "coeficiente": None}]


def test_unidades_ajenas_mismo_error_y_sin_escrituras(
    sesion_edificio: Session, identidad_edificio: Identidad
) -> None:
    from proptech_core.complejos.aplicacion import grupos
    from proptech_core.complejos.aplicacion.errores import EntradaInvalida

    a, b = crear(sesion_edificio, identidad_edificio), crear(sesion_edificio, identidad_edificio)
    propia = alta_unidad(sesion_edificio, identidad_edificio, a)
    ajena = alta_unidad(sesion_edificio, identidad_edificio, b)
    admin_b, persona_b = uuid4(), uuid4()
    sesion_edificio.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"), {"id": str(admin_b)}
    )
    sesion_edificio.execute(
        text("INSERT INTO administracion (id,nombre) VALUES (:id,'Otra ficticia')"), {"id": admin_b}
    )
    sesion_edificio.execute(
        text(
            "INSERT INTO persona (id,administracion_id,nombre) "
            "VALUES (:id,:admin,'Otra persona ficticia')"
        ),
        {"id": persona_b, "admin": admin_b},
    )
    identidad_b = Identidad(admin_b, persona_b)
    c = crear(sesion_edificio, identidad_b)
    otra_admin = alta_unidad(sesion_edificio, identidad_b, c)
    sesion_edificio.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"),
        {"id": str(identidad_edificio.administracion_id)},
    )
    grupo = grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=a,
        datos={"clave": "valido", "nombre": "Válido", "metodo": "coeficiente"},
        miembros=[{"unidad_id": propia}],
    )
    antes = grupos.listar_grupos(sesion_edificio, a)
    errores = []
    for ajeno in (ajena, otra_admin):
        with pytest.raises(EntradaInvalida) as error:
            grupos.crear_grupo(
                sesion_edificio,
                identidad_edificio,
                complejo_id=a,
                datos={"clave": "ajeno", "nombre": "Ajeno", "metodo": "coeficiente"},
                miembros=[{"unidad_id": ajeno}],
            )
        errores.append((error.value.campo, str(error.value)))
        with pytest.raises(EntradaInvalida):
            grupos.fijar_unidades(
                sesion_edificio,
                grupo_id=grupo,
                modo="propios",
                miembros=[{"unidad_id": ajeno, "coeficiente": "1"}],
            )
        assert grupos.listar_grupos(sesion_edificio, a) == antes
    assert errores == [("unidades", "unidades: valor inválido")] * 2


@pytest.mark.parametrize(
    "cambio", [{"metodo": "partes_iguales"}, {"nombre": "Otro"}, {"clave": "otro"}]
)
def test_generales_inmutable(
    sesion_edificio: Session, identidad_edificio: Identidad, cambio: dict[str, Any]
) -> None:
    from proptech_core.complejos.aplicacion import grupos
    from proptech_core.complejos.aplicacion.errores import EntradaInvalida

    edificio = crear(sesion_edificio, identidad_edificio)
    grupo = grupos.listar_grupos(sesion_edificio, edificio)[0]["id"]
    with pytest.raises(EntradaInvalida):
        grupos.editar_grupo(sesion_edificio, grupo_id=grupo, cambios=cambio)
    with pytest.raises(EntradaInvalida):
        grupos.fijar_unidades(sesion_edificio, grupo_id=grupo, modo="propios", miembros=[])
    assert grupos.listar_grupos(sesion_edificio, edificio)[0]["metodo"] == "coeficiente"


@pytest.mark.parametrize(
    ("modo", "coeficiente", "metodo"),
    [
        ("renormalizado", "0.5", "coeficiente"),
        ("propios", None, "coeficiente"),
        ("propios", "0.5", "superficie"),
        ("propios", 0.5, "coeficiente"),
    ],
)
def test_modo_incoherente_no_se_guarda(
    sesion_edificio: Session,
    identidad_edificio: Identidad,
    modo: str,
    coeficiente: Any,
    metodo: str,
) -> None:
    from proptech_core.complejos.aplicacion import grupos
    from proptech_core.complejos.aplicacion.errores import EntradaInvalida

    edificio = crear(sesion_edificio, identidad_edificio)
    unidad = alta_unidad(sesion_edificio, identidad_edificio, edificio)
    with pytest.raises(EntradaInvalida):
        grupos.crear_grupo(
            sesion_edificio,
            identidad_edificio,
            complejo_id=edificio,
            datos={"clave": "incoherente", "nombre": "Incoherente", "metodo": metodo},
            modo=modo,
            miembros=[{"unidad_id": unidad, "coeficiente": coeficiente}],
        )
    assert len(grupos.listar_grupos(sesion_edificio, edificio)) == 1


def test_miembro_y_clave_repetidos(sesion_edificio: Session, identidad_edificio: Identidad) -> None:
    from proptech_core.complejos.aplicacion import grupos
    from proptech_core.complejos.aplicacion.errores import Conflicto

    edificio = crear(sesion_edificio, identidad_edificio)
    unidad = alta_unidad(sesion_edificio, identidad_edificio, edificio)
    datos = {"clave": "ascensor", "nombre": "Ascensor", "metodo": "coeficiente"}
    grupo = grupos.crear_grupo(
        sesion_edificio,
        identidad_edificio,
        complejo_id=edificio,
        datos=datos,
        miembros=[{"unidad_id": unidad}],
    )
    with pytest.raises(Conflicto):
        grupos.fijar_unidades(
            sesion_edificio,
            grupo_id=grupo,
            modo="renormalizado",
            miembros=[{"unidad_id": unidad}, {"unidad_id": unidad}],
        )
    with pytest.raises(Conflicto) as error:
        grupos.crear_grupo(
            sesion_edificio, identidad_edificio, complejo_id=edificio, datos=datos, miembros=[]
        )
    assert error.value.campo == "clave"
    assert next(g for g in grupos.listar_grupos(sesion_edificio, edificio) if g["id"] == grupo)[
        "unidades"
    ] == [{"unidad_id": unidad, "coeficiente": None}]
