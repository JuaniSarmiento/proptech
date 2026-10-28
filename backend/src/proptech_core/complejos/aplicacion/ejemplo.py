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
la base"): sólo lo que sale de la semilla -- unidades, grupos y estado de
migración --, nunca la configuración versionada ni las categorías, que vienen
de `parametros.yaml` (D-042): esas dos cambian con el archivo sin que eso
cuente como "el ejemplo cambió".
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
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from proptech_core.acceso.aplicacion.auditoria import registrar
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
from proptech_core.acceso.dominio.eventos import EventoDeAcceso
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_reset_del_tenant_al_devolver,
    registrar_tenant_por_administracion,
    verificar_rol_de_aplicacion_seguro,
    verificar_tablas_de_solo_agregar,
)
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.georef import Georef, leer_georef
from proptech_core.compartido.parametros import Parametros, leer_parametros
from proptech_core.compartido.semilla import Semilla, leer_semilla
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


def _ruta_georef_por_defecto(configuracion: Configuracion | None = None) -> Path:
    base = Path((configuracion or Configuracion()).proptech_parametros).resolve().parent
    return base / "georef"


def _ruta_semilla_por_defecto(configuracion: Configuracion | None = None) -> Path:
    """Relativa a `PROPTECH_PARAMETROS` (D-042), nunca calculada por la
    profundidad del archivo: esa cuenta difiere entre la corrida local (bajo
    `backend/`) y la imagen de Docker (`/app/src/...`), que no tienen el
    mismo número de carpetas hasta la raíz del repo."""
    base = Path((configuracion or Configuracion()).proptech_parametros).resolve().parent
    return base / "semilla" / "edificio-ejemplo.yaml"


