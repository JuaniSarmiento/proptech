"""Paso de roles de PostgreSQL (D1, D2, D9, cambio 2a).

Hoy la base tiene un solo rol (el de arranque, superusuario de la imagen
oficial de PostgreSQL). Este módulo crea y repara los otros tres con un
trabajo cada uno, siempre con el rol de arranque:

- `proptech_migrador`: dueño de las tablas de dominio, corre Alembic.
- `proptech_app`: la usan la API y el worker; sin ser dueño de nada.
- `proptech_respaldo`: sólo lee, para `pg_dump` (`BYPASSRLS` + `pg_read_all_data`).

`antes()` corre ANTES de Alembic (D2): crea los roles si no existen, fija sus
atributos y contraseña en cada corrida (así una corrida repara un rol tocado
a mano), le da `CREATE` sobre `public` al migrador, le transfiere lo que el
rol de arranque haya creado hasta ahora (salvo `auditoria`, que es del rol de
arranque a propósito, D9) y otorga a la app los permisos de D1 sobre lo que
ya existe — los `DEFAULT PRIVILEGES` (que también fija) sólo cubren lo que se
cree de ahora en más, nunca lo que ya estaba ahí.

`despues()` corre DESPUÉS de Alembic (D2, D9, tarea 6.1): transfiere
`auditoria` (creada por el migrador en la migración `0004`) de vuelta al rol
de arranque, y le revoca a la app el `UPDATE`/`DELETE`/`TRUNCATE` que
`ALTER DEFAULT PRIVILEGES` le regaló por ser una tabla nueva del migrador,
dejándole sólo `SELECT, INSERT` (D9). Antes de la 6.1 (la tabla todavía no
existe), no hace nada.

CLI: `python -m proptech_core.compartido.roles antes|despues`.
"""

from __future__ import annotations

import sys

import psycopg
from psycopg import sql

from proptech_core.compartido.configuracion import (
    ConfiguracionDeAppSoloPostgres,
    ConfiguracionDeArranque,
    ConfiguracionDelMigrador,
    ConfiguracionDeRespaldo,
    ConfiguracionInvalida,
    _ConfiguracionPostgresBase,
)

#: Nunca se reasigna aunque exista (D9): es del rol de arranque a propósito.
_TABLA_EXCLUIDA_DE_LA_REASIGNACION = "auditoria"
#: El migrador nunca necesita tocarla (es bookkeeping de Alembic mismo).
_TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP = frozenset({"alembic_version", "auditoria"})


def _conectar(configuracion: ConfiguracionDeArranque) -> psycopg.Connection:
    """Conecta con el rol de arranque. La contraseña real sale de `URL.password`,
    nunca del método de `SecretStr` que D18 limita a `configuracion.py` y
    `conexion_redis.py`: `url_sqlalchemy()` ya resolvió el secreto adentro."""
    url = configuracion.url_sqlalchemy()
    return psycopg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname=url.database,
        autocommit=False,
    )


def _crear_rol_si_no_existe(cur: psycopg.Cursor, nombre: str) -> None:
    """`CREATE ROLE IF NOT EXISTS` no existe en PostgreSQL (D2): el `DO $$`
    chequea el catálogo él mismo antes de crear."""
    cur.execute(
        sql.SQL(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {nombre}) THEN "
            "CREATE ROLE {rol}; "
            "END IF; "
            "END $$;"
        ).format(nombre=sql.Literal(nombre), rol=sql.Identifier(nombre))
    )


def _password_real(configuracion: _ConfiguracionPostgresBase) -> str:
    """El campo es obligatorio (D3): nunca es `None` en la práctica. `URL.password`
    lo tipa `str | None` porque una URL de SQLAlchemy en general puede no
    llevar contraseña; acá siempre la lleva."""
    password = configuracion.url_sqlalchemy().password
    if password is None:
        raise ValueError("la configuración no tiene contraseña (no debería pasar, D3)")
    return password


def _fijar_atributos_y_password(
    cur: psycopg.Cursor, nombre: str, password: str, *, bypassrls: bool
) -> None:
    """Fija los atributos de D1 y la contraseña en CADA corrida (no sólo al
    crear): así repara un rol que alguien tocó a mano. La contraseña va como
    `sql.Literal`, nunca interpolada a mano (L-007): una comilla simple en la
    contraseña queda escapada correctamente."""
    atributo_bypass = sql.SQL("BYPASSRLS") if bypassrls else sql.SQL("NOBYPASSRLS")
    cur.execute(
        sql.SQL(
            "ALTER ROLE {rol} LOGIN NOSUPERUSER {bypass} "
            "NOCREATEROLE NOCREATEDB PASSWORD {password};"
        ).format(
            rol=sql.Identifier(nombre),
            bypass=atributo_bypass,
            password=sql.Literal(password),
        )
    )


