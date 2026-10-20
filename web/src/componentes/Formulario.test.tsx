/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Campo, Formulario } from "./Formulario";

afterEach(cleanup);

describe("Formulario", () => {
  it("un error de campo marca aria-invalid y aria-describedby, y el resumen enlaza al campo (Identificador repetido)", async () => {
    const usuario = userEvent.setup();
    render(
      <Formulario
        erroresPorCampo={{ identificador: "Ya existe una unidad con este identificador" }}
      >
        <Campo nombre="identificador" etiqueta="Identificador" />
      </Formulario>,
    );
    const campo = screen.getByLabelText("Identificador");
    expect(campo.getAttribute("aria-invalid")).toBe("true");
    const idDescriptor = campo.getAttribute("aria-describedby");
    expect(idDescriptor).toBeTruthy();
    expect(document.getElementById(idDescriptor as string)?.textContent).toBe(
      "Ya existe una unidad con este identificador",
    );

    const enlace = screen.getByRole("link", {
      name: "Ya existe una unidad con este identificador",
    });
    await usuario.click(enlace);
    expect(document.activeElement).toBe(campo);
  });

  it("un error de un campo que el formulario no tiene va sólo al resumen, sin marcar ningún campo (Error de un campo desconocido)", () => {
    render(
      <Formulario erroresPorCampo={{}} erroresDesconocidos={["algo_que_no_existe: raro"]}>
        <Campo nombre="identificador" etiqueta="Identificador" />
      </Formulario>,
    );
    expect(screen.getByText("algo_que_no_existe: raro")).toBeTruthy();
    const campo = screen.getByLabelText("Identificador");
    expect(campo.getAttribute("aria-invalid")).toBe("false");
    // el error desconocido no es un enlace: no hay campo al que llevar el foco.
    expect(screen.queryByRole("link", { name: "algo_que_no_existe: raro" })).toBeNull();
  });

  it("sin errores no muestra resumen", () => {
    render(
      <Formulario erroresPorCampo={{}}>
        <Campo nombre="identificador" etiqueta="Identificador" />
      </Formulario>,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("con `action`, se la pasa al <form> (tarea 4.1: envío real con una server action)", () => {
    const { container } = render(
      <Formulario erroresPorCampo={{}} action="/no-deberia-navegar-acá">
        <Campo nombre="identificador" etiqueta="Identificador" />
      </Formulario>,
    );
    expect(container.querySelector("form")?.getAttribute("action")).toBe("/no-deberia-navegar-acá");
  });

  it("con `onSubmit` y `aria-label`, se los pasa al <form> (tarea 4.7: validar antes de llamar a la acción)", () => {
    const alEnviar = vi.fn((e: { preventDefault: () => void }) => e.preventDefault());
    const { container } = render(
      <Formulario erroresPorCampo={{}} onSubmit={alEnviar} aria-label="Formulario de prueba">
        <Campo nombre="identificador" etiqueta="Identificador" />
      </Formulario>,
    );
    const formulario = container.querySelector("form");
    expect(formulario?.getAttribute("aria-label")).toBe("Formulario de prueba");
    formulario?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(alEnviar).toHaveBeenCalledTimes(1);
  });

  it("sin violaciones de axe, con errores", async () => {
    const { container } = render(
      <Formulario
        erroresPorCampo={{ identificador: "Repetido" }}
        erroresDesconocidos={["otro campo raro"]}
      >
        <Campo nombre="identificador" etiqueta="Identificador" />
      </Formulario>,
    );
    await sinViolaciones(container);
  });
});
