"""Paso de roles `antes` contra PostgreSQL real (D1, D2, cambio 2a, tarea 2.2).

Contenedor propio (nunca el de sesión, L-006): este módulo crea y altera roles
de verdad, y no queremos que eso le queda pegado a otros tests que comparten
el contenedor de `tests/conftest.py`.

El "rol de arranque" de estos tests es el superusuario con el que arranca el
contenedor (como en un despliegue real, donde `POSTGRES_USER` crea ese rol);
los tres roles nuevos (`proptech_migrador`, `proptech_app`, `proptech_respaldo`)
los crea `roles.antes()` mismo — son roles reales, no un alias del superusuario.

Escenarios de `aislamiento-por-administracion`: Los atributos de cada rol;
Arranque repetido; Volumen anterior a este cambio. Lecciones: L-006, L-007,
L-013.
"""

import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.configuracion import ConfiguracionDeArranque

pytestmark = pytest.mark.integracion

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
RUTA_ROLES = RAIZ_BACKEND / "src" / "proptech_core" / "compartido" / "roles.py"

#: Nombres y contraseñas de los tres roles nuevos para estos tests. Reales
#: (los crea `antes()`), no un alias del superusuario del contenedor.
MIGRADOR_USER = "proptech_migrador"
MIGRADOR_PASSWORD = "clave-migrador-no-real"
APP_USER = "proptech_app"
APP_PASSWORD = "clave-app-no-real"
RESPALDO_USER = "proptech_respaldo"
RESPALDO_PASSWORD = "clave-respaldo-no-real"


@pytest.fixture
def contenedor() -> Iterator[PostgresContainer]:
    from ..conftest import IMAGEN_POSTGRES_PARA_TESTS

    # El rol de arranque de estos tests: el superusuario con el que arranca
    # el contenedor (D1), con un nombre que NO sigue el patrón proptech_* a
    # propósito (como "proptech" en infra/.env.example hoy).
    with PostgresContainer(
        IMAGEN_POSTGRES_PARA_TESTS,
        driver="psycopg",
        username="arranque_de_prueba",
        password="clave-arranque-no-real",  # noqa: S106
    ) as iniciado:
        yield iniciado


def _entorno_de_arranque(contenedor: PostgresContainer) -> dict[str, str]:
    return {
        **os.environ,
        "POSTGRES_HOST": contenedor.get_container_host_ip(),
        "POSTGRES_PORT": str(contenedor.get_exposed_port(5432)),
        "POSTGRES_USER": contenedor.username,
        "POSTGRES_PASSWORD": contenedor.password,
        "POSTGRES_DB": contenedor.dbname,
        "POSTGRES_MIGRADOR_USER": MIGRADOR_USER,
        "POSTGRES_MIGRADOR_PASSWORD": MIGRADOR_PASSWORD,
        "POSTGRES_APP_USER": APP_USER,
        "POSTGRES_APP_PASSWORD": APP_PASSWORD,
        "POSTGRES_RESPALDO_USER": RESPALDO_USER,
        "POSTGRES_RESPALDO_PASSWORD": RESPALDO_PASSWORD,
    }


def _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor: PostgresContainer) -> None:
    """Simula el estado real anterior a este cambio (D2): `alembic_version` y
    `trabajos_hechos` ya existen, creadas por el rol de arranque, antes de que
    exista ningún `proptech_migrador`. DDL directa como el rol de arranque
    (no por Alembic): el nombre de este rol de prueba, a propósito, no sigue
    el patrón `proptech_*` (D1), y pasarlo por `migraciones/env.py` como si
    fuera el migrador chocaría con esa validación sin que tenga que ver con
    lo que este archivo prueba."""
    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            cur.execute("CREATE TABLE alembic_version (version_num varchar(32) NOT NULL)")
            cur.execute(
                "CREATE TABLE trabajos_hechos ("
                "clave text PRIMARY KEY, "
                "tarea text NOT NULL, "
                "request_id uuid NOT NULL, "
                "hecho_en timestamptz NOT NULL DEFAULT now())"
            )
        conexion.commit()


def _conectar_como(
    contenedor: PostgresContainer, usuario: str, password: str
) -> psycopg.Connection:
    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=usuario,
        password=password,
        dbname=contenedor.dbname,
    )


