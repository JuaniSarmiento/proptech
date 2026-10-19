/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { sinViolaciones } from "../lib/test/accesibilidad";
import { Ayuda } from "./Ayuda";
import { PanelLateral } from "./PanelLateral";

afterEach(cleanup);

function PruebaConFila() {
  const filaRef = useRef<HTMLButtonElement>(null);
  const [abierto, setAbierto] = useState(false);
  const [valor, setValor] = useState("");
  return (
    <div>
      <button ref={filaRef} type="button" onClick={() => setAbierto(true)}>
        Agregar unidad
      </button>
      <PanelLateral
        abierto={abierto}
        titulo="Nueva unidad"
        alCerrar={() => setAbierto(false)}
        devolverFocoA={filaRef}
      >
        <label htmlFor="identificador">Identificador</label>
        <input
          id="identificador"
          value={valor}
          onChange={(evento) => setValor(evento.target.value)}
        />
        <Ayuda paraQueSirve="x" pasos={["y"]} yDespues="z" />
        <button type="button">Guardar</button>
      </PanelLateral>
    </div>
  );
}

describe("PanelLateral", () => {
  it("atrapa el foco: Tab desde el último control vuelve al primero (El foco no se escapa)", async () => {
    const usuario = userEvent.setup();
    render(<PruebaConFila />);
    await usuario.click(screen.getByRole("button", { name: "Agregar unidad" }));

    const cerrar = screen.getByRole("button", { name: "Cerrar" });
    const guardar = screen.getByRole("button", { name: "Guardar" });
    guardar.focus();
    await usuario.tab();
    // "Guardar" es el último control del panel: Tab vuelve al primero
    // ("Cerrar"), sin escaparse hacia el resto de la página.
    expect(document.activeElement).toBe(cerrar);
  });

  it("se cierra con Esc y devuelve el foco a quien lo abrió (Cerrar el panel)", async () => {
    const usuario = userEvent.setup();
    render(<PruebaConFila />);
    const fila = screen.getByRole("button", { name: "Agregar unidad" });
    await usuario.click(fila);
    expect(screen.getByLabelText("Identificador")).toBeTruthy();

    await usuario.keyboard("{Escape}");
    expect(screen.queryByLabelText("Identificador")).toBeNull();
    expect(document.activeElement).toBe(fila);
  });

  it("se cierra con el botón visible", async () => {
    const usuario = userEvent.setup();
    render(<PruebaConFila />);
    await usuario.click(screen.getByRole("button", { name: "Agregar unidad" }));
    await usuario.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(screen.queryByLabelText("Identificador")).toBeNull();
  });

  it("la ayuda abierta DENTRO del panel y Esc dos veces: primero cierra la ayuda, no pierde lo cargado; el segundo Esc cierra el panel", async () => {
    const usuario = userEvent.setup();
    render(<PruebaConFila />);
    const fila = screen.getByRole("button", { name: "Agregar unidad" });
    await usuario.click(fila);

    const identificador = screen.getByLabelText("Identificador") as HTMLInputElement;
    await usuario.type(identificador, "A01");

    await usuario.click(screen.getByRole("button", { name: /Ayuda/ }));
    expect(screen.getByText("¿Qué hago acá?")).toBeTruthy();

    await usuario.keyboard("{Escape}");
    // la ayuda se cerró, el panel sigue abierto y lo cargado no se perdió
    expect(screen.queryByText("¿Qué hago acá?")).toBeNull();
    expect((screen.getByLabelText("Identificador") as HTMLInputElement).value).toBe("A01");

    await usuario.keyboard("{Escape}");
    expect(screen.queryByLabelText("Identificador")).toBeNull();
    expect(document.activeElement).toBe(fila);
  });

  it("sin violaciones de axe, abierto", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<PruebaConFila />);
    await usuario.click(screen.getByRole("button", { name: "Agregar unidad" }));
    await sinViolaciones(container);
  });
});
