# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **PropTech**. El estado vive **sólo acá**; el
> detalle de cada change (objetivo, reglas, qué prueba el rompedor, "terminado cuando") está en
> [`knowledge-base/12_fichas_de_changes.md`](knowledge-base/12_fichas_de_changes.md). Cada código
> `C-NN` es la numeración secuencial de Active Stack v1; el nombre entre comillas y el código propio
> del proyecto (por ejemplo `1a`, `6b`, `10b`) son los que ya usan el roadmap, `openspec/changes/` y
> las decisiones archivadas: **no se renumeran** (D-093).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 infraestructura-base (1a)
  └── C-02 arranque-del-sistema (1b)
        └── C-03 cola-logs-y-respaldos (1c)
              └── C-04 respaldos-y-restauracion (1d)
                    └── C-05 acceso-y-aislamiento (2)        ← desbloquea TODO lo demás
                          │
                          └── C-06 configuracion-del-edificio (3)
                                │
                                └── C-07 motor-de-cuenta-corriente (4)
                                      │
                                      ├── C-08 importacion-desde-excel (5)
                                      │
                                      └── C-09 gastos-y-cargos (6)
                                            │
                                      (C-08 + C-09)
                                            ▼
                                      C-10 liquidacion-y-emision (7)   ← el change más grande del MVP
                                            │
                        ┌───────────────────┼────────────────────────────┐
                        ▼                   ▼                            ▼
                C-11 pagos-informados   C-19 lectura-de-facturas   (resto de C-10 cierra M1,
                (8)                     (14, con C-09)              test de aceptación)
                        │
          ┌─────────────┼─────────────────┐
          ▼             ▼                 ▼
  C-12 motor-de-reglas  C-13 extracto-   C-14 morosidad (10a)
  (6b)                  bancario (9)           │
                                          ┌─────┴─────┐
                                          ▼           ▼
                        C-15 condonacion-judicial-  C-16 portal-del-vecino (11)
                        y-libre-deuda (10b)                │
                                          │           C-17 vista-del-consejo (12)
                                          └─────┐
                                                ▼
                                    C-18 avisos-por-email (13)
                                                │
                  (C-12 + C-13 + C-17 + C-18 + C-19 + todos los anteriores + datos del piloto)
                                                ▼
                                    C-20 piloto-en-paralelo (15)
```

### Paralelismo por fase

```
GATE 0: ninguna
  → C-01 infraestructura-base (solo)

GATE 1: C-01 ✓
  → C-02 arranque-del-sistema (solo)

GATE 2: C-02 ✓
  → C-03 cola-logs-y-respaldos (solo)

GATE 3: C-03 ✓
  → C-04 respaldos-y-restauracion (solo, HIGH: aprobación de un socio)

GATE 4: C-04 ✓
  → C-05 acceso-y-aislamiento (solo, CRITICAL: aprobación de un socio)

GATE 5: C-05 ✓
  → C-06 configuracion-del-edificio (solo, HIGH: aprobación de un socio)

GATE 6: C-06 ✓
  → C-07 motor-de-cuenta-corriente (solo, CRITICAL: aprobación de un socio)

GATE 7: C-07 ✓                                           ← PRIMER FORK real (2 paralelos)
  → C-08 importacion-desde-excel    [Agente A]
  → C-09 gastos-y-cargos            [Agente B]

GATE 8: C-08 + C-09 ✓
  → C-10 liquidacion-y-emision (solo, CRITICAL: aprobación de un socio; el más grande del MVP)

GATE 9: C-10 ✓                                           ← SEGUNDO FORK (2 paralelos)
  → C-11 pagos-informados           [Agente A] (CRITICAL: aprobación de un socio)
  → C-19 lectura-de-facturas        [Agente C] (necesita también C-09)

GATE 10: C-11 ✓                                          ← TERCER FORK (3 paralelos)
  → C-12 motor-de-reglas            [Agente A]
  → C-13 extracto-bancario          [Agente B]
  → C-14 morosidad                  [Agente C]

GATE 11: C-14 ✓                                          ← CUARTO FORK (2 paralelos)
  → C-15 condonacion-judicial-y-libre-deuda [Agente B] (CRITICAL: aprobación de un socio)
  → C-16 portal-del-vecino                  [Agente C]

GATE 12: C-16 ✓
  → C-17 vista-del-consejo (HIGH: revisión de un socio)   [Agente C]

GATE 13: C-11 + C-15 ✓
  → C-18 avisos-por-email   [Agente B]

GATE 14: C-12 + C-13 + C-17 + C-18 + C-19 ✓ + datos del edificio piloto (P1)
  → C-20 piloto-en-paralelo (solo, cierra el roadmap)
