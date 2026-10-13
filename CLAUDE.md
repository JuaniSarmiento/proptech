# CLAUDE.md · PropTech

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados):
liquidación de expensas,
cuenta corriente, pagos y portal del vecino. Proyecto con Alberto Cortez y sus hijos; **Juani lo
programa solo** (D-022). El comprador es el **administrador**; el mercado de arranque es **Mendoza**.

> Estado y avances del proyecto se registran en `conocimiento/` (decisiones) y en la nota personal
> de Juani (`obsidian.md`, symlink local, fuera del repo).

---

## Leé esto antes de tocar nada

**La fuente de verdad es `conocimiento/`.** Todo lo que se construye sale de ahí. Esta carpeta es
el repositorio del proyecto, **público**: https://github.com/JuaniSarmiento/proptech. Nunca
subir secretos, datos personales ni el material de Alberto (`especificacion/` está en `.gitignore`).

| Archivo | Qué tiene | Cómo se actualiza |
|---|---|---|
| `conocimiento/mvp.md` | Objetivo, usuarios, historias con criterios de aceptación, alcance, hitos M1 a M3, diferencias con la spec | Se reescribe |
| `conocimiento/reglas-de-negocio.md` | R01 a R41 (con estado vigente, propuesta o pendiente): prorrateo, estados, intereses, imputación, redondeo, pagos, facturas, ordinaria/extraordinaria, cargos particulares, fondo de reserva, categorías de gasto. **Cada regla es un test** | Se reescribe |
| `conocimiento/decisiones.md` | D-001 en adelante, con lo descartado y el porqué; preguntas abiertas al final | **Sólo se agrega** |
| `conocimiento/glosario.md` | El idioma común. El código usa estos nombres, en español | Se reescribe |
| `conocimiento/proyecto-final.md` | Fases posteriores al MVP con su criterio de entrada | Se reescribe |
| `conocimiento/roadmap.md` | **Los 18 cambios en orden**, con la ficha de cada uno: arrancá cada propose desde su ficha | Se reescribe |
| `conocimiento/motor-de-reglas.md` | El puerto de políticas (D-064) y GoRules ZEN con editor visual y validador propio (D-066, D-067): contrato, qué hace bien ZEN (calcula con decimales exactos) y su riesgo real (tablas que caen en silencio a la fila por defecto), versiones, fallas y dónde entra en el roadmap | Se reescribe |
| `conocimiento/forma-de-trabajo.md` | **Cómo se hace cada cambio**: vos orquestás; constructor, rompedor y auditor en secuencia; aprueba el auditor | Se reescribe |
| `conocimiento/lecciones.md` | Lo que cada cambio enseñó sobre cómo se rompe el sistema; lo leen constructor y rompedor antes de empezar | **Sólo se agrega** |

Si algo que vas a hacer contradice uno de estos archivos, **pará y preguntale a Juani**. Si
cambia una decisión, se escribe una decisión nueva; nunca se edita una vieja.

`especificacion/` es el material de partida (19 módulos, un análisis con 48 observaciones y
`arquitectura-alberto/`, el documento de arquitectura de Alberto). Es
**insumo, no verdad**: cuando contradice a `conocimiento/`, gana `conocimiento/`. El código
original de la especificación se descartó (D-002) y no se usa.

## Estado

- **Cambio 1a `infraestructura-base` archivado** (09/10/2026): el proyecto levanta con
  `cd infra && docker compose up --build` (ver README), con CI en GitHub Actions. Todavía no hay
  dominio: sólo el esqueleto y `/api/salud`.
- **Cambio 1b `arranque-del-sistema` archivado** (11/10/2026): configuración, `Dinero`, parámetros y semilla validada.
- **Próximo**: cambio 1c `cola-logs-y-respaldos` (ya propuesto, en `openspec/changes/`). Antes de cada cambio,
  constructor y rompedor leen `conocimiento/lecciones.md`.
- Preguntas abiertas (al final de `decisiones.md`): el edificio piloto (P1), el precio (P8), los
  extractos de Mendoza (P9), el modo de redondeo (P10), el cambio de titular (P11), la inscripción
  ante la AAIP (P12), el acceso de soporte (P13), el plazo del libre deuda (P14), los ingresos mayores que los gastos
  (P15), la parte de las unidades del consorcio (P16), el IVA (P17) y el vecino con unidades en dos
  administraciones (P18).

## Reglas que no se negocian

- **La plata nunca pasa por una cuenta de PropTech** (D-005). En el MVP no hay pagos integrados:
  el vecino informa con su comprobante y el administrador confirma (D-017, R11).
- **Cobros y cuenta corriente son dominio CRITICAL** (governance global): se propone y se espera
  aprobación de Juani antes de escribir código ahí.
- **TDD estricto en el núcleo**: cada regla vigente (R01 a R41) tiene sus tests mínimos escritos en
  `reglas-de-negocio.md`; se ven fallar antes de escribir el código.
- **Montos en `Decimal`** (desde texto), `NUMERIC(14,2)` en la base y texto en el JSON; nunca `float`;
  el frontend no calcula montos; reparto por mayor resto (R07, D-046).
- **La cuenta corriente sólo agrega movimientos**; una corrección es un movimiento nuevo con motivo (R08).
- **La administración sale del login**, nunca de un parámetro del cliente: es el tenant, y Row-Level
  Security es el segundo candado. El edificio es un alcance dentro de ella, controlado por rol (R10, D-076).
- **Intereses simples**, sin capitalización (art. 770 del CCyC) (R03).
- **Nunca secretos ni datos personales reales en el repo.** Los comprobantes y facturas de prueba
  se arman con datos inventados.
- Juani trabaja en español rioplatense; nada de `cat/grep/find/sed/ls` (usar `bat/rg/fdfind/sd/eza`).

## Stack y arquitectura (D-020, D-021)

- **Backend**: Python + FastAPI + SQLAlchemy + PostgreSQL, migraciones con Alembic. Redis + worker ARQ
  para PDFs, emails e IA (D-038).
- **Frontend**: Next.js (App Router) + TypeScript, áreas de titular/colaborador, consejo y vecino,
  instalable como PWA. El servidor de Next guarda el token; el navegador nunca lo ve (D-036). Sin app nativa. Toda interfaz pasa por la skill **impeccable**.
- **Monolito modular** (D-040): `backend/src/proptech_core` con los módulos `complejos`, `acceso`,
  `gastos`, `liquidacion`, `cuenta_corriente`, `pagos`, `avisos`, `politicas` (el motor de reglas,
  `motor-de-reglas.md`) y `compartido`, cada uno con
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

## Investigación de mercado

El informe "Discovery Kooris Mendoza" (octubre de 2026, fuera del repo). **Kooris (o koris) es este mismo
proyecto** (D-035), así que el informe aplica directo: ~150 barrios y ~20 administradores en la
Cámara de Mendoza, 75.124 departamentos ocupados en el Gran Mendoza (Censo 2022), líderes
nacionales a ARS 2.950 por unidad, **AccessIN** como competidor mendocino en barrios.