class EjemploDistinto(Exception):
    """El ejemplo ya está en la base pero distinto al de la semilla: no se
    escribió nada (datos-semilla, "El ejemplo cambió en la base")."""


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
    *,
    parametros: Parametros,
    semilla: Semilla,
    georef: Georef,
    reloj: Callable[[], datetime],
    request_id: UUID,
) -> UUID:
    sesion.execute(
        text(
            "INSERT INTO persona(id, administracion_id, nombre, email) "
            "VALUES (:id, :admin, :nombre, :email)"
        ),
        {
            "id": PERSONA_SUPER_ADMIN_EJEMPLO_ID,
            "admin": ADMINISTRACION_EJEMPLO_ID,
            "nombre": NOMBRE_SUPER_ADMIN_EJEMPLO,
            "email": EMAIL_SUPER_ADMIN_EJEMPLO,
        },
    )
    sesion.execute(
        text(
            "INSERT INTO asignacion_rol(administracion_id, persona_id, rol) "
            "VALUES (:admin, :persona, 'super_admin')"
        ),
        {"admin": ADMINISTRACION_EJEMPLO_ID, "persona": PERSONA_SUPER_ADMIN_EJEMPLO_ID},
    )
    identidad = Identidad(ADMINISTRACION_EJEMPLO_ID, PERSONA_SUPER_ADMIN_EJEMPLO_ID)
    registrar(
        sesion,
        identidad,
        EventoDeAcceso.ALTA_INICIAL,
        entidad="persona",
        entidad_id=PERSONA_SUPER_ADMIN_EJEMPLO_ID,
        request_id=request_id,
    )

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
        raise NotImplementedError("estado_migracion=confirmada: sin caso de uso todavía")

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
            if (
                fila["tipo"] != unidad.tipo
                or fila["piso"] != unidad.piso
                or Decimal(fila["coeficiente"]) != unidad.coeficiente
                or Decimal(fila["superficie_m2"]) != unidad.superficie_m2.decimal
            ):
                diferencias.append(f"unidades[{identificador}]: difiere de la semilla")

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

    if diferencias:
        raise EjemploDistinto("; ".join(diferencias))


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
            ganadora = sesion.execute(
                text(
                    "INSERT INTO administracion(id, nombre) VALUES (:id, :nombre) "
                    "ON CONFLICT (id) DO NOTHING RETURNING id"
                ),
                {"id": ADMINISTRACION_EJEMPLO_ID, "nombre": NOMBRE_ADMINISTRACION_EJEMPLO},
            ).first()
            if ganadora is not None:
                complejo_id = _crear_desde_cero(
                    sesion,
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

            complejo = sesion.execute(
                text("SELECT id FROM complejo WHERE administracion_id=:admin LIMIT 1"),
                {"admin": ADMINISTRACION_EJEMPLO_ID},
            ).first()
            if complejo is not None:
                _comparar_o_fallar(sesion, complejo.id, semilla)
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
                    ADMINISTRACION_EJEMPLO_ID, complejo.id, hizo_algo=False, vinculacion=vinculacion
                )
            # Otra corrida ganó la carrera de `administracion` pero todavía no
            # terminó de cargar el edificio: esperar a que confirme, con una
            # sesión nueva (la actual ya leyó un estado que puede quedar
            # obsoleto).
        time.sleep(espera_s)
    raise RuntimeError(
        "la carga del ejemplo no terminó a tiempo: otra corrida en paralelo no confirmó"
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


def _main(argv: list[str]) -> int:
    # B-2 (rompedor, vuelta 1): `allow_abbrev=False` en los dos parsers para
    # que `--clerk` no se acepte como abreviatura de `--clerk-usuario`, y
    # `parse_known_args` en vez de `parse_args` para no dejar que argparse
    # arme su propio mensaje de `unrecognized arguments`, que repite tal
    # cual cualquier valor del usuario (el id de Clerk incluido).
    parser = argparse.ArgumentParser(
        description="Comando del edificio de ejemplo", allow_abbrev=False
    )
    subparsers = parser.add_subparsers(dest="accion", required=True)
    cargar_parser = subparsers.add_parser(
        "cargar", help="Carga el edificio de ejemplo en la base", allow_abbrev=False
    )
    cargar_parser.add_argument("--semilla", default=None)
    cargar_parser.add_argument("--clerk-usuario", default=None)
    args, no_reconocidos = parser.parse_known_args(argv)
    if no_reconocidos:
        parser.error("argumentos no reconocidos; no se escribió nada")

    if os.environ.get("PROPTECH_ENTORNO") != ENTORNO_DE_DESARROLLO:
        print(
            "este comando es sólo para desarrollo: no corre sin "
            f"PROPTECH_ENTORNO={ENTORNO_DE_DESARROLLO}; no se escribió nada",
            file=sys.stderr,
        )
        return 1

    emisor_normalizado = None
    if args.clerk_usuario is not None:
        if re.fullmatch(r"user_[A-Za-z0-9]{1,64}", args.clerk_usuario, flags=re.ASCII) is None:
            print(
                "el id de cuenta no tiene el formato permitido; no se escribió nada",
                file=sys.stderr,
            )
            return 1
        emisor_normalizado = _emisor_de_desarrollo(os.environ.get("CLERK_EMISOR"))
        if emisor_normalizado is None:
            print(
                "la vinculación exige una instancia de Clerk de desarrollo; no se escribió nada",
                file=sys.stderr,
            )
            return 1

    configuracion = Configuracion(clerk_emisor=emisor_normalizado)
    parametros = leer_parametros(configuracion.proptech_parametros)
    try:
        georef = leer_georef(str(_ruta_georef_por_defecto(configuracion)))
        semilla = leer_semilla(
            args.semilla or str(_ruta_semilla_por_defecto(configuracion)), parametros, georef
        )
    except Exception as error:  # SemillaInvalida, ParametrosInvalidos o GeorefInvalido
        print(str(error), file=sys.stderr)
        return 1

    engine = crear_engine(configuracion)
    try:
        verificar_rol_de_aplicacion_seguro(engine)
        verificar_tablas_de_solo_agregar(engine)
        fabrica = crear_fabrica_de_sesiones(engine)
        registrar_tenant_por_administracion(fabrica)
        registrar_reset_del_tenant_al_devolver(engine)
        try:
            resultado = cargar(
                fabrica,
                parametros=parametros,
                semilla=semilla,
                georef=georef,
                request_id=uuid4(),
                clerk_usuario=args.clerk_usuario,
            )
        except (EjemploDistinto, VinculacionDeDesarrolloNoDisponible) as error:
            print(str(error), file=sys.stderr)
            return 1
        except IntegrityError:
            print("no se pudo completar la carga; no se escribió nada", file=sys.stderr)
            return 1
        if resultado.vinculacion is not None:
            print(resultado.vinculacion)
        if resultado.hizo_algo:
            print(f"ejemplo cargado: {resultado.administracion_id}")
        else:
            print(f"el ejemplo ya estaba: {resultado.administracion_id}")
        return 0
    finally:
        engine.dispose()


def main() -> None:
    sys.exit(_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
