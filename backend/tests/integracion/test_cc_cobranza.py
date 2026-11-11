"""7.2 · `situacion_de_cuenta` y `situacion_del_edificio` contra PostgreSQL real (design D6, E14).

Apoyo del constructor para H-006 (la aceptación que decide es `aceptacion/H-006/`): acá se miden los
mutantes de la tarea 7.2, por su aserción.
"""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from proptech_core.compartido.dinero import Dinero
from proptech_core.cuenta_corriente.aplicacion import cobranza, correcciones, creditos, emisiones
from proptech_core.cuenta_corriente.aplicacion.correcciones import PedidoDeCorreccion
from proptech_core.cuenta_corriente.aplicacion.emisiones import EmisionRegistrada, ObligacionAEmitir
from proptech_core.cuenta_corriente.aplicacion.errores import Conflicto, NoEncontrado
from proptech_core.cuenta_corriente.aplicacion.saldo_inicial import (
    FilaDeDeuda,
    FilaDeTotal,
    OrigenDeCarga,
    UnidadDeSaldoInicial,
    registrar_saldo_inicial,
)
from proptech_core.cuenta_corriente.dominio.cobranza import SituacionDeCobranza

from ._cuenta_corriente import Mundo, sembrar, sesion_app
from ._edificios import BaseDeEdificio, fijar_tenant

pytestmark = pytest.mark.integracion

AGO, SEP, OCT = date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)
MIGRACION = date(2026, 10, 15)


def d(t: str) -> Dinero:
    return Dinero(t)


def dia(m: int, dd: int) -> date:
    return date(2026, m, dd)


@pytest.fixture
def mundo(base_del_edificio: BaseDeEdificio) -> Mundo:
    return sembrar(base_del_edificio, con_configuracion=True)


def configurar(
    base: BaseDeEdificio, mundo: Mundo, *, desde: date, umbral: str, gracia: int = 0
) -> None:
    """Una versión más de configuración, confirmada (la lee otra conexión)."""
    with base.conectar_app() as c:
        c.autocommit = False
        fijar_tenant(c, mundo.admin)
        c.execute(
            "INSERT INTO configuracion_versionada (administracion_id, complejo_id, autor_id, "
            "vigente_desde, tasa_mensual, umbral_saldo_chico, dias_de_gracia, forma_de_calculo, "
            "porcentaje_fondo, dia_de_vencimiento, modalidad_de_vencimiento) "
            "VALUES (%s, %s, %s, %s, '0.00', %s, %s, 'proporcional_por_dia', '0.00', 10, 'unico')",
            (mundo.admin, mundo.complejo, mundo.persona, desde, umbral, gracia),
        )
        c.commit()


def paso(s: Session) -> None:
    s.commit()
    s.begin()


def emitir(
    s: Session, mundo: Mundo, periodo: date, filas: list[tuple[int, date, str]]
) -> EmisionRegistrada:
    r = emisiones.registrar_emision(
        s,
        mundo.identidad,
        emision_id=uuid4(),
        complejo_id=mundo.complejo,
        periodo=periodo,
        obligaciones=[
            ObligacionAEmitir(mundo.unidades[n], v, d(i), d("0.00"), d("0.00")) for n, v, i in filas
        ],
        request_id=uuid4(),
    )
    paso(s)
    return r


def pagar(s: Session, mundo: Mundo, cuenta: UUID, importe: str, valor: date) -> UUID:
    m = creditos.registrar_credito(
        s,
        mundo.identidad,
        cuenta_id=cuenta,
        tipo="pago",
        importe=d(importe),
        fecha_valor=valor,
        operacion_id=uuid4(),
        destino=None,
        request_id=uuid4(),
    )
    paso(s)
    return m


def cuenta_de(s: Session, unidad: UUID) -> UUID:
    fila = s.execute(text("SELECT id FROM cuenta WHERE unidad_id = :u"), {"u": unidad}).first()
    assert fila is not None, "la unidad no tiene cuenta"
    return UUID(str(fila.id))


def tupla(x: SituacionDeCobranza) -> tuple[str, int, bool, bool, bool, str]:
    return (
        x.total_vencido.a_texto(),
        x.liquidaciones_vencidas,
        x.bajo_umbral,
        x.deuda_de_intereses,
        x.moroso_critico,
        x.etiqueta,
    )


MOROSO = ("165000.00", 2, False, False, True, "moroso_critico")


def dos_periodos(s: Session, mundo: Mundo) -> UUID:
    emitir(s, mundo, AGO, [(0, dia(8, 10), "80000.00")])
    r = emitir(s, mundo, SEP, [(0, dia(9, 10), "85000.00")])
    return r.cuentas[mundo.unidades[0]]


