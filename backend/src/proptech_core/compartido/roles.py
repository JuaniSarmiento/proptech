"""Roles de deploy: antes prepara permisos; después protege las tablas de sólo agregar.

El arranque es dueño de las tablas declaradas en tablas_protegidas y de sus
funciones de bloqueo. El migrador conserva las demás tablas de dominio.
La app sólo recibe SELECT/INSERT sobre las protegidas. Cada transferencia y
verificación del paso posterior corre en una transacción que revierte ante error.
CLI: python -m proptech_core.compartido.roles antes|despues.
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
from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR, TablaProtegida

#: D0/D1: el paso anterior nunca devuelve tablas protegidas al migrador.
_TABLAS_EXCLUIDAS_DE_LA_REASIGNACION = frozenset(TABLAS_DE_SOLO_AGREGAR)
#: El migrador nunca necesita tocarla (es bookkeeping de Alembic mismo).
#: `accion_de_auditoria` (vuelta 2, R3): el vocabulario de D1 es sólo
#: `SELECT` para la app, nunca los cuatro permisos del grant amplio.
_TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP = frozenset(
    {"alembic_version", "auditoria", "accion_de_auditoria"}
)

# D0: conjunto derivado de la declaración única; auditoria conserva su sonda propia.
_TABLAS_DE_SOLO_AGREGAR = frozenset(TABLAS_DE_SOLO_AGREGAR)

#: Revisión final (19/10/2026), arreglo 8: mismo defecto que D9/D16 resolvieron
#: para `auditoria`/`configuracion_versionada`, para una tabla que Alembic
#: mismo crea (no el migrador vía una migración, pero el dueño es igual el
#: migrador) — estar en `_TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP` sólo evita el
#: `GRANT` explícito de `antes()`; los `ALTER DEFAULT PRIVILEGES` igual le dan
#: a la app los cuatro permisos la primera vez que Alembic la crea. La app sí
#: necesita LEERLA (confirmar que las migraciones corrieron); nunca escribirla.
_TABLAS_DE_SOLO_LECTURA_PARA_LA_APP = frozenset({"alembic_version"})


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
    del rol de arranque, salvo las tablas protegidas (D0/D1): nunca `REASSIGN OWNED`, que
    se llevaría objetos fuera del proyecto si el rol de arranque tuviera algo
    más (L-006). La lista sale del catálogo, nunca a mano."""
    for tabla in _tablas_de_public_del_rol(cur, arranque):
        if tabla in _TABLAS_EXCLUIDAS_DE_LA_REASIGNACION:
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
        if tabla in _TABLAS_EXCLUIDAS_DEL_GRANT_A_LA_APP | _TABLAS_DE_SOLO_AGREGAR:
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


class ConfiguracionDeRolesInsegura(Exception):
    """Dos de los cuatro roles (arranque, migrador, app, respaldo) tienen el
    mismo nombre de usuario, o dos de las cuatro tienen la misma contraseña
    (R8, vuelta 2). El mensaje nombra las DOS VARIABLES que colisionan,
    nunca el valor (L-007): con un mismo nombre, la app podría arrancar
    siendo en los hechos el rol de arranque o el de respaldo (`BYPASSRLS`),
    sin que nadie lo note hasta que algo ya pasó."""


#: V3-14 (2a), tarea 6.2: el mismo nombre que `migraciones/ayudas_rls.py`
#: tiene escrito a mano en sus `GRANT` (`_ROL_DE_LA_APP`). Duplicado a
#: propósito, nunca importado: `migraciones` depende de `proptech_core`
#: (ver `migraciones/env.py`), nunca al revés — importar desde acá
#: invertiría esa frontera por una sola constante. Si uno de los dos
#: cambia, el otro se queda desactualizado en silencio; ese riesgo es
#: menor que el de la frontera invertida, y los dos están comentados con
#: una referencia cruzada al otro.
_ROL_DE_LA_APP_QUE_CONOCEN_LAS_MIGRACIONES = "proptech_app"


