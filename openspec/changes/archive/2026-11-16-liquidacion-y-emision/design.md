# Design

## Context

- **Qué hay hoy en `main`** (`52755d5`, después del 5):
  - `cuenta_corriente` (4b, 4c): `registrar_emision(emision_id, complejo_id, periodo, obligaciones)` con
    `ObligacionAEmitir(unidad_id, vencimiento, ordinaria, fondo_de_reserva, extraordinaria)`; rechaza una
    obligación con algún componente negativo o con total cero; calcula y registra el interés de R03 bajo
    los candados de todas las cuentas de unidad del edificio; maneja intentos y re-emisión tras anular;
    devuelve `EmisionRegistrada` con la foto de `saldo_anterior` por cuenta (D12, R06) y los intereses.
    `anular_emision(emision_id, motivo)` agrega el evento `anulada` y nada más: no audita (D9 del 4b) y no
    sabe de "distribuida". `evento_de_emision.tipo` sólo admite `'anulada'` (`ck_evento_tipo`, 0023).
    `emision` no guarda nada de lo que se usó para calcular. El estado ya distingue créditos `retenidos`
    (E16 del 4b) y el interés toma la `fecha_valor` de cada crédito (P38 ya se cumple).
  - `gastos` (6): `gastos_aprobados_del_periodo` (por grupo, tipo y categoría, neto de notas de crédito
    del período), `cargos_aprobados_del_periodo`, `obligatorios_faltantes`; `aprobar_gasto` recibe
    `es_periodo_emitido` inyectable, hoy `_nada_esta_emitido_todavia`. `uq_gasto_factura` impide la
    factura duplicada por complejo. Estados del gasto: `borrador`, `sin_ia`, `en_revision`, `aprobado`.
  - `complejos`: grupos de reparto con su modo de coeficientes (D-100) e `informar_coeficientes`;
    `configuracion_vigente(complejo, fecha)` con `porcentaje_fondo`, `dia_de_vencimiento`,
    `modalidad_de_vencimiento` y los datos de interés; `estado_migracion`.
  - `compartido/reparto.py`: `repartir` (mayor resto, orden natural), `redondear_al_centavo`.
  - `acceso`: las acciones `cargar_gastos_y_preparar_liquidacion` (SA, AP, AE),
    `emitir_y_distribuir_liquidacion` (SA, AP, AE), `anular_liquidacion` (SA, AP),
    `aceptar_alertas_no_bloqueantes` (SA, AP, AE), `aceptar_alertas_bloqueantes` (SA, AP).
- **Fronteras**: sólo se importa entre módulos por `aplicacion`, sin ciclos. `cuenta_corriente` importa
  `complejos`; `gastos` no importa `cuenta_corriente`.
- **Decisiones que ya rigen**: D-157 (acuerdo del 7), D-069, D-070, D-073, D-074, D-075, D-081, D-082,
  D-100, D-109, D-113, D-118, D-123, D-124, D-141, D-153.

## Goals / Non-Goals

**Goals**
- Ver lo que paga cada unidad antes de emitir, sin efectos, con los controles de R34.
- Emitir exactamente lo revisado, en una transacción, dejando guardado todo lo que se usó.
- Distribuir, anular con sus límites y corregir un cargo cobrado de menos.
- El comprobante PDF con links firmados (H-015, después de D-060 y F2c).

**Non-Goals**: ver `proposal.md`, "Qué queda fuera".

## Elecciones (E1 a E16)

Cada una lleva la recomendación del orquestador. La firma de la propuesta las aprueba o las cambia.

### E1 · Un módulo nuevo `liquidacion`

`proptech_core/liquidacion/` (`dominio/` puro, `aplicacion/`, `puertos.py`, `adaptadores/`) importa
`complejos.aplicacion`, `gastos.aplicacion` y `cuenta_corriente.aplicacion`; nadie lo importa a él. El
adaptador real de `es_periodo_emitido` y el candado del período se inyectan a `aprobar_gasto` desde
`proptech_api` (el puerto ya existe), así `gastos` no importa `liquidacion` y no hay ciclo. Rutas en
`proptech_api/liquidaciones.py`.

### E2 · Qué se guarda (todo de sólo agregar, tablas protegidas)

- `liquidacion`: una por emisión (`emision_id` único), con complejo, período, huella, versión de
  configuración usada, porcentaje de fondo, vencimiento (y el original si se corrió, con motivo), quién y
  cuándo.
- `linea_de_liquidacion`: por unidad, el detalle que muestra la expensa: grupo, bloque (ordinaria o
  extraordinaria), categoría con **su nombre al emitir** (R16), importe; y las líneas de fondo, cargo
  particular e interés.
- `composicion_de_grupo`: por grupo, las unidades y el coeficiente efectivo usado (R01, "Historia").
- `alerta_aceptada`: código, detalle, quién y cuándo (R34).
- `saldo_anterior_de_liquidacion`: la foto de `EmisionRegistrada.saldo_anterior` por cuenta.

La preliquidación **no se guarda**: se calcula cada vez (es "sin efectos").

### E3 · La huella: se emite lo revisado

La preliquidación devuelve una huella (SHA-256 de su forma canónica: líneas por unidad, controles
activos, versión de configuración y vencimiento). Emitir exige esa huella; bajo el candado se recalcula y
si no coincide, 409 `preliquidacion_cambio` sin escribir nada. Cubre un gasto aprobado, una nota de
crédito o un pago entre la revisión y la emisión.

### E4 · Una sola forma de calcular

