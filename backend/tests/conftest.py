"""Fixtures compartidos: PostgreSQL y Redis reales por sesión de pytest
(testcontainers / DockerContainer genérico, D12)."""

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

RAIZ = Path(__file__).resolve().parents[2]
_COMPOSE = RAIZ / "infra" / "compose.yaml"

#: Contraseña sólo para el contenedor de test de Redis; nunca una credencial real.
REDIS_PASSWORD_DE_PRUEBA = "prueba-redis-no-real"

#: Los tres roles reales que crea `roles.antes()` sobre el contenedor de
#: sesión (D1, D2, tarea 2.2): desde que esa tarea cierra, ningún test de
#: integración usa el superusuario del contenedor como alias de otro rol.
MIGRADOR_USER_DE_SESION = "proptech_migrador"
MIGRADOR_PASSWORD_DE_SESION = "clave-migrador-de-sesion-no-real"
APP_USER_DE_SESION = "proptech_app"
APP_PASSWORD_DE_SESION = "clave-app-de-sesion-no-real"
RESPALDO_USER_DE_SESION = "proptech_respaldo"
RESPALDO_PASSWORD_DE_SESION = "clave-respaldo-de-sesion-no-real"


def _leer_imagen_de_compose(servicio: str) -> str:
    datos = yaml.safe_load(_COMPOSE.read_text())
    imagen = datos["services"][servicio]["image"]
    assert isinstance(imagen, str)
    return imagen


IMAGEN_POSTGRES_PARA_TESTS = _leer_imagen_de_compose("db")
IMAGEN_REDIS_PARA_TESTS = _leer_imagen_de_compose("redis")


@pytest.fixture(scope="session")
def postgres_contenedor() -> Iterator[PostgresContainer]:
    # Usuario con el patrón `proptech_[a-z_]{1,40}` (D1, D3, cambio 2a): antes
    # de que el 2.2 cree los cuatro roles reales, este único usuario del
    # contenedor hace de migrador, de app y de respaldo según el test, y las
    # tres configuraciones por rol validan que su nombre cumpla ese patrón.
    # El default de testcontainers ("test") no lo cumple.
    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username="proptech_test",
        password="proptech_test",  # noqa: S106 (contraseña de este contenedor de test, nunca real)
    ) as contenedor:
        yield contenedor