```

### Camino crítico (14 changes — mínimo irreducible hasta cerrar M3)

```
C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-07 → C-09 → C-10 → C-11 → C-14 → C-15 → C-18 → C-20
```

El **camino crítico al test de aceptación de M1** (reproducir al centavo la última liquidación del
piloto) es el prefijo de 10 changes: `C-01 → C-02 → C-03 → C-04 → C-05 → C-06 → C-07 → C-08/C-09 →
C-10`. Ese es el que el proyecto sigue priorizando hoy (ver
`knowledge-base/01_vision_y_objetivos.md` §Cómo se valida). El resto de la cadena hasta `C-20` cierra
M2 y M3.

### Plan óptimo con 3 agentes

> **Hoy programa una sola persona por change** (Juani o Alberto, `knowledge-base/14_forma_de_trabajo.md`):
> esta tabla muestra el paralelismo que el árbol de dependencias permitiría si hubiera tres agentes
> trabajando a la vez, no el reparto real.

```
Paso │ Agente A (Backend Core)        │ Agente B (Backend Aux)          │ Agente C (Frontend/IA)
─────┼─────────────────────────────────┼──────────────────────────────────┼────────────────────────────
  1  │ C-01 infraestructura-base       │         -                       │         -
  2  │ C-02 arranque-del-sistema       │         -                       │         -
  3  │ C-03 cola-logs-y-respaldos      │         -                       │         -
  4  │ C-04 respaldos-y-restauracion   │         -                       │         -
  5  │ C-05 acceso-y-aislamiento       │         -                       │         -
  6  │ C-06 configuracion-del-edificio │         -                       │         -
  7  │ C-07 motor-de-cuenta-corriente  │         -                       │         -
  8  │ C-08 importacion-desde-excel    │ C-09 gastos-y-cargos            │         -
  9  │ C-10 liquidacion-y-emision      │         -                       │         -
 10  │ C-11 pagos-informados           │         -                       │ C-19 lectura-de-facturas
 11  │ C-12 motor-de-reglas            │ C-13 extracto-bancario          │ C-14 morosidad
 12  │         -                       │ C-15 condonacion-judicial...    │ C-16 portal-del-vecino
 13  │         -                       │ C-18 avisos-por-email           │ C-17 vista-del-consejo
 14  │         -                       │         -                       │ C-20 piloto-en-paralelo
```

---

## FASE 1 — Infraestructura

### [C-01] `infraestructura-base` · 1a
- **Estado**: `[x]` archivado (09/10/2026)
- **Scope**: estructura de carpetas (D-040), Docker Compose con PostgreSQL/Caddy/API/web, Alembic
  con migración vacía, esqueleto FastAPI con `/api/salud`, esqueleto Next.js, CI con tests y linter,
  `.env.example` sin secretos, sólo Caddy con puertos públicos
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §1a
  - `knowledge-base/02_descripcion_general.md` §Arquitectura general
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios

---

### [C-02] `arranque-del-sistema` · 1b
- **Estado**: `[x]` archivado (11/10/2026)
- **Scope**: configuración con variables de Redis y parámetros conectadas en Compose, migraciones
  que dependen sólo de PostgreSQL, tipo `Dinero` sobre `Decimal`, `config/parametros.yaml` con su
  lector validado, edificio de ejemplo validado
- **Dependencias**: C-01
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §1b
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-042, D-046, D-052, D-053)
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno

---

### [C-03] `cola-logs-y-respaldos` · 1c
- **Estado**: `[x]` archivado (14/10/2026), OK con deuda anotada (D-091)
- **Scope**: logs JSON con campos cerrados, `request_id` de punta a punta, Redis + worker ARQ con
  reintentos e idempotencia (`trabajos_hechos`), `/api/salud` con la cola, `/salud-web`, rotación de
  logs, `Dinero` copiable y serializable, `SecretStr`, un engine único por proceso
- **Dependencias**: C-02
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §1c
  - `knowledge-base/15_lecciones.md` (L-001 a L-009)
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-038, D-087, D-090, D-091)

---

### [C-04] `respaldos-y-restauracion` · 1d
- **Estado**: `[ ]` ya propuesto en `openspec/changes/respaldos-y-restauracion/`: falta la aprobación escrita y fechada de un socio en `proposal.md` (HIGH); después, `/opsx:apply`
- **Scope**: servicio `respaldos` con `pg_dump` al arrancar y a diario, 14 copias, salud por
  antigüedad; `restaurar.sh` con destino validado; humo ampliado (Redis, worker, `request_id`,
  backup, restauración); `shellcheck` en el CI; README
- **Dependencias**: C-03
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §1d
  - `openspec/changes/respaldos-y-restauracion/proposal.md`
  - `knowledge-base/15_lecciones.md` (L-001, L-002, L-006 a L-009)
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-087, D-090)

---

## FASE 2 — Acceso y configuración

### [C-05] `acceso-y-aislamiento` · 2
- **Estado**: `[ ]` pendiente (CRITICAL, explore propio)
- **Scope**: login del personal y del vecino, los cuatro roles (D-037), alcance por edificio,
  Row-Level Security con `SET LOCAL`, auditoría de cada acción sensible, 404 fuera de alcance, 403
  sin permiso, límite de pedidos en el login
- **Dependencias**: C-04
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §2
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Acceso y aislamiento (R10)
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/06_funcionalidades.md` §HU-V1
  - `knowledge-base/10_preguntas_abiertas.md` (P18, P23)

