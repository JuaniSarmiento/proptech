/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Unidad } from "../../../../lib/api/tipos";
import type { VecinoDeUnidad } from "../../../../lib/api/vecinos";
import { sinViolaciones } from "../../../../lib/test/accesibilidad";
import { PantallaPadron } from "./Pantalla";

afterEach(cleanup);

const UNIDAD_1A: Unidad = {
  id: "u1",
  complejo_id: "1",
  identificador: "1A",
  tipo: "departamento",
  piso: "1",
  coeficiente: "0.500000",
  superficie_m2: "60.00",
};

function accionNula() {
  return Promise.resolve(null);
}

describe("PantallaPadron", () => {
  it("RF-F-2: guardar desde el estado vacío devuelve el foco al encabezado tras revalidar", async () => {
    const usuario = userEvent.setup();
    const accionCrear = vi
      .fn()
      .mockResolvedValue({ ok: true, erroresPorCampo: {}, erroresDesconocidos: [] });
    const vista = (conDatos: boolean) => (
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={conDatos ? [UNIDAD_1A] : []}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />
    );
    const { rerender } = render(vista(false));
    const botones = screen.getAllByRole("button", { name: "Agregar unidad" });
    const encabezado = botones[0];
    await usuario.click(botones[1] as HTMLElement);
    await usuario.type(screen.getByLabelText("Identificador"), "1A");
    await usuario.type(screen.getByLabelText("Superficie (m²)"), "60.00");
    await usuario.type(screen.getByLabelText("Coeficiente"), "1.000000");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(accionCrear).toHaveBeenCalledTimes(1);
    // La respuesta del servidor reemplaza el vacío y desmonta su botón.
    rerender(vista(true));
    expect(document.activeElement).toBe(encabezado);
    expect(encabezado?.isConnected).toBe(true);
  });

  it('informe "fuera_de_tolerancia" con diferencia -0.000200 se muestra en texto (Fuera de tolerancia)', () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "0.999800", diferencia: "-0.000200", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText(/falta 0,0200 %/)).toBeTruthy();
  });

  it("sin unidades muestra el estado vacío con Agregar unidad", () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText(/Todavía no cargaste unidades/)).toBeTruthy();
  });

  it("la tabla muestra números tabulares alineados a la derecha, con formato argentino (D6)", () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText("60,00")).toBeTruthy();
    expect(screen.getByText("0,500000")).toBeTruthy();
  });

  it('"Agregar unidad" abre el panel con el formulario de alta', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    expect(screen.getByLabelText("Identificador")).toBeTruthy();
  });

  it("tocar una fila abre el panel con los datos de esa unidad (edición)", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "1A" }));
    expect(screen.getByLabelText("Identificador")).toHaveProperty("value", "1A");
    expect(screen.getByLabelText("Superficie (m²)")).toHaveProperty("value", "60,00");
    expect(screen.getByLabelText("Coeficiente")).toHaveProperty("value", "0,500000");
  });

  it("409 de identificador repetido marca el campo identificador, sin el texto técnico (Identificador repetido)", async () => {
    const accionCrear = vi.fn().mockResolvedValue({
      erroresPorCampo: { identificador: "Ya existe una unidad con este identificador." },
      erroresDesconocidos: [],
    });
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    await usuario.type(screen.getByLabelText("Identificador"), "1A");
    await usuario.type(screen.getByLabelText("Superficie (m²)"), "60.00");
    await usuario.type(screen.getByLabelText("Coeficiente"), "0.500000");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      (await screen.findAllByText("Ya existe una unidad con este identificador.")).length,
    ).toBeGreaterThan(0);
  });

  it('el tipo se muestra con su etiqueta ("Departamento"), no con la clave cruda de la API (pulido 3b)', () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByRole("cell", { name: "Departamento" })).toBeTruthy();
  });

  it("prueba con 200 unidades: la tabla renderiza sin romper", () => {
    const unidades: Unidad[] = Array.from({ length: 200 }, (_, i) => ({
      ...UNIDAD_1A,
      id: `u${i}`,
      identificador: `U${i}`,
    }));
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={unidades}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getAllByRole("row").length).toBe(201); // 200 + encabezado
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await sinViolaciones(container);
  });

  it("R3C-4 · tocar otra fila con el panel abierto no mezcla lo tipeado de una unidad con el id de otra", async () => {
    const UNIDAD_2B: Unidad = {
      ...UNIDAD_1A,
      id: "u2",
      identificador: "2B",
      coeficiente: "0.300000",
    };
    const accionEditar = vi.fn().mockResolvedValue(null);
    const usuario = userEvent.setup();
    const { container } = render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A, UNIDAD_2B]}
        informe={{ suma: "0.800000", diferencia: "-0.200000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionEditar}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "1A" }));
    const coeficiente = screen.getByLabelText("Coeficiente") as HTMLInputElement;
    await usuario.clear(coeficiente);
    await usuario.type(coeficiente, "0.700000");
    // El panel no es modal (aria-modal=false, fijo a la derecha): la tabla
    // sigue clicable, así que tocar otra fila sin cerrar es un camino real.
    await usuario.click(screen.getByRole("button", { name: "2B" }));
    const oculto = container.querySelector('input[name="unidad_id"]') as HTMLInputElement;
    expect({
      id: oculto.value,
      coeficiente: (screen.getByLabelText("Coeficiente") as HTMLInputElement).value,
    }).toEqual({ id: "u2", coeficiente: "0,300000" });
  });
});

