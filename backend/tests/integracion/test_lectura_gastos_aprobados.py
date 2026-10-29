"""Bloque 8 de `gastos-y-cargos`: la lectura agregada pensada para el 7 (D10)."""

from uuid import uuid4

import pytest

from ._api_edificios import ApiEdificio

pytestmark = pytest.mark.integracion

_CUIT_A = "20123456786"


def _categoria(api_edificio: ApiEdificio) -> str:
    return api_edificio.cliente.post(
        api_edificio.ruta("/categorias"), json={"nombre": f"Cat {uuid4().hex[:8]}"}
    ).json()["id"]


def _grupo(api_edificio: ApiEdificio) -> str:
    return api_edificio.cliente.post(
        api_edificio.ruta("/grupos"),
        json={"nombre": f"Grupo {uuid4().hex[:8]}", "metodo": "coeficiente", "unidades": []},
    ).json()["id"]


def _gasto(
    api_edificio: ApiEdificio, *, categoria: str, grupo: str, tipo: str, importe: str
) -> str:
    gasto_id = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": f"Gasto {tipo}",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": importe,
            "tipo": tipo,
        },
    ).json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    return gasto_id


def _factura(
    api_edificio: ApiEdificio, *, categoria: str, grupo: str, tipo: str, importe: str
) -> str:
    """Igual que `_gasto`, pero con los cuatro datos de factura — necesarios
    para asociar una nota de crédito (R22)."""
    gasto_id = api_edificio.cliente.post(
        api_edificio.ruta("/gastos"),
        json={
            "concepto": f"Factura {tipo}",
            "categoria_id": categoria,
            "grupo_id": grupo,
            "periodo": "2026-10-01",
            "importe": importe,
            "tipo": tipo,
            "cuit_emisor": _CUIT_A,
            "punto_de_venta": "0001",
            "tipo_de_comprobante": "FA",
            "numero_de_comprobante": uuid4().hex[:8],
        },
    ).json()["id"]
    api_edificio.cliente.post(f"/api/gastos/{gasto_id}/aprobar")
    return gasto_id


def _nota(gasto_id: str, importe: str) -> dict[str, object]:
    return {
        "gasto_id": gasto_id,
        "importe": importe,
        "periodo": "2026-10-01",
        "cuit_emisor": _CUIT_A,
        "punto_de_venta": "0001",
        "tipo_de_comprobante": "NC",
        "numero_de_comprobante": uuid4().hex[:8],
    }


# --- 8.1: contrato completo de la lectura agregada ---


def test_lectura_cubre_total_por_grupo_neto_bloques_y_desglose_por_categoria(
    api_edificio: ApiEdificio,
) -> None:
    api_edificio.como("super_admin")
    categoria_a = _categoria(api_edificio)
    categoria_b = _categoria(api_edificio)
    grupo = _grupo(api_edificio)

    api_edificio.como("editar")
    factura_ordinaria = _factura(
        api_edificio, categoria=categoria_a, grupo=grupo, tipo="ordinario", importe="1000.00"
    )
    _gasto(
        api_edificio, categoria=categoria_b, grupo=grupo, tipo="extraordinario", importe="2000.00"
    )
    respuesta_nota = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(factura_ordinaria, "300.00")
    )
    assert respuesta_nota.status_code == 201, respuesta_nota.text

    lectura = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()

    # Todos los importes llegan como texto (nunca float).
    assert isinstance(lectura["total"], str)
    assert isinstance(lectura["grupos"][grupo]["total"], str)
    assert isinstance(lectura["grupos"][grupo]["ordinario"]["subtotal"], str)

    # Neto de notas de crédito (1000.00 - 300.00 = 700.00), separado por bloque.
    assert lectura["grupos"][grupo]["ordinario"]["subtotal"] == "700.00"
    assert lectura["grupos"][grupo]["extraordinario"]["subtotal"] == "2000.00"

    # Desglose por categoría dentro de cada bloque.
    assert lectura["grupos"][grupo]["ordinario"]["categorias"][categoria_a] == "700.00"
    assert lectura["grupos"][grupo]["extraordinario"]["categorias"][categoria_b] == "2000.00"

    # Total por grupo y total general: suma de los dos bloques netos.
    assert lectura["grupos"][grupo]["total"] == "2700.00"
    assert lectura["total"] == "2700.00"