def _asegurar_membresia_pg_read_all_data(cur: psycopg.Cursor, nombre: str) -> None:
    """`GRANT rol TO rol` es idempotente: re-otorgar una membresía que ya
    existe no da error (a lo sumo una NOTICE), así que no necesita el chequeo
    `IF NOT EXISTS` que sí hace falta para crear un rol."""
    cur.execute(sql.SQL("GRANT pg_read_all_data TO {rol};").format(rol=sql.Identifier(nombre)))


def _otorgar_create_al_migrador(cur: psycopg.Cursor, migrador: str) -> None:
    """Sin esto, el migrador no puede `CREATE TABLE` en `public` (punto 1 del
    arquitecto, D2)."""
    cur.execute(
        sql.SQL("GRANT CREATE, USAGE ON SCHEMA public TO {migrador};").format(
            migrador=sql.Identifier(migrador)
        )
    )


def _otorgar_usage_a_la_app_sobre_el_esquema(cur: psycopg.Cursor, app: str) -> None:
    cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {app};").format(app=sql.Identifier(app)))


def _tablas_de_public_del_rol(cur: psycopg.Cursor, rol: str) -> list[str]:
    cur.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner = %s",
        (rol,),
    )
    return [fila[0] for fila in cur.fetchall()]


def _secuencias_de_public_del_rol(cur: psycopg.Cursor, rol: str) -> list[str]:
    """Nunca las secuencias LIGADAS a una columna (`GENERATED ... AS IDENTITY`,
    o el viejo `serial`): `pg_depend` con `deptype IN ('a', 'i')` (vuelta 2,
    R1, cambio 2a). `ALTER TABLE ... OWNER TO` ya les cambia el dueño junto
    con la tabla, y `ALTER SEQUENCE ... OWNER TO` sobre una de éstas falla
    con "cannot change owner of sequence ...: Sequence is linked to table",
    sin importar quién sea el rol destino — es justo lo que le pasó a
    `auditoria_id_seq` (identity) al correr `antes()` después de la 6.1: el
    rol de arranque es su dueño (D9), y antes esta función la devolvía igual
    para que `_reasignar_duenio_de_lo_existente` intentara reasignarla."""
    cur.execute(
        "SELECT s.relname FROM pg_class s "
        "JOIN pg_namespace n ON n.oid = s.relnamespace "
        "WHERE s.relkind = 'S' AND n.nspname = 'public' "
        "AND s.relowner = (SELECT oid FROM pg_roles WHERE rolname = %s) "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM pg_depend d "
        "  WHERE d.objid = s.oid AND d.classid = 'pg_class'::regclass "
        "  AND d.deptype IN ('a', 'i')"
        ")",
        (rol,),
    )
    return [fila[0] for fila in cur.fetchall()]


def _reasignar_duenio_de_lo_existente(cur: psycopg.Cursor, arranque: str, migrador: str) -> None:
    """Le transfiere al migrador cada tabla y secuencia de `public` que hoy es
    del rol de arranque, salvo `auditoria` (D9): nunca `REASSIGN OWNED`, que
    se llevaría objetos fuera del proyecto si el rol de arranque tuviera algo
    más (L-006). La lista sale del catálogo, nunca a mano."""
    for tabla in _tablas_de_public_del_rol(cur, arranque):
        if tabla == _TABLA_EXCLUIDA_DE_LA_REASIGNACION:
            continue
        cur.execute(
            sql.SQL("ALTER TABLE {tabla} OWNER TO {migrador};").format(
                tabla=sql.Identifier(tabla), migrador=sql.Identifier(migrador)
            )
        )
    for secuencia in _secuencias_de_public_del_rol(cur, arranque):
        cur.execute(
            sql.SQL("ALTER SEQUENCE {secuencia} OWNER TO {migrador};").format(
                secuencia=sql.Identifier(secuencia), migrador=sql.Identifier(migrador)
            )
        )


def _tablas_de_public(cur: psycopg.Cursor) -> list[str]:
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    return [fila[0] for fila in cur.fetchall()]


