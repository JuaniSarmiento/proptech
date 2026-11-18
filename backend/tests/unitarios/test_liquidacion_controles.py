"""Los controles antes de emitir (H-012; R34, E6): nivel, orden y detalle, sin base."""

from proptech_core.compartido.dinero import Dinero
from proptech_core.liquidacion.dominio.controles import (
    BloqueDeGrupo,
    ContextoDeControles,
    InformeDeGrupo,
    controles_de,
)

_FUERA = InformeDeGrupo("g1", "Generales", "0.999800", "-0.000200", "fuera_de_tolerancia")
_TODO = ContextoDeControles(
    estado_migracion="pendiente",
    informes=(
        InformeDeGrupo("g0", "Ascensor", "1.000000", "0.000000", "ok"),
        InformeDeGrupo("g2", "Cocheras", "0.800000", "-0.200000", "fuera_de_tolerancia"),
        InformeDeGrupo("g3", "Patio", "0.999900", "-0.000100", "advertencia"),
    ),
    modalidad_de_vencimiento="doble",
    gastos_en_revision=("r1",),
    gastos_sin_ia=("s1", "s2"),
    categorias_faltantes=(("c1", "Seguridad"),),
)
_NEGATIVO = (
    BloqueDeGrupo("g1", "Generales", "ordinario", Dinero("-10000.00")),
    BloqueDeGrupo("g1", "Generales", "extraordinario", Dinero("0.00")),
)


def _codigos(contexto: ContextoDeControles, bloques: tuple[BloqueDeGrupo, ...] = ()) -> list[str]:
    return [c["codigo"] for c in controles_de(contexto, bloques)]


def test_sin_nada_que_avisar_no_hay_controles() -> None:
    assert controles_de(ContextoDeControles(), ()) == []


def test_el_orden_y_el_nivel_son_fijos() -> None:
    controles = controles_de(_TODO, _NEGATIVO)
    assert [(c["codigo"], c["nivel"]) for c in controles] == [
        ("saldos_iniciales_sin_validar", "duro"),
        ("coeficientes_fuera_de_tolerancia", "duro"),
        ("bloque_negativo", "duro"),
        ("doble_vencimiento_sin_regla", "duro"),
        ("gastos_en_revision", "bloqueante"),
        ("gastos_sin_ia", "advertencia"),
        ("gasto_mensual_obligatorio_faltante", "advertencia"),
    ]
    assert all(c["mensaje"].strip() and "detalle" in c for c in controles)


def test_los_estados_de_migracion_cerrados_no_disparan() -> None:
    for estado in ("confirmada", "sin_saldos_previos"):
        assert "saldos_iniciales_sin_validar" not in _codigos(
            ContextoDeControles(estado_migracion=estado)
        )
    assert _codigos(ContextoDeControles(estado_migracion="pendiente")) == [
        "saldos_iniciales_sin_validar"
    ]
    control = controles_de(ContextoDeControles(estado_migracion="pendiente"), ())[0]
    assert control["detalle"] == {"estado_migracion": "pendiente"}


def test_solo_los_grupos_fuera_de_tolerancia_entran_al_detalle() -> None:
    contexto = ContextoDeControles(informes=(*_TODO.informes, _FUERA))
    (control,) = controles_de(contexto, ())
    assert control["detalle"] == {
        "grupos": [
            {"grupo_id": "g2", "nombre": "Cocheras", "suma": "0.800000", "diferencia": "-0.200000"},
            {
                "grupo_id": "g1",
                "nombre": "Generales",
                "suma": "0.999800",
                "diferencia": "-0.000200",
            },
        ]
    }


def test_un_advertencia_de_coeficientes_no_es_un_control() -> None:
    contexto = ContextoDeControles(
        informes=(InformeDeGrupo("g3", "Patio", "0.999900", "-0.000100", "advertencia"),)
    )
    assert _codigos(contexto) == []


def test_bloque_negativo_solo_con_importe_menor_que_cero() -> None:
    assert _codigos(ContextoDeControles(), (_NEGATIVO[1],)) == []
    (control,) = controles_de(ContextoDeControles(), _NEGATIVO)
    assert control["detalle"] == {
        "bloques": [
            {"grupo_id": "g1", "nombre": "Generales", "bloque": "ordinario", "importe": "-10000.00"}
        ]
    }


def test_doble_vencimiento_dice_la_modalidad() -> None:
    (control,) = controles_de(ContextoDeControles(modalidad_de_vencimiento="doble"), ())
    assert control["codigo"] == "doble_vencimiento_sin_regla"
    assert control["detalle"] == {"modalidad": "doble"}


def test_gastos_en_revision_y_sin_ia_traen_cantidad_e_ids() -> None:
    contexto = ContextoDeControles(gastos_en_revision=("r1", "r2"), gastos_sin_ia=("s1",))
    revision, sin_ia = controles_de(contexto, ())
    assert revision["detalle"] == {"cantidad": 2, "gastos": ["r1", "r2"]}
    assert sin_ia["detalle"] == {"cantidad": 1, "gastos": ["s1"]}
    assert "2" in revision["mensaje"]
    assert sin_ia["mensaje"] == "Hay 1 factura sin cargar"
    dos = controles_de(ContextoDeControles(gastos_sin_ia=("a", "b")), ())[0]
    assert dos["mensaje"] == "Hay 2 facturas sin cargar"


def test_obligatorio_faltante_nombra_las_categorias() -> None:
    (control,) = controles_de(ContextoDeControles(categorias_faltantes=(("c1", "Seguridad"),)), ())
    assert control["nivel"] == "advertencia"
    assert control["detalle"] == {"categorias": [{"categoria_id": "c1", "nombre": "Seguridad"}]}
    assert "Seguridad" in control["mensaje"]


def test_pagos_sin_confirmar_es_una_advertencia_al_final_y_sin_pagos_no_aparece() -> None:
    from proptech_core.liquidacion.dominio.controles import ContextoDeControles, controles_de

    assert [c["codigo"] for c in controles_de(ContextoDeControles(), [])] == []
    contexto = ContextoDeControles(
        gastos_sin_ia=("g1",), pagos_sin_confirmar=2, total_sin_confirmar="45000.00"
    )
    controles = controles_de(contexto, [])
    assert [c["codigo"] for c in controles] == ["gastos_sin_ia", "pagos_sin_confirmar"]
    assert controles[-1]["nivel"] == "advertencia"
    assert controles[-1]["detalle"] == {"cantidad": 2, "total": "45000.00"}
