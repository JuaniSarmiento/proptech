"""H-012 · los controles antes de emitir en la preliquidación (C01 a C07, N01 a N04)."""

from __future__ import annotations

import re
from uuid import UUID, uuid4

import psycopg
import pytest

from ._h012 import (
    NOV,
    OCT,
    Mundo,
    cargar_base,
    codigos,
    conteo_de_todo,
    configurar,
    control,
    controles,
    gasto,
    nota_de_credito,
    poner_coeficiente,
    poner_estado,
    preliquidacion,
)


def _configurar_doble(m: Mundo) -> None:
    m.ejecutar(
        "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
        "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
        "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento, dia_segundo_vencimiento, "
        "recargo_segundo_vencimiento) VALUES (%s, %s, %s, '2026-01-01', '3.00', '500.00', 0, "
        "'proporcional_por_dia', '5.00', 10, 'doble', 20, '5.00')",
        (m.admin, m.edificio, m.personas["super_admin"]),
    )


def _grupo_propios(m: Mundo, coeficientes: dict[str, str]) -> UUID:
    fila = m.ejecutar(
        "INSERT INTO grupo_de_reparto (administracion_id, complejo_id, clave, nombre, metodo, "
        "modo_de_coeficientes) VALUES (%s, %s, 'cocheras', 'Cocheras', 'coeficiente', 'propios') "
        "RETURNING id",
        (m.admin, m.edificio),
    )
    grupo = UUID(str(fila[0]))
    for u, c in coeficientes.items():
        m.ejecutar(
            "INSERT INTO grupo_unidad (administracion_id, complejo_id, grupo_id, unidad_id, "
            "modo_de_coeficientes, coeficiente) VALUES (%s, %s, %s, %s, 'propios', %s)",
            (m.admin, m.edificio, grupo, m.unidades[u], c),
        )
    return grupo


def _obligatoria(m: Mundo, categoria: str) -> None:
    m.ejecutar(
        "UPDATE categoria_de_gasto SET obligatorio_mensual = true WHERE id = %s",
        (m.categorias[categoria],),
    )


# --- C01 a C06 ------------------------------------------------------------------------------------


def test_c01_saldos_iniciales_sin_validar_es_duro(mundo: Mundo) -> None:
    """Escenario: Saldos iniciales sin validar"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    poner_estado(mundo, "pendiente")
    c = control(preliquidacion(mundo), "saldos_iniciales_sin_validar")
    assert c["nivel"] == "duro", f"tiene que ser duro: {c}"


@pytest.mark.parametrize("estado", ["confirmada", "sin_saldos_previos"])
def test_c01_con_la_migracion_cerrada_no_aparece(mundo: Mundo, estado: str) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    poner_estado(mundo, "pendiente")
    assert "saldos_iniciales_sin_validar" in codigos(preliquidacion(mundo)), "control: con pendiente sí"
    poner_estado(mundo, estado)
    assert "saldos_iniciales_sin_validar" not in codigos(preliquidacion(mundo))


def test_c02_generales_fuera_de_tolerancia(mundo: Mundo) -> None:
    """Escenario: Coeficientes fuera de tolerancia"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    poner_coeficiente(mundo, "2B", "0.149800")
    c = control(preliquidacion(mundo), "coeficientes_fuera_de_tolerancia")
    assert c["nivel"] == "duro"
    grupos = c["detalle"].get("grupos")
    assert isinstance(grupos, list) and len(grupos) == 1, f"un solo grupo fuera: {c['detalle']}"
    g = grupos[0]
    assert g.get("grupo_id") == str(mundo.generales) and g.get("nombre") == "Generales", g
    assert (g.get("suma"), g.get("diferencia")) == ("0.999800", "-0.000200"), g


def test_c02_grupo_con_coeficientes_propios_fuera(mundo: Mundo) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    cocheras = _grupo_propios(mundo, {"1A": "0.400000", "1B": "0.400000"})
    c = control(preliquidacion(mundo), "coeficientes_fuera_de_tolerancia")
    grupos = {g["grupo_id"]: g for g in c["detalle"]["grupos"]}
    assert set(grupos) == {str(cocheras)}, f"sólo Cocheras está fuera: {c['detalle']}"
    assert grupos[str(cocheras)]["suma"] == "0.800000"


