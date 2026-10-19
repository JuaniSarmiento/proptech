import { describe, expect, it } from "vitest";
import { erroresDeFormulario, mensajeDeError } from "./mensajes";

describe("mensajeDeError", () => {
  it("traduce motivos conocidos a castellano simple", () => {
    expect(mensajeDeError("missing")).toBe("Este dato es obligatorio.");
    expect(mensajeDeError("string_too_short")).toBe("Es muy corto.");
  });

  it("da un mensaje genérico para un motivo desconocido (L-007: nunca el texto de la API)", () => {
    expect(mensajeDeError("MARCADOR_TECNICO_PRIVADO")).toBe("Revisá este dato.");
  });
});

describe("erroresDeFormulario", () => {
  it("separa los errores de campos conocidos de los desconocidos", () => {
    const resultado = erroresDeFormulario(
      [
        { campo: "nombre", motivo: "missing" },
        { campo: "un_campo_que_no_existe", motivo: "missing" },
      ],
      ["nombre", "localidad"],
    );
    expect(resultado.erroresPorCampo).toEqual({ nombre: "Este dato es obligatorio." });
    expect(resultado.erroresDesconocidos).toEqual(["Este dato es obligatorio."]);
  });
});
