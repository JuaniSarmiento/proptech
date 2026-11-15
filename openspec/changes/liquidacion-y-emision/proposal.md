# Proposal

> Acuerdo previo: D-157 (Juani, 15/11/2026, "vamos con tus recomendaciones"): D8, P26, P38 y P39 decididas;
> P27 y P28 pasan al 8; R40 adentro; doble vencimiento y bloque negativo frenan con un control duro.

## Why

Es el último paso del camino crítico a M1 (`4c → 5 → 7`): convertir los gastos aprobados del mes en la
expensa de cada unidad, revisable antes de emitir. El libro (4b, 4c) ya sabe registrar una emisión con su
interés y su foto de saldo anterior, y anularla; el 6 ya expone los gastos aprobados del período. Falta el
módulo que reparte, controla, emite, distribuye, anula y arma el comprobante. Sin el 7 no hay liquidación,
y sin liquidación no se puede probar M1 ni arrancar el 8 (pagos).

## Gobernanza

**CRITICAL** (liquidación y cuenta corriente, D-094, D-111): un error de reparto o de emisión le cobra de
más o de menos a todas las unidades del edificio y el libro sólo agrega (R08). Requiere la aprobación
escrita y fechada de Juani, Alberto o Emiliano en `## Aprobación` antes de escribir código.

## What Changes

- **Preliquidación (H-011)**: un módulo nuevo `liquidacion` (E1) que, sin escribir nada, calcula lo de cada
  unidad: reparto por grupo (R01, R07) de los gastos aprobados netos de notas de crédito, fondo de reserva
  sobre la ordinaria prorrateada (R15), cargos particulares aprobados (R14) e interés por mora (R03) con la
  misma función que usa la emisión (E4), agrupado por ordinaria y extraordinaria y por categoría (R13,
  R16). Devuelve su huella (E3). Los períodos van en orden (R40). Pantalla de la preliquidación.
- **Controles y alertas (H-012)**: la lista de R34 sobre la preliquidación, con bloqueantes, duros y
  advertencias (E6), y la aceptación explícita de las alertas aceptables, registrada (E7).
- **Emitir (H-013)**: emite la preliquidación revisada si su huella no cambió (E3), con el candado que
  comparte con aprobar un gasto (E5), en una sola transacción: congela lo usado (E2), llama a
  `registrar_emision`, guarda la foto del saldo anterior, permite correr el vencimiento con motivo (E8) y
  conecta el adaptador real de `es_periodo_emitido` (D8 del 6). Audita.
- **Distribuir y anular (H-014)**: distribuir a mano por un puerto único (E9); anular sólo emitida y no
  distribuida, con motivo, sólo si el siguiente período no está emitido (P26) y con el crédito de
  corrección retenido (D8, E10); el cargo cobrado de menos (E11). Audita.
- **PDF y links firmados (H-015)**: la plantilla de la expensa con el código corto de la unidad (R19), el
  encolado en el worker con su estado y su reproceso (E12), y los links firmados con vencimiento (D-070,
  E13). Espera la normativa de Mendoza (D-060) y F2c (C-25).
- **Permisos**: usa las acciones de D-106 que ya existen (`cargar_gastos_y_preparar_liquidacion`,
  `emitir_y_distribuir_liquidacion`, `anular_liquidacion`, `aceptar_alertas_*`). **Migraciones** desde
  `0040`.

## Qué queda fuera

- El portal del vecino (11) y los avisos por email (13); la bonificación por pronto pago (R37, P27, P28:
  van al 8); el cargo recurrente del reglamento (R14 propuesta), el vencimiento en día inhábil (R35) y los
  ingresos del consorcio (R38); cobrar el recargo del doble vencimiento (R26, Alberto); los controles de
  pagos, extracto y contactos (8, 9, 13); las pantallas de gastos (6c); el test de M1 con los datos del
  piloto (P1: se corre con el edificio de ejemplo y M1 queda pendiente).

## Capabilities

