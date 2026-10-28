import { describe, expect, it } from "vitest";
import { erroresDeFormulario } from "./mensajes";

describe("erroresDeFormulario", () => {
  it('tipo "fuera_de_rango" compone el mensaje desde los identificadores estructurados, no un texto crudo de la API', () => {
    const { erroresPorCampo } = erroresDeFormulario(
      [{ campo: "pisos", motivo: "fuera_de_rango", identificadores: ["3A", "3B"] }],
      ["pisos", "subsuelos"],
    );
    expect(erroresPorCampo.pisos).toBe("Quedarían unidades fuera de rango: 3A, 3B.");
  });

  it('otros tipos (ej. "value_error") siguen usando el diccionario genérico', () => {
    const { erroresPorCampo } = erroresDeFormulario(
      [{ campo: "pisos", motivo: "value_error" }],
      ["pisos"],
    );
    expect(erroresPorCampo.pisos).toBe("Este valor no es válido.");
  });
});
