"""Datos inventados del login, sembrados como app en dos administraciones."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from ._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad


@dataclass(frozen=True)
class DatosDeLogin:
    administraciones: tuple[UUID, UUID]
    personas: tuple[UUID, UUID]
    persona_ajena: UUID
    sub: str
    sub_ajeno: str


def preparar_personas(base: BaseDeEdificio) -> DatosDeLogin:
    datos = DatosDeLogin(
        (uuid4(), uuid4()),
        (uuid4(), uuid4()),
        uuid4(),
        "user_" + uuid4().hex,
        "user_" + uuid4().hex,
    )
    with base.conectar_app() as conexion, conexion.transaction():
        for admin, persona in zip(datos.administraciones, datos.personas, strict=True):
            fijar_tenant(conexion, admin)
            conexion.execute(
                "INSERT INTO administracion (id,nombre) VALUES (%s,'Ficticia')", (admin,)
            )
            conexion.execute(
                "INSERT INTO persona (id,administracion_id,nombre,clerk_usuario_id) "
                "VALUES (%s,%s,'Ficticia',%s)",
                (persona, admin, datos.sub),
            )
            complejo = uuid4()
            conexion.execute(
                "INSERT INTO complejo (id,administracion_id,nombre,localidad) "
                "VALUES (%s,%s,'Ficticio','Mendoza')",
                (complejo, admin),
            )
            insertar_unidad(conexion, admin, complejo)
            conexion.execute(
                "INSERT INTO asignacion_rol (administracion_id,persona_id,rol) "
                "VALUES (%s,%s,'super_admin')",
                (admin, persona),
            )
        conexion.execute(
            "INSERT INTO persona (id,administracion_id,nombre,clerk_usuario_id) "
            "VALUES (%s,%s,'Otra ficticia',%s)",
            (datos.persona_ajena, datos.administraciones[1], datos.sub_ajeno),
        )
    return datos
