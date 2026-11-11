"""Tests unitarios del endpoint GET /api/salud, sin base ni cola reales
(dependency_overrides). La cola se agrega en la tarea 4.6 (D4): escenarios de
`entorno-de-ejecucion` Todo funciona; La base no responde; La cola no
responde; La base y la cola no responden. Lecciones: L-007, L-009.

Tarea 5.1 (D20, F13): las dos verificaciones corren en paralelo con un plazo
total compartido (`PLAZO_TOTAL_SALUD_S`) y cada verificación fallida loguea
`salud_degradada` exactamente una vez, aunque el hilo que la corría termine
después de vencido el plazo.
"""

import threading
import time
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient


def _cliente_con_verificadores(
    verificador_base: Callable[[], bool], verificador_cola: Callable[[], bool]
) -> TestClient:
    from proptech_api.app import crear_app
    from proptech_api.salud import obtener_verificador_de_base, obtener_verificador_de_cola

    app = crear_app()
    app.dependency_overrides[obtener_verificador_de_base] = lambda: verificador_base
    app.dependency_overrides[obtener_verificador_de_cola] = lambda: verificador_cola
    return TestClient(app)


def test_todo_funciona_responde_200_con_base_y_cola_ok() -> None:
    cliente = _cliente_con_verificadores(lambda: True, lambda: True)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base": "ok", "cola": "ok"}


def test_base_caida_responde_503_con_cola_ok() -> None:
    cliente = _cliente_con_verificadores(lambda: False, lambda: True)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion", "cola": "ok"}


def test_cola_caida_responde_503_con_base_ok() -> None:
    cliente = _cliente_con_verificadores(lambda: True, lambda: False)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "ok", "cola": "sin_conexion"}


def test_base_y_cola_caidas_responde_503() -> None:
    cliente = _cliente_con_verificadores(lambda: False, lambda: False)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "estado": "degradado",
        "base": "sin_conexion",
        "cola": "sin_conexion",
    }


def test_excepcion_del_verificador_de_base_no_filtra_la_cadena_de_conexion() -> None:
    def verificador_que_explota() -> bool:
        raise RuntimeError("no se pudo conectar a postgresql://usuario:secreto@host/db")

    cliente = _cliente_con_verificadores(verificador_que_explota, lambda: True)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    cuerpo_texto = respuesta.text
    assert "secreto" not in cuerpo_texto
    assert "postgresql://" not in cuerpo_texto
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion", "cola": "ok"}


def test_excepcion_del_verificador_de_cola_no_filtra_host_ni_usuario_ni_excepcion() -> None:
    marcador = "marcador-excepcion-cola-7b1e2a"

    def verificador_que_explota() -> bool:
        raise RuntimeError(f"no se pudo conectar a redis://usuario:{marcador}@host:6379")

    cliente = _cliente_con_verificadores(lambda: True, verificador_que_explota)
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 503
    cuerpo_texto = respuesta.text
    assert marcador not in cuerpo_texto
    assert "redis://" not in cuerpo_texto
    assert respuesta.json() == {"estado": "degradado", "base": "ok", "cola": "sin_conexion"}


def test_sin_prefijo_responde_404() -> None:
    cliente = _cliente_con_verificadores(lambda: True, lambda: True)
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 404


