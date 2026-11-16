import { describe, expect, it } from "vitest";
import type { LiquidacionDeLaLista } from "../../../../lib/api/liquidaciones";
import { mesActualEnMendoza, periodoParaPreparar, periodoSiguiente } from "./periodos";

function liquidacion(periodo: string, estado: LiquidacionDeLaLista["estado"]) {
  return {
    liquidacion_id: "00000000-0000-0000-0000-000000000001",
    periodo,
    estado,
    total: "1.00",
    emitida_en: "2026-11-02T15:00:00+00:00",
  } satisfies LiquidacionDeLaLista;
}

describe("periodoSiguiente", () => {
  it.each([
    ["2026-11", "2026-12"],
    ["2026-12", "2027-01"],
    ["2026-01", "2026-02"],
  ])("%s -> %s", (periodo, esperado) => {
    expect(periodoSiguiente(periodo)).toBe(esperado);
  });
});

describe("mesActualEnMendoza", () => {
  it("usa la hora de Mendoza, no la de UTC", () => {
    // 1 de diciembre 01:00 UTC es 30 de noviembre 22:00 en Mendoza (UTC-3).
    expect(mesActualEnMendoza(new Date("2026-12-01T01:00:00Z"))).toBe("2026-11");
    expect(mesActualEnMendoza(new Date("2026-12-01T03:30:00Z"))).toBe("2026-12");
  });
});

describe("periodoParaPreparar", () => {
  const ahora = new Date("2026-06-15T15:00:00Z");

  it("el mes siguiente al último que no está anulado", () => {
    const lista = [liquidacion("2026-11-01", "distribuida"), liquidacion("2026-10-01", "anulada")];
    expect(periodoParaPreparar(lista, ahora)).toBe("2026-12");
  });

  it("una anulada más nueva no cuenta", () => {
    const lista = [liquidacion("2026-12-01", "anulada"), liquidacion("2026-11-01", "emitida")];
    expect(periodoParaPreparar(lista, ahora)).toBe("2026-12");
  });

  it("no depende del orden de la lista", () => {
    const lista = [liquidacion("2026-09-01", "emitida"), liquidacion("2026-10-01", "emitida")];
    expect(periodoParaPreparar(lista, ahora)).toBe("2026-11");
  });

  it("sin ninguna, el mes actual", () => {
    expect(periodoParaPreparar([], ahora)).toBe("2026-06");
    expect(periodoParaPreparar([liquidacion("2026-10-01", "anulada")], ahora)).toBe("2026-06");
  });
});
