/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Grupo, Unidad } from "../../../../lib/api/tipos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaGrupos } from "./Pantalla";

afterEach(cleanup);

const GENERALES: Grupo = {
  id: "g0",
  administracion_id: "a",
  complejo_id: "1",
  clave: "generales",
  nombre: "Generales",
  metodo: "coeficiente",
  es_generales: true,
  modo_de_coeficientes: "renormalizado",
  informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" },
  unidades: [{ unidad_id: "u1", coeficiente: "0.500000" }],
};

const ASCENSOR: Grupo = {
  id: "g1",
  administracion_id: "a",
  complejo_id: "1",
  clave: "ascensor",
  nombre: "Ascensor",
  metodo: "coeficiente",
  es_generales: false,
  modo_de_coeficientes: "propios",
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

describe("PantallaGrupos", () => {
  it("RF-F-2: guardar desde el estado vacío devuelve el foco al encabezado tras revalidar", async () => {
    const usuario = userEvent.setup();
    const accionCrear = vi
      .fn()
      .mockResolvedValue({ ok: true, erroresPorCampo: {}, erroresDesconocidos: [] });
    const vista = (conDatos: boolean) => (
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={conDatos ? [ASCENSOR] : []}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />
    );
    const { rerender } = render(vista(false));
    const botones = screen.getAllByRole("button", { name: "Agregar grupo" });
    const encabezado = botones[0];
    await usuario.click(botones[1] as HTMLElement);
    await usuario.type(screen.getByLabelText("Clave"), "ascensor");
    await usuario.type(screen.getByLabelText("Nombre"), "Ascensor");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(accionCrear).toHaveBeenCalledTimes(1);
    // La respuesta del servidor reemplaza el vacío y desmonta su botón.
    rerender(vista(true));
    expect(document.activeElement).toBe(encabezado);
    expect(encabezado?.isConnected).toBe(true);
  });

  it('"Generales" se muestra primero, automático y sin botones de edición (Generales)', () => {
    render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES, ASCENSOR]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    const lista = screen.getByRole("list", { name: "Grupos de reparto" });
    const filas = within(lista).getAllByRole("listitem");
    expect(filas[0]?.textContent).toContain("Generales");
    expect(screen.queryByRole("button", { name: "Editar Generales" })).toBeNull();
    expect(screen.getByText(/se calcula solo y no se edita/i)).toBeTruthy();
  });

  it('el método se lee en castellano ("por coeficiente"), no con la clave cruda de la API (pulido 3b)', () => {
    render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES, ASCENSOR]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    const boton = screen.getByRole("button", { name: /Ascensor/ });
    expect(boton.textContent).toContain("por coeficiente");
    expect(boton.textContent).not.toMatch(/· coeficiente ·/);
  });

  it('un grupo que no es "Generales" abre el panel de edición al tocarlo', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES, ASCENSOR]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: /Ascensor/ }));
    expect(screen.getByLabelText("Nombre")).toHaveProperty("value", "Ascensor");
    expect(screen.getByLabelText("Coeficiente de 1A")).toHaveProperty("value", "0,500000");
  });

  it('"Agregar grupo" abre el panel de alta, con clave, nombre, método y modo', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Agregar grupo" }));
    expect(screen.getByLabelText("Clave")).toBeTruthy();
    expect(screen.getByLabelText("Nombre")).toBeTruthy();
  });

  it("cambiar el modo en edición avisa que se reescriben los coeficientes", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES, ASCENSOR]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: /Ascensor/ }));
    await usuario.selectOptions(screen.getByLabelText("Modo"), "renormalizado");
    expect(screen.getByText(/se van a reescribir los coeficientes/i)).toBeTruthy();
  });

  it('"Guardar a medias": el segundo pedido falla y avisa qué se guardó y qué no (Guardar a medias)', async () => {
    const accionEditar = vi.fn().mockResolvedValue({
      erroresPorCampo: {},
      erroresDesconocidos: ["Se guardaron el nombre y el método; las unidades no."],
    });
    const usuario = userEvent.setup();
    render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES, ASCENSOR]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionEditar}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: /Ascensor/ }));
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      await screen.findByText("Se guardaron el nombre y el método; las unidades no."),
    ).toBeTruthy();
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES, ASCENSOR]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await sinViolaciones(container);
  });

  it("R3C-4 · tocar otro grupo con el panel abierto no mezcla el nombre tipeado con el id del otro", async () => {
    const BAULERAS: Grupo = { ...ASCENSOR, id: "g2", clave: "bauleras", nombre: "Bauleras" };
    const accionEditar = vi.fn().mockResolvedValue(null);
    const usuario = userEvent.setup();
    const { container } = render(
      <PantallaGrupos
        id="1"
        nombreEdificio="Edificio API"
        grupos={[GENERALES, ASCENSOR, BAULERAS]}
        unidadesDisponibles={UNIDADES}
        accionCrear={accionNula}
        accionEditar={accionEditar}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: /Ascensor/ }));
    const nombre = screen.getByLabelText("Nombre") as HTMLInputElement;
    await usuario.clear(nombre);
    await usuario.type(nombre, "Ascensor renombrado a medias");
    await usuario.click(screen.getByRole("button", { name: /Bauleras/ }));
    const oculto = container.querySelector('input[name="grupo_id"]') as HTMLInputElement;
    expect({
      id: oculto.value,
      nombre: (screen.getByLabelText("Nombre") as HTMLInputElement).value,
    }).toEqual({ id: "g2", nombre: "Bauleras" });
  });
});
