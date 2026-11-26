import { describe, expect, it } from "vitest";
import { seccionesDelPortal } from "./secciones";

describe("seccionesDelPortal", () => {
  it("arma Inicio, Mis liquidaciones, Comprobantes y Mis pagos con el edificio de la primera unidad", () => {
    expect(seccionesDelPortal("abc").map((s) => [s.etiqueta, s.href])).toEqual([
      ["Inicio", "/inicio"],
      ["Mis liquidaciones", "/mis-liquidaciones"],
      ["Comprobantes", "/comprobantes"],
      ["Mis pagos", "/edificios/abc/mis-pagos"],
    ]);
  });

  it("sin unidades no hay Mis pagos: no hay edificio al cual llevar", () => {
    expect(seccionesDelPortal(null).map((s) => s.clave)).toEqual([
      "inicio",
      "mis-liquidaciones",
      "comprobantes",
    ]);
  });

  it("ninguna sección pide una acción: el portal es de quien tiene unidades y la API frena lo demás", () => {
    expect(seccionesDelPortal("abc").every((s) => s.accion === undefined)).toBe(true);
  });
});
