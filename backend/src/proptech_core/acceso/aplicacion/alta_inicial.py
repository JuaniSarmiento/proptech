"""D10: alta inicial desde el operador, usando sólo proptech_app y un tenant nuevo."""

import argparse
import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from proptech_core.acceso.aplicacion.auditoria import registrar
from proptech_core.acceso.aplicacion.datos_de_usuario import email_valido, nombre_valido
from proptech_core.acceso.aplicacion.entrega import crear_invitacion, encolar_envio
from proptech_core.acceso.dominio.eventos import EventoDeAcceso
from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.acceso.puertos import ColaDeInvitaciones
from proptech_core.compartido.base_de_datos import (
    abrir_sesion,
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_reset_del_tenant_al_devolver,
    registrar_tenant_por_administracion,
    verificar_rol_de_aplicacion_seguro,
    verificar_tablas_de_solo_agregar,
)
from proptech_core.compartido.cola import AdaptadorColaArq
from proptech_core.compartido.conexion_redis import ajustes_redis_arq
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.parametros import Parametros, leer_parametros


@dataclass(frozen=True)
class AltaInicialDeAdministracion:
    administracion_id: UUID
    persona_id: UUID
    asignacion_id: UUID


def crear_administracion_y_super_admin(
    sesion: Session,
    *,
    nombre_administracion: str,
    nombre_persona: str,
    email: str,
    request_id: UUID,
    administracion_id: UUID | None = None,
    persona_id: UUID | None = None,
) -> AltaInicialDeAdministracion | None:
    """L-009 (D7, 2d grupo 6): el tramo administración + persona
    `super_admin` + asignación + `alta_inicial`, compartido por
    `alta_inicial.crear` (pasa el UUID de administración recién generado;
    esta función genera los demás ids) y
    `complejos.aplicacion.ejemplo.cargar` (con los ids fijos del ejemplo).
    La sesión ya tiene el tenant puesto (`abrir_sesion`); esta función no lo
    decide.

    Con `administracion_id` dado, usa `ON CONFLICT (id) DO NOTHING` para la
    idempotencia de la carrera de `cargar()` (D7, el riesgo que `ejemplo.py`
    ya resolvía): si otra corrida ganó, devuelve `None` sin escribir
    `persona` ni `asignacion_rol`. Sin `administracion_id`, genera uno nuevo:
    nadie más lo conoce, así que no hay carrera que perder.
    """
    if administracion_id is not None:
        fila = sesion.execute(
            text(
                "INSERT INTO administracion(id, nombre) VALUES (:id, :nombre) "
                "ON CONFLICT (id) DO NOTHING RETURNING id"
            ),
            {"id": administracion_id, "nombre": nombre_administracion},
        ).first()
        if fila is None:
            return None
        admin = administracion_id
    else:
        admin = sesion.execute(
            text("INSERT INTO administracion(nombre) VALUES (:nombre) RETURNING id"),
            {"nombre": nombre_administracion},
        ).scalar_one()
    if persona_id is not None:
        sesion.execute(
            text(
                "INSERT INTO persona(id, administracion_id, nombre, email) "
                "VALUES (:id, :admin, :nombre, :email)"
            ),
            {"id": persona_id, "admin": admin, "nombre": nombre_persona, "email": email},
        )
        persona = persona_id
    else:
        persona = sesion.execute(
            text(
                "INSERT INTO persona(administracion_id, nombre, email) "
                "VALUES (:admin, :nombre, :email) RETURNING id"
            ),
            {"admin": admin, "nombre": nombre_persona, "email": email},
        ).scalar_one()
    asignacion = sesion.execute(
        text(
            "INSERT INTO asignacion_rol(administracion_id, persona_id, rol) "
            "VALUES (:admin, :persona, 'super_admin') RETURNING id"
        ),
        {"admin": admin, "persona": persona},
    ).scalar_one()
    identidad = Identidad(admin, persona)
    registrar(
        sesion,
        identidad,
        EventoDeAcceso.ALTA_INICIAL,
        entidad="persona",
        entidad_id=persona,
        request_id=request_id,
    )
    return AltaInicialDeAdministracion(admin, persona, asignacion)


async def crear(
    fabrica: sessionmaker[Session],
    *,
    configuracion: Configuracion,
    parametros: Parametros,
    cola: ColaDeInvitaciones,
    administracion: str,
    nombre: str,
    email: str,
    request_id: UUID,
) -> UUID:
    administracion = nombre_valido(administracion, "administracion")
    nombre = nombre_valido(nombre)
    email = email_valido(email)
    clave = configuracion.clave_para_invitar()
    admin = uuid4()
    with abrir_sesion(fabrica, admin) as sesion, sesion.begin():
        if sesion.execute(
            text("SELECT 1 FROM asignacion_rol WHERE rol = 'super_admin' LIMIT 1")
        ).first():
            raise ValueError("administracion: ya tiene super admin")
        alta = crear_administracion_y_super_admin(
            sesion,
            administracion_id=admin,
            nombre_administracion=administracion,
            nombre_persona=nombre,
            email=email,
            request_id=request_id,
        )
        if alta is None:
            # `admin` es un uuid4 recién generado que nadie más conoce: no
            # puede perder la carrera de `ON CONFLICT` (L-009, D7).
            raise RuntimeError("administracion: id recién generado en conflicto")
        identidad = Identidad(admin, alta.persona_id)
        invitacion, sobre = crear_invitacion(sesion, identidad, alta.persona_id, parametros, clave)
    await encolar_envio(cola, admin, invitacion, sobre, request_id)
    return admin


def main() -> None:
    parser = argparse.ArgumentParser(description="Crear una administración y su primer super admin")
    for campo in ("administracion", "nombre", "email"):
        parser.add_argument("--" + campo, required=True)
    args = parser.parse_args()
    config = Configuracion()
    engine = crear_engine(config)
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    registrar_reset_del_tenant_al_devolver(engine)
    try:
        verificar_rol_de_aplicacion_seguro(engine)
        verificar_tablas_de_solo_agregar(engine)
        try:
            admin = asyncio.run(
                crear(
                    fabrica,
                    configuracion=config,
                    parametros=leer_parametros(config.proptech_parametros),
                    cola=AdaptadorColaArq(ajustes_redis_arq(config)),
                    administracion=args.administracion,
                    nombre=args.nombre,
                    email=args.email,
                    request_id=uuid4(),
                )
            )
        except ValueError as error:
            parser.exit(2, str(error) + "\n")
        print(admin)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
