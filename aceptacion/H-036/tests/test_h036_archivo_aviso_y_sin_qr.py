"""H-036 · C03 (la factura guardada y su link firmado), C04 (el receptor) y C05 (sin QR legible)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from ._h036 import (
    CUIT_DEL_EDIFICIO,
    CUIT_DEL_RECEPTOR_AJENO,
    Mundo,
    cantidad,
    creada,
    datos_qr,
    firmar_de_factura,
    gasto_del_6,
    pdf_con_qr,
    pdf_sin_qr,
    png_con_qr,
    png_sin_qr,
    sin_qr_ok,
    subir_qr,
    texto_del_qr,
    url_de_la_factura,
)

DESCARGA = "/api/facturas/descarga"

# --- C03: la factura guardada y el link firmado --------------------------------------------------------------


def test_c03_la_respuesta_trae_un_link_firmado_que_baja_los_mismos_bytes(mundo: Mundo) -> None:
    contenido = png_con_qr(texto_del_qr(datos_qr()))
    gasto = creada(mundo, contenido)
    url = url_de_la_factura(gasto)
    assert url.startswith(f"{DESCARGA}?token="), url
    vence = datetime.fromisoformat(gasto["factura"]["vence_en"])
    assert vence.tzinfo is not None
    assert timedelta(0) < vence - datetime.now(UTC) <= timedelta(minutes=15, seconds=5), f"vence_en: {vence}"
    d = mundo.cliente.get(url)
    assert d.status_code == 200, f"descarga: {d.status_code} {d.text[:200]}"
    assert d.content == contenido, "la descarga no trae los bytes que se subieron"
    assert d.headers["content-type"] == "image/png"
    assert d.headers["cache-control"] == "no-store" and d.headers["x-content-type-options"] == "nosniff"


def test_c03_un_pdf_se_baja_como_pdf_y_sin_sesion(mundo: Mundo) -> None:
    from proptech_api.acceso import identidad_actual

    contenido = pdf_con_qr(texto_del_qr(datos_qr()))
    gasto = creada(mundo, contenido, nombre="factura.pdf", tipo="application/pdf")
    mundo.app.dependency_overrides.pop(identidad_actual, None)
    d = mundo.cliente.get(url_de_la_factura(gasto))
    assert d.status_code == 200, f"el token firmado es la autorización, sin sesión: {d.status_code} {d.text[:200]}"
    assert d.content == contenido and d.headers["content-type"] == "application/pdf"


def test_c03_el_link_alterado_o_vencido_o_de_otra_administracion_no_baja_nada(mundo: Mundo) -> None:
    gasto = creada(mundo, png_con_qr(texto_del_qr(datos_qr())))
    url = url_de_la_factura(gasto)
    assert mundo.cliente.get(url).status_code == 200, "el link vigente tiene que bajar la factura"
    token = url.split("token=", 1)[1]
    cambiado = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert mundo.cliente.get(f"{DESCARGA}?token={cambiado}").status_code == 403
    vigente = firmar_de_factura(mundo, gasto["id"])
    assert mundo.cliente.get(f"{DESCARGA}?token={vigente}").status_code == 200
    vencido = firmar_de_factura(mundo, gasto["id"], vence_en=datetime.now(UTC) - timedelta(minutes=1))
    assert mundo.cliente.get(f"{DESCARGA}?token={vencido}").status_code == 410
    de_otra = firmar_de_factura(mundo, gasto["id"], administracion=mundo.admin_b)
    assert mundo.cliente.get(f"{DESCARGA}?token={de_otra}").status_code == 403, "la administración sale del token"
    de_nadie = firmar_de_factura(mundo, str(uuid4()))
    assert mundo.cliente.get(f"{DESCARGA}?token={de_nadie}").status_code == 403, "un gasto que no existe"
    assert mundo.cliente.get(DESCARGA).status_code == 422, "sin token no hay descarga"


def test_c03_un_token_de_otro_tipo_no_baja_una_factura_ni_al_reves(mundo: Mundo) -> None:
    gasto = creada(mundo, png_con_qr(texto_del_qr(datos_qr())))
    url = url_de_la_factura(gasto)
    assert mundo.cliente.get(url).status_code == 200
    de_comprobante = firmar_de_factura(mundo, gasto["id"], tipo="comprobante")
    assert mundo.cliente.get(f"{DESCARGA}?token={de_comprobante}").status_code == 403
    de_expensa = firmar_de_factura(mundo, gasto["id"], tipo="expensa")
    assert mundo.cliente.get(f"{DESCARGA}?token={de_expensa}").status_code == 403
    token_de_factura = url.split("token=", 1)[1]
    r = mundo.cliente.get(f"/api/comprobantes/descarga?token={token_de_factura}")
    assert r.status_code == 403, f"un token de factura no baja un comprobante: {r.status_code}"
    r = mundo.cliente.get(f"/api/documentos/descarga?token={token_de_factura}")
    assert r.status_code == 403, f"un token de factura no baja una expensa: {r.status_code}"


def test_c03_otro_link_para_la_misma_factura_a_pedido(mundo: Mundo) -> None:
    contenido = png_con_qr(texto_del_qr(datos_qr()))
    gasto = creada(mundo, contenido)
    r = mundo.cliente.post(f"/api/gastos/{gasto['id']}/factura/enlace")
    assert r.status_code == 201, f"enlace nuevo: {r.status_code} {r.text[:200]}"
    nuevo = r.json()
    assert set(nuevo) == {"url", "vence_en"} and nuevo["url"].startswith(f"{DESCARGA}?token=")
    assert mundo.cliente.get(nuevo["url"]).content == contenido
    manual = gasto_del_6(mundo, nro=4242)
    assert manual.status_code == 201, manual.text
    sin_archivo = mundo.cliente.post(f"/api/gastos/{manual.json()['id']}/factura/enlace")
    assert sin_archivo.status_code == 404, f"un gasto cargado a mano no tiene archivo: {sin_archivo.status_code}"
    mundo.como("administracion_b")
    assert mundo.cliente.post(f"/api/gastos/{gasto['id']}/factura/enlace").status_code == 404, "de otra administración"
    mundo.como("admin_de_otro_edificio")
    assert mundo.cliente.post(f"/api/gastos/{gasto['id']}/factura/enlace").status_code == 404, "de otro edificio"


def test_c03_la_factura_se_guarda_aunque_no_tenga_qr(mundo: Mundo) -> None:
    contenido = png_sin_qr()
    gasto = creada(mundo, contenido)
    d = mundo.cliente.get(url_de_la_factura(gasto))
    assert d.status_code == 200 and d.content == contenido, "la factura sin QR también se baja con su link"


# --- C04: el receptor distinto avisa y no bloquea ------------------------------------------------------------


def test_c04_el_receptor_distinto_lleva_el_aviso_del_6_y_no_bloquea(mundo: Mundo) -> None:
    gasto = subir_qr(mundo, datos_qr(nroDocRec=int(CUIT_DEL_RECEPTOR_AJENO)))
    assert gasto["origen"] == "qr" and gasto["estado"] == "borrador", "el aviso no bloquea"
    assert gasto["documento_receptor"] == CUIT_DEL_RECEPTOR_AJENO
    aviso = gasto["aviso"]
    assert isinstance(aviso, str) and CUIT_DEL_RECEPTOR_AJENO in aviso and CUIT_DEL_EDIFICIO in aviso, aviso
    del_6 = gasto_del_6(mundo, nro=9001, receptor=CUIT_DEL_RECEPTOR_AJENO)
    assert del_6.status_code == 201 and del_6.json().get("aviso") == aviso, \
        f"el aviso es el mismo del 6: {del_6.json()!r} contra {aviso!r}"
    assert mundo.uno("SELECT count(*) FROM gasto WHERE documento_receptor = %s", (CUIT_DEL_RECEPTOR_AJENO,)) == 2


def test_c04_sin_aviso_si_el_receptor_coincide_falta_o_el_edificio_no_tiene_cuit(mundo: Mundo) -> None:
    igual = subir_qr(mundo, datos_qr(nroCmp=11))
    assert igual["aviso"] is None
    sin_receptor = subir_qr(mundo, datos_qr(nroCmp=12, tipoDocRec=None, nroDocRec=None))
    assert sin_receptor["origen"] == "qr", f"el receptor es opcional en el QR: {sin_receptor['motivo_sin_qr']!r}"
    assert sin_receptor["aviso"] is None and sin_receptor["documento_receptor"] is None
    sin_cuit_en_el_edificio = subir_qr(mundo, datos_qr(nroDocRec=int(CUIT_DEL_RECEPTOR_AJENO)), complejo=mundo.otro)
    assert sin_cuit_en_el_edificio["aviso"] is None, "sin CUIT del edificio no hay contra qué comparar"
    assert sin_cuit_en_el_edificio["documento_receptor"] == CUIT_DEL_RECEPTOR_AJENO


# --- C05: sin QR legible ----------------------------------------------------------------------------------


def test_c05_una_imagen_sin_qr_queda_en_borrador_sin_datos_del_qr(mundo: Mundo) -> None:
    gasto = creada(mundo, png_sin_qr())
    sin_qr_ok(gasto, "no_hay_qr")
    assert cantidad(mundo, "gasto") == 1
    assert cantidad(mundo, "proveedor") == 0, "sin QR no hay CUIT: no se crea ningún proveedor"


def test_c05_un_pdf_sin_qr_tambien(mundo: Mundo) -> None:
    gasto = creada(mundo, pdf_sin_qr(), nombre="factura.pdf", tipo="application/pdf")
    sin_qr_ok(gasto, "no_hay_qr")
    d = mundo.cliente.get(url_de_la_factura(gasto))
    assert d.status_code == 200 and d.headers["content-type"] == "application/pdf"


def test_c05_el_gasto_sin_qr_espera_la_ia_o_la_carga_a_mano_y_no_se_aprueba(mundo: Mundo) -> None:
    gasto = creada(mundo, png_sin_qr())
    r = mundo.cliente.post(f"/api/gastos/{gasto['id']}/aprobar")
    assert r.status_code == 422, f"sin datos no se aprueba: {r.status_code} {r.text[:200]}"
    leido: dict[str, Any] = mundo.cliente.get(f"/api/gastos/{gasto['id']}").json()
    assert leido["origen"] == "sin_qr" and leido["motivo_sin_qr"] == "no_hay_qr" and leido["estado"] == "borrador"
    categoria_grupo = mundo.cliente.get(f"/api/complejos/{mundo.edificio}/gastos").json()
    assert [g["id"] for g in categoria_grupo] == [gasto["id"]], "el borrador sin datos se lista igual"


def test_c05_dos_facturas_sin_qr_no_chocan_entre_si(mundo: Mundo) -> None:
    """Sin los cuatro datos no hay clave de duplicado (R12): dos borradores sin QR conviven."""
    uno = creada(mundo, png_sin_qr())
    otro = creada(mundo, png_sin_qr())
    assert uno["id"] != otro["id"] and cantidad(mundo, "gasto") == 2
