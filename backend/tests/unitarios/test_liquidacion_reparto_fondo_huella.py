"""Reparto por grupo, fondo y huella de la preliquidación (H-011; R01, R07, R13, R15, E3).

Dominio puro, sin base: los mismos números que la aceptación, pero por función.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.liquidacion.dominio.fondo import fondo_de_reserva
from proptech_core.liquidacion.dominio.huella import huella_de
from proptech_core.liquidacion.dominio.reparto import (
    GrupoDelEdificio,
    MiembroDelGrupo,
    SinBaseDeReparto,
    UnidadDelPadron,
    repartir_en_grupo,
)

_COEFICIENTES = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}


def _padron(superficies: dict[str, str] | None = None) -> dict[UUID, UnidadDelPadron]:
    superficies = superficies or {}
    unidades = [
        UnidadDelPadron(uuid4(), nombre, Decimal(c), Decimal(superficies.get(nombre, "0.00")))
        for nombre, c in _COEFICIENTES.items()
    ]
    return {u.id: u for u in unidades}


def _id(unidades: dict[UUID, UnidadDelPadron], identificador: str) -> UUID:
    return next(u.id for u in unidades.values() if u.identificador == identificador)


def _por_nombre(
    unidades: dict[UUID, UnidadDelPadron], reparto: dict[UUID, Dinero]
) -> dict[str, str]:
    return {unidades[i].identificador: m.a_texto() for i, m in reparto.items()}


def _generales() -> GrupoDelEdificio:
    return GrupoDelEdificio(uuid4(), "Generales", "coeficiente", True)


def test_generales_reparte_entre_todas_por_su_coeficiente() -> None:
    unidades = _padron()
    reparto = repartir_en_grupo(Dinero("90000.00"), _generales(), unidades)
    assert _por_nombre(unidades, reparto) == {
        "1A": "27000.00",
        "1B": "27000.00",
        "2A": "22500.00",
        "2B": "13500.00",
    }


def test_mayor_resto_con_desempate_por_orden_natural() -> None:
    unidades = _padron()
    reparto = repartir_en_grupo(Dinero("333.33"), _generales(), unidades)
    assert _por_nombre(unidades, reparto) == {
        "1A": "100.00",
        "1B": "100.00",
        "2A": "83.33",
        "2B": "50.00",
    }


def test_la_suma_da_exacto_el_total() -> None:
    unidades = _padron()
    reparto = repartir_en_grupo(Dinero("0.07"), _generales(), unidades)
    assert sum((m.decimal for m in reparto.values()), Decimal(0)) == Decimal("0.07")


def test_grupo_parcial_renormalizado_usa_el_coeficiente_de_la_unidad() -> None:
    unidades = _padron()
    grupo = GrupoDelEdificio(
        uuid4(),
        "Ascensor",
        "coeficiente",
        False,
        (MiembroDelGrupo(_id(unidades, "2A")), MiembroDelGrupo(_id(unidades, "2B"))),
    )
    reparto = repartir_en_grupo(Dinero("40000.00"), grupo, unidades)
    assert _por_nombre(unidades, reparto) == {"2A": "25000.00", "2B": "15000.00"}


def test_grupo_de_coeficientes_propios_usa_el_del_miembro() -> None:
    unidades = _padron()
    grupo = GrupoDelEdificio(
        uuid4(),
        "Cocheras",
        "coeficiente",
        False,
        (
            MiembroDelGrupo(_id(unidades, "1A"), Decimal("0.800000")),
            MiembroDelGrupo(_id(unidades, "2B"), Decimal("0.200000")),
        ),
    )
    reparto = repartir_en_grupo(Dinero("1000.00"), grupo, unidades)
    assert _por_nombre(unidades, reparto) == {"1A": "800.00", "2B": "200.00"}


def test_por_superficie() -> None:
    unidades = _padron({"1A": "50.00", "2B": "150.00"})
    grupo = GrupoDelEdificio(
        uuid4(),
        "Pileta",
        "superficie",
        False,
        (MiembroDelGrupo(_id(unidades, "1A")), MiembroDelGrupo(_id(unidades, "2B"))),
    )
    reparto = repartir_en_grupo(Dinero("1000.00"), grupo, unidades)
    assert _por_nombre(unidades, reparto) == {"1A": "250.00", "2B": "750.00"}


def test_en_partes_iguales_el_centavo_que_sobra_va_al_primero_en_orden_natural() -> None:
    unidades = _padron()
    grupo = GrupoDelEdificio(
        uuid4(),
        "Cocheras",
        "partes_iguales",
        False,
        tuple(MiembroDelGrupo(_id(unidades, u)) for u in ("2A", "1B", "1A")),
    )
    reparto = repartir_en_grupo(Dinero("100.00"), grupo, unidades)
    assert _por_nombre(unidades, reparto) == {"1A": "33.34", "1B": "33.33", "2A": "33.33"}


def test_total_negativo_reparte_con_su_signo_y_suma_exacto() -> None:
    unidades = _padron()
    reparto = repartir_en_grupo(Dinero("-100.00"), _generales(), unidades)
    assert sum((m.decimal for m in reparto.values()), Decimal(0)) == Decimal("-100.00")


def test_sin_base_de_reparto_se_rechaza_con_el_grupo() -> None:
    unidades = _padron()  # superficies en cero
    grupo = GrupoDelEdificio(
        uuid4(), "Pileta", "superficie", False, (MiembroDelGrupo(_id(unidades, "1A")),)
    )
    with pytest.raises(SinBaseDeReparto) as error:
        repartir_en_grupo(Dinero("10.00"), grupo, unidades)
    assert error.value.grupo_id == grupo.id


def test_grupo_sin_miembros_se_rechaza() -> None:
    grupo = GrupoDelEdificio(uuid4(), "Vacío", "partes_iguales", False)
    with pytest.raises(SinBaseDeReparto):
        repartir_en_grupo(Dinero("10.00"), grupo, _padron())


# --- Fondo ------------------------------------------------------------------------------------


def test_fondo_es_el_porcentaje_de_la_ordinaria_repartido_en_proporcion() -> None:
    unidades = _padron()
    ordinarias = {
        _id(unidades, "1A"): Dinero("27000.00"),
        _id(unidades, "1B"): Dinero("27000.00"),
        _id(unidades, "2A"): Dinero("47500.00"),
        _id(unidades, "2B"): Dinero("28500.00"),
    }
    fondo = fondo_de_reserva(ordinarias, Porcentaje("5.00"), unidades)
    assert _por_nombre(unidades, fondo) == {
        "1A": "1350.00",
        "1B": "1350.00",
        "2A": "2375.00",
        "2B": "1425.00",
    }


def test_fondo_redondea_el_total_medio_hacia_arriba_y_suma_exacto() -> None:
    unidades = _padron()
    ordinarias = {i: Dinero("33.33") for i in unidades}  # 133,32 al 0,50% -> 0,6666 -> 0,67
    fondo = fondo_de_reserva(ordinarias, Porcentaje("0.50"), unidades)
    assert sum((m.decimal for m in fondo.values()), Decimal(0)) == Decimal("0.67")


def test_fondo_en_cero_por_ciento_es_cero_en_cada_unidad() -> None:
    unidades = _padron()
    fondo = fondo_de_reserva({i: Dinero("10.00") for i in unidades}, Porcentaje("0.00"), unidades)
    assert {m.a_texto() for m in fondo.values()} == {"0.00"}
    assert set(fondo) == set(unidades)


def test_fondo_sin_ordinaria_es_cero() -> None:
    unidades = _padron()
    fondo = fondo_de_reserva({i: Dinero("0.00") for i in unidades}, Porcentaje("5.00"), unidades)
    assert {m.a_texto() for m in fondo.values()} == {"0.00"}


# --- Huella -----------------------------------------------------------------------------------


def test_la_huella_son_64_hexadecimales_y_es_estable() -> None:
    cuerpo = {"a": "1.00", "b": [{"x": "2"}]}
    primera = huella_de(cuerpo, "v1")
    assert len(primera) == 64 and primera == primera.lower() and int(primera, 16) >= 0
    assert huella_de({"b": [{"x": "2"}], "a": "1.00"}, "v1") == primera


def test_la_huella_cambia_con_un_importe_o_con_la_version() -> None:
    base = huella_de({"a": "1.00"}, "v1")
    assert huella_de({"a": "1.01"}, "v1") != base
    assert huella_de({"a": "1.00"}, "v2") != base


def test_la_huella_ignora_su_propio_campo() -> None:
    assert huella_de({"a": "1.00", "huella": "x"}, "v1") == huella_de({"a": "1.00"}, "v1")