def test_verificador_real_no_cuelga_contra_host_que_no_responde(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D11: timeout de conexión de 2s. Contra una IP que no responde (no rechaza ni
    acepta: nadie contesta), el verificador real tiene que devolver False en pocos
    segundos, no colgarse con el timeout por defecto del sistema operativo.

    Corre en un hilo aparte con `join(timeout=...)` para que el propio test quede
    acotado aunque el código bajo prueba no tenga el timeout aplicado todavía.
    """
    from proptech_api.salud import _verificador_con_engine
    from proptech_core.compartido.base_de_datos import crear_engine
    from proptech_core.compartido.configuracion import Configuracion

    monkeypatch.setenv("POSTGRES_HOST", "10.255.255.1")  # IP privada sin ruta: no responde
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "x")
    monkeypatch.setenv("POSTGRES_PASSWORD", "x")
    monkeypatch.setenv("POSTGRES_DB", "x")

    configuracion = Configuracion()
    engine = crear_engine(configuracion)
    try:
        verificar = _verificador_con_engine(engine)

        resultado: list[bool] = []
        hilo = threading.Thread(target=lambda: resultado.append(verificar()), daemon=True)
        hilo.start()
        hilo.join(timeout=5)

        assert not hilo.is_alive(), (
            "el verificador sigue colgado después de 5s: falta el plazo propio de 2s (D18)"
        )
        assert resultado == [False]
    finally:
        engine.dispose()


def test_verificador_de_cola_real_con_excepcion_devuelve_false_y_loguea_sin_el_mensaje(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D4: cualquier excepción del cliente de Redis es `sin_conexion`, nunca el
    texto del error (L-007)."""
    from proptech_api.salud import _verificador_con_cliente_redis
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    marcador = "marcador-verificador-cola-4f9c3d"

    class _ClienteQueExplota:
        def ping(self) -> bool:
            raise RuntimeError(f"no se pudo conectar: {marcador}")

    verificar = _verificador_con_cliente_redis(_ClienteQueExplota())  # type: ignore[arg-type]
    assert verificar() is False

    salida = capsys.readouterr()
    assert marcador not in salida.out
    assert marcador not in salida.err


# --- Tarea 5.1 (D20, F13): plazo total compartido y una sola línea por falla ---


def _bloquea_para_siempre() -> bool:
    threading.Event().wait()
    return True  # pragma: no cover - nunca se llega: el Event nunca se setea


def _pedir_con_plazo(
    cliente: TestClient, plazo_s: float
) -> tuple[bool, httpx.Response | None, float]:
    """Corre `cliente.get('/api/salud')` en un hilo aparte con un plazo propio
    del TEST (no del código bajo prueba): así, si la implementación actual
    todavía llama a los verificadores de forma secuencial y bloqueante, el
    test corta limpio en vez de colgar el proceso entero (como
    `test_verificador_real_no_cuelga_contra_host_que_no_responde`, arriba)."""
    resultado: list[httpx.Response] = []

    def _pedir() -> None:
        resultado.append(cliente.get("/api/salud"))

    hilo = threading.Thread(target=_pedir, daemon=True)
    inicio = time.monotonic()
    hilo.start()
    hilo.join(timeout=plazo_s)
    duracion = time.monotonic() - inicio
    terminado = not hilo.is_alive()
    return terminado, (resultado[0] if resultado else None), duracion


def test_dos_dependencias_congeladas_responde_503_en_menos_de_1_8s() -> None:
    cliente = _cliente_con_verificadores(_bloquea_para_siempre, _bloquea_para_siempre)

    terminado, respuesta, duracion = _pedir_con_plazo(cliente, plazo_s=5)

    assert terminado, (
        "la respuesta no llegó en 5s: las dos verificaciones no comparten un plazo total (D20)"
    )
    assert duracion < 1.8, f"tardó {duracion:.2f}s, debía responder en menos de 1,8s"
    assert respuesta is not None
    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "estado": "degradado",
        "base": "sin_conexion",
        "cola": "sin_conexion",
    }


def test_solo_base_congelada_responde_503_con_base_sin_conexion_en_menos_de_1_8s() -> None:
    cliente = _cliente_con_verificadores(_bloquea_para_siempre, lambda: True)

    terminado, respuesta, duracion = _pedir_con_plazo(cliente, plazo_s=5)

    assert terminado, "la respuesta no llegó en 5s con sólo la base congelada"
    assert duracion < 1.8, f"tardó {duracion:.2f}s, debía responder en menos de 1,8s"
    assert respuesta is not None
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion", "cola": "ok"}