class NombreDeRolDeLaAppDesconocido(Exception):
    """`POSTGRES_APP_USER` no es el nombre que `migraciones/ayudas_rls.py`
    ya tiene escrito a mano en sus `GRANT` (V3-14, deuda del 2a). Sin este
    chequeo, `antes()` crea igual un rol con el nombre que diga la
    variable, y la falla aparece recién más tarde — un permiso denegado en
    la API o el worker, sin ninguna pista de que el nombre del rol es la
    causa. Nombra la variable, nunca el valor (L-007)."""


def _verificar_rol_de_la_app_conocido(app: ConfiguracionDeAppSoloPostgres) -> None:
    if app.postgres_user != _ROL_DE_LA_APP_QUE_CONOCEN_LAS_MIGRACIONES:
        raise NombreDeRolDeLaAppDesconocido(
            "POSTGRES_APP_USER no es el rol que las migraciones conocen "
            f"(tiene que ser {_ROL_DE_LA_APP_QUE_CONOCEN_LAS_MIGRACIONES!r}, "
            "ver migraciones/ayudas_rls.py)"
        )


def _verificar_sin_colisiones(valores: dict[str, str], que: str) -> None:
    vistas: dict[str, str] = {}
    for variable, valor in valores.items():
        if valor in vistas:
            raise ConfiguracionDeRolesInsegura(
                f"{que} repetida entre {vistas[valor]} y {variable} (D1, R8): "
                "los cuatro roles tienen que ser distintos entre sí"
            )
        vistas[valor] = variable


def _verificar_los_cuatro_roles_son_distintos(
    arranque: ConfiguracionDeArranque,
    migrador: ConfiguracionDelMigrador,
    app: ConfiguracionDeAppSoloPostgres,
    respaldo: ConfiguracionDeRespaldo,
) -> None:
    """Nada impide hoy que `POSTGRES_APP_USER` sea igual a
    `POSTGRES_RESPALDO_USER` (los dos cumplen `^proptech_[a-z_]{1,40}$`), o
    que las cuatro contraseñas sean la misma (el `.env.example` las traía
    así): la app arrancaría conectada como otro rol — con `BYPASSRLS`, o
    directamente con la contraseña del superusuario — sin que `antes()` lo
    note (R8, vuelta 2)."""
    _verificar_sin_colisiones(
        {
            "POSTGRES_USER": arranque.postgres_user,
            "POSTGRES_MIGRADOR_USER": migrador.postgres_user,
            "POSTGRES_APP_USER": app.postgres_user,
            "POSTGRES_RESPALDO_USER": respaldo.postgres_user,
        },
        "nombre de usuario",
    )
    _verificar_sin_colisiones(
        {
            "POSTGRES_PASSWORD": _password_real(arranque),
            "POSTGRES_MIGRADOR_PASSWORD": _password_real(migrador),
            "POSTGRES_APP_PASSWORD": _password_real(app),
            "POSTGRES_RESPALDO_PASSWORD": _password_real(respaldo),
        },
        "contraseña",
    )


def antes(configuracion: ConfiguracionDeArranque) -> None:
    """El paso `antes` de D2, en una sola transacción."""
    migrador = ConfiguracionDelMigrador()
    app = ConfiguracionDeAppSoloPostgres()
    respaldo = ConfiguracionDeRespaldo()

    # Antes de tocar la base (R8, vuelta 2): un chequeo puro, sin ida y
    # vuelta a Postgres, así falla lo más rápido posible.
    _verificar_los_cuatro_roles_son_distintos(configuracion, migrador, app, respaldo)
    # V3-14 (2a), tarea 6.2: ídem, antes de crear un rol con un nombre que
    # ninguna migración va a alcanzar con sus GRANT.
    _verificar_rol_de_la_app_conocido(app)

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


class AuditoriaNoProtegida(Exception):
    """`despues()` terminó sus pasos y, al verificar (R4, vuelta 2, D2: "verifica
    que el trigger y el FORCE sigan activos"), algo de la protección de
    `auditoria` no está. Nombra exactamente qué, nunca pasa en silencio."""