describe("PantallaPadron, vecinos (7.4)", () => {
  const VECINO_PENDIENTE: VecinoDeUnidad = {
    persona_id: "p1",
    asignacion_id: "a1",
    nombre: "Vecino Uno",
    vinculo: "propietario",
    invitacion: { invitacion_id: "i1", estado: "pendiente" },
  };
  const VECINO_ACEPTADO: VecinoDeUnidad = {
    persona_id: "p2",
    asignacion_id: "a2",
    nombre: "Vecino Dos",
    vinculo: "inquilino",
    invitacion: { invitacion_id: "i2", estado: "aceptada" },
  };

  function accionSimpleNula() {
    return Promise.resolve(null);
  }

  it("sin vecinosPorUnidad (no super admin): sin columna Vecinos ni sección en el panel", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionSimpleNula}
        accionEditar={accionSimpleNula}
      />,
    );
    expect(screen.queryByRole("columnheader", { name: "Vecinos" })).toBeNull();
    await usuario.click(screen.getByRole("button", { name: "1A" }));
    expect(screen.queryByRole("heading", { name: "Vecinos" })).toBeNull();
  });

  it("con vecinosPorUnidad: columna con cantidad y pendientes; sección con Revocar y Quitar", async () => {
    const usuario = userEvent.setup();
    const mapa = new Map([["u1", [VECINO_PENDIENTE, VECINO_ACEPTADO]]]);
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionSimpleNula}
        accionEditar={accionSimpleNula}
        vecinosPorUnidad={mapa}
        accionAltaVecino={accionSimpleNula}
        accionRevocarVecino={accionSimpleNula}
        accionQuitarVecino={accionSimpleNula}
      />,
    );
    const fila = screen.getByRole("button", { name: "1A" }).closest("tr") as HTMLElement;
    expect(within(fila).getByText("2 (1 pendiente)")).toBeTruthy();

    await usuario.click(screen.getByRole("button", { name: "1A" }));
    expect(screen.getByRole("heading", { name: "Vecinos" })).toBeTruthy();
    const filaUno = screen.getByText("Vecino Uno").closest("li") as HTMLElement;
    expect(within(filaUno).getByText(/Propietario.*Pendiente/)).toBeTruthy();
    expect(within(filaUno).getByRole("button", { name: "Revocar" })).toBeTruthy();
    const filaDos = screen.getByText("Vecino Dos").closest("li") as HTMLElement;
    expect(within(filaDos).getByText(/Inquilino.*Aceptada/)).toBeTruthy();
    expect(within(filaDos).queryByRole("button", { name: "Revocar" })).toBeNull();
    expect(within(filaDos).getByRole("button", { name: "Quitar" })).toBeTruthy();
  });

  it("agregar vecino manda unidad_id, nombre, email y vínculo a la acción", async () => {
    const usuario = userEvent.setup();
    const accionAlta = vi
      .fn()
      .mockResolvedValue({ erroresPorCampo: {}, erroresDesconocidos: [], ok: true });
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionSimpleNula}
        accionEditar={accionSimpleNula}
        vecinosPorUnidad={new Map()}
        accionAltaVecino={accionAlta}
        accionRevocarVecino={accionSimpleNula}
        accionQuitarVecino={accionSimpleNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "1A" }));
    await usuario.type(screen.getByLabelText("Nombre del vecino"), "Nuevo Vecino");
    await usuario.type(screen.getByLabelText("Email del vecino"), "vecino@test.com");
    await usuario.click(screen.getByRole("button", { name: "Agregar vecino" }));
    expect(accionAlta).toHaveBeenCalledTimes(1);
    const form = accionAlta.mock.calls[0]?.[1] as FormData;
    expect(form.get("unidad_id")).toBe("u1");
    expect(form.get("nombre")).toBe("Nuevo Vecino");
    expect(form.get("email")).toBe("vecino@test.com");
    expect(form.get("vinculo")).toBe("propietario");
  });

  it("sin violaciones de axe con la sección de vecinos abierta", async () => {
    const usuario = userEvent.setup();
    const mapa = new Map([["u1", [VECINO_PENDIENTE]]]);
    const { container } = render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[UNIDAD_1A]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionSimpleNula}
        accionEditar={accionSimpleNula}
        vecinosPorUnidad={mapa}
        accionAltaVecino={accionSimpleNula}
        accionRevocarVecino={accionSimpleNula}
        accionQuitarVecino={accionSimpleNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "1A" }));
    await sinViolaciones(container);
  });

  it('D7 (5.4) "Identificador demasiado largo": marca el campo antes de llamar a la acción', async () => {
    const usuario = userEvent.setup();
    const accionCrear = vi.fn();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    fireEvent.change(screen.getByLabelText("Identificador"), { target: { value: "a".repeat(41) } });
    await usuario.type(screen.getByLabelText("Superficie (m²)"), "60.00");
    await usuario.type(screen.getByLabelText("Coeficiente"), "0.5");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    expect(
      (await screen.findAllByText(/no puede tener más de 40 caracteres/i)).length,
    ).toBeGreaterThan(0);
    expect(accionCrear).not.toHaveBeenCalled();
  });

  it('D7 (5.4) "Ayuda del identificador": muestra el máximo', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    expect(screen.getByText(/hasta 40 caracteres/i)).toBeTruthy();
  });

  it('D7 (5.4) "Coeficiente cargado como porcentaje": marca el campo antes de llamar a la acción', async () => {
    const usuario = userEvent.setup();
    const accionCrear = vi.fn();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    await usuario.type(screen.getByLabelText("Identificador"), "1A");
    await usuario.type(screen.getByLabelText("Superficie (m²)"), "60.00");
    await usuario.type(screen.getByLabelText("Coeficiente"), "50");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    expect((await screen.findAllByText(/cargalo como proporción/i)).length).toBeGreaterThan(0);
    expect(accionCrear).not.toHaveBeenCalled();
  });

  it('D7 (5.4) "El error previo al envío tiene el mismo aria-describedby que el error de la API"', async () => {
    const usuario = userEvent.setup();
    const accionCrear = vi.fn().mockResolvedValue({
      erroresPorCampo: { identificador: "Ya existe una unidad con este identificador." },
      erroresDesconocidos: [],
    });
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionCrear}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    fireEvent.change(screen.getByLabelText("Identificador"), { target: { value: "a".repeat(41) } });
    await usuario.type(screen.getByLabelText("Superficie (m²)"), "60.00");
    await usuario.type(screen.getByLabelText("Coeficiente"), "0.5");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    const idPrevio = screen.getByLabelText("Identificador").getAttribute("aria-describedby");
    // Se corrige y manda un identificador válido que la API rechaza por otro motivo (409).
    await usuario.clear(screen.getByLabelText("Identificador"));
    await usuario.type(screen.getByLabelText("Identificador"), "1A");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    await waitFor(() =>
      expect(
        screen.getAllByText("Ya existe una unidad con este identificador.").length,
      ).toBeGreaterThan(0),
    );
    const idDespues = screen.getByLabelText("Identificador").getAttribute("aria-describedby");
    expect(idPrevio).toBe(idDespues);
  });

  it('D3 (6.2) "Elegir el piso de la lista del edificio": la lista trae el vocabulario del edificio', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[]}
        informe={{ suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Agregar unidad" })[0] as HTMLElement,
    );
    const piso = screen.getByLabelText("Piso") as HTMLSelectElement;
    expect(piso.tagName).toBe("SELECT");
    const opciones = Array.from(piso.options).map((o) => o.value);
    expect(opciones).toEqual(["", "PB", "1", "2", "3", "4", "SS1"]);
  });

  it('D3 (6.2) "Unidades con el piso sin completar": se muestran marcadas en la tabla', () => {
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[{ ...UNIDAD_1A, piso: null }]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText("Sin completar")).toBeTruthy();
  });

  it('D3 (6.2) "Abrir una unidad migrada no guarda ningún piso solo": el panel abre con la opción vacía, sin seleccionar la primera real', async () => {
    const usuario = userEvent.setup();
    const accionEditar = vi.fn().mockResolvedValue(null);
    render(
      <PantallaPadron
        id="1"
        nombreEdificio="Edificio API"
        pisosDelEdificio={4}
        subsuelosDelEdificio={1}
        unidades={[{ ...UNIDAD_1A, piso: null }]}
        informe={{ suma: "1.000000", diferencia: "0.000000", estado: "ok" }}
        accionCrear={accionNula}
        accionEditar={accionEditar}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "1A" }));
    const piso = screen.getByLabelText("Piso") as HTMLSelectElement;
    expect(piso.value).toBe("");
    await usuario.click(screen.getByRole("button", { name: "Guardar" }));
    const cuerpo = accionEditar.mock.calls[0]?.[1] as FormData;
    expect(cuerpo.get("piso")).toBe("");
  });
});
