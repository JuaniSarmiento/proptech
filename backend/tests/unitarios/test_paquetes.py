"""Verifica que los tres paquetes del backend sean importables."""


def test_importa_proptech_core() -> None:
    import proptech_core  # noqa: F401


def test_importa_proptech_api() -> None:
    import proptech_api  # noqa: F401


def test_importa_proptech_worker() -> None:
    import proptech_worker  # noqa: F401
