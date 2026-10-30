## Context

Ver `proposal.md` (por qué y qué). Estado de partida, verificado en el repo (HEAD `5c6d84c`):

- `web/e2e/api-falsa.ts` (915 líneas) valida cada escritura contra `_CONTRATO_DE_ESCRITURA` (tipos y
  opcionales por ruta y método). Las rutas de `PATCH` del 3c no figuran, y un método no declarado cae
  en un `405` (~línea 831). Ese archivo lo usa también el 6 (Emiliano).
- `vocabularioDePisos(pisos, subsuelos)` (`web/src/lib/pisos.ts`) arma `["PB", 1..N, SS1..SSn]`. El
  único consumidor que fija el orden es el test de `unidades/Pantalla.test.tsx:511-531`.
- `web/src/proxy.ts` aplica la política de Clerk y después le saca `'unsafe-inline'` y `'unsafe-eval'` a
  `script-src` (tanto en la respuesta como en la cabecera que Next lee para el nonce).
  `web/e2e/csp.spec.ts` ya prueba la política completa contra Next real; `proxy.test.ts` sólo cubre
  el token.
- El backend acota `dia_de_vencimiento` a `1..28` (`dominio/configuracion.py:24`); la web tiene
  `max={28}` en los dos campos de día (`configuracion/Pantalla.tsx:167,191`).

## Goals / Non-Goals

**Goals:**
- Que cada comportamiento del 3c que hoy no tiene regresión de navegador la tenga, con una API falsa
  que rechaza lo que la real rechazaría (L-027).
- Que ningún test certifique un comportamiento incorrecto como esperado.

**Non-Goals:**
- Tocar código de producción del backend o `acceso`.
- Rediseñar la raíz `/` como portal o landing.
- Reescribir `api-falsa.ts` fuera de las rutas nuevas.

## Decisions

1. **Orden de pisos: de altura, `SS<n>`…`SS1`, `PB`, `1`…`N`.** Decisión de Gianfranco (28/10/2026).
   Razón: es como se ordena un edificio de abajo hacia arriba, y deja `SS1` pegado a `PB`, que es lo
   que pedía la ficha con "SS1 arriba de PB". *Alternativas*: dejar `PB, 1…N, SS1…SSn` (el actual, que
   es lo que la ficha lista en su "Terminado cuando"); `SS1…SSn, PB, 1…N` (subsuelos ascendentes, que
   deja `SS1` lejos de `PB`). Se implementa sólo en la web; el vocabulario de valores válidos (backend)
   no cambia. El test usa 2 subsuelos porque con uno el orden no se distingue.
2. **`api-falsa.ts`: se agregan los `PATCH` al mismo contrato declarativo.** Cada ruta nueva entra con
   su esquema de campos, igual que las existentes, en vez de un atajo "aceptar todo". Georef se simula
   con una respuesta fija chica (no con el archivo real) para que el e2e no dependa de `config/georef/`.
   *Alternativa descartada*: mock por pedido dentro de cada spec de Playwright; reparte la simulación en
   muchos archivos y repite el problema de L-027.
3. **Raíz `/`: redirect.** Es la propuesta mínima que cumple "deja de ser un placeholder" sin inventar un
   producto. Es una decisión abierta, ver proposal; no entra a `tasks.md` hasta que Juani la confirme
   (tarea 2.1 la deja explícita).
4. **CSP: un test unitario del post-proceso de `proxy.ts`, no otro e2e.** El e2e ya existe. Lo que no
   tiene cobertura es el filtro que quita `'unsafe-inline'`, que es lógica propia nuestra y no de Clerk;
   un test unitario lo verifica sin levantar Next.
5. **axe por estado: se parametriza, no se copia.** Se reutiliza el helper `sinViolaciones` que ya usan
   las pantallas que lo hacen bien, con una lista de estados por pantalla (L-051: la clase, no el caso).
6. **Día 29 a 31: la primera tarea decide el alcance.** Hay cobertura parcial; la tarea confirma qué falta
   antes de escribir la prueba. No se cambia código de producción del backend.

## Risks / Trade-offs

- **[Choque con Emiliano en `api-falsa.ts`]** → Avisar antes de tocar; subir esos cambios en un commit
  aparte y primero; rebasear sobre lo que él haya subido.
- **[Redirect de `/` mal pensado]** → Es la única decisión de producto del change; queda como pregunta
  abierta y la tarea correspondiente no arranca sin respuesta.
- **[Un e2e verde en Windows no prueba nada]** → L-050: el juez es el job `web` del CI. Los e2e se
  corren localmente sólo como señal.
- **[Que cambiar el orden rompa otro consumidor de `vocabularioDePisos`]** → Primera tarea: buscar
  todos los usos con `rg` antes de tocar nada.
- **[La ficha de 3d tiene datos viejos (CSP, día 31)]** → Ya anotados en el proposal; si aparece otra
  discrepancia, se anota en el informe del constructor, no se resuelve por criterio propio.

## Open Questions

- **Qué muestra la raíz `/`** (decisión de producto, Juani). Mientras no responda, la tarea 2.1 queda
  bloqueada y el resto del change sigue.
- **Si el segundo vencimiento tiene su propio tope en el backend** (el archivo acota el primero a
  `1..28`; el segundo se compara contra él). Se verifica en la tarea 5.1.
