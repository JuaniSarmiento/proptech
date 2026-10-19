/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

afterEach(cleanup);

describe("ErrorDePantalla", () => {
  it('muestra el mensaje y "Reintentar" vuelve a pedir los datos del servidor (router.refresh)', async () => {
    const { ErrorDePantalla } = await import("./ErrorDePantalla");
    render(<ErrorDePantalla mensaje="No pudimos cargar tus edificios." />);
    expect(screen.getByText("No pudimos cargar tus edificios.")).toBeTruthy();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});
