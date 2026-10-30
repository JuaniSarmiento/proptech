"""Bloque 7 de `gastos-y-cargos`: período de origen y período de imputación
(D8, P36 resuelta en D-141)."""

import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.gastos.aplicacion import gastos as modulo_gastos

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion


def _categoria_y_grupo(api_edificio: ApiEdificio) -> tuple[str, str]:
    api_edificio.como("super_admin")
    categoria = api_edificio.cliente.post(
        api_edificio.ruta("/categorias"), json={"nombre": f"Cat {uuid4().hex[:8]}"}
    ).json()["id"]
    grupo = api_edificio.cliente.post(
        api_edificio.ruta("/grupos"),
        json={"nombre": f"Grupo {uuid4().hex[:8]}", "metodo": "coeficiente", "unidades": []},
    ).json()["id"]
    return categoria, grupo


def _crear_gasto(api_edificio: ApiEdificio, categoria: str, grupo: str, periodo: str) -> str:
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": "Gasto de prueba",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": periodo,
            "importe": "1000.00",
        },
    )
    return str(respuesta.json()["id"])


def _sesion_directa(api_edificio: ApiEdificio) -> Session:
    def conectar():  # type: ignore[no-untyped-def]
        con = api_edificio.base.conectar_app()
        con.autocommit = False
        return con

    engine = create_engine("postgresql+psycopg://", creator=conectar, poolclass=NullPool)
    sesion = Session(engine)
    sesion.execute(
        text("SELECT set_config('app.administracion_id', :id, true)"),
        {"id": str(api_edificio.admin)},
    )
    return sesion


# --- 7.1 ---


