/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it } from "vitest";
import { sinViolaciones } from "../../lib/test/accesibilidad";
import Privacidad from "./page";

afterEach(cleanup);

it("explica los datos, transferencia, finalidad, conservación, responsable y derechos sin pedir sesión", async () => {
  const { container } = render(<Privacidad />);
  expect(screen.getByRole("heading", { level: 1, name: "Aviso de privacidad" })).toBeTruthy();
  for (const nombre of [
    "Qué datos usamos",
    "Dónde se guardan",
    "Para qué los usamos",
    "Cuánto tiempo",
    "Responsable y contacto",
    "Tus derechos",
  ]) {
    expect(screen.getByRole("heading", { name: nombre })).toBeTruthy();
  }
  expect(container.textContent).toMatch(/Clerk.*email.*nombre/);
  expect(container.textContent).toContain("fuera de la Argentina");
  expect(container.textContent).toMatch(/acceso.*rectificación.*supresión/);
  expect(screen.getByText(/todavía está en revisión/)).toBeTruthy();
  expect(container.textContent).not.toMatch(/Juani|Alberto|Emiliano|aprobaci[oó]n/i);
  await userEvent.click(screen.getByRole("button", { name: "Ayuda" }));
  for (const nombre of ["¿Para qué sirve esta pantalla?", "¿Qué hago acá?", "¿Y después?"]) {
    expect(screen.getByRole("heading", { name: nombre })).toBeTruthy();
  }
  await sinViolaciones(container);
});
