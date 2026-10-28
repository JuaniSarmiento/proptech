/**
 * @vitest-environment jsdom
 *
 * B-3 (2d, 7.8, D10): la invitación dice con qué cuenta se está, con el
 * claim de email del token de sesión; sin ese claim, las dos formas (antes
 * de aceptar y cuando falla) quedan genéricas.
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PantallaInvitacion } from "./Pantalla";

afterEach(cleanup);

const INGRESO = "/ingresar?regreso=%2Finvitacion%2Fsobre-1&cerrar=1";
const REGISTRO = "/registrarse?regreso=%2Finvitacion%2Fsobre-1";

function accionQueFalla() {
  return Promise.resolve({ error: true });
}

describe("PantallaInvitacion", () => {
  describe("sin sesión (como hoy)", () => {
    it("ofrece Aceptar e ingresar (enlace) y crear la cuenta, sin mensaje de cuenta", () => {
      render(<PantallaInvitacion accion={null} ingreso={INGRESO} registro={REGISTRO} />);
      const enlace = screen.getByRole("link", { name: "Aceptar e ingresar" });
      expect(enlace.getAttribute("href")).toBe(INGRESO);
      expect(screen.getByRole("link", { name: /creá tu cuenta/ }).getAttribute("href")).toBe(
        REGISTRO,
      );
      expect(screen.queryByText(/Estás ingresado/)).toBeNull();
      expect(screen.queryByRole("link", { name: "Usar otra cuenta" })).toBeNull();
    });
  });

  describe("con sesión y el claim de email (Abrir la invitación con la sesión de otra cuenta)", () => {
    it('dice con qué cuenta está y ofrece "Aceptar e ingresar" y "Usar otra cuenta"', () => {
      render(
        <PantallaInvitacion
          accion={vi.fn()}
          ingreso={INGRESO}
          registro={REGISTRO}
          claimEmail="beto@example.invalid"
        />,
      );
      expect(screen.getByText("Estás ingresado como beto@example.invalid.")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Aceptar e ingresar" })).toBeTruthy();
      const usarOtra = screen.getByRole("link", { name: "Usar otra cuenta" });
      expect(usarOtra.getAttribute("href")).toBe(INGRESO);
    });

    it("si la aceptación falla, el mensaje nombra la cuenta y repite Usar otra cuenta (Aceptar con la cuenta equivocada)", async () => {
      const usuario = userEvent.setup();
      render(
        <PantallaInvitacion
          accion={accionQueFalla}
          ingreso={INGRESO}
          registro={REGISTRO}
          claimEmail="beto@example.invalid"
        />,
      );
      await usuario.click(screen.getByRole("button", { name: "Aceptar e ingresar" }));
      expect(
        await screen.findByText(/Este enlace no sirve con la cuenta beto@example\.invalid\./),
      ).toBeTruthy();
      expect(screen.getByRole("link", { name: "Usar otra cuenta" })).toBeTruthy();
    });
  });

  describe("con sesión sin el claim de email (Token sin email)", () => {
    it("dice que hay una sesión abierta, sin nombrar ningún email (ni vacío ni undefined)", () => {
      render(
        <PantallaInvitacion
          accion={vi.fn()}
          ingreso={INGRESO}
          registro={REGISTRO}
          claimEmail={null}
        />,
      );
      const mensaje = screen.getByText("Hay una sesión abierta en este navegador.");
      expect(mensaje.textContent).not.toMatch(/undefined|@/);
    });

    it(
      "si la aceptación falla sin claim, el mensaje no nombra ningún email " +
        "(Aceptación fallida sin claim de email)",
      async () => {
        const usuario = userEvent.setup();
        render(
          <PantallaInvitacion
            accion={accionQueFalla}
            ingreso={INGRESO}
            registro={REGISTRO}
            claimEmail={null}
          />,
        );
        await usuario.click(screen.getByRole("button", { name: "Aceptar e ingresar" }));
        const mensaje = await screen.findByRole("alert");
        expect(mensaje.textContent).toMatch(/con la cuenta con la que ingresaste/);
        expect(mensaje.textContent).not.toMatch(/undefined|@/);
        expect(screen.getByRole("link", { name: "Usar otra cuenta" })).toBeTruthy();
      },
    );
  });
});