def test_c03_bloque_negativo_es_duro_y_no_rompe(mundo: Mundo) -> None:
    """Escenario: Bloque negativo"""
    configurar(mundo)
    octubre = gasto(mundo, "80000.00", periodo=OCT)
    gasto(mundo, "50000.00")
    nota_de_credito(mundo, octubre, "60000.00", periodo=NOV)
    cuerpo = preliquidacion(mundo)
    c = control(cuerpo, "bloque_negativo")
    assert c["nivel"] == "duro"
    bloques = c["detalle"].get("bloques")
    assert bloques == [
        {"grupo_id": str(mundo.generales), "nombre": "Generales", "bloque": "ordinario",
         "importe": "-10000.00"}
    ], f"el bloque negativo con su grupo, bloque e importe: {bloques}"


def test_c04_doble_vencimiento_sin_regla_es_duro(mundo: Mundo) -> None:
    """Escenario: Doble vencimiento"""
    _configurar_doble(mundo)
    gasto(mundo, "1000.00")
    c = control(preliquidacion(mundo), "doble_vencimiento_sin_regla")
    assert c["nivel"] == "duro"


def test_c05_gastos_en_revision_es_bloqueante(mundo: Mundo) -> None:
    """Escenario: Gastos en revisión"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    en_revision = gasto(mundo, "555.00", estado="en_revision")
    cuerpo = preliquidacion(mundo)
    c = control(cuerpo, "gastos_en_revision")
    assert c["nivel"] == "bloqueante"
    assert c["detalle"].get("cantidad") == 1 and c["detalle"].get("gastos") == [str(en_revision)], c
    assert cuerpo["totales"]["gastos"] == "190000.00", "un gasto en revisión no entra en el cálculo"


def test_c05_gastos_sin_ia_es_advertencia_con_la_cantidad(mundo: Mundo) -> None:
    """Escenario: Facturas sin cargar"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    gasto(mundo, "777.00", estado="sin_ia")
    gasto(mundo, "778.00", estado="sin_ia")
    cuerpo = preliquidacion(mundo)
    c = control(cuerpo, "gastos_sin_ia")
    assert c["nivel"] == "advertencia"
    assert c["detalle"].get("cantidad") == 2
    assert re.search(r"hay 2 facturas sin cargar", c["mensaje"], flags=re.I), c["mensaje"]
    assert cuerpo["totales"]["gastos"] == "190000.00", "un gasto sin IA no entra en el cálculo"


def test_c06_falta_el_gasto_mensual_obligatorio(mundo: Mundo) -> None:
    """Escenario: Gasto mensual obligatorio faltante"""
    cargar_base(mundo, con_lo_que_no_entra=False)
    _obligatoria(mundo, "Seguridad")
    c = control(preliquidacion(mundo), "gasto_mensual_obligatorio_faltante")
    assert c["nivel"] == "advertencia"
    assert c["detalle"].get("categorias") == [
        {"categoria_id": str(mundo.categorias["Seguridad"]), "nombre": "Seguridad"}
    ], c["detalle"]


def test_c06_desaparece_al_aprobar_un_gasto_de_la_categoria(mundo: Mundo) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    _obligatoria(mundo, "Seguridad")
    assert "gasto_mensual_obligatorio_faltante" in codigos(preliquidacion(mundo)), "control: falta"
    gasto(mundo, "3000.00", categoria="Seguridad")
    assert "gasto_mensual_obligatorio_faltante" not in codigos(preliquidacion(mundo))


# --- C07 ------------------------------------------------------------------------------------------


def _todos_los_controles(m: Mundo) -> None:
    _configurar_doble(m)
    octubre = gasto(m, "80000.00", periodo=OCT)
    gasto(m, "50000.00")
    nota_de_credito(m, octubre, "60000.00", periodo=NOV)
    poner_estado(m, "pendiente")
    poner_coeficiente(m, "2B", "0.149800")
    gasto(m, "555.00", estado="en_revision")
    gasto(m, "777.00", estado="sin_ia")
    _obligatoria(m, "Seguridad")


