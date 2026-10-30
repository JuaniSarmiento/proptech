/**
 * @vitest-environment jsdom
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import type { Grupo, Unidad } from "../../../../lib/api/tipos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaGrupos } from "./Pantalla";

// pulido-2 (3d), escenario "axe cubre más de un estado": sólo Generales, panel de alta
// abierto y panel con un error de campo (el test de la pantalla sólo mide el feliz).
afterEach(cleanup);

const GENERALES: Grupo = {
  id: "g0",
  administracion_id: "a",
  complejo_id: "1",
  clave: "generales",
  nombre: "Generales",
  metodo: "coeficiente",
  es_generales: true,
  activo: true,
  modo_de_coeficientes: "renormalizado",
  informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" },
  unidades: [{ unidad_id: "u1", coeficiente: "0.500000" }],
};

const UNIDADES: Unidad[] = [
  {
    id: "u1",
    complejo_id: "1",
    identificador: "1A",
    tipo: "departamento",
    piso: "1",
    coeficiente: "0.500000",
    superficie_m2: "60.00",
  },
];

function accionNula() {
  return Promise.resolve(null);
}

function accionConError() {
  return Promise.resolve({
    erroresPorCampo: { nombre: "Ya existe un grupo con este nombre." },
    erroresDesconocidos: [],
  });
}

function pantalla(grupos: Grupo[], accionCrear: typeof accionNula | typeof accionConError) {
  return (
    <PantallaGrupos
      id="1"
      nombreEdificio="Edificio API"
      grupos={grupos}
      unidadesDisponibles={UNIDADES}
      accionCrear={accionCrear}
      accionEditar={accionNula}
    />
  );
}

describe("PantallaGrupos · axe por estado", () => {
  it("sólo con Generales (sin grupos propios), sin violaciones", async () => {
    const { container } = render(pantalla([GENERALES], accionNula));
    await sinViolaciones(container);
  });

  it("panel de alta abierto, sin violaciones", async () => {
    const usuario = userEvent.setup();
    const { container } = render(pantalla([GENERALES], accionNula));
    await usuario.click(screen.getByRole("button", { name: "Agregar grupo" }));
    expect(screen.getByLabelText("Nombre")).toBeTruthy();
    await sinViolaciones(container);
  });

  it("panel con un error de campo, sin violaciones", async () => {
    const usuario = userEvent.setup();
    const { container } = render(pantalla([GENERALES], accionConError));
    await usuario.click(screen.getByRole("button", { name: "Agregar grupo" }));
    const nombre = screen.getByLabelText("Nombre");
    fireEvent.change(nombre, { target: { value: "Ascensor" } });
    await act(async () => {
      fireEvent.submit(nombre.closest("form") as HTMLFormElement);
    });
    expect(nombre.getAttribute("aria-invalid")).toBe("true");
    await sinViolaciones(container);
  });
});