def _secuencias_de_public(cur: psycopg.Cursor) -> list[str]:
    cur.execute("SELECT sequencename FROM pg_sequences WHERE schemaname = 'public'")
    return [fila[0] for fila in cur.fetchall()]


def _otorgar_permisos_explicitos_a_la_app(cur: psycopg.Cursor, app: str) -> None:
    """`ALTER DEFAULT PRIVILEGES` (que `_fijar_default_privileges_para_la_app`
    deja puesto) sólo cubre lo que se cree DESPUÉS: una tabla que ya existía
    cuando `antes()` corre por primera vez (como `trabajos_hechos`, creada
    antes de este cambio) necesita el `GRANT` explícito, sin el cual la app
    recibe "permission denied" aunque esos DEFAULT PRIVILEGES ya estén
    (punto 2 del arquitecto, D2)."""
    for tabla in _tablas_de_public(cur):
        if tabla in _TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP:
            continue
        cur.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO {app};").format(
                tabla=sql.Identifier(tabla), app=sql.Identifier(app)
            )
        )
    for secuencia in _secuencias_de_public(cur):
        cur.execute(
            sql.SQL("GRANT USAGE, SELECT ON {secuencia} TO {app};").format(
                secuencia=sql.Identifier(secuencia), app=sql.Identifier(app)
            )
        )


def _fijar_default_privileges_para_la_app(cur: psycopg.Cursor, migrador: str, app: str) -> None:
    """Para las tablas y secuencias que el migrador cree de ahora en más."""
    cur.execute(
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE {migrador} IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app};"
        ).format(migrador=sql.Identifier(migrador), app=sql.Identifier(app))
    )
    cur.execute(
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE {migrador} IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO {app};"
        ).format(migrador=sql.Identifier(migrador), app=sql.Identifier(app))
    )


def antes(configuracion: ConfiguracionDeArranque) -> None:
    """El paso `antes` de D2, en una sola transacción."""
    migrador = ConfiguracionDelMigrador()
    app = ConfiguracionDeAppSoloPostgres()
    respaldo = ConfiguracionDeRespaldo()

    conexion = _conectar(configuracion)
    try:
        with conexion.cursor() as cur:
            # Paso 1: crear los tres roles si no existen.
            _crear_rol_si_no_existe(cur, migrador.postgres_user)
            _crear_rol_si_no_existe(cur, app.postgres_user)
            _crear_rol_si_no_existe(cur, respaldo.postgres_user)

            # Paso 2: atributos, contraseña y membresía, siempre (repara lo tocado a mano).
            _fijar_atributos_y_password(
                cur, migrador.postgres_user, _password_real(migrador), bypassrls=False
            )
            _fijar_atributos_y_password(
                cur, app.postgres_user, _password_real(app), bypassrls=False
            )
            _fijar_atributos_y_password(
                cur, respaldo.postgres_user, _password_real(respaldo), bypassrls=True
            )
            _asegurar_membresia_pg_read_all_data(cur, respaldo.postgres_user)

            # Paso 3: permisos sobre el esquema.
            _otorgar_create_al_migrador(cur, migrador.postgres_user)
            _otorgar_usage_a_la_app_sobre_el_esquema(cur, app.postgres_user)

            # Paso 4: transferir al migrador lo que el rol de arranque haya creado.
            _reasignar_duenio_de_lo_existente(
                cur, configuracion.postgres_user, migrador.postgres_user
            )

            # Paso 5: permisos explícitos de la app sobre lo que ya existe.
            _otorgar_permisos_explicitos_a_la_app(cur, app.postgres_user)

            # Paso 6: default privileges para lo que el migrador cree de ahora en más.
            _fijar_default_privileges_para_la_app(cur, migrador.postgres_user, app.postgres_user)
        conexion.commit()
    except BaseException:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def _existe_tabla(cur: psycopg.Cursor, tabla: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (tabla,))
    fila = cur.fetchone()
    return fila is not None and bool(fila[0])


def _funciones_de_los_triggers_de(cur: psycopg.Cursor, tabla: str) -> list[str]:
    """Por catálogo, nunca un nombre fijo (R2, vuelta 2): toda función que
    dispara un trigger de `tabla` hoy. Si mañana se suma otro trigger con
    otra función, `despues()` la transfiere igual sin tocar este módulo."""
    cur.execute(
        "SELECT DISTINCT p.proname FROM pg_trigger t "
        "JOIN pg_proc p ON p.oid = t.tgfoid "
        "WHERE t.tgrelid = %s::regclass AND NOT t.tgisinternal",
        (tabla,),
    )
    return [fila[0] for fila in cur.fetchall()]


