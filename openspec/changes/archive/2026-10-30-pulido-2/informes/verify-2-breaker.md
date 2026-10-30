# Rompedor · verify · intento 2 · pulido-2 (3d)

- **Rol**: rompedor (subagente nativo de Claude, role-breaker). Intento 2.
- **Revisión revisada**: `a4b4e53` (HEAD del worktree), diff `b1ec660..a4b4e53` (b5d7cbb 4.3, ef1d8e9 11.1 a 11.5, a4b4e53 docs). `backend/src` sin cambios en ese rango (`git diff --quiet`).
- **Fecha**: 30/10/2026, 12:26 a 12:28 (-03:00). Sin commit ni edición de producción; cada mutante se aplicó y se revirtió desde una copia.

## Fuentes leídas

- El diff `b1ec660..a4b4e53` de `web/e2e/api-falsa.ts`, `api-falsa.patch-georef.test.ts`, `ayuda.ts`, `ayuda.test.ts`, `ayuda.coherencia.test.tsx` y `specs/pantallas-del-edificio/spec.md`.
- `backend/src/proptech_api/complejos.py` (las 9 rutas citadas), `web/src/lib/api/cliente.ts` (`esIdValido`) y mi informe `verify-1-breaker.md`.
- Lecciones: las mismas del intento 1 (L-026, L-027, L-035, L-049 a L-052 de `knowledge-base/15_lecciones.md`); no las releí.

## Contaminación

- Leí el mensaje del orquestador con el resumen del informe del constructor (85/595, 9 citas, UUID sin guiones). **No** abrí `apply-1-constructor.md` ni `propose-2-plan-reviewer.md`. Todo lo de abajo lo verifiqué yo.

## Lo que no se ejecutó

- Suite completa (no la repetí), integración del backend (sin PostgreSQL), Playwright y navegador real. El contrato real lo saqué de una sonda con los modelos reales de `proptech_api` (FastAPI `TestClient`, sin base). `.venv` symlinkeado y borrado al terminar.

## EVIDENCIA

### E1 · Tests enfocados (verde) y Biome

```
$ (web) npx vitest run e2e/api-falsa.patch-georef.test.ts e2e/api-falsa.test.ts \
    "src/app/edificios/[id]/ayuda.test.ts" "src/app/edificios/[id]/ayuda.coherencia.test.tsx"
2026-10-30T12:27:37-03:00 · a4b4e53
 Test Files  4 passed (4)
      Tests  66 passed (66)
$ npx biome check (los 5 archivos web cambiados) -> Checked 5 files. No fixes applied.
```

### E2 · Mutantes sobre las correcciones (2026-10-30T12:26:58-03:00, a4b4e53)

| id | qué cierra | mutación | tests | resultado |
|---|---|---|---|---|
| B1 | F1 grupo | se quita el 422 por cuerpo vacío | api-falsa (62) | muerto (1 falla) |
| B2 | F1 edificio | `if (metodo === "PATCH" && cuerpo === "")` pasa a `if (false)` | ídem | muerto (1) |
| B3 | F2 | se quita el chequeo `_UUID` | ídem | muerto (1) |
| B4 | F2 | `_UUID` sin `/i` | ídem | muerto (1, el de mayúsculas) |
| B5 | F3 | `50028010` vuelve a "Godoy Cruz" | ídem | muerto (1) |
| B6 | F3 | `50028010` colgada de `50007` | ídem | muerto (1, chequeo del padre) |
| B7 | F5 | se anula la rama PATCH del edificio (era A1, sobrevivía) | ídem | **muerto** (1) |
| B8 | F4 | la ayuda vuelve a "arranca en 0 de 7" | ayuda.test + coherencia (4) | muerto (2) |
| B9 | F4 | "queda en 5 de 7" | ídem | muerto (1) |

### E3 · Las 9 citas de `complejos.py` (F6)

`rg` sobre `complejos.py` en a4b4e53: 318 `resumen_edificio`, 342 `modificar_edificio`, 363 `ver_complejo`, 423 `alta_unidad`, 485 `alta_grupo`, 506 `modificar_grupo` (citado dos veces), 556 `alta_categoria`, 612 `vigente_del_edificio` y 635 `alta_version`. Cada número apunta al decorador `@router.*` y la línea siguiente es el `def` con ese nombre. Las 9 son correctas y no queda ninguna cita vieja en `web/e2e` ni en `web/src`.

### E4 · Sonda de la real (2026-10-30T12:26:26-03:00)

