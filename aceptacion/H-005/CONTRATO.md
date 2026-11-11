# Contrato que asume la aceptación de H-005

La aceptación de H-005 (`aceptacion/H-005/tests/`) es de caja negra. Esto es exactamente lo que espera
del código. Si el constructor necesita cambiar algo de esta lista, frena y lo pide: cambiarlo obliga a
congelar otra aceptación.

## Módulo y función

`proptech_core.cuenta_corriente.aplicacion.saldo_inicial` (design D5) define:

```python
def registrar_saldo_inicial(
    sesion: Session,
    identidad: Identidad,
    *,
    complejo_id: UUID,
    operacion_id: UUID,
    fecha_de_migracion: date,
    origen: OrigenDeCarga,
    unidades: Sequence[UnidadDeSaldoInicial],
    request_id: UUID,
    reloj: Callable[[], datetime],
) -> SaldoInicialRegistrado
```

`reloj()` devuelve un `datetime` con zona. "Hoy" es su fecha: una `fecha_de_migracion` posterior a hoy
se rechaza. Los tests usan las 15:00 UTC del día.

## Tipos de entrada (en el mismo módulo)

Son dataclasses **sin validación propia**: se construyen con cualquier valor y toda la validación la
hace `registrar_saldo_inicial`. Los tests arman pedidos inválidos, por ejemplo un archivo vacío, un
motivo en blanco, un importe negativo o una unidad sin filas, y esperan el rechazo de la función, no
del constructor del tipo. Se construyen siempre con argumentos por nombre:

| Clase | Campos |
|---|---|
| `OrigenDeCarga` | `tipo: str` (`"importador"` o `"manual"`), `archivo: str \| None = None`, `motivo: str \| None = None` |
| `FilaDeDeuda` | `fila: int \| None`, `periodo: date`, `vencimiento: date`, `componente: str` (`ordinaria`, `fondo_de_reserva`, `extraordinaria`), `importe: Dinero`, `interes_acumulado: Dinero` |
| `FilaDeTotal` | `fila: int \| None`, `importe: Dinero`, `interes_acumulado: Dinero` |
| `FilaDeCredito` | `fila: int \| None`, `importe: Dinero` |
| `UnidadDeSaldoInicial` | `unidad_id: UUID`, `modo: str` (`"detalle"` o `"total"`), `filas: tuple[FilaDeDeuda \| FilaDeTotal \| FilaDeCredito, ...]` |

En las dos modalidades se admiten filas de crédito (`FilaDeCredito`).

## Resultado

```python
@dataclass(frozen=True)
class TotalesDeSaldoInicial:
    capital: Dinero            # suma de los componentes de las obligaciones cargadas
    interes_importado: Dinero  # suma de los intereses acumulados
    credito: Dinero            # suma de los créditos

@dataclass(frozen=True)
class SaldoInicialRegistrado:
    operacion_id: UUID
    carga_id: UUID                                   # id de la fila de carga_de_saldo_inicial
    cuentas: dict[UUID, UUID]                        # unidad -> cuenta
    por_unidad: dict[UUID, TotalesDeSaldoInicial]    # unidad -> totales
    total: TotalesDeSaldoInicial                     # del edificio (suma de por_unidad)
```

El replay (mismo `operacion_id` y misma firma) devuelve un resultado igual en `operacion_id`,
`cuentas`, `por_unidad` y `total`, sin escribir nada.

## Errores y campos (de `cuenta_corriente.aplicacion.errores`)

Ningún rechazo escribe nada **en la transacción del llamador**. La función valida antes de escribir o
deshace en un SAVEPOINT, y la transacción sigue usable: los tests cuentan filas en la misma sesión
después del rechazo.