def test_periodo_sin_aprobados_devuelve_totales_en_cero_sin_error(
    api_edificio: ApiEdificio,
) -> None:
    api_edificio.como("super_admin")
    respuesta = api_edificio.cliente.get(api_edificio.ruta("/periodos/2026-11-01/gastos-aprobados"))
    assert respuesta.status_code == 200, respuesta.text
    lectura = respuesta.json()
    assert lectura["total"] == "0.00"
    assert lectura["grupos"] == {}


# --- 8.2: mutante obligatorio ---


def test_mutante_que_suma_las_notas_de_credito_rompe_en_el_neto(
    api_edificio: ApiEdificio, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Copia de `gastos_aprobados_del_periodo` que SUMA la nota de crédito en
    vez de restarla — nunca se toca el archivo real (L-013)."""
    from sqlalchemy import text

    from proptech_core.compartido.dinero import Dinero, sumar
    from proptech_core.gastos.aplicacion import gastos as modulo_gastos

    api_edificio.como("super_admin")
    categoria = _categoria(api_edificio)
    grupo = _grupo(api_edificio)
    api_edificio.como("editar")
    factura = _factura(
        api_edificio, categoria=categoria, grupo=grupo, tipo="ordinario", importe="1000.00"
    )
    respuesta_nota = api_edificio.cliente.post(
        "/api/notas-de-credito", json=_nota(factura, "300.00")
    )
    assert respuesta_nota.status_code == 201, respuesta_nota.text

    def _mutada(sesion, complejo_id, periodo):  # type: ignore[no-untyped-def]
        filas = (
            sesion.execute(
                text(
                    "SELECT grupo_id, categoria_id, tipo, importe::text AS importe FROM gasto "
                    "WHERE complejo_id=:complejo AND periodo_de_imputacion=:periodo "
                    "AND estado='aprobado'"
                ),
                {"complejo": complejo_id, "periodo": periodo},
            )
            .mappings()
            .all()
        )
        grupos: dict = {}
        for fila in filas:
            g = grupos.setdefault(str(fila["grupo_id"]), {"ordinario": {}, "extraordinario": {}})
            b = g[fila["tipo"]]
            c = str(fila["categoria_id"])
            b[c] = b.get(c, Dinero("0.00")) + Dinero(fila["importe"])
        notas = (
            sesion.execute(
                text(
                    "SELECT g.grupo_id, g.categoria_id, g.tipo, n.importe::text AS importe "
                    "FROM nota_de_credito n JOIN gasto g ON g.id = n.gasto_id "
                    "WHERE n.complejo_id=:complejo AND n.periodo=:periodo AND g.estado='aprobado'"
                ),
                {"complejo": complejo_id, "periodo": periodo},
            )
            .mappings()
            .all()
        )
        for fila in notas:
            g = grupos.setdefault(str(fila["grupo_id"]), {"ordinario": {}, "extraordinario": {}})
            b = g[fila["tipo"]]
            c = str(fila["categoria_id"])
            #: MUTANTE: suma en vez de restar.
            b[c] = b.get(c, Dinero("0.00")) + Dinero(fila["importe"])
        resultado_grupos: dict = {}
        total_general = Dinero("0.00")
        for grupo_id, bloques in grupos.items():
            subtotales = {
                tipo: sumar(categorias.values()) if categorias else Dinero("0.00")
                for tipo, categorias in bloques.items()
            }
            total_grupo = sumar(subtotales.values())
            total_general = total_general + total_grupo
            resultado_grupos[grupo_id] = {
                "total": total_grupo.a_texto(),
                "ordinario": {
                    "subtotal": subtotales["ordinario"].a_texto(),
                    "categorias": {c: m.a_texto() for c, m in bloques["ordinario"].items()},
                },
                "extraordinario": {
                    "subtotal": subtotales["extraordinario"].a_texto(),
                    "categorias": {c: m.a_texto() for c, m in bloques["extraordinario"].items()},
                },
            }
        return {
            "periodo": periodo.isoformat(),
            "total": total_general.a_texto(),
            "grupos": resultado_grupos,
        }

    monkeypatch.setattr(modulo_gastos, "gastos_aprobados_del_periodo", _mutada)
    api_edificio.como("super_admin")
    lectura_mutada = api_edificio.cliente.get(
        api_edificio.ruta("/periodos/2026-10-01/gastos-aprobados")
    ).json()
    # Sin mutar sería "700.00" (1000.00 - 300.00); con el mutante activo
    # suma en vez de restar: "1300.00".
    assert lectura_mutada["grupos"][grupo]["total"] == "1300.00"
    assert lectura_mutada["grupos"][grupo]["total"] != "700.00"
