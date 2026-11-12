# Contrato que asume la aceptación de H-008

La aceptación de H-008 (`aceptacion/H-008/tests/` y `aceptacion/H-008/e2e/`) es de caja negra: entra
por la API real y por el navegador. Esto es exactamente lo que espera del código. Si el constructor
necesita cambiar algo de esta lista, frena y lo pide: cambiarlo obliga a congelar otra aceptación.

Fuente: `HISTORIAS.md` (H-008), `openspec/changes/importacion-desde-excel/design.md` (D1, D2, D5, D6,
D9, D10, D11; E6, E7, E8, E13, E14 en su recomendación), la spec `borrador-de-saldos` y el contrato de
H-007 (`aceptacion/H-007/CONTRATO.md`), que sigue valiendo entero: misma ruta de subida, mismo formato
del 422 y del 409, mismos números (E14).

## Las hojas `Saldos` y `Control`

Encabezados en la fila 1 por **nombre exacto** (no por posición; columnas extra se ignoran):

| Hoja | Encabezados |
|---|---|
| `Saldos` | `Unidad`, `Período`, `Vencimiento`, `Concepto`, `Importe`, `Interés acumulado` |
| `Control` | `Unidad`, `Saldo según el administrador` |

- En un edificio con el padrón ya cargado, el archivo trae `Saldos` y `Control` sin hoja `Unidades`
  (E7). `Control` es obligatoria cuando hay `Saldos`: si falta, error de archivo (`fila: null`) que
  nombra `Control` (en `hoja` o en `motivo`).
- Encabezado faltante en `Saldos` o `Control`: error de archivo con `hoja` y `columna` = el encabezado
  faltante, `fila: null`.
- Una fila de `Saldos` es:
  - **detalle**: `Período` (`AAAA-MM` o una fecha con día 1), `Vencimiento` (fecha), `Concepto`
    (`Ordinaria`, `Fondo de reserva`, `Extraordinaria`), `Importe` ≥ 0, `Interés acumulado` ≥ 0 (vacío
    = 0);
  - **total único**: sin `Período`, `Vencimiento` ni `Concepto`, `Importe` ≥ 0;
  - **crédito**: `Importe` negativo, sin `Período` ni `Concepto` (y sin interés).
- Errores de fila de `Saldos` (hoja `Saldos`, la fila del Excel, la columna):
  | Caso | Columna |
  |---|---|
  | unidad que no está en el padrón | `Unidad` |
  | período posterior al mes de la migración, o que no es un mes (`2026-13`) | `Período` |
  | vencimiento posterior a la fecha de migración, o vacío en una fila con período | `Vencimiento` |
  | dos vencimientos en el mismo período de una unidad | `Vencimiento`, en la segunda fila |
  | concepto fuera del vocabulario | `Concepto` |
  | importe con más de 2 decimales o ambiguo (`1.234`) | `Importe` |
  | interés acumulado negativo | `Interés acumulado` |
  | período de una unidad cuyas filas suman capital 0 y traen interés (E11 del 4c) | `Interés acumulado`, en la fila de ese período |
  | unidad que mezcla filas con y sin período | `Período`, en la primera fila cuyo modo difiere del de la primera fila de esa unidad |
  | crédito con período | `Período` |
  | crédito con concepto | `Concepto` |
- Errores de fila de `Control`: unidad que no está en el padrón (`Unidad`); unidad repetida (`Unidad`, en
  la segunda, y el motivo nombra la otra fila: "repetida, ya está en la fila 2").
- **Todos** los errores juntos, y un rechazo no escribe nada (ni `importacion`, ni filas de borrador, ni
  control, ni auditoría, ni libro).

## La subida (`POST /api/complejos/{id}/importaciones`, de H-007)

- Un archivo válido con `Saldos` y `Control` da **201** con `filas_de_saldo` = la cantidad de filas de
  datos de `Saldos` (7 en la base de la aceptación).
