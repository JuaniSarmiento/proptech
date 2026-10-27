"""D7 (tarea 4.1): clave derivada del nombre, función pura, sin base."""

from proptech_core.compartido.claves import derivar_clave


def test_clave_derivada_del_nombre() -> None:
    """Escenario "Clave derivada del nombre"."""
    assert derivar_clave("Pileta y SUM", existentes=()) == "pileta_y_sum"


def test_nombre_con_tildes_y_signos() -> None:
    """Escenario "Nombre con tildes y signos": ASCII, empieza con letra, sin
    guiones bajos repetidos ni al final, hasta 40 caracteres."""
    clave = derivar_clave("Ascensor — línea B (2° torre)", existentes=())
    assert clave is not None
    assert clave.isascii()
    assert clave[0].isalpha()
    assert "__" not in clave
    assert not clave.endswith("_")
    assert len(clave) <= 40


def test_clave_derivada_repetida_se_desempata() -> None:
    """Escenario "Clave derivada repetida"."""
    assert derivar_clave("Varios extra", existentes=("varios",)) == "varios_extra"
    assert derivar_clave("Pileta", existentes=("pileta",)) == "pileta_2"
    assert derivar_clave("Pileta", existentes=("pileta", "pileta_2")) == "pileta_3"


def test_nombre_del_que_no_sale_ninguna_clave() -> None:
    """Escenario "Nombre del que no sale ninguna clave"."""
    assert derivar_clave("123", existentes=()) is None
    assert derivar_clave("— —", existentes=()) is None


def test_recorte_a_40_sin_guion_bajo_al_final() -> None:
    clave = derivar_clave("a" * 50, existentes=())
    assert clave == "a" * 40


def test_prefijo_por_letra_cuando_empieza_con_digito() -> None:
    clave = derivar_clave("2do piso", existentes=())
    assert clave is not None
    assert clave[0].isalpha()
    assert clave.endswith("2do_piso")


def test_desempate_recorta_para_que_el_sufijo_entre() -> None:
    nombre_largo = "a" * 40
    clave = derivar_clave(nombre_largo, existentes=(nombre_largo,))
    assert clave == "a" * 38 + "_2"
    assert len(clave) <= 40
