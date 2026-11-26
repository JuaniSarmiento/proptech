"""H-041 · el certificado de libre deuda (C01 a C07). Contrato en `aceptacion/H-041/CONTRATO.md`."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ._h041 import (
    CORTE,
    Mundo,
    ars,
    armar_la_deuda,
    auditorias,
    bajar_el_pdf,
    del_libro_a,
    del_libro,
    emitir_certificado,
    en_cinco_minutos,
    filas_de_certificados,
    interes_corrido_del_libro,
    firmar_enlace,
    listar,
    pagar,
    rechazar,
    sin_espacios,
    superusuario,
    texto_de,
    texto_del_pdf,
)

# --- C01: emitir y guardar -------------------------------------------------------------------------------


def test_c01_emitir_responde_201_y_guarda_el_certificado_con_su_foto(mundo: Mundo) -> None:
    """Escenario: el super admin emite el libre deuda de la `1A` al 05/11/2026"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    assert (c["unidad_id"], c["fecha_de_corte"]) == (str(mundo.unidades["1A"]), "2026-11-05"), c
    assert (c["saldo"], c["libre_de_deuda"], c["en_revision"]) == ("20720.00", False, []), c
    assert filas_de_certificados(mundo) == 1, "emitir guarda el certificado"
    fila = superusuario(mundo, "SELECT id, unidad_id, fecha_de_corte, saldo::text, huella, emitido_por "
                               "FROM certificado_de_libre_deuda WHERE administracion_id = %s", (mundo.admin,))
    assert [(str(f[0]), str(f[1]), str(f[2]), f[3], f[4], str(f[5])) for f in fila] == [
        (c["id"], str(mundo.unidades["1A"]), "2026-11-05", "20720.00", c["huella"],
         str(mundo.personas["super_admin"]))], fila


def test_c01_una_unidad_sin_saldo_dice_libre_de_deuda_con_cero(mundo: Mundo) -> None:
    """Escenario: la `1B` pagó septiembre y octubre antes de vencer"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1B", CORTE)
    assert (c["saldo"], c["capital"], c["intereses"], c["libre_de_deuda"]) == ("0.00", "0.00", "0.00", True), c
    texto = texto_del_pdf(bajar_el_pdf(mundo, c)).lower()
    assert "libre de deuda" in texto and "0,00" in texto, texto[:400]


# --- C02: el saldo sale del libro, a la fecha de corte ------------------------------------------------------


def test_c02_el_saldo_es_el_capital_mas_los_intereses_registrados_al_centavo(mundo: Mundo) -> None:
    """Escenario: la `1A` debe septiembre y octubre; el libro registró 720,00 de interés hasta el 31/10"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    assert (c["capital"], c["intereses"], c["saldo"]) == ("20000.00", "720.00", "20720.00"), c
    libro = del_libro_a(mundo, "1A", CORTE)
    assert (texto_de(libro["capital"]), texto_de(libro["intereses"]), texto_de(libro["saldo"])) == (
        c["capital"], c["intereses"], c["saldo"]), (c, libro)
    dos = emitir_certificado(mundo, "2B", CORTE)
    assert dos["saldo"] == texto_de(del_libro_a(mundo, "2B", CORTE)["saldo"]) == "8489.76", dos


def test_c02_un_movimiento_posterior_al_corte_no_cambia_el_certificado(mundo: Mundo) -> None:
    """Escenario: un pago del 12/11 no cambia el libre deuda al 05/11 pero sí el del 15/11"""
    armar_la_deuda(mundo)
    antes = emitir_certificado(mundo, "1A", CORTE)
    pagar(mundo, "1A", "7000.00", date(2026, 11, 12))
    despues = emitir_certificado(mundo, "1A", CORTE)
    assert (despues["saldo"], despues["huella"]) == (antes["saldo"], antes["huella"]) == (
        "20720.00", antes["huella"]), (antes, despues)
    quince = emitir_certificado(mundo, "1A", date(2026, 11, 15))
    assert quince["saldo"] == "23720.00", f"30.000 de capital + 720 de interés - 7.000 pagados: {quince}"
    assert quince["saldo"] == texto_de(del_libro_a(mundo, "1A", date(2026, 11, 15))["saldo"]), quince


