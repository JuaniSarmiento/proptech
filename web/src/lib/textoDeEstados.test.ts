import { describe, expect, it } from "vitest";
import { textoEstadoDeMigracion } from "./textoDeEstados";

describe("textoEstadoDeMigracion", () => {
  it("traduce el vocabulario cerrado de la API a castellano simple", () => {
    expect(textoEstadoDeMigracion("pendiente")).toBe("Pendiente de confirmar saldos previos");
    expect(textoEstadoDeMigracion("sin_saldos_previos")).toBe(
      "Confirmado: arranca sin saldos previos",
    );
  });

  it("confirmada es Saldos iniciales confirmados, nunca el texto de desconocido (E12)", () => {
    expect(textoEstadoDeMigracion("confirmada")).toBe("Saldos iniciales confirmados");
  });

  it("da un texto genérico si el valor no es ninguno de los conocidos", () => {
    expect(textoEstadoDeMigracion("algo_nuevo")).toBe("Estado de migración desconocido");
  });
});