---

### [C-06] `configuracion-del-edificio` · 3
- **Estado**: `[ ]` pendiente (HIGH)
- **Scope**: edificios, unidades con tipo y coeficiente, grupos de reparto, categorías de gasto,
  configuración versionada de intereses y fondo de reserva, carga del edificio de ejemplo en la base,
  estado de migración del edificio
- **Dependencias**: C-05
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §3
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Complejos (configuración del edificio)
  - `knowledge-base/06_funcionalidades.md` §HU-A1
  - `knowledge-base/10_preguntas_abiertas.md` (P16, P19, P24, P33)

---

## FASE 3 — El núcleo financiero (cierra M1 Liquida)

### [C-07] `motor-de-cuenta-corriente` · 4
- **Estado**: `[ ]` pendiente (CRITICAL, explore propio)
- **Scope**: libro de movimientos de sólo agregar, obligaciones/pagos/imputaciones, intereses
  simples al registrarse, reparto por mayor resto, correcciones con contra-asiento, caso de uso de
  saldo inicial, función pura de moroso crítico, contrato mínimo de emisión
- **Dependencias**: C-05, C-06
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §4
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Cuenta corriente
  - `knowledge-base/06_funcionalidades.md` §HU-A9
  - `knowledge-base/10_preguntas_abiertas.md` (P10, P11, P21, P31, P34, P42)

---

### [C-08] `importacion-desde-excel` · 5
- **Estado**: `[ ]` pendiente (CRITICAL, D-077)
- **Scope**: plantilla de Excel con hoja opcional de saldos por período, validación fila por fila,
  carga atómica, detección de reimportación, saldos en borrador comparados unidad por unidad
- **Dependencias**: C-06, C-07
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §5
  - `knowledge-base/05_reglas_de_negocio.md` §R09
  - `knowledge-base/06_funcionalidades.md` §HU-A2
  - `knowledge-base/10_preguntas_abiertas.md` (P24)

---

### [C-09] `gastos-y-cargos` · 6
- **Estado**: `[ ]` pendiente
- **Scope**: proveedores, gastos con sus cuatro estados, sueldo del encargado como gasto, cargos
  particulares sueltos o por Excel, nota de crédito asociada a la factura
- **Dependencias**: C-06, C-07
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §6
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Gastos y cargos
  - `knowledge-base/06_funcionalidades.md` §HU-A3, HU-A3b
  - `knowledge-base/10_preguntas_abiertas.md` (P15, P17, P25, P36, P37)

---

### [C-10] `liquidacion-y-emision` · 7
- **Estado**: `[ ]` pendiente (CRITICAL, explore propio; el change más grande del MVP)
- **Scope**: preliquidación sin efectos, emisión con efectos en una sola transacción, estados de la
  liquidación (borrador, emitida, distribuida, anulada), controles antes de emitir con alertas
  aceptadas, links de descarga firmados, plantilla del PDF (skill impeccable)
- **Dependencias**: C-08, C-09
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §7
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Liquidación y emisión
  - `knowledge-base/06_funcionalidades.md` §HU-A4, HU-A5
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-069, D-070, D-074)
  - `knowledge-base/10_preguntas_abiertas.md` (P26 a P28, P38, P39)

---

## FASE 4 — M2 Cobra

> Los changes C-11 y C-19 pueden proponerse en paralelo una vez cerrado C-10. C-12, C-13 y C-14
> pueden proponerse en paralelo una vez cerrado C-11.

### [C-11] `pagos-informados` · 8
- **Estado**: `[ ]` pendiente (CRITICAL)
- **Scope**: subir comprobante, lectura con IA, número de operación único, bandeja de confirmación y
  rechazo, imputación con la fecha de la transferencia, reparto de un pago entre unidades, estado
  revertido, asistente de reimputación
- **Dependencias**: C-10
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §8
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Pagos
  - `knowledge-base/06_funcionalidades.md` §HU-A6, HU-V4
  - `knowledge-base/10_preguntas_abiertas.md` (P12, P27, P29, P40)