#: Nombres fijos de los dos triggers que crea la migración `0004` (D9): se
#: usan sólo para poder NOMBRAR cuál falta si alguno desaparece; cuáles
#: funciones transferir (R2) sigue saliendo del catálogo, nunca de acá.
_TRIGGERS_ESPERADOS_DE_AUDITORIA = frozenset(
    {"trg_auditoria_sin_update_delete", "trg_auditoria_sin_truncate"}
)


#: V3-2, vuelta 4: el SQLSTATE fijo de un `RAISE EXCEPTION` de PL/pgSQL
#: sin uno propio (D9, migración `0004`) — nunca el de una FK, un
#: `CheckViolation` o cualquier otra cosa que también herede de
#: `psycopg.Error`.
_SQLSTATE_DEL_BLOQUEO_DE_AUDITORIA = "P0001"
_MENSAJE_DEL_BLOQUEO_DE_AUDITORIA = "auditoria no admite"


def _es_el_bloqueo_esperado(error: psycopg.Error) -> bool:
    """V3-2, vuelta 4: antes, `except psycopg.Error: pass` trataba CUALQUIER
    error como "el bloqueo funciona" — el día que algo tenga una FK hacia
    `auditoria` (o cualquier otra razón ajena), un intento bloqueado por esa
    OTRA causa pasaba la verificación sin que el trigger propio hubiera
    hecho nada. Acá se exige el SQLSTATE y el texto exactos del `RAISE
    EXCEPTION` de `fn_auditoria_bloqueada` (migración `0004`), nunca "algún
    error cualquiera"."""
    sqlstate = getattr(error, "sqlstate", None)
    return (
        sqlstate == _SQLSTATE_DEL_BLOQUEO_DE_AUDITORIA
        and _MENSAJE_DEL_BLOQUEO_DE_AUDITORIA in str(error)
    )


