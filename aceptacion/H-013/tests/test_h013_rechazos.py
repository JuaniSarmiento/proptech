"""H-013 · lo que tiene que fallar al emitir (N01 a N09) y el ciclo de la migración (C12)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from .._edificios import BaseDeEdificio
from ._h013 import (
    DIC,
    NOV,
    Mundo,
    cargar_base,
    configurar,
    conteo_de_todo,
    cuerpo_de_emision,
    emitida,
    emitir,
    emitir_lo_revisado,
    en_paralelo,
    gasto,
    obligaciones_del_libro,
    preliquidacion,
)


def _sin_escribir(m: Mundo, pedido: Any) -> Any:
    antes = conteo_de_todo(m)
    r = pedido()
    despues = conteo_de_todo(m)
    cambiadas = sorted(t for t in antes if antes[t] != despues.get(t))
    assert not cambiadas, f"un rechazo escribió en: {cambiadas} ({r.status_code}: {r.text[:200]})"
    return r


def _conflicto(r: Any, campo: str, motivo: str) -> None:
    assert r.status_code == 409, f"se esperaba 409 {motivo}, llegó {r.status_code}: {r.text[:300]}"
    cuerpo = r.json()
    assert (cuerpo.get("campo"), cuerpo.get("motivo")) == (campo, motivo), cuerpo


def test_n01_huella_vieja(mundo: Mundo) -> None:
    """Escenario: La preliquidación cambió"""
    ids = cargar_base(mundo)
    huella = preliquidacion(mundo)["huella"]
    mundo.ejecutar("UPDATE gasto SET estado = 'aprobado' WHERE id = %s", (ids["borrador"],))
    r = _sin_escribir(mundo, lambda: emitir(mundo, cuerpo_de_emision(huella)))
    _conflicto(r, "huella", "preliquidacion_cambio")


@pytest.mark.parametrize("aceptadas", [[], ["saldos_iniciales_sin_validar"]])
def test_n02_un_duro_no_se_acepta(mundo: Mundo, aceptadas: list[str]) -> None:
    """Escenario: Control duro activo"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    mundo.ejecutar("UPDATE complejo SET estado_migracion = 'pendiente' WHERE id = %s", (mundo.edificio,))
    huella = preliquidacion(mundo)["huella"]
    r = _sin_escribir(mundo, lambda: emitir(mundo, cuerpo_de_emision(huella, aceptadas=aceptadas)))
    assert r.status_code == 422, f"{aceptadas}: {r.status_code} {r.text[:300]}"
    cuerpo = r.json()
    assert cuerpo.get("detail") == "control_duro" and cuerpo.get("controles") == ["saldos_iniciales_sin_validar"], cuerpo


@pytest.mark.parametrize(
    ("revision", "aceptadas"),
    [
        (True, []),
        (True, ["gastos_en_revision", "gastos_sin_ia"]),
        (False, ["gastos_en_revision"]),
    ],
    ids=["de_menos", "una_advertencia_de_mas", "uno_que_no_esta_activo"],
)
def test_n03_alertas_de_menos_o_de_mas(mundo: Mundo, revision: bool, aceptadas: list[str]) -> None:
    """Escenario: Alertas aceptadas distintas"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    gasto(mundo, "777.00", estado="sin_ia")
    if revision:
        gasto(mundo, "555.00", estado="en_revision")
    huella = preliquidacion(mundo)["huella"]
    r = _sin_escribir(mundo, lambda: emitir(mundo, cuerpo_de_emision(huella, aceptadas=aceptadas)))
    _conflicto(r, "alertas_aceptadas", "alertas_distintas")


def test_n04_el_administrador_del_edificio_no_acepta_bloqueantes(mundo: Mundo) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    gasto(mundo, "555.00", estado="en_revision")
    huella = preliquidacion(mundo)["huella"]
    mundo.como("admin_del_edificio")
    r = _sin_escribir(mundo, lambda: emitir(mundo, cuerpo_de_emision(huella, aceptadas=["gastos_en_revision"])))
    assert r.status_code == 403, f"{r.status_code} {r.text[:300]}"
    assert r.json()["detail"].get("permiso_faltante") == "aceptar_alertas_bloqueantes"


def test_n05_el_mismo_periodo_otra_vez(mundo: Mundo) -> None:
    """Escenario: Emitir dos veces el mismo período"""
    cargar_base(mundo)
    huella = preliquidacion(mundo)["huella"]
    emitida(emitir(mundo, cuerpo_de_emision(huella)))
    r = _sin_escribir(mundo, lambda: emitir(mundo, cuerpo_de_emision(huella)))
    _conflicto(r, "periodo", "periodo_emitido")


def test_n06_dos_emisiones_en_paralelo(mundo: Mundo) -> None:
    """Escenario: Dos emisiones a la vez"""
    cargar_base(mundo)
    huella = preliquidacion(mundo)["huella"]
    a, b = cuerpo_de_emision(huella), cuerpo_de_emision(huella)
    resultados = en_paralelo(lambda: emitir(mundo, a), lambda: emitir(mundo, b))
    codigos = sorted(getattr(r, "status_code", repr(r)) for r in resultados)
    assert codigos == [201, 409], f"una emite y la otra choca: {codigos}"
    assert len(obligaciones_del_libro(mundo)) == 4, "una sola obligación por unidad"


def test_n07_aprobar_un_gasto_mientras_se_emite(mundo: Mundo) -> None:
    """Escenario: Gasto aprobado durante la emisión"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    tarde = gasto(mundo, "800.00", estado="borrador")
    huella = preliquidacion(mundo)["huella"]
    resultados = en_paralelo(
        lambda: mundo.cliente.post(f"/api/gastos/{tarde}/aprobar"),
        lambda: emitir(mundo, cuerpo_de_emision(huella)),
    )
    aprobar, emision = resultados
    assert getattr(aprobar, "status_code", None) == 200, f"aprobar: {aprobar!r}"
    imputacion = mundo.uno("SELECT periodo_de_imputacion FROM gasto WHERE id = %s", (tarde,))
    emitio = getattr(emision, "status_code", None) == 201
    if emitio:
        assert imputacion == DIC, "noviembre se emitió sin el gasto y el gasto quedó en noviembre"
    else:
        _conflicto(emision, "huella", "preliquidacion_cambio")
        assert imputacion == NOV


