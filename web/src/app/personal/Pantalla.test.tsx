/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Persona } from "../../lib/api/personal";
import type { EdificioDeLista } from "../../lib/api/tipos";
import { sinViolaciones } from "../../lib/test/accesibilidad";
import { PantallaPersonal } from "./Pantalla";

afterEach(cleanup);

const EDIFICIOS: EdificioDeLista[] = [{ id: "e1", nombre: "Torre Norte", localidad: "Mendoza" }];

const PERSONAS: Persona[] = [
  {
    persona_id: "p1",
    nombre: "Ana Pérez",
    email: "ana@test.com",
    vinculado: true,
    asignaciones: [
      {
        asignacion_id: "a1",
        rol: "super_admin",
        complejo_id: null,
        unidad_id: null,
        vinculo: null,
      },
    ],
    invitacion: { invitacion_id: "i1", estado: "aceptada" },
  },
  {
    persona_id: "p2",
    nombre: "Beto Gómez",
    email: "beto@test.com",
    vinculado: false,
    asignaciones: [
      { asignacion_id: "a2", rol: "auxiliar", complejo_id: "e1", unidad_id: null, vinculo: null },
    ],
    invitacion: { invitacion_id: "i2", estado: "fallida" },
  },
];

function accionInvitarNula() {
  return Promise.resolve(null);
}
function accionSimpleNula() {
  return Promise.resolve(null);
}

