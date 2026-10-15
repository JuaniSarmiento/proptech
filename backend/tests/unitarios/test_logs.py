"""Tests del formatter de logs: una línea JSON con una lista cerrada de campos (D7).

Escenarios de `trazabilidad-y-logs`: Campo no permitido; Mensaje con argumentos;
Línea de un pedido atendido (formato de la línea). Cambio 1c, tarea 2.1.
"""

import json
import logging

import pytest

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


def test_traceback_crudo_se_descarta_con_tipo_y_traza_fijos() -> None:
    """D7, L-007, vuelta 2 (F7): Starlette/uvicorn pasan el traceback entero
    ya formateado como `msg` (sin `exc_info`); el formatter tiene que
    reconocerlo igual y no copiar el mensaje de la excepción ni las líneas
    de código.

    Tarea 5.2 (D21, F7c): antes `tipo_error` y `traza` salían de parsear ese
    texto (`RuntimeError` y los cuadros `File "..."`); el rompedor mostró
    formas en las que ese parseo sacaba datos del mensaje a esos campos
    (`test_ataque_traceback_crudo_v2.py`). Ahora los dos son valores FIJOS,
    sin leer el texto: esta expectativa cambia de los valores parseados a
    `"desconocido"` y `[]` (se borra el parseo, no se endurece)."""
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
    assert datos["tipo_error"] == "desconocido"
    assert datos["traza"] == []


@pytest.mark.parametrize(
    "mensaje_crudo",
    [
        # Marcador en el nombre de la excepción, con forma válida (termina en Error).
        (
            "Traceback (most recent call last):\n"
            '  File "/app/x.py", line 1, in f\n'
            "MarcadorError9f1b: detalle\n"
        ),
        # Marcador en el nombre de la excepción, con forma de clase rara (sin
        # sufijo Error/Exception/Warning/Exit/Interrupt: el parseo viejo caía
        # al "ErrorDesconocido" por default; ahora da lo mismo que cualquier
        # otro caso, sin leer nada).
        (
            "Traceback (most recent call last):\n"
            '  File "/app/x.py", line 1, in f\n'
            "ClaseRaraMarcador9f1b: detalle\n"
        ),
        # Marcador en la línea File "..." con comillas y espacios adentro.
        (
            "Traceback (most recent call last):\n"
            '  File "/app/directorio con espacio/\\"marcador9f1b\\".py", line 2, in f\n'
            "RuntimeError: detalle\n"
        ),
        # Marcador en la línea de la función.
        (
            "Traceback (most recent call last):\n"
            '  File "/app/x.py", line 3, in funcion_marcador9f1b\n'
            "RuntimeError: detalle\n"
        ),
        # Marcador en el mensaje multilínea de la excepción.
        (
            "Traceback (most recent call last):\n"
            '  File "/app/x.py", line 4, in f\n'
            "RuntimeError: primera linea\n"
            "marcador9f1b: segunda linea\n"
        ),
    ],
)
def test_traceback_crudo_con_marcador_en_cualquier_parte_da_siempre_valores_fijos(
    mensaje_crudo: str,
) -> None:
    """Tarea 5.2 (D21, F7c): un marcador en el nombre de la excepción, en la
    línea `File "..."` (con comillas o espacios), en la línea de la función o
    en el mensaje multilínea siempre da los mismos tres valores fijos, sin
    excepción: no se lee el texto para sacar nada de él (L-008)."""
    datos = json.loads(_formatear(_record(mensaje=mensaje_crudo, logger_nombre="uvicorn.error")))
    assert datos["evento"] == "traceback_crudo_descartado"
    assert datos["tipo_error"] == "desconocido"
    assert datos["traza"] == []
    assert "marcador9f1b" not in json.dumps(datos)
    assert "9f1b" not in json.dumps(datos)


def test_mensaje_que_es_un_dict_da_evento_mensaje_no_texto() -> None:
    """Tarea 5.2 (D21, F7c): un `msg` que no es texto ni excepción (acá, un
    `dict`) nunca se convierte con su representación de texto."""
    marcador = "marcador-dict-no-texto-7c3a"
    datos = json.loads(_formatear(_record(mensaje={"clave": marcador})))  # type: ignore[arg-type]
    assert datos["evento"] == "mensaje_no_texto"
    assert marcador not in json.dumps(datos)


def test_objeto_con_str_propio_da_evento_mensaje_no_texto_sin_llamar_str() -> None:
    """Un objeto cuyo `__str__` devolvería un marcador nunca debe convertirse:
    el evento es fijo y `__str__` no se llega a invocar sobre él."""
    marcador = "marcador-objeto-str-4e2b"

    class _ObjetoConStrPropio:
        def __str__(self) -> str:
            return marcador

    datos = json.loads(_formatear(_record(mensaje=_ObjetoConStrPropio())))  # type: ignore[arg-type]
    assert datos["evento"] == "mensaje_no_texto"
    assert marcador not in json.dumps(datos)


def test_subclase_de_str_con_str_propio_da_evento_mensaje_no_texto() -> None:
    """D21: `type(msg) is str` exige texto EXACTO, no una subclase: una
    subclase de `str` puede redefinir `__str__` y devolver cualquier cosa, así
    que también cae en `mensaje_no_texto`, no en su propio texto como
    plantilla."""
    marcador = "marcador-subclase-str-2f9d"

    class _SubclaseDeStr(str):
        def __str__(self) -> str:
            return marcador

    datos = json.loads(_formatear(_record(mensaje=_SubclaseDeStr("plantilla-original"))))
    assert datos["evento"] == "mensaje_no_texto"
    assert marcador not in json.dumps(datos)
    assert "plantilla-original" not in json.dumps(datos)


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