@pytest.mark.parametrize(
    "vencimiento",
    [{"fecha": "2026-11-12"}, {"fecha": "2026-11-12", "motivo": "   "}, {"fecha": "2026-10-31", "motivo": "Antes"}],
    ids=["sin_motivo", "motivo_en_blanco", "antes_del_periodo"],
)
def test_n08_vencimiento_corrido_invalido(mundo: Mundo, vencimiento: dict[str, str]) -> None:
    cargar_base(mundo)
    huella = preliquidacion(mundo)["huella"]
    r = _sin_escribir(mundo, lambda: emitir(mundo, cuerpo_de_emision(huella, vencimiento=vencimiento)))
    assert r.status_code == 422, f"{vencimiento}: {r.status_code} {r.text[:300]}"


def test_n09_una_unidad_sin_obligacion_no_recibe_una_en_cero(mundo: Mundo) -> None:
    """Escenario: Unidad sin nada que pagar"""
    configurar(mundo)
    gasto(mundo, "40000.00", categoria="Ascensor", grupo=mundo.ascensor)
    emitir_lo_revisado(mundo)
    assert set(obligaciones_del_libro(mundo)) == {"2A", "2B"}


# --- C12: el ciclo de la 0041 (L-082: su migración, no "la última") ---------------------------------

_VERSIONES = Path(__file__).resolve().parents[3] / "migraciones" / "versions"


def _dump(base: BaseDeEdificio, destino: Path) -> str:
    comando = ["pg_dump", "--schema-only", "-U", base.contenedor.username, "-d", base.nombre]
    codigo, salida = base.contenedor.exec(comando)
    assert codigo == 0
    texto = salida.decode()
    texto = re.sub(r"^\\(?:un)?restrict .*\n", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^-- Dumped (?:from|by) .*\n", "", texto, flags=re.MULTILINE)
    destino.write_text(texto)
    return texto


def _version(base: BaseDeEdificio) -> str:
    with base.conectar_app() as c:
        fila = c.execute("SELECT version_num FROM alembic_version").fetchone()
        assert fila is not None
        return str(fila[0])


def test_c12_la_0041_sube_y_baja_en_el_ciclo_de_devolucion(
    base_para_migraciones: BaseDeEdificio, tmp_path: Path
) -> None:
    assert list(_VERSIONES.glob("0041_*.py")), "falta la migración 0041 (tablas de la liquidación)"
    base = base_para_migraciones
    base.roles("antes")
    base.migrar("upgrade", "0040")
    base.roles("despues")
    antes = _dump(base, tmp_path / "0040-antes.sql")
    base.roles("antes")
    base.migrar("upgrade", "0041")
    base.roles("despues")
    assert _version(base) == "0041", "la 0041 no quedó aplicada"
    base.devolver_tablas_protegidas()
    base.migrar("downgrade", "0040")
    base.roles("despues")
    assert _dump(base, tmp_path / "0040-despues.sql") == antes, "bajar la 0041 no deja el esquema de la 0040"
    base.roles("antes")
    base.migrar("upgrade", "0041")
    base.roles("despues")
    assert _version(base) == "0041"