def _atributos_de_rol(cur: psycopg.Cursor, nombre: str) -> dict[str, bool]:
    cur.execute(
        "SELECT rolcanlogin, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
        "FROM pg_roles WHERE rolname = %s",
        (nombre,),
    )
    fila = cur.fetchone()
    assert fila is not None, f"el rol {nombre} no existe"
    return {
        "login": fila[0],
        "super": fila[1],
        "bypassrls": fila[2],
        "createrole": fila[3],
        "createdb": fila[4],
    }


def _es_miembro_de(cur: psycopg.Cursor, rol: str, grupo: str) -> bool:
    cur.execute(
        "SELECT 1 FROM pg_auth_members m "
        "JOIN pg_roles r ON r.oid = m.roleid "
        "JOIN pg_roles u ON u.oid = m.member "
        "WHERE r.rolname = %s AND u.rolname = %s",
        (grupo, rol),
    )
    return cur.fetchone() is not None


def _dueno_de(cur: psycopg.Cursor, tabla: str) -> str:
    cur.execute("SELECT tableowner FROM pg_tables WHERE tablename = %s", (tabla,))
    fila = cur.fetchone()
    assert fila is not None, f"la tabla {tabla} no existe"
    return str(fila[0])


def _correr_antes(contenedor: PostgresContainer) -> None:
    entorno = _entorno_de_arranque(contenedor)
    subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        check=True,
        capture_output=True,
        text=True,
    )


# --- Escenario base: volumen anterior (alembic_version y trabajos_hechos ya existen) ---


def test_atributos_de_cada_rol_y_permisos_sobre_lo_existente(
    contenedor: PostgresContainer,
) -> None:
    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)

    _correr_antes(contenedor)

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            atributos_migrador = _atributos_de_rol(cur, MIGRADOR_USER)
            atributos_app = _atributos_de_rol(cur, APP_USER)
            atributos_respaldo = _atributos_de_rol(cur, RESPALDO_USER)

            assert atributos_migrador == {
                "login": True,
                "super": False,
                "bypassrls": False,
                "createrole": False,
                "createdb": False,
            }
            assert atributos_app == {
                "login": True,
                "super": False,
                "bypassrls": False,
                "createrole": False,
                "createdb": False,
            }
            assert atributos_respaldo == {
                "login": True,
                "super": False,
                "bypassrls": True,
                "createrole": False,
                "createdb": False,
            }
            assert _es_miembro_de(cur, RESPALDO_USER, "pg_read_all_data") is True
            assert _es_miembro_de(cur, APP_USER, "pg_read_all_data") is False
            assert _es_miembro_de(cur, MIGRADOR_USER, "pg_read_all_data") is False

            # Las dos tablas que ya existían pasan a ser del migrador.
            assert _dueno_de(cur, "alembic_version") == MIGRADOR_USER
            assert _dueno_de(cur, "trabajos_hechos") == MIGRADOR_USER

    # El migrador puede crear tablas en public (paso 3: GRANT CREATE).
    with _conectar_como(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD) as conexion:
        with conexion.cursor() as cur:
            cur.execute("CREATE TABLE prueba_migrador_puede_crear (id int)")
            cur.execute("DROP TABLE prueba_migrador_puede_crear")
        conexion.commit()

    # La app tiene permisos explícitos sobre trabajos_hechos, aunque ya
    # existía antes de que corriera `antes` (paso 5, no sólo DEFAULT
    # PRIVILEGES, que sólo cubre objetos futuros).
    with _conectar_como(contenedor, APP_USER, APP_PASSWORD) as conexion:
        with conexion.cursor() as cur:
            cur.execute(
                "INSERT INTO trabajos_hechos (clave, tarea, request_id) "
                "VALUES ('clave-prueba-app', 'tarea-prueba', gen_random_uuid())"
            )
            cur.execute("SELECT clave FROM trabajos_hechos WHERE clave = 'clave-prueba-app'")
            assert cur.fetchone() == ("clave-prueba-app",)
            cur.execute(
                "UPDATE trabajos_hechos SET tarea = 'otra' WHERE clave = 'clave-prueba-app'"
            )
            cur.execute("DELETE FROM trabajos_hechos WHERE clave = 'clave-prueba-app'")
        conexion.commit()


# --- Arranque repetido (idempotencia) ---


