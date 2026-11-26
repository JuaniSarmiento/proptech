# Contrato que asume la aceptación de H-038

Lo que debo y lo que pagué: las lecturas HTTP del vecino para todas sus unidades (change 11 `portal-del-vecino`).
Caja negra por la API real, con la identidad inyectada. Fuente: `HISTORIAS.md` (H-038), D-170 y D-106. Si el
constructor necesita cambiar algo de esto, frena y lo pide. Los nombres, rutas y claves de abajo los fija esta
aceptación; las claves de cada objeto son **exactamente** las listadas (los tests comparan el conjunto).

## Quién es "mi unidad"

Una unidad es mía cuando la persona en sesión tiene una asignación `vecino` sobre esa unidad (`propietario` o
`inquilino`, D-106). Ser personal (super admin, administrador, contador, auxiliar, consejo) **no** da unidades en el
portal: sin asignación `vecino`, `GET /api/mis-unidades` devuelve la lista vacía. La administración sale de la
sesión (R10): una unidad de otra administración no existe para la persona.

**Toda ruta por unidad** (`/api/mis-unidades/{unidad_id}/...`) devuelve `404` con cuerpo exacto
`{"detail": "no encontrado"}` si la unidad no es de la persona: ajena del mismo edificio, de otro edificio, de otra
administración, inexistente, o pedida por personal sin vínculo. Nada distingue "no existe" de "no es tuya".

## `GET /api/mis-unidades`

`200` con un objeto de tres claves: `fecha` (hoy en Mendoza, `AAAA-MM-DD`; la fecha sale de una dependencia
`hoy` en `proptech_api.vecino`, que la aceptación fija en 18/11/2026, L-090), `conjunto` y `unidades`.

Cada elemento de `unidades` tiene exactamente: `unidad_id`, `identificador`, `vinculo` (`propietario` o
`inquilino`), `complejo_id`, `edificio` (el nombre), `total_a_pagar`, `vencimiento`, `deuda_anterior`, `intereses`,
`credito_aplicable` y `credito_retenido`. Los montos son texto Decimal con dos decimales (`"43350.00"`), nunca
número. Orden: por nombre de edificio y, dentro de cada uno, por identificador. Una persona con unidades en dos
edificios (o con dos vínculos distintos) las ve todas juntas.

Qué es cada cifra (las del libro, a la fecha de hoy; no se recalcula nada en la API):

| campo | qué es |
|---|---|
| `total_a_pagar` | `estado_de_cuenta.deuda`: todo lo pendiente (capital e interés, vencido o no), **sin descontar** ningún crédito |
| `vencimiento` | el menor vencimiento entre las obligaciones que cuentan con algo pendiente (`AAAA-MM-DD`); `null` sin deuda |
| `deuda_anterior` | `lecturas.saldo_anterior` de la emisión más reciente no anulada del edificio (D12: la deuda sin esa emisión); `"0.00"` sin emisión |
| `intereses` | `situacion_de_cuenta.interes_vencido` a hoy |
| `credito_aplicable` | `estado_de_cuenta.credito_a_favor_aplicable` |
| `credito_retenido` | `estado_de_cuenta.credito_a_favor_retenido` (D-170.5: nunca descuenta la deuda) |

Una unidad sin cuenta en el libro (nada emitido) aparece con todo en `"0.00"` y `vencimiento: null`.

`conjunto` tiene `total_a_pagar`, `intereses`, `credito_aplicable` y `credito_retenido`: la suma, hecha por la API, de
esos campos sobre todas las unidades de la lista (el frontend no calcula montos, R05).

**Inquilino (D-170.2)**: para una unidad en la que la persona es `inquilino`, `total_a_pagar` es la deuda **sin el
componente `extraordinaria`** (interés, ordinaria y fondo de reserva: lo mismo que la variante `sin_extraordinaria`
del PDF del 7), y `vencimiento` mira sólo esos componentes. En ninguna clave ni valor de la respuesta aparece un
monto extraordinario. `deuda_anterior`, `intereses` y los créditos se calculan igual (en estos ejemplos no hay
extraordinaria en ellos).