- Guarda el borrador y **no toca el libro**: ninguna `cuenta`, `obligacion` ni `movimiento` nuevo.
- Con el padrón ya creado, una subida nueva (otro contenido) **descarta** la importación en `borrador`
  anterior (`estado = 'descartada'`) y la nueva queda en `borrador`.

## La comparación

### `GET /api/complejos/{complejo_id}/importaciones/comparacion`

La del borrador vigente del edificio (el único en estado `borrador`). Alcance y tenant como siempre:
otra administración o fuera de alcance → 404 `{"detail": "no encontrado"}`.

```json
{
  "importacion_id": "<uuid>",
  "unidades": [
    {"unidad": "1A", "unidad_id": "<uuid>", "borrador": "169000.00", "control": "159000.00",
     "diferencia": "10000.00", "aviso": "El primer interés del sistema cubre octubre de 2026"}
  ],
  "total_borrador": "320000.00",
  "total_control": "320000.00",
  "unidades_con_diferencia": 2,
  "requiere_aceptacion": true,
  "aceptacion": null
}
```

- Una entrada por cada unidad con saldo **o** con control. Montos como texto con dos decimales, con
  signo `-` si son negativos.
- `borrador` = capital + interés importado − crédito de la unidad; `control` = el saldo de `Control` (0
  si la unidad no está); `diferencia` = `borrador` − `control`.
- `aviso`: el texto exacto `"El primer interés del sistema cubre <mes> de <año>"` (con el mes de la
  migración en minúscula, por ejemplo `octubre de 2026`) en cada unidad con deuda (borrador con capital
  mayor que cero) cuando la forma de cálculo de la versión de configuración vigente a la fecha de
  migración es `mes_entero` (E13, E18 del 4c); `null` en las demás, con `proporcional_por_dia` o sin
  versión vigente.
- `requiere_aceptacion`: `true` si hay alguna diferencia y no hay una aceptación vigente de este
  borrador.
- `aceptacion`: `null`, o `{"aceptacion_id", "diferencias": [{"unidad", "borrador", "control",
  "diferencia"}], "aceptada_por": "<persona_id>", "aceptada_en": "<ISO 8601 con zona>"}` de la
  aceptación de **este** borrador (la de un borrador descartado no se muestra).

### `POST /api/complejos/{complejo_id}/importaciones/aceptacion-de-diferencias`

- Cuerpo JSON `{"importacion_id": "<uuid>"}`.
- Orden de chequeo (D7 del 2a): edificio fuera de alcance → 404; sin el permiso
  `aceptar_diferencias_de_saldos` → 403 con el cuerpo de siempre (nombra el permiso); sin sesión → 401.
- **201** con `{"aceptacion_id", "diferencias": [...las unidades con diferencia distinta de 0, con
  unidad, borrador, control y diferencia...], "aceptada_por": "<persona_id>", "aceptada_en": "<ISO 8601
  con zona>"}`, una fila en `aceptacion_de_diferencias` y una auditoría `aceptar_diferencias_de_saldos`.
- **409** `{"detail": "conflicto", "campo": ...}`, sin escribir nada:
  - `"diferencias"`: el borrador no tiene diferencias;
  - `"aceptacion"`: este borrador ya tiene una aceptación (aceptar dos veces);
  - `"importacion_id"`: la importación no es el borrador vigente (por ejemplo, la descartada);
  - `"estado_migracion"`: la migración está `confirmada` o `sin_saldos_previos`.
- Toma `SELECT ... FOR UPDATE` del complejo (E8): dos aceptaciones simultáneas del mismo borrador dan una
  201 y una 409, con una sola fila y una sola auditoría.

## La base