def test_segunda_corrida_termina_sin_error_y_con_los_mismos_atributos(
    contenedor: PostgresContainer,
) -> None:
    """Escenario "Volumen anterior a este cambio" (D2, tarea 2.2): un volumen
    del 1d, sin la 0004 (ni ninguna migración real) entre las dos corridas —
    `auditoria` no existe todavía, así que esto por sí solo NUNCA iba a ver
    R1 (vuelta 1 del rompedor/auditor: `auditoria_id_seq`, ligada a la tabla,
    sólo existe después de esa migración). El ciclo completo con la 0004 de
    por medio es `test_un_segundo_ciclo_completo_sobre_el_mismo_volumen_no_falla`,
    más abajo."""
    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)
    _correr_antes(contenedor)

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            antes_1 = _atributos_de_rol(cur, APP_USER)

    _correr_antes(contenedor)  # segunda corrida: no debe fallar

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            antes_2 = _atributos_de_rol(cur, APP_USER)
            assert _dueno_de(cur, "trabajos_hechos") == MIGRADOR_USER

    assert antes_1 == antes_2


def test_un_rol_tocado_a_mano_vuelve_a_quedar_sin_bypassrls(
    contenedor: PostgresContainer,
) -> None:
    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)
    _correr_antes(contenedor)

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            cur.execute(f'ALTER ROLE "{APP_USER}" BYPASSRLS')
        conexion.commit()

    _correr_antes(contenedor)

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            assert _atributos_de_rol(cur, APP_USER)["bypassrls"] is False


def test_password_con_comilla_simple_funciona(contenedor: PostgresContainer) -> None:
    password_con_comilla = "o'brien-no-real"
    entorno = _entorno_de_arranque(contenedor)
    entorno["POSTGRES_APP_PASSWORD"] = password_con_comilla
    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr

    # La contraseña real funciona para conectarse (round-trip: si `sql.Literal`
    # hubiera escapado mal la comilla, la contraseña efectiva sería otra).
    with _conectar_como(contenedor, APP_USER, password_con_comilla):
        pass


def test_ninguna_salida_trae_el_marcador_de_la_contrasena(
    contenedor: PostgresContainer,
) -> None:
    marcador = "marcador-password-9f3c7a"
    entorno = _entorno_de_arranque(contenedor)
    entorno["POSTGRES_APP_PASSWORD"] = marcador
    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)

    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert marcador not in resultado.stdout
    assert marcador not in resultado.stderr


def test_ningun_objeto_fuera_de_public_cambia_de_dueno(contenedor: PostgresContainer) -> None:
    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            cur.execute("CREATE SCHEMA otro_esquema")
            cur.execute("CREATE TABLE otro_esquema.ajena (id int)")
        conexion.commit()

    _correr_antes(contenedor)

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT tableowner FROM pg_tables WHERE schemaname = 'otro_esquema' "
                "AND tablename = 'ajena'"
            )
            fila = cur.fetchone()
            assert fila is not None
            assert fila[0] == contenedor.username


# --- Rojo con una copia del módulo, mutada a propósito (L-013) ---


def _cargar_copia_mutada(nombre_modulo: str, texto_mutado: str) -> object:
    """Carga `texto_mutado` como un módulo nuevo en memoria, sin tocar el
    archivo real ni el módulo ya importado (L-013: comparado por `diff`
    contra el texto real abajo, en cada test que llama a esto)."""
    spec = importlib.util.spec_from_loader(nombre_modulo, loader=None)
    assert spec is not None
    modulo = importlib.util.module_from_spec(spec)
    # L-013: esto SÓLO corre sobre una copia del texto de roles.py mutada por este
    # mismo archivo de test (nunca sobre entrada externa), para ver un rojo real
    # sin mutar el módulo que ya está importado.
    exec(  # noqa: S102
        compile(texto_mutado, f"<copia mutada de {nombre_modulo}>", "exec"), modulo.__dict__
    )
    return modulo


