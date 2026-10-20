/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useActionState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Campo, Formulario } from "./Formulario";

afterEach(cleanup);

type EstadoDePrueba = { erroresPorCampo: Record<string, string>; erroresDesconocidos: string[] };

/** Envoltorio minimal con `useActionState`, igual que cada pantalla real
 * (D8): el reset automático de React 19 (R3C-3) es del `<form action>`
 * ligado a una acción, no algo que `Formulario` sola pueda disparar. */
function FormularioDePrueba({
  accion,
}: {
  accion: (previo: EstadoDePrueba | null, datos: FormData) => Promise<EstadoDePrueba>;
}) {
  const [estado, enviar] = useActionState(accion, null);
  return (
    <Formulario
      erroresPorCampo={estado?.erroresPorCampo ?? {}}
      erroresDesconocidos={estado?.erroresDesconocidos ?? []}
      action={enviar}
    >
      <Campo
        nombre="identificador"
        etiqueta="Identificador"
        name="identificador"
        defaultValue="Original"
      />
      <label>
        Tipo
        <select name="tipo" defaultValue="departamento">
          <option value="departamento">Departamento</option>
          <option value="cochera">Cochera</option>
        </select>
      </label>
      <button type="submit">Guardar</button>
    </Formulario>
  );
}

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

  it("R3C-3 · un 403/422/409 de la acción no borra lo cargado (React 19 resetea el <form> al terminar la acción)", async () => {
    const accion = vi
      .fn<(previo: EstadoDePrueba | null, datos: FormData) => Promise<EstadoDePrueba>>()
      .mockResolvedValue({
        erroresPorCampo: {},
        erroresDesconocidos: ["No podés modificar el padrón de unidades."],
      });
    const usuario = userEvent.setup();
    render(<FormularioDePrueba accion={accion} />);
    await usuario.clear(screen.getByLabelText("Identificador"));
    await usuario.type(screen.getByLabelText("Identificador"), "PB-LOCAL");
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Tipo" }), "cochera");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.getByText(/No podés modificar el padrón/)).toBeTruthy());
    expect((screen.getByLabelText("Identificador") as HTMLInputElement).value).toBe("PB-LOCAL");
    expect(screen.getByRole("combobox", { name: "Tipo" })).toHaveProperty("value", "cochera");
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