El reparto, el fondo y los cargos son funciones puras de `liquidacion/dominio`. El interés de la
preliquidación sale de la misma función pura que usa `registrar_emision` (`calcular_intereses`) sobre las
mismas lecturas, sin candado; la emisión lo recalcula bajo candado y la huella (E3) detecta cualquier
diferencia. Criterio obligatorio: lo preliquidado es igual, al centavo, a lo emitido.

### E5 · Candado del período

Emitir, anular y aprobar un gasto toman `SELECT ... FOR UPDATE` sobre la fila de `complejo` **antes** que
los candados de cuentas (orden fijo: complejo, después cuentas por `bloquear_cuentas`, E2 del 4b). Así un
gasto no se aprueba a un período mientras se emite, y `es_periodo_emitido` real lo manda al siguiente
(P36, D-141).

### E6 · Los controles del 7 (R34)

| Código | Nivel |
|---|---|
| `saldos_iniciales_sin_validar` (R09) | duro |
| `coeficientes_fuera_de_tolerancia` (R01, por grupo, con la diferencia) | duro |
| `bloque_negativo` (P25 abierta, D-157) | duro |
| `doble_vencimiento_sin_regla` (R26 pendiente, D-157) | duro |
| `gastos_en_revision` (D-075) | bloqueante aceptable |
| `gastos_sin_ia` ("hay N facturas sin cargar") | advertencia |
| `gasto_mensual_obligatorio_faltante` (D-141) | advertencia |

Fuera: factura duplicada (la garantiza `uq_gasto_factura`; un test la deja fija) e ingresos mayores que
los gastos (R38 no existe). Ningún control escribe nada.

### E7 · Aceptar alertas

El pedido de emitir trae la lista de códigos aceptados; tiene que ser exactamente el conjunto de
aceptables activos (ni de más ni de menos), si no, 409. Un duro nunca se acepta (422 si viene en la
lista). Aceptar un bloqueante pide `aceptar_alertas_bloqueantes`; una advertencia no se acepta: sólo se
muestra. Cada aceptación queda en `alerta_aceptada` y en la auditoría.

### E8 · Vencimiento

Por defecto, el `dia_de_vencimiento` de la configuración vigente, en el mes del período. Se puede correr
al emitir con fecha nueva y motivo (1 a 500); queda la original, la nueva, quién, cuándo y el motivo. La
configuración no cambia. No se corre a una fecha anterior al período.

### E9 · Distribuir

Migración: `ck_evento_tipo` admite `'distribuida'`, una por emisión. Un puerto único
`registrar_distribucion(emision_id, origen)` con `origen` en `manual`, `email`, `portal`: idempotente
(el primero gana; el 11 y el 13 lo llaman). La ruta manual responde 409 si ya estaba distribuida o
anulada. Distribuir una anulada se rechaza.

### E10 · Anular

Bajo el candado de E5: sólo `emitida` (ni distribuida ni anulada: 409), con motivo, y 409 si hay una
emisión no anulada de un período posterior (P26, D-157). Llama a `anular_emision` y audita en la misma
transacción. **D8 (D-157)**: un crédito de corrección imputado a una obligación de la emisión anulada
pasa a `retenidos` en `estado.py`: no vuelve como crédito a favor. El pago que vuelve conserva su
`fecha_valor` (P38).

### E11 · Cargo cobrado de menos

Como el ajuste de saldo inicial (D-156): una obligación nueva sin emisión, con `operacion_id`, el
componente que elige el administrador y su vínculo a la obligación de origen; motivo, quién y cuándo en
una tabla propia de sólo agregar. Interés desde el día siguiente a su vencimiento. Permiso
`corregir_movimiento`.

### E12 · PDF (H-015)

En la transacción de emitir se crea una fila `documento_de_expensa` por unidad en `pendiente`; después del
commit se encola. Si Redis no está, la emisión queda confirmada igual y un barrido reencola lo
`pendiente`. Estados `pendiente`, `generado`, `fallido`; una ruta reprocesa. Requiere F2c cerrado (C-25)
antes de registrar la tarea.

### E13 · Links firmados (H-015)

Token HMAC con unidad, documento, variante y vencimiento corto, verificado por la API; el PDF nunca tiene
dirección pública. El inquilino sólo recibe la variante sin extraordinaria (D-106), decidido del lado del
servidor.

### E14 · Lectura

Contador y consejo leen dentro de su alcance, sin escribir. El consejo no ve una liquidación emitida y no
distribuida (P39, D-157).

### E15 · Bordes del cálculo

- **Unidad en $0**: no recibe obligación; su interés se registra igual (D0 del 4c).
- **R40**: no se preliquida ni emite un período si el anterior no está emitido o distribuido (una anulada
  no cuenta); el primero después de la migración arranca desde los saldos confirmados.
- **Fondo**: sobre la ordinaria prorrateada de la unidad, sin cargos ni intereses (R13, R15), repartido de
  modo que la suma dé el total del fondo (R07).
- **Cargos particulares**: líneas propias dentro de la ordinaria; el libro los recibe sumados en
  `ordinaria` (no hay columna propia) y el detalle queda en `linea_de_liquidacion`.

### E16 · Índice de DBA-2

`grupo_unidad (administracion_id, complejo_id, grupo_id)` antes de leer la composición por edificio.

## Riesgos

- **Divergencia preliquidación/emisión**: la cubre E3 y el criterio de igualdad de E4.
- **Candados**: un orden distinto entre emitir y anular produce deadlocks; E5 fija el orden y se prueba con
  dos sesiones.
- **D8 en el estado**: cambiar `retenidos` toca la lectura que usan todos los cambios de plata: la
  aceptación de H-014 corre la regresión del 4b y el 4c.
