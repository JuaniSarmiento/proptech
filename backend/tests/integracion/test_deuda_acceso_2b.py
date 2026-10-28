"""4.3: ataques a cada comparación del catálogo y medición con identidad real."""

from collections.abc import Iterator
from statistics import median
from time import perf_counter
from uuid import uuid4

import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from proptech_core.compartido.roles import _verificar_politica_de_auditoria

from ._api_edificios import ApiEdificio
from ._clerk import api_clerk as api_clerk
from ._clerk import clerk_falso as clerk_falso
from ._clerk import encabezados
from ._edificios import BaseDeEdificio

pytestmark = pytest.mark.integracion


@pytest.fixture
def catalogo(base_del_edificio: BaseDeEdificio) -> Iterator[psycopg.Cursor]:
    c = base_del_edificio.contenedor
    with psycopg.connect(
        host=c.get_container_host_ip(),
        port=c.get_exposed_port(5432),
        dbname=base_del_edificio.nombre,
        user=c.username,
        password=c.password,
    ) as conexion:
        with conexion.cursor() as cur:
            yield cur
        conexion.rollback()


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        ("ALTER POLICY auditoria_por_administracion ON auditoria RENAME TO otra", "se llama"),
        (
            "UPDATE pg_policy SET polpermissive = false WHERE polrelid = 'auditoria'::regclass",
            "PERMISSIVE",
        ),
        ("UPDATE pg_policy SET polcmd = 'r' WHERE polrelid = 'auditoria'::regclass", "comando"),
        ("ALTER POLICY auditoria_por_administracion ON auditoria TO proptech_app", "PUBLIC"),
        ("ALTER POLICY auditoria_por_administracion ON auditoria WITH CHECK (true)", "WITH CHECK"),
    ],
)
def test_cada_comparacion_de_la_politica(
    catalogo: psycopg.Cursor, cambio: str, mensaje: str
) -> None:
    assert _verificar_politica_de_auditoria(catalogo) == []
    catalogo.execute(cambio)
    errores = _verificar_politica_de_auditoria(catalogo)
    assert len(errores) == 1 and mensaje in errores[0], errores


@pytest.mark.parametrize("sentencia", ["truncate auditoria", "TrUnCaTe auditoria"])
def test_truncate_se_prueba_por_el_efecto(catalogo: psycopg.Cursor, sentencia: str) -> None:
    with pytest.raises(psycopg.errors.RaiseException, match="auditoria no admite"):
        catalogo.execute(sentencia)


def test_migraciones_no_agregan_fk_hacia_auditoria(catalogo: psycopg.Cursor) -> None:
    catalogo.execute(
        "SELECT conname FROM pg_constraint WHERE contype = 'f' "
        "AND confrelid = 'auditoria'::regclass"
    )
    assert catalogo.fetchall() == []


def test_tiempos_403_y_404_con_identidad_real(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey
) -> None:
    # La identidad conserva el vínculo real de Clerk; pasa a vecino del edificio.
    api_clerk.filas(
        "DELETE FROM asignacion_rol WHERE persona_id = %s RETURNING id",
        (api_clerk.personas["editar"],),
    )
    api_clerk.filas(
        "INSERT INTO asignacion_rol (administracion_id, persona_id, rol, "
        "complejo_id, unidad_id, vinculo) VALUES (%s,%s,'vecino',%s,%s,"
        "'propietario') RETURNING id",
        (api_clerk.admin, api_clerk.personas["editar"], api_clerk.edificio, api_clerk.unidad),
    )
    headers = encabezados(clerk_falso)
    rutas = [
        api_clerk.ruta("/resumen"),
        f"/api/complejos/{uuid4()}/resumen",
        f"/api/complejos/{uuid4()}/resumen",
    ]
    muestras: list[list[float]] = [[], [], []]
    for ronda in range(210):
        for i in [(ronda + j) % 3 for j in range(3)]:
            inicio = perf_counter()
            respuesta = api_clerk.cliente.get(rutas[i], headers=headers)
            duracion = (perf_counter() - inicio) * 1000
            assert respuesta.status_code == (403 if i == 0 else 404)
            if ronda >= 10:
                muestras[i].append(duracion)
    m = [median(v) for v in muestras]
    control = abs(m[1] - m[2])
    dispersion = max(median([abs(t - median(v)) for t in v]) for v in muestras)
    diferencia = abs(m[0] - m[1])
    umbral = max(5.0, control + 3 * dispersion)
    print(
        f"R9 n=200: medianas_ms={m}, diferencia={diferencia:.3f}, "
        f"control={control:.3f}, MAD={dispersion:.3f}, umbral={umbral:.3f}"
    )
    assert diferencia <= umbral, "diferencia explotable según el criterio declarado en tasks.md"


@pytest.mark.parametrize("ruta", ["/api/sesion", "/api/complejos"])
def test_el_403_no_depende_del_email_ni_lee_por_email(
    api_clerk: ApiEdificio, clerk_falso: rsa.RSAPrivateKey, ruta: str
) -> None:
    from typing import Any

    from sqlalchemy import event

    persona = api_clerk.personas["ver"]
    api_clerk.filas(
        "UPDATE persona SET email='x@ejemplo.invalid' WHERE id=%s RETURNING id", (persona,)
    )
    api_clerk.filas(
        "INSERT INTO "
        "invitacion(administracion_id,persona_id,estado,token_resumen,vence,creada_por) "
        "VALUES (%s,%s,'enviada',%s,now()+interval '1 day',%s) RETURNING id",
        (api_clerk.admin, persona, uuid4().bytes, api_clerk.personas["super_admin"]),
    )
    sql: list[str] = []

    def contar(*args: Any) -> None:
        sql.append(args[2])

    event.listen(api_clerk.app.state.engine, "before_cursor_execute", contar)
    try:
        respuestas = [
            api_clerk.cliente.get(
                ruta, headers=encabezados(clerk_falso, sub="user_NoVinculado", email=email)
            )
            for email in ("x@ejemplo.invalid", "otra@ejemplo.invalid")
        ]
    finally:
        event.remove(api_clerk.app.state.engine, "before_cursor_execute", contar)
    a, b = respuestas
    assert a.status_code == b.status_code == 403
    assert a.json() == {"detail": {"codigo": "sin_acceso"}}
    assert a.content == b.content
    assert dict(a.headers) | {"x-request-id": ""} == dict(b.headers) | {"x-request-id": ""}
    assert str(api_clerk.admin) not in a.text and "Inventada API" not in a.text
    assert not any("email" in s.lower() for s in sql)
