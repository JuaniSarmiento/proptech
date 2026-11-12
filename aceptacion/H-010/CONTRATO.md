# Contrato que asume la aceptación de H-010

La aceptación de H-010 (`aceptacion/H-010/tests/` y `aceptacion/H-010/e2e/`) es de caja negra: entra
por la API real, por el caso de uso del ajuste (cuando el escenario fija el día con el `reloj`), por el
caso de uso de saldo inicial del 4c (para armar la base), por la emisión del libro (para mirar el
interés) y por el navegador. Esto es exactamente lo que espera del código. Si el constructor necesita
cambiar algo de esta lista, frena y lo pide: cambiarlo obliga a congelar otra aceptación.

Fuente: `HISTORIAS.md` (H-010), `openspec/changes/importacion-desde-excel/design.md` (D8, D9, D10, D11;
E6 y **E11** en su recomendación: el ajuste es una **obligación nueva**, no un movimiento), la spec
`ajuste-de-saldo-inicial`, D-155, y los contratos de H-007 a H-009 (`aceptacion/H-00{7,8,9}/CONTRATO.md`).

## El caso de uso

`proptech_core.importacion.aplicacion.ajuste` define:

```python
def ajustar_saldo_inicial(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    unidad_id: UUID,
    operacion_id: UUID,
    importe: Dinero,
    componente: str,          # "ordinaria", "fondo_de_reserva" o "extraordinaria"
    motivo: str,
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> AjusteRegistrado
```

- **Autoriza y audita** (no es D9 del 4c: el ajuste es una acción propia): permiso
  `ajustar_saldo_inicial` (super admin y administrador principal, E6) y una fila de `auditoria` con esa
  acción, en la misma transacción. No commitea: lo hace el llamador.
- "El día del ajuste" es `reloj().date()` (la misma convención que `registrar_saldo_inicial`).
- La obligación nueva (la crea `cuenta_corriente.aplicacion`, sin emisión, con su `operacion_id`):
  importe en el componente elegido y cero en los otros dos; **período** = primer día del mes de la
  `fecha_de_migracion` de la carga de saldo inicial del edificio; **vencimiento** = el día del ajuste.
- Si la unidad no tiene cuenta, se crea. `bloquear_cuentas` sobre la cuenta e `imputar_pendientes`
  (un crédito a favor se imputa a la obligación nueva, R04).
- Una fila en `ajuste_de_saldo_inicial` con la obligación, el motivo normalizado (recortado), quién y
  cuándo.
- **Replay**: el mismo `operacion_id` con los mismos datos (unidad, importe, componente, motivo)
  devuelve el mismo ajuste sin escribir nada (ni obligación, ni ajuste, ni auditoría); con otro dato
  cualquiera, conflicto en `operacion_id`. Dos pedidos simultáneos con la misma operación dejan un solo
  ajuste y los dos reciben el mismo.
- La interés de R03 de la obligación del ajuste corre desde el día siguiente a su vencimiento, con la
  gracia y la forma vigentes, como cualquier obligación (no hace falta código propio: la emisión ya lo
  calcula). Para la situación de cobranza cuenta como una liquidación cuando vence.

`AjusteRegistrado` (dataclass o similar) tiene, por nombre: `ajuste_id`, `operacion_id`,
`obligacion_id`, `cuenta_id`, `unidad_id`, `importe` (`Dinero`), `componente`, `periodo` (`date`),
`vencimiento` (`date`), `motivo`, `registrado_por`, `registrado_en`.

## La ruta

### `POST /api/complejos/{complejo_id}/unidades/{unidad_id}/ajustes-de-saldo-inicial`

- Cuerpo JSON `{"operacion_id": "<uuid>", "importe": "5000.00", "componente": "ordinaria", "motivo": "..."}`
  (campos extra se rechazan, como en el resto de la API).
- Orden de chequeo (D7 del 2a): edificio fuera de alcance (otra administración, o administrador de otro
  edificio), unidad inexistente o de otro edificio → **404** `{"detail": "no encontrado"}`; sin el
  permiso `ajustar_saldo_inicial` → **403** con el cuerpo de siempre (nombra el permiso); sin sesión →
  **401**.
- **201** con el ajuste en JSON: `ajuste_id`, `operacion_id`, `obligacion_id`, `cuenta_id`, `unidad_id`
  (uuid como texto), `importe` (texto con dos decimales), `componente`, `periodo` y `vencimiento`
  (`YYYY-MM-DD`), `motivo`, `registrado_por` (persona), `registrado_en` (ISO 8601 con zona). El replay
  devuelve el mismo cuerpo (200 o 201).
- **422** que nombra el campo en `loc` (`{"detail": [{"loc": ["body", "<campo>", ...], ...}]}`, el
  formato de validación de la API y del libro), sin escribir nada:
  - `motivo`: vacío, en blanco o de más de 500 caracteres (500 entra);
  - `importe`: cero, negativo, con más de 2 decimales, o que no entra en `NUMERIC(14,2)`;
  - `componente`: cualquier cosa que no sea `ordinaria`, `fondo_de_reserva` o `extraordinaria`
    (`interes` incluido).