def despues(configuracion: ConfiguracionDeArranque) -> None:
    """El paso `despues` de D2 (D9): transfiere `auditoria` de vuelta al rol
    de arranque (la crea el migrador en la migración `0004`, de paso) y ajusta
    los permisos de la app sobre ella.

    El migrador nunca queda como dueño de `auditoria`: así no puede
    `DISABLE TRIGGER` ni `NO FORCE ROW LEVEL SECURITY` (requieren ser dueño),
    aunque el trigger de todos modos bloquea `UPDATE`/`DELETE`/`TRUNCATE`
    para cualquier rol, dueño incluido.

    El `REVOKE` explícito es necesario, no decorativo: `ALTER DEFAULT
    PRIVILEGES` (que fija `antes()`) le da a `proptech_app`
    `SELECT, INSERT, UPDATE, DELETE` sobre *cualquier* tabla nueva del
    migrador — incluida `auditoria` — sin importar qué `GRANT` explícito
    haga la migración (`ayudas_rls.aislar_por_administracion` ahí sólo pide
    `SELECT, INSERT`). D9 exige que la app NO tenga `UPDATE`/`DELETE`/`TRUNCATE`
    sobre `auditoria`; sin este `REVOKE`, los tiene igual, de regalo.

    Antes de la tarea 6.1 (migración `0004_auditoria` todavía no corrida),
    `auditoria` no existe: no hay nada que hacer, y se vuelve sin error (así
    `infra/compose.yaml`, cableado desde la tarea 2.3, no tiene que cambiar).
    """
    app = ConfiguracionDeAppSoloPostgres()

    conexion = _conectar(configuracion)
    try:
        with conexion.cursor() as cur:
            if not _existe_tabla(cur, "auditoria"):
                return

            cur.execute(
                sql.SQL("ALTER TABLE auditoria OWNER TO {arranque};").format(
                    arranque=sql.Identifier(configuracion.postgres_user)
                )
            )
            # R2 (vuelta 2): la tabla no alcanza. El bloqueo vive en la
            # FUNCIÓN del trigger, y antes de esto quedaba del migrador —
            # dueño de una función alcanza para reemplazarla
            # (CREATE OR REPLACE) o borrarla (DROP ... CASCADE), que se
            # lleva los triggers con ella. `SET search_path = ''` de
            # paso: la función no usa ningún objeto sin calificar, así que
            # esto no le cambia el comportamiento y cierra la puerta a que
            # alguien la haga resolver algo de un esquema ajeno.
            for funcion in _funciones_de_los_triggers_de(cur, "auditoria"):
                cur.execute(
                    sql.SQL("ALTER FUNCTION {funcion}() OWNER TO {arranque};").format(
                        funcion=sql.Identifier(funcion),
                        arranque=sql.Identifier(configuracion.postgres_user),
                    )
                )
                cur.execute(
                    sql.SQL("ALTER FUNCTION {funcion}() SET search_path = '';").format(
                        funcion=sql.Identifier(funcion)
                    )
                )
            # Orden a propósito: primero el REVOKE amplio (deshace lo que
            # ALTER DEFAULT PRIVILEGES regaló), después el GRANT angosto de
            # D9 — nunca al revés, para no depender de qué vino primero.
            cur.execute(
                sql.SQL("REVOKE UPDATE, DELETE, TRUNCATE ON auditoria FROM {app};").format(
                    app=sql.Identifier(app.postgres_user)
                )
            )
            cur.execute(
                sql.SQL("GRANT SELECT, INSERT ON auditoria TO {app};").format(
                    app=sql.Identifier(app.postgres_user)
                )
            )
        conexion.commit()
    except BaseException:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def _main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("antes", "despues"):
        print("uso: python -m proptech_core.compartido.roles antes|despues", file=sys.stderr)
        return 1

    try:
        configuracion = ConfiguracionDeArranque()
    except ConfiguracionInvalida as error:
        print(str(error), file=sys.stderr)
        return 1

    try:
        if argv[1] == "antes":
            antes(configuracion)
        else:
            despues(configuracion)
    except psycopg.Error as error:
        # El mensaje de psycopg nombra la operación y el objeto, nunca un
        # valor que nosotros le hayamos pasado como literal (L-007): las
        # contraseñas viajan como `sql.Literal`, nunca interpoladas a mano.
        print(f"error en el paso de roles: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
