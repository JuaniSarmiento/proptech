"""Preliquidación de un período (HU-A4): lo que paga cada unidad, sin tocar ninguna base."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import localcontext
from typing import Any, Literal
from uuid import UUID

from proptech_core.compartido.dinero import Dinero, sumar
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.compartido.reparto import clave_de_orden_natural, redondear_al_centavo
from proptech_core.liquidacion.dominio.fondo import fondo_de_reserva
from proptech_core.liquidacion.dominio.huella import huella_de
from proptech_core.liquidacion.dominio.reparto import (
    GrupoDelEdificio,
    UnidadDelPadron,
    pesos_del_grupo,
    repartir_en_grupo,
)

_CERO = Dinero("0.00")
_BLOQUES: tuple[Bloque, ...] = ("ordinario", "extraordinario")

Bloque = Literal["ordinario", "extraordinario"]


@dataclass(frozen=True)
class LineaDeGasto:
    """Un gasto aprobado o una nota de crédito del período, siempre con importe positivo: la nota
    se resta por `es_nota_de_credito`."""

    grupo_id: UUID
    bloque: Bloque
    categoria_id: UUID
    importe: Dinero
    es_nota_de_credito: bool = False


@dataclass(frozen=True)
class CategoriaDeGasto:
    id: UUID
    nombre: str
    orden: int


@dataclass(frozen=True)
class CargoParticular:
    unidad_id: UUID
    concepto: str
    importe: Dinero


@dataclass(frozen=True)
class DatosDeLaPreliquidacion:
    complejo_id: UUID
    periodo: date
    vencimiento: date
    porcentaje_fondo: Porcentaje
    version_de_configuracion: str
    unidades: Mapping[UUID, UnidadDelPadron]
    grupos: Sequence[GrupoDelEdificio]
    categorias: Mapping[UUID, CategoriaDeGasto]
    lineas: Sequence[LineaDeGasto]
    cargos: Sequence[CargoParticular] = field(default_factory=tuple)
    intereses: Mapping[UUID, Dinero] = field(default_factory=dict)


def _con_signo(linea: LineaDeGasto) -> Dinero:
    return -linea.importe if linea.es_nota_de_credito else linea.importe


def _porcentaje_de(parte: Dinero, todo: Dinero) -> str:
    """Porcentaje con dos decimales, medio hacia arriba (R16); sobre un bloque en cero, 0,00."""
    if todo == _CERO:
        return "0.00"
    with localcontext() as contexto:
        contexto.prec = 32
        return redondear_al_centavo(parte.decimal * 100 / todo.decimal).a_texto()


def _bloques_por_categoria(
    datos: DatosDeLaPreliquidacion,
) -> dict[str, dict[str, Any]]:
    resultado: dict[str, dict[str, Any]] = {}
    for bloque in _BLOQUES:
        por_categoria: dict[UUID, Dinero] = defaultdict(lambda: _CERO)
        for linea in datos.lineas:
            if linea.bloque == bloque:
                por_categoria[linea.categoria_id] += _con_signo(linea)
        subtotal = sumar(por_categoria.values())
        ordenadas = sorted(
            por_categoria.items(),
            key=lambda par: (
                datos.categorias[par[0]].orden,
                datos.categorias[par[0]].nombre,
                str(par[0]),
            ),
        )
        resultado[bloque] = {
            "subtotal": subtotal.a_texto(),
            "categorias": [
                {
                    "categoria_id": str(categoria),
                    "nombre": datos.categorias[categoria].nombre,
                    "importe": importe.a_texto(),
                    "porcentaje": _porcentaje_de(importe, subtotal),
                }
                for categoria, importe in ordenadas
            ],
        }
    return resultado


def preliquidar(datos: DatosDeLaPreliquidacion) -> dict[str, Any]:
    """Todo lo que paga cada unidad, como el cuerpo de la respuesta (montos como texto).

    Cada gasto va al grupo que lo cargó y se reparte entre sus miembros según su método, un bloque
    (ordinario, extraordinario) por vez, con mayor resto (R07): un grupo cuyos miembros no tienen
    peso levanta `SinBaseDeReparto`. El fondo sale de la ordinaria prorrateada de cada unidad, sin
    cargos ni intereses (R13, R15). El interés ya viene calculado, con la misma función de la
    emisión (E4)."""
    orden = sorted(
        datos.unidades.values(), key=lambda u: clave_de_orden_natural(u.identificador, u.id)
    )
    grupos = {g.id: g for g in datos.grupos}
    netos: dict[UUID, dict[Bloque, Dinero]] = defaultdict(lambda: {b: _CERO for b in _BLOQUES})
    for linea in datos.lineas:
        netos[linea.grupo_id][linea.bloque] += _con_signo(linea)

    ordinaria = {u.id: _CERO for u in orden}
    extraordinaria = {u.id: _CERO for u in orden}
    por_grupo: dict[UUID, dict[UUID, dict[Bloque, Dinero]]] = {u.id: {} for u in orden}
    con_gastos = sorted(netos, key=lambda g: (not grupos[g].es_generales, grupos[g].nombre, str(g)))
    for grupo_id in con_gastos:
        grupo = grupos[grupo_id]
        participantes = pesos_del_grupo(grupo, datos.unidades)
        partes: dict[Bloque, dict[UUID, Dinero]] = {
            bloque: repartir_en_grupo(netos[grupo_id][bloque], grupo, datos.unidades)
            for bloque in _BLOQUES
        }
        for unidad_id in participantes:
            por_grupo[unidad_id][grupo_id] = {b: partes[b][unidad_id] for b in _BLOQUES}
            ordinaria[unidad_id] += partes["ordinario"][unidad_id]
            extraordinaria[unidad_id] += partes["extraordinario"][unidad_id]

    fondo = fondo_de_reserva(ordinaria, datos.porcentaje_fondo, datos.unidades)
    cargos: dict[UUID, list[CargoParticular]] = defaultdict(list)
    for cargo in sorted(datos.cargos, key=lambda c: (c.concepto, c.importe.a_texto())):
        cargos[cargo.unidad_id].append(cargo)

    unidades: list[dict[str, Any]] = []
    for unidad in orden:
        i = unidad.id
        suma_de_cargos = sumar(c.importe for c in cargos[i])
        interes = datos.intereses.get(i, _CERO)
        obligacion = ordinaria[i] + fondo[i] + extraordinaria[i] + suma_de_cargos
        unidades.append(
            {
                "unidad_id": str(i),
                "identificador": unidad.identificador,
                "ordinaria": ordinaria[i].a_texto(),
                "fondo_de_reserva": fondo[i].a_texto(),
                "extraordinaria": extraordinaria[i].a_texto(),
                "cargos_particulares": [
                    {"concepto": c.concepto, "importe": c.importe.a_texto()} for c in cargos[i]
                ],
                "intereses": interes.a_texto(),
                "total": (obligacion + interes).a_texto(),
                "sin_obligacion": obligacion == _CERO,
                "por_grupo": [
                    {
                        "grupo_id": str(g),
                        "ordinaria": por_grupo[i][g]["ordinario"].a_texto(),
                        "extraordinaria": por_grupo[i][g]["extraordinario"].a_texto(),
                    }
                    for g in con_gastos
                    if g in por_grupo[i]
                ],
            }
        )

    bruto = sumar(x.importe for x in datos.lineas if not x.es_nota_de_credito)
    notas = sumar(x.importe for x in datos.lineas if x.es_nota_de_credito)
    total_fondo = sumar(fondo.values())
    total_cargos = sumar(c.importe for c in datos.cargos)
    total_intereses = sumar(datos.intereses.get(u.id, _CERO) for u in orden)
    prorrateado = bruto - notas + total_fondo
    cuerpo: dict[str, Any] = {
        "complejo_id": str(datos.complejo_id),
        "periodo": datos.periodo.isoformat(),
        "vencimiento": datos.vencimiento.isoformat(),
        "porcentaje_fondo": datos.porcentaje_fondo.a_texto(),
        "totales": {
            "gastos": bruto.a_texto(),
            "notas_de_credito": notas.a_texto(),
            "fondo_de_reserva": total_fondo.a_texto(),
            "prorrateado": prorrateado.a_texto(),
            "cargos_particulares": total_cargos.a_texto(),
            "intereses": total_intereses.a_texto(),
            "total": (prorrateado + total_cargos + total_intereses).a_texto(),
        },
        "bloques": _bloques_por_categoria(datos),
        "grupos": [
            {
                "grupo_id": str(g),
                "nombre": grupos[g].nombre,
                "metodo": grupos[g].metodo,
                "ordinario": netos[g]["ordinario"].a_texto(),
                "extraordinario": netos[g]["extraordinario"].a_texto(),
            }
            for g in con_gastos
        ],
        "unidades": unidades,
        "controles": [],
    }
    cuerpo["huella"] = huella_de(cuerpo, datos.version_de_configuracion)
    return cuerpo
