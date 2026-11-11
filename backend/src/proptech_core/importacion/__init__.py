"""Módulo `importacion`: carga del padrón y de los saldos previos de un edificio desde la plantilla
de Excel (`openspec/changes/importacion-desde-excel`, design D0).

Importa a `complejos`, `acceso` y `cuenta_corriente` sólo por su `aplicacion`; ninguno de ellos lo
importa (sin ciclos). Es dueño de sus tablas (`importacion` desde la migración `0036`).
"""
