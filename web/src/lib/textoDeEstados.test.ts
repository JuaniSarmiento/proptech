import { describe, expect, it } from "vitest";
import { textoEstadoDeMigracion } from "./textoDeEstados";

describe("textoEstadoDeMigracion", () => {
  it("traduce el vocabulario cerrado de la API a castellano simple", () => {
    expect(textoEstadoDeMigracion("pendiente")).toBe("Pendiente de confirmar saldos previos");
    expect(textoEstadoDeMigracion("sin_saldos_previos")).toBe(
      "Confirmado: arranca sin saldos previos",
    );
  });

  it("da un texto genérico si el valor no es ninguno de los dos conocidos", () => {
    expect(textoEstadoDeMigracion("algo_nuevo")).toBe("Estado de migración desconocido");
  });
});
