# Proposal

> Acuerdo previo (Juani, 24/11/2026, en el chat; va a D-167 con H-027, K02): riesgo HIGH; ven la morosidad
> super admin, administrador, contador, auxiliar y consejo, y exportan sólo super admin, administrador y
> contador; los intereses son los registrados en el libro e impagos, sin estimar los corridos; la antigüedad
> sale de la liquidación vencida más vieja con algo impago y se cuenta desde su vencimiento; aparecen sólo las
> unidades con deuda vencida, con los morosos críticos primero; cada fila lleva la unidad y el nombre de sus
> propietarios, sin datos de contacto; el Excel lleva los montos como números con formato de pesos.

## Why

El 4c dejó la situación de cobranza de cada cuenta (`situacion_del_edificio`, R20 y R30) y el 8 dejó los
pagos confirmados en el libro, pero el administrador no tiene dónde ver quién debe, cuánto y desde cuándo:
no hay ruta, ni pantalla, ni exportación. HU-A8 es la primera lectura de la cobranza para el personal y la
base del 10b (libre deuda y gestión judicial), del 11 (portal) y del 12 (consejo).

## Gobernanza

**HIGH** (Juani, 24/11/2026). Es de sólo lectura y no escribe en el libro, pero muestra plata y datos
personales (quién debe y cuánto) detrás de permisos por perfil y alcance, y el Excel saca esos datos del
sistema. Requiere la aprobación escrita y fechada de Juani, Alberto o Emiliano en `## Aprobación` antes de
escribir código (D-094, D-111).

## What Changes

- **La lectura de la morosidad (H-027)**: `GET /api/complejos/{id}/morosidad` con las unidades que tienen deuda
  vencida a hoy: unidad, propietarios, etiqueta de R20/R30, total vencido, capital, intereses, liquidaciones
  vencidas, vencimiento más viejo impago y días; el resumen del edificio y la fecha de los intereses. Completa
  la lectura del 4c con capital e interés por separado y el vencimiento más viejo. Acción nueva
  `ver_morosidad` (SA, AP, AE, CP, CE, AX, CO).
- **El Excel (H-028)**: `GET /api/complejos/{id}/morosidad/excel` con la misma lista, montos numéricos con
  formato de pesos, totales al pie y el encabezado con edificio y fechas. Acción nueva `exportar_morosidad`
  (SA, AP, AE, CP, CE).
- **La pantalla (H-029)**: "Morosidad" en el menú del edificio para quien tiene `ver_morosidad`, con el
  resumen, la lista y el botón de exportar sólo para quien tiene `exportar_morosidad`. Pasa por impeccable.
- **Migraciones** desde `0048`: sólo el vocabulario de las dos acciones nuevas.

## Qué queda fuera

- La condonación, la marca de gestión judicial y su exclusión del cálculo de moroso crítico, y el libre
  deuda: 10b.
- El interés corrido desde la última emisión (no se estima: D-167).
- Las cuentas de persona (4d), los avisos a morosos (13) y la vista del consejo con sus otras lecturas (12).
- Filtros, búsqueda o historial de la morosidad a una fecha pasada: la lista es a hoy.

## Capabilities

### New Capabilities

- `morosidad`: la lectura de la morosidad por unidad, su exportación a Excel y su pantalla.

## Impact

- **Código**: `cuenta_corriente/dominio/cobranza.py` (capital, interés y vencimiento más viejo en la
  situación), `cuenta_corriente/aplicacion/` (la lectura de la morosidad), `acceso/dominio/permisos.py` (dos
  acciones), `proptech_api/morosidad.py` (nuevo, con su dependencia `hoy`), `web/src/app/edificios/[id]/`
  (pantalla y sección del menú), `web/e2e/api-falsa.ts`.
- **Base**: `0048` (`ver_morosidad`) y `0049` (`exportar_morosidad`), sólo vocabulario de auditoría.
- **Tests existentes que cambian** (L-064, L-084, L-090): `_RUTAS_CUBIERTAS` y los barridos que lo recorren,
  `test_vocabulario_configuracion.py`, los tests de acciones por perfil, `test_sesion_api.py`, el menú.
- **Consumidores**: 10b (libre deuda y exclusión judicial), 11 (portal), 12 (consejo), 13 (avisos).

## Lecciones que aplican (`knowledge-base/15_lecciones.md`)

- **L-064, L-084, L-090, L-100**: rutas y acciones nuevas tocan los tests estructurales; correr los barridos de
  `_RUTAS_CUBIERTAS`, ruff y mypy enteros.
- **L-092, L-095**: conteos por administración del mundo; el runner corre el commit.
- **L-019, L-035, L-049, L-061**: RED por aserción; cada garantía con su caso verde real.
- **L-094, L-096**: la lectura sale de `FotoDeCuenta` y `calcular_estado`, el interés neto de ajustes.
- **L-066, L-101**: el Excel se verifica leyéndolo con `openpyxl`; la pantalla no redondea.
- **L-085, L-087, L-099, L-101**: locators exactos, menú por acción, descarga sin perder el gesto.

## Knowledge Base Impact

| Documento | Acción | Qué |
|---|---|---|
| `knowledge-base/05_reglas_de_negocio.md` | REWRITE | R20: dónde vive el listado, antigüedad e intereses |
| `knowledge-base/03_actores_y_roles.md` | REWRITE | `ver_morosidad` y `exportar_morosidad` |
| `knowledge-base/06_funcionalidades.md` | REWRITE | HU-A8 con lo construido |
| `knowledge-base/08_arquitectura_propuesta.md` | REWRITE | la ruta y el módulo de la lectura |
| `knowledge-base/09_decisiones_y_supuestos.md` | APPEND | D-167 (acuerdos del 24/11/2026) y las que salgan |
| `knowledge-base/12_fichas_de_changes.md` | REWRITE | ficha 10a cerrada con su deuda |
| `knowledge-base/15_lecciones.md` | APPEND | lo que enseñe |
| `CHANGES.md` | REWRITE | estado de C-14 |

## Aprobación

Gobernanza HIGH (D-094, D-111). La completa Juani, Alberto o Emiliano, con fecha y alcance.

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| Juani Sarmiento | 24/11/2026 | Por adelantado (en el chat: "podes trabajar solo, te doy el permiso y armarte vos el change directamente y despues hacemos la demo juntos"): la propuesta completa del 10a y sus elecciones de `design.md` con la recomendación del orquestador, sobre los acuerdos del encabezado, partida en H-027 a H-029, sin rompedor (D-152); los criterios los escribe el orquestador bajo esta firma y lo que no me cierre en la demo vuelve a En proceso |
