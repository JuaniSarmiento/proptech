# Proposal

## Why

El libro del 4b guarda la deuda pero todavía no la hace crecer ni la puede recibir desde afuera: no hay
interés por mora (R03), no hay forma de cargar la deuda que un edificio trae al migrar (R09) y no hay
manera de decir qué unidad es morosa crítica (R20) ni de frenar la cobranza de saldos chicos (R30). El
7 (liquidación) necesita el interés al emitir y el 5 (importación) necesita el caso de uso de saldo
inicial; sin el 4c, el camino crítico a M1 (`4b → 4c → 5 → 7`) queda parado. Además el 4c es el primer
consumidor real de `registrar_emision` y de la anulación con intereses, así que hereda tres deudas de
tests débiles (RF-01, RF-02, RB-6, D-130, D-138) que hay que cerrar antes de confiar en ese camino.

## Gobernanza

**CRITICAL** (cuenta corriente y cobranza, D-094, D-111; dominio de plata de las reglas duras). El
riesgo no está en el tamaño del diff: un error de interés o de saldo inicial cobra de más o de menos a
vecinos reales y no se puede borrar del libro (R08). Requiere la aprobación escrita y fechada de Juani,
Alberto o Emiliano en `## Aprobación` antes de escribir código. Según L-048, el apply de las tareas
CRITICAL no se despacha a un constructor genérico que no puede verificar la firma: va a Codex o a un
fork del orquestador con la conversación de la persona que firmó.

## What Changes

- **Interés por mora al emitir (R03, D-109.5, D-113, D-143)**: `registrar_emision` registra, en la
  misma transacción y bajo los candados de todas las cuentas de unidad del edificio, un débito de
  interés por obligación vencida con su corte (fin del mes anterior al período que se emite), interés
  simple sobre el capital impago día por día, con días de gracia, "proporcional por día" o "mes entero",
  y la configuración vigente al corte. "Mes entero" cuenta meses calendario: una fracción de mes cobra
  el mes (decisión de Juani del 30/10/2026, E3, E13). Cada corte cobra los días que ningún interés que
  cuenta cubre, por intervalos y no por el último día cubierto, así no hay huecos ni doble cobro al
  migrar, al cambiar de forma ni al contra-asentar un interés viejo (E17). Cada débito guarda su
  detalle por tramo (días, tasa, base, versión de configuración) en una tabla nueva de sólo agregar.
  **Cambia el contrato del 4b**: `EmisionRegistrada` suma los intereses registrados por cuenta y el saldo
  anterior de todas las **cuentas alcanzadas** (con obligación o sólo con interés); el replay devuelve
  los mismos intereses y un saldo anterior recalculado (E15); `anular_emision` bloquea también las cuentas
  que sólo recibieron interés (PR-02); una emisión sin configuración vigente al corte, con deuda que la
  necesita, se rechaza con conflicto, y un edificio invisible sigue siendo no encontrado.
- **Re-emisión después de anular** (contradicción encontrada, E1): el único `uq_mov_interes
  (obligacion_id, corte)` de `0023` impide volver a registrar el interés del mismo corte cuando la
  emisión que lo registró se anula. El plan propone que esos días pasen al corte siguiente, sin préstamo
  D-115.3 y sin tocar `0023`, cobrados con la configuración de ese corte (el importe puede diferir del
  anulado); la elección queda para la firma.
- **Saldo inicial (R09, D-068, D-080, D-082, D-083)**: caso de uso de aplicación que llama el 5 al
  confirmar la importación: una sola carga por edificio, sólo con el estado de migración `pendiente`,
  con detalle por período o total único, que recibe las filas del archivo y agrupa las de un mismo
  período en una obligación (E16), interés acumulado que entra tal cual y no genera interés, crédito
  inicial, y el archivo, cada fila y el motivo de origen guardados, más una firma del pedido para que
  repetirlo con otros datos, aunque sumen lo mismo, se rechace (PR-11). El interés de R03 corre desde la
  fecha de migración, también con "mes entero" (E13, con la fracción del mes de la migración en E18).
- **Situación de cobranza (R20, R30, D-058, D-074, D-109.4, D-143)**: función pura sobre el libro que,
  para una cuenta o un edificio y una fecha de clasificación, devuelve total vencido, liquidaciones
  vencidas con capital, si está bajo el umbral, si es "deuda de intereses" y si es moroso crítico. La
  fecha decide qué está vencido y qué configuración rige; el saldo es el del libro al leer, no una
  historia (E14). La usan 8, 10a y 10b.
- **Deuda heredada**: RF-01 (una sola foto que cubre todas las cuentas al publicar el saldo anterior,
  con un mutante que hoy sobrevive), RF-02 (forma contra-asiento del test de anulación bajo una
  corrección) y RB-6 (`redondear_al_centavo` con valores enormes da `MontoInvalido`).
- **Migración `0034`**: tres tablas nuevas de sólo agregar con RLS forzada (`tramo_de_interes`,
  `carga_de_saldo_inicial`, `origen_de_saldo_inicial`), declaradas en `TABLAS_DE_SOLO_AGREGAR`. No
  altera ninguna tabla existente.

