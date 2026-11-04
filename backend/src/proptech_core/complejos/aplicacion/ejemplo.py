"""Carga del edificio de ejemplo (D9 del design de `configuracion-del-edificio`,
reescrito por D1/D2 del design de `acceso-de-desarrollo` sobre D10/D11 del
design de `login-y-usuarios`).

Corre siempre con las credenciales de `proptech_app` -- nunca
`proptech_migrador` -- sobre una administración de ejemplo con id fijo (no
generado), para que `cargar()` sea idempotente: la administración y la `persona` con su
`asignacion_rol` de `super_admin` se crean una sola vez, y el edificio se carga por los
mismos casos de uso que usa la API (`crear_edificio`, `crear_unidad`,
`crear_grupo`, `confirmar_sin_saldos_previos`), todo en una transacción. El
comando MUST NOT pedir ni otorgar ningún permiso nuevo: `proptech_app` ya
tiene lo que estos casos de uso necesitan (D1 del design de
`acceso-de-desarrollo`).

Comparación de idempotencia (datos-semilla, "Carga del edificio de ejemplo en
la base"): el edificio que se llama como dice la semilla, con lo que sale de
ella -- unidades, grupos y estado de migración -- y el super admin del ejemplo --
su nombre, su email y que siga con esa asignación --. Nunca la configuración
versionada ni las categorías, que vienen de `parametros.yaml` (D-042): esas dos
cambian con el archivo sin que eso cuente como "el ejemplo cambió". Tampoco otros
edificios, otras personas ni el vínculo con una cuenta de Clerk.

Cada error del comando sale con su mensaje y su código, sin traceback (`_main`): la
tabla de códigos está en el spec `datos-semilla` y en el README.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import NoReturn
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from proptech_core.acceso.aplicacion.alta_inicial import crear_administracion_y_super_admin
from proptech_core.acceso.aplicacion.usuarios import listar_personal
from proptech_core.acceso.aplicacion.vinculacion_de_desarrollo import (
    ADMINISTRACION_EJEMPLO_ID as ADMINISTRACION_EJEMPLO_ID,
)
from proptech_core.acceso.aplicacion.vinculacion_de_desarrollo import (
    PERSONA_SUPER_ADMIN_EJEMPLO_ID as PERSONA_SUPER_ADMIN_EJEMPLO_ID,
)
from proptech_core.acceso.aplicacion.vinculacion_de_desarrollo import (
    VinculacionDeDesarrolloNoDisponible,
    vincular,
)
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import (
    RolDeAplicacionInseguro,
    TablasDeSoloAgregarDesprotegidas,
    abrir_sesion,
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_reset_del_tenant_al_devolver,
    registrar_tenant_por_administracion,
    verificar_rol_de_aplicacion_seguro,
    verificar_tablas_de_solo_agregar,
)
from proptech_core.compartido.configuracion import ConfiguracionDelEjemplo, ConfiguracionInvalida
from proptech_core.compartido.georef import Georef, GeorefInvalido, leer_georef
from proptech_core.compartido.parametros import Parametros, ParametrosInvalidos, leer_parametros
from proptech_core.compartido.semilla import Semilla, SemillaInvalida, leer_semilla
from proptech_core.complejos.aplicacion.errores import EntradaInvalida
from proptech_core.complejos.aplicacion.escritura import (
    confirmar_sin_saldos_previos,
    crear_edificio,
)
from proptech_core.complejos.aplicacion.grupos import crear_grupo
from proptech_core.complejos.aplicacion.unidades import crear_unidad

NOMBRE_ADMINISTRACION_EJEMPLO = "Administración de ejemplo"
NOMBRE_SUPER_ADMIN_EJEMPLO = "Super admin de ejemplo"
#: Ficticio, nunca un dato personal real (D-093): sólo identifica la fila.
EMAIL_SUPER_ADMIN_EJEMPLO = "super-admin@ejemplo.proptech.invalid"
#: Guarda de entorno (D-112, Juani 25/10/2026): el módulo viaja en la
#: imagen de producción (`COPY src`), así que el comando se niega a correr salvo
#: que el entorno diga explícitamente que es una máquina de desarrollo.
ENTORNO_DE_DESARROLLO = "desarrollo"

# Códigos de salida (spec `datos-semilla`, D4 y D10 de `ejemplo-robusto`). El 1 es sólo de
# la guarda (D-112), por eso `_main` no deja escapar `Exception`: Python también usa 1 para
# una excepción sin capturar. Tampoco `KeyboardInterrupt`, que dejaría un traceback: sale con
# 130 (D10). `argparse` sale por su `SystemExit`, con el 2 de `_Parser` o el 0 de `--help`.
# Están en la tabla del README.
CODIGO_FUERA_DE_DESARROLLO = 1
CODIGO_USO = 2
CODIGO_CONFIGURACION = 3
CODIGO_BASE_INSEGURA = 4
CODIGO_BASE_NO_DISPONIBLE = 5
CODIGO_EJEMPLO_DISTINTO = 6
CODIGO_VINCULACION_RECHAZADA = 7
CODIGO_CARGA_INCOMPLETA = 8
CODIGO_INESPERADO = 9
CODIGO_INTERRUMPIDO = 130

_ARCHIVO_ILEGIBLE = "no se puede leer el archivo: "


def _ruta_georef_por_defecto(configuracion: ConfiguracionDelEjemplo) -> Path:
    return Path(configuracion.proptech_parametros).resolve().parent / "georef"


def _ruta_semilla_por_defecto(configuracion: ConfiguracionDelEjemplo) -> Path:
    """Relativa a `PROPTECH_PARAMETROS` (D-042), nunca calculada por la
    profundidad del archivo: esa cuenta difiere entre la corrida local (bajo
    `backend/`) y la imagen de Docker (`/app/src/...`), que no tienen el
    mismo número de carpetas hasta la raíz del repo."""
    base = Path(configuracion.proptech_parametros).resolve().parent
    return base / "semilla" / "edificio-ejemplo.yaml"


class EjemploDistinto(Exception):
    """El ejemplo ya está en la base pero distinto al de la semilla: no se
    escribió nada (datos-semilla, "El ejemplo cambió en la base")."""


class EsperaAgotada(Exception):
    """La administración de ejemplo existe sin edificio y ninguno apareció
    durante la espera (datos-semilla, "La administración de ejemplo quedó sin
    edificio"). No se escribió nada."""


@dataclass(frozen=True)
class ResultadoCarga:
    administracion_id: UUID
    complejo_id: UUID
    #: False cuando el ejemplo ya estaba igual ("ya estaba"); True cuando esta
    #: corrida lo creó.
    hizo_algo: bool
    vinculacion: str | None = None


def _reloj_por_defecto() -> datetime:
    return datetime.now(UTC)


def _nombre_de_grupo(clave: str, parametros: Parametros) -> tuple[str, str]:
    for grupo in parametros.grupos_de_reparto:
        if grupo.clave == clave:
            return grupo.nombre, grupo.metodo
    raise EjemploDistinto(f"grupos.{clave}: no está en los parámetros")


def _crear_desde_cero(
    sesion: Session,
    identidad: Identidad,
    *,
    parametros: Parametros,
    semilla: Semilla,
    georef: Georef,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> UUID:
    """La administración, la persona `super_admin` y su asignación ya las
    creó `crear_administracion_y_super_admin` (L-009, D7, 2d grupo 6): acá
    sólo se levanta el edificio con `identidad` ya resuelta."""
    complejo_id = crear_edificio(
        sesion,
        identidad,
        nombre=semilla.edificio.nombre,
        provincia_id=semilla.edificio.provincia_id,
        departamento_id=semilla.edificio.departamento_id,
        localidad_id=semilla.edificio.localidad_id,
        georef=georef,
        pisos=semilla.edificio.pisos,
        subsuelos=semilla.edificio.subsuelos,
        parametros=parametros,
        reloj=reloj,
        request_id=request_id,
    )

    unidad_ids: dict[str, UUID] = {}
    for unidad in semilla.unidades:
        unidad_ids[unidad.identificador] = crear_unidad(
            sesion,
            identidad,
            request_id=request_id,
            complejo_id=complejo_id,
            datos={
                "identificador": unidad.identificador,
                "tipo": unidad.tipo,
                "piso": unidad.piso,
                "coeficiente": str(unidad.coeficiente),
                "superficie_m2": unidad.superficie_m2,
            },
        )

    for clave, grupo in semilla.grupos.items():
        if clave == "generales" or grupo == "todas":
            continue
        nombre, metodo = _nombre_de_grupo(clave, parametros)
        miembros = [
            {
                "unidad_id": unidad_ids[miembro.identificador],
                **(
                    {"coeficiente": str(miembro.coeficiente)}
                    if miembro.coeficiente is not None
                    else {}
                ),
            }
            for miembro in grupo.unidades
        ]
        crear_grupo(
            sesion,
            identidad,
            complejo_id=complejo_id,
            datos={"clave": clave, "nombre": nombre, "metodo": metodo},
            miembros=miembros,
            modo=grupo.modo,
            request_id=request_id,
        )

    if semilla.edificio.estado_migracion == "sin_saldos_previos":
        confirmar_sin_saldos_previos(
            sesion, identidad, complejo_id=complejo_id, request_id=request_id
        )
    elif semilla.edificio.estado_migracion == "confirmada":
        # Sin caso de uso propio todavía (llega con la liquidación, changes 4
        # a 7): la semilla del repositorio no usa este estado hoy.
        raise EntradaInvalida("estado_migracion", "confirmada: sin caso de uso todavía")

    return complejo_id


def _comparar_o_fallar(sesion: Session, complejo_id: UUID, semilla: Semilla) -> None:
    diferencias: list[str] = []

    estado_migracion = sesion.execute(
        text("SELECT estado_migracion FROM complejo WHERE id=:id"), {"id": complejo_id}
    ).scalar_one()
    if estado_migracion != semilla.edificio.estado_migracion:
        diferencias.append(
            f"estado_migracion: base={estado_migracion!r} "
            f"semilla={semilla.edificio.estado_migracion!r}"
        )

    filas_unidad = (
        sesion.execute(
            text(
                "SELECT identificador, tipo, piso, coeficiente::text, "
                "superficie_m2::text FROM unidad WHERE complejo_id=:id"
            ),
            {"id": complejo_id},
        )
        .mappings()
        .all()
    )
    existentes = {fila["identificador"]: fila for fila in filas_unidad}
    esperadas = {unidad.identificador: unidad for unidad in semilla.unidades}
    if set(existentes) != set(esperadas):
        diferencias.append(
            "unidades: faltan "
            f"{sorted(set(esperadas) - set(existentes))}, sobran "
            f"{sorted(set(existentes) - set(esperadas))}"
        )
    else:
        for identificador, unidad in esperadas.items():
            fila = existentes[identificador]
            # D9: un mensaje por campo, sin valores.
            for campo, distinto in (
                ("tipo", fila["tipo"] != unidad.tipo),
                ("piso", fila["piso"] != unidad.piso),
                ("coeficiente", Decimal(fila["coeficiente"]) != unidad.coeficiente),
                ("superficie_m2", Decimal(fila["superficie_m2"]) != unidad.superficie_m2.decimal),
            ):
                if distinto:
                    diferencias.append(f"unidades[{identificador}].{campo}: difiere de la semilla")

    filas_grupo = (
        sesion.execute(
            text(
                "SELECT id, clave, modo_de_coeficientes FROM grupo_de_reparto "
                "WHERE complejo_id=:id AND NOT es_generales"
            ),
            {"id": complejo_id},
        )
        .mappings()
        .all()
    )
    grupos_base = {fila["clave"]: fila for fila in filas_grupo}
    grupos_semilla = {
        clave: grupo
        for clave, grupo in semilla.grupos.items()
        if clave != "generales" and grupo != "todas"
    }
    if set(grupos_base) != set(grupos_semilla):
        diferencias.append(
            "grupos: faltan "
            f"{sorted(set(grupos_semilla) - set(grupos_base))}, sobran "
            f"{sorted(set(grupos_base) - set(grupos_semilla))}"
        )
    else:
        miembros_por_grupo: dict[UUID, dict[str, dict[str, object]]] = {}
        for fila in grupos_base.values():
            miembros = (
                sesion.execute(
                    text(
                        "SELECT u.identificador, gu.coeficiente::text AS coeficiente "
                        "FROM grupo_unidad gu JOIN unidad u ON u.id = gu.unidad_id "
                        "WHERE gu.grupo_id=:id"
                    ),
                    {"id": fila["id"]},
                )
                .mappings()
                .all()
            )
            miembros_por_grupo[fila["id"]] = {m["identificador"]: dict(m) for m in miembros}
        for clave, grupo in grupos_semilla.items():
            fila = grupos_base[clave]
            if fila["modo_de_coeficientes"] != grupo.modo:
                diferencias.append(f"grupos.{clave}.modo: difiere de la semilla")
                continue
            existentes_miembros = miembros_por_grupo[fila["id"]]
            esperados_miembros = {m.identificador: m for m in grupo.unidades}
            if set(existentes_miembros) != set(esperados_miembros):
                diferencias.append(f"grupos.{clave}.unidades: difiere de la semilla")
                continue
            for identificador, miembro in esperados_miembros.items():
                coeficiente_base = existentes_miembros[identificador]["coeficiente"]
                difiere = (miembro.coeficiente is None) != (coeficiente_base is None) or (
                    miembro.coeficiente is not None
                    and Decimal(str(coeficiente_base)) != miembro.coeficiente
                )
                if difiere:
                    diferencias.append(
                        f"grupos.{clave}.unidades[{identificador}].coeficiente: "
                        "difiere de la semilla"
                    )

    diferencias.extend(_diferencias_del_super_admin(sesion))

    if diferencias:
        raise EjemploDistinto("; ".join(diferencias))


def _diferencias_del_super_admin(sesion: Session) -> list[str]:
    """D3 de `ejemplo-robusto`: la persona se lee por `acceso.aplicacion`, sin SQL
    propio sobre sus tablas (D-133). Basta con que tenga una asignación de
    `super_admin`: asignaciones de más, otras personas o una cuenta vinculada no
    son "el ejemplo cambió". Los mensajes nombran el dato, nunca su valor."""
    super_admin = next(
        (
            persona
            for persona in listar_personal(sesion)
            if persona["persona_id"] == str(PERSONA_SUPER_ADMIN_EJEMPLO_ID)
        ),
        None,
    )
    if super_admin is None:
        return ["persona: no está el super admin del ejemplo"]
    diferencias: list[str] = []
    if super_admin["nombre"] != NOMBRE_SUPER_ADMIN_EJEMPLO:
        diferencias.append("persona.nombre: difiere del ejemplo")
    if super_admin["email"] != EMAIL_SUPER_ADMIN_EJEMPLO:
        diferencias.append("persona.email: difiere del ejemplo")
    if not any(asignacion["rol"] == "super_admin" for asignacion in super_admin["asignaciones"]):
        diferencias.append("persona.asignaciones: perdió la de super_admin")
    return diferencias


def _edificio_del_ejemplo(edificios: list[tuple[UUID, str]], semilla: Semilla) -> UUID:
    """D2 de `ejemplo-robusto`: el edificio del ejemplo es el que se llama como dice
    la semilla, con cualquier otro al lado. `complejo` no tiene unicidad por nombre
    ni fecha de creación, y su `id` es aleatorio: sin un nombre que coincida una sola
    vez no hay forma de saber cuál es, y eso ya es "el ejemplo cambió"."""
    coinciden = [id_ for id_, nombre in edificios if nombre == semilla.edificio.nombre]
    if len(coinciden) != 1:
        raise EjemploDistinto(
            f"edificio.nombre: hay {len(coinciden)} edificios con el nombre de la semilla "
            "y se esperaba uno"
        )
    return coinciden[0]


def cargar(
    fabrica: sessionmaker[Session],
    *,
    parametros: Parametros,
    semilla: Semilla,
    georef: Georef,
    reloj: Callable[[], datetime] = _reloj_por_defecto,
    request_id: UUID,
    clerk_usuario: str | None = None,
    intentos: int = 50,
    espera_s: float = 0.1,
) -> ResultadoCarga:
    """Carga el edificio de ejemplo, idempotente (datos-semilla). `fabrica`
    tiene que venir de una conexión como `proptech_app`, con el tenant
    registrado (`registrar_tenant_por_administracion`): si no lo está, la
    política de RLS rechaza cualquier escritura con el tenant fijo de este
    módulo, y no queda nada a medias (D1 de `acceso-de-desarrollo`)."""
    for _ in range(intentos):
        with abrir_sesion(fabrica, ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
            alta = crear_administracion_y_super_admin(
                sesion,
                administracion_id=ADMINISTRACION_EJEMPLO_ID,
                persona_id=PERSONA_SUPER_ADMIN_EJEMPLO_ID,
                nombre_administracion=NOMBRE_ADMINISTRACION_EJEMPLO,
                nombre_persona=NOMBRE_SUPER_ADMIN_EJEMPLO,
                email=EMAIL_SUPER_ADMIN_EJEMPLO,
                request_id=request_id,
            )
            if alta is not None:
                identidad = Identidad(ADMINISTRACION_EJEMPLO_ID, PERSONA_SUPER_ADMIN_EJEMPLO_ID)
                complejo_id = _crear_desde_cero(
                    sesion,
                    identidad,
                    parametros=parametros,
                    semilla=semilla,
                    georef=georef,
                    reloj=reloj,
                    request_id=request_id,
                )
                vinculacion = (
                    vincular(
                        sesion,
                        ADMINISTRACION_EJEMPLO_ID,
                        PERSONA_SUPER_ADMIN_EJEMPLO_ID,
                        clerk_usuario,
                    )
                    if clerk_usuario is not None
                    else None
                )
                return ResultadoCarga(
                    ADMINISTRACION_EJEMPLO_ID, complejo_id, hizo_algo=True, vinculacion=vinculacion
                )

            edificios = sesion.execute(
                text("SELECT id, nombre FROM complejo WHERE administracion_id=:admin"),
                {"admin": ADMINISTRACION_EJEMPLO_ID},
            ).all()
            if edificios:
                complejo_id = _edificio_del_ejemplo(
                    [(fila.id, fila.nombre) for fila in edificios], semilla
                )
                _comparar_o_fallar(sesion, complejo_id, semilla)
                vinculacion = (
                    vincular(
                        sesion,
                        ADMINISTRACION_EJEMPLO_ID,
                        PERSONA_SUPER_ADMIN_EJEMPLO_ID,
                        clerk_usuario,
                    )
                    if clerk_usuario is not None
                    else None
                )
                return ResultadoCarga(
                    ADMINISTRACION_EJEMPLO_ID, complejo_id, hizo_algo=False, vinculacion=vinculacion
                )
            # La administración existe y no tiene edificios. Una corrida en
            # paralelo no llega acá: el `ON CONFLICT` de arriba espera a que la
            # otra confirme, y toda la carga va en una transacción. Es un estado
            # que quedó de otra forma, así que se mira de nuevo un rato, con una
            # sesión nueva (la actual ya leyó un estado que puede quedar
            # obsoleto), y se avisa lo que se ve.
        time.sleep(espera_s)
    raise EsperaAgotada(
        "la administración de ejemplo existe sin edificio y no apareció ninguno durante la "
        "espera; no se escribió nada"
    )


def _emisor_de_desarrollo(emisor: str | None) -> str | None:
    if not emisor:
        return None
    try:
        partes = urlsplit(emisor)
        if (
            partes.scheme != "https"
            or not partes.hostname
            or not partes.hostname.endswith(".clerk.accounts.dev")
            or partes.username is not None
            or partes.password is not None
            or partes.port not in (None, 443)
            or partes.query
            or partes.fragment
            or "?" in emisor
            or "#" in emisor
            or partes.path not in ("", "/")
        ):
            return None
        return f"https://{partes.hostname}"
    except ValueError:
        return None


def _fallar(codigo: int, mensaje: str) -> int:
    print(mensaje, file=sys.stderr)
    return codigo


class _Parser(argparse.ArgumentParser):
    """argparse repite en sus errores lo que se tipeó mal (`invalid choice`,
    `unrecognized arguments`), y eso puede ser el id de la cuenta (B-2, spec de los
    códigos): el mensaje es siempre el mismo, sin el valor."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(CODIGO_USO, "argumentos no reconocidos; no se escribió nada\n")


def _leer_argumentos(argv: list[str]) -> argparse.Namespace:
    # B-2 (rompedor, vuelta 1): `allow_abbrev=False` en los dos parsers para
    # que `--clerk` no se acepte como abreviatura de `--clerk-usuario`, y
    # `parse_known_args` en vez de `parse_args` para que lo que sobra termine en
    # `_Parser.error`, sin repetir ningún valor del usuario.
    parser = _Parser(description="Comando del edificio de ejemplo", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="accion", required=True)
    cargar_parser = subparsers.add_parser(
        "cargar", help="Carga el edificio de ejemplo en la base", allow_abbrev=False
    )
    cargar_parser.add_argument("--semilla", default=None)
    cargar_parser.add_argument("--clerk-usuario", default=None)
    args, no_reconocidos = parser.parse_known_args(argv)
    if no_reconocidos:
        parser.error("argumentos no reconocidos")
    return args


def _sin_la_ruta_del_archivo(mensaje: str, ruta_semilla: str, ruta_parametros: str) -> str:
    """D4: el lector de archivos repite la ruta, y `--semilla` es algo que se tipeó, que
    puede ser el id de la cuenta. Se saca sólo si el mensaje entero es ése: dentro de otro
    texto, una ruta corta como `e` se come las letras del mensaje. Georef ya nombra sólo
    el archivo (L-007)."""
    if mensaje == f"{_ARCHIVO_ILEGIBLE}{ruta_semilla}":
        return f"{_ARCHIVO_ILEGIBLE}<semilla>"
    if mensaje == f"{_ARCHIVO_ILEGIBLE}{ruta_parametros}":
        return f"{_ARCHIVO_ILEGIBLE}<parámetros>"
    return mensaje


def _ejecutar(args: argparse.Namespace) -> int:
    """El orden es parte del contrato (D4). `argparse` corre antes, en `_leer_argumentos`: un
    error de uso da 2 y `--help` da 0 en cualquier entorno, sin correr el comando ni
    conectarse. Después van la guarda, `--semilla` vacío, id, emisor, configuración, archivos,
    base y carga. La guarda va primero porque D-112 fija su código aunque no haya ninguna
    otra variable (RV-1)."""
    if os.environ.get("PROPTECH_ENTORNO") != ENTORNO_DE_DESARROLLO:
        return _fallar(
            CODIGO_FUERA_DE_DESARROLLO,
            "este comando es sólo para desarrollo: no corre sin "
            f"PROPTECH_ENTORNO={ENTORNO_DE_DESARROLLO}; no se escribió nada",
        )

    if args.semilla == "":
        return _fallar(CODIGO_USO, "--semilla no puede estar vacío; no se escribió nada")

    if args.clerk_usuario is not None:
        if re.fullmatch(r"user_[A-Za-z0-9]{1,64}", args.clerk_usuario, flags=re.ASCII) is None:
            return _fallar(
                CODIGO_USO, "el id de cuenta no tiene el formato permitido; no se escribió nada"
            )
        if _emisor_de_desarrollo(os.environ.get("CLERK_EMISOR")) is None:
            return _fallar(
                CODIGO_CONFIGURACION,
                "la vinculación exige una instancia de Clerk de desarrollo; no se escribió nada",
            )

    try:
        configuracion = ConfiguracionDelEjemplo()
    except ConfiguracionInvalida as error:
        return _fallar(CODIGO_CONFIGURACION, str(error))
    ruta_semilla = args.semilla or str(_ruta_semilla_por_defecto(configuracion))
    try:
        parametros = leer_parametros(configuracion.proptech_parametros)
        georef = leer_georef(str(_ruta_georef_por_defecto(configuracion)))
        semilla = leer_semilla(ruta_semilla, parametros, georef)
    except (ParametrosInvalidos, GeorefInvalido, SemillaInvalida) as error:
        return _fallar(
            CODIGO_CONFIGURACION,
            _sin_la_ruta_del_archivo(str(error), ruta_semilla, configuracion.proptech_parametros),
        )

    engine = crear_engine(configuracion)
    try:
        verificar_rol_de_aplicacion_seguro(engine)
        verificar_tablas_de_solo_agregar(engine)
        fabrica = crear_fabrica_de_sesiones(engine)
        registrar_tenant_por_administracion(fabrica)
        registrar_reset_del_tenant_al_devolver(engine)
        resultado = cargar(
            fabrica,
            parametros=parametros,
            semilla=semilla,
            georef=georef,
            request_id=uuid4(),
            clerk_usuario=args.clerk_usuario,
        )
        if resultado.vinculacion is not None:
            print(resultado.vinculacion)
        if resultado.hizo_algo:
            print(f"ejemplo cargado: {resultado.administracion_id}")
        else:
            print(f"el ejemplo ya estaba: {resultado.administracion_id}")
        return 0
    except RolDeAplicacionInseguro:
        return _fallar(
            CODIGO_BASE_INSEGURA,
            "el rol de la aplicación no es seguro para este comando: tiene privilegios de "
            "más; no se escribió nada",
        )
    except TablasDeSoloAgregarDesprotegidas as error:
        # D4: su texto sólo trae cada tabla y un motivo fijo (`verificar_tablas_de_solo_agregar`),
        # y la tabla es lo que hay que ir a arreglar.
        return _fallar(
            CODIGO_BASE_INSEGURA,
            f"la base no es segura para este comando: {error}; no se escribió nada",
        )
    except OperationalError:
        return _fallar(
            CODIGO_BASE_NO_DISPONIBLE,
            "la base no está disponible: no se pudo conectar o se cortó la conexión",
        )
    except EjemploDistinto as error:
        return _fallar(CODIGO_EJEMPLO_DISTINTO, str(error))
    except VinculacionDeDesarrolloNoDisponible as error:
        return _fallar(CODIGO_VINCULACION_RECHAZADA, str(error))
    except EsperaAgotada as error:
        return _fallar(CODIGO_CARGA_INCOMPLETA, str(error))
    except EntradaInvalida as error:
        # D10: sólo su `campo`, porque el `motivo` no llega nunca al cliente.
        return _fallar(
            CODIGO_CONFIGURACION,
            f"la semilla o los parámetros no se pueden cargar: {error.campo}; no se escribió nada",
        )
    except DBAPIError:
        # También `IntegrityError`. Texto fijo: `str(error)` trae la sentencia y los
        # parámetros del driver.
        return _fallar(
            CODIGO_CARGA_INCOMPLETA, "no se pudo completar la carga; no se escribió nada"
        )
    finally:
        engine.dispose()


def _main(argv: list[str]) -> int:
    try:
        return _ejecutar(_leer_argumentos(argv))
    except KeyboardInterrupt:
        # D10: no dice "no se escribió nada", porque puede llegar después del commit.
        return _fallar(
            CODIGO_INTERRUMPIDO,
            "interrumpido: una carga a medias no queda, porque toda la carga va en una transacción",
        )
    except Exception as error:
        # D4: lo que ninguna familia contempla sale con su tipo y nada más, porque su
        # texto puede repetir datos. Para depurarlo se llama a `cargar()` desde un test.
        return _fallar(CODIGO_INESPERADO, f"error inesperado: {type(error).__name__}")


def main() -> None:
    sys.exit(_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
