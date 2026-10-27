/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Resumen } from "../../../lib/api/tipos";
import { sinViolaciones } from "../../../lib/test/accesibilidad";
import { PantallaResumen } from "./Pantalla";

// `SelectorDeUbicacion` llama a estas server actions; mockeadas para que
// el árbol de imports nunca llegue a `server-only` (D3, tarea 6.1).
vi.mock("../../../componentes/accionesGeoref", () => ({
  provinciasAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
  departamentosDeAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
  localidadesDeAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
}));

afterEach(cleanup);

function accionNula() {
  return Promise.resolve(null);
}

const RESUMEN_EDIFICIO_NUEVO: Resumen = {
  nombre: "Edificio Nuevo",
  localidad: "Mendoza",
  provincia_id: "50",
  departamento_id: "50007",
  localidad_id: "50007010",
  calle_y_numero: null,
  pisos: 4,
  subsuelos: 1,
  cantidad_unidades: 0,
  unidades_sin_piso_completo: 0,
  estado_migracion: "pendiente",
  informe: { suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" },
  pasos: {
    ubicacion: "hecho",
    unidades: "falta",
    coeficientes: "falta",
    grupos: "falta",
    categorias: "falta",
    intereses_y_vencimiento: "falta",
    saldos_previos: "falta",
  },
  listo_para_liquidar: false,
};

describe("PantallaResumen", () => {
  it("un edificio recién creado muestra el checklist con ubicación hecha y el resto en falta (Edificio recién creado)", () => {
    render(
      <PantallaResumen
        id="1"
        resumen={RESUMEN_EDIFICIO_NUEVO}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    const items = screen.getAllByText("Falta");
    expect(items.length).toBe(6);
    expect(screen.queryByText("Listo para liquidar")).toBeNull();
  });

  it('"la web no calcula": 13 unidades con el paso en "falta" según la API se muestra en falta (Datos que no cuadran con el informe)', () => {
    render(
      <PantallaResumen
        id="1"
        resumen={{ ...RESUMEN_EDIFICIO_NUEVO, cantidad_unidades: 13 }}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText("13")).toBeTruthy();
    const items = screen.getAllByText("Falta");
    expect(items.length).toBe(6);
  });

  it('cada paso separa la etiqueta de su estado (no "Cargar unidadesFalta") y marca el estado en la fila (pulido 3b)', () => {
    render(
      <PantallaResumen
        id="1"
        resumen={RESUMEN_EDIFICIO_NUEVO}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    const checklist = screen.getByRole("list", { name: "Puesta a punto del edificio" });
    const pasos = within(checklist).getAllByRole("listitem");
    // El paso 0 ahora es "ubicación" (D3, 3.8); el segundo es "Cargar unidades".
    const segundo = pasos[1] as HTMLElement;
    // Enmienda 20/10: entre la etiqueta y el estado ahora va la línea gris
    // que explica el paso. Lo que se sigue exigiendo: la etiqueta es SU
    // enlace (sin el estado pegado) y el estado es un elemento aparte, al
    // final de la fila.
    expect(within(segundo).getByRole("link").textContent).toBe("Cargar unidades");
    const estado = within(segundo).getByText("Falta");
    expect(estado.closest("a")).toBeNull();
    expect(segundo.textContent).toMatch(/Falta$/);
    expect(segundo.getAttribute("data-estado")).toBe("falta");
  });

  it("un edificio completo muestra Listo para liquidar", () => {
    render(
      <PantallaResumen
        id="1"
        resumen={{
          ...RESUMEN_EDIFICIO_NUEVO,
          listo_para_liquidar: true,
          informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" },
          pasos: {
            ubicacion: "hecho",
            unidades: "hecho",
            coeficientes: "hecho",
            grupos: "hecho",
            categorias: "hecho",
            intereses_y_vencimiento: "hecho",
            saldos_previos: "hecho",
          },
        }}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByText("Listo para liquidar")).toBeTruthy();
    expect(screen.getAllByText("Hecho").length).toBe(7);
  });

  it("cada paso enlaza a su pantalla, y el último a saldos previos (D11)", () => {
    render(
      <PantallaResumen
        id="42"
        resumen={RESUMEN_EDIFICIO_NUEVO}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByRole("link", { name: /Cargar unidades/ }).getAttribute("href")).toBe(
      "/edificios/42/unidades",
    );
    expect(screen.getByRole("link", { name: /sin saldos previos/ }).getAttribute("href")).toBe(
      "/edificios/42/saldos-previos",
    );
  });

  it('barra de progreso "N de 7 pasos" contando lo que marcó la API, y "Tu próximo paso" lleva al primero que falta', () => {
    render(
      <PantallaResumen
        id="7"
        resumen={{
          ...RESUMEN_EDIFICIO_NUEVO,
          pasos: { ...RESUMEN_EDIFICIO_NUEVO.pasos, unidades: "hecho", grupos: "hecho" },
        }}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByRole("progressbar", { name: "3 de 7 pasos" })).toBeTruthy();
    const proximo = screen.getByRole("region", { name: "Tu próximo paso" });
    expect(within(proximo).getByText(/Revisar coeficientes/)).toBeTruthy();
    expect(
      within(proximo)
        .getByRole("link", { name: /Completar este paso/ })
        .getAttribute("href"),
    ).toBe("/edificios/7/unidades");
  });

  it('D3 (6.1) "Editar el edificio desde el resumen": "Editar" abre el panel con los datos actuales', async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaResumen
        id="1"
        resumen={RESUMEN_EDIFICIO_NUEVO}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    await usuario.click(screen.getByRole("button", { name: "Editar" }));
    expect(screen.getByLabelText("Nombre")).toHaveProperty("value", "Edificio Nuevo");
    expect(screen.getByLabelText("Pisos")).toHaveProperty("value", "4");
  });

  it('D3 (6.1) "Edificio migrado sin ubicación": el paso "ubicación" se completa desde el resumen', async () => {
    const usuario = userEvent.setup();
    const accionEditar = vi.fn().mockResolvedValue(null);
    render(
      <PantallaResumen
        id="1"
        resumen={{
          ...RESUMEN_EDIFICIO_NUEVO,
          provincia_id: null,
          departamento_id: null,
          localidad_id: null,
          localidad: null,
          pisos: null,
          subsuelos: null,
          pasos: { ...RESUMEN_EDIFICIO_NUEVO.pasos, ubicacion: "falta" },
        }}
        vigente={null}
        accionEditar={accionEditar}
      />,
    );
    const proximo = screen.getByRole("region", { name: "Tu próximo paso" });
    await usuario.click(within(proximo).getByRole("button", { name: /Completar este paso/ }));
    expect(screen.getByLabelText("Provincia")).toBeTruthy();
  });

  it('QA: la ubicación ya hecha NO tiene botón propio (editar ya vive en "Datos del edificio" → "Editar"; un segundo botón para lo mismo es redundante)', () => {
    render(
      <PantallaResumen
        id="1"
        resumen={RESUMEN_EDIFICIO_NUEVO}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    const checklist = screen.getByRole("list", { name: "Puesta a punto del edificio" });
    const primero = within(checklist).getAllByRole("listitem")[0] as HTMLElement;
    expect(within(primero).getByText("Completar la ubicación")).toBeTruthy();
    expect(within(primero).queryByRole("button")).toBeNull();
  });

  it('la ubicación sin completar sigue teniendo su botón (único punto de entrada, sin página propia) con "boton-enlace"', () => {
    render(
      <PantallaResumen
        id="1"
        resumen={{
          ...RESUMEN_EDIFICIO_NUEVO,
          pasos: { ...RESUMEN_EDIFICIO_NUEVO.pasos, ubicacion: "falta" },
        }}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    expect(screen.getByRole("button", { name: "Completar la ubicación" }).className).toBe(
      "boton-enlace",
    );
  });

  it("sin violaciones de axe", async () => {
    const { container } = render(
      <PantallaResumen
        id="1"
        resumen={RESUMEN_EDIFICIO_NUEVO}
        vigente={null}
        accionEditar={accionNula}
      />,
    );
    await sinViolaciones(container);
  });
});
