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

## El mapa en simple

Por etapas. ✅ terminado · 👉 en marcha · ⏳ pendiente. El detalle, las dependencias exactas y los
gates están en el árbol de abajo.

```
1. BASE TÉCNICA ✅
   1a infraestructura · 1b arranque · 1c cola y logs · 1d respaldos

2. ACCESO ✅
   2a aislamiento por administración (cada empresa ve sólo lo suyo)
   2b login con Clerk · 2.2a roles de la empresa · 2c endurecimiento

3. CONFIGURACIÓN DEL EDIFICIO
   ✅ 3a datos del edificio      ✅ 3b pantallas
   ✅ acceso de desarrollo (PR #1)
   👉 3c pulido: bugs + ubicación + pisos  ← en paralelo al 4a

4. LA PLATA (cuenta corriente)
   👉 4a cimientos: reparto al centavo, umbral de $500
   ⏳ 4b libro de movimientos (deudas y pagos)
   ⏳ 4c intereses y moroso
   ⏳ 4d cambio de titular (va después del 7)

5. CARGAR Y LIQUIDAR
   ⏳ 5 importar desde Excel       ⏳ 6 gastos y cargos
   ⏳ 7 liquidación y emisión  ← el más grande; con esto se llega a M1

6. COBRAR Y SEGUIR
   ⏳ 8 pagos informados · 9 extracto bancario · 6b motor de reglas
   ⏳ 10a morosidad · 10b condonación y libre deuda
   ⏳ 11 portal del vecino · 12 vista del consejo · 13 avisos por email
   ⏳ 14 lectura de facturas

7. PILOTO
   ⏳ 15 un edificio real en paralelo  ← el final
```

- **Orden obligado (camino crítico):** 4a → 4b → 4c → 5 → 7 → 8 → 10a → 10b → 13 → 15.
- **En paralelo, no frenan a nadie:** 3c, 6, 4d, 6b, 9, 11, 12 y 14.
- **Numeración:** el número corto (4a, 7, 10b) es el de las fichas de abajo; el código C-xx es el
  mismo change con otro nombre (4a = C-07a, 7 = C-10).

## Árbol de dependencias

