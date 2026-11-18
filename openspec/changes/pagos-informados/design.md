# Design

## Context

- **Qué hay hoy en `main`** (`8b12ed8`, después del 7):
  - `cuenta_corriente` (4b, 4c): `registrar_credito(sesion, identidad, cuenta_id, tipo, importe, fecha_valor,
    operacion_id, destino, request_id)` registra un crédito (`pago`, `condonacion`, `ajuste_de_interes`,
    `bonificacion`, `baja_de_deuda`) bajo el candado de la cuenta, con replay por `operacion_id`; imputa con
    R04 (`dominio/imputacion.py`: por período, interés primero) o a un destino fijo que tiene que absorber
    todo (E16). `corregir` hace un contra-asiento (`corrige_a`) que excluye del estado al par entero
    (`dominio/estado.py::_excluidos`): el movimiento corregido deja de contar con todas sus imputaciones.
    Un `ajuste_de_interes` con `enlazado_a` sobre un interés que no cuenta tampoco cuenta (D-085). El interés
    (`dominio/intereses.py`) cobra los días no cubiertos por otro interés con la base de capital de cada día,
    y una imputación baja la base desde el día siguiente a la `fecha_valor` de su crédito; `tramo_de_interes`
    (0034) guarda de cada interés sus tramos con base, tasa, forma y gracia.
  - Vocabulario sembrado en `tipo_de_movimiento` (0023): `pago`, `ajuste_de_interes`, `reversion_de_pago`
    (débito), `reimputacion` (débito y crédito); `enlazado_a` admite otra cuenta de la misma administración.
  - `liquidacion` (7): los controles de R34 (`controles` de la preliquidación, H-012), la huella, los enlaces
    firmados de la expensa (`liquidacion/aplicacion/enlaces.py`, HMAC con `PROPTECH_CLAVE_DE_ENLACES`).
  - `acceso`: `informar_pago` (vecino propietario e inquilino), `confirmar_pago_informado` (SA, AP, AE),
    `revertir_o_reimputar_pago`; un vecino es una `asignacion_rol` con `unidad_id` y `vinculo` (una por
    unidad).
  - `situacion_de_cuenta` y `situacion_del_edificio` (R20, 4c) se derivan del libro.
  - Web: no hay ninguna pantalla de vecino.
- **Fronteras**: sólo se importa entre módulos por `aplicacion`, sin ciclos. `pagos` importa `acceso`,
  `complejos` y `cuenta_corriente`; `liquidacion` importa `pagos` (el control); `pagos` no importa
  `liquidacion`.
- **Decisiones que ya rigen**: D-163 y D-164 (acuerdo del 8), D-017, D-056, D-057, D-070, D-074, D-082 a
  D-086, D-106, D-115, D-122, D-152, D-154, D-157, D-161.

## Goals / Non-Goals

**Goals**
- El vecino informa su pago con el comprobante, con la lectura de la IA como ayuda, y ve su estado.
- El administrador confirma o rechaza; confirmar imputa con la fecha de la transferencia y corrige el
  interés que se cobró de más.
- Revertir y reimputar un pago confirmado sin borrar nada, con el interés bien calculado.
- El comprobante sólo se descarga con un link firmado.

**Non-Goals**: ver `proposal.md`, "Qué queda fuera".

## Elecciones (E1 a E14)

Cada una lleva la recomendación del orquestador. La firma de la propuesta las aprueba.

### E1 · Un módulo nuevo `pagos`

`proptech_core/pagos/` (`dominio/` puro, `aplicacion/`, `puertos.py`, `adaptadores/`). La escritura en el
libro vive en `cuenta_corriente/aplicacion/pagos.py` (registrar el pago con su ajuste, revertir, reimputar),
porque el libro es de `cuenta_corriente`; `pagos` la llama. Rutas en `proptech_api/pagos.py`. La firma HMAC
de los enlaces pasa a `compartido/enlaces.py` con un **tipo** en el token (`expensa` o `comprobante`), y
`liquidacion/aplicacion/enlaces.py` queda como fachada con su contrato de H-015 intacto; un token de un
tipo nunca valida como el otro.

