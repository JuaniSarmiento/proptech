"""DBA-1 (auditoría de cimientos, 22/10/2026, informe `.git/informes-cimientos/03-dba.md`):
el dueño de una tabla de sólo agregar nunca puede ser `proptech_migrador`.

`test_catalogo_rls.py` (línea 243 en adelante) controla los GRANT de la app
(exactamente SELECT/INSERT) y que el trigger bloquee un UPDATE corrido COMO
`proptech_app`; no controla el DUEÑO de la tabla. El discriminante del DBA:
siendo dueño, `proptech_migrador` puede `NO FORCE ROW LEVEL SECURITY` sin que
nadie se lo impida — y de ahí, cualquier lectura/escritura sin pasar por la
política de aislamiento, sin que ninguno de los GRANT de la app (que sólo
limitan a `proptech_app`) lo roce.

`ALTER TABLE ... DISABLE TRIGGER ALL` (la sonda obvia) NO sirve como
discriminante: cualquier tabla con una FK crea triggers internos
(`RI_ConstraintTrigger_*`, `tgisinternal=true`) que Postgres exige
superusuario para desactivar vía `ALL`, sin importar quién sea el dueño — da
"permission denied: ... is a system trigger" tanto para `auditoria` (dueño:
arranque) como para `configuracion_versionada` (dueño: migrador), y esconde
la diferencia real. Confirmado a mano (22/10/2026, Postgres efímero propio)
contra las dos tablas en el mismo esquema real. `NO FORCE ROW LEVEL SECURITY`
no tiene ese problema: lo exige sólo el dueño (o el superusuario), sin
triggers de por medio.

Se controlan DOS tablas, nunca sólo una:

- `auditoria` NO está en `_TABLAS_DE_SOLO_AGREGAR` (tiene su propio
  tratamiento, D9) pero es de sólo agregar igual, y es el control sano: hoy
  su dueño es el rol de arranque (la exclusión de `roles.py:50`,
  `_TABLA_EXCLUIDA_DE_LA_REASIGNACION`), así que este caso tiene que pasar
  en VERDE real. Se suma a mano, con el motivo escrito acá, porque la
  revisión del 22/10/2026 encontró que sin ella el test commiteado no tenía
  ni un caso que pasara ni que protegiera nada: todo el peso recaía en un
  rojo de mutante que sólo se corrió contra un test descartable, nunca
  contra el commit.
- `configuracion_versionada` (la única hoy en `_TABLAS_DE_SOLO_AGREGAR`) da
  éxito, porque su dueño es el migrador (la reasignación general de
  `roles.py:184`, `_reasignar_duenio_de_lo_existente`): ese caso va marcado
  `xfail(strict=True)` hasta que el propose del change 4 decida el dueño
  real (DBA-1, opciones a/b/c del informe).

Cualquier tabla que se agregue a `_TABLAS_DE_SOLO_AGREGAR` queda controlada
por este test sin tocarlo; sólo `configuracion_versionada` lleva el `xfail`,
nombrada por su valor, nunca por posición.
"""

import sys

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.roles import _TABLAS_DE_SOLO_AGREGAR

# `contenedor` se importa para que pytest lo vea como fixture propia de este
# módulo (mismo patrón que usan entre sí los módulos de
# `tests/integracion/`); ruff no reconoce ese uso y marca el import y el
# parámetro de nombre igual como no usados/redefinidos (F401/F811).
# `esquema` NO se importa: este módulo define su propia versión (más abajo),
# que corre `despues()` además de migrar — sin eso, `auditoria` se queda con
# el dueño que le tocó al crearla (el migrador) y nunca se transfiere de
# vuelta al rol de arranque (D9), y el caso `auditoria` no representaría el
# estado realmente protegido.
from .test_catalogo_rls import (  # noqa: F401
    MIGRADOR_PASSWORD,
    MIGRADOR_USER,
    _alembic_env,
    _correr,
    _entorno_de_roles,
    contenedor,
)

pytestmark = pytest.mark.integracion

#: auditoria no está en _TABLAS_DE_SOLO_AGREGAR (D9, tratamiento propio),
#: pero es de sólo agregar igual y es el control sano del discriminante:
#: sumada a mano, con el motivo arriba, para que el test tenga al menos un
#: caso verde real.
_TABLAS_A_CONTROLAR = frozenset({"auditoria"}) | _TABLAS_DE_SOLO_AGREGAR

