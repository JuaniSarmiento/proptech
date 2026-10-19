/**
 * @vitest-environment jsdom
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { EstadoDeCoeficientes } from "./EstadoDeCoeficientes";

afterEach(cleanup);

describe("EstadoDeCoeficientes", () => {
  it("cada estado tiene un texto distinto, aunque se le quite el color (no sólo color)", () => {
    const { container: contenedorOk } = render(
      <EstadoDeCoeficientes estado="ok" diferencia="0.000000" />,
    );
    const { container: contenedorAdvertencia } = render(
      <EstadoDeCoeficientes estado="advertencia" diferencia="0.000050" />,
    );
    const { container: contenedorFuera } = render(
      <EstadoDeCoeficientes estado="fuera_de_tolerancia" diferencia="-0.000200" />,
    );

    const textos = [
      contenedorOk.textContent,
      contenedorAdvertencia.textContent,
      contenedorFuera.textContent,
    ];
    // las tres distintas entre sí: ningún par puede coincidir, aunque se
    // les quite el color (el texto es la ÚNICA señal que estamos probando).
    expect(new Set(textos).size).toBe(3);
  });

  it("fuera de tolerancia dice en texto cuánto falta, con el formato argentino (Fuera de tolerancia)", () => {
    const { container } = render(
      <EstadoDeCoeficientes estado="fuera_de_tolerancia" diferencia="-0.000200" />,
    );
    expect(container.textContent).toContain("falta 0,0200 %");
  });

  it("sobra, cuando la diferencia es positiva", () => {
    const { container } = render(
      <EstadoDeCoeficientes estado="advertencia" diferencia="0.000100" />,
    );
    expect(container.textContent).toContain("sobra 0,0100 %");
  });

  it('"ok" no muestra ningún signo de diferencia', () => {
    const { container } = render(<EstadoDeCoeficientes estado="ok" diferencia="0.000000" />);
    expect(container.textContent).not.toMatch(/falta|sobra/);
  });
});
