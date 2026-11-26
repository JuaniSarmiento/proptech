# Contrato que asume la aceptación de H-033

Caja negra por la API real (H-030 y H-031 para sembrar el traslado) y el libro (`estado_de_cuenta`, tablas `movimiento`
e `imputacion`), con la identidad inyectada y `proptech_api.morosidad.hoy` fijo en el 15/12/2026 (L-090). Si el
constructor necesita cambiar algo de esto, frena y lo pide.

Fuente: `HISTORIAS.md` (H-033), D-168.2c y R32. Las tres rutas son nuevas, bajo `/api/complejos/{c}/cuentas-de-vendedores`.

## Orden de los chequeos (D7)

Edificio que no existe o no alcanza: **404** `{"detail": "no encontrado"}`. Permiso: **403** con
`detail.permiso_faltante` (`ver_morosidad` en las dos lecturas, `confirmar_pago_informado` en el cobro). Cuenta que no es
una cuenta de **persona** de ese edificio de esa administración (de unidad, de otro edificio, de otra administración,
inexistente o con un id que no es uuid): **404**. Después, el cuerpo: **422**.

Matriz real de los dos permisos (`acceso/dominio/permisos.py`): `ver_morosidad` lo tienen super admin, administrador,
contador, auxiliar y consejo (los de alcance edificio, sólo en su edificio) y no los vecinos; `confirmar_pago_informado`
sólo super admin y administrador (principal o de su edificio). Por eso contador, auxiliar y consejo **leen y no cobran**
(403 en el cobro) y los vecinos no hacen nada (403 en las tres).

## `GET .../cuentas-de-vendedores` (C01)

**200** `{"cuentas": [ ... ]}`. Una fila por cuenta de persona del edificio, **también las que quedaron en cero**; nunca
las cuentas de unidad. Orden: `deuda` de mayor a menor. Cada fila, exactamente estas claves:

- `cuenta_id` (uuid) · `persona`: `{"id", "nombre"}` · `deuda`: texto con dos decimales (la de `estado_de_cuenta`).
- `unidades`: `[{"id", "identificador"}]`, las unidades de los cambios de titular que le trasladaron deuda, sin repetir y
  por identificador. Una persona con dos unidades vendidas tiene una sola cuenta con las dos (`uq_cuenta_persona`).

Sin cuentas de persona: `{"cuentas": []}`.

## `GET .../cuentas-de-vendedores/{cuenta_id}` (C02)

**200** con las claves de la fila de la lista más:

- `periodos`: por período (`"AAAA-MM-01"`, ascendente, sin repetir) y componente (`interes`, `ordinaria`,
  `fondo_de_reserva`, `extraordinaria`, en ese orden), sólo los componentes que alguna vez se le trasladaron:
  `{"periodo", "componentes": {componente: {"debe", "cobrado", "pendiente"}}}`, los tres en texto con dos decimales:
  `debe` lo trasladado, `cobrado` lo imputado por los cobros, `pendiente = debe - cobrado` (es el residual del libro).
  La suma de los `pendiente` es `deuda`.
- `movimientos`: todos los de la cuenta en el orden del libro (`registrado_en`, `id`), cada uno con exactamente
  `{"id", "tipo", "sentido", "importe", "fecha"}`. `tipo` y `sentido` son los del libro (`traslado`/`debito` los de H-031,
  `pago`/`credito` los cobros); `importe` texto con dos decimales; `fecha` es `fecha_valor` en ISO.

## `POST .../cuentas-de-vendedores/{cuenta_id}/cobros` (C03 a C05)

Cuerpo `{"importe": "1000.00", "fecha": "2026-12-10"}`, **ni más ni menos claves**. **201** con el mismo documento que el
`GET` del detalle, ya con el cobro. Registra un `pago` del libro (crédito, con `operacion_id` no nulo y `registrado_por`
la persona de la identidad) sobre la cuenta de persona, **imputado con R04** (lo más viejo primero y, dentro de un
período, el interés primero) a la **fecha de la transferencia**; todo en una transacción.

- `importe`: **texto** con a lo sumo dos decimales y mayor que cero (`"0"`, `"0.00"`, negativo, `"10.001"`, `"1e2"`,
  vacío, no numérico, número JSON, `null` y booleano dan 422).
- `fecha`: texto `AAAA-MM-DD`, válida y **no posterior a hoy** (hoy vale; una anterior también). Número JSON, `null`,
  otro formato, fecha inexistente o vacía dan 422.
- **Un cobro mayor que la deuda da 422** sin cambiar nada (no hay crédito a favor ni expensas futuras donde aplicarlo);
  uno igual la deja en cero, y a una cuenta en cero cualquier cobro le da 422.
- Un 422 (o 403/404) no deja movimientos, imputaciones, auditoría ni nada.

## Auditoría (C05)

Acción `registrar_cobro_de_vendedor`: una fila por cobro, `entidad = "cuenta"`, `entidad_id = cuenta_id`, `persona_id` la
del actor, `detalle` exactamente `{"cuenta_id": "<uuid>", "importe": "1000.00", "fecha": "2026-12-10"}`. Leer no se audita.

## Lo que el cobro no toca (N03)

Ninguna cuenta de unidad (ni sus movimientos, imputaciones y obligaciones), ninguna fila de `pago_informado` ni la
respuesta de `GET .../pagos` (la bandeja), ni `GET .../morosidad` (el vendedor no aparece, D-168.2b). Emitir el período
siguiente después de un cobro no escribe nada en la cuenta del vendedor: sin interés, sin cambio de deuda (D-168.2a).

## Decisiones de forma de esta aceptación (las toma el orquestador; se cambian pidiéndolo)

- **D1.** La lista y el detalle son lecturas, no se auditan; contador, auxiliar y consejo leen (matriz de `ver_morosidad`).
- **D2.** El cobro responde con el detalle y no con un recibo aparte, así la pantalla de H-034 se actualiza con una sola
  llamada.
- **D3.** Sin idempotencia por pedido repetido: dos POST iguales son dos cobros (la pantalla confirma antes).
- **D4.** La acción de auditoría y su detalle entran al vocabulario (`test_vocabulario_configuracion`, `test_permisos`,
  `test_rutas_protegidas`): los estructurales de `aceptar.py` los cubren, la ficha y `03_actores_y_roles.md` lo documentan (K01).
