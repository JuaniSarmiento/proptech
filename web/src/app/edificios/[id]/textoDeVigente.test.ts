import { describe, expect, it } from "vitest";
import { textoDeVigente } from "./textoDeVigente";

describe("textoDeVigente", () => {
  it("sin configuración vigente da el texto de falta", () => {
    expect(textoDeVigente(null)).toBe("Todavía no configuraste la tasa ni el vencimiento.");
  });

  it("vencimiento único: tasa, fondo y día, en formato argentino (D6)", () => {
    expect(
      textoDeVigente({
        id: "1",
        complejo_id: "1",
        vigente_desde: "2026-01-01",
        tasa_mensual: "3.00",
        dias_de_gracia: 0,
        forma_de_calculo: "mes_entero",
        porcentaje_fondo: "5.00",
        dia_de_vencimiento: 10,
        modalidad_de_vencimiento: "unico",
        dia_segundo_vencimiento: null,
        recargo_segundo_vencimiento: null,
        autor_id: "a",
        creada_en: "2026-01-01",
      }),
    ).toBe("Tasa 3,00 % · Fondo de reserva 5,00 % · Vencimiento día 10");
  });

  it("vencimiento doble: suma el segundo vencimiento y su recargo", () => {
    expect(
      textoDeVigente({
        id: "1",
        complejo_id: "1",
        vigente_desde: "2026-01-01",
        tasa_mensual: "3.00",
        dias_de_gracia: 0,
        forma_de_calculo: "mes_entero",
        porcentaje_fondo: "5.00",
        dia_de_vencimiento: 10,
        modalidad_de_vencimiento: "doble",
        dia_segundo_vencimiento: 20,
        recargo_segundo_vencimiento: "1.50",
        autor_id: "a",
        creada_en: "2026-01-01",
      }),
    ).toBe(
      "Tasa 3,00 % · Fondo de reserva 5,00 % · Vencimiento día 10, segundo vencimiento día 20 (recargo 1,50 %)",
    );
  });
});
