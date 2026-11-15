"""El armado de la preliquidación (H-011; R01, R07, R13, R16, R22): totales y por unidad."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.liquidacion.dominio.preliquidacion import (
    CargoParticular,
    CategoriaDeGasto,
    DatosDeLaPreliquidacion,
    LineaDeGasto,
    preliquidar,
)
from proptech_core.liquidacion.dominio.reparto import (
    GrupoDelEdificio,
    MiembroDelGrupo,
    UnidadDelPadron,
)


class Torre:
    """La base de los ejemplos de HISTORIAS.md (H-011)."""

    def __init__(self) -> None:
        coeficientes = {"1A": "0.300000", "1B": "0.300000", "2A": "0.250000", "2B": "0.150000"}
        self.unidades = {
            (u := UnidadDelPadron(uuid4(), n, Decimal(c), Decimal("0.00"))).id: u
            for n, c in coeficientes.items()
        }
        self.u = {u.identificador: u.id for u in self.unidades.values()}
        self.generales = GrupoDelEdificio(uuid4(), "Generales", "coeficiente", True)
        self.ascensor = GrupoDelEdificio(
            uuid4(),
            "Ascensor",
            "coeficiente",
            False,
            (MiembroDelGrupo(self.u["2A"]), MiembroDelGrupo(self.u["2B"])),
        )
        self.categorias = {
            (c := CategoriaDeGasto(uuid4(), n, i)).id: c
            for i, n in enumerate(("Limpieza", "Ascensor", "Pintura"))
        }
        self.c = {c.nombre: c.id for c in self.categorias.values()}

    def datos(self, lineas: list[LineaDeGasto], **kw: Any) -> DatosDeLaPreliquidacion:
        base: dict[str, Any] = {
            "complejo_id": uuid4(),
            "periodo": date(2026, 11, 1),
            "vencimiento": date(2026, 11, 10),
            "porcentaje_fondo": Porcentaje("5.00"),
            "version_de_configuracion": "version-1",
            "unidades": self.unidades,
            "grupos": (self.generales, self.ascensor),
            "categorias": self.categorias,
            "lineas": lineas,
        }
        return DatosDeLaPreliquidacion(**{**base, **kw})

    def base(self) -> list[LineaDeGasto]:
        return [
            LineaDeGasto(self.generales.id, "ordinario", self.c["Limpieza"], Dinero("100000.00")),
            LineaDeGasto(
                self.generales.id, "ordinario", self.c["Limpieza"], Dinero("10000.00"), True
            ),
            LineaDeGasto(self.ascensor.id, "ordinario", self.c["Ascensor"], Dinero("40000.00")),
            LineaDeGasto(
                self.generales.id, "extraordinario", self.c["Pintura"], Dinero("50000.00")
            ),
        ]


def _unidad(cuerpo: dict[str, Any], identificador: str) -> dict[str, Any]:
    return next(u for u in cuerpo["unidades"] if u["identificador"] == identificador)


def test_la_base_de_los_ejemplos_unidad_por_unidad() -> None:
    t = Torre()
    cuerpo = preliquidar(
        t.datos(t.base(), cargos=[CargoParticular(t.u["1B"], "Multa", Dinero("5000.00"))])
    )
    esperado = {
        "1A": ("27000.00", "1350.00", "15000.00", "43350.00"),
        "1B": ("27000.00", "1350.00", "15000.00", "48350.00"),
        "2A": ("47500.00", "2375.00", "12500.00", "62375.00"),
        "2B": ("28500.00", "1425.00", "7500.00", "37425.00"),
    }
    for identificador, (ordinaria, fondo, extra, total) in esperado.items():
        u = _unidad(cuerpo, identificador)
        assert (u["ordinaria"], u["fondo_de_reserva"], u["extraordinaria"], u["total"]) == (
            ordinaria,
            fondo,
            extra,
            total,
        )
    assert _unidad(cuerpo, "1B")["cargos_particulares"] == [
        {"concepto": "Multa", "importe": "5000.00"}
    ]
    assert cuerpo["totales"] == {
        "gastos": "190000.00",
        "notas_de_credito": "10000.00",
        "fondo_de_reserva": "6500.00",
        "prorrateado": "186500.00",
        "cargos_particulares": "5000.00",
        "intereses": "0.00",
        "total": "191500.00",
    }


def test_las_unidades_vienen_todas_en_orden_natural() -> None:
    t = Torre()
    cuerpo = preliquidar(t.datos(t.base()))
    assert [u["identificador"] for u in cuerpo["unidades"]] == ["1A", "1B", "2A", "2B"]


def test_por_grupo_sólo_trae_los_grupos_con_gastos_en_los_que_participa() -> None:
    t = Torre()
    cuerpo = preliquidar(t.datos(t.base()))
    assert [g["grupo_id"] for g in _unidad(cuerpo, "1A")["por_grupo"]] == [str(t.generales.id)]
    de_2a = {g["grupo_id"]: g for g in _unidad(cuerpo, "2A")["por_grupo"]}
    assert de_2a[str(t.ascensor.id)]["ordinaria"] == "25000.00"
    assert de_2a[str(t.generales.id)]["ordinaria"] == "22500.00"
    assert de_2a[str(t.ascensor.id)]["extraordinaria"] == "0.00"
    assert [(g["nombre"], g["ordinario"], g["extraordinario"]) for g in cuerpo["grupos"]] == [
        ("Generales", "90000.00", "50000.00"),
        ("Ascensor", "40000.00", "0.00"),
    ]


def test_un_grupo_sin_gastos_no_aparece() -> None:
    t = Torre()
    solo_generales = [LineaDeGasto(t.generales.id, "ordinario", t.c["Limpieza"], Dinero("100.00"))]
    cuerpo = preliquidar(t.datos(solo_generales))
    assert [g["nombre"] for g in cuerpo["grupos"]] == ["Generales"]
    assert all(
        g["grupo_id"] != str(t.ascensor.id) for u in cuerpo["unidades"] for g in u["por_grupo"]
    )


def test_un_periodo_solo_de_ascensor_deja_sin_obligacion_a_las_otras() -> None:
    t = Torre()
    cuerpo = preliquidar(
        t.datos([LineaDeGasto(t.ascensor.id, "ordinario", t.c["Ascensor"], Dinero("40000.00"))])
    )
    assert _unidad(cuerpo, "1A")["sin_obligacion"] is True
    assert _unidad(cuerpo, "1A")["total"] == "0.00"
    assert _unidad(cuerpo, "2A")["sin_obligacion"] is False


def test_el_interes_no_genera_obligacion_pero_suma_al_total() -> None:
    t = Torre()
    cuerpo = preliquidar(
        t.datos(
            [LineaDeGasto(t.ascensor.id, "ordinario", t.c["Ascensor"], Dinero("40000.00"))],
            intereses={t.u["1A"]: Dinero("2000.00")},
        )
    )
    u = _unidad(cuerpo, "1A")
    assert (u["intereses"], u["sin_obligacion"], u["total"]) == ("2000.00", True, "2000.00")
    assert cuerpo["totales"]["intereses"] == "2000.00"
    assert cuerpo["totales"]["total"] == "44000.00"  # 40.000 + fondo 2.000 + interés 2.000


def test_el_fondo_no_lleva_cargos_ni_intereses() -> None:
    t = Torre()
    cuerpo = preliquidar(
        t.datos(
            t.base(),
            cargos=[CargoParticular(t.u["1B"], "Multa", Dinero("5000.00"))],
            intereses={t.u["1A"]: Dinero("100.00")},
        )
    )
    assert _unidad(cuerpo, "1A")["fondo_de_reserva"] == _unidad(cuerpo, "1B")["fondo_de_reserva"]


def test_fondo_en_cero_por_ciento() -> None:
    t = Torre()
    cuerpo = preliquidar(t.datos(t.base(), porcentaje_fondo=Porcentaje("0.00")))
    assert cuerpo["porcentaje_fondo"] == "0.00"
    assert {u["fondo_de_reserva"] for u in cuerpo["unidades"]} == {"0.00"}


def test_categorias_netas_de_notas_con_porcentaje_y_nombre() -> None:
    t = Torre()
    cuerpo = preliquidar(t.datos(t.base()))
    ordinario = cuerpo["bloques"]["ordinario"]
    assert ordinario["subtotal"] == "130000.00"
    assert [(c["nombre"], c["importe"], c["porcentaje"]) for c in ordinario["categorias"]] == [
        ("Limpieza", "90000.00", "69.23"),
        ("Ascensor", "40000.00", "30.77"),
    ]
    assert cuerpo["bloques"]["extraordinario"]["categorias"][0]["porcentaje"] == "100.00"


def test_porcentaje_medio_hacia_arriba() -> None:
    t = Torre()
    lineas = [
        LineaDeGasto(t.generales.id, "ordinario", t.c["Limpieza"], Dinero("1.00")),
        LineaDeGasto(t.generales.id, "ordinario", t.c["Pintura"], Dinero("31.00")),
    ]
    categorias = preliquidar(t.datos(lineas))["bloques"]["ordinario"]["categorias"]
    # 1/32 = 3,125 % y 31/32 = 96,875 %: medio hacia arriba, no al par (que daría 3,12 y 96,88).
    assert [c["porcentaje"] for c in categorias] == ["3.13", "96.88"]


def test_bloque_vacio_tiene_subtotal_cero_y_sin_categorias() -> None:
    t = Torre()
    cuerpo = preliquidar(
        t.datos([LineaDeGasto(t.generales.id, "ordinario", t.c["Limpieza"], Dinero("10.00"))])
    )
    assert cuerpo["bloques"]["extraordinario"] == {"subtotal": "0.00", "categorias": []}


def test_sin_gastos_todo_en_cero() -> None:
    t = Torre()
    cuerpo = preliquidar(t.datos([]))
    assert cuerpo["totales"]["total"] == "0.00"
    assert all(u["sin_obligacion"] for u in cuerpo["unidades"])


def test_las_sumas_cierran_con_un_reparto_con_centavos() -> None:
    t = Torre()
    lineas = [LineaDeGasto(t.generales.id, "ordinario", t.c["Limpieza"], Dinero("333.33"))]
    cuerpo = preliquidar(t.datos(lineas, porcentaje_fondo=Porcentaje("3.33")))
    suma = sum((Decimal(u["total"]) for u in cuerpo["unidades"]), Decimal(0))
    assert suma == Decimal(cuerpo["totales"]["total"])
    assert Decimal(cuerpo["totales"]["prorrateado"]) == Decimal("333.33") + Decimal(
        cuerpo["totales"]["fondo_de_reserva"]
    )


def test_la_huella_es_estable_y_cambia_con_cualquier_importe() -> None:
    t = Torre()
    datos = t.datos(t.base())
    huella = preliquidar(datos)["huella"]
    assert preliquidar(datos)["huella"] == huella
    mas = [LineaDeGasto(t.generales.id, "ordinario", t.c["Limpieza"], Dinero("1.00"))]
    cambios: list[dict[str, Any]] = [
        {"lineas": [*t.base(), *mas]},
        {"vencimiento": date(2026, 11, 11)},
        {"version_de_configuracion": "version-2"},
        {"porcentaje_fondo": Porcentaje("6.00")},
    ]
    for cambio in cambios:
        otro = replace(datos, **cambio)
        assert preliquidar(otro)["huella"] != huella, cambio


def test_los_cargos_se_ordenan_para_que_la_huella_no_dependa_del_orden_de_lectura() -> None:
    t = Torre()
    a = CargoParticular(t.u["1B"], "Multa", Dinero("5.00"))
    b = CargoParticular(t.u["1B"], "Arreglo", Dinero("7.00"))
    complejo = uuid4()
    uno = preliquidar(t.datos(t.base(), cargos=[a, b], complejo_id=complejo))
    otro = preliquidar(t.datos(t.base(), cargos=[b, a], complejo_id=complejo))
    assert uno == otro


def test_un_gasto_de_un_grupo_desconocido_es_un_error_y_no_un_reparto_silencioso() -> None:
    t = Torre()
    desconocido: UUID = uuid4()
    with pytest.raises(KeyError):
        preliquidar(
            t.datos([LineaDeGasto(desconocido, "ordinario", t.c["Limpieza"], Dinero("1.00"))])
        )
