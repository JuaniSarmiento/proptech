"""4.4: config/parametros.yaml del repositorio afirma cada default de D-042."""

from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
ARCHIVO = RAIZ / "config" / "parametros.yaml"


def test_archivo_del_repo_cumple_los_defaults_de_d042() -> None:
    from proptech_core.compartido.parametros import leer_parametros

    parametros = leer_parametros(str(ARCHIVO))

    assert parametros.intereses.tasa_mensual == Decimal("3.00")
    assert parametros.intereses.dias_de_gracia == 0
    assert parametros.intereses.forma_de_calculo == "proporcional_por_dia"
    assert parametros.fondo_de_reserva.porcentaje == Decimal("0.00")

    assert len(parametros.categorias_de_gasto) == 9
    claves_categoria = {c.clave for c in parametros.categorias_de_gasto}
    assert claves_categoria == {
        "encargado",
        "seguridad",
        "limpieza",
        "ascensor",
        "mantenimiento",
        "servicios",
        "seguros",
        "administracion",
        "varios",
    }

    assert len(parametros.grupos_de_reparto) == 4
    generales = next(g for g in parametros.grupos_de_reparto if g.clave == "generales")
    assert generales.metodo == "coeficiente"
    assert generales.alcance == "todas_las_unidades"
    claves_grupo = {g.clave for g in parametros.grupos_de_reparto}
    assert claves_grupo == {"generales", "ascensor", "cocheras", "servicios_centrales"}

    assert len(parametros.tipos_de_unidad) == 4
    claves_tipo = {t.clave for t in parametros.tipos_de_unidad}
    assert claves_tipo == {"departamento", "cochera", "baulera", "local"}

    assert parametros.estados_de_unidad.habilitados is False
    assert len(parametros.estados_de_unidad.estados) == 4
    for estado in parametros.estados_de_unidad.estados:
        assert estado.factor.a_texto() == "100.00"
        assert estado.cargo_fijo.a_texto() == "0.00"
    claves_estado = {e.clave for e in parametros.estados_de_unidad.estados}
    assert claves_estado == {"baldio", "en_obra", "habitado", "desocupado"}
