import { describe, expect, it } from "vitest";
import type { VersionDelHistorial } from "../../../../lib/api/tipos";
import { camposCambiados } from "./historial";

const _BASE: VersionDelHistorial = {
  id: "v1",
  complejo_id: "e1",
  vigente_desde: "2026-10-19",
  tasa_mensual: "3.00",
  dias_de_gracia: 0,
  forma_de_calculo: "proporcional_por_dia",
  porcentaje_fondo: "0.00",
  dia_de_vencimiento: 10,
  modalidad_de_vencimiento: "unico",
  dia_segundo_vencimiento: null,
  recargo_segundo_vencimiento: null,
  autor_id: "a1",
  autor_nombre: "Alberto",
  creada_en: "2026-10-19T00:00:00Z",
};

describe("camposCambiados", () => {
  it("la primera versión (sin anterior) no tiene campos cambiados", () => {
    expect(camposCambiados(_BASE, null)).toEqual([]);
  });

  it("si cambia la tasa, la lista incluye 'tasa'", () => {
    const nueva: VersionDelHistorial = { ..._BASE, id: "v2", tasa_mensual: "4.00" };
    expect(camposCambiados(nueva, _BASE)).toContain("tasa");
  });

  it("si no cambia nada, la lista queda vacía", () => {
    const igual: VersionDelHistorial = { ..._BASE, id: "v2" };
    expect(camposCambiados(igual, _BASE)).toEqual([]);
  });

  it("compara por texto, no por número: '10' y '10' no son un cambio", () => {
    const igual: VersionDelHistorial = { ..._BASE, id: "v2", dia_de_vencimiento: 10 };
    expect(camposCambiados(igual, _BASE)).not.toContain("día de vencimiento");
  });
});
