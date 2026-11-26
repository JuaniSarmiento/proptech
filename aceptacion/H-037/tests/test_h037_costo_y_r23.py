"""H-037 · C04 y C05: el costo de cada llamada y el monto atípico de R23."""

from __future__ import annotations

from decimal import Decimal

import psycopg
import pytest

from ._h037 import (
    ErrorDeIaFalso,
    LectorDeIaFalso,
    Mundo,
    OTRO_CUIT,
    UsoFalso,
    aprobado_del_6,
    categoria_y_grupo,
    correr_la_tarea,
    datos_intocables,
    datos_qr,
    fijar_tenant,
    gasto,
    leida,
    leida_sin_qr,
    lectura,
    llamadas,
    propuesta_buena,
    proveedor_con_aprobados,
    subir_qr,
)

# --- C04: cada llamada deja su costo ------------------------------------------------------------------------


def test_c04_una_llamada_buena_registra_modelo_tokens_y_costo(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    uso = UsoFalso(propuesta_buena(categoria, grupo), modelo="proveedor/otro-modelo", tokens_entrada=2345,
                   tokens_salida=67, costo="0.004321")
    id_ = leida(mundo, datos_qr(), LectorDeIaFalso(uso=uso))
    [fila] = llamadas(mundo, id_)
    assert fila["resultado"] == "ok"
    assert fila["modelo"] == "proveedor/otro-modelo"
    assert (fila["tokens_entrada"], fila["tokens_salida"]) == (2345, 67)
    assert Decimal(str(fila["costo_usd"])) == Decimal("0.004321"), fila["costo_usd"]
    assert fila["complejo_id"] == str(mundo.edificio)


def test_c04_una_llamada_fallida_tambien_se_registra(mundo: Mundo) -> None:
    gastado = ErrorDeIaFalso("cortó a mitad", tokens_entrada=900, tokens_salida=0, costo="0.000900")
    con_uso = leida(mundo, datos_qr(), LectorDeIaFalso(falla=gastado))
    sin_uso = leida(mundo, datos_qr(nroCmp=3002), LectorDeIaFalso(falla=RuntimeError("no respondió")))
    [fila_con] = llamadas(mundo, con_uso)
    [fila_sin] = llamadas(mundo, sin_uso)
    assert fila_con["resultado"] == "fallida" and fila_con["tokens_entrada"] == 900
    assert Decimal(str(fila_con["costo_usd"])) == Decimal("0.000900")
    assert fila_sin["resultado"] == "fallida", "una falla sin datos de uso igual deja su fila"
    assert (fila_sin["tokens_entrada"], fila_sin["tokens_salida"]) == (0, 0)
    assert Decimal(str(fila_sin["costo_usd"])) == 0
    assert fila_sin["modelo"] == LectorDeIaFalso.modelo, "el modelo sale del lector aunque la llamada falle"


def test_c04_una_respuesta_fuera_de_contrato_cuesta_y_queda_registrada_como_fallida(mundo: Mundo) -> None:
    id_ = leida(mundo, datos_qr(), LectorDeIaFalso(uso=UsoFalso("no es un objeto", tokens_entrada=700,
                                                                   tokens_salida=30, costo="0.000500")))
    [fila] = llamadas(mundo, id_)
    assert fila["resultado"] == "fallida" and fila["tokens_entrada"] == 700
    assert Decimal(str(fila["costo_usd"])) == Decimal("0.000500")


def test_c04_la_tabla_es_de_solo_agregar_y_aislada_por_administracion(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    leida(mundo, datos_qr(), LectorDeIaFalso(propuesta_buena(categoria, grupo)))
    assert len(llamadas(mundo)) == 1
    for sentencia in ("UPDATE llamada_de_ia SET tokens_entrada = 0", "DELETE FROM llamada_de_ia"):
        with mundo.base.conectar_app() as conexion, pytest.raises(psycopg.Error):  # noqa: PT012
            with conexion.transaction():
                fijar_tenant(conexion, mundo.admin)
                conexion.execute(sentencia)
        assert len(llamadas(mundo)) == 1, f"{sentencia} no puede dejar rastro"
    with mundo.base.conectar_app() as conexion, conexion.transaction():
        fijar_tenant(conexion, mundo.admin_b)
        assert conexion.execute("SELECT count(*) FROM llamada_de_ia").fetchone()[0] == 0, "RLS por administración"


def test_c04_sin_ia_configurada_no_hay_llamada_y_por_lo_tanto_ninguna_fila(mundo: Mundo) -> None:
    """Sin lector no hay llamada: ninguna fila, ni de costo cero."""
    subido = subir_qr(mundo, datos_qr())
    correr_la_tarea(mundo, str(subido["id"]), None)
    assert llamadas(mundo) == []


# --- C05: R23, el importe atípico -----------------------------------------------------------------------------


def _con_importe(m: Mundo, importe: str, **qr: object) -> str:
    """Sube una factura del proveedor con ese importe y corre la lectura con una IA que propone todo lo demás."""
    categoria, grupo = categoria_y_grupo(m)
    return leida(m, datos_qr(importe=float(importe), nroCmp=m.numero_nuevo(), **qr),
                 LectorDeIaFalso(propuesta_buena(categoria, grupo, importe=importe)))


@pytest.mark.parametrize("importe, atipico", [("2000.01", True), ("2000.00", False), ("1000.00", False),
                                              ("500.01", False), ("500.00", False), ("499.99", True),
                                              ("38900.00", True)])
def test_c05_mas_del_doble_o_menos_de_la_mitad_del_promedio_deja_el_gasto_en_revision(
        mundo: Mundo, importe: str, atipico: bool) -> None:
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "1000.00"])
    id_ = _con_importe(mundo, importe)
    g = gasto(mundo, id_)
    estado = lectura(mundo, id_)
    if atipico:
        assert g["estado"] == "en_revision", f"{importe} contra un promedio de 1000.00: {g['estado']}"
        assert estado["estado"] == "en_revision" and estado["motivo"] == "importe_atipico"
        assert estado["detalle"]["promedio"] == "1000.00"
        assert estado["detalle"]["muestras"] == 3
        assert estado["detalle"]["importe"] == importe
        assert g["concepto"] == "Mantenimiento de ascensores, octubre", "la propuesta se aplica igual, a revisar"
    else:
        assert g["estado"] == "borrador" and estado["motivo"] is None, f"{importe}: {g['estado']} {estado}"