### E2 · Qué se guarda

- `comprobante_de_pago`: los bytes (sólo agregar, protegida, como `pdf_de_expensa`), su SHA-256, el tipo
  (JPEG, PNG o PDF, comprobado por los primeros bytes, no por la extensión), el tamaño (hasta 10 MB), quién
  lo subió, cuándo, y lo que leyó la IA (la propuesta en JSON y el resultado de la lectura).
- `pago_informado`: edificio, comprobante, banco y número de operación (los dos tal como se cargaron y
  normalizados, E3), fecha de la transferencia, monto, CBU de origen (opcional), quién lo informó (vecino o
  personal) y cuándo. Inmutable: sólo agregar.
- `parte_de_pago`: la unidad y el importe de cada parte (una o más; suman el monto). Inmutable.
- `evento_de_pago`: `confirmado`, `rechazado`, `revertido`, `reimputado`, con motivo (obligatorio salvo en
  `confirmado`), quién y cuándo; sólo agregar. **El estado se deriva** del último evento (informado si no hay
  ninguno). Índices únicos parciales: un solo `confirmado` o `rechazado` por pago, un solo `revertido`.
  Así un doble clic o dos pestañas no pueden confirmar dos veces aunque las tablas no admitan `UPDATE`.
- `movimiento_de_pago`: el enlace de cada movimiento del libro con su pago y su papel (`pago`,
  `ajuste_de_interes`, `reversion_de_pago`, `interes_por_reversion`, `reimputacion`), para revertir todo lo
  enlazado (D-082, D-083) sin buscar por motivo.
- `cbu_de_unidad`: CBU, unidad y pago de origen, al confirmar con el CBU conocido (R19). La sugerencia que lo
  usa es del 9.

Todas con RLS por administración, protegidas por el rol de arranque (D-115) y en el catálogo de tablas
protegidas, el ensayo de roles y el barrido de migraciones (L-064, L-083, L-089).

### E3 · El número de operación único (P40, D-163)

Único por **edificio, banco y número** entre los pagos no rechazados (un pago rechazado libera su número
para que el vecino lo vuelva a informar bien). El banco y el número se normalizan antes de comparar: sin
espacios ni guiones ni puntos, en minúscula y sin tildes. Lo garantiza un índice único parcial; la carrera
entre dos pedidos se traduce a 409 `{"detail": "conflicto", "campo": "numero_de_operacion", "motivo":
"repetido"}`.

### E4 · Quién informa y para qué unidades (R10, R11)

- El vecino informa sólo para unidades del edificio donde tiene una asignación de vecino (propietario o
  inquilino). Otra unidad, aunque exista: 404. Varias unidades suyas: una parte por unidad (R11).
- El personal con `confirmar_pago_informado` puede informarlo por el vecino, para cualquier unidad del
  edificio (R11: "o el administrador lo carga por él").
- Validaciones: monto mayor que cero con dos decimales; partes que suman el monto, sin unidades repetidas;
  fecha de la transferencia no futura y no anterior a un año; banco y número no vacíos. Todo 422 con su
  campo.
- Ver: el vecino ve los pagos con alguna parte en sus unidades (propietario e inquilino por igual, como la
  expensa de su unidad); el personal con `confirmar_pago_informado` ve la bandeja del edificio. Ningún otro.

### E5 · La lectura con IA (D-164)

- Flujo en dos pasos: `POST .../pagos/lectura` guarda el comprobante y devuelve la propuesta; `POST
  .../pagos` informa el pago con el `comprobante_id` y los datos que el vecino revisó. Un comprobante se usa
  en un solo pago.
- La lectura es **sincrónica** con un tope (20 s): si la IA falla, tarda o no hay clave configurada, responde
  igual con la propuesta vacía y `lectura: "fallida"` o `"sin_ia"`, y el vecino carga a mano. Nunca 5xx por la
  IA.
