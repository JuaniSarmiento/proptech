import { describe, expect, it } from "vitest";
import { seccionesDelEdificio } from "./secciones";

describe("seccionesDelEdificio", () => {
  it("arma las ocho secciones del menú con el id del edificio en cada href", () => {
    const secciones = seccionesDelEdificio("abc");
    expect(secciones.map((s) => s.clave)).toEqual([
      "resumen",
      "unidades",
      "grupos",
      "liquidaciones",
      "pagos",
      "mis-pagos",
      "categorias",
      "configuracion",
    ]);
    expect(secciones[0]?.href).toBe("/edificios/abc");
    expect(secciones[1]?.href).toBe("/edificios/abc/unidades");
  });

  it('agrupa en "El edificio" y "Configuración", cada sección con su ícono (enmienda 20/10)', () => {
    const secciones = seccionesDelEdificio("abc");
    expect(secciones.map((s) => [s.clave, s.grupo])).toEqual([
      ["resumen", "El edificio"],
      ["unidades", "El edificio"],
      ["grupos", "El edificio"],
      ["liquidaciones", "Liquidación"],
      ["pagos", "Liquidación"],
      ["mis-pagos", "Liquidación"],
      ["categorias", "Configuración"],
      ["configuracion", "Configuración"],
    ]);
    expect(new Set(secciones.map((s) => s.icono)).size).toBe(8);
  });

  it("Liquidaciones lleva a la lista y sólo se pide con ver_liquidaciones, en ese edificio (H-017)", () => {
    const liquidaciones = seccionesDelEdificio("abc").find((s) => s.clave === "liquidaciones");
    expect(liquidaciones).toMatchObject({
      href: "/edificios/abc/liquidaciones",
      accion: "ver_liquidaciones",
      complejoId: "abc",
    });
  });

  it('"Pagos" se pide con confirmar_pago_informado y "Mis pagos" con informar_pago, cada uno en ese edificio (H-025, D-131)', () => {
    const secciones = seccionesDelEdificio("abc");
    expect(secciones.find((s) => s.clave === "pagos")).toMatchObject({
      etiqueta: "Pagos",
      href: "/edificios/abc/pagos",
      accion: "confirmar_pago_informado",
      complejoId: "abc",
    });
    expect(secciones.find((s) => s.clave === "mis-pagos")).toMatchObject({
      etiqueta: "Mis pagos",
      href: "/edificios/abc/mis-pagos",
      accion: "informar_pago",
      complejoId: "abc",
    });
  });
});
