"""Ataque del rompedor (vuelta 2, F6; L-001 'lenta', L-009 gemelos): el
verificador de base de `/api/salud` tiene un plazo TOTAL de 2 s (hilo +
`queue.get(timeout=...)`, `PLAZO_VERIFICACION_S`); el de cola sólo tenía
`socket_timeout=2` POR OPERACIÓN. Un Redis lento que contesta cada comando en
1,5 s (por debajo del timeout de socket) hace que una sola verificación tarde
varias veces 2 s: AUTH + CLIENT SETINFO x2 + PING.
"""

import socket
import threading
import time
from types import SimpleNamespace

from pydantic import SecretStr

from proptech_api.salud import _verificador_con_cliente_redis
from proptech_core.compartido.conexion_redis import cliente_redis_sincrono

_DEMORA_POR_COMANDO_S = 1.5
#: Tarea 5.1 (D20, F13): el plazo por verificación bajó de 2 s
#: (`PLAZO_VERIFICACION_S`) a un plazo TOTAL compartido de 1,5 s
#: (`PLAZO_TOTAL_SALUD_S`). La cota de este test baja con él, de 2,5 s a
#: 1,8 s (el mismo margen de 0,3 s sobre el plazo que usan los escenarios de
#: `/api/salud` con dependencias congeladas).
_COTA_S = 1.8


def _redis_lento() -> int:
    servidor = socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(5)

    def _atender() -> None:
        conexion, _ = servidor.accept()
        while True:
            datos = conexion.recv(4096)
            if not datos:
                return
            time.sleep(_DEMORA_POR_COMANDO_S)
            respuesta = b"+PONG\r\n" if b"PING" in datos.upper() else b"+OK\r\n"
            conexion.sendall(respuesta)

    threading.Thread(target=_atender, daemon=True).start()
    return int(servidor.getsockname()[1])


def test_verificador_de_cola_acotado_a_2s_con_redis_lento() -> None:
    puerto = _redis_lento()
    configuracion = SimpleNamespace(
        redis_host="127.0.0.1", redis_port=puerto, redis_password=SecretStr("x")
    )
    verificar = _verificador_con_cliente_redis(cliente_redis_sincrono(configuracion))  # type: ignore[arg-type]

    inicio = time.monotonic()
    resultado = verificar()
    duracion = time.monotonic() - inicio

    assert duracion < _COTA_S, f"la verificación de cola tardó {duracion:.1f}s"
    # Red de seguridad del test: si esto da True, el verificador ni siquiera
    # habló con el socket lento y la cota no prueba nada.
    assert resultado is False
