import { auth } from "@clerk/nextjs/server";
import type { ReactElement } from "react";
import { afterEach, expect, it, vi } from "vitest";
import Invitacion from "./page";

afterEach(() => {
  vi.mocked(auth).mockClear();
});

const SOBRE = "sobre-1";

function sinSesion() {
  vi.mocked(auth).mockResolvedValueOnce({ userId: null } as unknown as Awaited<
    ReturnType<typeof auth>
  >);
}

async function enlacesDeInvitacion(ticket?: string) {
  sinSesion();
  const elemento = (await Invitacion({
    params: Promise.resolve({ sobre: SOBRE }),
    searchParams: Promise.resolve(ticket === undefined ? {} : { __clerk_ticket: ticket }),
  })) as ReactElement<{ ingreso: string; registro: string }>;
  return { ingreso: elemento.props.ingreso, registro: elemento.props.registro };
}

it("8.2 RED: sin ticket, ingreso y registro no llevan __clerk_ticket", async () => {
  const { ingreso, registro } = await enlacesDeInvitacion();
  expect(ingreso).toBe(`/ingresar?regreso=%2Finvitacion%2F${SOBRE}`);
  expect(registro).toBe(`/registrarse?regreso=%2Finvitacion%2F${SOBRE}`);
});

it("8.2: con el __clerk_ticket de Clerk en la URL, lo conserva en los dos links sin mezclarlo con el regreso", async () => {
  const { ingreso, registro } = await enlacesDeInvitacion("abc.123-xyz_9");
  for (const href of [ingreso, registro]) {
    const url = new URL(href, "https://x.invalid");
    expect(url.searchParams.get("__clerk_ticket")).toBe("abc.123-xyz_9");
    expect(url.searchParams.get("regreso")).toBe(`/invitacion/${SOBRE}`);
  }
});

it.each([
  ["caracteres fuera de lo seguro para URL", "con espacio y ñ"],
  ["demasiado largo", "a".repeat(3000)],
])("8.2: descarta un ticket inválido (%s)", async (_nombre, ticketInvalido) => {
  const { ingreso, registro } = await enlacesDeInvitacion(ticketInvalido);
  expect(ingreso).not.toContain("__clerk_ticket");
  expect(registro).not.toContain("__clerk_ticket");
});

// --- B-3 (2d, 7.8, D10): el claim de email llega a PantallaInvitacion ---

it("sin sesión, claimEmail es null", async () => {
  sinSesion();
  const elemento = (await Invitacion({
    params: Promise.resolve({ sobre: SOBRE }),
    searchParams: Promise.resolve({}),
  })) as ReactElement<{ claimEmail: string | null }>;
  expect(elemento.props.claimEmail).toBeNull();
});

it("con sesión y el claim de email, lo pasa a la pantalla", async () => {
  vi.mocked(auth).mockResolvedValueOnce({
    userId: "user_prueba",
    sessionClaims: { email: "alguien@example.invalid" },
    getToken: async () => "token-local",
  } as unknown as Awaited<ReturnType<typeof auth>>);
  const elemento = (await Invitacion({
    params: Promise.resolve({ sobre: SOBRE }),
    searchParams: Promise.resolve({}),
  })) as ReactElement<{ claimEmail: string | null }>;
  expect(elemento.props.claimEmail).toBe("alguien@example.invalid");
});

it("un email en la query de la URL nunca llega como claimEmail (El email no sale de la URL)", async () => {
  sinSesion();
  const elemento = (await Invitacion({
    params: Promise.resolve({ sobre: SOBRE }),
    // @ts-expect-error -- un parámetro que la página no declara, a propósito.
    searchParams: Promise.resolve({ email: "intruso@example.invalid" }),
  })) as ReactElement<{ claimEmail: string | null }>;
  expect(elemento.props.claimEmail).toBeNull();
});

it.each([undefined, "abc.123-xyz_9", "con espacio"])(
  "E10: la URL de cierre vuelve a la misma invitación con ticket seguro (%s)",
  async (ticket) => {
    vi.mocked(auth).mockResolvedValueOnce({
      userId: "user_prueba",
      sessionClaims: {},
      getToken: async () => "token-local",
    } as unknown as Awaited<ReturnType<typeof auth>>);
    const pantalla = (await Invitacion({
      params: Promise.resolve({ sobre: "sobre con /" }),
      searchParams: Promise.resolve({ __clerk_ticket: ticket }),
    })) as ReactElement<{ volverAInvitacion: string }>;
    const esperado =
      "/invitacion/sobre%20con%20%2F" +
      (ticket === "abc.123-xyz_9" ? "?__clerk_ticket=abc.123-xyz_9" : "");
    expect(pantalla.props.volverAInvitacion).toBe(esperado);
  },
);
