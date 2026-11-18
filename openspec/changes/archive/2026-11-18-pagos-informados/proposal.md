# Proposal

> Acuerdo previo: D-163 (Juani, 18/11/2026, "dale sisi"): P12 no frena la construcción, P40 con el banco,
> P29 desde el vencimiento original, R37 con P27 y P28 al 6b, R25 adentro. D-164: OpenRouter lee los
> comprobantes detrás de un puerto.

## Why

El 7 dejó emitida la expensa de cada unidad; falta cobrarla. Hoy el libro sabe registrar un pago
(`registrar_credito` con tipo `pago`, R04 y R05), pero nadie puede informarlo ni confirmarlo: no hay módulo
`pagos`, ni comprobante, ni bandeja, ni pantalla de vecino. Sin el 8 no se puede seguir el camino crítico a
M2 (cobra): el extracto (9), la morosidad (10a) y los avisos (13) dependen de pagos confirmados.

## Gobernanza

**CRITICAL** (cobros y cuenta corriente, D-094, D-111): confirmar, revertir o reimputar un pago escribe en
el libro, que sólo agrega (R08); un error de fecha, de unidad o de ajuste de interés le cobra de más o de
menos a un vecino real. Requiere la aprobación escrita y fechada de Juani, Alberto o Emiliano en
`## Aprobación` antes de escribir código.

## What Changes

- **Informar un pago (H-018)**: un módulo nuevo `pagos`. El vecino (propietario o inquilino) sube el
  comprobante y lo informa con banco, número de operación, fecha de la transferencia y monto, para una de
  sus unidades o repartido entre ellas; el administrador puede informarlo por él. El número de operación es
  único por edificio y banco (P40, D-163). Informar no cambia la deuda (R11).
- **Lectura con IA (H-019)**: un puerto de lectura con el adaptador de OpenRouter (D-164) que precarga
  banco, número, fecha, monto y CBU de origen; el vecino revisa y confirma. Si la IA falla, carga a mano.
  Lo que devuelve la IA es una propuesta validada, nunca una orden.
- **Confirmar y rechazar (H-020)**: la bandeja del administrador. Confirmar imputa cada parte con R04 a la
  fecha de la transferencia (R11), deja el excedente como crédito a favor (R05) y guarda el CBU de origen
  (R19). Rechazar lleva motivo y no toca el libro. Auditado.
- **Ajuste de interés (H-021)**: si una emisión ya cobró interés por días posteriores a la transferencia,
  confirmar registra el ajuste exacto, enlazado al pago y al interés que compensa (R11, D-082, D-084,
  D-085).
- **Revertir (H-022)**: un pago confirmado que el banco devuelve pasa a revertido con un contra-movimiento
  `reversion_de_pago` y motivo; sus ajustes se revierten con él (R18, D-083) y el interés de los días que
  ya se habían cobrado con el pago adentro se cobra por la diferencia (P29, D-163). Auditado.
- **Reimputar (H-023)**: un pago confirmado en la unidad equivocada pasa a la correcta en una sola
  transacción, con los dos movimientos `reimputacion` enlazados (R25, vigente por D-163). Auditado.
- **Comprobantes y control (H-024)**: el comprobante se descarga sólo con un link firmado que vence (D-070);
  el control "pagos sin confirmar" entra a la lista de R34 como advertencia.
- **Pantallas (H-025)**: la del vecino para informar y ver el estado de sus pagos (HU-V4) y la bandeja del
  administrador (HU-A6), con la skill impeccable.
- **Permisos**: usa las acciones que ya existen (`informar_pago`, `confirmar_pago_informado`,
  `revertir_o_reimputar_pago`). **Migraciones** desde `0044`.

## Qué queda fuera

- La bonificación por pronto pago (R37), P27, P28 y la reversión de la bonificación retenida (E16 del 4b):
  pasan al 6b (D-163).
- El cruce con el extracto y la sugerencia por CBU o código de unidad (9, R19); un CBU que paga varias
  unidades (P30, 9).
- El resto del portal del vecino (11): saldo, expensas, descargas de PDF; los avisos por email (13).
- La inscripción ante la AAIP (P12): frena el despliegue con datos reales, no la construcción (D-163).

## Capabilities

### New Capabilities