```
grupo sin guiones (1c9d…c10)            -> 200 {"id":"1c9d6f7e-0b0e-…"}
grupo urn:uuid:…                         -> 200
grupo {…} con llaves                     -> 200
grupo en MAYÚSCULAS                      -> 200 {"id":"1c9d6f7e-…"}   (id devuelto en minúsculas)
grupo no-es-uuid y sin cuerpo            -> 422 [uuid_parsing path.grupo_id, missing body]
edificio /api/complejos/no-es-uuid       -> 422 [uuid_parsing path.complejo_id]
```

La falsa, con la misma entrada (sonda temporal 12:26:37): sin guiones da **422**; mayúsculas da 200 con `{"id":"1C9D…"}` (en mayúsculas); no-uuid y sin cuerpo da 422 con un solo error; `PATCH /api/complejos/no-es-uuid` da **200**.

### E5 · Test que dejo fallando (sin commit)

```
$ (web) npx vitest run e2e/api-falsa.rompedor-3d-v2.test.ts
2026-10-30T12:27:52-03:00 · a4b4e53
   × RB3D-7: PATCH /api/complejos/no-es-uuid da 422 uuid_parsing en el path
AssertionError: expected 200 to be 422
      Tests  1 failed (1)
```

## Lente 1 · Correctitud

- F1, F2, F3 y F5 están cerradas, y cada una la vigila un test que mata su mutante (B1 a B7).
- **F7 (reproducida, BAJA) · `PATCH /api/complejos/{id}` con un id que no es UUID: la falsa da 200, la real 422 `uuid_parsing`.** Es el mismo caso que F2, pero en la otra ruta PATCH que agregó el 3d; la corrección sólo cubrió `/grupos`. En el intento 1 no probé esta ruta, así que no es una regresión del intento 2: es un hueco que quedó. Hoy la web no lo alcanza (`esIdValido` filtra antes de pedir). Test: RB3D-7 (E5).
- **UUID sin guiones (divergencia nueva, declarada; JUICIO, no la cuento como falla).** La real acepta sin guiones, con `urn:uuid:` y con llaves; la falsa los rechaza con 422 (E4). El comentario de `_UUID` lo declara a propósito, y la web no puede mandar esas formas: `esIdValido` (`cliente.ts:27`) exige el formato con guiones, igual que `_UUID`. No hay consumidor que lo alcance. Si se acepta, que quede como decisión.
- **Fidelidad menor (JUICIO, sin falla)**: con un UUID en mayúsculas, la real devuelve el id en minúsculas y la falsa lo devuelve tal como llegó. Con path inválido y cuerpo vacío, la real lista 2 errores y la falsa 1. Ningún consumidor depende de eso hoy.

## Lente 2 · Cableado

- Las correcciones no tocan rutas existentes: el 422 por cuerpo vacío se limita a `PATCH` (los POST conservan su forma, lo confirma `api-falsa.test.ts` en verde, E1), y el chequeo de UUID se limita a la rama `/api/grupos/{id}`. `esIdValido` y `_UUID` usan el mismo formato, así que la falsa no rechaza nada que la web mande. Las rutas nuevas siguen sin un consumidor de Playwright (2.5, declarado en el intento 1).

## Lente 3 · Verdad

- **F4 cerrada.** La ayuda dice "arranca en 4 de 7 … queda en 6 de 7". Lo comparé con `lectura.py:250-264`: un edificio recién creado tiene ubicación, grupos, categorías e intereses hechos (4); con unidades que tienen piso y coeficientes en ok se suman unidades y coeficientes (6); saldos previos sigue en falta. La spec corregida dice lo mismo y declara como deuda la sincronía automática. `ayuda.coherencia.test.tsx` compara la ayuda con la barra renderizada a partir de los `pasos` de la API real (mata B8). El "6 de 7" sólo lo fija el texto (B9 lo mata `ayuda.test.ts`), sin comparación con un render; así lo declara la spec.
- **F6 cerrada**, con las 9 citas verificadas (E3).

## Conteo propio

- Verde: 66 tests en 4 archivos (E1).
- Mutantes: 9, todos muertos (E2).
- Sondas: 6 pedidos a la real (E4) y 3 a la falsa (E4, sonda borrada).
- Test nuevo que falla: 1 (RB3D-7).

## SUPOSICIÓN

- Nada nuevo. S1 a S4 del intento 1 siguen igual (no las reabrí).

## JUICIO

Autor: rompedor (Claude, intento 2). Confianza alta: F1 a F6 cerradas con tests que vigilan (9 de 9 mutantes muertos) y las 9 citas son correctas. Queda un hueco del mismo tipo que F2 en la ruta del edificio (F7, BAJA). No reemplaza al auditor.

## Fallas reproducidas

1. **F7** (BAJA): `PATCH /api/complejos/no-es-uuid` da 200 en la falsa y 422 `uuid_parsing` en la real. Test `web/e2e/api-falsa.rompedor-3d-v2.test.ts` (RB3D-7).