## `GET /api/mis-unidades/{unidad_id}/pagos`

`200` con una lista de los pagos **confirmados** de esa unidad (N03: nunca los informados, rechazados o revertidos; el
estado sale de los eventos, como en el 8). Cada elemento: `pago_id`, `fecha_de_transferencia` (`AAAA-MM-DD`),
`importe`, `banco`, `numero_de_operacion`. Del más nuevo al más viejo por fecha de transferencia. Es una lista vacía
si no hay ninguno.

`importe` es lo que ese pago cargó **a esa unidad** (su `parte_de_pago`), no el monto total del pago (un pago de
dos unidades aparece en cada una con su parte). Lo ven los dos vínculos de la unidad, con esta diferencia para el
**inquilino (D-170.2)**: su `importe` es sólo lo imputado a interés, ordinaria y fondo de reserva, y un pago que fue
entero a la extraordinaria no aparece en su lista. (Ejemplo: Beto paga `"40000.00"` y la 1B debe `"33350.00"` sin
extraordinaria: ve `"33350.00"` de ese pago; el pago de `"8350.00"` de Carla, imputado todo a la extraordinaria, no
figura en su lista.) El propietario ve el importe entero de cada pago.

## `GET /api/mis-unidades/{unidad_id}/documentos`

`200` con la lista de los PDFs de esa unidad, de las liquidaciones **emitidas y no anuladas**, sólo los documentos en
estado `generado` (un `pendiente` o `fallido` no se ofrece), y sólo **la variante del vínculo**: el propietario la
`completa`, el inquilino la `sin_extraordinaria` (D-106, `puede_pedir_el_enlace` del 7). Un período sin emitir (por
ejemplo un gasto aprobado de octubre sin liquidación) no aparece. Cada elemento: `documento_id`, `liquidacion_id`,
`complejo_id`, `periodo` (`AAAA-MM-01`), `variante`, `url` y `vence_en`. Del período más nuevo al más viejo.

`url` es el enlace firmado del 7 (`/api/documentos/descarga?token=...`, vence a los 15 minutos, HMAC con
`PROPTECH_CLAVE_DE_ENLACES`), firmado **al listar** con la misma función que usa
`POST /api/complejos/{id}/documentos/{documento_id}/enlace` (que sigue existiendo, sin cambios); `vence_en` es su
vencimiento en ISO. `GET url` baja el PDF (`application/pdf`, empieza con `%PDF`). Sin `PROPTECH_CLAVE_DE_ENLACES`
configurada: `503` `{"detail": "enlaces_no_configurados"}`, como en el 7.

## `GET /api/mis-unidades/{unidad_id}/cargos-particulares/{cargo_id}` (cierra D3 del 6)

`200` con el cargo particular **aprobado** de esa unidad, de sólo lectura, con las mismas claves y valores que
devuelve hoy `GET /api/cargos-particulares/{cargo_id}` al administrador: `id`, `complejo_id`, `unidad_id`,
`concepto`, `importe`, `periodo`, `motivo`, `estado`. `404` (cuerpo exacto de arriba) si el cargo no existe, es de
otra unidad que la de la ruta (aunque sea otra unidad también mía), o no está aprobado (`borrador`). Lo leen los dos
vínculos. La ruta `GET /api/cargos-particulares/{cargo_id}` del 6 **no cambia** (sigue pidiendo
`ver_configuracion_del_edificio`).

## Lo que no hace

Ninguna de estas rutas escribe nada (N04): ni libro, ni auditoría, ni distribución, ni firma persistida. No hay
rutas de escritura nuevas. La distribución al abrir una liquidación (D-170.4), la comparación con el mes anterior y
el detalle por categoría son de H-039; las pantallas y la app instalable, de H-040.
