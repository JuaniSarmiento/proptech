"""Cuenta de unidad y candado por cuenta (D2, E2)."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from proptech_core.acceso.dominio.identidad import Identidad
from proptech_core.cuenta_corriente.aplicacion.errores import (
    AislamientoNoAdmitido,
    BloqueoFueraDeOrden,
    CandadoIncompleto,
    IdentidadDeOtraAdministracion,
    NoEncontrado,
    exigir_transaccion,
    traducir,
)

_TOMADAS = "cuenta_corriente.cuentas_bloqueadas"
_IDS = bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))


def tenant(sesion: Session) -> UUID:
    valor = sesion.execute(
        text("SELECT nullif(current_setting('app.administracion_id', true), '')::uuid")
    ).scalar_one()
    if valor is None:
        raise NoEncontrado
    return UUID(str(valor))


def exigir_identidad(sesion: Session, identidad: Identidad) -> UUID:
    """D3: el INSERT toma la administración de la identidad, que tiene que ser la del tenant."""
    administracion = tenant(sesion)
    if identidad.administracion_id != administracion:
        raise IdentidadDeOtraAdministracion("la identidad no es de la administración de la sesión")
    return administracion


def _exigir_read_committed(sesion: Session) -> None:
    vigente = sesion.execute(text("SELECT current_setting('transaction_isolation')")).scalar_one()
    if vigente != "read committed":
        raise AislamientoNoAdmitido(f"el candado exige read committed, no {vigente}")


def bloquear_cuentas(sesion: Session, cuenta_ids: Sequence[UUID]) -> None:
    """Pública e idempotente dentro de la transacción (D2, D3, RC-05).

    Quien va a tocar varias cuentas las bloquea todas en una sola llamada antes de escribir y antes
    de leer lo que decide la escritura (RC2-03). Volver a pedir una cuenta ya tomada no falla; sumar
    una cuenta menor que la mayor ya tomada sí (RC2-01): ése es el orden cruzado que interbloquea.

    El SELECT ... FOR UPDATE se ejecuta SIEMPRE, también para las cuentas que el caché cree tomadas
    (RB4B-02): un ROLLBACK TO SAVEPOINT del llamador suelta el candado en PostgreSQL y el caché no
    se entera. En PostgreSQL volver a pedir un candado propio es idempotente; el caché sólo sirve
    para el chequeo de orden.
    """
    exigir_transaccion(sesion)
    _exigir_read_committed(sesion)
    ids = sorted(set(cuenta_ids))  # RC2-02: un id repetido no es un candado faltante.
    if not ids:
        return
    raiz = sesion.get_transaction()
    previo = sesion.info.get(_TOMADAS)
    tomadas: set[UUID] = previo[1] if previo is not None and previo[0] is raiz else set()
    nuevas = [i for i in ids if i not in tomadas]
    if tomadas and nuevas and min(nuevas) < max(tomadas):
        raise BloqueoFueraDeOrden("una cuenta nueva menor que la mayor ya bloqueada")
    administracion = tenant(sesion)
    sesion.execute(
        text(
            "INSERT INTO candado_de_cuenta (cuenta_id, administracion_id) "
            "SELECT x, :administracion FROM unnest(:ids) AS x "
            "WHERE EXISTS (SELECT 1 FROM cuenta c WHERE c.id = x) "
            "ORDER BY x ON CONFLICT (cuenta_id) DO NOTHING"
        ).bindparams(_IDS),
        {"ids": ids, "administracion": administracion},
    )
    filas = (
        sesion.execute(
            text(
                "SELECT cuenta_id FROM candado_de_cuenta WHERE cuenta_id = ANY(:ids) "
                "ORDER BY cuenta_id FOR UPDATE"
            ).bindparams(_IDS),
            {"ids": ids},
        )
        .scalars()
        .all()
    )
    if len(filas) != len(ids):
        existentes = sesion.execute(
            text("SELECT count(*) FROM cuenta WHERE id = ANY(:ids)").bindparams(_IDS),
            {"ids": ids},
        ).scalar_one()
        if existentes != len(ids):
            raise NoEncontrado
        raise CandadoIncompleto("faltan filas de candado para las cuentas pedidas")
    sesion.info[_TOMADAS] = (raiz, tomadas | set(ids))


def crear_cuentas_de_unidades(
    sesion: Session, *, complejo_id: UUID, unidad_ids: Sequence[UUID]
) -> dict[UUID, UUID]:
    """Cuentas de varias unidades en UNA sentencia ordenada por unidad_id, y sus candados en la
    misma transacción, en otra sentencia ordenada por cuenta_id (D2, D4 paso 4, RC-03)."""
    exigir_transaccion(sesion)
    unidades = sorted(set(unidad_ids))
    administracion = tenant(sesion)
    ahora = datetime.now(UTC)
    # E11: el libro no nombra `unidad` en su SQL; la unidad de otro edificio o de otra
    # administración la rechaza la FK compuesta, traducida a NoEncontrado (D4).
    with traducir(sesion, {}):  # fk_cuenta_unidad, fk_cuenta_complejo: 23503, NoEncontrado
        sesion.execute(
            text(
                "INSERT INTO cuenta (id, administracion_id, complejo_id, unidad_id, creada_en) "
                "SELECT gen_random_uuid(), :administracion, :complejo, u, :ahora "
                "FROM unnest(:ids) AS u ORDER BY u "
                "ON CONFLICT (administracion_id, unidad_id) WHERE unidad_id IS NOT NULL DO NOTHING"
            ).bindparams(_IDS),
            {
                "administracion": administracion,
                "complejo": complejo_id,
                "ids": unidades,
                "ahora": ahora,
            },
        )
    filas = sesion.execute(
        text(
            "SELECT unidad_id, id, complejo_id FROM cuenta WHERE unidad_id = ANY(:ids)"
        ).bindparams(_IDS),
        {"ids": unidades},
    ).all()
    if any(f.complejo_id != complejo_id for f in filas) or len(filas) != len(unidades):
        raise NoEncontrado
    cuentas = {f.unidad_id: f.id for f in filas}
    sesion.execute(
        text(
            "INSERT INTO candado_de_cuenta (cuenta_id, administracion_id) "
            "SELECT x, :administracion FROM unnest(:ids) AS x ORDER BY x "
            "ON CONFLICT (cuenta_id) DO NOTHING"
        ).bindparams(_IDS),
        {"administracion": administracion, "ids": sorted(cuentas.values())},
    )
    return cuentas


def cuenta_de_unidad(sesion: Session, *, complejo_id: UUID, unidad_id: UUID) -> UUID:
    """Crea si falta, con su candado en la misma transacción; dos pedidos dan la misma cuenta."""
    return crear_cuentas_de_unidades(sesion, complejo_id=complejo_id, unidad_ids=[unidad_id])[
        unidad_id
    ]
