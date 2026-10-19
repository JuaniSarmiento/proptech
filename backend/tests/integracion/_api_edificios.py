"""Cliente real del 3a: identidad inyectada, sesión y RLS de producción."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from proptech_api.acceso import identidad_actual
from proptech_core.acceso.dominio.identidad import Identidad

from ._edificios import BaseDeEdificio


@dataclass
class ApiEdificio:
    app: FastAPI
    cliente: TestClient
    base: BaseDeEdificio
    admin: UUID
    admin_ajena: UUID
    edificio: UUID
    otro: UUID
    ajeno: UUID
    unidad: UUID
    otra_unidad: UUID
    unidad_ajena: UUID
    grupo_ajeno: UUID
    personas: dict[str, UUID]

    def como(self, rol: str) -> None:
        self.app.dependency_overrides[identidad_actual] = lambda: Identidad(
            self.admin, self.personas[rol]
        )

    def ruta(self, sufijo: str = "") -> str:
        return f"/api/complejos/{self.edificio}{sufijo}"

    def filas(self, consulta: str, parametros: tuple[Any, ...] = ()) -> list[Any]:
        with self.base.conectar_app() as conexion, conexion.transaction():
            conexion.execute(
                "SELECT set_config('app.administracion_id', %s, true)", (str(self.admin),)
            )
            return list(conexion.execute(consulta, parametros).fetchall())
