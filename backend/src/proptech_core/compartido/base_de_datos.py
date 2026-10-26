"""Engine de SQLAlchemy y Base declarativa, usados también por Alembic."""

import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, MetaData, create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, SessionTransaction, sessionmaker

from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.seguimiento import request_id_actual
from proptech_core.compartido.tablas_protegidas import TABLAS_DE_SOLO_AGREGAR

# D13 (deuda del 1b con dueño 3, tarea 2.3): nombres deterministas para toda
# constraint que se declare sin nombre explícito desde un modelo de
# SQLAlchemy Core/ORM. Las migraciones del 2a (0001 a 0004) ya nombran cada
# constraint a mano con este mismo prefijo (`fk_<tabla>_...`,
# `uq_<tabla>_...`, `ck_<tabla>_...`, ver `migraciones/versions/
# 0003_acceso_minimo.py`); esto no les cambia nada, cubre lo que venga desde
# 3.1 en adelante.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa común para todos los modelos del dominio."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


def crear_engine(
    configuracion: Configuracion, connect_args: dict[str, object] | None = None
) -> Engine:
    """Crea el engine sincrónico a partir de la configuración.

    `connect_args` se pasa a `create_engine`, nunca a `execution_options`: ahí
    SQLAlchemy lo ignora en silencio y el timeout de conexión no se aplica.

    Los parámetros del pool (`pool_pre_ping`, `pool_size`, `pool_recycle`,
    `pool_timeout`) y el timeout de conexión salen de la configuración (D18,
    M14), para que el engine de la API y el del worker sean gemelos (L-009).
    Un `connect_args` explícito pisa el `connect_timeout` de la
    configuración para ese valor puntual; el resto de `connect_args` llega
    intacto.
    """
    connect_args_finales: dict[str, object] = {
        "connect_timeout": configuracion.db_connect_timeout_s,
        **(connect_args or {}),
    }
    return create_engine(
        configuracion.url_sqlalchemy(),
        connect_args=connect_args_finales,
        pool_pre_ping=configuracion.db_pool_pre_ping,
        pool_size=configuracion.db_pool_size,
        pool_recycle=configuracion.db_pool_recycle_s,
        pool_timeout=configuracion.db_pool_timeout_s,
    )