def test_c05_el_promedio_es_la_media_de_los_aprobados_de_la_ventana(mundo: Mundo) -> None:
    """1000, 1000 y 4000: media 2000.00 (la mediana, 1000, marcaría 3000.00; la media no)."""
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "4000.00"])
    no = _con_importe(mundo, "3000.00")
    assert gasto(mundo, no)["estado"] == "borrador"
    si = _con_importe(mundo, "4000.01")
    assert gasto(mundo, si)["estado"] == "en_revision"
    assert lectura(mundo, si)["detalle"]["promedio"] == "2000.00"
    justo = _con_importe(mundo, "4000.00")
    assert gasto(mundo, justo)["estado"] == "borrador", "justo el doble no es más del doble"


def test_c05_con_un_solo_aprobado_en_la_ventana_ya_se_compara(mundo: Mundo) -> None:
    proveedor_con_aprobados(mundo, ["1000.00"])
    marcado = _con_importe(mundo, "2000.01")
    assert gasto(mundo, marcado)["estado"] == "en_revision"
    detalle = lectura(mundo, marcado)["detalle"]
    assert (detalle["promedio"], detalle["muestras"]) == ("1000.00", 1)
    normal = _con_importe(mundo, "1900.00")
    assert gasto(mundo, normal)["estado"] == "borrador"


def test_c05_sin_historial_en_la_ventana_no_se_marca(mundo: Mundo) -> None:
    id_ = _con_importe(mundo, "50000.00")
    assert gasto(mundo, id_)["estado"] == "borrador" and lectura(mundo, id_)["motivo"] is None


@pytest.mark.parametrize("periodo, cuenta", [("2026-04-01", True), ("2026-09-01", True), ("2026-03-01", False),
                                             ("2025-10-01", False), ("2026-10-01", False), ("2026-11-01", False)])
