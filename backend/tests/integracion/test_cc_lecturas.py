"""3.7 · Lecturas contra PostgreSQL real (D12, DB-2, RC-08, RC-13, RC-15, AN-06, BE-6)."""

import json
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import creditos, emisiones, lecturas
from proptech_core.cuenta_corriente.aplicacion.emisiones import ObligacionAEmitir
from proptech_core.cuenta_corriente.dominio.imputacion import Componente, Destino

from ._cuenta_corriente import Mundo, contar_escrituras, sembrar, sesion_app
from ._edificios import BaseDeEdificio
from .test_umbral_migracion import arranque

pytestmark = pytest.mark.integracion
GRANDES = {"obligacion", "movimiento", "imputacion"}


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio)


def d(t: str) -> Dinero:
    return Dinero(t)


def emitir(s: Session, mundo: Mundo, periodo: date, *importes: str) -> emisiones.EmisionRegistrada:
    return emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=[
            ObligacionAEmitir(
                mundo.unidades[n], periodo.replace(day=10), d(i), d("0.00"), d("0.00")
            )
            for n, i in enumerate(importes)
        ],
        request_id=uuid4(),
    )


def pagar(s: Session, mundo: Mundo, cuenta: UUID, importe: str, **extra: Any) -> UUID:
    datos: dict[str, Any] = {
        "cuenta_id": cuenta,
        "tipo": "pago",
        "importe": d(importe),
        "fecha_valor": date(2026, 10, 20),
        "operacion_id": uuid4(),
        "destino": None,
        "request_id": uuid4(),
    }
    datos.update(extra)
    return creditos.registrar_credito(s, mundo.identidad, **datos)


def test_deuda_del_edificio_coincide_cuenta_por_cuenta(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, date(2026, 10, 1), "100.00", "200.00", "300.00")
        pagar(s, mundo, r.cuentas[mundo.unidades[1]], "250.00")
        escrituras = contar_escrituras(s)
        filas = lecturas.deuda_del_edificio(s, complejo_id=mundo.complejo)
        assert escrituras == []  # ninguna lectura escribe
        assert {f.cuenta_id: f.deuda for f in filas} == {
            c: lecturas.estado_de_cuenta(s, cuenta_id=c).deuda for c in r.cuentas.values()
        }
        assert {f.deuda for f in filas} == {d("100.00"), d("0.00"), d("300.00")}
        # Cada cuenta ve sólo sus movimientos: el pago de $250 deja $50 a favor sólo en la suya.
        assert {f.cuenta_id: f.credito_a_favor for f in filas} == {
            r.cuentas[mundo.unidades[0]]: d("0.00"),
            r.cuentas[mundo.unidades[1]]: d("50.00"),
            r.cuentas[mundo.unidades[2]]: d("0.00"),
        }


