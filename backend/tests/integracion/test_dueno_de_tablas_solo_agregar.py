"""DBA-1 (auditoría de cimientos, 22/10/2026, informe `.git/informes-cimientos/03-dba.md`):
el dueño de cada tabla de `_TABLAS_DE_SOLO_AGREGAR` nunca puede ser `proptech_migrador`.

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
triggers de por medio, y es universal para cualquier tabla de
`_TABLAS_DE_SOLO_AGREGAR` porque D5 ya exige RLS forzada en todas ellas.

El mismo discriminante, probado a mano por el DBA sobre `auditoria` (que NO
está en `_TABLAS_DE_SOLO_AGREGAR`: tiene su propio tratamiento, D9), da
`must be owner` porque su dueño es el rol de arranque (la exclusión de
`roles.py:50`, `_TABLA_EXCLUIDA_DE_LA_REASIGNACION`). Sobre
`configuracion_versionada` da éxito, porque su dueño es el migrador (la
reasignación general de `roles.py:184`,
`_reasignar_duenio_de_lo_existente`): ese caso va marcado
`xfail(strict=True)` hasta que el propose del change 4 decida el dueño real
(DBA-1, opciones a/b/c del informe). Cualquier tabla que se agregue a
`_TABLAS_DE_SOLO_AGREGAR` queda controlada por este test sin tocarlo: sólo
`configuracion_versionada` lleva el `xfail`, nombrada por su valor, nunca por
posición.
"""

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from proptech_core.compartido.roles import _TABLAS_DE_SOLO_AGREGAR

# `contenedor` y `esquema` se importan para que pytest los vea como fixtures
# propias de este módulo (mismo patrón que usan entre sí los módulos de
# `tests/integracion/`); ruff no reconoce ese uso y marca el import y los
# parámetros de nombre igual como no usados/redefinidos (F401/F811).
from .test_catalogo_rls import (  # noqa: F401
    MIGRADOR_PASSWORD,
    MIGRADOR_USER,
    contenedor,
    esquema,
)

pytestmark = pytest.mark.integracion

#: El mensaje exacto que Postgres da ante un `ALTER TABLE ... NO FORCE ROW
#: LEVEL SECURITY` corrido por un rol que no es dueño de la tabla (nunca
#: "cualquier error", mismo criterio que `roles._es_el_bloqueo_esperado`):
#: sin este chequeo de texto, cualquier otro motivo de
#: `InsufficientPrivilege` (un rol sin `USAGE` sobre el esquema, por ejemplo)
#: se confundiría con "no es dueño".
_MENSAJE_DE_NO_SER_DUENIO = "must be owner"


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
        for tabla in sorted(_TABLAS_DE_SOLO_AGREGAR)
    ],
)
def test_el_migrador_no_es_dueno_de_las_tablas_de_solo_agregar(
    contenedor: PostgresContainer,  # noqa: F811
    esquema: None,  # noqa: F811
    tabla: str,
) -> None:
    puede_quitar_force = _migrador_puede_quitar_el_force_rls(contenedor, tabla)
    assert not puede_quitar_force, (
        f"proptech_migrador puede NO FORCE ROW LEVEL SECURITY sobre {tabla}: es su dueño (DBA-1)"
    )
