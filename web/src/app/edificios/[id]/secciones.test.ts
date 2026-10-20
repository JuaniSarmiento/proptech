import { describe, expect, it } from "vitest";
import { seccionesDelEdificio } from "./secciones";

describe("seccionesDelEdificio", () => {
  it("arma las cinco secciones del menú con el id del edificio en cada href", () => {
    const secciones = seccionesDelEdificio("abc");
    expect(secciones.map((s) => s.clave)).toEqual([
      "resumen",
      "unidades",
      "grupos",
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
      ["categorias", "Configuración"],
      ["configuracion", "Configuración"],
    ]);
    expect(new Set(secciones.map((s) => s.icono)).size).toBe(5);
  });
});