def test_emision_anulada_no_cuenta(mundo: Mundo, base_del_edificio: BaseDeEdificio) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, AGO, [(0, dia(8, 10), "80000.00")])
        r = emitir(s, mundo, SEP, [(0, dia(9, 10), "85000.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        assert tupla(cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 30))) == MOROSO
        emisiones.anular_emision(
            s, mundo.identidad, emision_id=r.emision_id, motivo="Mal cargada", request_id=uuid4()
        )
        paso(s)
        despues = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 30))
        assert tupla(despues) == ("80000.00", 1, False, False, False, "con_deuda_vencida")


def test_deshacer_un_pago_vuelve_a_marcar(mundo: Mundo, base_del_edificio: BaseDeEdificio) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo)
        pago = pagar(s, mundo, cuenta, "80000.00", dia(9, 20))
        limpia = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 30))
        assert tupla(limpia) == ("85000.00", 1, False, False, False, "con_deuda_vencida")
        correcciones.corregir(
            s,
            mundo.identidad,
            complejo_id=mundo.complejo,
            pedido=PedidoDeCorreccion(
                "contra_asiento", uuid4(), "Pago mal cargado", movimiento_id=pago
            ),
            request_id=uuid4(),
        )
        paso(s)
        vuelve = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 30))
        assert tupla(vuelve) == MOROSO


def _migrar(s: Session, mundo: Mundo, unidad: UnidadDeSaldoInicial) -> None:
    registrar_saldo_inicial(
        s,
        mundo.identidad,
        complejo_id=mundo.complejo,
        operacion_id=uuid4(),
        fecha_de_migracion=MIGRACION,
        origen=OrigenDeCarga(tipo="importador", archivo="saldos.xlsx"),
        unidades=[unidad],
        request_id=uuid4(),
        reloj=lambda: datetime(2026, 11, 11, 15, tzinfo=UTC),
    )
    paso(s)


def test_migrada_con_dos_periodos_es_moroso(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _migrar(
            s,
            mundo,
            UnidadDeSaldoInicial(
                mundo.unidades[1],
                "detalle",
                (
                    FilaDeDeuda(1, AGO, dia(8, 10), "ordinaria", d("80000.00"), d("0.00")),
                    FilaDeDeuda(2, SEP, dia(9, 10), "ordinaria", d("85000.00"), d("0.00")),
                ),
            ),
        )
        x = cobranza.situacion_de_cuenta(
            s, cuenta_id=cuenta_de(s, mundo.unidades[1]), fecha=dia(11, 11)
        )
        assert tupla(x) == MOROSO


def test_migrada_con_total_unico_cuenta_una_sola(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        _migrar(
            s,
            mundo,
            UnidadDeSaldoInicial(
                mundo.unidades[2], "total", (FilaDeTotal(1, d("50000.00"), d("0.00")),)
            ),
        )
        x = cobranza.situacion_de_cuenta(
            s, cuenta_id=cuenta_de(s, mundo.unidades[2]), fecha=dia(11, 11)
        )
        assert tupla(x) == ("50000.00", 1, False, False, False, "con_deuda_vencida")


def test_el_umbral_y_la_gracia_son_los_de_la_version_vigente_a_la_fecha(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    configurar(base_del_edificio, mundo, desde=dia(6, 1), umbral="300.00", gracia=5)
    with sesion_app(base_del_edificio, mundo.admin) as s:
        emitir(s, mundo, AGO, [(0, dia(8, 10), "200.00")])
        r = emitir(s, mundo, SEP, [(0, dia(9, 10), "200.00")])
        cuenta = r.cuentas[mundo.unidades[0]]
        x = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 30))
        assert tupla(x) == ("400.00", 2, False, False, True, "moroso_critico"), "umbral 300"
        dentro = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 15))
        assert tupla(dentro) == ("200.00", 1, True, False, False, "bajo_umbral"), "gracia 5"


def test_listado_del_edificio_trae_una_entrada_por_cuenta_de_unidad(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo)
        persona = uuid4()
        s.execute(
            text(
                "INSERT INTO cuenta (id, administracion_id, complejo_id, persona_id, creada_en) "
                "VALUES (:id, :adm, :c, :p, :en)"
            ),
            {
                "id": persona,
                "adm": mundo.admin,
                "c": mundo.complejo,
                "p": mundo.persona,
                "en": datetime(2026, 9, 1, 12, tzinfo=UTC),
            },
        )
        paso(s)
        listado = list(
            cobranza.situacion_del_edificio(s, complejo_id=mundo.complejo, fecha=dia(9, 30))
        )
        por_cuenta = {x.cuenta_id: x for x in listado}
        assert persona not in por_cuenta, "las cuentas de persona quedan fuera"
        assert set(por_cuenta) == {cuenta}, "una entrada por cuenta de unidad"
        assert por_cuenta[cuenta].unidad_id == mundo.unidades[0]
        assert tupla(por_cuenta[cuenta].situacion) == MOROSO