def test_c07_orden_fijo_de_los_controles(mundo: Mundo) -> None:
    _todos_los_controles(mundo)
    assert codigos(preliquidacion(mundo)) == [
        "saldos_iniciales_sin_validar",
        "coeficientes_fuera_de_tolerancia",
        "bloque_negativo",
        "doble_vencimiento_sin_regla",
        "gastos_en_revision",
        "gastos_sin_ia",
        "gasto_mensual_obligatorio_faltante",
    ]


def test_c07_la_huella_cambia_con_los_controles(mundo: Mundo) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    antes = preliquidacion(mundo)
    poner_estado(mundo, "pendiente")
    despues = preliquidacion(mundo)
    assert despues["totales"] == antes["totales"], "cambiar el estado de migración no mueve importes"
    assert despues["huella"] != antes["huella"], "cambió el conjunto de controles y no la huella"


# --- N01 a N04 ------------------------------------------------------------------------------------


def test_n01_0_9999_no_dispara_un_duro(mundo: Mundo) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    poner_coeficiente(mundo, "2B", "0.149800")
    assert "coeficientes_fuera_de_tolerancia" in codigos(preliquidacion(mundo)), "control: 0,9998 sí"
    poner_coeficiente(mundo, "2B", "0.149900")
    cuerpo = preliquidacion(mundo)
    assert not [c for c in controles(cuerpo) if c["nivel"] == "duro"], (
        f"0,9999 está dentro de la tolerancia: {codigos(cuerpo)}"
    )


def test_n02_lo_de_otro_edificio_no_dispara_nada(mundo: Mundo) -> None:
    cargar_base(mundo, con_lo_que_no_entra=False)
    gasto(mundo, "555.00", estado="en_revision", complejo=mundo.otro)
    gasto(mundo, "777.00", estado="sin_ia", complejo=mundo.otro)
    propio = gasto(mundo, "556.00", estado="en_revision")
    cuerpo = preliquidacion(mundo)
    assert codigos(cuerpo) == ["gastos_en_revision"], f"un gasto de otro edificio disparó algo: {codigos(cuerpo)}"
    assert control(cuerpo, "gastos_en_revision")["detalle"].get("gastos") == [str(propio)]


def test_n03_mostrar_los_controles_no_escribe(mundo: Mundo) -> None:
    _todos_los_controles(mundo)
    antes = conteo_de_todo(mundo)
    assert len(controles(preliquidacion(mundo))) == 7
    despues = conteo_de_todo(mundo)
    cambiadas = sorted(t for t in antes if antes[t] != despues.get(t))
    assert not cambiadas and set(despues) == set(antes), f"los controles escribieron en: {cambiadas}"


def test_n04_no_hay_controles_fuera_de_d157(mundo: Mundo) -> None:
    _todos_los_controles(mundo)
    presentes = set(codigos(preliquidacion(mundo)))
    assert len(presentes) == 7, f"control: los siete controles del 7 activos: {presentes}"
    assert not presentes & {"factura_duplicada", "ingresos_mayores_que_los_gastos"}, presentes


def test_n04_la_factura_duplicada_la_rechaza_la_base(mundo: Mundo) -> None:
    configurar(mundo)
    numero = uuid4().hex[:8]
    consulta = (
        "INSERT INTO gasto (administracion_id, complejo_id, categoria_id, grupo_id, concepto, periodo, "
        "periodo_de_imputacion, importe, estado, cuit_emisor, punto_de_venta, tipo_de_comprobante, "
        "numero_de_comprobante) VALUES (%s, %s, %s, %s, 'Factura', %s, %s, '100.00', 'aprobado', "
        "'20111111112', '0001', 'A', %s)"
    )
    parametros = (mundo.admin, mundo.edificio, mundo.categorias["Limpieza"], mundo.generales, NOV, NOV,
                  numero)
    mundo.ejecutar(consulta, parametros)
    with pytest.raises(psycopg.errors.UniqueViolation):
        mundo.ejecutar(consulta, parametros)