```
C-01 infraestructura-base (1a)
  └── C-02 arranque-del-sistema (1b)
        └── C-03 cola-logs-y-respaldos (1c)
              └── C-04 respaldos-y-restauracion (1d)
                    └── C-05a aislamiento-por-administracion (2a)   ← el candado (D-097); desbloquea TODO lo demás
                          │
                          ├── C-05a-bis roles-de-la-empresa (2.2a) ← archivado
                          │     └── C-05b login-y-usuarios (2b) ← archivado; Clerk; lo piden C-16 y C-20
                          ├── C-05c endurecimiento-de-infraestructura (2c)
                          │
                          └── C-06a configuracion-del-edificio (3a)   ← partido en 3a y 3b (E1)
                                │
                                ├── C-06b pantallas-del-edificio (3b)    ← fuera del camino crítico
                                │     └── C-06c pulido-de-la-configuracion (3c) ← en paralelo al 4a, fuera del camino crítico
                                │
                                └── C-07a cimientos-del-libro (4a)        ← el 4 partido en 4a a 4d (exploración del 4, §8)
                                      │
                                      ├── C-09 gastos-y-cargos (6)        ← tras el 4a si no escribe en el libro (S-04); si escribe, tras el 4b
                                      │
                                      └── C-07b libro-de-movimientos (4b)
                                            │
                                            └── C-07c intereses-saldo-inicial-y-moroso (4c)
                                                  │
                                                  └── C-08 importacion-desde-excel (5)
                                                        │
                                      (C-07b + C-07c + C-08 + C-09)
                                                        ▼
                                      C-10 liquidacion-y-emision (7)   ← el change más grande del MVP
                                            │
                        ┌───────────────────┼──────────────────────┬────────────────────────┐
                        ▼                   ▼                      ▼                        ▼
                C-11 pagos-informados   C-19 lectura-de-facturas   C-07d cambio-de-titular  (resto de C-10 cierra M1,
                (8)                     (14, con C-09)             (4d, no bloquea M1)      test de aceptación)
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
                  (C-07d + C-12 + C-13 + C-17 + C-18 + C-19 + todos los anteriores + datos del piloto)
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
  → C-05a aislamiento-por-administracion (solo, CRITICAL: aprobación de un socio)

GATE 5: C-05a ✓                                          ← roles antes del login
  → C-06a configuracion-del-edificio [Agente A] (HIGH: aprobación de un socio; camino crítico)
  → C-05c endurecimiento-de-infraestructura [Agente C] (MEDIUM)

GATE 6: C-06a ✓
  → C-06b pantallas-del-edificio (archivado; su propose esperó los siete shape con Juani)
  → C-07a cimientos-del-libro [Agente A] (4a, HIGH: aprobación de un firmante de D-111; camino crítico)
  → C-06c pulido-de-la-configuracion [Agente B] (3c, HIGH: aprobación de un firmante de D-111;
    en paralelo al 4a, fuera del camino crítico; necesita también C-06b y C-05b, archivados)

GATE 6 bis: C-05a + C-06a + C-06b ✓
  → C-05a-bis roles-de-la-empresa (2.2a, archivado)
    → C-05b login-y-usuarios (2b, archivado 22/10/2026; Clerk, CRITICAL; P48 resuelta en D-099)

GATE 7: C-07a ✓                                          ← PRIMER FORK real (2 paralelos)
  → C-07b libro-de-movimientos [Agente A] (4b, CRITICAL: aprobación de un firmante de D-111)
  → C-09 gastos-y-cargos        [Agente B] (sólo si no escribe en el libro, SUPUESTO S-04 sin
    verificar contra R14 y R25; si escribe, pasa al GATE 8)

GATE 8: C-07b ✓
  → C-07c intereses-saldo-inicial-y-moroso (4c, CRITICAL: aprobación de un firmante de D-111)

GATE 9: C-07c ✓
  → C-08 importacion-desde-excel (CRITICAL)

GATE 10: C-07b + C-07c + C-08 + C-09 ✓
  → C-10 liquidacion-y-emision (solo, CRITICAL: aprobación de un firmante de D-111; el más grande del MVP)

GATE 11: C-10 ✓                                          ← SEGUNDO FORK (3 paralelos)
  → C-11 pagos-informados           [Agente A] (CRITICAL: aprobación de un firmante de D-111)
  → C-07d cambio-de-titular         [Agente B] (4d, CRITICAL; fuera del camino a M1)
  → C-19 lectura-de-facturas        [Agente C] (necesita también C-09)

GATE 12: C-11 ✓                                          ← TERCER FORK (3 paralelos)
  → C-12 motor-de-reglas            [Agente A]
  → C-13 extracto-bancario          [Agente B]
  → C-14 morosidad                  [Agente C]

GATE 13: C-14 ✓                                          ← CUARTO FORK (2 paralelos)
  → C-15 condonacion-judicial-y-libre-deuda [Agente B] (CRITICAL: aprobación de un firmante de D-111)
  → C-16 portal-del-vecino                  [Agente C] (necesita también C-05b)

GATE 14: C-16 ✓
  → C-17 vista-del-consejo (HIGH: revisión de un firmante de D-111)   [Agente C]

GATE 15: C-11 + C-15 ✓
  → C-18 avisos-por-email   [Agente B]

GATE 16: C-05b + C-05c + C-06c + C-07d + C-12 + C-13 + C-17 + C-18 + C-19 ✓ + datos del edificio piloto (P1)
  → C-20 piloto-en-paralelo (solo, cierra el roadmap)
```

### Camino crítico (16 changes — mínimo irreducible hasta cerrar M3)

```
C-01 → C-02 → C-03 → C-04 → C-05a → C-06a → C-07a → C-07b → C-07c → C-08 → C-10 → C-11 → C-14 → C-15 → C-18 → C-20
```