def test_un_pago_posterior_cuenta_aunque_la_fecha_sea_anterior(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo)
        pagar(s, mundo, cuenta, "165000.00", dia(10, 20))
        x = cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 30))
        assert tupla(x) == ("0.00", 0, False, False, False, "sin_deuda_vencida")


def test_edificio_y_cuenta_de_otra_administracion_dan_no_encontrado(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo)
        assert cobranza.situacion_del_edificio(s, complejo_id=mundo.complejo, fecha=dia(9, 30))
    with sesion_app(base_del_edificio, mundo.admin_b) as s_b:
        with pytest.raises(NoEncontrado):
            cobranza.situacion_del_edificio(s_b, complejo_id=mundo.complejo, fecha=dia(9, 30))
        with pytest.raises(NoEncontrado):
            cobranza.situacion_de_cuenta(s_b, cuenta_id=cuenta, fecha=dia(9, 30))


def test_sin_configuracion_vigente_a_la_fecha_es_conflicto(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo)
        for llamada in (
            lambda: cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(12, 31)),
            lambda: cobranza.situacion_del_edificio(
                s, complejo_id=mundo.complejo, fecha=dia(12, 31)
            ),
        ):
            assert llamada(), "control: con la versión vigente responde"
        fecha_sin_version = date(2025, 12, 31)
        with pytest.raises(Conflicto) as e1:
            cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=fecha_sin_version)
        assert e1.value.campo == "configuracion"
        with pytest.raises(Conflicto) as e2:
            cobranza.situacion_del_edificio(s, complejo_id=mundo.complejo, fecha=fecha_sin_version)
        assert e2.value.campo == "configuracion"


def test_es_una_lectura_sin_escrituras_ni_candados(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        cuenta = dos_periodos(s, mundo)
        vistas: list[str] = []

        @event.listens_for(s.get_bind(), "before_cursor_execute")
        def _ver(conn: object, cursor: object, sentencia: str, *args: object) -> None:
            vistas.append(sentencia.upper())

        cobranza.situacion_de_cuenta(s, cuenta_id=cuenta, fecha=dia(9, 30))
        cobranza.situacion_del_edificio(s, complejo_id=mundo.complejo, fecha=dia(9, 30))
        assert vistas, "control: se vieron sentencias"
        malas = [
            x
            for x in vistas
            if x.lstrip().startswith(("INSERT", "UPDATE", "DELETE"))
            or "FOR UPDATE" in x
            or "FOR NO KEY UPDATE" in x
            or "PG_ADVISORY" in x
        ]
        assert malas == [], malas[:1]


def test_la_sentencia_del_edificio_filtra_por_tenant_aunque_rls_no_filtre(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    """L-034: el filtro propio de la sentencia, separado de RLS. Con la conexión privilegiada (RLS
    no la filtra) y el tenant de B, la sentencia del edificio de A no trae ninguna fila."""
    with sesion_app(base_del_edificio, mundo.admin) as s:
        dos_periodos(s, mundo)
    c = base_del_edificio.contenedor
    sentencia = cobranza.SENTENCIA_DE_COBRANZA.replace(":complejo", "%(complejo)s")
    with psycopg.connect(
        host=c.get_container_host_ip(),
        port=c.get_exposed_port(5432),
        dbname=base_del_edificio.nombre,
        user=c.username,
        password=c.password,
    ) as conexion:
        assert conexion.execute(
            "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone() == (True,), "precondición: RLS no filtra a esta conexión"
        with conexion.transaction(force_rollback=True):
            fijar_tenant(conexion, mundo.admin)
            propias = conexion.execute(sentencia, {"complejo": mundo.complejo}).fetchall()
            assert propias, "control: con su propio tenant la sentencia trae filas"
            fijar_tenant(conexion, mundo.admin_b)
            ajenas = conexion.execute(sentencia, {"complejo": mundo.complejo}).fetchall()
            assert ajenas == [], "la sentencia trajo cuentas de otra administración"


def test_la_cuenta_de_una_persona_no_tiene_situacion(
    mundo: Mundo, base_del_edificio: BaseDeEdificio
) -> None:
    with sesion_app(base_del_edificio, mundo.admin) as s:
        dos_periodos(s, mundo)
        persona = uuid4()
        s.execute(
            text(
                "INSERT INTO cuenta (id, administracion_id, complejo_id, persona_id, creada_en) "
                "VALUES (:id, :adm, :c, :p, :en)"
            ),
            {
                "id": persona,
                "adm": mundo.admin,
                "c": mundo.complejo,
                "p": mundo.persona,
                "en": datetime(2026, 9, 1, 12, tzinfo=UTC),
            },
        )
        paso(s)
        with pytest.raises(NoEncontrado):
            cobranza.situacion_de_cuenta(s, cuenta_id=persona, fecha=dia(9, 30))
