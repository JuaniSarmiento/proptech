"""Todo contenedor de Postgres de los tests espera a aceptar conexiones (2e, xdist)."""

from testcontainers.community.postgres import PostgresContainer


def test_start_de_postgres_espera_conexiones_en_todo_modulo() -> None:
    # Los módulos de integración levantan `PostgresContainer(...)` por su cuenta; sin esta espera,
    # bajo `-n 4` el primer `roles antes` recibía `Connection refused` de forma intermitente.
    assert getattr(PostgresContainer.start, "espera_conexiones", False) is True