El **camino crítico al test de aceptación de M1** (reproducir al centavo la última liquidación del
piloto) es el prefijo de 11 changes: `C-01 → C-02 → C-03 → C-04 → C-05a → C-06a → C-07a → C-07b →
C-07c → C-08 → C-10`, con C-09 en paralelo desde C-07a. Ese es el que el proyecto sigue priorizando hoy
(ver `knowledge-base/01_vision_y_objetivos.md` §Cómo se valida). El resto de la cadena hasta `C-20`
cierra M2 y M3. Partir el 4 (exploración del 4, §8) alarga la cadena en cantidad de changes pero no en
trabajo: cada sub-change es una parte del mismo 4, y el 6 deja de esperar el libro entero.
**C-06c y C-07d quedan fuera del camino crítico.**

### Plan óptimo con 3 agentes

> **Hoy programa una sola persona por change** (Juani, Alberto o Emiliano, `knowledge-base/14_forma_de_trabajo.md`):
> esta tabla muestra el paralelismo que el árbol de dependencias permitiría si hubiera tres agentes
> trabajando a la vez, no el reparto real. El reparto real del paso 7 sí es en paralelo: el 4a lo
> lleva su propose en revisión y el 3c lo propone Emiliano (pedido de Juani, 26/10/2026).

```
Paso │ Agente A (Backend Core)        │ Agente B (Backend Aux)          │ Agente C (Frontend/IA)
─────┼─────────────────────────────────┼──────────────────────────────────┼────────────────────────────
  1  │ C-01 infraestructura-base       │         -                       │         -
  2  │ C-02 arranque-del-sistema       │         -                       │         -
  3  │ C-03 cola-logs-y-respaldos      │         -                       │         -
  4  │ C-04 respaldos-y-restauracion   │         -                       │         -
  5  │ C-05a aislamiento-por-admin.    │         -                       │         -
  6  │ C-06a configuracion-del-edif.   │         -                       │ C-05c endurecimiento-de-infra.
  7  │ C-07a cimientos-del-libro       │ C-06c pulido-de-la-config.      │ C-06b pantallas-del-edificio
  8  │ C-07b libro-de-movimientos      │ C-09 gastos-y-cargos            │ C-05a-bis roles-de-la-empresa
  9  │ C-07c intereses-saldo-y-moroso  │         -                       │ C-05b login-y-usuarios
 10  │ C-08 importacion-desde-excel    │         -                       │         -
 11  │ C-10 liquidacion-y-emision      │         -                       │         -
 12  │ C-11 pagos-informados           │ C-07d cambio-de-titular         │ C-19 lectura-de-facturas
 13  │ C-12 motor-de-reglas            │ C-13 extracto-bancario          │ C-14 morosidad
 14  │         -                       │ C-15 condonacion-judicial...    │ C-16 portal-del-vecino
 15  │         -                       │ C-18 avisos-por-email           │ C-17 vista-del-consejo
 16  │         -                       │         -                       │ C-20 piloto-en-paralelo
```

---

## FASE 1 — Infraestructura

### [C-01] `infraestructura-base` · 1a
- **Estado**: `[x]` archivado (09/10/2026)
- **Scope**: estructura de carpetas (D-040), Docker Compose con PostgreSQL/Caddy/API/web, Alembic
  con migración vacía, esqueleto FastAPI con `/api/salud`, esqueleto Next.js, CI con tests y linter,
  `.env.example` sin secretos, sólo Caddy con puertos públicos
- **Dependencias**: ninguna
- **Governance**: no declarado (archivado); su propuesta no declara nivel de gobernanza
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
- **Governance**: no declarado (archivado); su propuesta no declara nivel de gobernanza
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
- **Estado**: `[x]` archivado (14/10/2026), OK con deuda anotada en la vuelta 3 (D-095)
- **Scope**: servicio `respaldos` con `pg_dump` al arrancar y a diario, 14 copias, salud por
  antigüedad; `restaurar.sh` con destino validado; humo ampliado (Redis, worker, `request_id`,
  backup, restauración); `shellcheck` en el CI; README
- **Dependencias**: C-03
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §1d
  - `openspec/changes/archive/2026-10-14-respaldos-y-restauracion/proposal.md`
  - `knowledge-base/15_lecciones.md` (L-001, L-002, L-006 a L-009, L-014 a L-017)
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-087, D-090, D-095)