### New Capabilities

- `preliquidacion`: el cálculo por unidad sin efectos, su huella y su pantalla.
- `controles-antes-de-emitir`: la lista de R34 y la aceptación registrada de alertas.
- `emision-de-liquidacion`: emitir lo revisado, congelar, correr el vencimiento, auditar.
- `ciclo-de-la-liquidacion`: distribuir, anular y el cargo cobrado de menos.
- `comprobante-de-expensa`: PDF, encolado y links firmados.

### Modified Capabilities

- `libro-de-movimientos`: el crédito de corrección de una emisión anulada queda retenido (D8, D-157); el
  evento `distribuida`.
- `gastos-y-cargos`: aprobar un gasto toma el candado del período y usa el adaptador real de
  `es_periodo_emitido`.

## Impact

- **Código**: `backend/src/proptech_core/liquidacion/` (nuevo), `cuenta_corriente/dominio/estado.py`
  (retenidos de D8), `cuenta_corriente/aplicacion/emisiones.py` (distribuida), `gastos/aplicacion/
  gastos.py` (candado y adaptador), `proptech_api/liquidaciones.py`, `proptech_worker/tareas.py` (H-015),
  `web/src/app/edificios/[id]/liquidaciones/`.
- **Base**: migraciones desde `0040`; índice de DBA-2 sobre `grupo_unidad`.
- **Tests existentes que cambian** (L-064): `_DUENO_DE_TABLA`, `_RUTAS_CUBIERTAS`, vocabulario de
  auditoría, tablas protegidas, ensayo de roles, fronteras de módulos y los tests que bajan migraciones.
- **Consumidores**: 8 (pagos imputan a estas obligaciones), 10a, 11, 12, 13, 14 y el test de M1.

## Lecciones que aplican (`knowledge-base/15_lecciones.md`)

- **L-064, L-083**: tablas protegidas nuevas, barrido local de migraciones y ensayo de roles.
- **L-082**: la aceptación prueba su migración, no "la última".
- **L-084**: barridos de rutas y mypy entero antes del PR.
- **L-019, L-035, L-049, L-061**: RED por aserción, commiteado antes del código, mutante por aserción de
  plata o seguridad.
- **L-076**: números de D y L únicos al archivar.

## Knowledge Base Impact

| Documento | Acción | Qué |
|---|---|---|
| `knowledge-base/05_reglas_de_negocio.md` | REWRITE | R01, R13, R15, R16 (dónde vive el reparto), R17 (distribuida, P26, D8), R34 (controles del 7, bloque negativo, doble vencimiento), R40 (vigente) |
| `knowledge-base/04_modelo_de_datos.md` | REWRITE | las tablas de `liquidacion` |
| `knowledge-base/06_funcionalidades.md` | REWRITE | HU-A4 y HU-A5 con lo construido |
| `knowledge-base/07_flujos_principales.md` | REWRITE | el flujo de liquidar y emitir |
| `knowledge-base/08_arquitectura_propuesta.md` | REWRITE | módulo `liquidacion`, links firmados |
| `knowledge-base/09_decisiones_y_supuestos.md` | APPEND | D-157 (hecha); las elecciones firmadas |
| `knowledge-base/10_preguntas_abiertas.md` | REWRITE | P26, P38, P39 resueltas (D-157); P27, P28 al 8 |
| `knowledge-base/11_glosario.md` | REWRITE | preliquidación, huella, distribuir, anular |
| `knowledge-base/12_fichas_de_changes.md` | REWRITE | ficha 7 cerrada, deuda del cierre; ficha 8 con P27 y P28 |
| `knowledge-base/15_lecciones.md` | APPEND | lo que enseñe |
| `CHANGES.md` | REWRITE | estado de C-10 |

## Aprobación

Gobernanza CRITICAL (D-094, D-111). La completa, a mano, Juani, Alberto o Emiliano, con fecha y alcance.
Ningún agente la escribe.

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| | | |