- Migración `0037` (revisión `"0037"`, sobre la `0036`), en `backend/migraciones/versions/0037_*.py`.
- `fila_de_saldo_importada`: al menos `importacion_id`, `unidad_id`, `fila` (la del Excel), `tipo`
  (`detalle`, `total` o `credito`), `periodo` (date, el día 1; nulo en total y crédito), `vencimiento`
  (date; nulo en total y crédito), `concepto` (`ordinaria`, `fondo_de_reserva`, `extraordinaria`; nulo en
  total y crédito), `importe` (`NUMERIC(14,2)`, siempre ≥ 0: el crédito se guarda positivo con `tipo =
  'credito'`) e `interes_acumulado` (`NUMERIC(14,2)`, 0 si vino vacío).
- `control_de_saldo`: al menos `importacion_id`, `unidad_id`, `fila` y el saldo.
- `aceptacion_de_diferencias`: al menos `id` (el `aceptacion_id`), `administracion_id`,
  `importacion_id`, `aceptada_por` (la persona) y `aceptada_en`. **De sólo agregar**: en
  `TABLAS_DE_SOLO_AGREGAR`, `UPDATE`/`DELETE` de la app → `42501`, `UPDATE`/`DELETE`/`TRUNCATE` del
  arranque → `P0001`; está en `infra/ci/ensayo-roles.sh` (`ALTER TABLE aceptacion_de_diferencias OWNER
  TO`) y en los tests que bajan migraciones (L-083).
- Las tres tablas con RLS activada **y forzada**; otra administración no ve sus filas.
- `aceptar_diferencias_de_saldos` en `Accion`, en la matriz sólo para super admin y administrador
  principal (E6; el administrador por edificio **no**), y en `accion_de_auditoria`.
- Los tests estructurales siguen verdes (fronteras con el dueño de las tablas nuevas, rutas protegidas
  con las dos rutas nuevas en `_RUTAS_CUBIERTAS`, vocabulario).

## La pantalla (`/edificios/{id}/importar/comparacion`)

- Encabezado (`heading`) **"Comparación de saldos"**.
- Tabla con nombre accesible **"Comparación por unidad"**, columnas **Unidad**, **Borrador**,
  **Control** y **Diferencia**; una fila por unidad, montos en formato argentino (`169.000,00`); el aviso
  de mes entero dentro de la fila de cada unidad que lo tiene.
- Los totales con los textos **"Total del borrador"** y **"Total de control"** y sus montos, y
  **"<n> unidades con diferencia"** (también `0 unidades con diferencia`).
- Botón **"Aceptar diferencias"** sólo si `requiere_aceptacion`; abre una confirmación (`dialog` o
  `alertdialog`) que nombra **"<n> unidades con diferencia"** y tiene el botón **"Aceptar"**. Al
  confirmar, la web manda `POST .../importaciones/aceptacion-de-diferencias` con
  `{"importacion_id": ...}` y muestra una región (`role="region"`) **"Diferencias aceptadas"**.
- 403 al aceptar: un `alert` con **"No podés aceptar diferencias en este edificio."**

## La API falsa (`web/e2e/api-falsa.ts`)

| Edificio | `GET .../importaciones/comparacion` | `POST .../aceptacion-de-diferencias` |
|---|---|---|
| `00000000-0000-0000-0000-000000000801` | `importacion_id` `00000000-0000-0000-0000-000000008801`; `1A` 169000.00 / 159000.00 / 10000.00, `1B` 105000.00 / 105000.00 / 0.00, `2A` 52000.00 / 62000.00 / -10000.00; aviso de mes entero en las tres; totales 326000.00 y 326000.00; `unidades_con_diferencia` 2; `requiere_aceptacion` true | 201 |
| `00000000-0000-0000-0000-000000000802` | `1A` 169000.00 / 169000.00 / 0.00 sin aviso; `unidades_con_diferencia` 0; `requiere_aceptacion` false | (no se llama) |
| `00000000-0000-0000-0000-000000000803` | igual que el 801 | 403 `sin_permiso` |

- Los tres responden las lecturas que necesite la pantalla como un edificio con la migración
  `pendiente`.
- El `POST` queda en `/api/__debug/ultima-escritura` con su cuerpo crudo (JSON).
