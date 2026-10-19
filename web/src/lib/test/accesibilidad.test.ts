/** @vitest-environment jsdom */
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "./accesibilidad";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("sinViolaciones", () => {
  it("no encuentra nada en un botón con nombre accesible", async () => {
    document.body.innerHTML = "<button>Guardar</button>";
    await expect(sinViolaciones(document.body)).resolves.toBeUndefined();
  });

  it("falla con un botón sin nombre accesible (L-019: se ve fallar antes de confiar)", async () => {
    document.body.innerHTML = "<button></button>";
    await expect(sinViolaciones(document.body)).rejects.toThrow(/button-name/);
  });
});
