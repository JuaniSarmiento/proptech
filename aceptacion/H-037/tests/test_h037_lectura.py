"""H-037 · C01 a C03: la IA completa el borrador, sólo dentro del vocabulario, y si falla queda `sin_ia`.

Cada test corre la tarea `leer_factura_con_ia` con un lector falso (el puerto de CONTRATO.md); hoy la tarea no existe y
cada uno cae en un `assert` con ese mensaje.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from ._h037 import (
    LectorDeIaFalso,
    Mundo,
    categoria_y_grupo,
    correr_la_tarea,
    creada,
    datos_intocables,
    datos_qr,
    desactivar,
    encolado,
    fijar_tenant,
    gasto,
    leida,
    leida_sin_qr,
    lectura,
    png_con_qr,
    propuesta_buena,
    subir_qr,
    texto_del_qr,
)

# --- C01: lo que completa la IA ------------------------------------------------------------------------------


def test_c01_subir_la_factura_encola_la_lectura_despues_del_commit(mundo: Mundo) -> None:
    subido = subir_qr(mundo, datos_qr())
    pedidos = encolado(mundo, str(subido["id"]))
    assert len(pedidos) == 1, f"el POST encola `leer_factura_con_ia` una vez: {mundo.cola.llamadas}"
    pedido = pedidos[0]
    assert pedido["administracion_id"] == str(mundo.admin), "la tarea recibe el tenant como texto"
    assert isinstance(pedido.get("clave"), str) and pedido["clave"], "la clave de idempotencia es parte del pedido"
    assert isinstance(pedido.get("request_id"), str) and pedido["request_id"]
    # El gasto ya existe, confirmado, cuando la tarea lo pida: el 201 no espera a la IA.
    assert gasto(mundo, str(subido["id"]))["estado"] == "borrador"


def test_c01_una_factura_sin_qr_tambien_encola_la_lectura_y_cada_factura_su_clave(mundo: Mundo) -> None:
    uno = creada(mundo, png_con_qr(texto_del_qr("basura que no es una factura")))
    otro = subir_qr(mundo, datos_qr(nroCmp=3001))
    [pedido_uno] = encolado(mundo, str(uno["id"])) or [None]
    [pedido_otro] = encolado(mundo, str(otro["id"])) or [None]
    assert pedido_uno is not None and pedido_otro is not None, f"los dos se encolan: {mundo.cola.llamadas}"
    assert pedido_uno["clave"] != pedido_otro["clave"]


def test_c01_la_ia_completa_concepto_periodo_categoria_y_grupo(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    subido = subir_qr(mundo, datos_qr())
    lector = LectorDeIaFalso(propuesta_buena(categoria, grupo))
    assert correr_la_tarea(mundo, str(subido["id"]), lector) is True
    g = gasto(mundo, str(subido["id"]))
    assert g["estado"] == "borrador", f"la IA nunca aprueba: {g['estado']}"
    assert g["concepto"] == "Mantenimiento de ascensores, octubre"
    assert g["periodo"] == "2026-10-01", f"AAAA-MM pasa al primer día del mes: {g['periodo']!r}"
    assert g["categoria_id"] == categoria and g["grupo_id"] == grupo
    assert g["periodo_de_imputacion"] is None, "se fija una sola vez, al aprobar (D8)"
    assert datos_intocables(g) == datos_intocables(subido) | {"periodo_de_imputacion": None}
    estado = lectura(mundo, str(subido["id"]))
    assert estado["estado"] == "borrador" and estado["motivo"] is None
    assert estado["datos_de"] == {"importe": "qr", "concepto": "ia", "periodo": "ia", "categoria_id": "ia",
                                  "grupo_id": "ia"}
    assert len(lector.llamadas) == 1


def test_c01_antes_de_la_lectura_datos_de_dice_de_donde_sale_cada_campo(mundo: Mundo) -> None:
    subido = subir_qr(mundo, datos_qr())
    estado = lectura(mundo, str(subido["id"]))
    assert estado["datos_de"] == {"importe": "qr", "concepto": None, "periodo": None, "categoria_id": None,
                                  "grupo_id": None}
    assert estado["estado"] == "borrador" and estado["motivo"] is None and estado["detalle"] is None


def test_c01_el_importe_de_la_ia_sirve_sólo_si_el_qr_no_lo_trajo(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    con_qr = leida(mundo, datos_qr(), LectorDeIaFalso(propuesta_buena(categoria, grupo, importe="9999.99")))
    g = gasto(mundo, con_qr)
    assert g["importe"] == "1500.50", f"el QR manda sobre la IA: {g['importe']!r}"
    assert lectura(mundo, con_qr)["datos_de"]["importe"] == "qr"
    sin_qr = leida_sin_qr(mundo, LectorDeIaFalso(propuesta_buena(categoria, grupo, importe="2500.00")))
    s = gasto(mundo, sin_qr)
    assert s["importe"] == "2500.00" and s["origen"] == "sin_qr"
    assert lectura(mundo, sin_qr)["datos_de"]["importe"] == "ia"
    assert s["proveedor_id"] is None and s["cuit_emisor"] is None, "la IA no inventa el proveedor ni la factura"


def test_c01_el_lector_recibe_el_archivo_tal_cual_y_nada_de_otro_edificio(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    categoria_ajena, grupo_ajeno = categoria_y_grupo(mundo, mundo.otro)
    archivo = png_con_qr(texto_del_qr(datos_qr()))
    subido = creada(mundo, archivo)
    lector = LectorDeIaFalso(propuesta_buena(categoria, grupo))
    correr_la_tarea(mundo, str(subido["id"]), lector)
    [llamada] = lector.llamadas or [None]
    assert llamada is not None, "el lector no se llamó"
    assert llamada["contenido"] == archivo and llamada["tipo"] == "image/png"
    ids_de_categorias = {c["id"] for c in llamada["categorias"]}
    ids_de_grupos = {g["id"] for g in llamada["grupos"]}
    assert categoria in ids_de_categorias and grupo in ids_de_grupos
    assert categoria_ajena not in ids_de_categorias and grupo_ajeno not in ids_de_grupos
    assert all(set(c) == {"id", "nombre"} for c in llamada["categorias"] + llamada["grupos"]), "sólo id y nombre"


def test_c01_la_lectura_del_gasto_es_de_quien_puede_leerlo(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    id_ = leida(mundo, datos_qr(), LectorDeIaFalso(propuesta_buena(categoria, grupo)))
    for rol in ("super_admin", "admin_del_edificio", "consejo"):
        mundo.como(rol)
        assert mundo.cliente.get(f"/api/gastos/{id_}/lectura").status_code == 200, rol
    for rol in ("admin_de_otro_edificio", "administracion_b"):
        mundo.como(rol)
        assert mundo.cliente.get(f"/api/gastos/{id_}/lectura").status_code == 404, rol
    mundo.como("super_admin")
    assert mundo.cliente.get(f"/api/gastos/{uuid4()}/lectura").status_code == 404


# --- C02: sólo lo que existe y está activo en el edificio -----------------------------------------------------


def _ajeno(m: Mundo) -> tuple[str, str]:
    return categoria_y_grupo(m, m.otro)


def test_c02_categoria_y_grupo_de_otro_edificio_quedan_nulos_con_su_motivo(mundo: Mundo) -> None:
    categoria_ajena, grupo_ajeno = _ajeno(mundo)
    id_ = leida(mundo, datos_qr(), LectorDeIaFalso(propuesta_buena(categoria_ajena, grupo_ajeno)))
    g = gasto(mundo, id_)
    assert g["categoria_id"] is None and g["grupo_id"] is None, (g["categoria_id"], g["grupo_id"])
    assert g["concepto"] == "Mantenimiento de ascensores, octubre", "lo demás se aplica igual"
    estado = lectura(mundo, id_)
    assert estado["estado"] == "borrador" and estado["motivo"] is None
    assert estado["detalle"]["descartados"] == {"categoria_id": "fuera_del_vocabulario",
                                                "grupo_id": "fuera_del_vocabulario"}
    assert estado["datos_de"]["categoria_id"] is None and estado["datos_de"]["grupo_id"] is None
    assert estado["datos_de"]["concepto"] == "ia"


def test_c02_categoria_y_grupo_desactivados_no_se_aplican_ni_se_le_ofrecen_a_la_ia(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    viva, grupo_vivo = categoria_y_grupo(mundo)
    desactivar(mundo, "categorias", categoria)
    desactivar(mundo, "grupos", grupo)
    lector = LectorDeIaFalso(propuesta_buena(categoria, grupo))
    id_ = leida(mundo, datos_qr(), lector)
    g = gasto(mundo, id_)
    assert g["categoria_id"] is None and g["grupo_id"] is None
    assert lectura(mundo, id_)["detalle"]["descartados"] == {"categoria_id": "fuera_del_vocabulario",
                                                             "grupo_id": "fuera_del_vocabulario"}
    [llamada] = lector.llamadas
    assert categoria not in {c["id"] for c in llamada["categorias"]} and viva in {c["id"] for c in llamada["categorias"]}
    assert grupo not in {c["id"] for c in llamada["grupos"]} and grupo_vivo in {c["id"] for c in llamada["grupos"]}


@pytest.mark.parametrize("valor", [str(uuid4()), "no-es-un-uuid", "", 123, None, ["x"], {"id": "x"}])
def test_c02_un_id_inventado_o_mal_formado_queda_nulo_y_no_rompe_nada(mundo: Mundo, valor: Any) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    id_ = leida(mundo, datos_qr(), LectorDeIaFalso(propuesta_buena(valor, grupo)))
    g = gasto(mundo, id_)
    assert g["categoria_id"] is None, f"{valor!r} no es una categoría del edificio"
    assert g["grupo_id"] == grupo, "el otro campo se evalúa por separado"
    estado = lectura(mundo, id_)
    assert estado["estado"] == "borrador"
    assert estado["detalle"]["descartados"]["categoria_id"] in {"fuera_del_vocabulario", "invalido"}


# --- C03: la IA falla, no responde o se sale del contrato -----------------------------------------------------


def _quedo_sin_ia(m: Mundo, id_: str, antes: dict[str, Any], motivo: str) -> None:
    g = gasto(m, id_)
    assert g["estado"] == "sin_ia", f"estado: se esperaba sin_ia, llegó {g['estado']!r}"
    assert datos_intocables(g) == datos_intocables(antes), "los datos del QR quedan intactos"
    assert all(g[c] is None for c in ("concepto", "categoria_id", "grupo_id", "periodo")), "nada a medias"
    estado = lectura(m, id_)
    assert estado["estado"] == "sin_ia" and estado["motivo"] == motivo, estado
    assert all(v is None for k, v in estado["datos_de"].items() if k != "importe")


def test_c03_si_el_lector_falla_el_gasto_queda_sin_ia_con_los_datos_del_qr(mundo: Mundo) -> None:
    subido = subir_qr(mundo, datos_qr())
    correr_la_tarea(mundo, str(subido["id"]), LectorDeIaFalso(falla=RuntimeError("503 del proveedor")))
    _quedo_sin_ia(mundo, str(subido["id"]), subido, "ia_fallo")
    assert lectura(mundo, str(subido["id"]))["datos_de"]["importe"] == "qr"


def test_c03_sin_lector_configurado_queda_sin_ia_y_no_hay_llamada(mundo: Mundo) -> None:
    subido = subir_qr(mundo, datos_qr())
    correr_la_tarea(mundo, str(subido["id"]), None)
    _quedo_sin_ia(mundo, str(subido["id"]), subido, "ia_no_configurada")
    assert llamadas(mundo) == [], "sin llamada no hay fila de costo"


@pytest.mark.parametrize("propuesta", ["texto suelto", ["lista"], 42, None, {}, {"concepto": "sólo uno"},
                                       {"concepto": "x", "periodo": "2026-10", "categoria_id": None,
                                        "grupo_id": None}])
def test_c03_una_respuesta_fuera_de_contrato_queda_sin_ia_y_no_aplica_nada(mundo: Mundo, propuesta: Any) -> None:
    subido = subir_qr(mundo, datos_qr())
    correr_la_tarea(mundo, str(subido["id"]), LectorDeIaFalso(propuesta))
    _quedo_sin_ia(mundo, str(subido["id"]), subido, "fuera_de_contrato")


def test_c03_una_factura_sin_qr_con_la_ia_caida_queda_sin_ia_y_vacia(mundo: Mundo) -> None:
    subido = creada(mundo, png_con_qr(texto_del_qr("no es de ARCA")))
    correr_la_tarea(mundo, str(subido["id"]), LectorDeIaFalso(falla=TimeoutError("sin respuesta")))
    g = gasto(mundo, str(subido["id"]))
    assert g["estado"] == "sin_ia" and g["origen"] == "sin_qr"
    assert g["importe"] is None and g["concepto"] is None
    assert lectura(mundo, str(subido["id"]))["motivo"] == "ia_fallo"


def test_c03_un_campo_con_valor_invalido_no_tumba_a_los_demas(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    malos = {"concepto": 123, "periodo": "ayer", "importe": "-5.00"}
    id_ = leida_sin_qr(mundo, LectorDeIaFalso(propuesta_buena(categoria, grupo, **malos)))
    g = gasto(mundo, id_)
    assert g["estado"] == "borrador", "la respuesta cumple el contrato: algunos campos no"
    assert g["concepto"] is None and g["periodo"] is None and g["importe"] is None
    assert g["categoria_id"] == categoria and g["grupo_id"] == grupo
    descartados = lectura(mundo, id_)["detalle"]["descartados"]
    assert descartados == {"concepto": "invalido", "periodo": "invalido", "importe": "invalido"}


@pytest.mark.parametrize("campo, valor", [("periodo", "2026-13"), ("periodo", "2026-10-15"), ("periodo", "10/2026"),
                                          ("importe", "1500,50"), ("importe", "1500.5"), ("importe", "0.00"),
                                          ("importe", 1500.5), ("concepto", "   "), ("concepto", "a" * 201),
                                          ("concepto", "línea 1\nlínea 2")])
def test_c03_los_formatos_fuera_de_la_regla_se_descartan(mundo: Mundo, campo: str, valor: Any) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    id_ = leida_sin_qr(mundo, LectorDeIaFalso(propuesta_buena(categoria, grupo, **{campo: valor})))
    g = gasto(mundo, id_)
    destino = "periodo" if campo == "periodo" else campo
    assert g[destino] is None, f"{campo}={valor!r} debía descartarse, quedó {g[destino]!r}"
    assert lectura(mundo, id_)["detalle"]["descartados"] == {campo: "invalido"}


def test_c03_la_ia_no_pisa_lo_que_la_persona_ya_cargo(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    subido = subir_qr(mundo, datos_qr())
    with mundo.base.conectar_app() as conexion, conexion.transaction():
        fijar_tenant(conexion, mundo.admin)
        conexion.execute("UPDATE gasto SET concepto = 'Concepto de la persona' WHERE id = %s", (subido["id"],))
    correr_la_tarea(mundo, str(subido["id"]), LectorDeIaFalso(propuesta_buena(categoria, grupo)))
    g = gasto(mundo, str(subido["id"]))
    assert g["concepto"] == "Concepto de la persona"
    assert lectura(mundo, str(subido["id"]))["datos_de"]["concepto"] != "ia"
    assert g["categoria_id"] == categoria, "lo que estaba vacío sí se completa"


def test_c01_c03_si_la_cola_esta_caida_el_201_sale_igual_y_la_lectura_se_puede_reintentar(mundo: Mundo) -> None:
    categoria, grupo = categoria_y_grupo(mundo)
    mundo.cola.falla = True
    subido = subir_qr(mundo, datos_qr())
    assert gasto(mundo, str(subido["id"]))["estado"] == "borrador"
    correr_la_tarea(mundo, str(subido["id"]), LectorDeIaFalso(propuesta_buena(categoria, grupo)))
    assert gasto(mundo, str(subido["id"]))["concepto"] == "Mantenimiento de ascensores, octubre"
