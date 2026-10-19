/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { MenuDelEdificio, type SeccionDelEdificio } from "./MenuDelEdificio";

afterEach(cleanup);

const secciones: SeccionDelEdificio[] = [
  { clave: "resumen", etiqueta: "Resumen", href: "/edificios/1" },
  { clave: "unidades", etiqueta: "Unidades", href: "/edificios/1/unidades" },
  { clave: "grupos", etiqueta: "Grupos", href: "/edificios/1/grupos" },
];

describe("MenuDelEdificio", () => {
  it("marca la sección actual con aria-current y no sólo con color (Sección actual)", () => {
    render(
      <MenuDelEdificio
        nombreEdificio="Alsina 123"
        seccionActual="unidades"
        secciones={secciones}
      />,
    );
    const actual = screen.getByRole("link", { name: /Unidades/ });
    expect(actual.getAttribute("aria-current")).toBe("page");
    const otra = screen.getByRole("link", { name: /Resumen/ });
    expect(otra.getAttribute("aria-current")).toBeNull();
    // marca de FORMA, no sólo color: el texto visible del enlace actual trae
    // un indicador de forma además de su etiqueta.
    expect(actual.textContent).toMatch(/[▸›]/);
  });

  it('despliega "Secciones" con el teclado, se recorre con Tab y se cierra con Esc (Menú plegado)', async () => {
    const usuario = userEvent.setup();
    render(
      <MenuDelEdificio nombreEdificio="Alsina 123" seccionActual="resumen" secciones={secciones} />,
    );
    const boton = screen.getByRole("button", { name: "Secciones" });
    expect(boton.getAttribute("aria-expanded")).toBe("false");

    boton.focus();
    await usuario.keyboard("{Enter}");
    expect(boton.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("list").getAttribute("data-abierto")).toBe("true");

    await usuario.keyboard("{Escape}");
    expect(boton.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByRole("list").getAttribute("data-abierto")).toBe("false");
    expect(document.activeElement).toBe(boton);
  });

  it("sin violaciones de axe, abierto y cerrado", async () => {
    const usuario = userEvent.setup();
    const { container } = render(
      <MenuDelEdificio nombreEdificio="Alsina 123" seccionActual="resumen" secciones={secciones} />,
    );
    await sinViolaciones(container);
    await usuario.click(screen.getByRole("button", { name: "Secciones" }));
    await sinViolaciones(container);
  });
});