describe("PantallaPersonal", () => {
  it("lista cada persona con su perfil, su alcance y el estado de invitación en texto", () => {
    render(
      <PantallaPersonal
        personas={PERSONAS}
        edificios={EDIFICIOS}
        accionInvitar={accionInvitarNula}
        accionRevocar={accionSimpleNula}
        accionQuitar={accionSimpleNula}
      />,
    );
    const filaAna = screen.getByText("Ana Pérez").closest("tr") as HTMLElement;
    expect(within(filaAna).getByText("Super admin")).toBeTruthy();
    expect(within(filaAna).getByText("Aceptada")).toBeTruthy();

    const filaBeto = screen.getByText("Beto Gómez").closest("tr") as HTMLElement;
    expect(within(filaBeto).getByText("Auxiliar")).toBeTruthy();
    expect(within(filaBeto).getByText(/Torre Norte/)).toBeTruthy();
    // Ajuste del shape (21/10/2026), corregido por el auditor del 2b (fila 2, 21/10/2026):
    // el worker NO reintenta un 4xx definitivo (tareas.py:278-292); "fallida" ofrece la
    // acción real, que ya existe en esta fila: revocar e invitar de nuevo.
    expect(
      within(filaBeto).getByText("No se pudo enviar. Revocala e invitá de nuevo."),
    ).toBeTruthy();
    expect(within(filaBeto).queryByText(/reintentar/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /reenviar/i })).toBeNull();
  });

  it("aceptada no ofrece Revocar; fallida sí (estado abierto, L-030)", () => {
    render(
      <PantallaPersonal
        personas={PERSONAS}
        edificios={EDIFICIOS}
        accionInvitar={accionInvitarNula}
        accionRevocar={accionSimpleNula}
        accionQuitar={accionSimpleNula}
      />,
    );
    const filaAna = screen.getByText("Ana Pérez").closest("tr") as HTMLElement;
    expect(within(filaAna).queryByRole("button", { name: "Revocar" })).toBeNull();
    const filaBeto = screen.getByText("Beto Gómez").closest("tr") as HTMLElement;
    expect(within(filaBeto).getByRole("button", { name: "Revocar" })).toBeTruthy();
  });

  it("el perfil auxiliar fuerza alcance de edificio y oculta el selector de alcance", async () => {
    const usuario = userEvent.setup();
    render(
      <PantallaPersonal
        personas={[]}
        edificios={EDIFICIOS}
        accionInvitar={accionInvitarNula}
        accionRevocar={accionSimpleNula}
        accionQuitar={accionSimpleNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Invitar a alguien" })[0] as HTMLElement,
    );
    expect(screen.getByLabelText("Alcance")).toBeTruthy();
    await usuario.selectOptions(screen.getByLabelText("Perfil"), "auxiliar");
    expect(screen.queryByLabelText("Alcance")).toBeNull();
    expect(screen.getByLabelText("Edificio")).toBeTruthy();
  });

  it("invitar con éxito manda nombre, email, rol y alcance a la acción", async () => {
    const usuario = userEvent.setup();
    const accionInvitar = vi
      .fn()
      .mockResolvedValue({ erroresPorCampo: {}, erroresDesconocidos: [], ok: true });
    render(
      <PantallaPersonal
        personas={[]}
        edificios={EDIFICIOS}
        accionInvitar={accionInvitar}
        accionRevocar={accionSimpleNula}
        accionQuitar={accionSimpleNula}
      />,
    );
    await usuario.click(
      screen.getAllByRole("button", { name: "Invitar a alguien" })[0] as HTMLElement,
    );
    await usuario.type(screen.getByLabelText("Nombre"), "Nueva Persona");
    await usuario.type(screen.getByLabelText("Email"), "nueva@test.com");
    await usuario.click(screen.getByRole("button", { name: "Invitar" }));
    expect(accionInvitar).toHaveBeenCalledTimes(1);
    const form = accionInvitar.mock.calls[0]?.[1] as FormData;
    expect(form.get("nombre")).toBe("Nueva Persona");
    expect(form.get("email")).toBe("nueva@test.com");
    expect(form.get("rol")).toBe("administrador");
    expect(form.get("alcance")).toBe("principal");
    // RF-F-2 (mismo patrón que unidades): guardar cierra el panel y
    // devuelve el foco al botón que lo abrió.
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.activeElement).toBe(
      screen.getAllByRole("button", { name: "Invitar a alguien" })[0],
    );
  });

  it("vacío ofrece invitar a la primera persona", () => {
    render(
      <PantallaPersonal
        personas={[]}
        edificios={EDIFICIOS}
        accionInvitar={accionInvitarNula}
        accionRevocar={accionSimpleNula}
        accionQuitar={accionSimpleNula}
      />,
    );
    expect(screen.getByText("Todavía no invitaste a nadie")).toBeTruthy();
  });

  it("un vecino en los datos de la API nunca aparece en Personal ni en el conteo (corrección L-026)", () => {
    // Personal vive de la misma fuente que el padrón de 7.4 (`GET
    // /api/personal`), que puede traer filas con `rol: "vecino"` (ver
    // `_PERSONAL_DE_PRUEBA` de `e2e/api-falsa.ts`, "Deco Vecino"). Esta
    // pantalla sólo muestra personal: super admin, administrador, contador,
    // auxiliar y consejo; los vecinos viven en el padrón de unidades.
    const conVecino: Persona[] = [
      ...PERSONAS,
      {
        persona_id: "p3",
        nombre: "Deco Vecino",
        email: "deco@test.com",
        vinculado: false,
        asignaciones: [
          {
            asignacion_id: "a3",
            rol: "vecino",
            complejo_id: null,
            unidad_id: "u1",
            vinculo: "propietario",
          },
        ],
        invitacion: { invitacion_id: "i3", estado: "pendiente" },
      },
    ];
    render(
      <PantallaPersonal
        personas={conVecino}
        edificios={EDIFICIOS}
        accionInvitar={accionInvitarNula}
        accionRevocar={accionSimpleNula}
        accionQuitar={accionSimpleNula}
      />,
    );
    expect(screen.queryByText("Deco Vecino")).toBeNull();
    expect(screen.queryByText(/^vecino$/i)).toBeNull();
    // Las dos personas de personal siguen ahí: no se vacía la tabla entera.
    expect(screen.getByText("Ana Pérez")).toBeTruthy();
    expect(screen.getByText("Beto Gómez")).toBeTruthy();
  });

  it("sin violaciones de axe, con datos y con el panel de invitar abierto", async () => {
    const usuario = userEvent.setup();
    const { container } = render(
      <PantallaPersonal
        personas={PERSONAS}
        edificios={EDIFICIOS}
        accionInvitar={accionInvitarNula}
        accionRevocar={accionSimpleNula}
        accionQuitar={accionSimpleNula}
      />,
    );
    await sinViolaciones(container);
    await usuario.click(
      screen.getAllByRole("button", { name: "Invitar a alguien" })[0] as HTMLElement,
    );
    await sinViolaciones(container);
  });
});