- El adaptador real llama a `https://openrouter.ai/api/v1/chat/completions` con el modelo de la
  configuración, la imagen (o el PDF) en base64, una instrucción fija y `response_format` con esquema JSON
  estricto (`banco`, `numero_de_operacion`, `fecha`, `monto`, `cbu_origen`, todos texto o nulo), y
  `provider: {"zdr": true, "data_collection": "deny", "require_parameters": true}`. Nunca manda el nombre de
  la persona, la unidad ni el edificio.
- **Lo que vuelve es dato, no orden**: el dominio valida cada campo (monto con el formato de plata, fecha
  real y no futura, CBU de 22 dígitos, textos acotados) y descarta el que no cumple. Una imagen con texto
  que le da órdenes a la IA sólo puede producir valores que el vecino ve y corrige; la IA no tiene
  herramientas, no confirma nada y no elige la unidad.
- Clave en `PROPTECH_OPENROUTER_API_KEY` y modelo en `PROPTECH_OPENROUTER_MODELO`, en la configuración
  (D-042): sin clave, la lectura responde `sin_ia`. Los tests usan un adaptador falso y, para el real, un
  transporte HTTP falso que deja ver el pedido.

### E6 · Confirmar: R04 a la fecha de la transferencia (R11)

- Bajo el candado de las cuentas de todas las partes (`bloquear_cuentas`, en orden), por cada parte se
  registra un crédito `pago` con `fecha_valor` = fecha de la transferencia y un `operacion_id` derivado del
  pago y la parte (UUID v5), así que repetir la confirmación es un replay y no duplica.
- **Orden de imputación**: el pago se imputa con R04 **a la fecha de la transferencia**: primero a la deuda
  que existía ese día (obligaciones e intereses registrados hasta esa fecha) y lo que sobra, con R04 sobre
  el resto, como lo habría imputado la emisión siguiente; lo que sobra después queda como crédito a favor
  (R05). Así un pago confirmado tarde termina imputado igual que si se hubiera confirmado el día de la
  transferencia.
- El evento `confirmado`, el CBU de origen y la auditoría van en la misma transacción. Confirmar un pago
  rechazado o revertido: 409 `motivo: "estado"`. Confirmar dos veces: 200 con el mismo resultado.
- Rechazar exige motivo (3 a 500 caracteres), no toca el libro y deja el evento `rechazado`; rechazar uno
  confirmado: 409.

### E7 · El ajuste de interés (R11, D-082, D-084, D-085)

- Al confirmar, por cada parte: cada interés que cuenta en la cuenta, **registrado después de la fecha de
  la transferencia**, se recalcula sobre sus mismos tramos (la tasa, la forma y la gracia guardadas en
  `tramo_de_interes`) con la base que habría tenido con el pago imputado como dice E6. Si lo registrado
  supera lo recalculado, la diferencia es un `ajuste_de_interes` con destino fijo ese interés, `enlazado_a`
  ese movimiento de interés (si su emisión se anula, el ajuste deja de contar con él, D-085) y enlazado al
  pago en `movimiento_de_pago`.
- **Los ajustes se registran antes que el pago**, para que R04 no use el pago en un interés que se está
  compensando. La función de la diferencia es pura (`cuenta_corriente/dominio/intereses.py`) y sirve
  igual para E9.
- Un ajuste que no entra en su interés (porque otro crédito ya lo pagó) se registra hasta lo que entra; el
  resto no se registra solo: la confirmación lo devuelve (`ajuste_sin_destino`, con el importe y el
  interés) y queda auditado, para que el administrador lo corrija con R08 (`corregir_movimiento`).
- Un pago confirmado antes de la emisión siguiente no genera ajuste: la emisión ya calcula el interés con
  él adentro.

### E8 · Revertir (R18)

- Sólo un pago confirmado (si no, 409 `motivo: "estado"`), con motivo. Por cada parte vigente, un
  `reversion_de_pago` (débito) con `corrige_a` el movimiento vigente de esa parte (el `pago`, o el
  `reimputacion` crédito si se reimputó): el par deja de contar y la unidad vuelve a deber como si el pago
  no hubiera entrado. Cada `ajuste_de_interes` enlazado se revierte con un contra-asiento (D-083).