def crear_fabrica_de_sesiones(engine: Engine) -> sessionmaker[Session]:
    """Crea la fábrica de sesiones ligada al engine dado."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def registrar_application_name(fabrica: sessionmaker[Session], prefijo: str) -> None:
    """Registra en `fabrica` un evento `after_begin` (D8) que, al abrir cada
    transacción, fija `application_name` a `"<prefijo>:<request_id>"` si hay
    un `request_id` en curso (la `ContextVar` de `seguimiento.py`).

    `set_config(..., true)` es **local a la transacción**: al confirmar o
    revertir, la conexión vuelve al nombre base que se le dio en
    `connect_args` (por eso el pedido siguiente del mismo pool no lo
    hereda). El parámetro va ligado, nunca interpolado en el SQL.
    """

    @event.listens_for(fabrica, "after_begin")
    def _after_begin(
        session: Session, transaction: SessionTransaction, connection: Connection
    ) -> None:
        request_id = request_id_actual.get()
        if request_id is None:
            return
        connection.execute(
            text("SELECT set_config('application_name', :nombre, true)"),
            {"nombre": f"{prefijo}:{request_id}"},
        )


def abrir_sesion(fabrica: sessionmaker[Session], administracion_id: uuid.UUID | None) -> Session:
    """Única forma de abrir una sesión de dominio en la API y en el worker
    (D4, gemelos L-009): el tenant viaja en `session.info`, un dato explícito
    de la sesión, nunca en una `ContextVar` ambiente (L-015, no depende de
    qué hilo la usa). Una sesión abierta con `fabrica()` directo, sin pasar
    por acá, no tiene esta clave: `registrar_tenant_por_administracion` no
    fija nada y la política de RLS (D5) da cero filas, nunca un error.
    """
    return fabrica(info={"administracion_id": administracion_id})


def abrir_sesion_por_identidad(fabrica: sessionmaker[Session], sub: str) -> Session:
    """D2: lectura de personas por una identidad ya verificada, sin tenant."""
    return fabrica(info={"identidad_clerk": sub})


def abrir_sesion_por_token_de_invitacion(
    fabrica: sessionmaker[Session], resumen_hex: str
) -> Session:
    """D6: busca la invitación por el resumen de su token (los 64 caracteres
    hexadecimales del SHA-256, nunca el token crudo ni el sobre), sin tenant:
    la política `invitacion_por_token` (migración 0020) sólo filtra cuando
    `app.administracion_id` está vacío, así que esta sesión nunca lo fija."""
    return fabrica(info={"invitacion_token": resumen_hex})


def registrar_tenant_por_administracion(fabrica: sessionmaker[Session]) -> None:
    """Registra en `fabrica` un evento `after_begin` (D4) que, al abrir cada
    transacción, fija `app.administracion_id` a partir de
    `session.info["administracion_id"]` (la que puso `abrir_sesion`).

    Si la clave falta (sesión abierta sin `abrir_sesion`, o `None`
    explícito), **no fija nada**: la política de D5 queda con
    `current_setting` vacío y da cero filas, nunca un error. Si lo que hay
    no es un `UUID` (un `str`, por un error de programación), levanta ANTES
    de tocar la base: nunca inventa ni interpola un valor ajeno.

    `set_config(..., true)` equivale a `SET LOCAL`: muere con la
    transacción, así que un `commit` a mitad de pedido que abre la
    transacción siguiente vuelve a pasar por este mismo evento (D4) y la
    conexión que vuelve al pool después de cerrar la sesión no lo hereda
    (gemelo de `registrar_application_name`, D8).
    """

    @event.listens_for(fabrica, "after_begin")
    def _after_begin(
        session: Session, transaction: SessionTransaction, connection: Connection
    ) -> None:
        identidad_clerk = session.info.get("identidad_clerk")
        if identidad_clerk is not None:
            connection.execute(
                text("SELECT set_config('app.identidad_clerk', :valor, true)"),
                {"valor": identidad_clerk},
            )
        invitacion_token = session.info.get("invitacion_token")
        if invitacion_token is not None:
            connection.execute(
                text("SELECT set_config('app.invitacion_token', :valor, true)"),
                {"valor": invitacion_token},
            )
        administracion_id = session.info.get("administracion_id")
        if administracion_id is None:
            return
        if not isinstance(administracion_id, uuid.UUID):
            raise TypeError(
                "administracion_id de la sesión tiene que ser un UUID, no "
                f"{type(administracion_id).__name__}"
            )
        connection.execute(
            text("SELECT set_config('app.administracion_id', :valor, true)"),
            {"valor": str(administracion_id)},
        )


def registrar_reset_del_tenant_al_devolver(engine: Engine) -> None:
    """Cinturón, además del `SET LOCAL` de D4 (R7, vuelta 2, rompedor/auditor).

    `set_config(..., true)` (D4) muere solo con la transacción — pero esa
    garantía depende de que TODO el código de arriba use ese mecanismo.
    Un `SET` de sesión (sin `LOCAL`), hecho por error en algún camino
    futuro, sobrevive al `ROLLBACK` que el pool ya hace al devolver la
    conexión (D4 no lo contradice: ese `ROLLBACK` es de la transacción, y un
    `SET` de sesión no es parte de ella). Sin este cinturón, esa conexión
    vuelve al pool con el tenant anterior pegado, y el próximo pedido que la
    reutilice sin pasar su propio tenant ve filas de la administración de
    otro (en vez de cero, D5).

    El evento `checkin` de SQLAlchemy corre SIEMPRE que una conexión vuelve
    al pool, DESPUÉS del `ROLLBACK` por default (`reset_on_return`): acá se
    agrega, siempre, un `RESET app.administracion_id` explícito sobre la
    conexión cruda. `RESET` de un parámetro que nunca se fijó en esa sesión
    no es un error (Postgres lo deja pasar): no hace falta chequear antes
    si hay algo que limpiar.

    **V2-1 (vuelta 3, regresión encontrada por el rompedor/auditor):** una
    conexión cortada a mitad de pedido (un reinicio de la base, una red que
    se cae, `pg_terminate_backend`) le llega a `checkin` de dos formas
    distintas, y las dos tienen que terminar sin propagar nada:

    1. SQLAlchemy ya la invalidó sola antes de despachar el evento, y acá
       llega `dbapi_connection=None` — no hay nada que resetear.
    2. Todavía parece viva, pero el propio `RESET` es lo que descubre que
       está rota (la conexión física ya no responde).

    Antes de esto, el caso 1 levantaba `AttributeError` dentro del
    handler, y una excepción sin atrapar en un evento de `checkin` aborta
    el "devolver al pool" de SQLAlchemy A MITAD DE CAMINO: el lugar queda
    `checked out` para siempre, nunca vuelve a estar disponible. Con el
    pool por default (5 + 10 de overflow), 15 cortes bastan para dejar la
    API en 500 permanente y al worker sin reintentar nada (`AttributeError`
    no es un error pasajero). El caso 2 tenía el mismo problema en potencia,
    sin necesitar que SQLAlchemy llegara a invalidar la conexión primero.

    Por eso acá: `dbapi_connection is None` se ignora sin más (nada que
    hacer), y cualquier error REAL del `RESET` invalida la conexión
    (`connection_record.invalidate`) en vez de dejarlo escapar — así
    SQLAlchemy sí completa el `checkin`, descarta esta conexión física
    rota y abre una nueva la próxima vez que haga falta. El error original
    (`OperationalError`) sigue siendo el que ve quien pidió la conexión:
    nunca se lo tapa un `AttributeError` de acá adentro.
    """

    @event.listens_for(engine, "checkin")
    def _checkin(dbapi_connection: Any, connection_record: Any) -> None:
        if dbapi_connection is None:
            return
        try:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("RESET app.administracion_id")
                cursor.execute("RESET app.identidad_clerk")
                cursor.execute("RESET app.invitacion_token")
                dbapi_connection.commit()
            finally:
                cursor.close()
        except Exception as error:
            connection_record.invalidate(error)


class RolDeAplicacionInseguro(Exception):
    """El rol con el que esta conexión corre no es seguro para un servicio
    permanente (R8, vuelta 2): es superusuario, tiene `BYPASSRLS`, o es
    dueño de alguna tabla. Cualquiera de los tres quiere decir que, pese a
    las variables `POSTGRES_APP_*`, en los hechos terminó conectada como
    otro rol — el de arranque o el de respaldo, por ejemplo, si
    `POSTGRES_APP_USER` quedó igual a uno de esos por error (R8 también
    pide que `roles antes` rechace esa configuración; esto es la segunda
    barrera, del lado de quien se conecta, no de quien crea los roles)."""


def verificar_rol_de_aplicacion_seguro(engine: Engine) -> None:
    """La API y el worker la llaman al arrancar, antes de aceptar ningún
    pedido o tarea (R8, vuelta 2): si no se cumple, el proceso no arranca,
    nombrando qué atributo está mal — nunca arranca "igual" confiando en
    que las variables de entorno dicen la verdad."""
    with engine.connect() as conexion:
        fila = conexion.execute(
            text(
                "SELECT rolsuper, rolbypassrls, "
                "(SELECT count(*) FROM pg_tables WHERE tableowner = current_user) "
                "FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
    rolsuper, rolbypassrls, tablas_propias = fila
    problemas: list[str] = []
    if rolsuper:
        problemas.append("es superusuario")
    if rolbypassrls:
        problemas.append("tiene BYPASSRLS")
    if tablas_propias:
        problemas.append(f"es dueño de {tablas_propias} tabla(s)")
    if problemas:
        raise RolDeAplicacionInseguro(
            "la conexión de la aplicación no es segura: " + "; ".join(problemas)
        )


def obtener_sesion(fabrica: sessionmaker[Session]) -> Iterator[Session]:
    """Dependencia de FastAPI: abre y cierra una sesión por request."""
    sesion = fabrica()
    try:
        yield sesion
    finally:
        sesion.close()


class TablasDeSoloAgregarDesprotegidas(Exception):
    """Una tabla protegida no existe en public o tiene dueño no superusuario."""


def verificar_tablas_de_solo_agregar(engine: Engine) -> None:
    """Falla cerrado sobre el conjunto entero y el esquema public (D3)."""
    with engine.connect() as conexion:
        filas = conexion.execute(
            text(
                "SELECT t.tablename, r.rolsuper FROM pg_tables t "
                "JOIN pg_roles r ON r.rolname=t.tableowner WHERE t.schemaname='public'"
            )
        )
        catalogo = {f[0]: f[1] for f in filas}
    faltantes = [
        f"{tabla}: no existe en public"
        if tabla not in catalogo
        else f"{tabla}: dueño no superusuario"
        for tabla in sorted(TABLAS_DE_SOLO_AGREGAR)
        if not catalogo.get(tabla, False)
    ]
    if faltantes:
        raise TablasDeSoloAgregarDesprotegidas(
            "tablas de sólo agregar desprotegidas: " + "; ".join(faltantes)
        )
