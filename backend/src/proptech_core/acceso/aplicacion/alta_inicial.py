"""D10: alta inicial desde el operador, usando sólo proptech_app y un tenant nuevo."""

import argparse
import asyncio
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
)
from proptech_core.compartido.cola import AdaptadorColaArq
from proptech_core.compartido.conexion_redis import ajustes_redis_arq
from proptech_core.compartido.configuracion import Configuracion
from proptech_core.compartido.parametros import Parametros, leer_parametros


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
        sesion.execute(
            text("INSERT INTO administracion(id,nombre) VALUES (:id,:nombre)"),
            {"id": admin, "nombre": administracion},
        )
        persona = sesion.execute(
            text(
                "INSERT INTO persona(administracion_id,nombre,email) "
                "VALUES (:admin,:nombre,:email) RETURNING id"
            ),
            {"admin": admin, "nombre": nombre, "email": email},
        ).scalar_one()
        sesion.execute(
            text(
                "INSERT INTO asignacion_rol(administracion_id,persona_id,rol) "
                "VALUES (:admin,:persona,'super_admin')"
            ),
            {"admin": admin, "persona": persona},
        )
        identidad = Identidad(admin, persona)
        invitacion, sobre = crear_invitacion(sesion, identidad, persona, parametros, clave)
        registrar(
            sesion,
            identidad,
            EventoDeAcceso.ALTA_INICIAL,
            entidad="persona",
            entidad_id=persona,
            request_id=request_id,
        )
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
