/** @vitest-environment jsdom */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PantallaIngreso } from "./Pantalla";

const recibido = vi.hoisted(() => vi.fn());
vi.mock("@clerk/nextjs", () => ({
  ClerkLoaded: ({ children }: { children: React.ReactNode }) => children,
  ClerkLoading: () => null,
  SignIn: (props: unknown) => {
    recibido(props);
    return <p>Ingreso de Clerk</p>;
  },
  SignUp: () => <p>Registro de Clerk</p>,
  useClerk: () => ({ signOut: vi.fn() }),
}));
afterEach(cleanup);
it("Clerk usa tokens y oculta el registro suelto, con aviso y ayuda", () => {
  render(<PantallaIngreso regreso="/edificios" />);
  expect(screen.getByRole("heading", { name: "Ingresar" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Aviso de privacidad" }).getAttribute("href")).toBe(
    "/privacidad",
  );
  expect(recibido.mock.lastCall?.[0]).toMatchObject({
    withSignUp: false,
    appearance: {
      variables: { colorPrimary: "var(--color-terracota)", fontFamily: "var(--tipo-fuente-base)" },
    },
  });
  expect(screen.queryByRole("link", { name: /registr/i })).toBeNull();
  expect(screen.getByRole("button", { name: "Ayuda" })).toBeTruthy();
});
