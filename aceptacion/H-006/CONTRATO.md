# Contrato que asume la aceptación de H-006

La aceptación de H-006 (`aceptacion/H-006/tests/`) es de caja negra. Esto es exactamente lo que espera
del código. Si el constructor necesita cambiar algo de esta lista, frena y lo pide: cambiarlo obliga a
congelar otra aceptación.

## Módulo y funciones

`proptech_core.cuenta_corriente.aplicacion.cobranza` (design D6) define:

```python
def situacion_de_cuenta(sesion: Session, *, cuenta_id: UUID, fecha: date) -> SituacionDeCobranza
def situacion_del_edificio(sesion: Session, *, complejo_id: UUID, fecha: date) -> Sequence[SituacionDeCuenta]
```

- Sin identidad: el tenant es el de la sesión (RLS). Una cuenta o un edificio que la sesión no ve da
  `NoEncontrado` (de `cuenta_corriente.aplicacion.errores`).
- Sin versión de configuración vigente a `fecha` (ninguna, o sólo versiones que empiezan después) da
  `Conflicto("configuracion")`, también en `situacion_de_cuenta`.
- Es una lectura: ningún `INSERT`, `UPDATE` ni `DELETE`, y ningún candado (`FOR UPDATE`,
  `FOR NO KEY UPDATE`, `pg_advisory_*`).
- `fecha` es la **fecha de clasificación** (E14): decide qué obligaciones están vencidas (`fecha >
  vencimiento + días de gracia`, con la gracia y el umbral de la versión vigente a `fecha`) pero el libro
  se lee como está al leer: un pago con fecha valor posterior a `fecha` cuenta igual.

La función pura `clasificar` de `cuenta_corriente.dominio.cobranza` no la usa la aceptación (es interna
al diseño).

## `SituacionDeCobranza`

Objeto (dataclass o similar) con estos campos, por nombre:

| Campo | Tipo | Qué es |
|---|---|---|
| `total_vencido` | `Dinero` | Residual de capital más residual de interés de las obligaciones vencidas a `fecha`, sin restar el crédito a favor |
| `liquidaciones_vencidas` | `int` | Obligaciones vencidas con residual de **capital** mayor que cero (una con sólo interés impago no cuenta, E7) |
| `bajo_umbral` | `bool` | `0 < total_vencido < umbral` (R30, E6: $500 o más no queda bajo) |
| `deuda_de_intereses` | `bool` | No está bajo el umbral, hay total vencido y es todo interés (D-109.4) |
| `moroso_critico` | `bool` | No está bajo el umbral y `liquidaciones_vencidas >= 2` (R20) |
| `etiqueta` | `str` | Una sola, con la precedencia de D6 (abajo) |

Valores de `etiqueta`, en orden de precedencia: `"sin_deuda_vencida"` (total vencido cero) →
`"bajo_umbral"` → `"deuda_de_intereses"` → `"moroso_critico"` → `"con_deuda_vencida"`.

## Cada entrada del listado del edificio (`SituacionDeCuenta`)

Una por cada cuenta **de unidad** del edificio (las de persona quedan fuera hasta el 4d), con:

- `cuenta_id: UUID` y `unidad_id: UUID`;
- los seis campos de `SituacionDeCobranza`, directos en la entrada **o** en un atributo `situacion` que
  sea un `SituacionDeCobranza` (la aceptación acepta las dos formas).

El orden del listado no importa.

## Cómo arma los datos la aceptación

Sólo con casos de uso que ya existen: `registrar_emision`, `anular_emision`, `registrar_credito`,
`correcciones.corregir` (contra-asiento de un pago) y `registrar_saldo_inicial` (H-005). La
configuración la inserta por SQL en `configuracion_versionada` (tasa, gracia, `umbral_saldo_chico`,
`vigente_desde`). Las cuentas de persona (C16) las inserta por SQL, porque no hay caso de uso que las cree.
