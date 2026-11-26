# Proposal

> Acuerdo previo: D-169 (26/11/2026), por la delegación escrita de Juani (D-168).

## Why

R12 está vigente pero sólo su parte manual (cambio 6): hoy cada gasto se tipea. HU-A3 pide cargar una factura con una
foto: el QR de ARCA trae CUIT, número, fecha e importe, y la IA completa lo que el QR no trae.

## Gobernanza

**HIGH**: facturas con CUIT y montos que salen a un servicio externo de IA (OpenRouter, D-164); no toca la cuenta
corriente.

## What Changes

- **H-036** subir la factura, leer el QR de ARCA y dejar el gasto en borrador, con duplicado, receptor y link firmado.
- **H-037** la IA propone concepto, período, categoría y grupo; costo por llamada; control de monto atípico (R23); el
  gasto queda `sin_ia` o `en_revision`.

## Qué queda fuera

La pantalla (6c); la validación del CAE contra ARCA (WSCDC); facturas en dólares más allá de `importe × ctz`.

## Knowledge Base Impact

`05` (R12, R23), `04`, `12` (ficha 14), `09` (D-169), `15` al cerrar.

## Aprobación

Firmado por el orquestador por delegación escrita de Juani, 26/11/2026 (D-169, D-168), antes de construir.
