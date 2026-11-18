"""La base de los pagos informados (8, H-018, `0044`, D-163, D-165): el número de operación único
por edificio frenado por la propia base aunque dos pedidos lleguen a la vez, un pago rechazado que
lo libera, y lo que la base exige sin pasar por la API (un solo desenlace por pago, edificios que
no se cruzan)."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
import pytest

from ._edificios import BaseDeEdificio, fijar_tenant, insertar_unidad

pytestmark = pytest.mark.integracion


@dataclass(frozen=True)
class Datos:
    admin: UUID
    persona: UUID
    edificio: UUID
    otro: UUID
    unidad: UUID
    unidad_otro: UUID


@pytest.fixture(scope="module")
def datos(base_del_edificio: BaseDeEdificio) -> Datos:
    admin, persona, edificio, otro = uuid4(), uuid4(), uuid4(), uuid4()
    with base_del_edificio.conectar_app() as c, c.transaction():
        fijar_tenant(c, admin)
        c.execute("INSERT INTO administracion (id, nombre) VALUES (%s, 'Ficticia')", (admin,))
        c.execute(
            "INSERT INTO persona (id, administracion_id, nombre) VALUES (%s, %s, 'Persona')",
            (persona, admin),
        )
        for complejo in (edificio, otro):
            c.execute(
                "INSERT INTO complejo (id, administracion_id, nombre, localidad) "
                "VALUES (%s, %s, 'Edificio', 'Mendoza')",
                (complejo, admin),
            )
        unidad = insertar_unidad(c, admin, edificio, "1A")
        unidad_otro = insertar_unidad(c, admin, otro, "9A")
    return Datos(admin, persona, edificio, otro, unidad, unidad_otro)


def _comprobante(c: psycopg.Connection, d: Datos, complejo: UUID | None = None) -> UUID:
    contenido = uuid4().bytes + b"\x89PNG\r\n\x1a\n"
    fila = c.execute(
        "INSERT INTO comprobante_de_pago (administracion_id, complejo_id, contenido, sha256, tipo, "
        "tamano, subido_por) VALUES (%s, %s, %s, %s, 'png', %s, %s) RETURNING id",
        (
            d.admin,
            complejo or d.edificio,
            contenido,
            hashlib.sha256(contenido).hexdigest(),
            len(contenido),
            d.persona,
        ),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def _pago(
    c: psycopg.Connection,
    d: Datos,
    *,
    banco: str = "banconacion",
    numero: str = "12345678",
    complejo: UUID | None = None,
) -> UUID:
    comprobante = _comprobante(c, d, complejo)
    fila = c.execute(
        "INSERT INTO pago_informado (administracion_id, complejo_id, comprobante_id, banco, "
        "banco_normalizado, numero_de_operacion, numero_normalizado, fecha_de_transferencia, "
        "monto, informado_por) VALUES (%s, %s, %s, %s, %s, %s, %s, '2026-11-05', '100.00', %s) "
        "RETURNING id",
        (d.admin, complejo or d.edificio, comprobante, banco, banco, numero, numero, d.persona),
    ).fetchone()
    assert fila is not None
    return UUID(str(fila[0]))


def _evento(c: psycopg.Connection, d: Datos, pago: UUID, tipo: str, motivo: str | None) -> None:
    c.execute(
        "INSERT INTO evento_de_pago (administracion_id, pago_id, tipo, motivo, registrado_por) "
        "VALUES (%s, %s, %s, %s, %s)",
        (d.admin, pago, tipo, motivo, d.persona),
    )


def _conexion(base: BaseDeEdificio, d: Datos) -> psycopg.Connection:
    c = base.conectar_app()
    c.autocommit = False
    fijar_tenant(c, d.admin)
    return c


def test_dos_pedidos_simultaneos_con_el_mismo_numero_no_pasan_los_dos(
    base_del_edificio: BaseDeEdificio, datos: Datos
) -> None:
    """La carrera la frena la base (D-165): el segundo INSERT espera al primero y, cuando éste
    confirma, ve su fila y falla con la restricción del número."""
    primero = _conexion(base_del_edificio, datos)
    segundo = _conexion(base_del_edificio, datos)
    try:
        _pago(primero, datos, numero="carrera-1")
        resultado: list[object] = []

        def insertar_el_segundo() -> None:
            try:
                _pago(segundo, datos, numero="carrera-1")
                segundo.commit()
                resultado.append("inserto")
            except psycopg.errors.UniqueViolation as error:
                resultado.append(error.diag.constraint_name)

        hilo = threading.Thread(target=insertar_el_segundo)
        hilo.start()
        hilo.join(timeout=1.0)
        assert hilo.is_alive(), "el segundo INSERT tenía que esperar el candado del primero"
        primero.commit()
        hilo.join(timeout=10.0)
        assert resultado == ["uq_pago_numero_por_edificio"], resultado
    finally:
        primero.close()
        segundo.close()


def test_un_rechazo_libera_el_numero_y_otro_edificio_nunca_choca(
    base_del_edificio: BaseDeEdificio, datos: Datos
) -> None:
    with _conexion(base_del_edificio, datos) as c:
        viejo = _pago(c, datos, numero="libera-1")
        with pytest.raises(psycopg.errors.UniqueViolation):
            with c.transaction():
                _pago(c, datos, numero="libera-1")
        _pago(c, datos, numero="libera-1", complejo=datos.otro)
        _evento(c, datos, viejo, "rechazado", "Motivo ficticio")
        _pago(c, datos, numero="libera-1")
        c.commit()


def test_un_pago_tiene_un_solo_desenlace(base_del_edificio: BaseDeEdificio, datos: Datos) -> None:
    with _conexion(base_del_edificio, datos) as c:
        pago = _pago(c, datos, numero="desenlace-1")
        _evento(c, datos, pago, "confirmado", None)
        for tipo in ("confirmado", "rechazado"):
            with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
                _evento(c, datos, pago, tipo, "Motivo ficticio")
        _evento(c, datos, pago, "reimputado", "Reimputado")
        _evento(c, datos, pago, "revertido", "Revertido")
        with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
            _evento(c, datos, pago, "revertido", "Otra vez")
        c.rollback()


def test_el_evento_exige_motivo_salvo_confirmado_y_un_tipo_conocido(
    base_del_edificio: BaseDeEdificio, datos: Datos
) -> None:
    with _conexion(base_del_edificio, datos) as c:
        pago = _pago(c, datos, numero="motivo-1")
        for tipo, motivo in (("rechazado", None), ("rechazado", "  "), ("inventado", "x")):
            with pytest.raises(psycopg.errors.CheckViolation), c.transaction():
                _evento(c, datos, pago, tipo, motivo)
        c.rollback()


def test_una_parte_no_cruza_de_edificio(base_del_edificio: BaseDeEdificio, datos: Datos) -> None:
    """Una unidad de otro edificio no entra como parte de un pago, ni siquiera por SQL."""
    with _conexion(base_del_edificio, datos) as c:
        pago = _pago(c, datos, numero="cruce-1")
        with pytest.raises(psycopg.errors.ForeignKeyViolation), c.transaction():
            c.execute(
                "INSERT INTO parte_de_pago (administracion_id, complejo_id, pago_id, unidad_id, "
                "importe) VALUES (%s, %s, %s, %s, '100.00')",
                (datos.admin, datos.edificio, pago, datos.unidad_otro),
            )
        c.execute(
            "INSERT INTO parte_de_pago (administracion_id, complejo_id, pago_id, unidad_id, "
            "importe) VALUES (%s, %s, %s, %s, '100.00')",
            (datos.admin, datos.edificio, pago, datos.unidad),
        )
        with pytest.raises(psycopg.errors.UniqueViolation), c.transaction():
            c.execute(
                "INSERT INTO parte_de_pago (administracion_id, complejo_id, pago_id, unidad_id, "
                "importe) VALUES (%s, %s, %s, %s, '1.00')",
                (datos.admin, datos.edificio, pago, datos.unidad),
            )
        c.rollback()


def test_un_comprobante_es_de_un_solo_pago(base_del_edificio: BaseDeEdificio, datos: Datos) -> None:
    with _conexion(base_del_edificio, datos) as c:
        comprobante = _comprobante(c, datos)
        for numero in ("uno-1", "dos-1"):
            try:
                with c.transaction():
                    c.execute(
                        "INSERT INTO pago_informado (administracion_id, complejo_id, "
                        "comprobante_id, banco, banco_normalizado, numero_de_operacion, "
                        "numero_normalizado, fecha_de_transferencia, monto, informado_por) "
                        "VALUES (%s, %s, %s, 'b', 'b', %s, %s, '2026-11-05', '1.00', %s)",
                        (datos.admin, datos.edificio, comprobante, numero, numero, datos.persona),
                    )
            except psycopg.errors.UniqueViolation as error:
                assert numero == "dos-1"
                assert error.diag.constraint_name == "uq_pago_comprobante"
            else:
                assert numero == "uno-1"
        c.rollback()
