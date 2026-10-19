"""Los cuatro tipos de unidad de D-029 (deuda del 1b con dueño 3, tarea 2.3,
nota N9 c de `design.md`).

Una sola constante para dos consumidores: `parametros.py` (rechaza un tipo de
unidad fuera de esta lista en `config/parametros.yaml`) y el `CHECK` de la
migración de la tarea 3.1 sobre `unidad.tipo`. Si D-029 cambiara los cuatro
tipos, es una migración nueva, igual que el vocabulario de auditoría (D14);
no una tabla de tipos por edificio (alternativa descartada en `design.md`,
D2)."""

from __future__ import annotations

TIPOS_DE_UNIDAD_VALIDOS: frozenset[str] = frozenset({"departamento", "cochera", "baulera", "local"})
