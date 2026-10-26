"""3.1 · Cuenta de unidad y candado contra PostgreSQL real (D2, D3, RC-05, RC2-01/02, DB-4)."""

import threading
import time
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.cuenta_corriente.aplicacion import cuentas
from proptech_core.cuenta_corriente.aplicacion.errores import (
    AislamientoNoAdmitido,
    BloqueoFueraDeOrden,
    IdentidadDeOtraAdministracion,
    NoEncontrado,
    RegistroFueraDeTransaccion,
)

from ._cuenta_corriente import Mundo, contar_escrituras, en_hilo, sembrar, sesion_app
from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def _candados(s: Session, cuenta: UUID) -> int:
    return int(
        s.execute(
            text("SELECT count(*) FROM candado_de_cuenta WHERE cuenta_id = :c"), {"c": cuenta}
        ).scalar_one()
    )


def test_dos_pedidos_dan_la_misma_cuenta_con_su_candado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    u = mundo.unidades[0]
    with sesion_app(base_del_edificio, mundo.admin) as s:
        primera = cuentas.cuenta_de_unidad(s, complejo_id=mundo.complejo, unidad_id=u)
        assert cuentas.cuenta_de_unidad(s, complejo_id=mundo.complejo, unidad_id=u) == primera
        assert _candados(s, primera) == 1
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        assert cuentas.cuenta_de_unidad(s, complejo_id=mundo.complejo, unidad_id=u) == primera
        assert (
            s.execute(
                text("SELECT count(*) FROM cuenta WHERE unidad_id = :u"), {"u": u}
            ).scalar_one()
            == 1
        )


