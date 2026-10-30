/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { PantallaSelector, SesionNoUtilizable } from "./Pantalla";

afterEach(cleanup);
it("el selector ya no presenta un estado vacío", () => {
  render(
    <PantallaSelector
      datos={{ persona: { nombre: "Ficticia" }, administraciones: [] }}
      aceptada={true}
      accion={async () => null}
    />,
  );
  expect(screen.queryByText("Todavía no tenés una administración")).toBeNull();
});
it("error de sesión: Tab llega a Cerrar sesión y Enter lo activa", async () => {
  render(<SesionNoUtilizable />);
  const user = userEvent.setup();
  expect(screen.queryByText("No pudimos validar tu sesión")).toBeTruthy();
  const cerrar = screen.getByRole("link", { name: "Cerrar sesión" });
  await user.tab();
  await user.tab();
  await user.tab();
  expect(document.activeElement).toBe(cerrar);
  const click = vi.fn((e: Event) => e.preventDefault());
  cerrar.addEventListener("click", click);
  await user.keyboard("{Enter}");
  expect(click).toHaveBeenCalledOnce();
});
