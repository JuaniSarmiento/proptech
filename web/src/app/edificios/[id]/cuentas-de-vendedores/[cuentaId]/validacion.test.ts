import { describe, expect, it } from "vitest";
import { importeParaApi, validarCobro } from "./validacion";

describe("importeParaApi", () => {
  it("pasa la coma decimal a punto y completa a dos decimales", () => {
    expect(importeParaApi("20000,00")).toBe("20000.00");
    expect(importeParaApi("5.000,5")).toBe("5000.50");
    expect(importeParaApi("100")).toBe("100.00");
  });

  it("lo que no es plata con a lo sumo dos decimales es null", () => {
    for (const texto of ["", "abc", "10,001", "1e2", "-5", "1,2,3"]) {
      expect(importeParaApi(texto)).toBeNull();
    }
  });
});

describe("validarCobro", () => {
  it("no juzga el tope ni la fecha futura: eso lo dice la API", () => {
    expect(validarCobro("99999,00", "2099-01-01")).toEqual({});
  });

  it("dice qué campo falta", () => {
    expect(Object.keys(validarCobro("", "")).sort()).toEqual(["fecha", "importe"]);
  });
});