def test_deuda_del_edificio_no_trae_cuentas_de_otro_edificio(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """Mutante de lecturas (auditor): la del edificio filtra por edificio, no sólo por tenant."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        r = emitir(s, mundo, date(2026, 10, 1), "100.00")
        # Una emisión por transacción: dos emisiones con cuentas cruzadas en la misma transacción
        # pueden pedir una cuenta menor que la ya bloqueada (BloqueoFueraDeOrden, RC2-01).
        s.commit()
        s.execute(text("SELECT 1"))  # abre la transacción siguiente
        emisiones.registrar_emision(
            s,
            mundo.identidad,
            emision_id=uuid4(),
            complejo_id=mundo.otro_complejo,
            periodo=date(2026, 10, 1),
            obligaciones=[
                ObligacionAEmitir(
                    mundo.unidad_otro_complejo, date(2026, 10, 10), d("7.00"), d("0.00"), d("0.00")
                )
            ],
            request_id=uuid4(),
        )
        filas = lecturas.deuda_del_edificio(s, complejo_id=mundo.complejo)
        assert {f.cuenta_id: f.deuda for f in filas} == {r.cuentas[mundo.unidades[0]]: d("100.00")}


def test_saldo_anterior(base_del_edificio: BaseDeEdificio, mundo: Mundo) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, date(2026, 3, 1), "30000.00")
        abril = emitir(s, mundo, date(2026, 4, 1), "40000.00")
        cuenta = abril.cuentas[mundo.unidades[0]]
        assert abril.saldo_anterior[cuenta] == d("30000.00")  # la foto que devuelve la emisión
        assert lecturas.saldo_anterior(s, emision_id=abril.emision_id, cuenta_id=cuenta) == d(
            "30000.00"
        )
        pagar(s, mundo, cuenta, "30000.00")
        mayo = emitir(s, mundo, date(2026, 5, 1), "40000.00")
        assert lecturas.saldo_anterior(s, emision_id=mayo.emision_id, cuenta_id=cuenta) == d(
            "40000.00"
        )
        # AN-06: la foto devuelta en abril no cambia por leer después de pagar.
        assert lecturas.saldo_anterior(s, emision_id=abril.emision_id, cuenta_id=cuenta) == d(
            "40000.00"
        )
        assert abril.saldo_anterior[cuenta] == d("30000.00")


def test_saldo_anterior_con_credito_a_favor(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        marzo = emitir(s, mundo, date(2026, 3, 1), "30000.00")
        cuenta = marzo.cuentas[mundo.unidades[0]]
        pagar(s, mundo, cuenta, "65000.00")
        abril = emitir(s, mundo, date(2026, 4, 1), "40000.00")
        assert abril.saldo_anterior[cuenta] == d("0.00")
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        assert (e.deuda, e.credito_a_favor) == (d("5000.00"), d("0.00"))


def test_bonificacion_retenida_en_ambas_lecturas(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    """RC-13: noviembre bonificado y anulado, diciembre $40.000."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        nov = emitir(s, mundo, date(2026, 11, 1), "40000.00")
        cuenta = nov.cuentas[mundo.unidades[0]]
        obligacion = s.execute(
            text("SELECT id FROM obligacion WHERE emision_id = :e"), {"e": nov.emision_id}
        ).scalar_one()
        pagar(
            s,
            mundo,
            cuenta,
            "2000.00",
            tipo="bonificacion",
            destino=Destino(obligacion, Componente.ORDINARIA),
        )
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=nov.emision_id, motivo="Error", request_id=uuid4()
        )
        emitir(s, mundo, date(2026, 12, 1), "40000.00")
        e = lecturas.estado_de_cuenta(s, cuenta_id=cuenta)
        fila = next(
            f
            for f in lecturas.deuda_del_edificio(s, complejo_id=mundo.complejo)
            if f.cuenta_id == cuenta
        )
        for x in (e, fila):
            assert (
                x.deuda,
                x.credito_a_favor,
                x.credito_a_favor_aplicable,
                x.credito_a_favor_retenido,
            ) == (
                d("40000.00"),
                d("2000.00"),
                d("0.00"),
                d("2000.00"),
            )


def test_otra_administracion_no_ve_el_edificio(
    base_del_edificio: BaseDeEdificio, mundo: Mundo
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, date(2026, 10, 1), "1.00")
        s.commit()
    with sesion_app(base_del_edificio, mundo.admin_b) as s:
        assert lecturas.deuda_del_edificio(s, complejo_id=mundo.complejo) == []


# --- Planes (DB-2, RC-08, RC-15) ---------------------------------------------------------------