def test_c02_un_corte_anterior_deja_afuera_lo_que_vencio_o_se_registro_despues(mundo: Mundo) -> None:
    """Escenario: el libre deuda de la `1A` al 30/09, con octubre y noviembre ya emitidos"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", date(2026, 9, 30))
    assert (c["capital"], c["intereses"], c["saldo"]) == ("10000.00", "200.00", "10200.00"), c
    assert [q["periodo"] for q in c["vencen_despues"]] == ["2026-10-01", "2026-11-01"], c["vencen_despues"]
    assert c["saldo"] == texto_de(del_libro_a(mundo, "1A", date(2026, 9, 30))["saldo"]), c


# --- C03: pagos confirmados por la fecha de la transferencia; informados, aparte ------------------------------


def test_c03_un_pago_confirmado_cuenta_por_la_fecha_de_la_transferencia(mundo: Mundo) -> None:
    """Escenario: P1 (8.000, transferido el 20/10) y P3 (1.000, transferido el 12/11), los dos confirmados el 18/11"""
    armar_la_deuda(mundo)
    al_5 = emitir_certificado(mundo, "2B", CORTE)
    assert al_5["saldo"] == "8489.76", f"16.000 + 489,76 de interés - los 8.000 de P1 (P3 es posterior): {al_5}"
    al_15 = emitir_certificado(mundo, "2B", date(2026, 11, 15))
    assert al_15["saldo"] == "15489.76", f"+ 8.000 de noviembre (vence el 10) - 1.000 de P3: {al_15}"
    assert al_15["saldo"] == texto_de(del_libro_a(mundo, "2B", date(2026, 11, 15))["saldo"]), al_15


def test_c03_un_pago_informado_sin_confirmar_se_lista_aparte_y_no_resta(mundo: Mundo) -> None:
    """Escenario: Ana informó P2 (3.000, transferido el 02/11) y nadie lo confirmó"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "2B", CORTE)
    assert c["en_revision"] == [{"pago_id": mundo.pagos["P2"], "importe": "3000.00",
                                 "fecha_de_transferencia": "2026-11-02", "banco": "Banco Nación",
                                 "numero_de_operacion": "OP-0002"}], c["en_revision"]
    assert c["saldo"] == "8489.76", "el pago en revisión no resta"
    assert emitir_certificado(mundo, "2B", date(2026, 10, 31))["en_revision"] == [], "se transfirió después del corte"
    rechazar(mundo, mundo.pagos["P2"])
    assert emitir_certificado(mundo, "2B", CORTE)["en_revision"] == [], "un pago rechazado ya no está en revisión"
    assert emitir_certificado(mundo, "1A", CORTE)["en_revision"] == [], "la `1A` no tiene pagos informados"


# --- C04: las cuotas que vencen después del corte -------------------------------------------------------------


def test_c04_las_cuotas_posteriores_al_corte_se_listan_aparte_y_no_suman(mundo: Mundo) -> None:
    """Escenario: noviembre vence el 10 y el corte es el 05"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    assert c["vencen_despues"] == [{"periodo": "2026-11-01", "vencimiento": "2026-11-10", "importe": "10000.00"}], c
    assert c["saldo"] == "20720.00", "noviembre no suma al saldo"
    uno_b = emitir_certificado(mundo, "1B", CORTE)
    assert (uno_b["saldo"], uno_b["libre_de_deuda"]) == ("0.00", True), uno_b
    assert uno_b["vencen_despues"] == [
        {"periodo": "2026-11-01", "vencimiento": "2026-11-10", "importe": "40000.00"}], uno_b["vencen_despues"]
    quince = emitir_certificado(mundo, "1A", date(2026, 11, 15))
    assert quince["vencen_despues"] == [] and quince["saldo"] == "30720.00", f"ya venció y suma: {quince}"


# --- C05: el PDF, por enlace firmado ----------------------------------------------------------------------------


def test_c05_el_pdf_se_baja_por_un_enlace_firmado_que_vence_en_15_minutos(mundo: Mundo) -> None:
    """Escenario: el enlace del certificado de la `1A`"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    assert c["enlace"]["url"].startswith("/api/libre-deuda/descarga?token="), c["enlace"]
    vence = datetime.fromisoformat(c["enlace"]["vence_en"].replace("Z", "+00:00"))
    assert vence.tzinfo is not None, "el vencimiento lleva zona horaria"
    assert timedelta(minutes=14) < vence - datetime.now(UTC) <= timedelta(minutes=15, seconds=5), c["enlace"]
    texto = texto_del_pdf(bajar_el_pdf(mundo, c))
    assert c["id"] in sin_espacios(texto), "el PDF lleva el identificador del certificado"
    for esperado in ("Torre Ficticia", "1A", "05/11/2026", ars("20720.00"), ars("10000.00")):
        assert esperado in texto, f"falta `{esperado}` en el PDF: {texto[:500]}"
    assert "libre de deuda" not in texto.lower(), "una unidad con saldo no es libre de deuda"


