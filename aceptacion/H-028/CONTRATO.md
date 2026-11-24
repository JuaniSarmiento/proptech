# Contrato que asume la aceptación de H-028

Caja negra por la API real, con la identidad inyectada como en H-027. Si el constructor necesita cambiar algo de
esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-028), `openspec/changes/morosidad/design.md` (E6, E8), D-167 y el contrato de H-027, que
sigue rigiendo para `GET /api/complejos/{id}/morosidad`.

## Quién puede

Acción nueva `exportar_morosidad` en `Accion` y en `_MATRIZ`: super admin, administrador principal y por
edificio, contador principal y por edificio. Auxiliar, consejo y vecinos no. Vocabulario de auditoría con su
migración (sube y baja, como `0048`). Exportar no se audita.

Orden de chequeo (D7): edificio fuera del alcance u otra administración, **404** `{"detail": "no encontrado"}`;
sin `exportar_morosidad`, **403** con `permiso_faltante` `exportar_morosidad`.

## `GET /api/complejos/{id}/morosidad/excel`

Usa la misma dependencia `proptech_api.morosidad.hoy` y la misma lectura que la ruta de H-027 (mismas filas, mismo
orden, mismos montos). **200** con:

- `content-type`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- `content-disposition`: `attachment; filename="morosidad-<edificio>-<AAAA-MM-DD>.xlsx"`, con el nombre del edificio
  en minúscula, sin tildes y con todo lo que no sea `[a-z0-9]` colapsado a un guion (sin guiones al principio ni al
  final): "Torre Ficticia" el 18/11/2026 da `morosidad-torre-ficticia-2026-11-18.xlsx`.

Un libro con una sola hoja, llamada `Morosidad`:

| Celda | Valor |
|---|---|
| `A1` | `Morosidad` |
| `B1` | el nombre del edificio |
| `A2`, `B2` | `Fecha` y la fecha de la lista (celda de fecha) |
| `A3`, `B3` | `Intereses al` y `intereses_al` (celda de fecha), o vacía si es nula |
| fila 5 | los títulos: `Unidad`, `Propietarios`, `Situación`, `Total vencido`, `Capital`, `Intereses`, `Liquidaciones vencidas`, `Vencida desde`, `Días` (columnas `A` a `I`) |
| desde la fila 6 | una fila por unidad, en el orden de la API |
| la fila siguiente a la última unidad | `A` = `Total`; `D`, `E` y `F` = las sumas; el resto vacío |

En cada fila de unidad: `A` el identificador; `B` los propietarios separados por `", "` (vacía si no hay); `C` la
situación en palabras (`moroso_critico` → `Moroso crítico`, `con_deuda_vencida` → `Con deuda vencida`,
`deuda_de_intereses` → `Deuda de intereses`, `bajo_umbral` → `Bajo el umbral`); `D`, `E` y `F` el total vencido, el
capital y los intereses; `G` las liquidaciones vencidas (entero); `H` `vencida_desde` (celda de fecha); `I` los días
(entero).

- **Montos** (`D`, `E` y `F`, también en el total): **números**, nunca texto ni fórmula, con `number_format` que
  contenga `#,##0.00`; iguales al centavo a los de la API.
- Sin email, teléfono ni documento de nadie.
- No escribe nada: `movimiento`, `imputacion`, `obligacion` y `auditoria` quedan iguales.
- Un edificio sin deuda vencida: el encabezado, los títulos y la fila `Total` (en la fila 6) con `0`.
