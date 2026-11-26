"""H-036 · lo que no tiene que pasar (N01 a N04).

Cada test sube antes una factura buena: lo que se pide después sobre la ruta nueva hoy responde 404, que contra el
201, 409, 422 o 403 esperado es una aserción, y que ningún negativo pase verde sin la construcción.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from proptech_core.pagos.dominio.comprobante import TAMANO_MAXIMO

from ._h036 import (
    ACCION_DE_CARGAR,
    CAMPOS_DEL_QR,
    CUIT_DEL_PROVEEDOR,
    Mundo,
    OTRO_CUIT,
    cantidad,
    creada,
    datos_qr,
    en_el_libro,
    gasto_del_6,
    pdf_con_qr,
    png_con_cabecera_enorme,
    png_con_qr,
    png_sin_qr,
    sin_qr_ok,
    subir,
    subir_qr,
    texto_del_qr,
)


def _bien(m: Mundo, nro: int = 3001) -> dict[str, Any]:
    """Una factura buena subida: si la ruta no existe, el test cae acá por aserción."""
    return subir_qr(m, datos_qr(nroCmp=nro))


# --- N01: la misma factura dos veces ------------------------------------------------------------------------


def test_n01_la_misma_factura_dos_veces_da_409_y_no_crea_nada(mundo: Mundo) -> None:
    primera = _bien(mundo, 1)
    antes = (cantidad(mundo, "gasto"), cantidad(mundo, "proveedor"))
    r = subir(mundo, png_con_qr(texto_del_qr(datos_qr(nroCmp=1))))
    assert r.status_code == 409, f"la misma factura: se esperaba 409, llegó {r.status_code}: {r.text[:200]}"
    assert r.json() == {"detail": "conflicto", "campo": "factura"}, r.json()
    assert (cantidad(mundo, "gasto"), cantidad(mundo, "proveedor")) == antes == (1, 1)
    assert mundo.uno("SELECT id::text FROM gasto") == primera["id"]


def test_n01_los_cuatro_datos_deciden_no_los_bytes_ni_el_importe(mundo: Mundo) -> None:
    _bien(mundo, 2)
    otro_archivo = pdf_con_qr(texto_del_qr(datos_qr(nroCmp=2, importe=99999.9, fecha="2026-11-02")))
    r = subir(mundo, otro_archivo, nombre="rescaneada.pdf", tipo="application/pdf")
    assert r.status_code == 409, f"mismos cuatro datos en otro archivo y con otro importe: {r.status_code} {r.text[:200]}"
    assert cantidad(mundo, "gasto") == 1


def test_n01_contra_un_gasto_cargado_a_mano_en_el_6_en_los_dos_sentidos(mundo: Mundo) -> None:
    manual = gasto_del_6(mundo, nro=3)
    assert manual.status_code == 201, manual.text
    r = subir(mundo, png_con_qr(texto_del_qr(datos_qr(nroCmp=3))))
    assert r.status_code == 409, f"la factura ya cargada a mano: {r.status_code} {r.text[:200]}"
    assert cantidad(mundo, "gasto") == 1
    _bien(mundo, 4)
    al_reves = gasto_del_6(mundo, nro=4)
    assert al_reves.status_code == 409, f"la carga a mano de una factura leída por QR: {al_reves.status_code}"


def test_n01_el_mismo_numero_con_otro_tipo_otro_cuit_u_otro_edificio_no_choca(mundo: Mundo) -> None:
    _bien(mundo, 5)
    distintas = [datos_qr(nroCmp=5, tipoCmp=6), datos_qr(nroCmp=5, ptoVta=4), datos_qr(nroCmp=5, cuit=int(OTRO_CUIT))]
    for datos in distintas:
        assert subir_qr(mundo, datos)["origen"] == "qr", f"no es la misma factura: {datos}"
    en_otro_edificio = subir_qr(mundo, datos_qr(nroCmp=5), complejo=mundo.otro)
    assert en_otro_edificio["origen"] == "qr", "la clave de duplicado es por edificio"
    assert cantidad(mundo, "gasto") == 5


# --- N02: un QR que no sirve no deja datos --------------------------------------------------------------------

_BASE = datos_qr()
_CASOS_N02: list[tuple[str, Any, str, str]] = [
    ("version_desconocida", datos_qr(ver=2), "www.arca.gob.ar", "version_desconocida"),
    ("version_texto", datos_qr(ver="1"), "www.arca.gob.ar", "version_desconocida"),
    ("sin_version", datos_qr(ver=None), "www.arca.gob.ar", "version_desconocida"),
    ("json_invalido", "esto no es json", "www.arca.gob.ar", "json_invalido"),
    ("json_cortado", '{"ver":1,"fecha":"2026-10-14"', "www.arca.gob.ar", "json_invalido"),
    ("json_que_no_es_objeto", "[1,2,3]", "www.arca.gob.ar", "json_invalido"),
    ("dominio_ajeno", datos_qr(), "www.ejemplo.invalid", "dominio_ajeno"),
    ("dominio_que_empieza_igual", datos_qr(), "www.arca.gob.ar.ejemplo.invalid", "dominio_ajeno"),
    ("dominio_que_termina_igual", datos_qr(), "ejemplo-arca.gob.ar", "dominio_ajeno"),
    ("dominio_con_credenciales", datos_qr(), "www.arca.gob.ar@ejemplo.invalid", "dominio_ajeno"),
    ("importe_texto", datos_qr(importe="abc"), "www.arca.gob.ar", "importe_invalido"),
    ("importe_booleano", datos_qr(importe=True), "www.arca.gob.ar", "importe_invalido"),
    ("importe_cero", datos_qr(importe=0), "www.arca.gob.ar", "importe_invalido"),
    ("importe_negativo", datos_qr(importe=-10), "www.arca.gob.ar", "importe_invalido"),
    ("importe_con_tres_decimales", datos_qr(importe=10.123), "www.arca.gob.ar", "importe_invalido"),
    ("sin_importe", datos_qr(importe=None), "www.arca.gob.ar", "importe_invalido"),
    ("cotizacion_cero", datos_qr(moneda="DOL", ctz=0), "www.arca.gob.ar", "importe_invalido"),
    ("cotizacion_texto", datos_qr(moneda="DOL", ctz="x"), "www.arca.gob.ar", "importe_invalido"),
    ("cuit_con_verificador_malo", datos_qr(cuit=int(CUIT_DEL_PROVEEDOR) + 1), "www.arca.gob.ar", "datos_invalidos"),
    ("cuit_texto", datos_qr(cuit="no"), "www.arca.gob.ar", "datos_invalidos"),
    ("sin_numero_de_comprobante", datos_qr(nroCmp=None), "www.arca.gob.ar", "datos_invalidos"),
    ("punto_de_venta_texto", datos_qr(ptoVta="abc"), "www.arca.gob.ar", "datos_invalidos"),
    ("fecha_inexistente", datos_qr(fecha="2026-02-30"), "www.arca.gob.ar", "datos_invalidos"),
    ("fecha_con_otro_formato", datos_qr(fecha="14/10/2026"), "www.arca.gob.ar", "datos_invalidos"),
]


@pytest.mark.parametrize(("datos", "dominio", "motivo"), [c[1:] for c in _CASOS_N02], ids=[c[0] for c in _CASOS_N02])
def test_n02_un_qr_que_no_sirve_deja_el_gasto_sin_qr_con_su_motivo(mundo: Mundo, datos: Any, dominio: str,
                                                                    motivo: str) -> None:
    gasto = creada(mundo, png_con_qr(texto_del_qr(datos, dominio)))
    sin_qr_ok(gasto, motivo)
    assert cantidad(mundo, "gasto") == 1 and cantidad(mundo, "proveedor") == 0, "ni proveedor ni datos a medias"
    fila = mundo.filas("SELECT " + ", ".join(CAMPOS_DEL_QR[1:]) + " FROM gasto")[0]
    assert all(v is None for v in fila), f"la base no puede guardar datos de un QR descartado: {fila}"


def test_n02_un_qr_que_no_es_una_url_de_arca_ni_es_un_pago_conocido_queda_sin_qr(mundo: Mundo) -> None:
    gasto = creada(mundo, png_con_qr("https://ejemplo.invalid/pagar?factura=1"))
    sin_qr_ok(gasto, "dominio_ajeno")
    texto_suelto = creada(mundo, png_con_qr("hola, esto no es una url"))
    sin_qr_ok(texto_suelto, "dominio_ajeno")


# --- N03: lo que no es una factura ----------------------------------------------------------------------------

_BASURA = [
    ("texto_plano", b"esto no es una factura"),
    ("ejecutable", b"MZ\x90\x00" + b"\x00" * 200),
    ("gif", b"GIF89a" + b"\x00" * 100),
    ("svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
    ("html", b"<html><body>factura</body></html>"),
    ("vacio", b""),
]


@pytest.mark.parametrize("contenido", [b[1] for b in _BASURA], ids=[b[0] for b in _BASURA])
def test_n03_un_archivo_que_no_es_imagen_ni_pdf_da_422_y_no_crea_nada(mundo: Mundo, contenido: bytes) -> None:
    _bien(mundo, 1)
    antes = (cantidad(mundo, "gasto"), cantidad(mundo, "proveedor"))
    for nombre, tipo in (("factura.png", "image/png"), ("factura.pdf", "application/pdf")):
        r = subir(mundo, contenido, nombre=nombre, tipo=tipo)
        assert r.status_code == 422, f"{nombre} con bytes ajenos: se esperaba 422, llegó {r.status_code}: {r.text[:200]}"
    assert (cantidad(mundo, "gasto"), cantidad(mundo, "proveedor")) == antes


def test_n03_el_limite_de_tamano_es_el_de_los_comprobantes_del_8(mundo: Mundo) -> None:
    _bien(mundo, 1)
    justo = b"%PDF-1.4\n" + b"0" * (TAMANO_MAXIMO - 9)
    assert len(justo) == TAMANO_MAXIMO
    aceptado = creada(mundo, justo, nombre="grande.pdf", tipo="application/pdf")
    sin_qr_ok(aceptado, "no_hay_qr")
    antes = cantidad(mundo, "gasto")
    r = subir(mundo, justo + b"0", nombre="grande.pdf", tipo="application/pdf")
    assert r.status_code == 422, f"un byte de más: se esperaba 422, llegó {r.status_code}: {r.text[:200]}"
    assert cantidad(mundo, "gasto") == antes


def test_n03_un_archivo_que_dice_ser_png_o_pdf_y_esta_roto_no_rompe_el_servidor(mundo: Mundo) -> None:
    _bien(mundo, 1)
    for nombre, contenido, tipo in (("roto.png", b"\x89PNG\r\n\x1a\n" + b"basura" * 50, "image/png"),
                                    ("roto.pdf", b"%PDF-1.4\n" + b"basura" * 50, "application/pdf"),
                                    ("roto.jpg", b"\xff\xd8\xff" + b"basura" * 50, "image/jpeg"),
                                    ("bomba.png", png_con_cabecera_enorme(), "image/png")):
        gasto = creada(mundo, contenido, nombre=nombre, tipo=tipo)
        sin_qr_ok(gasto, "no_hay_qr")


def test_n03_sin_el_campo_archivo_o_sin_multipart_da_422(mundo: Mundo) -> None:
    _bien(mundo, 1)
    ruta = f"/api/complejos/{mundo.edificio}/facturas"
    assert mundo.cliente.post(ruta).status_code == 422, "sin cuerpo"
    assert mundo.cliente.post(ruta, json={"archivo": "hola"}).status_code == 422, "JSON en vez de multipart"
    r = subir(mundo, png_sin_qr(), campo="factura")
    assert r.status_code == 422, f"el campo se llama `archivo`: {r.status_code}"
    assert cantidad(mundo, "gasto") == 1


# --- N04: permisos, alcance y el libro -----------------------------------------------------------------------


@pytest.mark.parametrize("rol", ["contador", "contador_del_edificio", "auxiliar", "consejo"])
def test_n04_sin_el_permiso_de_cargar_gastos_da_403_y_no_guarda_nada(mundo: Mundo, rol: str) -> None:
    _bien(mundo, 1)
    mundo.como(rol)
    r = subir(mundo, png_con_qr(texto_del_qr(datos_qr(nroCmp=2))))
    assert r.status_code == 403, f"{rol}: se esperaba 403, llegó {r.status_code}: {r.text[:200]}"
    assert r.json()["detail"]["permiso_faltante"] == ACCION_DE_CARGAR, r.json()
    assert cantidad(mundo, "gasto") == 1 and cantidad(mundo, "proveedor") == 1


def test_n04_edificio_ajeno_inexistente_o_de_otra_administracion_da_404(mundo: Mundo) -> None:
    _bien(mundo, 1)
    nueva = png_con_qr(texto_del_qr(datos_qr(nroCmp=2)))
    for quien, complejo in (("admin_principal", mundo.edificio_b), ("admin_principal", uuid4()),
                            ("admin_de_otro_edificio", mundo.edificio), ("consejo_de_otro_edificio", mundo.edificio),
                            ("administracion_b", mundo.edificio)):
        mundo.como(quien)
        r = subir(mundo, nueva, complejo=complejo)
        assert r.status_code == 404, f"{quien} en {complejo}: se esperaba 404, llegó {r.status_code}: {r.text[:200]}"
        assert r.json() == {"detail": "no encontrado"}, r.json()
    assert cantidad(mundo, "gasto") == 1


def test_n04_el_orden_de_los_chequeos_es_alcance_permiso_y_recien_el_archivo(mundo: Mundo) -> None:
    _bien(mundo, 1)
    mundo.como("contador")
    assert subir(mundo, b"basura").status_code == 403, "sin permiso gana al archivo inválido"
    mundo.como("admin_de_otro_edificio")
    assert subir(mundo, b"basura").status_code == 404, "sin alcance gana a todo"
    mundo.como("admin_principal")
    assert subir(mundo, b"basura").status_code == 422


def test_n04_nunca_se_escribe_en_el_libro(mundo: Mundo) -> None:
    assert en_el_libro(mundo) == 0
    _bien(mundo, 1)
    subir(mundo, png_con_qr(texto_del_qr(datos_qr(nroCmp=1))))  # el duplicado (409)
    creada(mundo, png_sin_qr())
    subir(mundo, b"basura")  # el 422
    mundo.como("contador")
    subir(mundo, png_sin_qr())  # el 403
    assert en_el_libro(mundo) == 0, "la factura es un borrador del 6: el libro no se entera hasta emitir (7)"
    assert cantidad(mundo, "gasto") == 2