def test_solo_cola_congelada_responde_503_con_cola_sin_conexion_en_menos_de_1_8s() -> None:
    cliente = _cliente_con_verificadores(lambda: True, _bloquea_para_siempre)

    terminado, respuesta, duracion = _pedir_con_plazo(cliente, plazo_s=5)

    assert terminado, "la respuesta no llegó en 5s con sólo la cola congelada"
    assert duracion < 1.8, f"tardó {duracion:.2f}s, debía responder en menos de 1,8s"
    assert respuesta is not None
    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "ok", "cola": "sin_conexion"}


def test_dependencia_lenta_dentro_del_plazo_responde_200() -> None:
    def _tarda_1s_y_responde_ok() -> bool:
        time.sleep(1)
        return True

    cliente = _cliente_con_verificadores(_tarda_1s_y_responde_ok, lambda: True)

    inicio = time.monotonic()
    respuesta = cliente.get("/api/salud")
    duracion = time.monotonic() - inicio

    assert duracion < 1.8, f"tardó {duracion:.2f}s"
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "base": "ok", "cola": "ok"}


def test_salud_degradada_una_sola_linea_para_base_con_hilo_tardio(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D20: el hilo que corre la verificación de base vence el plazo y
    termina después con un error; sólo informa (y loguea) el primero que
    llega, nunca los dos (el duplicado que arrastraba el 1c)."""
    from proptech_api.salud import _verificador_con_engine
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    marcador = "marcador-hilo-tardio-base-7e2c1a"
    terminado = threading.Event()

    class _ConexionLentaQueFalla:
        def __enter__(self) -> _ConexionLentaQueFalla:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, *_args: object, **_kwargs: object) -> None:
            time.sleep(3.0)
            terminado.set()
            raise RuntimeError(f"fallo tardío {marcador}")

    class _EngineFalso:
        def connect(self) -> _ConexionLentaQueFalla:
            return _ConexionLentaQueFalla()

    verificar = _verificador_con_engine(_EngineFalso())  # type: ignore[arg-type]

    inicio = time.monotonic()
    assert verificar() is False
    duracion = time.monotonic() - inicio
    assert duracion < 2.5, (
        f"el corte tardó {duracion:.2f}s: debía cortar por el plazo, no esperar al hilo tardío"
    )

    assert terminado.wait(timeout=4), "el hilo tardío de la base nunca terminó"
    time.sleep(0.3)  # margen para que el hilo tardío termine de loguear, si lo hace

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    lineas_salud_degradada = [linea for linea in texto.splitlines() if "salud_degradada" in linea]
    assert len(lineas_salud_degradada) == 1, (
        f"se esperaba una sola línea salud_degradada, se loguearon {len(lineas_salud_degradada)}"
    )
    assert marcador not in texto


def test_salud_degradada_una_sola_linea_para_cola_con_hilo_tardio(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Gemelo del anterior para la cola (L-009)."""
    from proptech_api.salud import _verificador_con_cliente_redis
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    marcador = "marcador-hilo-tardio-cola-9d4f2b"
    terminado = threading.Event()

    class _ClienteLentoQueFalla:
        def ping(self) -> bool:
            time.sleep(3.0)
            terminado.set()
            raise RuntimeError(f"fallo tardío {marcador}")

    verificar = _verificador_con_cliente_redis(_ClienteLentoQueFalla())  # type: ignore[arg-type]

    inicio = time.monotonic()
    assert verificar() is False
    duracion = time.monotonic() - inicio
    assert duracion < 2.5, (
        f"el corte tardó {duracion:.2f}s: debía cortar por el plazo, no esperar al hilo tardío"
    )

    assert terminado.wait(timeout=4), "el hilo tardío de la cola nunca terminó"
    time.sleep(0.3)

    salida = capsys.readouterr()
    texto = salida.out + salida.err
    lineas_salud_degradada = [linea for linea in texto.splitlines() if "salud_degradada" in linea]
    assert len(lineas_salud_degradada) == 1, (
        f"se esperaba una sola línea salud_degradada, se loguearon {len(lineas_salud_degradada)}"
    )
    assert marcador not in texto


# --- B1 (auditor, vuelta 2, F1/L-015): el request_id del pedido tiene que
# llegar a la línea `salud_degradada` de una dependencia CONGELADA (el caso
# F13), tal como lo pide `logs.py:67` ("cuando exista"). Un `threading.Thread`
# pelado no hereda la `ContextVar` `request_id_actual`; esto es una regresión
# del 1c, que sí la llevaba. ---


class _ConexionCongelada:
    """Como `_ConexionLentaQueFalla` de arriba, pero nunca falla: se queda
    esperando hasta que el test la libera, para ejercitar el camino del
    PLAZO VENCIDO (no el de la excepción tardía, ya cubierto arriba)."""

    def __init__(self, liberar: threading.Event) -> None:
        self._liberar = liberar

    def __enter__(self) -> _ConexionCongelada:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, *_args: object, **_kwargs: object) -> None:
        self._liberar.wait(5)