def _verificar_bloqueo_de_escritura_de_verdad(cur: psycopg.Cursor) -> list[str]:
    """V2-2(b), vuelta 3; V3-2, vuelta 4: prueba el BLOQUEO, no su forma. El
    catálogo (R2: dueño de la función; R4: nombre y `tgenabled` del
    trigger) no distingue una función reemplazada por una que no hace
    nada, o un trigger recreado con el mismo nombre sobre otro evento
    (`AFTER INSERT ... WHEN (false)` en vez de `BEFORE UPDATE OR DELETE`)
    — en los dos casos el catálogo sigue viéndose "bien". Acá se inserta
    una fila de prueba dentro de un `SAVEPOINT`, se intenta `UPDATE`,
    `DELETE` y `TRUNCATE` de verdad, se exige que los tres fallen CON EL
    ERROR ESPERADO (V3-2: nunca "cualquier error", que podría ser una FK
    ajena bloqueando por una razón distinta), y se revierte todo al final:
    la fila de prueba nunca queda, pase lo que pase."""
    faltantes: list[str] = []

    cur.execute("SELECT nombre FROM accion_de_auditoria LIMIT 1")
    fila_accion = cur.fetchone()
    if fila_accion is None:
        faltantes.append(
            "no se pudo probar el bloqueo de escritura: accion_de_auditoria está vacía"
        )
        return faltantes
    accion = fila_accion[0]

    cur.execute("SAVEPOINT verificacion_bloqueo_auditoria")
    try:
        # El rol de arranque ES superusuario (V3-10, vuelta 4: este
        # comentario decía lo contrario) y bypassea RLS siempre, sin
        # importar `BYPASSRLS` ni `FORCE` — eso no es lo que exige fijar
        # el tenant acá. Se fija de todos modos por prolijidad: la fila de
        # prueba queda con un `administracion_id` real y coherente, en vez
        # de depender de que nadie vuelva a leer este código asumiendo que
        # el `INSERT` necesita sortear una política que, para este rol, ni
        # se aplica. `set_config(..., true)` es local a la transacción
        # (D4) y el `ROLLBACK TO SAVEPOINT` de más abajo también lo revierte.
        cur.execute("SELECT gen_random_uuid()")
        fila_tenant = cur.fetchone()
        if fila_tenant is None:
            faltantes.append("no se pudo generar el tenant de prueba para verificar el bloqueo")
            return faltantes
        tenant_de_prueba = str(fila_tenant[0])
        cur.execute("SELECT set_config('app.administracion_id', %s, true)", (tenant_de_prueba,))
        cur.execute(
            "INSERT INTO auditoria "
            "(administracion_id, persona_id, accion, entidad, entidad_id, request_id) "
            "VALUES (%s, gen_random_uuid(), %s, 'verificacion_de_despues', "
            "gen_random_uuid(), gen_random_uuid()) RETURNING id",
            (tenant_de_prueba, accion),
        )
        fila_id = cur.fetchone()
        if fila_id is None:
            faltantes.append("no se pudo insertar la fila de prueba para verificar el bloqueo")
            return faltantes
        id_de_prueba = fila_id[0]

        intentos = (
            ("UPDATE auditoria SET entidad = 'x' WHERE id = %s", "UPDATE", True),
            ("DELETE FROM auditoria WHERE id = %s", "DELETE", True),
            # TRUNCATE es por sentencia, no por fila: no necesita el id de
            # prueba, pero sí corre dentro del mismo SAVEPOINT para no
            # perder la fila.
            ("TRUNCATE auditoria", "TRUNCATE", False),
        )
        for sentencia, nombre, con_id in intentos:
            cur.execute("SAVEPOINT intento_de_escritura")
            try:
                cur.execute(sentencia, (id_de_prueba,) if con_id else None)
            except psycopg.Error as error:
                if not _es_el_bloqueo_esperado(error):
                    faltantes.append(
                        f"no se pudo probar el bloqueo de {nombre}: "
                        f"un error distinto del esperado lo frenó "
                        f"(SQLSTATE {error.sqlstate}), nunca confirmado como el bloqueo real"
                    )
            else:
                faltantes.append(f"auditoria admite {nombre} (el bloqueo no funciona)")
            finally:
                cur.execute("ROLLBACK TO SAVEPOINT intento_de_escritura")
                cur.execute("RELEASE SAVEPOINT intento_de_escritura")
    finally:
        cur.execute("ROLLBACK TO SAVEPOINT verificacion_bloqueo_auditoria")
        cur.execute("RELEASE SAVEPOINT verificacion_bloqueo_auditoria")

    return faltantes


#: V3-1, vuelta 4: exactamente lo que `ayudas_rls.aislar_por_administracion`
#: genera para `auditoria` (columna `administracion_id`), confirmado contra
#: Postgres real con `pg_get_expr`: la forma que Postgres devuelve normaliza
#: los casts (`::text`) que el SQL original no escribe explícitos.
_CONDICION_ESPERADA_DE_LA_POLITICA_DE_AUDITORIA = (
    "(administracion_id = (NULLIF(current_setting('app.administracion_id'::text, true), "
    "''::text))::uuid)"
)