def test_c05_el_pdf_siempre_es_el_mismo_para_ese_certificado(mundo: Mundo) -> None:
    """Escenario: se baja dos veces y después cambia el libro: es el mismo archivo, no se regenera"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    primero = bajar_el_pdf(mundo, c)
    assert bajar_el_pdf(mundo, c) == primero, "dos descargas, el mismo archivo"
    pagar(mundo, "1A", "7000.00", date(2026, 11, 12))
    otro = emitir_certificado(mundo, "1A", date(2026, 11, 15))
    assert bajar_el_pdf(mundo, c) == primero, "el libro cambió y el PDF del certificado no"
    assert bajar_el_pdf(mundo, otro) != primero, "otro certificado, otro PDF"


def test_c05_el_enlace_vencido_da_410_el_alterado_403_y_el_de_otro_tipo_403(mundo: Mundo) -> None:
    """Escenario: tokens malos contra la descarga pública"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    assert mundo.cliente.get(firmar_enlace(mundo, c["id"], vence_en=en_cinco_minutos())).status_code == 200, (
        "control: un token bien firmado sirve")
    vencido = firmar_enlace(mundo, c["id"], vence_en=datetime.now(UTC) - timedelta(minutes=1))
    assert mundo.cliente.get(vencido).status_code == 410
    alterado = firmar_enlace(mundo, c["id"], vence_en=en_cinco_minutos())[:-1] + "0"
    assert mundo.cliente.get(alterado).status_code == 403
    de_expensa = firmar_enlace(mundo, c["id"], vence_en=en_cinco_minutos(), tipo="expensa")
    assert mundo.cliente.get(de_expensa).status_code == 403, "un token de otro tipo no baja un libre deuda"
    inexistente = firmar_enlace(mundo, "00000000-0000-4000-8000-000000000000", vence_en=en_cinco_minutos())
    assert mundo.cliente.get(inexistente).status_code == 404
    assert mundo.cliente.get("/api/libre-deuda/descarga").status_code in (403, 422), "sin token no hay descarga"


def test_c05_get_lista_los_certificados_de_la_unidad_del_mas_nuevo_al_mas_viejo(mundo: Mundo) -> None:
    """Escenario: dos certificados de la `1A`, uno de la `1B` y ninguno de la `2A`"""
    armar_la_deuda(mundo)
    primero = emitir_certificado(mundo, "1A", CORTE)
    segundo = emitir_certificado(mundo, "1A", date(2026, 11, 15))
    emitir_certificado(mundo, "1B", CORTE)
    de_la_1a = listar(mundo, "1A")
    assert [c["id"] for c in de_la_1a] == [segundo["id"], primero["id"]], "el más nuevo primero"
    assert [(c["fecha_de_corte"], c["saldo"], c["huella"]) for c in de_la_1a] == [
        ("2026-11-15", segundo["saldo"], segundo["huella"]), ("2026-11-05", "20720.00", primero["huella"])]
    assert bajar_el_pdf(mundo, de_la_1a[1]) == bajar_el_pdf(mundo, primero), "cada elemento trae su enlace"
    assert [c["fecha_de_corte"] for c in listar(mundo, "1B")] == ["2026-11-05"]
    assert listar(mundo, "2A") == [], "una unidad sin certificados da la lista vacía"


# --- C06: la gestión judicial (la marca llega con H-042) ---------------------------------------------------------


