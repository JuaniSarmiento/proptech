/**
 * axe en el navegador real (D7, tarea 5.1): SIN `@axe-core/playwright`
 * (D7 lo pide explícito) — se inyecta el script de `axe-core` ya instalado
 * (`node_modules/axe-core/axe.min.js`, misma versión que ya usa
 * `lib/test/accesibilidad.ts` en jsdom) y se corre `axe.run()` adentro de
 * la página. A diferencia de jsdom, acá SÍ hay layout real: el contraste
 * de color (`color-contrast`) entra en la corrida porque hay estilos
 * computados de verdad, que es justo lo que jsdom no puede dar.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

const _AQUI = dirname(fileURLToPath(import.meta.url));
const _AXE_MIN_JS = readFileSync(join(_AQUI, "../node_modules/axe-core/axe.min.js"), "utf-8");

type ResultadoAxe = {
  violations: Array<{
    id: string;
    help: string;
    nodes: Array<{ target: string[] }>;
  }>;
};

/** Inyecta `axe-core` en la página SI todavía no está (una sola vez por
 * página: inyectarlo de nuevo en cada llamada no rompe nada, pero no hace
 * falta). */
async function inyectarAxeSiFalta(page: Page): Promise<void> {
  const yaEsta = await page.evaluate(
    () => typeof (window as { axe?: unknown }).axe !== "undefined",
  );
  if (!yaEsta) {
    await page.addScriptTag({ content: _AXE_MIN_JS });
  }
}

/** Corre axe sobre toda la página y hace fallar el test, con el detalle
 * de cada violación, si encuentra alguna (misma forma que `sinViolaciones`
 * de `lib/test/accesibilidad.ts`, acá contra el navegador real). */
export async function sinViolacionesEnElNavegador(page: Page): Promise<void> {
  await inyectarAxeSiFalta(page);
  const resultado = (await page.evaluate(() =>
    (window as unknown as { axe: { run: () => Promise<ResultadoAxe> } }).axe.run(),
  )) as ResultadoAxe;
  if (resultado.violations.length === 0) {
    return;
  }
  const detalle = resultado.violations
    .map(
      (violacion) =>
        `${violacion.id} (${violacion.help}): ${violacion.nodes
          .map((nodo) => nodo.target.join(" "))
          .join(", ")}`,
    )
    .join("\n");
  expect(detalle, `axe encontró ${resultado.violations.length} violación(es)`).toBe("");
}