def test_gasto_aprobado_en_su_propio_periodo_conserva_periodo_de_imputacion(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _categoria_y_grupo(api_edificio)
    gasto_id = _crear_gasto(api_edificio, categoria, grupo, "2026-10-01")
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    gasto = api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()
    assert gasto["periodo"] == "2026-10-01"
    assert gasto["periodo_de_imputacion"] == "2026-10-01"


def test_editar_periodo_en_borrador_actualiza_periodo_de_imputacion(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _categoria_y_grupo(api_edificio)
    gasto_id = _crear_gasto(api_edificio, categoria, grupo, "2026-10-01")
    api_edificio.cliente.patch(f"/api/gastos/{gasto_id}", json={"periodo": "2026-11-01"})
    gasto = api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()
    assert gasto["periodo"] == "2026-11-01"
    assert gasto["periodo_de_imputacion"] == "2026-11-01"


def test_aprobar_dos_veces_no_vuelve_a_mover_el_periodo_de_imputacion(
    api_edificio: ApiEdificio,
) -> None:
    categoria, grupo = _categoria_y_grupo(api_edificio)
    gasto_id = _crear_gasto(api_edificio, categoria, grupo, "2026-10-01")
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    gasto = api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()
    assert gasto["periodo_de_imputacion"] == "2026-10-01"


def test_aprobado_tarde_se_imputa_en_el_primer_periodo_no_emitido(
    api_edificio: ApiEdificio,
) -> None:
    """D8: si el período de origen ya está emitido al momento de aprobar, el
    gasto se imputa en el primer período no emitido — sin reabrir el
    emitido. El puerto `es_periodo_emitido` no tiene todavía un adaptador
    real (change 7, `liquidacion`, no existe aún); se dobla acá con una
    función fija, mismo patrón D6 que el lector de planillas."""
    categoria, grupo = _categoria_y_grupo(api_edificio)
    gasto_id = _crear_gasto(api_edificio, categoria, grupo, "2026-10-01")

    def _solo_octubre_esta_emitido(sesion, complejo_id, periodo):  # type: ignore[no-untyped-def]
        return periodo == datetime.date(2026, 10, 1)

    sesion = _sesion_directa(api_edificio)
    try:
        modulo_gastos.aprobar_gasto(
            sesion,
            Identidad(api_edificio.admin, api_edificio.personas["super_admin"]),
            gasto_id=UUID(gasto_id),
            request_id=uuid4(),
            es_periodo_emitido=_solo_octubre_esta_emitido,
        )
        sesion.commit()
    finally:
        sesion.bind.dispose()  # type: ignore[union-attr]

    gasto = api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()
    assert gasto["periodo"] == "2026-10-01", "el período de origen nunca cambia"
    assert gasto["periodo_de_imputacion"] == "2026-11-01", (
        "octubre está emitido: el primer período no emitido es noviembre"
    )


def test_periodo_de_imputacion_nunca_queda_igual_a_un_periodo_emitido(
    api_edificio: ApiEdificio,
) -> None:
    """Dos meses emitidos seguidos: avanza hasta el primero que no lo está."""
    categoria, grupo = _categoria_y_grupo(api_edificio)
    gasto_id = _crear_gasto(api_edificio, categoria, grupo, "2026-10-01")

    emitidos = {datetime.date(2026, 10, 1), datetime.date(2026, 11, 1)}

    def _emitido(sesion, complejo_id, periodo):  # type: ignore[no-untyped-def]
        return periodo in emitidos

    sesion = _sesion_directa(api_edificio)
    try:
        modulo_gastos.aprobar_gasto(
            sesion,
            Identidad(api_edificio.admin, api_edificio.personas["super_admin"]),
            gasto_id=UUID(gasto_id),
            request_id=uuid4(),
            es_periodo_emitido=_emitido,
        )
        sesion.commit()
    finally:
        sesion.bind.dispose()  # type: ignore[union-attr]

    gasto = api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()
    assert gasto["periodo_de_imputacion"] not in {"2026-10-01", "2026-11-01"}
    assert gasto["periodo_de_imputacion"] == "2026-12-01"


# --- Intento 2 (rompedor F2): editar un aprobado tardío sin tocar campos
# bloqueados nunca lo devuelve a su período de origen (D8, D-141). ---


def _aprobado_tarde(api_edificio: ApiEdificio) -> str:
    categoria, grupo = _categoria_y_grupo(api_edificio)
    gasto_id = _crear_gasto(api_edificio, categoria, grupo, "2026-10-01")

    def _octubre_emitido(sesion, complejo_id, periodo):  # type: ignore[no-untyped-def]
        return periodo == datetime.date(2026, 10, 1)

    sesion = _sesion_directa(api_edificio)
    try:
        modulo_gastos.aprobar_gasto(
            sesion,
            Identidad(api_edificio.admin, api_edificio.personas["super_admin"]),
            gasto_id=UUID(gasto_id),
            request_id=uuid4(),
            es_periodo_emitido=_octubre_emitido,
        )
        sesion.commit()
    finally:
        sesion.bind.dispose()  # type: ignore[union-attr]
    assert (
        api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()["periodo_de_imputacion"]
        == "2026-11-01"
    )
    return gasto_id


def test_patch_vacio_de_un_aprobado_tarde_conserva_su_periodo_de_imputacion(
    api_edificio: ApiEdificio,
) -> None:
    gasto_id = _aprobado_tarde(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.patch(f"/api/gastos/{gasto_id}", json={})
    assert respuesta.status_code == 200, respuesta.text
    gasto = api_edificio.cliente.get(f"/api/gastos/{gasto_id}").json()
    assert gasto["periodo"] == "2026-10-01"
    assert gasto["periodo_de_imputacion"] == "2026-11-01", gasto
    filas = api_edificio.filas(
        "SELECT periodo_de_imputacion::text FROM gasto WHERE id=%s", (gasto_id,)
    )
    assert filas == [("2026-11-01",)]


def test_editar_un_campo_de_un_aprobado_tarde_da_422_y_no_lo_mueve(
    api_edificio: ApiEdificio,
) -> None:
    """Borde: con un campo bloqueado el guardia de aprobado responde 422 y
    la imputación fijada al aprobar tampoco se mueve."""
    gasto_id = _aprobado_tarde(api_edificio)
    api_edificio.como("editar")
    respuesta = api_edificio.cliente.patch(
        f"/api/gastos/{gasto_id}", json={"concepto": "Concepto corregido"}
    )
    assert respuesta.status_code == 422, respuesta.text
    filas = api_edificio.filas(
        "SELECT periodo_de_imputacion::text FROM gasto WHERE id=%s", (gasto_id,)
    )
    assert filas == [("2026-11-01",)]