@pytest.fixture(scope="session")
def roles_reales(postgres_contenedor: PostgresContainer) -> None:
    """Corre `roles.antes()` una sola vez por sesión (D1, D2, tarea 2.2), con
    el superusuario del contenedor como rol de arranque: crea los tres roles
    reales (`proptech_migrador`, `proptech_app`, `proptech_respaldo`) con sus
    propias credenciales, distintas de las del contenedor."""
    entorno = {
        **os.environ,
        "POSTGRES_HOST": postgres_contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(postgres_contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": postgres_contenedor.username,
        "POSTGRES_PASSWORD": postgres_contenedor.password,
        "POSTGRES_DB": postgres_contenedor.dbname,
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER_DE_SESION,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD_DE_SESION,
        "POSTGRES_APP_USER": APP_USER_DE_SESION,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD_DE_SESION,
        "POSTGRES_RESPALDO_USER": RESPALDO_USER_DE_SESION,
        "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD_DE_SESION,
    }
    subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ / "backend",
        env=entorno,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def ajustes_del_worker(
    postgres_contenedor: PostgresContainer,
    redis_contenedor: DockerContainer,
    roles_reales: None,
) -> object:
    """Importa `proptech_worker.ajustes` UNA SOLA VEZ por sesión, después de
    fijar las variables de entorno hacia los contenedores de sesión (cambio
    1c, tareas 5.5 a 5.8): el módulo valida la configuración al importarse
    (D11), así que las variables tienen que estar puestas antes del primer
    `import`. Reimportarlo en otro test no vuelve a ejecutar ese código
    (Python cachea el módulo): por eso este fixture es de sesión y los
    contenedores (también de sesión) no cambian de puerto entre tests."""
    import importlib

    parametros_del_repo = RAIZ / "config" / "parametros.yaml"
    os.environ["POSTGRES_HOST"] = postgres_contenedor.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = str(postgres_contenedor.get_exposed_port(5432))
    # `proptech_worker.ajustes` arma su `Configuracion` con el par de la app
    # (D3): desde la tarea 2.2, el rol real que crea `roles_reales`, no el
    # superusuario del contenedor.
    os.environ["POSTGRES_APP_USER"] = APP_USER_DE_SESION
    os.environ["POSTGRES_APP_PASSWORD"] = APP_PASSWORD_DE_SESION
    os.environ["POSTGRES_DB"] = postgres_contenedor.dbname
    os.environ["REDIS_HOST"] = redis_contenedor.get_container_host_ip()
    os.environ["REDIS_PORT"] = str(redis_contenedor.get_exposed_port(6379))
    os.environ["REDIS_PASSWORD"] = REDIS_PASSWORD_DE_PRUEBA
    os.environ["PROPTECH_PARAMETROS"] = str(parametros_del_repo)
    # D7 (2b, tarea 5.4): el worker exige las dos al arrancar; nunca una
    # clave real, nunca contra `api.clerk.com` (los tests del adaptador
    # usan `base_url` propia, nunca esta variable).
    os.environ["CLERK_SECRET_KEY"] = "sk_test_no_real_0000000000000000000000"
    os.environ["PROPTECH_URL_PUBLICA"] = "https://proptech-test.invalid"

    return importlib.import_module("proptech_worker.ajustes")


@pytest.fixture
async def cola_de_prueba_aislada(
    ajustes_del_worker: object,
) -> AsyncIterator[tuple[str, object]]:
    """Una cola con su propio `queue_name` (cambio 1c, tareas 5.5 a 5.8):
    las tests de la sección 4 (`test_cola.py`) encolan `tarea_de_prueba` en
    la cola default del mismo Redis de sesión y nunca corren un worker que
    los drene; sin una cola propia, un burst de estos tests también procesa
    esos trabajos huérfanos y contamina los conteos de eventos."""
    import uuid

    from arq.connections import create_pool

    from proptech_core.compartido.cola import deserializar_job, serializar_job

    nombre_cola = f"arq:queue:test:{uuid.uuid4()}"
    redis_settings = ajustes_del_worker.AjustesDelWorker.redis_settings  # type: ignore[attr-defined]
    pool = await create_pool(
        redis_settings,
        job_serializer=serializar_job,
        job_deserializer=deserializar_job,
        default_queue_name=nombre_cola,
    )

    class _ColaAislada:
        async def encolar(
            self,
            tarea: str,
            *,
            clave: str,
            request_id: str,
            expira_en_s: int | None = None,
            **datos: Any,
        ) -> object:
            from proptech_core.compartido.cola import ResultadoEncolado, validar_datos

            validar_datos(datos)
            resultado = await pool.enqueue_job(
                tarea,
                _job_id=clave,
                _expires=expira_en_s,
                request_id=request_id,
                clave=clave,
                **datos,
            )
            return (
                ResultadoEncolado.YA_ENCOLADO if resultado is None else ResultadoEncolado.ENCOLADO
            )

    try:
        yield nombre_cola, _ColaAislada()
    finally:
        await pool.aclose(close_connection_pool=True)


@pytest.fixture(scope="session")
def esquema_migrado(postgres_contenedor: PostgresContainer, roles_reales: None) -> None:
    """Corre las migraciones a `head` una sola vez por sesión, para los
    tests que necesitan `trabajos_hechos` real (cambio 1c, tareas 5.5 a
    5.8). No hace `downgrade`: los tests que necesitan bajar revisiones usan
    bases propias por módulo; nunca borran este esquema compartido, sin
    importar en qué orden los ejecute pytest."""
    entorno = {
        **os.environ,
        "POSTGRES_HOST": postgres_contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(postgres_contenedor.get_exposed_port(5432)),
        # Alembic corre como el migrador real (D1, D2, tarea 2.2), que
        # `roles_reales` ya creó con `CREATE` sobre `public`.
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER_DE_SESION,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD_DE_SESION,
        "POSTGRES_DB": postgres_contenedor.dbname,
    }
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=RAIZ / "backend",
        env=entorno,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def redis_contenedor() -> Iterator[DockerContainer]:
    """Redis real de sesión (D12), con `--enable-debug-command yes` para que
    4.5 pueda usar `DEBUG SLEEP` (sólo en el contenedor de test, nunca en el
    de Compose). Los tests que detienen o pausan Redis usan su propio
    contenedor de función/módulo, nunca éste (L-006)."""
    contenedor = (
        DockerContainer(IMAGEN_REDIS_PARA_TESTS)
        .with_command(
            f"redis-server --requirepass {REDIS_PASSWORD_DE_PRUEBA} --enable-debug-command yes"
        )
        .with_exposed_ports(6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    with contenedor:
        yield contenedor


# El runner selecciona ci; una invocación directa de pytest puede usar local.
from hypothesis import settings  # noqa: E402

settings.register_profile("ci", derandomize=True, deadline=None)
settings.register_profile("local", deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "local"))
