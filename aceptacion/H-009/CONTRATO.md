# Contrato que asume la aceptación de H-009

La aceptación de H-009 (`aceptacion/H-009/tests/` y `aceptacion/H-009/e2e/`) es de caja negra: entra
por la API real, por el caso de uso de emisión del libro (C05) y por el navegador. Esto es exactamente lo
que espera del código. Si el constructor necesita cambiar algo de esta lista, frena y lo pide: cambiarlo
obliga a congelar otra aceptación.

Fuente: `HISTORIAS.md` (H-009), `openspec/changes/importacion-desde-excel/design.md` (D5, D7, D9, D10,
D11; E6, E8, E10, E12, E15 en su recomendación), la spec `confirmacion-de-saldos`, y los contratos de
H-007 (`aceptacion/H-007/CONTRATO.md`) y H-008 (`aceptacion/H-008/CONTRATO.md`), que siguen valiendo
enteros (subida, comparación, aceptación, formato del 422 y del 409), y el de `registrar_saldo_inicial`
del 4c (`aceptacion/H-005/CONTRATO.md`).

## Confirmar

### `POST /api/complejos/{complejo_id}/importaciones/confirmacion`

- Cuerpo JSON `{"importacion_id": "<uuid>"}`.
- Orden de chequeo (D7 del 2a): edificio fuera de alcance (otra administración, o administrador de otro
  edificio) → 404 `{"detail": "no encontrado"}`; sin el permiso `confirmar_saldos_iniciales` → 403 con
  el cuerpo de siempre (nombra el permiso); sin sesión → 401.
