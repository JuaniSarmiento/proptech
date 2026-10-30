# Rompedor · verify · intento 3 (acotado a F7) · pulido-2 (3d)

- **Rol**: rompedor (subagente nativo de Claude). Intento 3.
- **Revisión**: `d15c610` (fix en `173089b`, tarea 11.6), diff `a4b4e53..d15c610`. Sólo cambian en código `web/e2e/api-falsa.ts` (+9) y `web/e2e/api-falsa.patch-georef.test.ts` (+2 tests).
- **Fecha**: 30/10/2026, 12:30 a 12:31 (-03:00). Sin commit; los mutantes se revirtieron desde una copia.
- **Fuentes**: el diff `a4b4e53..d15c610` de `web/`, `web/e2e/escenarios.ts` y `escenarios-escritura.ts` (ids), y `rg PATCH e2e/*.spec.ts`. **Contaminación**: ninguna; no leí la entrada nueva del informe del constructor.
- **Alcance**: no reabrí F1 a F6 ni las sospechas S1 a S4.

## EVIDENCIA

```
$ (web) npx vitest run e2e/api-falsa.patch-georef.test.ts e2e/api-falsa.test.ts
2026-10-30T12:30:59-03:00 · d15c610
base                                            Tests  64 passed (64)
C1  `if (… && !_UUID.test(id))` pasa a `if (false)`   Tests  1 failed | 63 passed   -> muerto (el test de F7)
C2  se quita `!_UUID.test(id)` (rechaza todo PATCH)    Tests  9 failed | 55 passed   -> muerto
C3  el chequeo se aplica a cualquier escritura          Tests  64 passed              -> sobrevive (ver JUICIO)
$ npx biome check e2e/api-falsa.ts e2e/api-falsa.patch-georef.test.ts -> No fixes applied.
```

## Lentes

- **Correctitud**: F7 cerrada. `PATCH /api/complejos/no-es-uuid` da 422 `uuid_parsing` en `path.complejo_id`, igual que la real (sonda del intento 2), y el test lo vigila (C1). Un UUID en mayúsculas se sigue aceptando, y C2 confirma que el chequeo no rechaza ids válidos.
- **Cableado**: el chequeo va después del Content-Type y del 405, y sólo para `PATCH` sobre el edificio. Los POST y los escenarios por id no cambian. Todos los ids de `escenarios.ts` y `escenarios-escritura.ts` son UUID con guiones (`rg` sin coincidencias que no lo sean), y ningún spec de Playwright manda `PATCH`. Nada vecino se rompe.
- **Verdad**: el comentario ("`complejo_id: UUID` en la real, igual que `grupo_id`") coincide con `complejos.py:342-344`.

## JUICIO

Autor: rompedor (Claude). Confianza alta. C3 sobrevive porque ningún test fija qué hace la falsa con un **POST** a `/api/complejos/{no-uuid}/…`. La real también lo rechazaría con 422, así que aplicar el chequeo a todas las escrituras sería *más* fiel: no es un defecto de F7, es un hueco previo al 3d, fuera del alcance de esta vuelta. Lo anoto, no lo cuento como falla.

## Fallas reproducidas

Ninguna.
