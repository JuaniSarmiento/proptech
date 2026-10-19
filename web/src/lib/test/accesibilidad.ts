/**
 * Ayudante de axe para los tests de componentes (D3, tarea 3.1).
 *
 * Deliberadamente sin `vitest-axe` (es de 2022, fija `axe-core@^4.4.2`
 * propio y arrastraría una segunda copia de `axe-core` junto a la que ya
 * pineamos acá): un envoltorio de tres líneas sobre `axe.run()` alcanza.
 */

import axe from "axe-core";
import { expect } from "vitest";

/** Corre axe sobre `contenedor` y hace fallar el test, con el detalle de
 * cada violación, si encuentra alguna. Se ve fallar de verdad (L-019): el
 * test de este mismo archivo pasa un botón sin nombre accesible y comprueba
 * que `sinViolaciones` rechaza. */
export async function sinViolaciones(contenedor: Element): Promise<void> {
  const resultado = await axe.run(contenedor);
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
  expect.fail(`axe encontró ${resultado.violations.length} violación(es):\n${detalle}`);
}
