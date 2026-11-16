import { describe, expect, it } from "vitest";
import { seccionesDelEdificio } from "./secciones";

describe("seccionesDelEdificio", () => {
  it("arma las seis secciones del menú con el id del edificio en cada href", () => {
    const secciones = seccionesDelEdificio("abc");
    expect(secciones.map((s) => s.clave)).toEqual([
      "resumen",
      "unidades",
      "grupos",
      "liquidaciones",
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
      ["categorias", "Configuración"],
      ["configuracion", "Configuración"],
    ]);
    expect(new Set(secciones.map((s) => s.icono)).size).toBe(6);
  });

  it("Liquidaciones lleva a la lista y sólo se pide con ver_liquidaciones, en ese edificio (H-017)", () => {
    const liquidaciones = seccionesDelEdificio("abc").find((s) => s.clave === "liquidaciones");
    expect(liquidaciones).toMatchObject({
      href: "/edificios/abc/liquidaciones",
      accion: "ver_liquidaciones",
      complejoId: "abc",
    });
  });
});