- Evento `revertido`, auditoría y todo en una transacción. Después, `situacion_de_cuenta` da la unidad
  como moroso crítico si ahora cumple R20 (D-074): no hay marca que actualizar.

### E9 · El interés de un pago revertido o reimputado (P29, D-163)

Al sacar un pago de una unidad, cada interés que cuenta y que se calculó con ese pago adentro (registrado
después de la fecha de la transferencia) se recalcula sin él sobre sus mismos tramos. La diferencia es un
movimiento nuevo **`interes_por_reversion`** (débito, componente interés, sobre la misma obligación,
`enlazado_a` ese interés): si su emisión se anula, deja de contar con él, igual que el ajuste (D-085). El
interés sigue siendo simple: la base de `_base_del_dia` nunca suma componentes de interés (R03). Es un tipo
nuevo en `tipo_de_movimiento` (migración).

### E10 · Reimputar (R25)

Un pago confirmado, una de sus partes, de la unidad equivocada a otra unidad del mismo edificio, con
motivo. En una sola transacción, con los candados de las dos cuentas en orden: en la equivocada, un
`reimputacion` débito con `corrige_a` el movimiento vigente de la parte, la reversión de sus ajustes y el
interés de E9; en la correcta, un `reimputacion` crédito con la fecha de la transferencia, imputado como en
E6, con su ajuste de E7, y `enlazado_a` el débito. Si falla un paso no queda ninguno (una transacción). La
misma unidad o una de otro edificio: 422 o 404. El pago sigue confirmado y suma el evento `reimputado`.

### E11 · El comprobante con link firmado (D-070)

`POST .../pagos/{id}/comprobante/enlace` devuelve `{url, vence_en}` a 15 minutos para quien puede ver ese
pago (E4); `GET /api/comprobantes/descarga?token=` sin sesión: 200 con los bytes y su tipo, 410 vencido,
403 alterado o de otro tipo. Igual que la expensa, la web lo baja por una ruta de Next (Caddy no publica
`/api/*`).

### E12 · El control "pagos sin confirmar" (R34)

`pagos_sin_confirmar`, **advertencia**, al final de la lista de H-012: cuántos pagos del edificio siguen
informados, con el total. No frena la emisión.

### E13 · Auditoría

Confirmar, rechazar, revertir y reimputar son acciones sensibles (D-016): se auditan en la misma
transacción, con el vocabulario ampliado en la migración.

### E14 · Las pantallas (HU-V4, HU-A6)

- **Vecino**: "Mis pagos" (lista con estado en texto y el motivo del rechazo) e "Informar un pago" (subir,
  ver la propuesta de la IA, revisar y corregir, elegir la unidad o repartir, enviar). Entra al portal por
  el menú según su rol (D-131).
- **Administrador**: "Pagos" del edificio en el menú: la bandeja de informados con confirmar y rechazar, y
  los confirmados con revertir y reimputar, cada acción con su confirmación y motivo; el comprobante por
  link firmado.
- Pasan por la skill **impeccable**, a 320 px sin scroll horizontal y sin errores de axe; la API falsa de
  e2e suma los escenarios.

## Risks / Trade-offs

- **La IA lee mal un comprobante**: el vecino revisa todo y el administrador confirma mirando el
  comprobante; la IA nunca escribe en el libro.
- **Datos de comprobantes a un tercero** (P12): sólo la imagen, con ZDR; la inscripción ante la AAIP frena
  el despliegue con datos reales (D-163).
- **R04 a la fecha de la transferencia** es más complejo que R04 sobre la deuda de hoy, pero es lo único que
  deja igual un pago confirmado tarde y uno confirmado a tiempo (R11). Se prueba al centavo.
- **Lectura sincrónica**: ocupa la petición hasta 20 s; aceptable con el volumen del MVP.

## Migration Plan

`0044` las tablas de `pagos` y el vocabulario de auditoría (H-018 a H-020); el tipo `interes_por_reversion`
con su migración (H-022). Cada una sube sobre una base ya desplegada (L-089) y baja limpia.
