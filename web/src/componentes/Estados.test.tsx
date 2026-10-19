/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Estados } from "./Estados";

afterEach(cleanup);

describe("Estados", () => {
  it("cargando: esqueleto anunciado, sin texto técnico", async () => {
    const { container } = render(<Estados tipo="cargando" />);
    expect(screen.getByRole("status", { name: "Cargando" })).toBeTruthy();
    await sinViolaciones(container);
  });

  it("vacío: muestra el mensaje y la acción", async () => {
    const { container } = render(
      <Estados
        tipo="vacio"
        mensaje="Todavía no tenés edificios"
        accion={<a href="/x">Nuevo edificio</a>}
      />,
    );
    expect(screen.getByText("Todavía no tenés edificios")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Nuevo edificio" })).toBeTruthy();
    await sinViolaciones(container);
  });

  it("error: nunca el texto técnico, y Reintentar llama a la acción (Error de la API con texto técnico)", async () => {
    const alReintentar = vi.fn();
    const usuario = userEvent.setup();
    const { container } = render(
      <Estados
        tipo="error"
        mensaje="No pudimos cargar esta pantalla"
        onReintentar={alReintentar}
      />,
    );
    expect(screen.getByText("No pudimos cargar esta pantalla")).toBeTruthy();
    expect(container.textContent).not.toContain("Traceback");
    await usuario.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(alReintentar).toHaveBeenCalledTimes(1);
    await sinViolaciones(container);
  });

  it("sin permiso: dice qué no puede hacer y que lo puede hacer el titular (Sin permiso)", async () => {
    const { container } = render(
      <Estados tipo="sinPermiso" queNoPuede="cambiar la configuración" />,
    );
    expect(screen.getByText(/cambiar la configuración/)).toBeTruthy();
    expect(screen.getByText(/titular/)).toBeTruthy();
    await sinViolaciones(container);
  });

  it('no existe: "No encontramos este edificio" con enlace a Mis edificios (Edificio de otra administración)', async () => {
    const { container } = render(<Estados tipo="noExiste" />);
    expect(screen.getByText("No encontramos este edificio")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Mis edificios" })).toHaveProperty(
      "href",
      expect.stringContaining("/edificios"),
    );
    await sinViolaciones(container);
  });

  it("sin sesión: avisa sin tecnicismos", async () => {
    const { container } = render(<Estados tipo="sinSesion" />);
    expect(screen.getByText(/sesión/i)).toBeTruthy();
    await sinViolaciones(container);
  });
});