def test_c05_la_ventana_son_los_6_periodos_anteriores_al_del_gasto_leido(
        mundo: Mundo, periodo: str, cuenta: bool) -> None:
    """El gasto leído es de 2026-10: cuentan 2026-04 a 2026-09; 7 períodos atrás, el mismo mes o uno posterior, no."""
    proveedor_con_aprobados(mundo, ["1000.00"], periodo=periodo)
    id_ = _con_importe(mundo, "50000.00")
    esperado = "en_revision" if cuenta else "borrador"
    assert gasto(mundo, id_)["estado"] == esperado, f"un aprobado de {periodo}: {gasto(mundo, id_)['estado']}"


def test_c05_el_promedio_sólo_usa_los_aprobados_de_la_ventana(mundo: Mundo) -> None:
    proveedor = proveedor_con_aprobados(mundo, ["1000.00", "1000.00"], periodo="2026-07-01")
    aprobado_del_6(mundo, proveedor, "90000.00", periodo="2026-03-01")
    id_ = _con_importe(mundo, "2000.01")
    assert gasto(mundo, id_)["estado"] == "en_revision"
    detalle = lectura(mundo, id_)["detalle"]
    assert (detalle["promedio"], detalle["muestras"]) == ("1000.00", 2), "el de hace 7 períodos no cuenta"


def test_c05_sólo_cuentan_los_aprobados_de_ese_proveedor_en_ese_edificio(mundo: Mundo) -> None:
    proveedor = proveedor_con_aprobados(mundo, [])
    # No cuentan: un borrador del mismo proveedor, otro proveedor del edificio y el mismo CUIT en otro edificio.
    aprobado_del_6(mundo, proveedor, "1000.00", aprobar=False)
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "1000.00"], cuit=OTRO_CUIT)
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "1000.00"], complejo=mundo.otro)
    antes = _con_importe(mundo, "50000.00")
    assert gasto(mundo, antes)["estado"] == "borrador", "ninguno de esos cuenta: no hay historial propio"
    aprobado_del_6(mundo, proveedor, "1000.00")
    despues = _con_importe(mundo, "50000.00")
    assert gasto(mundo, despues)["estado"] == "en_revision"
    assert lectura(mundo, despues)["detalle"]["muestras"] == 1


def test_c05_si_la_ia_no_da_periodo_no_hay_ventana_y_no_se_marca(mundo: Mundo) -> None:
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "1000.00"])
    categoria, grupo = categoria_y_grupo(mundo)
    id_ = leida(mundo, datos_qr(importe=50000.0, nroCmp=mundo.numero_nuevo()),
                LectorDeIaFalso(propuesta_buena(categoria, grupo, periodo=None, importe="50000.00")))
    assert gasto(mundo, id_)["estado"] == "borrador" and gasto(mundo, id_)["periodo"] is None


def test_c05_una_factura_sin_qr_no_tiene_proveedor_y_no_se_marca(mundo: Mundo) -> None:
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "1000.00"])
    categoria, grupo = categoria_y_grupo(mundo)
    id_ = leida_sin_qr(mundo, LectorDeIaFalso(propuesta_buena(categoria, grupo, importe="90000.00")))
    assert gasto(mundo, id_)["estado"] == "borrador"


def test_c05_la_persona_puede_confirmar_un_gasto_en_revision(mundo: Mundo) -> None:
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "1000.00"])
    id_ = _con_importe(mundo, "2500.00")
    assert gasto(mundo, id_)["estado"] == "en_revision"
    r = mundo.cliente.post(f"/api/gastos/{id_}/aprobar")
    assert r.status_code == 200, f"la confirmación es de la persona: {r.status_code} {r.text[:200]}"
    assert gasto(mundo, id_)["estado"] == "aprobado"


def test_c05_la_revision_no_toca_lo_que_trajo_el_qr(mundo: Mundo) -> None:
    proveedor_con_aprobados(mundo, ["1000.00", "1000.00", "1000.00"])
    categoria, grupo = categoria_y_grupo(mundo)
    subido = subir_qr(mundo, datos_qr(importe=2500.0, nroCmp=3100))
    correr_la_tarea(mundo, str(subido["id"]), LectorDeIaFalso(propuesta_buena(categoria, grupo, importe="1.00")))
    g = gasto(mundo, str(subido["id"]))
    assert g["estado"] == "en_revision"
    assert datos_intocables(g) == datos_intocables(subido) | {"periodo_de_imputacion": None}
    assert g["importe"] == "2500.00"