- `pago-informado`: informar un pago con su comprobante, el número único y el reparto entre unidades.
- `lectura-de-comprobantes`: el puerto de lectura y el adaptador de OpenRouter.
- `confirmacion-de-pagos`: la bandeja, confirmar con su imputación y su ajuste de interés, rechazar.
- `reversion-y-reimputacion`: revertir y reimputar un pago confirmado.
- `comprobante-de-pago`: el comprobante guardado y su descarga con link firmado.

### Modified Capabilities

- `controles-antes-de-emitir`: el control `pagos_sin_confirmar`, advertencia.

El tipo de movimiento nuevo `interes_por_reversion` queda especificado en `reversion-y-reimputacion`.

## Impact

- **Código**: `backend/src/proptech_core/pagos/` (nuevo), `cuenta_corriente/dominio/intereses.py` (la
  diferencia de interés), `cuenta_corriente/aplicacion/` (registrar un pago con su ajuste, revertir,
  reimputar), `compartido/` (la firma de enlaces compartida), `liquidacion/` (el control nuevo),
  `proptech_api/pagos.py`, `web/src/app/` (vecino y bandeja).
- **Base**: migraciones desde `0044`; tablas nuevas de `pagos`, el tipo de movimiento nuevo y el vocabulario
  de auditoría.
- **Configuración**: `PROPTECH_OPENROUTER_API_KEY` y el modelo (D-164); la línea en `infra/.env.example` la
  agrega Juani (una regla de permisos impide que la edite un agente).
- **Tests existentes que cambian** (L-064): `_DUENO_DE_TABLA`, `_RUTAS_CUBIERTAS`, vocabulario de
  auditoría, tablas protegidas, ensayo de roles, fronteras de módulos, controles de R34 de H-012.
- **Consumidores**: 6b (bonificación), 9 (extracto), 10a (morosidad), 11 (portal), 13 (avisos).

## Lecciones que aplican (`knowledge-base/15_lecciones.md`)

- **L-064, L-083, L-088, L-089**: tablas protegidas nuevas, barrido de migraciones, préstamo de propiedad,
  migración sobre una base ya desplegada.
- **L-082, L-086**: la aceptación prueba su migración; el ciclo de migración en su propio módulo.
- **L-085, L-087**: locators exactos y esperar la escritura en los e2e.
- **L-090**: fechas fijas en los tests.
- **L-019, L-035, L-049, L-061**: RED por aserción, mutante por aserción de plata o seguridad.

## Knowledge Base Impact

| Documento | Acción | Qué |
|---|---|---|
| `knowledge-base/05_reglas_de_negocio.md` | REWRITE | R11, R18, R19 (dónde vive), R25 (vigente), R34 (pagos sin confirmar), R37 (al 6b) |
| `knowledge-base/04_modelo_de_datos.md` | REWRITE | las tablas de `pagos` |
| `knowledge-base/06_funcionalidades.md` | REWRITE | HU-A6 y HU-V4 con lo construido |
| `knowledge-base/07_flujos_principales.md` | REWRITE | el flujo de informar y confirmar |
| `knowledge-base/08_arquitectura_propuesta.md` | REWRITE | módulo `pagos`, OpenRouter, variables nuevas |
| `knowledge-base/09_decisiones_y_supuestos.md` | APPEND | D-163 y D-164 (hechas); las que salgan al construir |
| `knowledge-base/10_preguntas_abiertas.md` | REWRITE | P29 y P40 resueltas (D-163); P27 y P28 al 6b; P12 bloquea el despliegue |
| `knowledge-base/11_glosario.md` | REWRITE | pago informado, comprobante, reimputación, ajuste de interés |
| `knowledge-base/12_fichas_de_changes.md` | REWRITE | ficha 8 cerrada con su deuda; ficha 6b con R37, P27, P28 |
| `knowledge-base/15_lecciones.md` | APPEND | lo que enseñe |
| `CHANGES.md` | REWRITE | estado de C-11 |

## Aprobación

Gobernanza CRITICAL (D-094, D-111). La completa, a mano, Juani, Alberto o Emiliano, con fecha y alcance.
Ningún agente la escribe.

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| Juani Sarmiento | 18/11/2026 | Por adelantado (en el chat: "dale sisi, te podes hacer cargo del change, yo te apruebo ahora"): la propuesta completa del 8 y sus elecciones de `design.md` con la recomendación del orquestador, sobre el acuerdo D-163 y D-164, partida en H-018 a H-025 sin rompedor (D-152); los criterios los escribe el orquestador bajo esta firma y lo que no me cierre en la demo vuelve a En proceso |
