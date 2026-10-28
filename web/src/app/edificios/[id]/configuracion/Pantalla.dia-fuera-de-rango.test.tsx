/**
 * @vitest-environment jsdom
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { crearVersionDeConfiguracion } from "../../../../lib/api/configuracion";
import type { VersionDelHistorial } from "../../../../lib/api/tipos";
import { crearVersionDeConfiguracionAction } from "./acciones";
import { PantallaConfiguracion } from "./Pantalla";

// pulido-2 (3d), escenario "Día 31": hoy lo frena el `<input type="number" max=28>`
// del navegador, no la aplicación. Acá se manda el formulario SIN esa validación
// nativa (`fireEvent.submit` no la corre), con la acción real y la API simulada
// respondiendo el 422 que da la real, para probar que la pantalla marca el campo.
vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
// Sin importActual: el módulo real arrastra `server-only`, que no resuelve bajo jsdom.
vi.mock("../../../../lib/api/configuracion", () => ({ crearVersionDeConfiguracion: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const VIGENTE: VersionDelHistorial = {
  id: "v1",
  complejo_id: "e1",
  vigente_desde: "2026-10-19",
  tasa_mensual: "3.00",
  dias_de_gracia: 0,
  forma_de_calculo: "proporcional_por_dia",
  porcentaje_fondo: "0.00",
  dia_de_vencimiento: 10,
  modalidad_de_vencimiento: "doble",
  dia_segundo_vencimiento: 20,
  recargo_segundo_vencimiento: "1.50",
  umbral_saldo_chico: "500.00",
  autor_id: "a1",
  autor_nombre: "Alberto",
  creada_en: "2026-10-19T22:06:28Z",
};

async function abrirPanelYEnviarSinValidacionNativa(
  campo: "Día de vencimiento" | "Segundo vencimiento",
  valor: string,
) {
  const usuario = userEvent.setup();
  render(
    <PantallaConfiguracion
      id="e1"
      nombreEdificio="Edificio API"
      vigente={VIGENTE}
      historial={[VIGENTE]}
      accionCrear={crearVersionDeConfiguracionAction.bind(null, "e1")}
    />,
  );
  await usuario.click(screen.getByRole("button", { name: "Cambiar configuración" }));
  fireEvent.change(screen.getByLabelText("Rige desde"), { target: { value: "2099-01-01" } });
  const entrada = screen.getByLabelText(campo) as HTMLInputElement;
  fireEvent.change(entrada, { target: { value: valor } });
  // El navegador real frenaría acá por `max=28`; `submit` salta esa validación.
  await act(async () => {
    fireEvent.submit(entrada.closest("form") as HTMLFormElement);
  });
  return entrada;
}

it.each([
  ["Día de vencimiento", "31", "dia_de_vencimiento"],
  ["Día de vencimiento", "29", "dia_de_vencimiento"],
  ["Segundo vencimiento", "31", "dia_segundo_vencimiento"],
])(
  'escenario "Día 31": con %s=%s fuera de rango marca sólo ese campo',
  async (etiqueta, valor, nombre) => {
    vi.mocked(crearVersionDeConfiguracion).mockResolvedValue({
      estado: "invalido",
      errores: [{ campo: nombre, motivo: "value_error" }],
    });

    const entrada = await abrirPanelYEnviarSinValidacionNativa(
      etiqueta as "Día de vencimiento" | "Segundo vencimiento",
      valor,
    );

    // La aplicación mandó el valor tal cual a la API: no lo frenó nadie antes.
    expect(crearVersionDeConfiguracion).toHaveBeenCalledTimes(1);
    const enviado = vi.mocked(crearVersionDeConfiguracion).mock.calls[0]?.[1];
    expect(enviado?.[nombre as "dia_de_vencimiento"]).toBe(Number(valor));

    // El campo, y sólo ese, queda marcado y asociado a su mensaje.
    expect(entrada.getAttribute("aria-invalid")).toBe("true");
    const idMensaje = entrada.getAttribute("aria-describedby") ?? "";
    expect(idMensaje).not.toBe("");
    expect(document.getElementById(idMensaje.split(" ")[0] ?? "")?.textContent).toContain(
      "Este valor no es válido.",
    );
    for (const otra of ["Tasa mensual", "Rige desde", "Días de gracia"]) {
      expect(screen.getByLabelText(otra).getAttribute("aria-invalid")).toBe("false");
    }
  },
);
