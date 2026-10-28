/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { SesionDePantalla } from "../../../../componentes/SesionDePantalla";
import PaginaPadron from "./page";

vi.mock("./acciones", () => ({
  crearUnidadAction: vi.fn(),
  editarUnidadAction: vi.fn(),
  altaVecinoAction: vi.fn(),
  revocarVecinoAction: vi.fn(),
  quitarVecinoAction: vi.fn(),
}));
vi.mock("../../../../lib/api/edificios", () => ({
  edificioPorId: async () => ({
    estado: "ok",
    datos: { nombre: "Edificio", pisos: 4, subsuelos: 1 },
  }),
}));
vi.mock("../../../../lib/api/unidades", () => ({
  padronDelEdificio: async () => ({
    estado: "ok",
    datos: {
      unidades: [
        {
          id: "u1",
          complejo_id: "1",
          identificador: "1A",
          tipo: "departamento",
          piso: "1",
          coeficiente: "1.000000",
          superficie_m2: "60.00",
        },
      ],
      informe: { suma: "1.000000", diferencia: "0.000000", estado: "ok" },
    },
  }),
}));
vi.mock("../../../../lib/api/personal", async () => ({
  vecinosPorUnidad: (await import("../../../../lib/api/vecinos")).vecinosPorUnidad,
  // GET 200 del principal: lista sin vecinos, que el consumidor convierte en Map vacío.
  listarPersonal: async () => ({ estado: "ok", datos: [] }),
}));
afterEach(cleanup);
it.each([false, true])(
  "R2D-R2 consumidor: GET personal 200 y permiso de invitar=%s",
  async (invita) => {
    const pantalla = await PaginaPadron({ params: Promise.resolve({ id: "1" }) });
    render(
      <SesionDePantalla
        value={{
          administracionId: "a",
          datos: {
            persona: { nombre: "Prueba" },
            administraciones: [
              {
                id: "a",
                nombre: "A",
                acciones: {
                  administracion: [
                    "ver_personal",
                    ...(invita ? ["invitar_usuarios_y_asignar_edificios"] : []),
                  ],
                  todos_los_edificios: ["configurar_padron"],
                  por_edificio: {},
                },
              },
            ],
          },
        }}
      >
        {pantalla}
      </SesionDePantalla>,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "1A" }));
    if (invita) expect(screen.getByRole("button", { name: "Agregar vecino" })).toBeTruthy();
    else expect(screen.queryByRole("button", { name: "Agregar vecino" })).toBeNull();
  },
);
