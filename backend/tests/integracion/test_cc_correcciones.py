"""3.5 · `corregir` contra PostgreSQL real (D7, E6, E7, RC-04, RC-12, BE-2, BE-5.1, AN-08)."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import correcciones, creditos, emisiones, lecturas
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import (
    Conflicto,
    EntradaInvalida,
    NoEncontrado,
)

from ._cuenta_corriente import Mundo, sembrar, sesion_app
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def d(t: str) -> Dinero:
    return Dinero(t)


def reloj(dia: int, hora: int = 12) -> datetime:
    return datetime(2026, 10, dia, hora, tzinfo=UTC)


def emitir(
    s: Session, mundo: Mundo, unidad: int, ordinaria: str, periodo: date = date(2026, 10, 1)
) -> tuple[UUID, UUID, UUID]:
    r = emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=[
            ObligacionAEmitir(
                mundo.unidades[unidad], periodo.replace(day=10), d(ordinaria), d("0.00"), d("0.00")
            )
        ],
        request_id=uuid4(),
    )
    cuenta = r.cuentas[mundo.unidades[unidad]]
    obligacion = s.execute(
        text("SELECT id FROM obligacion WHERE cuenta_id = :c AND emision_id = :e"),
        {"c": cuenta, "e": r.emision_id},
    ).scalar_one()
    return r.emision_id, cuenta, UUID(str(obligacion))


def interes(
    s: Session, mundo: Mundo, cuenta: UUID, obligacion: UUID, importe: str, corte: date
) -> UUID:
    """Fila anticipada del 4c (la fixture la inserta; ninguna imputación a mano)."""
    m = uuid4()
    s.execute(
        text(
            "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, sentido, "
            "importe, fecha_valor, registrado_por, request_id, registrado_en, obligacion_id, "
            "componente, corte) VALUES (:id, :adm, :c, :cuenta, 'interes', 'debito', :imp, :corte, "
            ":por, :req, now(), :obl, 'interes', :corte)"
        ),
        {
            "id": m,
            "adm": mundo.admin,
            "c": mundo.complejo,
            "cuenta": cuenta,
            "imp": importe,
            "corte": corte,
            "por": mundo.persona,
            "req": uuid4(),
            "obl": obligacion,
        },
    )
    return m


def pagar(
    s: Session,
    mundo: Mundo,
    cuenta: UUID,
    importe: str,
    fecha_valor: date,
    dia: int,
    **extra: object,
) -> UUID:
    return creditos.registrar_credito(
        s,
        mundo.identidad,
        cuenta_id=cuenta,
        tipo="pago",
        importe=d(importe),
        fecha_valor=fecha_valor,
        operacion_id=uuid4(),
        destino=None,
        request_id=uuid4(),
        reloj=lambda: reloj(dia),
        **extra,
    )


def contra(
    s: Session,
    mundo: Mundo,
    movimiento: UUID,
    *,
    op: UUID | None = None,
    motivo: str = "Error de carga",
    complejo: UUID | None = None,
    dia: int = 20,
) -> UUID:
    return correcciones.corregir(
        s,
        mundo.identidad,
        complejo_id=complejo or mundo.complejo,
        pedido=PedidoDeCorreccion(
            "contra_asiento", op or uuid4(), motivo, movimiento_id=movimiento
        ),
        request_id=uuid4(),
        reloj=lambda: reloj(dia),
    )


def credito_corr(
    s: Session,
    mundo: Mundo,
    obligacion: UUID,
    importe: str,
    *,
    op: UUID | None = None,
    motivo: str = "Cobrado de más",
) -> UUID:
    return correcciones.corregir(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        pedido=PedidoDeCorreccion(
            "credito", op or uuid4(), motivo, obligacion_id=obligacion, importe=d(importe)
        ),
        request_id=uuid4(),
    )


def favor(s: Session, cuenta: UUID) -> dict[UUID, Dinero]:
    return lecturas.estado_de_cuenta(s, cuenta_id=cuenta).a_favor_por_credito


def test_contra_asiento_de_un_pago(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, _ = emitir(s, mundo, 0, "1000.00")
        pago = pagar(s, mundo, cuenta, "1000.00", date(2026, 10, 5), 5)
        c = contra(s, mundo, pago)
        fila = s.execute(
            text(
                "SELECT corrige_a, registrado_por, registrado_en, fecha_valor FROM movimiento "
                "WHERE id = :c"
            ),
            {"c": c},
        ).one_or_none()
        assert fila is not None, "la corrección no quedó en el libro"
        assert fila.corrige_a == pago and fila.registrado_por == mundo.persona  # AN-08
        assert fila.fecha_valor == date(2026, 10, 20)
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("1000.00")
        assert (
            s.execute(
                text("SELECT count(*) FROM movimiento WHERE id IN (:a, :b)"), {"a": pago, "b": c}
            ).scalar_one()
            == 2
        )


def test_contra_asiento_de_un_interes_cubierto_devuelve_el_exceso(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 1, "1000.00")
        i1 = interes(s, mundo, cuenta, obl, "300.00", date(2026, 10, 15))
        pago = pagar(s, mundo, cuenta, "300.00", date(2026, 10, 16), 16)
        contra(s, mundo, i1)
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.deuda, e.a_favor_por_credito[pago]) == (d("1000.00"), d("300.00"))


def test_rc04_credito_retroactivo_con_imputacion_posterior(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 2, "40000.00")
        i1 = interes(s, mundo, cuenta, obl, "4000.00", date(2026, 10, 10))
        interes(s, mundo, cuenta, obl, "6000.00", date(2026, 10, 12))
        b = pagar(s, mundo, cuenta, "6000.00", date(2026, 10, 15), 15)
        a = pagar(s, mundo, cuenta, "4000.00", date(2026, 9, 1), 16)
        ordenes: dict[UUID, int] = dict(
            s.execute(
                text("SELECT movimiento_id, orden FROM imputacion WHERE movimiento_id IN (:a, :b)"),
                {"a": a, "b": b},
            ).all()
        )
        assert ordenes[b] < ordenes[a]
        contra(s, mundo, i1, dia=17)
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert {b: e.a_favor_por_credito[b], a: e.a_favor_por_credito[a]} == {
            b: d("0.00"),
            a: d("4000.00"),
        }
        assert e.deuda == d("40000.00")


def test_empate_de_registro_atribucion_estable(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """E7: dos créditos pendientes imputados en la MISMA corrida (misma registrada_en)."""
    for vuelta in range(20):
        unidad = vuelta % 12
        with sesion_app(base_del_edificio, mundo.admin) as s:
            _, cuenta, obl = emitir(s, mundo, unidad, "1.00")
            # Dos pagos a favor antes del interés: quedan pendientes, con fecha valor fija (RC2-08).
            pagar(s, mundo, cuenta, "1.00", date(2026, 1, 1), 1)
            primero = pagar(s, mundo, cuenta, "6000.00", date(2026, 1, 2), 2)
            segundo = pagar(s, mundo, cuenta, "4000.00", date(2026, 1, 3), 3)
            i1 = interes(s, mundo, cuenta, obl, "4000.00", date(2026, 10, 10))
            interes(s, mundo, cuenta, obl, "6000.00", date(2026, 10, 11))
            # Una escritura cualquiera corre imputar_pendientes: los dos en una sola corrida.
            pagar(s, mundo, cuenta, "0.01", date(2026, 10, 20), 20)
            registradas = s.execute(
                text(
                    "SELECT count(DISTINCT registrada_en) FROM imputacion "
                    "WHERE movimiento_id IN (:a, :b)"
                ),
                {"a": primero, "b": segundo},
            ).scalar_one()
            assert registradas == 1
            contra(s, mundo, i1, dia=21)
            f = favor(s, cuenta)
            assert (f[primero], f[segundo]) == (d("0.00"), d("4000.00")), vuelta
            s.rollback()


def test_segunda_correccion_del_mismo_movimiento(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, _ = emitir(s, mundo, 3, "100.00")
        pago = pagar(s, mundo, cuenta, "100.00", date(2026, 10, 5), 5)
        contra(s, mundo, pago)
        with pytest.raises(Conflicto) as e:
            contra(s, mundo, pago)
        assert e.value.campo == "movimiento_id"
        # BE-5.1: la transacción del llamador sigue usable después del 409.
        assert s.execute(text("SELECT 1")).scalar_one() == 1


def test_contra_asiento_sobre_emision_anulada(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emision, cuenta, obl = emitir(s, mundo, 4, "100.00")
        i1 = interes(s, mundo, cuenta, obl, "10.00", date(2026, 10, 15))
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=emision, motivo="Error", request_id=uuid4()
        )
        with pytest.raises(Conflicto) as e:
            contra(s, mundo, i1)
        assert e.value.campo == "movimiento_id"
        with pytest.raises(Conflicto) as e:
            credito_corr(s, mundo, obl, "1.00")
        assert e.value.campo == "obligacion_id"


def test_cadena_e6_credito_de_correccion_equivocado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """$50.000 en vez de $5.000: se contra-asienta una sola vez; el débito de corrección no."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 5, "60000.00")
        mal = credito_corr(s, mundo, obl, "50000.00")
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("10000.00")
        deshace = contra(s, mundo, mal)
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("60000.00")
        with pytest.raises(Conflicto):
            contra(s, mundo, mal)
        with pytest.raises(Conflicto) as e:
            contra(s, mundo, deshace)  # débito de corrección
        assert e.value.campo == "movimiento_id"