def _cargar_volumen(base: BaseDeEdificio) -> tuple[UUID, UUID, UUID]:
    """3 administraciones, 100 edificios c/u, 20 cuentas por edificio, 12 obligaciones, 12
    movimientos y 24 imputaciones por cuenta: 6.000/72.000/72.000/144.000 filas."""
    admins = [uuid4() for _ in range(3)]
    with base.conectar_app() as c:
        c.autocommit = False
        for adm in admins:
            c.execute("SELECT set_config('app.administracion_id', %s, true)", (str(adm),))
            c.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'Volumen')", (adm,))
            c.execute(
                "INSERT INTO persona (id, administracion_id, nombre) "
                "SELECT gen_random_uuid(), %s, 'P' || g FROM generate_series(1, 20) g",
                (adm,),
            )
            c.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "SELECT gen_random_uuid(), %s, 'E' || g, 'Mendoza' FROM generate_series(1, 100) g",
                (adm,),
            )
            c.execute(
                "INSERT INTO cuenta (id, administracion_id, complejo_id, persona_id, creada_en) "
                "SELECT gen_random_uuid(), %s, cx.id, p.id, now() FROM complejo cx, persona p "
                "WHERE cx.administracion_id = %s AND p.administracion_id = %s",
                (adm, adm, adm),
            )
            c.execute(
                "INSERT INTO obligacion (id, administracion_id, complejo_id, cuenta_id, "
                "operacion_id, "
                "periodo, vencimiento, ordinaria, fondo_de_reserva, extraordinaria, "
                "registrada_en) "
                "SELECT gen_random_uuid(), %s, cu.complejo_id, cu.id, gen_random_uuid(), "
                "make_date(2025, m, 1), make_date(2025, m, 10), 1000, 0, 0, now() "
                "FROM cuenta cu, generate_series(1, 12) m WHERE cu.administracion_id = %s",
                (adm, adm),
            )
            c.execute(
                "INSERT INTO movimiento (id, administracion_id, complejo_id, cuenta_id, tipo, "
                "sentido, "
                "importe, fecha_valor, registrado_por, request_id, registrado_en, operacion_id) "
                "SELECT gen_random_uuid(), %s, cu.complejo_id, cu.id, 'pago', 'credito', 1000, "
                "make_date(2025, m, 15), cu.persona_id, gen_random_uuid(), now(), "
                "gen_random_uuid() "
                "FROM cuenta cu, generate_series(1, 12) m WHERE cu.administracion_id = %s",
                (adm, adm),
            )
            c.execute(
                "INSERT INTO imputacion (id, administracion_id, complejo_id, cuenta_id, "
                "movimiento_id, "
                "sentido_del_movimiento, obligacion_id, componente, importe, corrida_id, "
                "registrada_en) "
                "SELECT gen_random_uuid(), %s, m.complejo_id, m.cuenta_id, m.id, 'credito', o.id, "
                "'ordinaria', 500, gen_random_uuid(), now() FROM movimiento m "
                "JOIN obligacion o ON o.cuenta_id = m.cuenta_id "
                "AND o.administracion_id = m.administracion_id "
                "AND extract(month FROM o.periodo) = extract(month FROM m.fecha_valor), "
                "generate_series(1, 2) WHERE m.administracion_id = %s",
                (adm, adm),
            )
        c.commit()
    with arranque(base) as c:
        c.execute("ANALYZE cuenta, obligacion, movimiento, imputacion")
        conteos = c.execute(
            "SELECT (SELECT count(*) FROM cuenta WHERE administracion_id = ANY(%(a)s)), "
            "(SELECT count(*) FROM obligacion WHERE administracion_id = ANY(%(a)s)), "
            "(SELECT count(*) FROM movimiento WHERE administracion_id = ANY(%(a)s)), "
            "(SELECT count(*) FROM imputacion WHERE administracion_id = ANY(%(a)s))",
            {"a": admins},
        ).fetchone()
        assert conteos == (6000, 72000, 72000, 144000), conteos
    with base.conectar_app() as c:
        c.autocommit = False
        c.execute("SELECT set_config('app.administracion_id', %s, true)", (str(admins[0]),))
        complejo, cuenta = c.execute("SELECT complejo_id, id FROM cuenta LIMIT 1").fetchone()  # type: ignore[misc]
        c.rollback()
    return admins[0], complejo, cuenta


def _barridos(plan: Any) -> set[str]:
    """Las tablas grandes leídas sin el acceso por cuenta: un `Seq Scan` (DB-2) o un índice cuya
    condición no incluye `cuenta_id` (con 3 administraciones, el prefijo de la RLS solo ya
    recorre un tercio de la tabla y el planificador no lo muestra como barrido)."""
    encontrados: set[str] = set()

    def recorrer(nodo: dict[str, Any]) -> None:
        tabla = nodo.get("Relation Name")
        if tabla in GRANDES:
            barrido = nodo.get("Node Type") in {"Seq Scan", "Parallel Seq Scan"}
            sin_cuenta = "cuenta_id" not in nodo.get("Index Cond", "") + nodo.get(
                "Recheck Cond", ""
            )
            if barrido or sin_cuenta:
                encontrados.add(tabla)
        for hijo in nodo.get("Plans", []):
            recorrer(hijo)

    recorrer(plan[0]["Plan"])
    return encontrados


@pytest.fixture(scope="module")
def volumen(base_del_edificio: BaseDeEdificio) -> tuple[UUID, UUID, UUID]:
    return _cargar_volumen(base_del_edificio)


def _plan(base: BaseDeEdificio, admin: UUID, sentencia: str, parametros: dict[str, Any]) -> Any:
    with sesion_app(base, admin) as s:
        fila = s.execute(
            text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sentencia), parametros
        ).scalar_one()
        return json.loads(fila) if isinstance(fila, str) else fila


def test_plan_del_edificio_sin_barrido(
    base_del_edificio: BaseDeEdificio, volumen: tuple[UUID, UUID, UUID]
) -> None:
    admin, complejo, _ = volumen
    sentencia = lecturas.SENTENCIA_DEL_EDIFICIO
    assert _barridos(_plan(base_del_edificio, admin, sentencia, {"complejo": complejo})) == set()


def test_plan_de_una_cuenta_sin_edificio(
    base_del_edificio: BaseDeEdificio, volumen: tuple[UUID, UUID, UUID]
) -> None:
    admin, _, cuenta = volumen
    plan = _plan(
        base_del_edificio,
        admin,
        lecturas.SENTENCIA_DE_CUENTAS.replace(":ids", "ARRAY[CAST(:c AS uuid)]"),
        {"c": str(cuenta)},
    )
    assert _barridos(plan) == set()
