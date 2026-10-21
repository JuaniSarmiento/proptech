"""D7 (2b, tarea 5.4): el worker habla con Clerk, contra un servidor falso
que valida el contrato real (L-027).

Escenarios de `gestion-de-usuarios`: Envío exitoso; Reintento tras una
caída; Trabajo repetido; Rechazo definitivo; Revocar una invitación
enviada; Entrega sin token crudo. Lecciones: L-001, L-007, L-009, L-013,
L-027.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

import arq
import arq.worker
import psycopg
import pytest
from pydantic import SecretStr
from testcontainers.community.postgres import PostgresContainer

from proptech_core.acceso.adaptadores.clerk_http import AdaptadorClerkHttp
from proptech_core.compartido.base_de_datos import (
    crear_engine,
    crear_fabrica_de_sesiones,
    registrar_tenant_por_administracion,
)
from proptech_core.compartido.reintentos import PoliticaReintentos

from .._clerk_falso import CLAVE_DE_PRUEBA, ServidorClerkFalso
from .test_worker_caminos_de_falla import _capturar_logs, _lineas_json

pytestmark = pytest.mark.integracion

_POLITICA_RAPIDA = PoliticaReintentos(espera_base=0.05, intentos_maximos=5)
SOBRE = "sobre-cifrado-de-prueba-nunca-el-token-crudo"
EMAIL = "vecina@example.invalid"


def _conectar(contenedor: PostgresContainer, usuario: str, password: str) -> psycopg.Connection:
    from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION

    return psycopg.connect(
        host=contenedor.get_container_host_ip(),
        port=contenedor.get_exposed_port(5432),
        user=usuario or MIGRADOR_USER_DE_SESION,
        password=password or MIGRADOR_PASSWORD_DE_SESION,
        dbname=contenedor.dbname,
        autocommit=True,
    )


def _crear_invitacion_pendiente(
    contenedor: PostgresContainer, *, email: str = EMAIL
) -> dict[str, Any]:
    from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION

    admin_id, persona_id, invitacion_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    resumen = hashlib.sha256(str(invitacion_id).encode()).digest()
    conexion = _conectar(contenedor, MIGRADOR_USER_DE_SESION, MIGRADOR_PASSWORD_DE_SESION)
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
            cur.execute(
                "INSERT INTO administracion (id, nombre) VALUES (%s, 'Admin de prueba')",
                (str(admin_id),),
            )
            cur.execute(
                "INSERT INTO persona (id, administracion_id, nombre, email) "
                "VALUES (%s,%s,'Vecina',%s)",
                (str(persona_id), str(admin_id), email),
            )
            cur.execute(
                "INSERT INTO invitacion (id, administracion_id, persona_id, estado, "
                "token_resumen, vence, creada_por) VALUES "
                "(%s,%s,%s,'pendiente',%s, now() + interval '7 days', %s)",
                (str(invitacion_id), str(admin_id), str(persona_id), resumen, str(persona_id)),
            )
    finally:
        conexion.close()
    return {"administracion_id": admin_id, "persona_id": persona_id, "invitacion_id": invitacion_id}


def _leer_fila(contenedor: PostgresContainer, admin_id: uuid.UUID, invitacion_id: uuid.UUID) -> Any:
    from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION

    conexion = _conectar(contenedor, MIGRADOR_USER_DE_SESION, MIGRADOR_PASSWORD_DE_SESION)
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
            cur.execute(
                "SELECT estado, clerk_invitacion_id FROM invitacion WHERE id=%s",
                (str(invitacion_id),),
            )
            return cur.fetchone()
    finally:
        conexion.close()


def _fijar_estado(
    contenedor: PostgresContainer,
    admin_id: uuid.UUID,
    invitacion_id: uuid.UUID,
    *,
    estado: str,
    clerk_invitacion_id: str | None,
) -> None:
    from ..conftest import MIGRADOR_PASSWORD_DE_SESION, MIGRADOR_USER_DE_SESION

    conexion = _conectar(contenedor, MIGRADOR_USER_DE_SESION, MIGRADOR_PASSWORD_DE_SESION)
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT set_config('app.administracion_id', %s, false)", (str(admin_id),))
            cur.execute(
                "UPDATE invitacion SET estado=%s, clerk_invitacion_id=%s WHERE id=%s",
                (estado, clerk_invitacion_id, str(invitacion_id)),
            )
    finally:
        conexion.close()


def _fabrica_con_tenant(ajustes_del_worker: Any) -> Any:
    engine = crear_engine(ajustes_del_worker._configuracion)
    fabrica = crear_fabrica_de_sesiones(engine)
    registrar_tenant_por_administracion(fabrica)
    return fabrica


def _ctx(ajustes_del_worker: Any, fabrica: Any, clerk: AdaptadorClerkHttp) -> dict[str, Any]:
    return {
        "fabrica_de_sesiones": fabrica,
        "clerk": clerk,
        "configuracion_app": ajustes_del_worker._configuracion,
        "parametros": ajustes_del_worker._PARAMETROS,
        "politica": _POLITICA_RAPIDA,
        "job_try": 1,
    }


async def _correr_worker_burst_con_clerk(
    ajustes_del_worker: Any,
    nombre_cola: str,
    clerk: AdaptadorClerkHttp,
    *,
    max_burst_jobs: int = 10,
) -> None:
    kwargs: dict[str, Any] = dict(arq.worker.get_kwargs(ajustes_del_worker.AjustesDelWorker))

    async def _on_startup_de_test(ctx: dict[str, Any]) -> None:
        await ajustes_del_worker.on_startup(ctx)
        ctx["politica"] = _POLITICA_RAPIDA
        ctx["clerk"] = clerk

    kwargs["on_startup"] = _on_startup_de_test
    kwargs["queue_name"] = nombre_cola
    worker = arq.Worker(
        **kwargs, burst=True, handle_signals=False, poll_delay=0.01, max_burst_jobs=max_burst_jobs
    )
    try:
        await worker.async_run()
    finally:
        await worker.close()


@pytest.mark.anyio
async def test_envio_exitoso_guarda_el_id_y_marca_enviada(
    ajustes_del_worker: Any, esquema_migrado: None, postgres_contenedor: PostgresContainer
) -> None:
    fila = _crear_invitacion_pendiente(postgres_contenedor)
    with ServidorClerkFalso(lambda *_: (201, {"id": "inv_enviada01"})) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        from proptech_worker.tareas import enviar_invitacion

        ctx = _ctx(ajustes_del_worker, _fabrica_con_tenant(ajustes_del_worker), clerk)
        resultado = await enviar_invitacion(
            ctx,
            request_id=str(uuid.uuid4()),
            clave=f"invitacion:{fila['invitacion_id']}",
            administracion_id=str(fila["administracion_id"]),
            invitacion_id=str(fila["invitacion_id"]),
            sobre=SOBRE,
        )
    assert resultado is True
    estado, clerk_id = _leer_fila(
        postgres_contenedor, fila["administracion_id"], fila["invitacion_id"]
    )
    assert (estado, clerk_id) == ("enviada", "inv_enviada01")
    pedido = servidor.pedidos[0]
    assert pedido["cuerpo"]["redirect_url"].endswith(f"/invitacion/{SOBRE}")
    assert (
        "email" not in json.dumps(pedido["cuerpo"]).lower()
        or pedido["cuerpo"]["email_address"] == EMAIL
    )


@pytest.mark.anyio
async def test_rechazo_definitivo_422_marca_fallida_sin_reintento(
    ajustes_del_worker: Any, esquema_migrado: None, postgres_contenedor: PostgresContainer
) -> None:
    from proptech_worker.tareas import enviar_invitacion

    fila = _crear_invitacion_pendiente(postgres_contenedor)
    with ServidorClerkFalso(
        lambda *_: (422, {"errors": [{"message": "email_address inválido"}]})
    ) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        ctx = _ctx(ajustes_del_worker, _fabrica_con_tenant(ajustes_del_worker), clerk)
        resultado = await enviar_invitacion(
            ctx,
            request_id=str(uuid.uuid4()),
            clave=f"invitacion:{fila['invitacion_id']}",
            administracion_id=str(fila["administracion_id"]),
            invitacion_id=str(fila["invitacion_id"]),
            sobre=SOBRE,
        )
        cantidad_de_pedidos = len(servidor.pedidos)
    assert resultado is False
    assert cantidad_de_pedidos == 1
    estado, clerk_id = _leer_fila(
        postgres_contenedor, fila["administracion_id"], fila["invitacion_id"]
    )
    assert (estado, clerk_id) == ("fallida", None)


@pytest.mark.anyio
async def test_trabajo_repetido_sobre_enviada_no_llama_al_servidor(
    ajustes_del_worker: Any, esquema_migrado: None, postgres_contenedor: PostgresContainer
) -> None:
    from proptech_worker.tareas import enviar_invitacion

    fila = _crear_invitacion_pendiente(postgres_contenedor)
    _fijar_estado(
        postgres_contenedor,
        fila["administracion_id"],
        fila["invitacion_id"],
        estado="enviada",
        clerk_invitacion_id="inv_yaenviada",
    )
    with ServidorClerkFalso(lambda *_: (201, {"id": "inv_otro"})) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        ctx = _ctx(ajustes_del_worker, _fabrica_con_tenant(ajustes_del_worker), clerk)
        resultado = await enviar_invitacion(
            ctx,
            request_id=str(uuid.uuid4()),
            clave=f"invitacion:{fila['invitacion_id']}",
            administracion_id=str(fila["administracion_id"]),
            invitacion_id=str(fila["invitacion_id"]),
            sobre=SOBRE,
        )
        assert servidor.pedidos == []
    assert resultado is True
    estado, clerk_id = _leer_fila(
        postgres_contenedor, fila["administracion_id"], fila["invitacion_id"]
    )
    assert (estado, clerk_id) == ("enviada", "inv_yaenviada")


@pytest.mark.anyio
async def test_tenant_ajeno_no_llama_al_servidor(
    ajustes_del_worker: Any, esquema_migrado: None, postgres_contenedor: PostgresContainer
) -> None:
    from proptech_worker.tareas import enviar_invitacion

    fila = _crear_invitacion_pendiente(postgres_contenedor)
    with ServidorClerkFalso(lambda *_: (201, {"id": "inv_x"})) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        ctx = _ctx(ajustes_del_worker, _fabrica_con_tenant(ajustes_del_worker), clerk)
        resultado = await enviar_invitacion(
            ctx,
            request_id=str(uuid.uuid4()),
            clave="invitacion:ajena",
            administracion_id=str(uuid.uuid4()),  # otra administración
            invitacion_id=str(fila["invitacion_id"]),
            sobre=SOBRE,
        )
        assert servidor.pedidos == []
    assert resultado is True
    estado, _ = _leer_fila(postgres_contenedor, fila["administracion_id"], fila["invitacion_id"])
    assert estado == "pendiente"


@pytest.mark.anyio
async def test_revocar_llama_al_endpoint_de_revoke(
    ajustes_del_worker: Any, esquema_migrado: None, postgres_contenedor: PostgresContainer
) -> None:
    from proptech_worker.tareas import revocar_invitacion_en_clerk

    fila = _crear_invitacion_pendiente(postgres_contenedor)
    _fijar_estado(
        postgres_contenedor,
        fila["administracion_id"],
        fila["invitacion_id"],
        estado="revocada",
        clerk_invitacion_id="inv_arevocar",
    )
    with ServidorClerkFalso(lambda *_: (200, {})) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        ctx = _ctx(ajustes_del_worker, _fabrica_con_tenant(ajustes_del_worker), clerk)
        resultado = await revocar_invitacion_en_clerk(
            ctx,
            request_id=str(uuid.uuid4()),
            clave=f"revocar:{fila['invitacion_id']}",
            administracion_id=str(fila["administracion_id"]),
            invitacion_id=str(fila["invitacion_id"]),
        )
    assert resultado is True
    assert (servidor.pedidos[0]["metodo"], servidor.pedidos[0]["ruta"]) == (
        "POST",
        "/invitations/inv_arevocar/revoke",
    )


@pytest.mark.anyio
async def test_revocar_sin_clerk_id_no_llama_a_nadie(
    ajustes_del_worker: Any, esquema_migrado: None, postgres_contenedor: PostgresContainer
) -> None:
    from proptech_worker.tareas import revocar_invitacion_en_clerk

    fila = _crear_invitacion_pendiente(postgres_contenedor)
    _fijar_estado(
        postgres_contenedor,
        fila["administracion_id"],
        fila["invitacion_id"],
        estado="revocada",
        clerk_invitacion_id=None,
    )
    with ServidorClerkFalso(lambda *_: (200, {})) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        ctx = _ctx(ajustes_del_worker, _fabrica_con_tenant(ajustes_del_worker), clerk)
        resultado = await revocar_invitacion_en_clerk(
            ctx,
            request_id=str(uuid.uuid4()),
            clave=f"revocar:{fila['invitacion_id']}",
            administracion_id=str(fila["administracion_id"]),
            invitacion_id=str(fila["invitacion_id"]),
        )
        assert servidor.pedidos == []
    assert resultado is True


@pytest.mark.anyio
async def test_reintento_tras_caidas_y_exito_final_deja_un_solo_id(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    postgres_contenedor: PostgresContainer,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    nombre_cola, cola = cola_de_prueba_aislada
    fila = _crear_invitacion_pendiente(postgres_contenedor)
    intentos: list[int] = []

    def _manejador(*_: Any) -> tuple[int, dict[str, Any]]:
        intentos.append(1)
        if len(intentos) < 3:
            return 503, {"errors": []}
        return 201, {"id": "inv_trasreintentos"}

    salida = _capturar_logs()
    with ServidorClerkFalso(_manejador) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        await cola.encolar(
            "enviar_invitacion",
            clave=f"invitacion:{fila['invitacion_id']}",
            request_id=str(uuid.uuid4()),
            administracion_id=str(fila["administracion_id"]),
            invitacion_id=str(fila["invitacion_id"]),
            sobre=SOBRE,
        )
        await _correr_worker_burst_con_clerk(ajustes_del_worker, nombre_cola, clerk)
        cantidad_de_pedidos = len(servidor.pedidos)

    assert cantidad_de_pedidos == 3
    estado, clerk_id = _leer_fila(
        postgres_contenedor, fila["administracion_id"], fila["invitacion_id"]
    )
    assert (estado, clerk_id) == ("enviada", "inv_trasreintentos")

    lineas = _lineas_json(salida)
    texto = json.dumps(lineas)
    assert EMAIL not in texto and SOBRE not in texto
    reintentos = [linea for linea in lineas if linea.get("evento") == "reintento_programado"]
    assert len(reintentos) == 2, lineas


@pytest.mark.anyio
async def test_ttl_en_redis_es_3600_y_se_borra_tras_el_exito(
    ajustes_del_worker: Any,
    esquema_migrado: None,
    postgres_contenedor: PostgresContainer,
    cola_de_prueba_aislada: tuple[str, Any],
) -> None:
    """D7, RB2b-7: `_expires=3600` desde el encolado original (el mismo que
    pasa `entrega.encolar_envio`, 5.1/5.2); `keep_result=0` (`arq.func` en
    `AjustesDelWorker.functions`) no deja resultado en Redis tras el
    éxito."""
    import redis.asyncio as redis_asincronico

    nombre_cola, cola = cola_de_prueba_aislada
    fila = _crear_invitacion_pendiente(postgres_contenedor)
    clave = f"invitacion:{fila['invitacion_id']}"
    with ServidorClerkFalso(lambda *_: (201, {"id": "inv_ttlborrado"})) as servidor:
        clerk = AdaptadorClerkHttp(SecretStr(CLAVE_DE_PRUEBA), base_url=servidor.base_url)
        await cola.encolar(
            "enviar_invitacion",
            clave=clave,
            request_id=str(uuid.uuid4()),
            expira_en_s=3600,
            administracion_id=str(fila["administracion_id"]),
            invitacion_id=str(fila["invitacion_id"]),
            sobre=SOBRE,
        )
        redis_settings = ajustes_del_worker.AjustesDelWorker.redis_settings
        cliente = redis_asincronico.Redis(
            host=redis_settings.host,
            port=redis_settings.port,
            password=redis_settings.password,
        )
        try:
            ttl_antes = await cliente.ttl(f"arq:job:{clave}")
            assert 3000 < ttl_antes <= 3600, ttl_antes
            await _correr_worker_burst_con_clerk(ajustes_del_worker, nombre_cola, clerk)
            assert await cliente.get(f"arq:job:{clave}") is None
            assert await cliente.get(f"arq:result:{clave}") is None
        finally:
            await cliente.aclose()
    estado, clerk_id = _leer_fila(
        postgres_contenedor, fila["administracion_id"], fila["invitacion_id"]
    )
    assert (estado, clerk_id) == ("enviada", "inv_ttlborrado")