def test_dos_transacciones_simultaneas_dan_la_misma_cuenta(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    u = mundo.unidades[1]
    with (
        sesion_app(base_del_edificio, mundo.admin) as s1,
        sesion_app(base_del_edificio, mundo.admin) as s2,
    ):
        primera = cuentas.cuenta_de_unidad(s1, complejo_id=mundo.complejo, unidad_id=u)
        hilo, r = en_hilo(
            lambda: cuentas.cuenta_de_unidad(s2, complejo_id=mundo.complejo, unidad_id=u)
        )
        time.sleep(0.5)
        assert hilo.is_alive(), "la segunda debía esperar el único de la primera"
        s1.commit()
        hilo.join(20)
        assert "error" not in r, r.get("error")
        assert r["valor"] == primera


def test_rollback_no_deja_cuenta_ni_candado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    u = mundo.unidades[2]
    sql = text("SELECT count(*) FROM cuenta WHERE unidad_id = :u")
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = cuentas.cuenta_de_unidad(s, complejo_id=mundo.complejo, unidad_id=u)
        assert (s.execute(sql, {"u": u}).scalar_one(), _candados(s, cuenta)) == (1, 1)
        s.rollback()
        s.begin()
        assert (s.execute(sql, {"u": u}).scalar_one(), _candados(s, cuenta)) == (0, 0)


@pytest.mark.parametrize("cual", ["otro_edificio", "otra_administracion"])
def test_unidad_ajena_no_encontrada(
    base_del_edificio: BaseDeEdificio, mundo: Mundo, cual: str
) -> None:
    u = mundo.unidad_otro_complejo if cual == "otro_edificio" else mundo.unidad_b
    with sesion_app(base_del_edificio, mundo.admin) as s:
        # E11: el libro no lee `unidad`; la FK compuesta rechaza el INSERT dentro de un SAVEPOINT.
        with pytest.raises(NoEncontrado):
            cuentas.cuenta_de_unidad(s, complejo_id=mundo.complejo, unidad_id=u)
        assert s.execute(text("SELECT count(*) FROM cuenta")).scalar_one() == 0
        assert s.execute(text("SELECT 1")).scalar_one() == 1  # la transacción sigue usable


def test_fuera_de_transaccion(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin, comenzar=False) as s:
        assert not s.in_transaction()
        with pytest.raises(RegistroFueraDeTransaccion):
            cuentas.cuenta_de_unidad(s, complejo_id=mundo.complejo, unidad_id=mundo.unidades[0])
        with pytest.raises(RegistroFueraDeTransaccion):
            cuentas.bloquear_cuentas(s, [mundo.unidades[0]])


def test_bloquear_recrea_un_candado_borrado(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = cuentas.cuenta_de_unidad(
            s, complejo_id=mundo.complejo, unidad_id=mundo.unidades[3]
        )
        s.commit()
    with arranque(base_del_edificio) as c:
        c.execute("DELETE FROM candado_de_cuenta WHERE cuenta_id = %s", (cuenta,))
    with sesion_app(base_del_edificio, mundo.admin) as s:
        s.execute(text("SELECT 1"))
        cuentas.bloquear_cuentas(s, [cuenta])
        assert _candados(s, cuenta) == 1


def test_rebloqueo_idempotente_ids_repetidos_y_orden(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        a, b = sorted(
            cuentas.crear_cuentas_de_unidades(
                s, complejo_id=mundo.complejo, unidad_ids=mundo.unidades[4:6]
            ).values()
        )
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin) as s:
        s.execute(text("SELECT 1"))
        cuentas.bloquear_cuentas(s, [a, a])  # RC2-02: repetido no es candado faltante
        cuentas.bloquear_cuentas(s, [a, b])
        cuentas.bloquear_cuentas(s, [b])  # rebloqueo interno de una operación unitaria
    with sesion_app(base_del_edificio, mundo.admin) as s:
        s.execute(text("SELECT 1"))
        cuentas.bloquear_cuentas(s, [b])
        with pytest.raises(BloqueoFueraDeOrden):  # RC2-01
            cuentas.bloquear_cuentas(s, [a])
    with sesion_app(base_del_edificio, mundo.admin) as s:
        s.execute(text("SELECT 1"))
        cuentas.bloquear_cuentas(s, [b])
        s.commit()
        s.execute(text("SELECT 1"))
        cuentas.bloquear_cuentas(s, [a])  # otra transacción: lo tomado antes no cuenta


def test_bloquear_cuenta_inexistente_o_ajena(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin_b) as s:
        ajena = cuentas.cuenta_de_unidad(s, complejo_id=mundo.complejo_b, unidad_id=mundo.unidad_b)
        s.commit()
    from uuid import uuid4

    for cuenta in (uuid4(), ajena):
        with sesion_app(base_del_edificio, mundo.admin) as s:
            s.execute(text("SELECT 1"))
            with pytest.raises(NoEncontrado):
                cuentas.bloquear_cuentas(s, [cuenta])


def test_repeatable_read_rechazado(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = cuentas.cuenta_de_unidad(
            s, complejo_id=mundo.complejo, unidad_id=mundo.unidades[6]
        )
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin, aislamiento="REPEATABLE READ") as s:
        s.execute(text("SELECT 1"))
        with pytest.raises(AislamientoNoAdmitido):
            cuentas.bloquear_cuentas(s, [cuenta])
    with sesion_app(base_del_edificio, mundo.admin) as s:
        s.execute(text("SELECT 1"))
        cuentas.bloquear_cuentas(s, [cuenta])  # READ COMMITTED sí


def test_identidad_de_otra_administracion_antes_de_escribir(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin_b) as s:
        escrituras = contar_escrituras(s)
        s.execute(text("SELECT 1"))
        with pytest.raises(IdentidadDeOtraAdministracion):
            cuentas.exigir_identidad(s, mundo.identidad)
        assert escrituras == []


#: El mutante de RC-05 pone esto en False: cada operación toma su cuenta incrementalmente.
PREBLOQUEAR = True


def test_prebloqueo_compone_ordenes_opuestos_sin_interbloqueo(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """RC-05: A/B y B/A prebloqueando el conjunto terminan las dos, sin 40P01.

    Con el candado real la segunda espera a la primera en el prebloqueo, así que la señal de
    "ya tomé mi primera cuenta" se espera con plazo y sin exigir que llegue (L-020)."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        a, b = sorted(
            cuentas.crear_cuentas_de_unidades(
                s, complejo_id=mundo.complejo, unidad_ids=mundo.unidades[7:9]
            ).values()
        )
        s.commit()
    listos = [threading.Event(), threading.Event()]

    def operar(yo: int, orden: list[UUID]) -> str:
        with sesion_app(base_del_edificio, mundo.admin) as s:
            cuentas.bloquear_cuentas(s, [a, b] if PREBLOQUEAR else [orden[0]])
            listos[yo].set()
            listos[1 - yo].wait(2)
            for cuenta in orden:  # operaciones unitarias con su rebloqueo interno
                cuentas.bloquear_cuentas(s, [cuenta])
            s.commit()
            return "ok"

    h1, r1 = en_hilo(lambda: operar(0, [a, b]))
    h2, r2 = en_hilo(lambda: operar(1, [b, a]))
    h1.join(40)
    h2.join(40)
    assert (r1.get("valor"), r2.get("valor")) == ("ok", "ok"), (r1.get("error"), r2.get("error"))
