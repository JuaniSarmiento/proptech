"""D13 (deuda del 1b con dueño 3, tarea 2.3): `naming_convention` en la
`MetaData` de `Base`, para que los nombres de constraints de las migraciones
nuevas (desde 3.1) sean deterministas. Las migraciones del 2a (0001-0004) ya
nombran cada constraint a mano (`fk_...`, `uq_...`, `ck_...`); esto cubre lo
que se declare desde modelos de SQLAlchemy Core/ORM sin nombre explícito."""

from __future__ import annotations


def test_metadata_de_base_tiene_naming_convention_determinista() -> None:
    from proptech_core.compartido.base_de_datos import Base

    convencion = Base.metadata.naming_convention
    for clave in ("ix", "uq", "ck", "fk", "pk"):
        assert clave in convencion, f"falta la clave {clave!r} en naming_convention: {convencion}"


def test_naming_convention_sigue_el_estilo_ya_usado_a_mano() -> None:
    """Las migraciones del 2a nombran a mano `fk_<tabla>_<algo>`,
    `uq_<tabla>_<columnas>`, `ck_<tabla>_<algo>` y `pk_<tabla>` (ver
    `migraciones/versions/0003_acceso_minimo.py`): la convención nueva usa el
    mismo prefijo para no introducir un segundo estilo de nombres."""
    from proptech_core.compartido.base_de_datos import Base

    convencion = Base.metadata.naming_convention
    uq, ck, fk, pk = convencion["uq"], convencion["ck"], convencion["fk"], convencion["pk"]
    for nombre, prefijo in ((uq, "uq_"), (ck, "ck_"), (fk, "fk_"), (pk, "pk_")):
        assert isinstance(nombre, str), f"no es un patrón de texto: {nombre!r}"
        assert nombre.startswith(prefijo)
