"""3.2 y 3.3 · `registrar_emision` y `anular_emision` contra PostgreSQL real (D4, R17, QA-3)."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import creditos, emisiones, lecturas
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    IdentidadDeOtraAdministracion,
    NoEncontrado,
)

from ._cuenta_corriente import Mundo, contar_escrituras, sembrar, sesion_app
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion
OCT, NOV, DIC = date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1)


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def d(t: str) -> Dinero:
    return Dinero(t)


def obligaciones(mundo: Mundo, *importes: str, desde: int = 0) -> list[ObligacionAEmitir]:
    return [
        ObligacionAEmitir(mundo.unidades[desde + n], date(2026, 10, 10), d(i), d("0.00"), d("0.00"))
        for n, i in enumerate(importes)
    ]


def emitir(
    s: Session,
    mundo: Mundo,
    periodo: date,
    obls: list[ObligacionAEmitir],
    emision_id: UUID | None = None,
) -> emisiones.EmisionRegistrada:
    return emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=emision_id or uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=obls,
        request_id=uuid4(),
    )


def conteos(s: Session) -> dict[str, int]:
    return {
        t: int(s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608 - tablas fijas
        for t in (
            "cuenta",
            "emision",
            "evento_de_emision",
            "obligacion",
            "movimiento",
            "imputacion",
        )
    }


def test_registra_emision_y_obligaciones(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, OCT, obligaciones(mundo, "40000.00", "30000.00"))
        assert r.intento == 1 and len(r.cuentas) == 2
        for cuenta in r.cuentas.values():
            assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda in {
                d("40000.00"),
                d("30000.00"),
            }
        assert set(r.saldo_anterior.values()) == {d("0.00")}


def test_la_misma_emision_dos_veces_no_duplica(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    obls = obligaciones(mundo, "40000.00")
    eid = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, OCT, obls, eid)
        antes = conteos(s)
        assert (antes["emision"], antes["obligacion"]) >= (1, 1)
        r = emitir(s, mundo, OCT, obls, eid)
        assert conteos(s) == antes and r.emision_id == eid


def test_el_mismo_id_con_otras_obligaciones(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    eid = uuid4()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, OCT, obligaciones(mundo, "40000.00"), eid)
        with pytest.raises(Conflicto) as e:
            emitir(s, mundo, OCT, obligaciones(mundo, "41000.00"), eid)
        assert e.value.campo == "emision_id"


def test_segunda_emision_del_periodo_sin_anular(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, OCT, obligaciones(mundo, "40000.00"))
        with pytest.raises(Conflicto) as e:
            emitir(s, mundo, OCT, obligaciones(mundo, "40000.00"))
        assert e.value.campo == "periodo"


def test_emitir_de_nuevo_despues_de_anular_imputa_el_pago_devuelto(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = emitir(s, mundo, NOV, obligaciones(mundo, "40000.00"))
        cuenta = next(iter(primera.cuentas.values()))
        creditos.registrar_credito(
            s,
            mundo.identidad,
            cuenta_id=cuenta,
            tipo="pago",
            importe=d("40000.00"),
            fecha_valor=date(2026, 11, 5),
            operacion_id=uuid4(),
            destino=None,
            request_id=uuid4(),
        )
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("0.00")
        antes = conteos(s)
        emisiones.anular_emision(
            s,
            mundo.identidad,
            emision_id=primera.emision_id,
            motivo="Error de importe",
            request_id=uuid4(),
        )
        despues = conteos(s)
        assert {t: despues[t] - antes[t] for t in antes} == {
            "cuenta": 0,
            "emision": 0,
            "evento_de_emision": 1,
            "obligacion": 0,
            "movimiento": 0,
            "imputacion": 0,
        }
        estado = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (estado.deuda, estado.credito_a_favor) == (d("0.00"), d("40000.00"))
        segunda = emitir(s, mundo, NOV, obligaciones(mundo, "40000.00"))
        assert segunda.intento == 2
        estado = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (estado.deuda, estado.credito_a_favor) == (d("0.00"), d("0.00"))


def test_credito_a_favor_se_imputa_en_la_emision_siguiente(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, OCT, obligaciones(mundo, "50000.00", desde=2))
        cuenta = r.cuentas[mundo.unidades[2]]
        creditos.registrar_credito(
            s,
            mundo.identidad,
            cuenta_id=cuenta,
            tipo="pago",
            importe=d("60000.00"),
            fecha_valor=date(2026, 10, 5),
            operacion_id=uuid4(),
            destino=None,
            request_id=uuid4(),
        )
        emitir(s, mundo, DIC, obligaciones(mundo, "40000.00", desde=2))
        estado = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (estado.deuda, estado.credito_a_favor) == (d("30000.00"), d("0.00"))


@pytest.mark.parametrize(
    "caso,campo",
    [
        ("periodo", "periodo"),
        ("vacia", "obligaciones"),
        ("repetida", "obligaciones"),
        ("cero", "obligaciones"),
    ],
)
def test_entrada_invalida(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, caso: str, campo: str
) -> None:
    obls = obligaciones(mundo, "100.00")
    periodo = OCT
    if caso == "periodo":
        periodo = date(2026, 10, 15)
    elif caso == "vacia":
        obls = []
    elif caso == "repetida":
        obls = obls * 2
    else:
        obls = obligaciones(mundo, "0.00")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        escrituras = contar_escrituras(s)
        with pytest.raises(EntradaInvalida) as e:
            emitir(s, mundo, periodo, obls)
        assert e.value.campo == campo and escrituras == []


def test_unidad_de_otro_edificio(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    obls = [
        ObligacionAEmitir(
            mundo.unidad_otro_complejo, date(2026, 10, 10), d("1.00"), d("0.00"), d("0.00")
        )
    ]
    with sesion_app(base_del_edificio, mundo.admin) as s:
        with pytest.raises(NoEncontrado):
            emitir(s, mundo, OCT, obls)


def test_identidad_de_otra_administracion(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin_b) as s:
        escrituras = contar_escrituras(s)
        with pytest.raises(IdentidadDeOtraAdministracion):
            emitir(s, mundo, OCT, obligaciones(mundo, "1.00"))
        assert escrituras == []


# --- 3.3 ---


def test_anular_sin_motivo(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, OCT, obligaciones(mundo, "1.00"))
        for motivo in ("   ", "x" * 501):
            with pytest.raises(EntradaInvalida) as e:
                emisiones.anular_emision(
                    s, mundo.identidad, emision_id=r.emision_id, motivo=motivo, request_id=uuid4()
                )
            assert e.value.campo == "motivo"


@pytest.mark.parametrize("motivo", ["Error", "Otro motivo"])
def test_anular_dos_veces(base_del_edificio: BaseDeEdificio, mundo: Mundo, motivo: str) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, OCT, obligaciones(mundo, "1.00"))
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=r.emision_id, motivo="Error", request_id=uuid4()
        )
        with pytest.raises(Conflicto) as e:
            emisiones.anular_emision(
                s, mundo.identidad, emision_id=r.emision_id, motivo=motivo, request_id=uuid4()
            )
        assert e.value.campo == "emision_id"
        assert (
            s.execute(
                text("SELECT count(*) FROM evento_de_emision WHERE emision_id = :e"),
                {"e": r.emision_id},
            ).scalar_one()
            == 1
        )


def test_anular_inexistente_o_ajena(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin_b) as s:
        ajena = emisiones.registrar_emision(
            s,
            mundo.identidad_b,
            emision_id=uuid4(),
            complejo_id=mundo.complejo_b,
            periodo=OCT,
            obligaciones=[
                ObligacionAEmitir(
                    mundo.unidad_b, date(2026, 10, 10), d("1.00"), d("0.00"), d("0.00")
                )
            ],
            request_id=uuid4(),
        ).emision_id
        s.commit()
    for emision in (uuid4(), ajena):
        with sesion_app(base_del_edificio, mundo.admin) as s:
            escrituras = contar_escrituras(s)
            with pytest.raises(NoEncontrado):
                emisiones.anular_emision(
                    s, mundo.identidad, emision_id=emision, motivo="Error", request_id=uuid4()
                )
            assert escrituras == []


def test_anular_no_audita(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, OCT, obligaciones(mundo, "1.00"))
        antes = s.execute(text("SELECT count(*) FROM auditoria")).scalar_one()
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=r.emision_id, motivo="Error", request_id=uuid4()
        )
        assert s.execute(text("SELECT count(*) FROM auditoria")).scalar_one() == antes
        eventos = text("SELECT count(*) FROM evento_de_emision WHERE emision_id = :e")
        assert s.execute(eventos, {"e": r.emision_id}).scalar_one() == 1
