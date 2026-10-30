/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import type { SesionVisible } from "../../componentes/SesionDePantalla";
import { seccionesDeLaAdministracion } from "./secciones";

function sesionCon(verPersonal: boolean): SesionVisible {
  return {
    datos: {
      persona: { nombre: "Alguien" },
      administraciones: [
        {
          id: "a",
          nombre: "A",
          acciones: {
            administracion: verPersonal ? ["ver_personal"] : [],
            todos_los_edificios: [],
            por_edificio: {},
          },
        },
      ],
    },
    administracionId: "a",
  };
}

describe("seccionesDeLaAdministracion", () => {
  it('con ver_personal muestra "Personal"', () => {
    const secciones = seccionesDeLaAdministracion(sesionCon(true));
    expect(secciones.map((s) => s.clave)).toEqual(["personal"]);
  });

  it('sin ver_personal no muestra "Personal" (D11, control oculto)', () => {
    const secciones = seccionesDeLaAdministracion(sesionCon(false));
    expect(secciones).toEqual([]);
  });

  it("sin sesión en el contexto no muestra nada", () => {
    expect(seccionesDeLaAdministracion(null)).toEqual([]);
  });
});