def test_sin_el_grant_create_el_migrador_no_puede_crear_tablas(
    contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rojo de la 2.2 (L-013): una copia de `roles.py` sin el paso que otorga
    `CREATE` sobre `public` al migrador. Mutación y diff contra el texto real,
    mostrados en el informe."""
    texto_real = RUTA_ROLES.read_text(encoding="utf-8")
    marca = "            _otorgar_create_al_migrador(cur, migrador.postgres_user)\n"
    assert marca in texto_real, "la marca del paso 3 no está donde el test la espera"
    texto_mutado = texto_real.replace(
        marca, "            pass  # paso 3 removido a propósito para ver el rojo (L-013)\n"
    )
    assert texto_mutado != texto_real, "el reemplazo no encontró la línea exacta a mutar"

    modulo_mutado = _cargar_copia_mutada("roles_sin_grant_create", texto_mutado)

    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)
    config = _config_de_arranque_para_test(contenedor, monkeypatch)
    modulo_mutado.antes(config)  # type: ignore[attr-defined]

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with _conectar_como(contenedor, MIGRADOR_USER, MIGRADOR_PASSWORD) as conexion:
            with conexion.cursor() as cur:
                cur.execute("CREATE TABLE prueba_sin_create (id int)")
            conexion.commit()


def test_sin_el_grant_explicito_la_app_no_puede_leer_trabajos_hechos_preexistente(
    contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rojo de la 2.2 (L-013): una copia de `roles.py` sin el paso que otorga
    permisos explícitos a la app sobre lo que ya existe. Las `DEFAULT
    PRIVILEGES` (paso 6, que sí queda) no cubren retroactivamente
    `trabajos_hechos`, creada antes de que `antes()` corriera."""
    texto_real = RUTA_ROLES.read_text(encoding="utf-8")
    marca = "            _otorgar_permisos_explicitos_a_la_app(cur, app.postgres_user)\n"
    assert marca in texto_real, "la marca del paso 5 no está donde el test la espera"
    texto_mutado = texto_real.replace(
        marca, "            pass  # paso 5 removido a propósito para ver el rojo (L-013)\n"
    )
    assert texto_mutado != texto_real, "el reemplazo no encontró la línea exacta a mutar"

    modulo_mutado = _cargar_copia_mutada("roles_sin_grant_app", texto_mutado)

    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)
    config = _config_de_arranque_para_test(contenedor, monkeypatch)
    modulo_mutado.antes(config)  # type: ignore[attr-defined]

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with _conectar_como(contenedor, APP_USER, APP_PASSWORD) as conexion:
            with conexion.cursor() as cur:
                cur.execute("SELECT * FROM trabajos_hechos")


def _config_de_arranque_para_test(
    contenedor: PostgresContainer, monkeypatch: pytest.MonkeyPatch
) -> ConfiguracionDeArranque:
    for clave, valor in _entorno_de_arranque(contenedor).items():
        monkeypatch.setenv(clave, valor)
    return ConfiguracionDeArranque()


# --- `despues`, por ahora un no-op documentado (D9, tarea 6.1 lo completa) ---


def test_despues_no_falla_aunque_auditoria_no_exista_todavia(
    contenedor: PostgresContainer,
) -> None:
    _crear_alembic_version_y_trabajos_hechos_como_arranque(contenedor)
    _correr_antes(contenedor)

    entorno = _entorno_de_arranque(contenedor)
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr


# --- Vuelta 2, R1: un segundo ciclo completo sobre la MISMA base no rompe ---
#
# `test_segunda_corrida_termina_sin_error_y_con_los_mismos_atributos` (arriba)
# corre `antes()` dos veces sin que la 0004 exista nunca entre medio (sólo
# fabrica `alembic_version`/`trabajos_hechos` a mano): por eso seguía en
# verde con R1 abierto (hallazgo real del auditor, vuelta 1). Este test corre
# el ciclo REAL — `antes` → `alembic upgrade head` (0001 a 0004, como
# migrador) → `despues` → `antes` otra vez → `despues` otra vez — sobre el
# MISMO volumen, como un reinicio real del servidor (D2, escenario "Arranque
# repetido"). `auditoria_id_seq` (IDENTITY) queda del rol de arranque desde
# el primer `despues()`; sin el filtro de R1, el segundo `antes()` intenta
# `ALTER SEQUENCE auditoria_id_seq OWNER TO proptech_migrador` y Postgres lo
# rechaza porque está ligada a la tabla.


def _entorno_de_alembic(contenedor: PostgresContainer) -> dict[str, str]:
    entorno = dict(_entorno_de_arranque(contenedor))
    for variable in ("REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "PROPTECH_PARAMETROS"):
        entorno.pop(variable, None)
    return entorno


def _correr_alembic_upgrade_head(contenedor: PostgresContainer) -> None:
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=RAIZ_BACKEND,
        env=_entorno_de_alembic(contenedor),
        check=True,
        capture_output=True,
        text=True,
    )


def _correr_despues(contenedor: PostgresContainer) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "despues"],
        cwd=RAIZ_BACKEND,
        env=_entorno_de_arranque(contenedor),
        capture_output=True,
        text=True,
    )


def _correr_antes_sin_check(contenedor: PostgresContainer) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ_BACKEND,
        env=_entorno_de_arranque(contenedor),
        capture_output=True,
        text=True,
    )


