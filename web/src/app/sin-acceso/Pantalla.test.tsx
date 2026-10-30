/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { afterEach, expect, it, vi } from "vitest";
import { PantallaSinAcceso } from "./Pantalla";

const estado = vi.hoisted(() => ({
  email: "ficticia@ejemplo.invalid" as string | undefined,
  cargado: true,
}));
vi.mock("@clerk/nextjs", () => ({
  useUser: () => ({
    user: { primaryEmailAddress: estado.email ? { emailAddress: estado.email } : null },
  }),
  ClerkLoaded: ({ children }: { children: React.ReactNode }) => (estado.cargado ? children : null),
}));
afterEach(() => {
  cleanup();
  estado.email = "ficticia@ejemplo.invalid";
  estado.cargado = true;
});
it("título, email y acciones independientes de la carga de Clerk", () => {
  render(<PantallaSinAcceso />);
  expect(screen.queryByRole("heading", { name: "Tu cuenta no tiene acceso todavía" })).toBeTruthy();
  expect(screen.queryByText("ficticia@ejemplo.invalid")).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Cerrar sesión" })?.getAttribute("href")).toBe(
    "/ingresar?cerrar=1",
  );
  expect(screen.queryByRole("link", { name: "Volver a intentar" })?.getAttribute("href")).toBe(
    "/elegir-administracion",
  );
});
it("sin email no inventa ni vacío ni undefined", () => {
  estado.email = undefined;
  const { container } = render(<PantallaSinAcceso />);
  expect(screen.queryByRole("heading", { name: "Tu cuenta no tiene acceso todavía" })).toBeTruthy();
  expect(container.textContent).not.toContain("undefined");
  expect(container.textContent).not.toContain("@");
});
it("las dos acciones existen aunque Clerk no cargue", () => {
  estado.cargado = false;
  render(<PantallaSinAcceso />);
  expect(screen.queryByRole("link", { name: "Cerrar sesión" })).toBeTruthy();
  expect(screen.queryByRole("link", { name: "Volver a intentar" })).toBeTruthy();
});
it("Tab y Enter recorren y activan las dos acciones", async () => {
  render(<PantallaSinAcceso />);
  const user = userEvent.setup();
  expect(screen.queryByRole("link", { name: "Cerrar sesión" })).toBeTruthy();
  const cerrar = screen.getByRole("link", { name: "Cerrar sesión" });
  const volver = screen.getByRole("link", { name: "Volver a intentar" });
  const cerrarClick = vi.fn((e: Event) => e.preventDefault());
  const volverClick = vi.fn((e: Event) => e.preventDefault());
  cerrar.addEventListener("click", cerrarClick);
  volver.addEventListener("click", volverClick);
  await user.tab();
  await user.tab();
  await user.tab();
  expect(document.activeElement).toBe(cerrar);
  await user.keyboard("{Enter}");
  expect(cerrarClick).toHaveBeenCalledOnce();
  await user.tab();
  expect(document.activeElement).toBe(volver);
  await user.keyboard("{Enter}");
  expect(volverClick).toHaveBeenCalledOnce();
});
it("axe sin violaciones", async () => {
  const { container } = render(<PantallaSinAcceso />);
  expect((await axe.run(container)).violations).toEqual([]);
});
