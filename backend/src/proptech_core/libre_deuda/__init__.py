"""Módulo `libre_deuda`: el certificado de libre deuda de una unidad (10b
`condonacion-judicial-y-libre-deuda`, H-041, R21, D-171, D-172).

Importa a `acceso`, `complejos`, `cuenta_corriente` y `pagos` sólo por su `aplicacion`; ninguno de
ellos lo importa (sin ciclos). Es dueño de `certificado_de_libre_deuda` (migración `0056`): lee el
libro y no escribe nada en él.
"""