def test_c06_por_ahora_el_certificado_trae_en_gestion_judicial_en_falso_y_sin_leyenda(mundo: Mundo) -> None:
    """Escenario: ninguna unidad tiene todavía la marca judicial (H-042)"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    assert c["en_gestion_judicial"] is False, c
    assert "gestión judicial" not in texto_del_pdf(bajar_el_pdf(mundo, c)).lower()


# --- C07: la auditoría -------------------------------------------------------------------------------------------


def test_c07_la_emision_queda_auditada_con_quien_la_unidad_y_el_corte(mundo: Mundo) -> None:
    """Escenario: el super admin emite un libre deuda de la `1A`"""
    existe = mundo.filas("SELECT count(*) FROM accion_de_auditoria WHERE nombre = 'emitir_libre_deuda'")
    assert existe[0][0] == 1, "la migración suma `emitir_libre_deuda` al vocabulario de auditoría"
    armar_la_deuda(mundo)
    assert auditorias(mundo) == [], "control: antes de emitir no hay nada"
    c = emitir_certificado(mundo, "1A", CORTE)
    filas = auditorias(mundo)
    assert len(filas) == 1, filas
    entidad, entidad_id, persona_id, detalle = filas[0]
    assert (entidad, str(entidad_id), str(persona_id)) == (
        "certificado_de_libre_deuda", c["id"], str(mundo.personas["super_admin"])), filas
    assert detalle == {"unidad_id": str(mundo.unidades["1A"]), "fecha_de_corte": "2026-11-05"}, detalle
    cuando = superusuario(mundo, "SELECT creado_en, now() FROM auditoria WHERE accion = 'emitir_libre_deuda'")[0]
    assert abs((cuando[1] - cuando[0]).total_seconds()) < 600, "la fecha de la auditoría es la de la emisión"


# --- C08: el interés corrido, en una línea aparte (R21, D-081) -----------------------------------------------------


def test_c08_el_interes_corrido_es_el_de_r03_al_centavo_y_no_suma_al_saldo(mundo: Mundo) -> None:
    """Escenario: la `1A` debe septiembre y octubre; el libro registró el interés hasta el 31/10"""
    armar_la_deuda(mundo)
    # 3% mensual proporcional = 0,1% por día sobre el capital impago: 20.000 x 0,001 x 5 días.
    al_5 = emitir_certificado(mundo, "1A", CORTE)
    assert al_5["interes_corrido"] == "100.00" == texto_de(interes_corrido_del_libro(mundo, "1A", CORTE)), al_5
    assert (al_5["saldo"], al_5["intereses"]) == ("20720.00", "720.00"), "el corrido no suma al saldo"
    al_15 = emitir_certificado(mundo, "1A", date(2026, 11, 15))
    assert al_15["interes_corrido"] == "350.00", f"15 días de 20.000 y 5 días de los 10.000 de noviembre: {al_15}"
    assert al_15["interes_corrido"] == texto_de(interes_corrido_del_libro(mundo, "1A", date(2026, 11, 15)))
    assert al_15["saldo"] == "30720.00", al_15
    hoy = emitir_certificado(mundo, "1A", date(2026, 11, 18))
    assert hoy["interes_corrido"] == "440.00" == texto_de(interes_corrido_del_libro(mundo, "1A", date(2026, 11, 18)))
    assert hoy["saldo"] == "30720.00", hoy
    dos_b = emitir_certificado(mundo, "2B", CORTE)
    assert dos_b["interes_corrido"] == texto_de(interes_corrido_del_libro(mundo, "2B", CORTE)), dos_b
    assert dos_b["interes_corrido"] == "40.80", f"5 días sobre 160 de septiembre y 8.000 de octubre: {dos_b}"
    assert dos_b["saldo"] == "8489.76", dos_b


def test_c08_sin_vencimientos_impagos_el_interes_corrido_es_cero(mundo: Mundo) -> None:
    """Escenario: la `1B` pagó en término"""
    armar_la_deuda(mundo)
    assert emitir_certificado(mundo, "1B", CORTE)["interes_corrido"] == "0.00"


def test_c08_el_interes_corrido_no_se_registra_en_el_libro(mundo: Mundo) -> None:
    """Escenario: se emiten certificados con interés corrido y el libro no se entera"""
    armar_la_deuda(mundo)
    antes = del_libro(mundo)
    assert emitir_certificado(mundo, "1A", date(2026, 11, 18))["interes_corrido"] == "440.00"
    assert del_libro(mundo) == antes, "ni un movimiento de interés nuevo"
    assert interes_corrido_del_libro(mundo, "1A", date(2026, 11, 18)) == Decimal("440.00"), "sigue sin registrarse"


def test_c08_el_pdf_muestra_la_linea_del_interes_corrido(mundo: Mundo) -> None:
    """Escenario: el PDF del libre deuda de la `1A` al 05/11"""
    armar_la_deuda(mundo)
    c = emitir_certificado(mundo, "1A", CORTE)
    texto = texto_del_pdf(bajar_el_pdf(mundo, c))
    assert "corrido" in texto.lower() and ars("100.00") in texto, texto[:600]
