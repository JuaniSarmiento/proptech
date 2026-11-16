"""Preliquidación de un período (HU-A4, D-157): lee, calcula y devuelve; nunca escribe.

Todo lo ajeno se lee por la `aplicacion` de su dueño: el padrón, los grupos y la configuración
(`complejos`), los gastos y cargos del período (`gastos`), el interés y los períodos emitidos
(`cuenta_corriente`). El reparto, el fondo y la huella son funciones puras de `dominio`.
"""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.compartido.porcentaje import Porcentaje
from proptech_core.complejos.aplicacion import categorias, grupos, unidades
from proptech_core.complejos.aplicacion.lectura import cargar_complejo, configuracion_vigente
from proptech_core.cuenta_corriente.aplicacion.liquidar import intereses_a_cobrar, periodos_emitidos
from proptech_core.gastos.aplicacion.cargos_particulares import cargos_aprobados_del_periodo
from proptech_core.gastos.aplicacion.gastos import (
    gastos_por_resolver_del_periodo,
    lineas_del_periodo,
    obligatorios_faltantes,
)
from proptech_core.liquidacion.aplicacion.errores import Conflicto, EntradaInvalida
from proptech_core.liquidacion.dominio.controles import ContextoDeControles, InformeDeGrupo
from proptech_core.liquidacion.dominio.periodos import motivo_de_rechazo
from proptech_core.liquidacion.dominio.preliquidacion import (
    CargoParticular,
    CategoriaDeGasto,
    DatosDeLaPreliquidacion,
    LineaDeGasto,
    preliquidar,
)
from proptech_core.liquidacion.dominio.reparto import (
    GrupoDelEdificio,
    MiembroDelGrupo,
    SinBaseDeReparto,
    UnidadDelPadron,
)

_CERO = Decimal("0")


def _uuid(valor: Any) -> UUID:
    return valor if isinstance(valor, UUID) else UUID(str(valor))


def _decimal(valor: Any) -> Decimal:
    return _CERO if valor is None else Decimal(str(valor))


def _padron(sesion: Session, complejo_id: UUID) -> dict[UUID, UnidadDelPadron]:
    filas = unidades.listar_unidades(sesion, complejo_id)["unidades"]
    return {
        (i := _uuid(f["id"])): UnidadDelPadron(
            i, f["identificador"], _decimal(f["coeficiente"]), _decimal(f["superficie_m2"])
        )
        for f in filas
    }


def _grupos(sesion: Session, complejo_id: UUID) -> list[GrupoDelEdificio]:
    return [
        GrupoDelEdificio(
            _uuid(g["id"]),
            g["nombre"],
            g["metodo"],
            bool(g["es_generales"]),
            ()
            if g["es_generales"]
            else tuple(
                MiembroDelGrupo(
                    _uuid(m["unidad_id"]),
                    None if m["coeficiente"] is None else _decimal(m["coeficiente"]),
                )
                for m in g["unidades"]
            ),
        )
        for g in grupos.listar_grupos(sesion, complejo_id)
    ]


def _contexto_de_controles(
    sesion: Session, complejo_id: UUID, periodo: date, version: dict[str, Any]
) -> ContextoDeControles:
    """Lo que necesitan los controles de R34, leído por la `aplicacion` de cada dueño. Sólo
    cuentan Generales y los grupos activos con coeficientes propios (D-100)."""
    complejo = cargar_complejo(sesion, complejo_id)
    if complejo is None:  # pragma: no cover - el router ya lo cargó
        raise Conflicto("complejo", "no_encontrado")
    informes = tuple(
        InformeDeGrupo(
            str(g["id"]),
            g["nombre"],
            g["informe"]["suma"],
            g["informe"]["diferencia"],
            g["informe"]["estado"],
        )
        for g in grupos.listar_grupos(sesion, complejo_id, solo_activos=True)
        if g["informe"] is not None
    )
    por_resolver = gastos_por_resolver_del_periodo(sesion, complejo_id, periodo)
    faltantes = obligatorios_faltantes(sesion, complejo_id, periodo)["faltantes"]
    return ContextoDeControles(
        estado_migracion=complejo.estado_migracion,
        informes=informes,
        modalidad_de_vencimiento=str(version["modalidad_de_vencimiento"]),
        gastos_en_revision=tuple(por_resolver["en_revision"]),
        gastos_sin_ia=tuple(por_resolver["sin_ia"]),
        categorias_faltantes=tuple((str(c["id"]), str(c["nombre"])) for c in faltantes),
    )


def preliquidar_periodo(sesion: Session, *, complejo_id: UUID, periodo: date) -> dict[str, Any]:
    """El cuerpo de la preliquidación de `periodo` (día 1). Rechaza con `Conflicto` si el período
    ya está emitido o si el anterior no lo está (R40), o si el edificio no tiene configuración
    vigente el primer día del período."""
    if periodo.day != 1:
        raise EntradaInvalida("periodo")
    motivo = motivo_de_rechazo(periodo, periodos_emitidos(sesion, complejo_id=complejo_id))
    if motivo is not None:
        raise Conflicto("periodo", motivo)
    version = configuracion_vigente(sesion, complejo_id, periodo)
    if version is None:
        raise Conflicto("configuracion", "configuracion_sin_definir")

    lineas = [
        LineaDeGasto(
            _uuid(f["grupo_id"]),
            f["tipo"],
            _uuid(f["categoria_id"]),
            Dinero(f["importe"]),
            bool(f["es_nota_de_credito"]),
        )
        for f in lineas_del_periodo(sesion, complejo_id, periodo)
    ]
    cargos = [
        CargoParticular(_uuid(unidad_id), c["concepto"], Dinero(c["importe"]))
        for unidad_id, de_la_unidad in cargos_aprobados_del_periodo(sesion, complejo_id, periodo)[
            "unidades"
        ].items()
        for c in de_la_unidad["cargos"]
    ]
    datos = DatosDeLaPreliquidacion(
        complejo_id=complejo_id,
        periodo=periodo,
        vencimiento=periodo.replace(day=int(version["dia_de_vencimiento"])),
        porcentaje_fondo=Porcentaje(version["porcentaje_fondo"]),
        version_de_configuracion=str(version["id"]),
        unidades=_padron(sesion, complejo_id),
        grupos=_grupos(sesion, complejo_id),
        categorias={
            (i := _uuid(c["id"])): CategoriaDeGasto(i, c["nombre"], int(c["orden"]))
            for c in categorias.listar_categorias(sesion, complejo_id)
        },
        lineas=lineas,
        cargos=cargos,
        intereses=intereses_a_cobrar(sesion, complejo_id=complejo_id, periodo=periodo),
        contexto_de_controles=_contexto_de_controles(sesion, complejo_id, periodo, version),
    )
    try:
        return preliquidar(datos)
    except SinBaseDeReparto:
        raise Conflicto("grupo", "grupo_sin_base_de_reparto") from None
