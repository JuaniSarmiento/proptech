/**
 * @vitest-environment jsdom
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useCerrarConEscape } from "./useCerrarConEscape";

function presionarEscape() {
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
}

describe("useCerrarConEscape", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("no hace nada si no está activo", () => {
    const alCerrar = vi.fn();
    renderHook(() => useCerrarConEscape(false, alCerrar));
    act(() => presionarEscape());
    expect(alCerrar).not.toHaveBeenCalled();
  });

  it("llama a alCerrar con Escape cuando está activo", () => {
    const alCerrar = vi.fn();
    renderHook(() => useCerrarConEscape(true, alCerrar));
    act(() => presionarEscape());
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });

  it("con dos capas activas (la ayuda abierta dentro del panel), Escape cierra sólo la de arriba", () => {
    const cerrarPanel = vi.fn();
    const cerrarAyuda = vi.fn();
    renderHook(() => useCerrarConEscape(true, cerrarPanel)); // se abrió primero
    renderHook(() => useCerrarConEscape(true, cerrarAyuda)); // se abrió después, encima

    act(() => presionarEscape());
    expect(cerrarAyuda).toHaveBeenCalledTimes(1);
    expect(cerrarPanel).not.toHaveBeenCalled();
  });
});
