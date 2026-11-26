"""H-036 · C01 y C02: la factura con QR queda como gasto en borrador con lo que trae el QR.

Cada test sube la factura por la ruta nueva; hoy responde 404, que contra el 201 esperado es una aserción.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from ._h036 import (
    CLAVES_DE_LA_RESPUESTA,
    CUIT_DEL_EDIFICIO,
    CUIT_DEL_EJEMPLO,
    CUIT_DEL_PROVEEDOR,
    EJEMPLO_OFICIAL,
    Mundo,
    cantidad,
    creada,
    datos_qr,
    jpeg_con_qr,
    pdf_con_qr,
    pdf_con_qr_en_la_segunda_pagina,
    png_con_qr,
    sin_qr_ok,
    subir_qr,
    texto_del_qr,
)


# --- C01: el gasto en borrador con los datos del QR ---------------------------------------------------------


def test_c01_la_factura_con_qr_crea_el_gasto_en_borrador(mundo: Mundo) -> None:
    gasto = subir_qr(mundo, datos_qr())
    assert set(gasto) == CLAVES_DE_LA_RESPUESTA, f"claves: sobran {set(gasto) - CLAVES_DE_LA_RESPUESTA}, " \
                                                  f"faltan {CLAVES_DE_LA_RESPUESTA - set(gasto)}"
    assert gasto["estado"] == "borrador"
    assert gasto["origen"] == "qr" and gasto["motivo_sin_qr"] is None
    assert gasto["complejo_id"] == str(mundo.edificio)
    assert gasto["cuit_emisor"] == CUIT_DEL_PROVEEDOR
    assert gasto["punto_de_venta"] == "3" and gasto["tipo_de_comprobante"] == "11"
    assert gasto["numero_de_comprobante"] == "1001"
    assert gasto["fecha_de_factura"] == "2026-10-14"
    assert gasto["documento_receptor"] == CUIT_DEL_EDIFICIO
    assert isinstance(gasto["importe"], str) and gasto["importe"] == "1500.50", f"importe: {gasto['importe']!r}"
    assert gasto["tipo"] == "ordinario"
    assert gasto["aviso"] is None, "el receptor es el edificio: no hay aviso"
    assert cantidad(mundo, "gasto") == 1


def test_c01_lo_que_el_qr_no_trae_queda_vacio_y_no_se_puede_aprobar(mundo: Mundo) -> None:
    """Concepto, categoría, grupo y período los pone la IA (H-037) o la persona: nunca se inventan acá."""
    gasto = subir_qr(mundo, datos_qr())
    vacios = {c: gasto[c] for c in ("concepto", "categoria_id", "grupo_id", "periodo", "periodo_de_imputacion")}
    assert all(v is None for v in vacios.values()), f"el QR no trae esos datos: {vacios}"
    r = mundo.cliente.post(f"/api/gastos/{gasto['id']}/aprobar")
    assert r.status_code == 422, f"un borrador incompleto no se aprueba (422): {r.status_code} {r.text[:200]}"
    assert mundo.uno("SELECT estado FROM gasto WHERE id = %s", (gasto["id"],)) == "borrador"


def test_c01_el_proveedor_se_busca_por_cuit_y_se_crea_si_no_existe(mundo: Mundo) -> None:
    assert cantidad(mundo, "proveedor") == 0
    uno = subir_qr(mundo, datos_qr(nroCmp=1))
    assert uno["proveedor_id"] is not None
    filas = mundo.filas("SELECT id::text, cuit, razon_social, complejo_id::text, activo FROM proveedor")
    assert len(filas) == 1, f"tenía que crearse un proveedor: {filas}"
    proveedor_id, cuit, razon, complejo, activo = filas[0]
    assert proveedor_id == uno["proveedor_id"] and cuit == CUIT_DEL_PROVEEDOR
    assert complejo == str(mundo.edificio) and activo is True
    assert razon == f"CUIT {CUIT_DEL_PROVEEDOR}", f"razón social provisoria: {razon!r}"
    otro = subir_qr(mundo, datos_qr(nroCmp=2))
    assert otro["proveedor_id"] == uno["proveedor_id"], "la segunda factura del mismo CUIT reusa el proveedor"
    assert cantidad(mundo, "proveedor") == 1


def test_c01_un_proveedor_ya_cargado_por_el_6_se_reusa_sin_cambiarle_nada(mundo: Mundo) -> None:
    r = mundo.cliente.post(f"/api/complejos/{mundo.edificio}/proveedores",
                           json={"razon_social": "Ascensores del Plata S.R.L.", "cuit": CUIT_DEL_PROVEEDOR})
    assert r.status_code == 201, r.text
    existente = r.json()["id"]
    gasto = subir_qr(mundo, datos_qr())
    assert gasto["proveedor_id"] == existente, "tenía que usar el proveedor que ya existe"
    assert mundo.filas("SELECT razon_social FROM proveedor") == [("Ascensores del Plata S.R.L.",)]


def test_c01_el_mismo_cuit_en_otro_edificio_es_otro_proveedor(mundo: Mundo) -> None:
    aqui = subir_qr(mundo, datos_qr())
    alla = subir_qr(mundo, datos_qr(), complejo=mundo.otro)
    assert aqui["proveedor_id"] != alla["proveedor_id"], "los proveedores son del edificio"
    assert cantidad(mundo, "proveedor") == 2
    assert alla["complejo_id"] == str(mundo.otro)


def test_c01_el_importe_en_pesos_es_importe_por_cotizacion(mundo: Mundo) -> None:
    gasto = subir_qr(mundo, datos_qr(moneda="DOL", ctz=1.5, importe=100.5, nroCmp=7))
    assert gasto["importe"] == "150.75", f"100,50 USD x 1,5 = 150,75 pesos, llegó {gasto['importe']!r}"
    assert Decimal(gasto["importe"]) == Decimal("150.75")
    mismo = subir_qr(mundo, datos_qr(moneda="PES", ctz=1, importe=2000, nroCmp=8))
    assert mismo["importe"] == "2000.00", f"en pesos la cotización es 1: {mismo['importe']!r}"


def test_c01_el_gasto_se_lee_despues_con_su_origen(mundo: Mundo) -> None:
    gasto = subir_qr(mundo, datos_qr())
    r = mundo.cliente.get(f"/api/gastos/{gasto['id']}")
    assert r.status_code == 200, r.text
    leido = r.json()
    for clave in (*(set(CLAVES_DE_LA_RESPUESTA) - {"aviso", "factura"}),):
        assert clave in leido, f"el detalle del gasto no trae `{clave}`"
        assert leido[clave] == gasto[clave], f"`{clave}`: el detalle dice {leido[clave]!r}, el alta {gasto[clave]!r}"
    assert "factura" not in leido and "url" not in leido, "el detalle no lleva un link permanente"
    listado = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/gastos").json()
    assert [g["id"] for g in listado] == [gasto["id"]] and listado[0]["origen"] == "qr"


@pytest.mark.parametrize("rol", ["super_admin", "admin_principal", "admin_del_edificio"])
def test_c01_los_perfiles_que_cargan_gastos_pueden_subir_facturas(mundo: Mundo, rol: str) -> None:
    mundo.como(rol)
    gasto = subir_qr(mundo, datos_qr(nroCmp=mundo.numero_nuevo()))
    assert gasto["origen"] == "qr"


def test_c01_una_imagen_jpeg_tambien_vale(mundo: Mundo) -> None:
    gasto = creada(mundo, jpeg_con_qr(texto_del_qr(datos_qr(nroCmp=55))), nombre="factura.jpg", tipo="image/jpeg")
    assert gasto["origen"] == "qr" and gasto["numero_de_comprobante"] == "55"


# --- C02: los dos dominios, el ejemplo oficial y el PDF -----------------------------------------------------


def test_c02_el_ejemplo_oficial_de_la_especificacion_v1(mundo: Mundo) -> None:
    gasto = subir_qr(mundo, EJEMPLO_OFICIAL)
    assert gasto["origen"] == "qr", f"el ejemplo oficial se tiene que leer: {gasto['motivo_sin_qr']!r}"
    assert gasto["cuit_emisor"] == CUIT_DEL_EJEMPLO
    assert gasto["punto_de_venta"] == "10" and gasto["tipo_de_comprobante"] == "1"
    assert gasto["numero_de_comprobante"] == "94"
    assert gasto["fecha_de_factura"] == "2020-10-13"
    assert gasto["documento_receptor"] == "20000000001"
    assert gasto["importe"] == "786500.00", f"12.100 USD x 65 = 786.500 pesos, llegó {gasto['importe']!r}"
    assert gasto["aviso"] is None, "el receptor del ejemplo es el CUIT del edificio de la aceptación"


@pytest.mark.parametrize("dominio", ["www.arca.gob.ar", "www.afip.gob.ar", "arca.gob.ar", "afip.gob.ar"])
def test_c02_los_dos_dominios_se_leen(mundo: Mundo, dominio: str) -> None:
    gasto = subir_qr(mundo, datos_qr(nroCmp=mundo.numero_nuevo()), dominio=dominio)
    assert gasto["origen"] == "qr", f"{dominio}: {gasto['motivo_sin_qr']!r}"
    assert gasto["cuit_emisor"] == CUIT_DEL_PROVEEDOR


def test_c02_un_pdf_se_lee_desde_su_primera_pagina(mundo: Mundo) -> None:
    gasto = creada(mundo, pdf_con_qr(texto_del_qr(datos_qr(nroCmp=77))), nombre="factura.pdf",
                   tipo="application/pdf")
    assert gasto["origen"] == "qr" and gasto["numero_de_comprobante"] == "77", gasto["motivo_sin_qr"]
    assert gasto["importe"] == "1500.50"


def test_c02_un_qr_en_la_segunda_pagina_no_cuenta(mundo: Mundo) -> None:
    """Sólo la primera página: una factura con el QR de otra cosa más abajo no pasa por buena."""
    gasto = creada(mundo, pdf_con_qr_en_la_segunda_pagina(texto_del_qr(datos_qr(nroCmp=78))),
                   nombre="factura.pdf", tipo="application/pdf")
    sin_qr_ok(gasto, "no_hay_qr")


def test_c02_el_tipo_sale_de_los_bytes_y_no_del_nombre_ni_del_content_type(mundo: Mundo) -> None:
    png = png_con_qr(texto_del_qr(datos_qr(nroCmp=91)))
    como_pdf = creada(mundo, png, nombre="factura.pdf", tipo="application/pdf")
    assert como_pdf["origen"] == "qr", "un PNG con nombre .pdf sigue siendo un PNG"
    pdf = pdf_con_qr(texto_del_qr(datos_qr(nroCmp=92)))
    como_png = creada(mundo, pdf, nombre="factura.png", tipo="image/png")
    assert como_png["origen"] == "qr", "un PDF con nombre .png sigue siendo un PDF"


def test_c02_los_numeros_del_qr_llegan_como_texto_sin_perder_ceros_ni_signos(mundo: Mundo) -> None:
    """ptoVta y nroCmp enteros del JSON: texto decimal, sin '.0' (clave de duplicado de R12)."""
    gasto = subir_qr(mundo, datos_qr(ptoVta=12, tipoCmp=6, nroCmp=123456))
    assert (gasto["punto_de_venta"], gasto["tipo_de_comprobante"], gasto["numero_de_comprobante"]) == \
        ("12", "6", "123456")
    assert not any("." in gasto[c] for c in ("punto_de_venta", "tipo_de_comprobante", "numero_de_comprobante"))


def test_c02_el_gasto_creado_no_toca_nada_mas_que_su_fila_y_el_proveedor(mundo: Mundo) -> None:
    antes: dict[str, int] = {t: cantidad(mundo, t) for t in ("gasto", "proveedor", "nota_de_credito", "cargo_particular")}
    subir_qr(mundo, datos_qr())
    despues: dict[str, Any] = {t: cantidad(mundo, t) for t in antes}
    assert despues == {**antes, "gasto": antes["gasto"] + 1, "proveedor": antes["proveedor"] + 1}, (antes, despues)