#: El mensaje exacto que Postgres da ante un `ALTER TABLE ... NO FORCE ROW
#: LEVEL SECURITY` corrido por un rol que no es dueño de la tabla (nunca
#: "cualquier error", mismo criterio que `roles._es_el_bloqueo_esperado`):
#: sin este chequeo de texto, cualquier otro motivo de
#: `InsufficientPrivilege` (un rol sin `USAGE` sobre el esquema, por ejemplo)
#: se confundiría con "no es dueño".
_MENSAJE_DE_NO_SER_DUENIO = "must be owner"


@pytest.fixture(scope="module")
def esquema(contenedor: PostgresContainer) -> None:  # noqa: F811
    """Pipeline real completo, con una SEGUNDA vuelta de `antes()` (sin su
    propio `despues()` todavía) después de migrar y correr la primera
    `despues()`: el mismo escenario que ya cubre `test_roles_solo_agregar.py`
    (D16) para `configuracion_versionada` — el redeploy entra por `antes()`
    antes de que termine su propio `despues()` — y el único punto donde
    `_TABLA_EXCLUIDA_DE_LA_REASIGNACION` hace algo. Sin esta segunda vuelta,
    un mutante que saque a `auditoria` de esa exclusión no cambiaría nada
    acá: `auditoria` no existe todavía cuando la PRIMERA `antes()` corre (la
    crea la migración `0004`), así que la exclusión no tiene nada que hacer
    en esa primera vuelta; recién en la segunda, con `auditoria` ya existente
    y dueña del rol de arranque (gracias a la primera `despues()`), la
    exclusión es lo único que evita que se la devuelvan al migrador.

    Sin `downgrade base` al final, a propósito: después de la segunda
    `antes()` (sin su `despues()` todavía), `auditoria` queda del rol de
    arranque (D9) y el migrador YA NO LA PUEDE `DROP` — `alembic downgrade
    base` corrido como migrador fallaría ahí con `CalledProcessError`, y
    pytest, con el test marcado `xfail`, confunde ese error de TEARDOWN con
    un segundo xfail del mismo test (visto a mano: dos `<skipped>` para un
    solo `<testcase>` en el XML). El contenedor (`contenedor`, módulo-scope)
    se destruye solo al final; no hace falta dejar el esquema limpio antes."""
    entorno = _entorno_de_roles(contenedor)
    roles_cmd = [sys.executable, "-m", "proptech_core.compartido.roles"]
    _correr([*roles_cmd, "antes"], entorno)
    _correr(["uv", "run", "alembic", "upgrade", "head"], _alembic_env(contenedor))
    _correr([*roles_cmd, "despues"], entorno)
    _correr([*roles_cmd, "antes"], entorno)


def _migrador_puede_quitar_el_force_rls(
    contenedor: PostgresContainer,  # noqa: F811
    tabla: str,
) -> bool:
    """True si, conectado como `proptech_migrador`, `NO FORCE ROW LEVEL
    SECURITY` sobre `tabla` tiene éxito. En PostgreSQL sólo el DUEÑO de una
    tabla puede hacer eso, nunca un rol con GRANT por fuera de la propiedad
    (ni siquiera con los cuatro permisos): por eso esta sonda, y no una
    lectura de catálogo, es el discriminante real (DBA-1).

    Corre dentro de su propia transacción y siempre hace ROLLBACK al final,
    gane o pierda la aserción: nunca deja el FORCE real desactivado para el
    resto de la corrida."""
    with psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        dbname=contenedor.dbname,
        user=MIGRADOR_USER,
        password=MIGRADOR_PASSWORD,
        autocommit=False,
    ) as conexion:
        try:
            with conexion.cursor() as cur:
                cur.execute(f'ALTER TABLE "{tabla}" NO FORCE ROW LEVEL SECURITY')
        except psycopg.errors.InsufficientPrivilege as error:
            if _MENSAJE_DE_NO_SER_DUENIO not in str(error):
                raise
            return False
        else:
            return True
        finally:
            conexion.rollback()


@pytest.mark.parametrize(
    "tabla",
    [
        pytest.param(
            tabla,
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    "DBA-1: dueño de las tablas de sólo agregar, "
                    "se decide en el propose del change 4"
                ),
            ),
        )
        if tabla == "configuracion_versionada"
        else tabla
        for tabla in sorted(_TABLAS_A_CONTROLAR)
    ],
)
def test_el_migrador_no_es_dueno_de_las_tablas_de_solo_agregar(
    contenedor: PostgresContainer,  # noqa: F811
    esquema: None,
    tabla: str,
) -> None:
    puede_quitar_force = _migrador_puede_quitar_el_force_rls(contenedor, tabla)
    assert not puede_quitar_force, (
        f"proptech_migrador puede NO FORCE ROW LEVEL SECURITY sobre {tabla}: es su dueño (DBA-1)"
    )
