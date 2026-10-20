/**
 * @vitest-environment jsdom
 */
/**
 * R3C-7 (rompedor 3b): `loading.tsx` reemplaza TODA la pantalla (ningún
 * `page.tsx` lo anida dentro de `ArmazonDelEdificio`, a diferencia de
 * "cargando" en el flujo normal) — sin su propio `<main>`/`<h1>`, axe en
 * el navegador real da `landmark-one-main`/`page-has-heading-one` (ver
 * `e2e/rompedor.spec.ts`, confirmado en Chromium; jsdom no corre esas
 * reglas de documento completo sobre un fragmento aislado, por eso este
 * test de componente sólo chequea la estructura, no el axe completo).
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import Cargando from "./loading";

afterEach(cleanup);

describe("loading.tsx (unidades)", () => {
  it("tiene un <main> y un <h1>", () => {
    const { container } = render(<Cargando />);
    expect(container.querySelector("main")).toBeTruthy();
    expect(container.querySelector("h1")).toBeTruthy();
  });
});