---

### [C-12] `motor-de-reglas` · 6b
- **Estado**: `[ ]` pendiente (explore propio; fuera del camino a M1)
- **Scope**: módulo `politicas`, puerto de políticas, adaptador GoRules ZEN, validador en sus dos
  momentos, reglas versionadas por edificio, editor jdm-editor en el frontend
- **Dependencias**: C-10, C-11
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §6b
  - `knowledge-base/13_motor_de_reglas.md`
  - `knowledge-base/05_reglas_de_negocio.md` §R33
  - `knowledge-base/10_preguntas_abiertas.md` (P22)

---

### [C-13] `extracto-bancario` · 9
- **Estado**: `[ ]` pendiente
- **Scope**: subir extracto en CSV o Excel, adaptador por banco, marcar coincidencias, fondos
  pendientes de identificar, sugerencias de confianza alta por código de unidad o CBU histórico
- **Dependencias**: C-11
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §9
  - `knowledge-base/06_funcionalidades.md` §HU-A7
  - `knowledge-base/05_reglas_de_negocio.md` §R19, R34
  - `knowledge-base/10_preguntas_abiertas.md` (P9, P30)

---

### [C-14] `morosidad` · 10a
- **Estado**: `[ ]` pendiente
- **Scope**: listado por unidad desde las imputaciones, exportación a Excel, presentación del
  moroso crítico (sólo lectura, no escribe en la cuenta corriente)
- **Dependencias**: C-11
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §10a
  - `knowledge-base/05_reglas_de_negocio.md` §R20
  - `knowledge-base/06_funcionalidades.md` §HU-A8

---

### [C-15] `condonacion-judicial-y-libre-deuda` · 10b
- **Estado**: `[ ]` pendiente (CRITICAL)
- **Scope**: condonación de interés como movimiento con motivo, marca de gestión judicial,
  certificado de libre deuda con fecha de corte
- **Dependencias**: C-14
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §10b
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Morosidad y gestión de deuda
  - `knowledge-base/06_funcionalidades.md` §HU-A10, HU-A11
  - `knowledge-base/10_preguntas_abiertas.md` (P14, P20, P32)

---

### [C-16] `portal-del-vecino` · 11
- **Estado**: `[ ]` pendiente
- **Scope**: todas las unidades de la persona juntas, deuda y vencimiento, expensa por ordinaria y
  extraordinaria con comparación contra el mes anterior, descarga de PDFs, app instalable
- **Dependencias**: C-14
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §11
  - `knowledge-base/06_funcionalidades.md` §HU-V1 a HU-V5
  - `knowledge-base/05_reglas_de_negocio.md` §R16

---

### [C-17] `vista-del-consejo` · 12
- **Estado**: `[ ]` pendiente (HIGH)
- **Scope**: morosidad, gastos y liquidaciones en sólo lectura para el consejo
- **Dependencias**: C-16
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §12
  - `knowledge-base/06_funcionalidades.md` §HU-C1
  - `knowledge-base/03_actores_y_roles.md`

---

### [C-18] `avisos-por-email` · 13
- **Estado**: `[ ]` pendiente
- **Scope**: puerto de email, aviso de vencimiento y de mora con clave de idempotencia, aviso
  corrido a día hábil (propuesta), validación de contactos (propuesta)
- **Dependencias**: C-11, C-15
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §13
  - `knowledge-base/06_funcionalidades.md` §HU-V6
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Avisos
  - `knowledge-base/10_preguntas_abiertas.md` (P41)

---

## FASE 5 — M3 Piloto

### [C-19] `lectura-de-facturas` · 14
- **Estado**: `[ ]` pendiente
- **Scope**: lectura del QR de ARCA, IA completa concepto/período/categoría/grupo, factura
  duplicada frenada, control de monto atípico (propuesta)
- **Dependencias**: C-09, C-10
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §14
  - `knowledge-base/05_reglas_de_negocio.md` §R12, R23
  - `knowledge-base/06_funcionalidades.md` §HU-A3
  - `knowledge-base/10_preguntas_abiertas.md` (P12, P21)

---

### [C-20] `piloto-en-paralelo` · 15
- **Estado**: `[ ]` pendiente
- **Scope**: carga de los datos reales del piloto, un mes completo en paralelo, comparación al
  centavo, prueba de restauración de un backup, evidencia de aislamiento
- **Dependencias**: C-12, C-13, C-17, C-18, C-19 (y todos los anteriores) + datos del edificio piloto (P1)
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §15
  - `knowledge-base/01_vision_y_objetivos.md` §Cómo se valida
  - `knowledge-base/10_preguntas_abiertas.md` (P1, P12)
