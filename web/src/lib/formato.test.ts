import { describe, expect, it } from "vitest";
import {
  coeficiente,
  diferenciaComoPorcentaje,
  dinero,
  fecha,
  fechaYHora,
  porcentaje,
  sumaComoPorcentaje,
  superficie,
  tasa,
} from "./formato";

describe("coeficiente", () => {
  it("un valor que el punto flotante pierde (D6)", () => {
    expect(coeficiente("0.083333")).toBe("0,083333");
  });
});

describe("superficie", () => {
  it("con punto de miles", () => {
    expect(superficie("1234.50")).toBe("1.234,50");
  });
});

describe("tasa y porcentaje", () => {
  it("dos decimales, coma decimal", () => {
    expect(tasa("3.00")).toBe("3,00");
    expect(porcentaje("2.00")).toBe("2,00 %");
  });
});

describe("sumaComoPorcentaje", () => {
  it("mueve la coma dos lugares sobre el texto de 6 decimales", () => {
    expect(sumaComoPorcentaje("0.999950")).toBe("99,9950 %");
  });

  it("un edificio completo (suma exacta)", () => {
    expect(sumaComoPorcentaje("1.000000")).toBe("100,0000 %");
  });
});

describe("diferenciaComoPorcentaje", () => {
  it('"falta" cuando la diferencia es negativa', () => {
    expect(diferenciaComoPorcentaje("-0.000200")).toBe("falta 0,0200 %");
  });

  it('"sobra" cuando la diferencia es positiva', () => {
    expect(diferenciaComoPorcentaje("0.000100")).toBe("sobra 0,0100 %");
  });
});

describe("rechazo de formatos que no son texto decimal ASCII (L-008)", () => {
  it.each([
    ["notación científica", "1e-1"],
    ["no numérico", "NaN"],
    ["espacio inicial", " 1.0"],
    ["dígitos Unicode (fullwidth)", "０.999950"],
    ["salto de línea final", "0.999950\n"],
  ])("%s: %s", (_motivo, texto) => {
    expect(() => coeficiente(texto)).toThrow();
    expect(() => sumaComoPorcentaje(texto)).toThrow();
  });
});

describe("fecha", () => {
  it("una fecha ISO de la API como día/mes/año argentino, sin pasar por Date (pulido 3b)", () => {
    expect(fecha("2026-10-20")).toBe("20/10/2026");
    expect(fecha("2027-01-05")).toBe("05/01/2027");
  });

  it("un texto que no es una fecha ISO se devuelve tal cual, nunca un 'Invalid Date'", () => {
    expect(fecha("mañana")).toBe("mañana");
  });
});

describe("dinero", () => {
  it.each([
    ["169000.00", "169.000,00"],
    ["0.00", "0,00"],
    ["-10000.00", "-10.000,00"],
    ["1234567.89", "1.234.567,89"],
    ["5.05", "5,05"],
  ])("%s -> %s", (entrada, esperado) => {
    expect(dinero(entrada)).toBe(esperado);
  });

  it.each(["10", "10.5", "1,00", "-", "", "1.000,00", " 1.00", "1.00\n"])(
    "un texto que no es plata con dos decimales (%j) se rechaza, nunca se muestra mal",
    (entrada) => {
      expect(() => dinero(entrada)).toThrow();
    },
  );
});

describe("fechaYHora", () => {
  it("una hora con zona se muestra en Mendoza, sin depender de la zona de quien corre", () => {
    expect(fechaYHora("2026-11-12T15:00:00+00:00")).toBe("12/11/2026 12:00");
    expect(fechaYHora("2026-11-13T02:30:00+00:00")).toBe("12/11/2026 23:30");
  });

  it("lo que no es una fecha con hora vuelve tal cual", () => {
    expect(fechaYHora("ayer")).toBe("ayer");
  });
});
