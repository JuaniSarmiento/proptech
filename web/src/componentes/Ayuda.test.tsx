/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Ayuda } from "./Ayuda";

afterEach(cleanup);

function elTexto() {
  return (
    <Ayuda
      paraQueSirve="Acá cargás las unidades del edificio."
      pasos={["Revisá que estén todas.", "Fijate que los coeficientes sumen 100%."]}
      yDespues="Con esto armado ya podés liquidar."
    />
  );
}

describe("Ayuda", () => {
  it("se abre con clic, muestra las tres partes y se cierra con el botón, devolviendo el foco (Abrir y cerrar la ayuda con teclado)", async () => {
    const usuario = userEvent.setup();
    render(elTexto());
    const boton = screen.getByRole("button", { name: /Ayuda/ });

    await usuario.click(boton);
    expect(screen.getByText("¿Para qué sirve esta pantalla?")).toBeTruthy();
    expect(screen.getByText("¿Qué hago acá?")).toBeTruthy();
    expect(screen.getByText("¿Y después?")).toBeTruthy();
    expect(
      screen.getByRole("region", { name: "Ayuda: para qué sirve esta pantalla" }),
    ).toBeTruthy();

    await usuario.click(screen.getByRole("button", { name: "Cerrar ayuda" }));
    expect(screen.queryByText("¿Para qué sirve esta pantalla?")).toBeNull();
    expect(document.activeElement).toBe(boton);
  });

  it("se abre con Enter desde el teclado y se cierra con Esc, devolviendo el foco", async () => {
    const usuario = userEvent.setup();
    render(elTexto());
    const boton = screen.getByRole("button", { name: /Ayuda/ });

    boton.focus();
    await usuario.keyboard("{Enter}");
    expect(screen.getByText("¿Qué hago acá?")).toBeTruthy();

    await usuario.keyboard("{Escape}");
    expect(screen.queryByText("¿Qué hago acá?")).toBeNull();
    expect(document.activeElement).toBe(boton);
  });

  it("sin violaciones de axe, cerrada y abierta", async () => {
    const usuario = userEvent.setup();
    const { container } = render(elTexto());
    await sinViolaciones(container);
    await usuario.click(screen.getByRole("button", { name: /Ayuda/ }));
    await sinViolaciones(container);
  });
});