## Qué queda fuera

- La emisión completa, su preliquidación, la distribución y la auditoría de emitir/anular (7); D8
  sigue bloqueando el 7.
- La importación del Excel, el borrador, la comparación unidad por unidad, la aceptación de
  diferencias, el cambio de estado a `confirmada` y la auditoría de la carga (5).
- Pagos, ajuste de interés de R11 y reversión de R18 (8); avisos de mora (10a, 13); exclusión por
  gestión judicial (10b); certificado de libre deuda (R21).
- Interés y morosidad de las cuentas de persona (4d, P-2 abierta).
- Rutas de API y pantallas: el 4c no expone ninguna ruta nueva.
- R26 (recargo de segundo vencimiento), R35, R36, R39: pendientes o propuestas; el interés corre desde
  el vencimiento guardado en la obligación aunque el edificio tenga doble vencimiento (P59).
- Recalcular un interés ya registrado: el libro sólo agrega (R08).

## Preguntas abiertas de las que depende, y de las que no

- **Bloquean la firma, no el plan** (detalle en `design.md`, "Elecciones a firmar", E1 a E19): las que
  piden una elección real son E1 (re-emisión y único de interés), E2 (qué corte usa cada emisión), E3.1
  (divisor 30 del proporcional), E7 (período con sólo interés en el caso mixto), E11 (período migrado con
  sólo interés), E14 (qué significa "a una fecha"), E15 (saldo anterior del replay), E16 (varias filas
  del Excel en un período y replay por firma), E17 (cobertura por intervalos), E18 (fracción del mes de
  la migración con "mes entero") y E19 (días de un corte con tasa 0). E6 no es una elección: ratifica que
  el 4c cumple D-143 ("$500 o más"); E3.2 y E13 ratifican la decisión de Juani del 30/10/2026 (meses
  calendario en "mes entero").
- **No bloquea el 4c pero sí el 5**: PA-1, cómo se corrige un saldo inicial cargado de menos después de
  confirmar, si R08 no admite débito libre. El 4c no declara cumplida esa parte de R09.
- **No bloquean**: P57 a P60 de Alberto (antes del piloto, D-109.6, D-143). P58 (corte del interés en
  su Excel) y P59 (doble vencimiento) quedan como supuestos nombrados; P60 sigue siendo el orden
  provisorio del 4b. P42 (contador de Mendoza) también es antes del piloto.

## Capabilities

### New Capabilities

- `intereses-por-mora`: cálculo y registro del interés simple de R03 al emitir, su detalle por tramo,
  el corte, la configuración que se usa y la re-emisión.
- `saldo-inicial`: carga única de la deuda previa de un edificio (R09) con su origen, y cómo corre el
  interés desde la migración.
- `situacion-de-cobranza`: moroso crítico (R20), deuda de intereses (D-109.4) y umbral de saldos
  chicos (R30), derivados del libro a una fecha.

### Modified Capabilities

- `libro-de-movimientos`: tres requisitos nuevos que cierran deuda del 4b y extienden su garantía a las
  cuentas que la emisión sólo toca con interés: el saldo anterior publicado sale de una sola lectura de
  todas las cuentas alcanzadas (RF-01), la anulación bloquea todas las cuentas alcanzadas (PR-02) y
  espera también a un contra-asiento en curso (RF-02).
- `reparto-de-montos`: el redondeo de un monto suelto rechaza con `MontoInvalido` un valor que no
  entra en la precisión, en vez de dejar escapar `InvalidOperation` (RB-6).

## Impact

- **Código**: `backend/src/proptech_core/cuenta_corriente/` (`dominio/intereses.py`,
  `dominio/cobranza.py`, `dominio/estado.py`, `aplicacion/emisiones.py` con `registrar_emision`,
  `_replay` y `anular_emision`, `aplicacion/lecturas.py`,
  `aplicacion/saldo_inicial.py`, `aplicacion/cobranza.py`), `compartido/reparto.py`,
  `compartido/tablas_protegidas.py`.
- **Dependencia nueva entre módulos**: `cuenta_corriente.aplicacion → complejos.aplicacion.lectura`
  (configuración vigente y estado de migración). Permitida por D-116 (sólo `aplicacion`, sin ciclo:
  `complejos` no importa `cuenta_corriente`).
- **Base**: migración `backend/migraciones/versions/0034_intereses_y_saldo_inicial.py` (cabeza actual
  `0033`).
- **Tests existentes que cambian** (L-064): la semilla `tests/integracion/_cuenta_corriente.py`
  (`sembrar`) suma una versión de configuración con tasa 0; los tests que fijan la versión de alembic
  en `0033`; `_DUENO_DE_TABLA` de `tests/unitarios/test_fronteras_de_modulos.py`; los planes de
  `EXPLAIN` de la foto; `test_cc_anulacion_candado.py`; y los ocho archivos que llaman a
  `registrar_emision` (inventario en `design.md`, Context), revisados uno por uno en la tarea 5.5.
