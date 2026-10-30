/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { type AccionesDeSesion, type DatosDeSesion, permite } from "./SesionDePantalla";

function acciones(parcial: Partial<AccionesDeSesion> = {}): AccionesDeSesion {
  return {
    administracion: [],
    todos_los_edificios: [],
    por_edificio: {},
    ...parcial,
  };
}

function sesionCon(
  accionesDeA: AccionesDeSesion,
  administracionId = "a",
): { datos: DatosDeSesion; administracionId?: string } {
  return {
    datos: {
      persona: { nombre: "Alguien" },
      administraciones: [{ id: "a", nombre: "A", acciones: accionesDeA }],
    },
    administracionId,
  };
}

describe("permite", () => {
  it("sin sesión en el contexto da false (D11)", () => {
    expect(permite(null, "crear_edificio")).toBe(false);
  });

  it("sin acciones en la sesión oculta todo (Sin acciones en la sesión)", () => {
    const sesion = sesionCon(acciones());
    expect(permite(sesion, "crear_edificio")).toBe(false);
    expect(permite(sesion, "configurar_padron", "e1")).toBe(false);
  });

  it("una acción de administración da lo mismo con o sin complejoId", () => {
    const sesion = sesionCon(acciones({ administracion: ["crear_edificio"] }));
    expect(permite(sesion, "crear_edificio")).toBe(true);
    expect(permite(sesion, "crear_edificio", "e1")).toBe(true);
  });

  it("una acción de edificio sin complejoId da false aunque esté en todos_los_edificios", () => {
    const sesion = sesionCon(acciones({ todos_los_edificios: ["configurar_padron"] }));
    expect(permite(sesion, "configurar_padron")).toBe(false);
  });

  it("todos_los_edificios permite en cualquier edificio (Un administrador por edificio / principal)", () => {
    const sesion = sesionCon(acciones({ todos_los_edificios: ["configurar_padron"] }));
    expect(permite(sesion, "configurar_padron", "e1")).toBe(true);
    expect(permite(sesion, "configurar_padron", "e2")).toBe(true);
  });

  it("por_edificio sólo permite en el edificio que trae (Un contador por edificio)", () => {
    const sesion = sesionCon(
      acciones({ por_edificio: { e1: ["ver_configuracion_del_edificio"] } }),
    );
    expect(permite(sesion, "ver_configuracion_del_edificio", "e1")).toBe(true);
    expect(permite(sesion, "ver_configuracion_del_edificio", "e2")).toBe(false);
  });

  it("la administración elegida no está en la lista: false", () => {
    const sesion = sesionCon(acciones({ administracion: ["crear_edificio"] }), "otra");
    expect(permite(sesion, "crear_edificio")).toBe(false);
  });
});
