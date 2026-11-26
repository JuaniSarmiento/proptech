import { describe, expect, it } from "vitest";
import {
  type BorradorDeCambio,
  hayQueElegirDeudor,
  pedidoDelBorrador,
  validarBorrador,
} from "./validacion";

const BASE: BorradorDeCambio = {
  fecha: "2026-11-10",
  vendedores: ["a"],
  compradores: [{ nombre: " Carlos ", email: "" }],
  expensa: "entera",
  deuda: "en_la_unidad",
  deudor: "",
};

describe("validarBorrador", () => {
  it("un borrador completo no tiene errores", () => {
    expect(validarBorrador(BASE)).toEqual({});
  });

  it("dice qué campo falta con el mensaje de la pantalla", () => {
    const errores = validarBorrador({
      ...BASE,
      fecha: "",
      vendedores: [],
      compradores: [{ nombre: "  ", email: "" }],
    });
    expect(Object.keys(errores).sort()).toEqual(["compradores", "fecha", "vendedores"]);
    expect(errores.fecha).toBe("Poné una fecha válida, que no sea posterior a hoy.");
  });

  it("no juzga una fecha futura: eso lo dice la API", () => {
    expect(validarBorrador({ ...BASE, fecha: "2099-01-01" })).toEqual({});
  });

  it("con más de un vendedor y algo que pasarle, pide elegir el deudor", () => {
    const dos = { ...BASE, vendedores: ["a", "b"], deuda: "a_nombre_del_vendedor" as const };
    expect(validarBorrador(dos).vendedor_deudor).toBeDefined();
    expect(validarBorrador({ ...dos, deudor: "b" })).toEqual({});
  });
});

describe("hayQueElegirDeudor", () => {
  it("sólo con más de un vendedor y deuda a su nombre o prorrateo", () => {
    const dos = { ...BASE, vendedores: ["a", "b"] };
    expect(hayQueElegirDeudor(dos)).toBe(false);
    expect(hayQueElegirDeudor({ ...dos, expensa: "prorrateo" })).toBe(true);
    expect(hayQueElegirDeudor({ ...dos, deuda: "a_nombre_del_vendedor" })).toBe(true);
    expect(hayQueElegirDeudor({ ...BASE, deuda: "a_nombre_del_vendedor" })).toBe(false);
  });
});

describe("pedidoDelBorrador", () => {
  it("recorta el nombre, manda el email vacío como null y omite el deudor sin elegirlo", () => {
    expect(pedidoDelBorrador(BASE)).toEqual({
      fecha: "2026-11-10",
      vendedores: ["a"],
      compradores: [{ nombre: "Carlos", email: null }],
      expensa_del_mes: "entera",
      deuda_previa: "en_la_unidad",
    });
  });

  it("manda el deudor cuando hay que elegirlo", () => {
    const pedido = pedidoDelBorrador({
      ...BASE,
      vendedores: ["a", "b"],
      expensa: "prorrateo",
      deudor: "b",
    });
    expect(pedido.vendedor_deudor).toBe("b");
  });
});