def _verificar_politica_de_auditoria(cur: psycopg.Cursor) -> list[str]:
    """V3-1, vuelta 4: compara el CONJUNTO ENTERO de políticas de
    `auditoria` contra lo esperado — nunca una lista de cosas prohibidas,
    que deja pasar cualquier política nueva que alguien agregue a mano
    (una política PERMISIVA extra abre la tabla igual aunque la original
    siga intacta: las permisivas se combinan con OR, hallazgo real del
    rompedor en la vuelta 3). `ALTER POLICY ... USING (true)` deja el
    nombre y la forma intactos y sólo cambia la condición: por eso la
    comparación es por `qual`/`with_check` exactos, no sólo "¿existe una
    política con este nombre?"."""
    faltantes: list[str] = []
    cur.execute(
        "SELECT polname, polpermissive, polcmd, polroles, "
        "pg_get_expr(polqual, polrelid), pg_get_expr(polwithcheck, polrelid) "
        "FROM pg_policy WHERE polrelid = 'auditoria'::regclass"
    )
    filas = cur.fetchall()
    if len(filas) != 1:
        nombres = sorted(str(fila[0]) for fila in filas)
        faltantes.append(
            f"auditoria tiene {len(filas)} políticas ({', '.join(nombres) or 'ninguna'}), "
            "se esperaba exactamente 1"
        )
        return faltantes

    nombre, permisiva, comando, roles, qual, with_check = filas[0]
    if nombre != "auditoria_por_administracion":
        faltantes.append(
            f"la política de auditoria se llama {nombre!r}, "
            "se esperaba 'auditoria_por_administracion'"
        )
    if permisiva is not True:
        faltantes.append("la política de auditoria no es PERMISSIVE")
    if comando != "*":
        faltantes.append(
            f"la política de auditoria es sólo para el comando {comando!r}, "
            "se esperaba todos los comandos ('*')"
        )
    if roles not in (None, [0]):
        faltantes.append(f"la política de auditoria no es para PUBLIC (polroles={roles!r})")
    if qual != _CONDICION_ESPERADA_DE_LA_POLITICA_DE_AUDITORIA:
        faltantes.append(f"el USING de la política de auditoria no es el esperado (es: {qual!r})")
    if with_check != _CONDICION_ESPERADA_DE_LA_POLITICA_DE_AUDITORIA:
        faltantes.append(
            f"el WITH CHECK de la política de auditoria no es el esperado (es: {with_check!r})"
        )
    return faltantes


def _verificar_auditoria_protegida(cur: psycopg.Cursor, arranque: str) -> None:
    """Al final de `despues()` (R4, vuelta 2; V2-2, vuelta 3): el `FORCE`,
    el RLS encendido, los dos triggers (habilitados) y el dueño de sus
    funciones por catálogo, MÁS el bloqueo de escritura probado de verdad
    (`_verificar_bloqueo_de_escritura_de_verdad`, porque el catálogo por sí
    solo no distingue un bloqueo real de uno con la forma correcta pero
    neutralizado). `despues()` no RECREA nada si falta (eso es tocar
    `auditoria`, y D9/D11 dicen que eso pasa por el paso de roles, no en
    silencio dentro de él) — sólo deja de pasar por alto que alguien lo
    desarmó."""
    faltantes: list[str] = []

    cur.execute(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
        "WHERE relname = 'auditoria' AND relnamespace = 'public'::regnamespace"
    )
    fila_rls = cur.fetchone()
    if fila_rls is None or not fila_rls[0]:
        # V2-2(a), vuelta 3: con `relrowsecurity=false` la política no se
        # aplica a NADIE (ni siquiera a la app, que no tiene BYPASSRLS),
        # `FORCE` da igual activo o no — rompe "Auditoría de otra
        # administración" sin tocar el `FORCE` para nada.
        faltantes.append("ROW LEVEL SECURITY (relrowsecurity) en auditoria")
    if fila_rls is None or not fila_rls[1]:
        faltantes.append("FORCE ROW LEVEL SECURITY en auditoria")

    cur.execute(
        "SELECT tgname, tgenabled FROM pg_trigger "
        "WHERE tgrelid = 'auditoria'::regclass AND NOT tgisinternal"
    )
    triggers = {fila[0]: fila[1] for fila in cur.fetchall()}
    for nombre in sorted(_TRIGGERS_ESPERADOS_DE_AUDITORIA - triggers.keys()):
        faltantes.append(f"el trigger {nombre} (no existe)")
    for nombre, habilitado in sorted(triggers.items()):
        if habilitado != "O":
            faltantes.append(f"el trigger {nombre} (deshabilitado)")

    for funcion in _funciones_de_los_triggers_de(cur, "auditoria"):
        cur.execute("SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE proname = %s", (funcion,))
        fila_dueno = cur.fetchone()
        if fila_dueno is None or fila_dueno[0] != arranque:
            dueno_real = fila_dueno[0] if fila_dueno is not None else "(no existe)"
            faltantes.append(f"el dueño de la función {funcion} (es {dueno_real})")

    faltantes.extend(_verificar_politica_de_auditoria(cur))
    faltantes.extend(_verificar_bloqueo_de_escritura_de_verdad(cur))

    if faltantes:
        raise AuditoriaNoProtegida(
            "la protección de auditoria no se pudo confirmar: " + "; ".join(faltantes)
        )


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


