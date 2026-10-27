"""Lector de `config/georef/` (D1): provincias, departamentos y localidades
de Argentina, reducidos a id/nombre/id-del-padre, cargados una vez al
arrancar. Ningún error repite el contenido del archivo (L-002, L-007,
L-008): sólo nombra el archivo y, cuando aplica, el motivo general."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class GeorefInvalido(Exception):
    """Un archivo de `config/georef/` falta, está vacío, truncado, no es del
    tipo esperado, tiene un id repetido o un padre que no existe."""


@dataclass(frozen=True)
class Provincia:
    id: str
    nombre: str


@dataclass(frozen=True)
class Departamento:
    id: str
    nombre: str
    provincia_id: str


@dataclass(frozen=True)
class Localidad:
    id: str
    nombre: str
    departamento_id: str


@dataclass(frozen=True)
class Georef:
    provincias: tuple[Provincia, ...]
    departamentos: tuple[Departamento, ...]
    localidades: tuple[Localidad, ...]

    def listar_provincias(self) -> list[Provincia]:
        return sorted(self.provincias, key=lambda p: p.nombre)

    def _provincia_existe(self, provincia_id: str) -> bool:
        return any(p.id == provincia_id for p in self.provincias)

    def _departamento(self, departamento_id: str) -> Departamento | None:
        return next((d for d in self.departamentos if d.id == departamento_id), None)

    def _localidad(self, localidad_id: str) -> Localidad | None:
        return next((loc for loc in self.localidades if loc.id == localidad_id), None)

    def departamentos_de(self, provincia_id: str) -> list[Departamento] | None:
        if not self._provincia_existe(provincia_id):
            return None
        return sorted(
            (d for d in self.departamentos if d.provincia_id == provincia_id),
            key=lambda d: d.nombre,
        )

    def localidades_de(self, departamento_id: str) -> list[Localidad] | None:
        if self._departamento(departamento_id) is None:
            return None
        return sorted(
            (loc for loc in self.localidades if loc.departamento_id == departamento_id),
            key=lambda loc: loc.nombre,
        )

    def existe_el_trio(self, provincia_id: str, departamento_id: str, localidad_id: str) -> bool:
        localidad = self._localidad(localidad_id)
        if localidad is None or localidad.departamento_id != departamento_id:
            return False
        departamento = self._departamento(departamento_id)
        if departamento is None or departamento.provincia_id != provincia_id:
            return False
        return self._provincia_existe(provincia_id)

    def nombre_de_localidad(self, localidad_id: str) -> str | None:
        localidad = self._localidad(localidad_id)
        return None if localidad is None else localidad.nombre

    def campo_incoherente(
        self, provincia_id: str, departamento_id: str, localidad_id: str
    ) -> str | None:
        """`None` si el trío es coherente; si no, el nombre del primer campo
        que no encadena, en el orden provincia → departamento → localidad
        (D2, tarea 2.3): "provincia_id", "departamento_id" o "localidad_id".
        La comparación de padres (no sólo la existencia de cada id) es la
        garantía específica que este método agrega sobre `existe_el_trio`."""
        if not self._provincia_existe(provincia_id):
            return "provincia_id"
        departamento = self._departamento(departamento_id)
        if departamento is None or departamento.provincia_id != provincia_id:
            return "departamento_id"
        localidad = self._localidad(localidad_id)
        if localidad is None or localidad.departamento_id != departamento_id:
            return "localidad_id"
        return None


def _leer_lista_json(ruta: Path) -> list[dict[str, object]]:
    try:
        contenido = ruta.read_bytes()
    except OSError:
        raise GeorefInvalido(f"no se puede leer el archivo: {ruta.name}") from None
    if not contenido:
        raise GeorefInvalido(f"archivo vacío: {ruta.name}")
    try:
        datos = json.loads(contenido.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise GeorefInvalido(f"archivo mal formado o truncado: {ruta.name}") from None
    if not isinstance(datos, list):
        raise GeorefInvalido(f"el archivo debe ser una lista de registros: {ruta.name}")
    return datos


def _campos_texto(fila: object, nombre_archivo: str, *claves: str) -> tuple[str, ...]:
    if not isinstance(fila, dict):
        raise GeorefInvalido(f"{nombre_archivo}: registro mal formado")
    valores = []
    for clave in claves:
        valor = fila.get(clave)
        if not isinstance(valor, str) or not valor:
            raise GeorefInvalido(f"{nombre_archivo}: registro mal formado")
        valores.append(valor)
    return tuple(valores)


def _provincias(datos: list[dict[str, object]]) -> tuple[Provincia, ...]:
    vistos: set[str] = set()
    resultado: list[Provincia] = []
    for fila in datos:
        id_, nombre = _campos_texto(fila, "provincias.json", "id", "nombre")
        if id_ in vistos:
            raise GeorefInvalido("provincias.json: id repetido")
        vistos.add(id_)
        resultado.append(Provincia(id=id_, nombre=nombre))
    return tuple(resultado)


def _departamentos(
    datos: list[dict[str, object]], provincias_validas: set[str]
) -> tuple[Departamento, ...]:
    vistos: set[str] = set()
    resultado: list[Departamento] = []
    for fila in datos:
        id_, nombre, padre = _campos_texto(
            fila, "departamentos.json", "id", "nombre", "provincia_id"
        )
        if id_ in vistos:
            raise GeorefInvalido("departamentos.json: id repetido")
        if padre not in provincias_validas:
            raise GeorefInvalido("departamentos.json: provincia_id inexistente")
        vistos.add(id_)
        resultado.append(Departamento(id=id_, nombre=nombre, provincia_id=padre))
    return tuple(resultado)


def _localidades(
    datos: list[dict[str, object]], departamentos_validos: set[str]
) -> tuple[Localidad, ...]:
    vistos: set[str] = set()
    resultado: list[Localidad] = []
    for fila in datos:
        id_, nombre, padre = _campos_texto(
            fila, "localidades.json", "id", "nombre", "departamento_id"
        )
        if id_ in vistos:
            raise GeorefInvalido("localidades.json: id repetido")
        if padre not in departamentos_validos:
            raise GeorefInvalido("localidades.json: departamento_id inexistente")
        vistos.add(id_)
        resultado.append(Localidad(id=id_, nombre=nombre, departamento_id=padre))
    return tuple(resultado)


def leer_georef(directorio: str) -> Georef:
    """Lee y valida los tres archivos de una vez (estructura, ids únicos,
    padres existentes). Pensado para llamarse una sola vez al arrancar."""
    base = Path(directorio)
    provincias = _provincias(_leer_lista_json(base / "provincias.json"))
    ids_provincias = {p.id for p in provincias}
    departamentos = _departamentos(_leer_lista_json(base / "departamentos.json"), ids_provincias)
    ids_departamentos = {d.id for d in departamentos}
    localidades = _localidades(_leer_lista_json(base / "localidades.json"), ids_departamentos)
    return Georef(provincias=provincias, departamentos=departamentos, localidades=localidades)