def test_un_segundo_ciclo_completo_sobre_el_mismo_volumen_no_falla(
    contenedor: PostgresContainer,
) -> None:
    resultado_antes_1 = _correr_antes_sin_check(contenedor)
    assert resultado_antes_1.returncode == 0, resultado_antes_1.stderr

    _correr_alembic_upgrade_head(contenedor)

    resultado_despues_1 = _correr_despues(contenedor)
    assert resultado_despues_1.returncode == 0, resultado_despues_1.stderr

    # El "reinicio": exactamente lo que vio fallar el rompedor (R1, vuelta 1).
    resultado_antes_2 = _correr_antes_sin_check(contenedor)
    assert resultado_antes_2.returncode == 0, (
        f"stdout={resultado_antes_2.stdout!r} stderr={resultado_antes_2.stderr!r}"
    )
    assert "auditoria_id_seq" not in resultado_antes_2.stderr

    resultado_despues_2 = _correr_despues(contenedor)
    assert resultado_despues_2.returncode == 0, resultado_despues_2.stderr

    with _conectar_como(contenedor, contenedor.username, contenedor.password) as conexion:
        with conexion.cursor() as cur:
            assert _dueno_de(cur, "auditoria") == contenedor.username
            cur.execute(
                "SELECT sequenceowner FROM pg_sequences "
                "WHERE schemaname = 'public' AND sequencename = 'auditoria_id_seq'"
            )
            fila = cur.fetchone()
            assert fila is not None
            assert fila[0] == contenedor.username


# --- Vuelta 2, R8: los cuatro roles (nombre y contraseña) tienen que ser distintos ---


def test_antes_falla_si_dos_usuarios_coinciden(contenedor: PostgresContainer) -> None:
    """Nada impedía que `POSTGRES_APP_USER` fuera igual a
    `POSTGRES_RESPALDO_USER` (los dos cumplen el patrón `proptech_*`): la
    app arrancaría conectada como el rol de respaldo, con `BYPASSRLS`
    (hallazgo real del rompedor, vuelta 1, R8)."""
    entorno = _entorno_de_arranque(contenedor)
    entorno["POSTGRES_APP_USER"] = entorno["POSTGRES_RESPALDO_USER"]
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 1, resultado.stdout
    assert "POSTGRES_APP_USER" in resultado.stderr
    assert "POSTGRES_RESPALDO_USER" in resultado.stderr


def test_antes_falla_si_dos_contrasenas_coinciden(contenedor: PostgresContainer) -> None:
    """Las cuatro contraseñas iguales era justo lo que traía
    `infra/.env.example` (hallazgo real del rompedor, vuelta 1, R8): la API
    arrancaría con la contraseña del superusuario."""
    entorno = _entorno_de_arranque(contenedor)
    password_compartida = entorno["POSTGRES_APP_PASSWORD"]
    entorno["POSTGRES_MIGRADOR_PASSWORD"] = password_compartida
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 1, resultado.stdout
    assert "POSTGRES_APP_PASSWORD" in resultado.stderr
    assert "POSTGRES_MIGRADOR_PASSWORD" in resultado.stderr
    assert password_compartida not in resultado.stderr


def test_antes_rechaza_un_postgres_app_user_que_las_migraciones_no_conocen(
    contenedor: PostgresContainer,
) -> None:
    """V3-14 (2a), tarea 6.2: `ayudas_rls.py` (migraciones) tiene el `GRANT`
    escrito a mano para `proptech_app` (`_ROL_DE_LA_APP`); un
    `POSTGRES_APP_USER` distinto crea igual un rol (con ESE otro nombre),
    pero ningún `GRANT` de una migración futura lo alcanza — antes de esta
    tarea, `antes()` pasaba igual y la falla aparecía recién más tarde (un
    permiso denegado en la API, sin ninguna pista de esto). Nombra la
    variable, nunca el valor: el nombre elegido no aparece en la salida."""
    entorno = _entorno_de_arranque(contenedor)
    entorno["POSTGRES_APP_USER"] = "proptech_otra_app"
    resultado = subprocess.run(
        [sys.executable, "-m", "proptech_core.compartido.roles", "antes"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 1, (
        f"antes() tenía que rechazar el arranque; stdout={resultado.stdout!r}"
    )
    assert "POSTGRES_APP_USER" in resultado.stderr
    assert "proptech_otra_app" not in resultado.stderr
