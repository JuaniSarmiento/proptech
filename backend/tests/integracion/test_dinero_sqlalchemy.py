"""3.5: TipoDinero contra PostgreSQL real, con una tabla temporal (D5)."""

from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import Column, Engine, MetaData, Table, Text, create_engine, insert, select
from sqlalchemy.exc import StatementError
from sqlalchemy.types import TypeEngine
from testcontainers.community.postgres import PostgresContainer

pytestmark = pytest.mark.integracion


def _engine(contenedor: PostgresContainer) -> Engine:
    url = contenedor.get_connection_url()
    return create_engine(url)


def _tabla_temporal(metadata: MetaData, tipo: TypeEngine[Any]) -> Table:
    return Table(
        "_test_dinero",
        metadata,
        Column("id", Text, primary_key=True),
        Column("monto", tipo),
        prefixes=["TEMPORARY"],
    )


def test_monto_extremo_vuelve_exacto_y_como_dinero(postgres_contenedor: PostgresContainer) -> None:
    from proptech_core.compartido.dinero import Dinero
    from proptech_core.compartido.dinero_sqlalchemy import TipoDinero

    engine = _engine(postgres_contenedor)
    metadata = MetaData()
    tabla = _tabla_temporal(metadata, TipoDinero())
    with engine.begin() as conexion:
        metadata.create_all(conexion)
        conexion.execute(insert(tabla).values(id="a", monto=Dinero("999999999999.99")))
        resultado = conexion.execute(select(tabla.c.monto).where(tabla.c.id == "a")).scalar_one()
        assert isinstance(resultado, Dinero)
        assert resultado.a_texto() == "999999999999.99"
    engine.dispose()


@pytest.mark.parametrize("valor_invalido", [20000.5, Decimal("20000.50"), "20000.50"])
def test_bind_rechaza_tipos_no_dinero_antes_de_la_base(
    postgres_contenedor: PostgresContainer, valor_invalido: object
) -> None:
    from proptech_core.compartido.dinero import MontoInvalido
    from proptech_core.compartido.dinero_sqlalchemy import TipoDinero

    engine = _engine(postgres_contenedor)
    metadata = MetaData()
    tabla = _tabla_temporal(metadata, TipoDinero())
    with engine.begin() as conexion:
        metadata.create_all(conexion)
        with pytest.raises(StatementError) as exc_info:
            conexion.execute(insert(tabla).values(id="b", monto=valor_invalido))
        assert isinstance(exc_info.value.orig, MontoInvalido)
    engine.dispose()