def test_original_restaurado_no_se_contra_asienta_otra_vez(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 6, "100.00")
        i1 = interes(s, mundo, cuenta, obl, "10.00", date(2026, 10, 15))
        c1 = contra(s, mundo, i1)
        contra(s, mundo, c1)  # corregir el contra-asiento crédito de un interés: permitido
        assert lecturas.estado_de_cuenta(s, cuenta_id=cuenta).deuda == d("110.00")
        with pytest.raises(Conflicto) as e:
            contra(s, mundo, i1)
        assert e.value.campo == "movimiento_id"


def test_credito_de_correccion_va_con_r04_a_la_deuda_mas_vieja(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """AN-10, R14: aunque referencie octubre, imputa primero agosto."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, 7, "1000.00", date(2026, 8, 1))
        _, _, octubre = emitir(s, mundo, 7, "1000.00", date(2026, 10, 1))
        c = credito_corr(s, mundo, octubre, "500.00")
        periodos = (
            s.execute(
                text(
                    "SELECT o.periodo FROM imputacion i "
                    "JOIN obligacion o ON o.id = i.obligacion_id "
                    "WHERE i.movimiento_id = :m"
                ),
                {"m": c},
            )
            .scalars()
            .all()
        )
        assert periodos == [date(2026, 8, 1)]


@pytest.mark.parametrize("motivo", ["   ", "x" * 501])
def test_motivo_invalido(base_del_edificio: BaseDeEdificio, mundo: Mundo, motivo: str) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, _, obl = emitir(s, mundo, 8, "100.00")
        with pytest.raises(EntradaInvalida) as e:
            credito_corr(s, mundo, obl, "1.00", motivo=motivo)
        assert e.value.campo == "motivo"


@pytest.mark.parametrize("importe", ["0.00", "-1.00"])
def test_importe_no_positivo(base_del_edificio: BaseDeEdificio, mundo: Mundo, importe: str) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, _, obl = emitir(s, mundo, 9, "100.00")
        with pytest.raises(EntradaInvalida) as e:
            credito_corr(s, mundo, obl, importe)
        assert e.value.campo == "importe"


def test_recursos_inexistentes_ajenos_o_de_otro_edificio(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, _ = emitir(s, mundo, 10, "100.00")
        pago = pagar(s, mundo, cuenta, "10.00", date(2026, 10, 5), 5)
        with pytest.raises(NoEncontrado):
            credito_corr(s, mundo, uuid4(), "1.00")
        with pytest.raises(NoEncontrado):
            contra(s, mundo, uuid4())
        with pytest.raises(NoEncontrado):  # AN-09: mismo tenant, otro edificio en la ruta
            contra(s, mundo, pago, complejo=mundo.otro_complejo)


def test_replay_antes_de_validar_y_con_otros_datos(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, _ = emitir(s, mundo, 11, "100.00")
        pago = pagar(s, mundo, cuenta, "100.00", date(2026, 10, 5), 5)
        op = uuid4()
        c = contra(s, mundo, pago, op=op)
        n = s.execute(text("SELECT count(*) FROM imputacion")).scalar_one()
        assert contra(s, mundo, pago, op=op, motivo="  Error de carga ") == c  # motivo normalizado
        assert s.execute(text("SELECT count(*) FROM imputacion")).scalar_one() == n
        for otros in ({"motivo": "Otro motivo"}, {"complejo": mundo.otro_complejo}):
            with pytest.raises(Conflicto) as e:
                contra(s, mundo, pago, op=op, **otros)
            assert e.value.campo == "operacion_id"


def _imputado_por_filas(s: Session, movimiento: UUID) -> Dinero:
    return Dinero(
        s.execute(
            text("SELECT coalesce(sum(importe), 0)::text FROM imputacion WHERE movimiento_id = :m"),
            {"m": movimiento},
        ).scalar_one()
    )


def test_rb4b01_deshacer_c1_no_cuenta_dos_veces_el_pago(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Enmienda E7: E6 deshace C1 y el interés vuelve a contar; el pago B ya se había reimputado al
    capital. B tiene filas por $8.000 pero cuenta $4.000, la más vieja primero."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 8, "40000.00")
        i1 = interes(s, mundo, cuenta, obl, "4000.00", date(2026, 10, 10))
        b = pagar(s, mundo, cuenta, "4000.00", date(2026, 10, 15), 15)
        c1 = contra(s, mundo, i1, dia=16)
        p = pagar(s, mundo, cuenta, "0.01", date(2026, 10, 17), 17)  # reimputa B al capital
        contra(s, mundo, c1, dia=18)  # deshace C1: I1 vuelve a contar
        assert _imputado_por_filas(s, b) == d("8000.00")  # los hechos no se reescriben
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.a_favor_por_credito[b], e.a_favor_por_credito[p]) == (d("0.00"), d("0.00"))
        assert e.deuda == d("39999.99")


def test_rb4b01_interes_nuevo_no_revive_la_imputacion_vieja_de_mas(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Sin deshacer nada: el interés de otro corte (el 4c, todos los meses) sobre la misma
    obligación no hace que B cuente $8.000."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 9, "40000.00")
        i1 = interes(s, mundo, cuenta, obl, "4000.00", date(2026, 10, 10))
        b = pagar(s, mundo, cuenta, "4000.00", date(2026, 10, 15), 15)
        contra(s, mundo, i1, dia=16)
        p = pagar(s, mundo, cuenta, "0.01", date(2026, 10, 17), 17)
        interes(s, mundo, cuenta, obl, "4000.00", date(2026, 11, 10))
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.a_favor_por_credito[b], e.a_favor_por_credito[p]) == (d("0.00"), d("0.00"))
        assert e.deuda == d("39999.99")


def test_identidad_de_otra_administracion_antes_de_escribir(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """RB4B-04 (corr_sin_identidad): error nombrado, no un 42501 de la RLS."""
    from proptech_core.cuenta_corriente.aplicacion.errores import IdentidadDeOtraAdministracion

    from ._cuenta_corriente import contar_escrituras

    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 0, "100.00")
        pago = pagar(s, mundo, cuenta, "10.00", date(2026, 10, 5), 5)
        escrituras = contar_escrituras(s)
        for pedido in (
            PedidoDeCorreccion("contra_asiento", uuid4(), "Error", movimiento_id=pago),
            PedidoDeCorreccion("credito", uuid4(), "Error", obligacion_id=obl, importe=d("1.00")),
        ):
            with pytest.raises(IdentidadDeOtraAdministracion):
                correcciones.corregir(
                    s,
                    mundo.identidad_b,
                    complejo_id=mundo.complejo,
                    pedido=pedido,
                    request_id=uuid4(),
                )
        assert escrituras == []


def test_credito_de_correccion_sobre_obligacion_de_otro_edificio(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """RB4B-04 (credcorr_sin_complejo): mismo tenant, otro edificio: 404 antes de escribir."""
    from ._cuenta_corriente import contar_escrituras

    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emisiones.registrar_emision(
            s,
            mundo.identidad,
            emision_id=uuid4(),
            complejo_id=mundo.otro_complejo,
            periodo=date(2026, 10, 1),
            obligaciones=[
                ObligacionAEmitir(
                    mundo.unidad_otro_complejo,
                    date(2026, 10, 10),
                    d("100.00"),
                    d("0.00"),
                    d("0.00"),
                )
            ],
            request_id=uuid4(),
        )
        cuenta_otra = r.cuentas[mundo.unidad_otro_complejo]
        pagar(s, mundo, cuenta_otra, "150.00", date(2026, 10, 5), 5)  # deja crédito pendiente
        obl = s.execute(
            text("SELECT id FROM obligacion WHERE cuenta_id = :c"), {"c": cuenta_otra}
        ).scalar_one()
        escrituras = contar_escrituras(s)
        with pytest.raises(NoEncontrado):
            credito_corr(s, mundo, obl, "1.00")  # la ruta dice mundo.complejo
        assert escrituras == []


def test_contra_asiento_imputa_pendientes_antes_de_lo_suyo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """RB4B-04 (contra_sin_pendientes), D7: P tiene $50 a favor y aparece un interés de $10 que
    nadie imputó todavía; la corrección corre `imputar_pendientes` antes de insertar."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, obl = emitir(s, mundo, 1, "100.00")
        p = pagar(s, mundo, cuenta, "150.00", date(2026, 10, 5), 5)
        q = pagar(s, mundo, cuenta, "5.00", date(2026, 10, 6), 6)
        interes(s, mundo, cuenta, obl, "10.00", date(2026, 10, 10))
        contra(s, mundo, q, dia=12)
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.deuda, e.a_favor_por_credito[p]) == (d("0.00"), d("40.00"))


def test_fecha_de_la_correccion_es_hoy_en_mendoza(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """RB4B-04 (contra_fecha_utc): a la 01:00 UTC del 21/10 en Mendoza es todavía el 20/10."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _, cuenta, _ = emitir(s, mundo, 2, "100.00")
        pago = pagar(s, mundo, cuenta, "10.00", date(2026, 10, 5), 5)
        c = correcciones.corregir(
            s,
            mundo.identidad,
            complejo_id=mundo.complejo,
            pedido=PedidoDeCorreccion("contra_asiento", uuid4(), "Error", movimiento_id=pago),
            request_id=uuid4(),
            reloj=lambda: datetime(2026, 10, 21, 1, tzinfo=UTC),
        )
        fecha = s.execute(
            text("SELECT fecha_valor FROM movimiento WHERE id = :c"), {"c": c}
        ).scalar_one_or_none()
        assert fecha == date(2026, 10, 20)
