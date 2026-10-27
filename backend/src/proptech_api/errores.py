"""Formas existentes de error HTTP, declaradas una vez para la ruta del libro (E9)."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class Error401(BaseModel):
    detail: str


class PermisoFaltante(BaseModel):
    detalle: Literal["sin_permiso"]
    permiso_faltante: str


class Error403(BaseModel):
    detail: PermisoFaltante


class Error404(BaseModel):
    detail: Literal["no encontrado"]


class Error409(BaseModel):
    detail: Literal["conflicto"]
    campo: str


class CampoInvalido(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class Error422(BaseModel):
    detail: list[CampoInvalido]


class Error500(BaseModel):
    error: Literal["interno"]
    request_id: UUID


class Error503(BaseModel):
    detail: Literal["temporalmente no disponible"]


RESPUESTAS_DE_ERROR: dict[int | str, dict[str, Any]] = {
    codigo: {"model": modelo}
    for codigo, modelo in (
        (401, Error401),
        (403, Error403),
        (404, Error404),
        (409, Error409),
        (422, Error422),
        (500, Error500),
        (503, Error503),
    )
}
