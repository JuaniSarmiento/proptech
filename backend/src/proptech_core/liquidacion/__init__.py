"""Módulo `liquidacion`: preliquidación, emisión y distribución de las expensas (change 7).

Importa sólo la `aplicacion` de `complejos`, `gastos`, `cuenta_corriente` y `acceso`, y
`compartido`; ningún otro módulo lo importa (E1 del diseño,
`openspec/changes/archive/2026-11-16-liquidacion-y-emision`).
No escribe SQL propio: lee lo ajeno por la `aplicacion` de su dueño.
"""
