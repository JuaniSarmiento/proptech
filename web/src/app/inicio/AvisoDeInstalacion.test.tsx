/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AvisoDeInstalacion } from "./AvisoDeInstalacion";

const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15";
const ESCRITORIO = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36";

function conNavegador(userAgent: string) {
  vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(userAgent);
  window.matchMedia = vi.fn().mockReturnValue({ matches: false }) as unknown as typeof matchMedia;
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AvisoDeInstalacion", () => {
  it("en iPhone explica Compartir y Agregar a inicio", async () => {
    conNavegador(IPHONE);
    render(<AvisoDeInstalacion />);
    const aviso = await screen.findByRole("region", { name: "Agregar a la pantalla de inicio" });
    expect(aviso.textContent).toContain("Compartir");
    expect(aviso.textContent).toContain("Agregar a inicio");
  });

  it("fuera de iPhone no existe", () => {
    conNavegador(ESCRITORIO);
    render(<AvisoDeInstalacion />);
    expect(screen.queryByRole("region")).toBeNull();
  });

  it("al cerrarlo se va y no vuelve a mostrarse", async () => {
    conNavegador(IPHONE);
    const { unmount } = render(<AvisoDeInstalacion />);
    await userEvent.click(await screen.findByRole("button", { name: "Cerrar aviso" }));
    expect(screen.queryByRole("region")).toBeNull();
    unmount();
    render(<AvisoDeInstalacion />);
    expect(screen.queryByRole("region")).toBeNull();
  });

  it("sin almacenamiento (que tira al leer o escribir) se ve igual y cerrarlo no rompe nada", async () => {
    conNavegador(IPHONE);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("sin almacenamiento");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("sin almacenamiento");
    });
    render(<AvisoDeInstalacion />);
    await userEvent.click(await screen.findByRole("button", { name: "Cerrar aviso" }));
    expect(screen.queryByRole("region")).toBeNull();
  });

  it("si la app ya está instalada (modo standalone) no lo muestra", () => {
    conNavegador(IPHONE);
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as unknown as typeof matchMedia;
    render(<AvisoDeInstalacion />);
    expect(screen.queryByRole("region")).toBeNull();
  });
});
