/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { BarraDeProgreso } from "./BarraDeProgreso";

afterEach(cleanup);

describe("BarraDeProgreso", () => {
  it('dice "N de 6 pasos" en texto y lo mismo al lector de pantalla', () => {
    render(<BarraDeProgreso hechos={3} total={6} />);
    expect(screen.getByText("3 de 6 pasos")).toBeTruthy();
    const barra = screen.getByRole("progressbar", { name: "3 de 6 pasos" });
    expect(barra.getAttribute("aria-valuenow")).toBe("3");
    expect(barra.getAttribute("aria-valuemax")).toBe("6");
    expect(barra.getAttribute("aria-valuetext")).toBe("3 de 6 pasos");
  });

  it("el relleno es la fracción hecha: vacío en 0, lleno en 6 de 6", () => {
    const { container, rerender } = render(<BarraDeProgreso hechos={0} total={6} />);
    const relleno = () =>
      (
        container.querySelector(".barra-de-progreso__relleno") as HTMLElement
      ).style.getPropertyValue("--progreso");
    expect(relleno()).toBe("0");
    rerender(<BarraDeProgreso hechos={6} total={6} />);
    expect(relleno()).toBe("1");
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(<BarraDeProgreso hechos={2} total={6} />);
    await sinViolaciones(container);
  });
});