- **Consumidores fuera del área**: 5 (llama `registrar_saldo_inicial`, autoriza, audita y confirma),
  7 (recibe intereses en `EmisionRegistrada`, asegura configuración vigente, conserva D8), 8 (fecha
  valor de los pagos, R11, R18), 10a y 10b (situación de cobranza), 11 (detalle de interés en el
  portal), 4d (cuentas de persona).

## Lecciones que aplican (`knowledge-base/15_lecciones.md`)

- **L-019, L-035, L-049, L-061**: cada aserción de plata o de seguridad lleva un mutante que la hace
  fallar; el RED se lee en el traceback y se guarda en `tasks.md` antes del código (todas las tareas).
- **L-034, L-036**: el mutante de RF-01 apunta a la foto final, no a un paso anterior (tarea 1.2); cada
  mutante de aislamiento apaga una sola defensa y espera el rojo donde esa defensa es la única que
  queda (tareas 2.1 y 7.2).
- **L-016, L-017**: la observación de "una sola foto" mira la sentencia SQL real, que sí puede dar
  otro resultado (tarea 1.2).
- **L-064, L-041**: tablas protegidas, dueño de tablas y versión de alembic hardcodeados; suite
  completa al cierre (tareas 2.1, 5.5, 8.1).
- **L-054**: las tablas nuevas entran por `TABLAS_DE_SOLO_AGREGAR` y se verifican por el efecto, con
  su cierre de dependencias (tarea 2.1).
- **L-012**: la deuda RF-01, RF-02 y RB-6 la cierra este change, primer consumidor real (grupo 1).
- **L-048**: quién construye las tareas CRITICAL (Gobernanza).

## Knowledge Base Impact

| Documento | Acción | Qué |
|---|---|---|
| `knowledge-base/05_reglas_de_negocio.md` | REWRITE | R03 (dónde vive, corte, convención diaria, "mes entero" por meses calendario, cobertura por intervalos y tasa 0 que difiere, configuración por corte), R09 (contrato y dónde vive), R20 (umbral `>=`, período con sólo interés, dónde vive), R30 (dónde vive), R17 (re-emisión según E1) |
| `knowledge-base/04_modelo_de_datos.md` | REWRITE | `tramo_de_interes`, `carga_de_saldo_inicial`, `origen_de_saldo_inicial`; uso de `movimiento.corte` |
| `knowledge-base/08_arquitectura_propuesta.md` | REWRITE | lista de tablas de sólo agregar; dependencia `cuenta_corriente → complejos.aplicacion` |
| `knowledge-base/09_decisiones_y_supuestos.md` | APPEND | decisiones con las elecciones E1 a E19 firmadas (E6 como cumplimiento de D-143; E3.2 y E13 como la decisión de Juani del 30/10/2026 sobre "mes entero") |
| `knowledge-base/10_preguntas_abiertas.md` | REWRITE | preguntas nuevas que no se resuelvan al firmar (por ejemplo E11 y PA-1), notas en P58 (más la pregunta de E18) y P59 |
| `knowledge-base/11_glosario.md` | REWRITE | corte, tramo de interés, días cubiertos (unión de tramos), mes entero (meses calendario), firma del pedido, cuentas alcanzadas por una emisión, carga de saldo inicial, fecha de migración, situación de cobranza, fecha de clasificación, deuda de intereses |
| `knowledge-base/12_fichas_de_changes.md` | REWRITE | ficha 4c, cierre de RF-01, RF-02 y RB-6, deuda del cierre del 4c; consumidores 5 (contrato de filas de E16, firma del pedido, PA-1 como bloqueante, mostrar el mes de la migración por E18), 7 (contrato de `EmisionRegistrada`, replay de E15, anulación de D0), 8, 10a y 10b (fecha de clasificación de E14) |
| `knowledge-base/15_lecciones.md` | APPEND | sólo las lecciones que dé el auditor |
| `CHANGES.md` | REWRITE | estado de C-07c |
| `01`, `02`, `03`, `06`, `07`, `13`, `14`, `16` | none | sin actores, rutas, historias, flujos, stack ni forma de trabajo nuevos: el 4c es núcleo sin API |

Fuera de `knowledge-base/`: la sección "Estado" de `CLAUDE.md` y `AGENTS.md` (idénticos) y la nota
`obsidian.md` de Juani se actualizan al archivar.

## Aprobación

Gobernanza CRITICAL (D-094, D-111). La completa, a mano, Juani, Alberto o Emiliano, con fecha y
alcance. Ningún agente la escribe. Las elecciones E1 a E19 y sus alternativas están en `design.md`,
sección "Elecciones a firmar" (E6 ratifica D-143; E3.2 y E13 ratifican la decisión de Juani del
30/10/2026; ninguna de las tres es una alternativa abierta).

| Firmante (Juani, Alberto o Emiliano) | Fecha | Alcance aprobado |
|---|---|---|
| Juani Sarmiento | 11/11/2026 | Propuesta completa; E1 a E19 con la recomendación de design.md; partida en H-004, H-005 y H-006 sin rompedor (D-152) |