---

## FASE 2 — Acceso y configuración

### [C-05a] `aislamiento-por-administracion` · 2a
- **Estado**: `[x]` archivado (15/10/2026), OK con deuda anotada en la vuelta 3, cerrado en la vuelta 4
  con la opción B (D-098); partido del cambio 2 `acceso-y-aislamiento` por D-097
- **Scope**: roles de PostgreSQL separados (arranque, migrador, aplicación, respaldo), Row-Level Security con
  `SET LOCAL` por administración, tablas mínimas, alcance por edificio (404) y permiso por acción
  según D-096 (403), auditoría de acciones sensibles (D-016), el tenant del worker, la web fuera de la
  red de la base; se prueba sin login, con la identidad inyectada
- **Dependencias**: C-04
- **Governance**: CRITICO
- **Leer antes**:
  - `openspec/changes/archive/2026-10-15-aislamiento-por-administracion/proposal.md`
  - `openspec/exploraciones/2026-10-15-acceso-y-aislamiento.md`
  - `knowledge-base/12_fichas_de_changes.md` §2a y "Deuda del cierre del 2a"
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Acceso y aislamiento (R10)
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/15_lecciones.md` (L-001 a L-021)
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-016, D-037, D-087, D-091, D-095, D-096, D-097,
    D-098)

---

### [C-05a-bis] `roles-de-la-empresa` · 2.2a
- **Estado**: `[x]` archivado (20/10/2026); 17 tareas hechas, cierre 7.2 en `4c24333`.
  Número **2.2a** decidido por Juani; se conserva la numeración de los demás changes.
- **Scope**: perfil × alcance, roles de la empresa, vínculo propietario/inquilino por unidad,
  migraciones 0017/0018, matriz de D-106, personal único por alcance y consejo único por persona y
  edificio; contrato de asignación y auditoría. Deuda y límites en la ficha del 2.2a.
- **Dependencias**: C-05a y C-06a/C-06b (adapta configuración y textos construidos).
- **Governance**: CRITICO; E1 a E8 y RR-1 a RR-4 firmadas por Juani (20/10/2026, `610eb4a`).
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §2.2a
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-106)
  - `openspec/changes/archive/2026-10-20-roles-de-la-empresa/`

---

### [C-05b] `login-y-usuarios` · 2b
- **Estado**: `[x]` archivado (22/10/2026); 36 de 37 tareas hechas (7.2, aviso de privacidad, queda
  en borrador a propósito, D-108 decisión de cierre 3). P48 resuelta en D-099. El método de D-097 fue
  reemplazado por D-107; E1 a E17 firmadas por Juani (D-108, 21/10/2026).
- **Scope**: Clerk sólo para autenticación, usuario y contraseña también para vecinos, link mágico y
  Google (E17); vínculo por `persona.clerk_usuario_id` único por administración, autorización en la
  base; selector de administración, sesión del servidor de Next (con `CLERK_SECRET_KEY`, E16), límite
  de intentos por cuenta de Clerk, auditoría de ingresos y CSP estricta con nonce. El super admin
  invita al personal con perfil y alcance; vecinos desde el padrón con vínculo e invitación por mail.
  Caddy deja de publicar `/api/*` salvo `/api/salud`. Aviso de privacidad **en borrador**, sin los
  datos legales del responsable; costo de Clerk a verificar antes del piloto. Cierra deuda de 2a (R9,
  V2-7, D-1, D-6), 2c (CSP) y 3a (RF-B-4); hereda el resto en su ficha, más la nueva de este cierre
  (SU-01, 8.2 acortada, 7 hallazgos).
- **Dependencias**: C-05a, C-05a-bis (2.2a).
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §2b y "Deuda del cierre del 2b"
  - `knowledge-base/03_actores_y_roles.md`
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-036, D-099, D-106, D-107, D-108)
  - `openspec/changes/archive/2026-10-22-login-y-usuarios/`
  - `knowledge-base/15_lecciones.md`

---

### [C-05c] `endurecimiento-de-infraestructura` · 2c
- **Estado**: `[x]` archivado (16/10/2026), OK con deuda anotada (D-101).
- **Scope**: cabeceras de seguridad y volúmenes de Caddy, sin `Via` ni `X-Powered-By`, también en los
  502 de Caddy, HEAD revisado; CI en pull requests (sin perder `push` a `main` ni `workflow_dispatch`)
  con límite de tiempo medido y gitleaks y `shellcheck` por digest; contenedores con
  `no-new-privileges` y capacidades mínimas verificadas en el proceso vivo, PID 1 no root en siete
  servicios; humo con pasos nombrados, logs al fallar, un respaldo por arranque y la doble congelada;
  una sola tabla de variables; la deuda del 2a con dueño 2c (V2-5, V3-8, V3-9, V3-14, V3-15, D-5);
  rollback ejercitado y clon limpio
- **Dependencias**: C-05a
- **Governance**: MEDIO, con regla de freno en el arranque del candado (`app.py`, `roles.py`)
- **Leer antes**:
  - `openspec/changes/archive/2026-10-16-endurecimiento-de-infraestructura/proposal.md` (incluida la pregunta P1)
  - `knowledge-base/12_fichas_de_changes.md` §2c y las tablas de deuda
  - `knowledge-base/15_lecciones.md` (L-001, L-013, L-014, L-016, L-018, L-019)
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-051, D-095, D-097, D-098)

---

### [C-06a] `configuracion-del-edificio` · 3a
- **Estado**: `[x]` archivado (19/10/2026), OK (D-103, D-104); deuda en su ficha.
- **Scope**: edificio y unidad completos (tipo, coeficiente, superficie, estado de migración),
  grupos de reparto con FK compuesta por edificio y dos modos de coeficientes (D-100), categorías de
  gasto, configuración versionada de intereses, vencimiento (día fijo, único o doble con recargo) y
  fondo de reserva de sólo agregar, permisos de configuración y de lectura (el vecino ve sólo lo suyo)
  y auditoría, API con contrato de error, y la deuda R6 y R11 del 2a y la del 1b con dueño 3
- **Dependencias**: C-05a
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §3a
  - `openspec/changes/archive/2026-10-19-configuracion-del-edificio/proposal.md` y `design.md`
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Complejos (configuración del edificio)
  - `knowledge-base/06_funcionalidades.md` §HU-A1
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-096, D-098, D-100)
  - `knowledge-base/10_preguntas_abiertas.md` (P16, P47)

---

### [C-06b] `pantallas-del-edificio` · 3b
- **Estado**: `[x]` archivado (20/10/2026), OK (D-105).
- **Scope**: siete pantallas de configuración del administrador, todo el ancho, menú lateral, barra
  superior y ayuda acoplada; teclado, errores por campo, carga, vacío, 320 px y WCAG 2.2 AA.
  Acceso sin login y carga del ejemplo quedaron en `acceso-de-desarrollo` (3b-bis), archivado OK el
  24/10/2026 (D-110; firma de Emiliano ratificada por D-111): el acceso sin login se descartó por D11 del 2b, y la carga del ejemplo corre como
  `proptech_app` (D10 del 2b), sin `GRANT` nuevo. Ver ficha 3b-bis.
- **Dependencias**: C-06a y los briefs de `shape`.
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §3b y §3b-bis
  - `PRODUCT.md`, `DESIGN.md` y los briefs en `openspec/exploraciones/`
  - `openspec/changes/archive/2026-10-20-pantallas-del-edificio/`

---

### [C-06c] `pulido-de-la-configuracion` · 3c
- **Estado**: `[ ]` por proponer (lo propone Emiliano con el stack; exploración del 26/10/2026)
- **Scope**: los bugs y gaps del QA manual del 23/10/2026 sobre las pantallas del edificio (errores de
  intereses y vencimiento mal atribuidos o genéricos, ayudas y mensajes de identificador, coeficiente y
  clave, confirmar "Quitar", la nota interna de `/privacidad`, grupos que no se pueden sacar); la
  **ubicación** del edificio con listas encadenadas provincia, departamento y localidad desde Georef
  guardado en el repo, y editar el edificio; la **cantidad de pisos** del edificio y el piso de cada
  unidad elegido de esa lista, con la migración de lo ya cargado. Los ítems de acceso (invitación con
  otra cuenta, menú por rol, reinvitar, `/personal` jerárquica) quedan afuera salvo que Juani los meta
  (P68), y entonces el cambio sube a CRITICAL
- **Dependencias**: C-06a, C-06b, C-05b (archivados). En paralelo al C-07a, fuera del camino crítico;
  sus migraciones se numeran después de las del 4a (`0021`, `0022`) para no dejar dos cabezas en Alembic
- **Governance**: ALTO (toca esquema de `complejo` y `unidad` y migra datos); firma Juani, Alberto o
  Emiliano (D-094, D-111)
- **Leer antes**:
  - `openspec/exploraciones/2026-10-26-pulido-de-la-configuracion.md`
  - `knowledge-base/12_fichas_de_changes.md` §3c, §3b y §3b-bis (deuda del PR #1)
  - `knowledge-base/04_modelo_de_datos.md` (`complejo`, `unidad`)
  - `knowledge-base/10_preguntas_abiertas.md` (P61 a P69)
  - `knowledge-base/15_lecciones.md` (L-029, L-034, L-038 a L-040)
  - `openspec/changes/archive/2026-10-20-pantallas-del-edificio/`

---

## FASE 3 — El núcleo financiero (cierra M1 Liquida)

> El cambio 4 `motor-de-cuenta-corriente` se parte en cuatro sub-changes (exploración del 4,
> `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md` §8), sin renumerar C-08 en
> adelante, como el 2 en 2a, 2b y 2c (D-097). Las preguntas que bloquean cada uno están en
> `knowledge-base/10_preguntas_abiertas.md` (P51 a P60); P-3 y P-7 de la exploración quedaron
> resueltas en D-113.

### [C-07a] `cimientos-del-libro` · 4a
- **Estado**: `[ ]` propose en revisión (rama `change/cimientos-del-libro`, D-113)
- **Scope**: reglas nuevas del test de fronteras sobre un `cuenta_corriente/` vacío; dueño de las
  tablas de sólo agregar y chequeo de arranque; `compartido/reparto.py`, aritmética de `Dinero` y
  `hypothesis`; columnas nuevas de `configuracion_versionada` (umbral de R30); auditoría del
  coeficiente; deuda D-053 del 1b. Sin pantallas
- **Dependencias**: C-05a, C-06a
- **Governance**: ALTO
- **Leer antes**:
  - `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md` §4 y §8
  - `openspec/exploraciones/2026-10-22-cimientos-antes-del-4.md`
  - `knowledge-base/12_fichas_de_changes.md` §4
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-040, D-053, D-109, D-113)

---

### [C-07b] `libro-de-movimientos` · 4b
- **Estado**: `[ ]` pendiente (CRITICAL)
- **Scope**: `cuenta` (de unidad o de persona), `emision`, `evento_de_emision`, `obligacion`,
  `movimiento` e `imputacion` de sólo agregar, con RLS y claves naturales; concurrencia; R04, R05, R06,
  R08, R13; HU-A9 (ruta, permiso y contrato de error); saldo sin anuladas; la API que el 4 le expone al
  resto
- **Dependencias**: C-07a
- **Governance**: CRITICO
- **Leer antes**:
  - `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md` §3 a §5
  - `knowledge-base/12_fichas_de_changes.md` §4
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Cuenta corriente
  - `knowledge-base/06_funcionalidades.md` §HU-A9
  - `knowledge-base/10_preguntas_abiertas.md` (P55, P56)

---

### [C-07c] `intereses-saldo-inicial-y-moroso` · 4c
- **Estado**: `[ ]` pendiente (CRITICAL)
- **Scope**: R03 con corte al cierre del período (D-113); R09, el caso de uso de saldo inicial que
  llama el 5; R20 con "deuda de intereses" y R30
- **Dependencias**: C-07b
- **Governance**: CRITICO
- **Leer antes**:
  - `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md` §4.5 y §9
  - `knowledge-base/12_fichas_de_changes.md` §4
  - `knowledge-base/05_reglas_de_negocio.md` (R03, R09, R20, R30)
  - `knowledge-base/10_preguntas_abiertas.md` (P53, P54; P57 a P60 para Alberto)

---

### [C-07d] `cambio-de-titular` · 4d
- **Estado**: `[ ]` pendiente (CRITICAL; puede ir después del 7, no bloquea M1)
- **Scope**: R32 y D-109.2: registro del cambio de titular, las dos opciones configurables, traspaso a
  la cuenta de persona y aviso sin bloqueo. `cuenta` ya nace polimórfica en el 4b, así que esperar no
  cuesta una migración
- **Dependencias**: C-07b, C-07c y C-10 (el prorrateo por días)
- **Governance**: CRITICO
- **Leer antes**:
  - `openspec/exploraciones/2026-10-22-motor-de-cuenta-corriente.md` §4.13 y §9
  - `knowledge-base/05_reglas_de_negocio.md` (R32)
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-109, SU-02)
  - `knowledge-base/10_preguntas_abiertas.md` (P51, P52)

---

### [C-08] `importacion-desde-excel` · 5
- **Estado**: `[ ]` pendiente (CRITICAL, D-077)
- **Scope**: plantilla de Excel con hoja opcional de saldos por período, validación fila por fila,
  carga atómica, detección de reimportación, saldos en borrador comparados unidad por unidad
- **Dependencias**: C-06a, C-07c (el caso de uso de saldo inicial)
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
- **Dependencias**: C-06a, C-07a (el reparto); C-07b si escribe en el libro (SUPUESTO S-04 del
  arquitecto del 4, sin verificar contra R14 y R25)
- **Governance**: se declara en el propose (`openspec/config.yaml`)
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
- **Dependencias**: C-07b, C-07c, C-08, C-09
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §7
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Liquidación y emisión
  - `knowledge-base/06_funcionalidades.md` §HU-A4, HU-A5
  - `knowledge-base/09_decisiones_y_supuestos.md` (D-069, D-070, D-074)
  - `knowledge-base/10_preguntas_abiertas.md` (P26 a P28, P38, P39)

---

## FASE 4 — M2 Cobra

> C-11 y C-19 podrían proponerse en paralelo una vez cerrado C-10, y C-12, C-13 y C-14 una vez cerrado
> C-11, si se resuelve P47 (ramas o turnos con dos desarrolladores). Hoy se trabaja de a un cambio por
> vez (`knowledge-base/14_forma_de_trabajo.md`).

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
- **Governance**: se declara en el propose (`openspec/config.yaml`)
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
- **Governance**: se declara en el propose (`openspec/config.yaml`)
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
- **Governance**: se declara en el propose (`openspec/config.yaml`)
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
  extraordinaria para propietarios y sólo ordinaria para inquilinos, comparación contra el mes
  anterior, descarga de PDFs según vínculo, app instalable (D-106)
- **Dependencias**: C-14, C-05b (el vecino tiene que poder entrar)
- **Governance**: se declara en el propose (`openspec/config.yaml`)
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §11
  - `knowledge-base/06_funcionalidades.md` §HU-V1 a HU-V5
  - `knowledge-base/05_reglas_de_negocio.md` §R16

---

### [C-17] `vista-del-consejo` · 12
- **Estado**: `[ ]` pendiente (HIGH)
- **Scope**: morosidad, gastos, liquidaciones y comprobantes en sólo lectura para consejo y contador
  según su alcance (D-106)
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
- **Governance**: se declara en el propose (`openspec/config.yaml`)
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
- **Governance**: se declara en el propose (`openspec/config.yaml`)
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
- **Dependencias**: C-05b, C-05c, C-06c, C-07d, C-12, C-13, C-17, C-18, C-19 (y todos los anteriores) + datos del edificio piloto (P1)
- **Governance**: se declara en el propose (`openspec/config.yaml`)
- **Leer antes**:
  - `knowledge-base/12_fichas_de_changes.md` §15
  - `knowledge-base/01_vision_y_objetivos.md` §Cómo se valida
  - `knowledge-base/10_preguntas_abiertas.md` (P1, P12)