| Caso | Error | `campo` |
|---|---|---|
| Estado de migración `sin_saldos_previos` o `confirmada` (sin carga previa con ese `operacion_id`) | `Conflicto` | `estado_migracion` |
| Otra carga del mismo edificio, con otro `operacion_id` (secuencial o simultánea) | `Conflicto` | cualquiera |
| Mismo `operacion_id` con otra firma del pedido | `Conflicto` | `operacion_id` |
| Vencimiento posterior a la migración; mismo período con vencimientos distintos | `EntradaInvalida` | `vencimiento` |
| Período que no es día 1, o posterior al mes de la migración | `EntradaInvalida` | `periodo` |
| Migración posterior a hoy | `EntradaInvalida` | `fecha_de_migracion` |
| Período que suma capital 0 (E11) | `EntradaInvalida` | `interes_acumulado` |
| Importe de deuda negativo; crédito ≤ 0 | `EntradaInvalida` | `importe` |
| Unidad repetida, o sin filas | `EntradaInvalida` | `unidades` |
| Unidad que mezcla filas de detalle y de total (por ejemplo una `FilaDeTotal` en modo `detalle`); número de fila repetido en la carga | `EntradaInvalida` | `fila` |
| Carga manual con motivo vacío o en blanco | `EntradaInvalida` | `motivo` |
| Importador con archivo vacío | `EntradaInvalida` | `archivo` |
| Unidad de otro edificio; edificio de otra administración | `NoEncontrado` | — |
| Sesión sin transacción abierta | `RegistroFueraDeTransaccion` | — |

El replay se resuelve **antes** del estado de migración (D5): repetir la misma carga con la migración
ya `confirmada` devuelve lo registrado.

## Lo que la aceptación lee del libro y de la base

- **Obligaciones migradas** (`obligacion`): `emision_id` nulo.
  - Con detalle: una por unidad y período, con la suma de cada componente.
  - Con total único: una sola, con todo en `ordinaria`, `periodo` igual al día 1 del mes de la
    migración y `vencimiento` igual a la migración.
- **Interés importado**: un `movimiento` `tipo='interes'`, `sentido='debito'`, `emision_id` nulo, sobre
  la obligación de su período, con `corte` igual a la fecha de migración y por la suma exacta de las
  filas. Nunca entra en la base de R03.
- **Crédito inicial**: un `movimiento` `tipo='saldo_inicial'` con `fecha_valor` igual a la migración,
  imputado con R04 (`lecturas.estado_de_cuenta`: `deuda`, `credito_a_favor`,
  `credito_a_favor_aplicable`).
- **Interés de R03 sobre una obligación migrada**: corre desde el día siguiente a la migración (E13,
  E18).
  - Los tramos (`tramo_de_interes`) nunca cubren días anteriores a ese.
  - Con gracia, se cuenta desde el vencimiento, que en el total único es la migración.
  - Una emisión cuyo corte es la fecha de migración no registra nada ni choca con el importado
    (`uq_mov_interes`).
- **`carga_de_saldo_inicial`**: columnas de D5 (`id`, `administracion_id`, `complejo_id`,
  `operacion_id`, `fecha_de_migracion`, `origen`, `archivo`, `motivo`, `firma_del_pedido`,
  `registrado_por`, `request_id`, `registrado_en`). Tiene estos CHECK:
  - `origen='importador' AND archivo IS NOT NULL`, o bien `origen='manual' AND motivo IS NOT NULL`;
  - `firma_del_pedido ~ '^v1:[0-9a-f]{64}$'`.

  En una carga manual, `archivo` queda nulo; en una del importador, `motivo` queda nulo.
- **`origen_de_saldo_inicial`**: columnas de D5 (`id`, `administracion_id`, `complejo_id`, `carga_id`,
  `cuenta_id`, `fila`, `obligacion_id`, `movimiento_id`, `sentido_del_movimiento`).
  - CHECK: `num_nonnulls(obligacion_id, movimiento_id) = 1` y `fila >= 1`. `fila` es nula sólo en
    una carga manual.
  - FK compuesta a la obligación y al movimiento de la **misma cuenta**.
  - Una fila con importe mayor que 0 liga la obligación de su período, o el crédito. Una fila con
    interés mayor que 0 liga además el movimiento de interés importado.
  - El `TRUNCATE` del arranque se prueba con `CASCADE`.
- **Las dos tablas**:
  - de sólo agregar: están en `TABLAS_DE_SOLO_AGREGAR`, `UPDATE`/`DELETE` como app dan `42501`, y
    `UPDATE`/`DELETE`/`TRUNCATE` como arranque dan `P0001`;
  - con RLS forzada por administración;
  - devueltas al migrador en `infra/ci/ensayo-roles.sh` (`ALTER TABLE <tabla> OWNER TO`).
- **Migración**: `0035`, con `down_revision` igual a `"0034"`. La cabeza de alembic queda en `0035`.
- **Estado de migración**: lo fija el test con `UPDATE complejo SET estado_migracion = ...` como app.
  La carga no cambia el estado: pasarlo a `confirmada` es del 5.