class _EngineCongelado:
    def __init__(self) -> None:
        self.liberar = threading.Event()

    def connect(self) -> _ConexionCongelada:
        return _ConexionCongelada(self.liberar)


class _ClienteRedisCongelado:
    """Gemelo de `_EngineCongelado` para la cola (L-009)."""

    def __init__(self) -> None:
        self.liberar = threading.Event()

    def ping(self) -> bool:
        self.liberar.wait(5)
        return True


def test_salud_degradada_por_base_congelada_lleva_el_request_id_del_pedido(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F1 (rompedor, vuelta 2): con la base CONGELADA (el caso F13), la línea
    `salud_degradada` perdía el `request_id` del pedido porque el hilo de
    afuera de `_ejecutar_verificaciones_en_paralelo` no hereda la
    `ContextVar` (L-015). En el 1c sí lo llevaba."""
    from proptech_api import salud
    from proptech_api.app import crear_app
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    engine = _EngineCongelado()
    app = crear_app()
    app.dependency_overrides[salud.obtener_verificador_de_base] = (
        lambda: salud._verificador_con_engine(engine)  # type: ignore[arg-type]
    )
    app.dependency_overrides[salud.obtener_verificador_de_cola] = lambda: lambda: True
    rid = "03a1ce5b-1111-4111-8111-111111111111"

    try:
        respuesta = TestClient(app).get("/api/salud", headers={"X-Request-ID": rid})
    finally:
        engine.liberar.set()
        time.sleep(0.3)  # margen para que el hilo colgado se libere y salga.

    assert respuesta.status_code == 503
    salida = capsys.readouterr()
    lineas_degradadas = [linea for linea in salida.out.splitlines() if "salud_degradada" in linea]
    assert len(lineas_degradadas) == 1, lineas_degradadas
    assert rid in lineas_degradadas[0], lineas_degradadas[0]


def test_salud_degradada_por_cola_congelada_lleva_el_request_id_del_pedido(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Gemelo del anterior para la cola (L-009)."""
    from proptech_api import salud
    from proptech_api.app import crear_app
    from proptech_core.compartido.logs import configurar_logs

    configurar_logs("api")
    cliente_redis = _ClienteRedisCongelado()
    app = crear_app()
    app.dependency_overrides[salud.obtener_verificador_de_base] = lambda: lambda: True
    app.dependency_overrides[salud.obtener_verificador_de_cola] = (
        lambda: salud._verificador_con_cliente_redis(cliente_redis)  # type: ignore[arg-type]
    )
    rid = "14b2df6c-2222-4222-8222-222222222222"

    try:
        respuesta = TestClient(app).get("/api/salud", headers={"X-Request-ID": rid})
    finally:
        cliente_redis.liberar.set()
        time.sleep(0.3)

    assert respuesta.status_code == 503
    salida = capsys.readouterr()
    lineas_degradadas = [linea for linea in salida.out.splitlines() if "salud_degradada" in linea]
    assert len(lineas_degradadas) == 1, lineas_degradadas
    assert rid in lineas_degradadas[0], lineas_degradadas[0]


class _VerificadorQueNuncaInformaPorSuCuenta:
    """F6/D5: simula EXACTAMENTE la carrera perdida que el rompedor del 1d
    reprodujo contra `GET /api/salud` (1 de 18, y hasta 14 de 30 en esta
    máquina, ver tasks.md 5.1): un verificador que devuelve `False` sin
    haber llamado nunca a `_informar_una_sola_vez` — el caso en que el
    hilo interno todavía no llegó a su propio camino de "informar" cuando
    el de afuera ya decidió darse por vencido. Expone `lock`/`informado`/
    `dependencia` con la MISMA forma que `_verificador_con_engine` para que
    el código de producción (si ya tiene el arreglo de D5) pueda usarlos."""

    def __init__(self, dependencia: str) -> None:
        self.lock = threading.Lock()
        self.informado: list[bool] = [False]
        self.dependencia = dependencia

    def __call__(self) -> bool:
        return False


def test_f6_ninguna_respuesta_503_sale_sin_su_linea_salud_degradada() -> None:
    """D5: antes de este arreglo, `_ejecutar_verificaciones_en_paralelo` no
    hacía nada con un verificador que devuelve `False` sin haber informado
    — el 503 salía igual, sin ninguna línea. Esta es la versión
    DETERMINISTA del escenario que 5.1 reprodujo con una ráfaga: no depende
    de ganar una carrera de timing, fuerza el caso directamente."""
    import logging

    _logger = logging.getLogger("proptech_api.salud")
    registro: list[logging.LogRecord] = []

    class _Capturador(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            registro.append(record)

    capturador = _Capturador()
    _logger.addHandler(capturador)
    nivel_anterior = _logger.level
    _logger.setLevel(logging.DEBUG)
    try:
        verificador_base = _VerificadorQueNuncaInformaPorSuCuenta("base")
        cliente = _cliente_con_verificadores(verificador_base, lambda: True)
        respuesta = cliente.get("/api/salud")
    finally:
        _logger.removeHandler(capturador)
        _logger.setLevel(nivel_anterior)

    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "sin_conexion", "cola": "ok"}

    degradadas = [r for r in registro if r.getMessage() == "salud_degradada"]
    assert len(degradadas) == 1, (
        f"se esperaba exactamente 1 línea salud_degradada (ni 0 ni 2), hubo {len(degradadas)}"
    )
    assert degradadas[0].dependencia == "base"  # type: ignore[attr-defined]


def test_f6_la_cola_tambien_queda_cubierta() -> None:
    """Triangulación: el mismo escenario del test anterior pero con la
    dependencia `cola`, para que el arreglo no quede atado sólo a `base`."""
    import logging

    _logger = logging.getLogger("proptech_api.salud")
    registro: list[logging.LogRecord] = []

    class _Capturador(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            registro.append(record)

    capturador = _Capturador()
    _logger.addHandler(capturador)
    nivel_anterior = _logger.level
    _logger.setLevel(logging.DEBUG)
    try:
        verificador_cola = _VerificadorQueNuncaInformaPorSuCuenta("cola")
        cliente = _cliente_con_verificadores(lambda: True, verificador_cola)
        respuesta = cliente.get("/api/salud")
    finally:
        _logger.removeHandler(capturador)
        _logger.setLevel(nivel_anterior)

    assert respuesta.status_code == 503
    assert respuesta.json() == {"estado": "degradado", "base": "ok", "cola": "sin_conexion"}

    degradadas = [r for r in registro if r.getMessage() == "salud_degradada"]
    assert len(degradadas) == 1
    assert degradadas[0].dependencia == "cola"  # type: ignore[attr-defined]


def test_head_responde_200_igual_que_get() -> None:
    """Tarea 2c 5.3 (`entorno-de-ejecucion` > "Respuesta de la web y de la
    API"): un HEAD a /api/salud tiene que responder como el GET (mismo
    código, sin depender de que el proxy lo arregle: si la ruta de FastAPI
    no acepta HEAD, el 405 llega igual por Caddy)."""
    cliente = _cliente_con_verificadores(lambda: True, lambda: True)
    respuesta = cliente.head("/api/salud")
    assert respuesta.status_code == 200
    # Sin aserto sobre el cuerpo: `TestClient` descarta el cuerpo de todo
    # HEAD, así que `content == b""` no podía dar rojo (C2V2-4).
