# PropTech

Plataforma para administrar edificios en propiedad horizontal (y después barrios privados) en
Mendoza: liquidación de expensas, cuenta corriente de cada unidad, registro de pagos y portal del
vecino. Proyecto de Alberto Cortez (también conocido como **koris**) y Juan Ignacio Sarmiento.

## Estado

Diseño del MVP cerrado, sin código todavía (octubre de 2026). El MVP arranca por **edificios**.

## Estructura

| Carpeta | Qué tiene |
|---|---|
| [`conocimiento/`](conocimiento/) | **La base de conocimiento del MVP**: objetivo, historias de usuario, reglas de negocio, decisiones, glosario y fases. Es la fuente de verdad: empezá por su [README](conocimiento/README.md) |
| `config/` | Parámetros iniciales del sistema (próximamente) |
| `openspec/` | Cambios del ciclo OPSX (próximamente) |
| `web/` | Frontend en Next.js (próximamente) |
| `backend/` | API en FastAPI, worker y dominio compartido (próximamente) |
| `infra/` | Docker Compose, Caddy y backups (próximamente) |

La estructura completa y su porqué están en la decisión D-040 de
[`conocimiento/decisiones.md`](conocimiento/decisiones.md).

## Cómo se trabaja

1. Nada se programa sin estar escrito antes en `conocimiento/` y en un cambio de OPSX.
2. El núcleo financiero se construye con TDD: cada regla de
   [`reglas-de-negocio.md`](conocimiento/reglas-de-negocio.md) tiene sus tests antes que el código.
3. Si algo contradice la base de conocimiento, se para y se decide: una decisión nueva en
   `decisiones.md`, nunca una edición de una vieja.

## Stack

Next.js · FastAPI · PostgreSQL con Row-Level Security · Redis con worker · Caddy · Docker en un VPS.