- **409** `{"detail": "conflicto", "campo": ...}`, sin escribir nada:
  - `"estado_migracion"`: el edificio está `pendiente` o `sin_saldos_previos`;
  - `"operacion_id"`: el mismo `operacion_id` con otros datos.
- La ruta nueva va en `_RUTAS_CUBIERTAS` de `tests/integracion/test_rutas_protegidas.py`.

## La base

- Migración `0039` (revisión `"0039"`, sobre la `0038`), en
  `backend/migraciones/versions/0039_*.py`: crea `ajuste_de_saldo_inicial` y agrega
  `ajustar_saldo_inicial` a `accion_de_auditoria`, y nada más. La bajada deja el esquema y el
  vocabulario de la `0038` exactamente igual.
- `ajuste_de_saldo_inicial(id, administracion_id, complejo_id, cuenta_id, obligacion_id, operacion_id,
  motivo, registrado_por, request_id, registrado_en)`, con el patrón de las tablas del libro (`0034`,
  `0035`):
  - de sólo agregar: en `TABLAS_DE_SOLO_AGREGAR`, tres triggers, `UPDATE`/`DELETE` de la app dan
    `42501` y del arranque `P0001`, también `TRUNCATE`;
  - RLS forzada por administración;
  - FK compuesta `(administracion_id, complejo_id, cuenta_id, obligacion_id)` → `obligacion` por
    `uq_obligacion_cuenta_id` (el ajuste y su obligación son de la misma cuenta), FK a `complejo` y a
    `persona` (`registrado_por`);
  - CHECK: el motivo tiene de 1 a 500 caracteres y no está en blanco;
  - único `(administracion_id, operacion_id)`.
- Las inserciones de la aceptación usan esas columnas por nombre; `registrado_en` lo pone el test con
  `now()`.
- `ajustar_saldo_inicial` en `Accion` y en la matriz sólo para super admin y administrador principal
  (E6; el administrador por edificio **no**).
- La tabla en `infra/ci/ensayo-roles.sh` (`devolver_al_migrador`, bloque `ALTER TABLE
  ajuste_de_saldo_inicial OWNER TO`) y en las helpers de devolución de los tests (L-083): la aceptación
  corre el barrido de tests que bajan o restauran migraciones.

## La web

- **Padrón** (`/edificios/{id}/unidades`): con la migración `confirmada`, cada unidad tiene un link
  **"Ajustar saldo inicial de {identificador}"** (por ejemplo "Ajustar saldo inicial de 1A") a
  `/edificios/{id}/unidades/{unidad_id}/ajuste-de-saldo-inicial`; con la migración pendiente (o sin
  saldos previos), ningún link de ajuste.
- **Ajuste** (`/edificios/{id}/unidades/{unidad_id}/ajuste-de-saldo-inicial`), D11 e impeccable:
  - título (heading) **"Ajustar saldo inicial"**;
  - campos con label **"Importe"** (se escribe con coma decimal: `5000,00`), **"Concepto"** (un `select`
    con las opciones "Ordinaria", "Fondo de reserva" y "Extraordinaria") y **"Motivo"**;
  - botón **"Registrar ajuste"**, que abre una confirmación (`dialog` o `alertdialog`) cuyo texto dice
    **"no se deshace"** y tiene el botón **"Confirmar"**;
  - al confirmar manda el `POST` de arriba con `importe` como texto con punto y dos decimales
    (`"5000.00"`), el `componente` (`"ordinaria"`), el `motivo` y un `operacion_id` uuid nuevo, y
    muestra una región (`role="region"`) **"Ajuste registrado"** con el importe en formato argentino
    (`5.000,00`) y el motivo;
  - 403 al registrar: un `alert` con **"No podés ajustar saldos en este edificio."**

## La API falsa (`web/e2e/api-falsa.ts`)

| Edificio | `estado_migracion` | Unidad `1A` | `POST .../ajustes-de-saldo-inicial` |
|---|---|---|---|
| `00000000-0000-0000-0000-000000001001` | `confirmada` | `00000000-0000-0000-0000-000000100101` | 201 con el ajuste (importe `5000.00`, motivo el enviado) |
| `00000000-0000-0000-0000-000000001002` | `pendiente` | `00000000-0000-0000-0000-000000100201` | (no se llama) |
| `00000000-0000-0000-0000-000000001003` | `confirmada` | `00000000-0000-0000-0000-000000100301` | 403 `sin_permiso` |

- Los tres responden las lecturas que necesiten el padrón y la pantalla de ajuste (el edificio con su
  `estado_migracion`, sus unidades con `1A`) como cualquier edificio de la API falsa.
- El `POST` queda en `/api/__debug/ultima-escritura` con su cuerpo crudo (JSON).
