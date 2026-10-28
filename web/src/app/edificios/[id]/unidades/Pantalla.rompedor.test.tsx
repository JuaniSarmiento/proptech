/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it } from "vitest";
import type { Unidad } from "../../../../lib/api/tipos";
import { PantallaPadron } from "./Pantalla";

afterEach(cleanup);

const base: Unidad = {
  id: "u1",
  complejo_id: "1",
  identificador: "1A",
  tipo: "departamento",
  piso: "SS1",
  coeficiente: "0.500000",
  superficie_m2: "60.00",
};
const nula = () => Promise.resolve(null);

function pantalla(unidades: Unidad[], subsuelos: number) {
  return (
    <PantallaPadron
      id="1"
      nombreEdificio="E"
      pisosDelEdificio={3}
      subsuelosDelEdificio={subsuelos}
      unidades={unidades}
      informe={{ suma: "0.500000", diferencia: "-0.500000", estado: "fuera_de_tolerancia" }}
      accionCrear={nula}
      accionEditar={nula}
    />
  );
}

it("rompedor: editar una unidad con piso SS1 la deja preseleccionada y la lista de 2 subsuelos va en orden de altura", async () => {
  const usuario = userEvent.setup();
  render(pantalla([base], 2));
  await usuario.click(screen.getByRole("button", { name: "1A" }));
  const piso = screen.getByLabelText("Piso") as HTMLSelectElement;
  expect(Array.from(piso.options).map((o) => o.value)).toEqual([
    "",
    "SS2",
    "SS1",
    "PB",
    "1",
    "2",
    "3",
  ]);
  expect(piso.value).toBe("SS1");
});

it("rompedor: unidad migrada con piso null queda en la opción vacía, no en la primera real", async () => {
  const usuario = userEvent.setup();
  render(pantalla([{ ...base, piso: null }], 2));
  await usuario.click(screen.getByRole("button", { name: "1A" }));
  const piso = screen.getByLabelText("Piso") as HTMLSelectElement;
  expect(piso.value).toBe("");
});