- En **una** transacción, con `SELECT ... FOR UPDATE` del complejo (E8, el mismo candado que "sin saldos
  previos"): estado `pendiente`; la importación es el borrador vigente; tiene filas de saldo (E10); sus
  diferencias están aceptadas si las hay; traduce las filas del borrador a los tipos del 4c (concepto a
  componente, crédito a `FilaDeCredito`, total a `FilaDeTotal`) y llama a `registrar_saldo_inicial` con
  `operacion_id` = el id de la importación, `fecha_de_migracion` = la de la importación y
  `OrigenDeCarga(tipo="importador", archivo=<nombre del archivo subido>)`; pasa el edificio a
  `confirmada` (por un caso de uso de `complejos.aplicacion`) y la importación a `confirmada`; y audita
  `confirmar_saldos_iniciales`.
- **201**:

  ```json
  {
    "importacion_id": "<uuid>",
    "carga_id": "<uuid de carga_de_saldo_inicial>",
    "estado_migracion": "confirmada",
    "totales": {"capital": "320000.00", "interes_importado": "6000.00", "credito": "6000.00"},
    "confirmada_por": "<persona_id>",
    "confirmada_en": "<ISO 8601 con zona>"
  }
  ```

  `totales` son los del edificio que devuelve `registrar_saldo_inicial` (`SaldoInicialRegistrado.total`),
  como texto con dos decimales.
- **409** `{"detail": "conflicto", "campo": ...}`, sin escribir nada (ni libro, ni estado del edificio,
  ni estado de la importación, ni auditoría):
  - `"diferencias"`: el borrador tiene diferencias y no hay una aceptación vigente de este borrador;
  - `"importacion_id"`: la importación no existe o no es el borrador vigente (por ejemplo, la descartada);
  - `"saldos"`: la importación no trae filas de saldo (archivo sin hoja `Saldos`, E10);
  - `"estado_migracion"`: la migración está `confirmada` o `sin_saldos_previos` (también la segunda de
    dos confirmaciones, y la que pierde contra "sin saldos previos").
- **422** con un texto que nombra `fecha_de_migracion` si `registrar_saldo_inicial` rechaza la fecha
  (una fecha de migración posterior a hoy); el edificio sigue `pendiente`, la importación `borrador`, sin
  carga ni auditoría de confirmar.
- Con el edificio `confirmada`, `POST .../importaciones` (subir) y `POST .../aceptacion-de-diferencias`
  dan 409 `estado_migracion` (H-007 y H-008 ya lo exigen para la migración cerrada).
- Dos confirmaciones simultáneas: una 201 y otra 409 `estado_migracion`, con una sola carga y una sola
  auditoría. Confirmar contra `POST .../estado-de-migracion/sin-saldos-previos` a la vez: uno gana (2xx)
  y el otro da 409 `estado_migracion`; si gana confirmar, el edificio queda `confirmada` con una carga; si
  gana "sin saldos previos", queda `sin_saldos_previos`, sin carga y la importación en `borrador`.

## Lo que la aceptación lee de la base

- `complejo.estado_migracion` (`confirmada`), `importacion.estado` (`confirmada`).
- `carga_de_saldo_inicial` del edificio: una sola, con `operacion_id` = id de la importación, `origen =
  'importador'`, `archivo` = el nombre del archivo subido y `fecha_de_migracion` = la de la importación.
- `origen_de_saldo_inicial`: cada fila de `Saldos` ligada a lo que formó (obligación, interés importado o
  crédito `saldo_inicial`), con su número de fila del Excel.
- `auditoria.accion = 'confirmar_saldos_iniciales'`, una por confirmación.
- La aceptación puede hacer `UPDATE importacion SET fecha_de_migracion = ...` y
  `UPDATE complejo SET estado_migracion = ...` como `proptech_app` (las tablas de la importación son
  mutables por la app con RLS, D10; el estado de migración ya lo era).

## La base

- Migración `0038` (revisión `"0038"`, sobre la `0037`), en `backend/migraciones/versions/0038_*.py`: agrega
  `confirmar_saldos_iniciales` a `accion_de_auditoria` y nada más al vocabulario; la bajada lo saca y deja
  el esquema de la `0037` igual (no agrega tablas).
- `confirmar_saldos_iniciales` en `Accion` y en la matriz sólo para super admin y administrador principal
  (E6; el administrador por edificio **no**).
- La ruta nueva en `_RUTAS_CUBIERTAS` de `tests/integracion/test_rutas_protegidas.py`; los tests de
  fronteras y de vocabulario siguen verdes.

## La web

- `textoDeEstados.ts`: `confirmada` → **"Saldos iniciales confirmados"** (nunca "Estado de migración
  desconocido").
- **Resumen** (`/edificios/{id}`):
  - con la migración `confirmada`: el texto "Saldos iniciales confirmados" y **ningún** link "Importar
    desde Excel" ni "Confirmar sin saldos previos";
  - con la migración `pendiente`: el paso 7 ofrece dos links, **"Importar desde Excel"** (`href`
    `/edificios/{id}/importar`) y **"Confirmar sin saldos previos"** (`href`
    `/edificios/{id}/saldos-previos`).
- **Comparación** (`/edificios/{id}/importar/comparacion`, de H-008):
  - botón **"Confirmar saldos"**, habilitado sólo sin diferencias o con ellas aceptadas
    (`requiere_aceptacion` falso), deshabilitado si hay diferencias sin aceptar;
  - abre una confirmación (`dialog` o `alertdialog`) cuyo texto dice que **"no se deshace"** y tiene el
    botón **"Confirmar"**; al confirmar, la web manda `POST .../importaciones/confirmacion` con
    `{"importacion_id": ...}` y muestra una región (`role="region"`) **"Saldos iniciales confirmados"**;
  - 403 al confirmar: un `alert` con **"No podés confirmar saldos en este edificio."**

## La API falsa (`web/e2e/api-falsa.ts`)

| Edificio | Resumen / estado | `GET .../importaciones/comparacion` | `POST .../importaciones/confirmacion` |
|---|---|---|---|
| `00000000-0000-0000-0000-000000000901` | `pendiente` | `importacion_id` `00000000-0000-0000-0000-000000009901`; `1A` 169000.00 / 169000.00 / 0.00 sin aviso; `unidades_con_diferencia` 0; `requiere_aceptacion` false; `aceptacion` null | 201 con el cuerpo de arriba |
| `00000000-0000-0000-0000-000000000902` | `confirmada` | (no se llama) | (no se llama) |
| `00000000-0000-0000-0000-000000000903` | `pendiente` | `1A` 169000.00 / 159000.00 / 10000.00; `unidades_con_diferencia` 1; `requiere_aceptacion` true | (no se llama) |
| `00000000-0000-0000-0000-000000000904` | `pendiente` | igual que el 901 | 403 `sin_permiso` |

- Los cuatro responden las lecturas que necesiten el resumen y la comparación como cualquier edificio de
  la API falsa, con su `estado_migracion`.
- El `POST` queda en `/api/__debug/ultima-escritura` con su cuerpo crudo (JSON).
