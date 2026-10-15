# PropTech — Instrucciones para Agentes

> Este archivo (y su copia `AGENTS.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a mano a partir de `knowledge-base/` y `CHANGES.md` (Active Stack v1, D-093). No editar
> uno sin editar el otro: tienen que quedar idénticos (`diff AGENTS.md CLAUDE.md` vacío).

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados):
liquidación de expensas, cuenta corriente, pagos y portal del vecino. Proyecto con Alberto Cortez y
sus hijos; lo programaba Juani solo (D-022) y desde el 14/10/2026 Alberto también construye cambios propios
sobre este mismo repositorio con Active Stack v1 (D-093). El comprador es el **administrador**; el
mercado de arranque es **Mendoza**.

> Estado y avances del proyecto se registran en `knowledge-base/` (decisiones) y en la nota personal
> de Juani (`obsidian.md`, symlink local, fuera del repo).

## Estado

- **Cambio 1a `infraestructura-base` archivado** (09/10/2026): el proyecto levanta con
  `cd infra && docker compose up --build` (ver README), con CI en GitHub Actions. Todavía no hay
  dominio: sólo el esqueleto y `/api/salud`.
- **Cambio 1b `arranque-del-sistema` archivado** (11/10/2026): configuración, `Dinero`, parámetros y semilla validada.
- **Cambio 1c `cola-logs-y-respaldos` archivado** (14/10/2026): Redis, worker ARQ con reintentos e
  idempotencia, logs estructurados en JSON, número de seguimiento (`request_id`) de punta a punta,
  `/api/salud` con la cola y `/salud-web`. Cerrado con **OK con deuda anotada** (D-091); la deuda
  queda en `knowledge-base/12_fichas_de_changes.md` ("Deuda técnica de las auditorías del 13/10"), con dueño por
  ítem (mayormente el cambio 7, antes de su primera tarea real).
- **Cambio 1d `respaldos-y-restauracion` archivado** (14/10/2026): servicio `respaldos` con `pg_dump`
  al arrancar y a diario, 14 copias, salud por antigüedad; `restaurar.sh` con destino validado; humo
  ampliado (Redis, worker, `request_id`, backup, restauración); `shellcheck` en el CI. Cerrado con
  **OK con deuda anotada** en la vuelta 3 (D-095); la deuda queda en
  `knowledge-base/12_fichas_de_changes.md` ("Deuda del cierre del 1d"), con dueño por ítem (mayormente
  el cambio 15 y el cambio 2).
- **Próximo**: cambio 2 `acceso-y-aislamiento` (CRITICAL, explore propio); ya no está bloqueado por P18
  ni P23, resueltas el 15/10/2026 en D-096 (una cuenta por administración; permisos por acción).
  Antes de cada cambio, constructor y rompedor leen `knowledge-base/15_lecciones.md`.
- Preguntas abiertas (la lista P, completa en `knowledge-base/10_preguntas_abiertas.md`): el edificio piloto (P1), el precio (P8), los
  extractos de Mendoza (P9), el modo de redondeo (P10), el cambio de titular (P11), la inscripción
  ante la AAIP (P12), el acceso de soporte (P13), el plazo del libre deuda (P14), los ingresos mayores que los gastos
  (P15), la parte de las unidades del consorcio (P16), el IVA (P17), el doble vencimiento (P19), quién
  aprueba una condonación (P20), los umbrales de R23 y R30 (P21) quién usa el editor de reglas (P22),
  los casos de borde para decidir antes de su cambio (P24 a P41), la validación de los valores de
  plata (P42), el contenido derivado de ProTecc (P43), la licencia (P44), las entrevistas a
  administradores (P45) y los nombres propios en el repo (P46), ramas o turnos con dos desarrolladores
  (P47). P18 y P23 se resolvieron en D-096.

## Stack Tecnológico

- **Backend**: Python + FastAPI + SQLAlchemy + PostgreSQL, migraciones con Alembic. Redis + worker ARQ
  para PDFs, emails e IA (D-038).
- **Frontend**: Next.js (App Router) + TypeScript, áreas de titular/colaborador, consejo y vecino,
  instalable como PWA. El servidor de Next guarda el token; el navegador nunca lo ve (D-036). Sin app nativa. Toda interfaz pasa por la skill **impeccable**.
- **Monolito modular** (D-040): `backend/src/proptech_core` con los módulos `complejos`, `acceso`,
  `gastos`, `liquidacion`, `cuenta_corriente`, `pagos`, `avisos`, `politicas` (el motor de reglas,
  `knowledge-base/13_motor_de_reglas.md`) y `compartido`, cada uno con
  `dominio/` (reglas puras) · `aplicacion/` (casos de uso) · `puertos.py` · `adaptadores/`. Lo usan
  `proptech_api` (routers FastAPI) y `proptech_worker` (tareas). Los módulos se hablan sólo por
  `aplicacion`. Frontend en `web/`, despliegue en `infra/`.
- **Puerto de políticas** (D-064): las reglas propias de cada edificio entran por un puerto en
  `proptech_core` que devuelve acciones propuestas; el núcleo valida y registra. En el MVP se
  implementa con GoRules ZEN y su editor visual (D-066): el motor devuelve la plata como texto, el
  núcleo redondea y registra (D-067), y un validador propio bloquea la emisión ante cualquier
  respuesta fuera de contrato.
- **Tests**: unitarios (reglas, sin base), integración (PostgreSQL real en Docker), aceptación
  (la liquidación del piloto al centavo).
- **Despliegue**: VPS con Docker y Caddy (D-043). PDFs con WeasyPrint, avisos por email.
- **Parámetros iniciales** en `config/parametros.yaml` (D-042), nunca escritos en el código.
- **Criterio de costo**: ante dos opciones equivalentes, la que no cobra licencia ni uso (D-043).
- Detalle completo, con las versiones exactas tomadas del código:
  `knowledge-base/02_descripcion_general.md`.

## Base de Conocimiento

**La fuente de verdad es `knowledge-base/`.** Todo lo que se construye sale de ahí. Esta carpeta es
el repositorio del proyecto, **público**: https://github.com/JuaniSarmiento/proptech. Nunca
subir secretos, datos personales ni el material de Alberto (`especificacion/` está en `.gitignore`).

| Archivo | Qué tiene | Cómo se actualiza |
|---|---|---|
| `knowledge-base/01_vision_y_objetivos.md` | Propósito, objetivos por actor, alcance, hitos M1 a M3, diferencias con la spec | Se reescribe |
| `knowledge-base/02_descripcion_general.md` | Stack, arquitectura general, integraciones externas | Se reescribe |
| `knowledge-base/03_actores_y_roles.md` | Actores, RBAC (acciones por rol según D-096), rutas públicas | Se reescribe |
| `knowledge-base/04_modelo_de_datos.md` | Dominios, ERD (existente y planificado), entidades y seed data | Se reescribe |
| `knowledge-base/05_reglas_de_negocio.md` | R01 a R41 (agrupadas por dominio, estado vigente, propuesta o pendiente): prorrateo, estados, intereses, imputación, redondeo, pagos, facturas, ordinaria/extraordinaria, cargos particulares, fondo de reserva, categorías de gasto. **Cada regla vigente es un test** | Se reescribe |
| `knowledge-base/06_funcionalidades.md` | Historias de usuario (HU-\*) por épica, con criterios de aceptación y reglas relacionadas | Se reescribe |
| `knowledge-base/07_flujos_principales.md` | Flujos extremo a extremo, con sus casos de error | Se reescribe |
| `knowledge-base/08_arquitectura_propuesta.md` | Patrones, estructura de directorios, seguridad y variables de entorno | Se reescribe |
| `knowledge-base/09_decisiones_y_supuestos.md` | D-001 en adelante, con lo descartado y el porqué; supuestos (SU) | **Sólo se agrega** |
| `knowledge-base/10_preguntas_abiertas.md` | Inconsistencias (IN) y preguntas abiertas (P1 a P47), con la sección "Para Alberto" | Se reescribe |
| `knowledge-base/11_glosario.md` | El idioma común. El código usa estos nombres, en español | Se reescribe |
| `knowledge-base/12_fichas_de_changes.md` | El detalle de cada cambio del roadmap (objetivo, reglas, dependencias, qué prueba el rompedor) | Se reescribe |
| `knowledge-base/13_motor_de_reglas.md` | El puerto de políticas (D-064) y GoRules ZEN con editor visual y validador propio (D-066, D-067): contrato, qué hace bien ZEN y su riesgo real, versiones, fallas y dónde entra en el roadmap | Se reescribe |
| `knowledge-base/14_forma_de_trabajo.md` | **Cómo construye Juani cada cambio**: constructor, rompedor y auditor en secuencia; aprueba el auditor | Se reescribe |
| `knowledge-base/15_lecciones.md` | Lo que cada cambio enseñó sobre cómo se rompe el sistema; lo leen constructor y rompedor antes de empezar | **Sólo se agrega** |
| `knowledge-base/16_proyecto_final.md` | Fases posteriores al MVP con su criterio de entrada | Se reescribe |
| `CHANGES.md` | **Los 20 cambios en orden, con su estado**: arrancá cada propose desde ahí y desde la ficha de `12_fichas_de_changes.md` | Se reescribe |

Si algo que vas a hacer contradice uno de estos archivos, **pará y preguntale a Juani (o a Alberto,
si el cambio es de él)**. Si cambia una decisión, se escribe una decisión nueva; nunca se edita una
vieja.

`especificacion/` es el material de partida (19 módulos, un análisis con 48 observaciones y
`arquitectura-alberto/`, el documento de arquitectura de Alberto). Es
**insumo, no verdad**: cuando contradice a `knowledge-base/`, gana `knowledge-base/`. El código
original de la especificación se descartó (D-002) y no se usa.

> ⚠️ Resolver las preguntas de prioridad alta de `knowledge-base/10_preguntas_abiertas.md` (P1, P9 a
> P11, P19, entre otras) antes de arrancar un cambio que dependa de ellas: cada ficha de
> `12_fichas_de_changes.md` dice "Bloqueado por" con las que le tocan.

## Skills Disponibles

Este repositorio **no versiona `.atl/skill-registry.md`**: la skill `skill-registry` se puede correr
(sólo escribe `.atl/`, que está en `.gitignore`). Cada agente resuelve sus skills desde `.claude/skills/` del repo (las
`openspec-*` generadas por `openspec init` en su momento) y desde `~/.claude/skills/` de su propia
máquina.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend** | FastAPI / SQLAlchemy / Alembic / dominio hexagonal | `fastapi-templates` o equivalente, `test-driven-development`, `postgresql-optimization` |
| **Frontend** | Next.js / TypeScript / PWA | `typescript-advanced-types`, `tailwind-design-system` o la que use el proyecto, **impeccable** para toda interfaz |
| **Motor de reglas** | GoRules ZEN / jdm-editor | sin skill dedicada hoy; ver `knowledge-base/13_motor_de_reglas.md` |
| **Orquestación** | OPSX / changes | `openspec-explore`, `openspec-propose`, `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change` (versionadas en `.claude/skills/` de este repo, openspec 1.13.0) |

Cargá la skill correspondiente al contexto ANTES de escribir código.

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md), con el detalle de cada cambio
en [knowledge-base/12_fichas_de_changes.md](knowledge-base/12_fichas_de_changes.md). Resumen:

- **Total**: 20 cambios (D-088), repartidos en M1 Liquida, M2 Cobra y M3 Piloto.
- **Camino crítico a M1** (reproducir al centavo la última liquidación del piloto):
  `1a → 1b → 1c → 1d → 2 → 3 → 4 → 5 → 6 → 7`.
- **Archivados**: 1a `infraestructura-base`, 1b `arranque-del-sistema`, 1c `cola-logs-y-respaldos`, 1d
  `respaldos-y-restauracion`.
- **Próximo**: 2 `acceso-y-aislamiento` (CRITICAL); P18 y P23 se resolvieron en D-096, así que se puede
  proponer.

**Antes de cualquier `/opsx:propose`**: leé `CHANGES.md`, identificá las dependencias del cambio y los
archivos de "Leer antes" de su ficha en `knowledge-base/12_fichas_de_changes.md`.

## Reglas Duras

> Reglas **globales** ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram):
> el proyecto las **hereda**, no se repiten acá.

**Qué no se corre nunca en este repositorio** (D-093): la base ya existe, está escrita a mano y
tiene meses de decisiones y un roadmap de 20 cambios. Correr cualquiera de estas herramientas de
fundación la pisa o la regenera con contenido que no es el nuestro:

- `active-orchestrator`: **tampoco elegir "Regenerar"** si en algún momento lo pregunta. Si la
  detección de fundación dice que falta algo, la respuesta es "ya existe, no lo toques", nunca
  invocar la skill.
- `kb-creator`, `roadmap-generator`, `agent-instruction`: generarían `knowledge-base/`, `CHANGES.md`
  y este mismo archivo desde cero, pisando el trabajo ya hecho.
- `openspec init`: el repositorio ya tiene `openspec/` inicializado.
- `openspec update`: reescribe `.claude/skills/openspec-*` y `.claude/commands/opsx/*` con la
  versión de openspec que esté instalada, que puede no coincidir con la fijada acá.

**openspec fijado en 1.13.0**: instalar con `npm install -g @fission-ai/openspec@1.13.0`, sin rango
abierto. No instalar la última versión de npm sin verificar antes que coincide.

**Gobernanza CRITICAL y HIGH, a cargo de cualquiera de los dos socios** (D-094): la propuesta de un
cambio CRITICAL o HIGH la aprueba **Juani o Alberto**, dejándolo por escrito y con fecha en la
propuesta. No hace falta que apruebe el que no programa ese cambio puntual.

- **La plata nunca pasa por una cuenta de PropTech** (D-005). En el MVP no hay pagos integrados:
  el vecino informa con su comprobante y el administrador confirma (D-017, R11).
- **Cobros y cuenta corriente son dominio CRITICAL** (governance global): se propone y se espera
  aprobación de uno de los dos socios antes de escribir código ahí.
- **Base congelada** (D-087, D-089): nada de R42 en adelante y la base no se reabre salvo por hallazgos
  del código o respuestas a las preguntas abiertas.
- **TDD estricto en el núcleo**: cada regla vigente tiene sus tests mínimos escritos en
  `knowledge-base/05_reglas_de_negocio.md`; se ven fallar antes de escribir el código.
- **Montos en `Decimal`** (desde texto), `NUMERIC(14,2)` en la base y texto en el JSON; nunca `float`;
  el frontend no calcula montos; reparto por mayor resto (R07, D-046).
- **La cuenta corriente sólo agrega movimientos**; una corrección es un movimiento nuevo con motivo (R08).
- **La administración sale del login**, nunca de un parámetro del cliente: es el tenant, y Row-Level
  Security es el segundo candado. El edificio es un alcance dentro de ella, controlado por rol (R10, D-076).
- **Intereses simples**, sin capitalización (art. 770 del CCyC) (R03).
- **Nunca secretos ni datos personales reales en el repo.** Los comprobantes y facturas de prueba
  se arman con datos inventados.
- Juani trabaja en español rioplatense; nada de `cat/grep/find/sed/ls` (usar `bat/rg/fdfind/sd/eza`).

## Flujo de Trabajo

Dos ciclos conviven sobre el mismo repositorio y la misma base; los dos terminan en `openspec
archive` y una actualización de `knowledge-base/` según su sección "Knowledge Base Impact":

**El de Alberto, ciclo OPSX de Active Stack v1**:

```
1. Leer la KB relevante (knowledge-base/) y CHANGES.md   → entender el dominio y las dependencias
2. /opsx:explore (si el cambio lo pide, ⓔ en 01)          → pensar antes de proponer
3. /opsx:propose <nombre-del-change>                      → proposal + design + specs + tasks
4. /opsx:apply                                            → implementar con TDD estricto
5. /opsx:verify                                           → chequear contra specs, tasks y design
6. /opsx:archive <nombre-del-change> + marcar [x] en CHANGES.md
```

**El de Juani, constructor/rompedor/auditor en secuencia** (detalle completo en
`knowledge-base/14_forma_de_trabajo.md`):

```
1. Proponer ──► 2. Construir (TDD) ──► 3. Romper ──► 4. Auditar ──► 5. Archivar (commit + push)
```

El proponente escribe `proposal.md`/`design.md`/`tasks.md`; el constructor implementa con TDD
estricto; el rompedor intenta romperlo y deja cada falla como un test; el auditor da el veredicto
final (**OK** o **NO con motivos**) y un cambio queda aprobado cuando lo da. Los cambios CRITICAL o
HIGH llevan además la aprobación escrita de uno de los dos socios antes de codear (D-094).

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas
duras prevalecen.

## Investigación de mercado

El informe "Discovery Kooris Mendoza" (octubre de 2026, fuera del repo). **Kooris (o koris) es este mismo
proyecto** (D-035), así que el informe aplica directo: ~150 barrios y ~20 administradores en la
Cámara de Mendoza, 75.124 departamentos ocupados en el Gran Mendoza (Censo 2022), líderes
nacionales a ARS 2.950 por unidad, **AccessIN** como competidor mendocino en barrios.