def _verificar_tabla_protegida(
    cur: psycopg.Cursor, tabla: str, declaracion: TablaProtegida, arranque: str
) -> None:
    faltantes: list[str] = []
    cur.execute(
        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid=to_regclass(%s)",
        (f"public.{tabla}",),
    )
    rls = cur.fetchone()
    if rls is None or not all(rls):
        faltantes.append("ROW LEVEL SECURITY habilitada y FORCE")
    cur.execute(
        "SELECT t.tgname, t.tgenabled, pg_get_userbyid(p.proowner) FROM pg_trigger t JOIN "
        "pg_proc p ON p.oid=t.tgfoid WHERE t.tgrelid=to_regclass(%s) AND NOT t.tgisinternal",
        (f"public.{tabla}",),
    )
    triggers = {f[0]: (f[1], f[2]) for f in cur.fetchall()}
    for nombre in sorted(declaracion.triggers):
        if nombre not in triggers:
            faltantes.append(f"trigger {nombre} no existe")
        elif triggers[nombre] != ("O", arranque):
            faltantes.append(f"trigger {nombre} deshabilitado o función con otro dueño")
    cur.execute(
        "SELECT attname FROM pg_attribute WHERE attrelid=to_regclass(%s) AND attnum>0 AND "
        "NOT attisdropped ORDER BY attnum LIMIT 1",
        (f"public.{tabla}",),
    )
    primera = cur.fetchone()
    if primera is None:
        faltantes.append("sin columna para probar UPDATE")
    else:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE contype='f' AND "
            "confrelid=to_regclass(%s))",
            (f"public.{tabla}",),
        )
        fk = cur.fetchone()
        cascada = sql.SQL(" CASCADE") if fk and fk[0] else sql.SQL("")
        intentos = [
            (
                "UPDATE",
                sql.SQL("UPDATE {} SET {}={} WHERE false").format(
                    sql.Identifier("public", tabla),
                    sql.Identifier(primera[0]),
                    sql.Identifier(primera[0]),
                ),
            ),
            (
                "DELETE",
                sql.SQL("DELETE FROM {} WHERE false").format(sql.Identifier("public", tabla)),
            ),
            ("TRUNCATE", sql.SQL("TRUNCATE {}{}").format(sql.Identifier("public", tabla), cascada)),
        ]
        for nombre, sentencia in intentos:
            cur.execute("SAVEPOINT sonda_tabla_protegida")
            try:
                cur.execute(sentencia)
            except psycopg.Error as error:
                if error.sqlstate != "P0001" or declaracion.mensaje not in str(error):
                    faltantes.append(
                        f"no se pudo confirmar bloqueo de {nombre}: "
                        f"error distinto (SQLSTATE {error.sqlstate})"
                    )
            else:
                faltantes.append(f"admite {nombre}")
            finally:
                cur.execute("ROLLBACK TO SAVEPOINT sonda_tabla_protegida")
                cur.execute("RELEASE SAVEPOINT sonda_tabla_protegida")
    if faltantes:
        raise AuditoriaNoProtegida(
            f"la protección de {tabla} no se pudo confirmar: " + "; ".join(faltantes)
        )


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
            for tabla in sorted(_TABLAS_DE_SOLO_AGREGAR):
                if _existe_tabla(cur, tabla):
                    cur.execute(
                        sql.SQL("ALTER TABLE {} OWNER TO {}").format(
                            sql.Identifier("public", tabla),
                            sql.Identifier(configuracion.postgres_user),
                        )
                    )
                    for funcion in _funciones_de_los_triggers_de(cur, tabla):
                        cur.execute(
                            sql.SQL("ALTER FUNCTION {}() OWNER TO {}").format(
                                sql.Identifier("public", funcion),
                                sql.Identifier(configuracion.postgres_user),
                            )
                        )
                        cur.execute(
                            sql.SQL("ALTER FUNCTION {}() SET search_path = ''").format(
                                sql.Identifier("public", funcion)
                            )
                        )
                    cur.execute(
                        sql.SQL("REVOKE UPDATE, DELETE, TRUNCATE ON {} FROM {}").format(
                            sql.Identifier(tabla), sql.Identifier(app.postgres_user)
                        )
                    )
                    cur.execute(
                        sql.SQL("GRANT SELECT, INSERT ON {} TO {}").format(
                            sql.Identifier(tabla), sql.Identifier(app.postgres_user)
                        )
                    )
                    if not TABLAS_DE_SOLO_AGREGAR[tabla].verificacion_con_fila:
                        _verificar_tabla_protegida(
                            cur, tabla, TABLAS_DE_SOLO_AGREGAR[tabla], configuracion.postgres_user
                        )
                else:
                    print(f"tabla protegida {tabla}: no existe, se saltea")
            # Revisión final (19/10/2026), arreglo 8: `REVOKE ALL` primero
            # (deshace lo que los DEFAULT PRIVILEGES regalaron, cualquiera
            # sea el permiso) y recién después el `GRANT SELECT` angosto —
            # mismo orden que el de `auditoria` más abajo, nunca al revés.
            for tabla in sorted(_TABLAS_DE_SOLO_LECTURA_PARA_LA_APP):
                if _existe_tabla(cur, tabla):
                    cur.execute(
                        sql.SQL("REVOKE ALL ON {} FROM {}").format(
                            sql.Identifier(tabla), sql.Identifier(app.postgres_user)
                        )
                    )
                    cur.execute(
                        sql.SQL("GRANT SELECT ON {} TO {}").format(
                            sql.Identifier(tabla), sql.Identifier(app.postgres_user)
                        )
                    )
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
            # R3 (vuelta 2): mismo mecanismo que arriba, para el vocabulario
            # (D1: la app sólo tiene SELECT sobre `accion_de_auditoria`).
            # Excluirla del grant amplio de `antes()` no alcanza por sí
            # sola: la crea el migrador, y los `ALTER DEFAULT PRIVILEGES`
            # le dan los cuatro permisos igual, sin importar qué `GRANT`
            # explícito haga o deje de hacer la migración.
            cur.execute(
                sql.SQL("REVOKE INSERT, UPDATE, DELETE ON accion_de_auditoria FROM {app};").format(
                    app=sql.Identifier(app.postgres_user)
                )
            )
            cur.execute(
                sql.SQL("GRANT SELECT ON accion_de_auditoria TO {app};").format(
                    app=sql.Identifier(app.postgres_user)
                )
            )
            # R4 (vuelta 2): recién acá, con todo lo de arriba ya aplicado
            # en esta misma transacción. Si algo sigue sin estar (un
            # trigger que alguien borró antes de esta corrida, por
            # ejemplo: esto no lo recrea), se corta ACÁ, antes de
            # confirmar nada — nunca un "despues() salió bien" silencioso
            # sobre una auditoria que en los hechos no está protegida.
            _verificar_auditoria_protegida(cur, configuracion.postgres_user)
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
    except AuditoriaNoProtegida as error:
        print(f"error en el paso de roles: {error}", file=sys.stderr)
        return 1
    except ConfiguracionDeRolesInsegura as error:
        print(f"error en el paso de roles: {error}", file=sys.stderr)
        return 1
    except NombreDeRolDeLaAppDesconocido as error:
        print(f"error en el paso de roles: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
