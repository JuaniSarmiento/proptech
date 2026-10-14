"""Tests del formatter de logs: una línea JSON con una lista cerrada de campos (D7).

Escenarios de `trazabilidad-y-logs`: Campo no permitido; Mensaje con argumentos;
Línea de un pedido atendido (formato de la línea). Cambio 1c, tarea 2.1.
"""

import json
import logging

from proptech_core.compartido.logs import FormateadorJSON


def _record(
    *,
    nivel: int = logging.INFO,
    mensaje: str = "evento_de_prueba",
    argumentos: tuple[object, ...] = (),
    extra: dict[str, object] | None = None,
    logger_nombre: str = "proptech_api.prueba",
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=logger_nombre,
        level=nivel,
        pathname="archivo.py",
        lineno=1,
        msg=mensaje,
        args=argumentos,
        exc_info=None,
    )
    for clave, valor in (extra or {}).items():
        setattr(record, clave, valor)
    return record


def _formatear(record: logging.LogRecord, servicio: str = "api") -> str:
    return FormateadorJSON(servicio=servicio).format(record)


def test_una_sola_linea_json_aunque_el_valor_tenga_saltos_de_linea() -> None:
    resultado = _formatear(_record(mensaje="pago\nfraccionado\npara el vecino"))
    assert "\n" not in resultado
    assert len(resultado.splitlines()) == 1
    datos = json.loads(resultado)
    assert datos["evento"] == "pago\nfraccionado\npara el vecino"


def test_ts_utc_con_milisegundos() -> None:
    # 2026-10-09T18:04:05.123456 UTC como epoch.
    import datetime as _dt

    momento = _dt.datetime(2026, 10, 9, 18, 4, 5, 123456, tzinfo=_dt.UTC)
    record = _record()
    record.created = momento.timestamp()
    datos = json.loads(_formatear(record))
    assert datos["ts"] == "2026-10-09T18:04:05.123Z"


def test_campos_base_presentes_y_en_el_orden_de_d7() -> None:
    record = _record(
        mensaje="pedido_atendido",
        extra={"request_id": "3f2c1a00-0000-4000-8000-000000000000"},
        logger_nombre="proptech_api.seguimiento",
    )
    resultado = _formatear(record, servicio="api")
    claves = list(json.loads(resultado, object_pairs_hook=lambda pares: [p[0] for p in pares]))
    assert claves[:6] == ["ts", "nivel", "servicio", "logger", "evento", "request_id"]


def test_request_id_ausente_cuando_no_se_paso() -> None:
    datos = json.loads(_formatear(_record()))
    assert "request_id" not in datos


def test_niveles_en_minuscula() -> None:
    niveles = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical",
    }
    for nivel, esperado in niveles.items():
        datos = json.loads(_formatear(_record(nivel=nivel)))
        assert datos["nivel"] == esperado


def test_campo_no_permitido_se_descarta_y_se_cuenta() -> None:
    datos = json.loads(_formatear(_record(extra={"email": "vecino@ejemplo.invalid"})))
    assert "email" not in datos
    assert datos["campos_descartados"] == 1


def test_dos_campos_no_permitidos_se_cuentan_los_dos() -> None:
    datos = json.loads(
        _formatear(_record(extra={"email": "x@y.invalid", "telefono": "+54 261 000 0000"}))
    )
    assert "email" not in datos
    assert "telefono" not in datos
    assert datos["campos_descartados"] == 2


def test_campo_permitido_no_se_descarta_y_no_hay_contador() -> None:
    datos = json.loads(_formatear(_record(extra={"metodo": "GET", "estado": 200})))
    assert datos["metodo"] == "GET"
    assert datos["estado"] == 200
    assert "campos_descartados" not in datos


def test_mensaje_con_argumentos_deja_la_plantilla_y_no_el_dato() -> None:
    datos = json.loads(_formatear(_record(mensaje="pago de %s", argumentos=("dato-sensible-123",))))
    assert datos["evento"] == "pago de %s"
    assert "dato-sensible-123" not in json.dumps(datos)


def test_traceback_crudo_se_descarta_y_se_reemplaza_por_tipo_y_traza() -> None:
    """D7, L-007, vuelta 2 (F7): Starlette/uvicorn pasan el traceback entero
    ya formateado como `msg` (sin `exc_info`); el formatter tiene que
    reconocerlo igual y no copiar el mensaje de la excepción ni las líneas
    de código."""
    marcador = "marcador-traceback-crudo-9f1b"
    mensaje_crudo = (
        "Traceback (most recent call last):\n"
        '  File "/app/starlette/routing.py", line 660, in lifespan\n'
        "    await receive()\n"
        '  File "/app/app_que_falla.py", line 7, in lifespan\n'
        f"    raise RuntimeError('password authentication failed for user {marcador}')\n"
        f"RuntimeError: password authentication failed for user {marcador}\n"
    )
    datos = json.loads(_formatear(_record(mensaje=mensaje_crudo, logger_nombre="uvicorn.error")))
    assert datos["evento"] == "traceback_crudo_descartado"
    assert marcador not in json.dumps(datos)
    assert datos["tipo_error"] == "RuntimeError"
    assert datos["traza"] == [
        "/app/starlette/routing.py:660:lifespan",
        "/app/app_que_falla.py:7:lifespan",
    ]


def test_mensaje_de_uvicorn_sin_traceback_no_se_toca() -> None:
    """Triangula el caso anterior: un mensaje normal de `uvicorn.error` (sin
    el marcador de un traceback) sigue siendo su propia plantilla, como
    cualquier otro evento (D7)."""
    datos = json.loads(
        _formatear(
            _record(mensaje="Application startup failed. Exiting.", logger_nombre="uvicorn.error")
        )
    )
    assert datos["evento"] == "Application startup failed. Exiting."
    assert "tipo_error" not in datos
    assert "traza" not in datos
