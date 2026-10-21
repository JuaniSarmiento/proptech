import { NextRequest } from "next/server";
import { afterEach, expect, it, vi } from "vitest";
import { crearToken, PUBLICA, PUBLICABLE, SECRETA_FALSA } from "../e2e/sesion-local";

vi.unmock("@clerk/nextjs/server");
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("E16: el middleware real valida el token local con clave ficticia y sin red ni handshake", async () => {
  vi.stubEnv("CLERK_SECRET_KEY", SECRETA_FALSA);
  vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", PUBLICABLE);
  vi.stubEnv("CLERK_JWT_KEY", PUBLICA);
  vi.stubEnv("CLERK_PARTES_AUTORIZADAS", "http://127.0.0.1:3100");
  const red = vi.fn(() => {
    throw new Error("red prohibida");
  });
  vi.stubGlobal("fetch", red);
  const { default: proxy } = await import("./proxy");
  const token = crearToken();
  const ahora = Math.floor(Date.now() / 1000);
  const respuesta = await proxy(
    new NextRequest("http://127.0.0.1:3100/edificios", {
      headers: { cookie: `__session=${token}; __client_uat=${ahora}`, accept: "text/html" },
    }),
    {} as Parameters<typeof proxy>[1],
  );
  expect(respuesta?.status).toBe(200);
  expect(respuesta?.headers.get("location")).toBeNull();
  expect(respuesta?.headers.get("x-middleware-request-x-clerk-auth-status")).toBe("signed-in");
  expect(red).not.toHaveBeenCalled();
});

it.each(["ausente", "vencido", "otra_firma"])(
  "Clerk caído, sesión %s: no hay ingreso ni renovación local",
  async (caso) => {
    vi.stubEnv("CLERK_SECRET_KEY", SECRETA_FALSA);
    vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", PUBLICABLE);
    vi.stubEnv("CLERK_JWT_KEY", PUBLICA);
    vi.stubEnv("CLERK_PARTES_AUTORIZADAS", "http://127.0.0.1:3100");
    const red = vi.fn(() => {
      throw new Error("Clerk no responde");
    });
    vi.stubGlobal("fetch", red);
    const { default: proxy } = await import("./proxy");
    const ahora = Math.floor(Date.now() / 1000);
    const token = caso === "ausente" ? "" : crearToken({ exp: ahora - 5 });
    const alterado = caso === "otra_firma" ? `${token.slice(0, -12)}AAAAAAAAAAAA` : token;
    const respuesta = await proxy(
      new NextRequest("http://127.0.0.1:3100/edificios", {
        headers: {
          cookie: `__session=${alterado}; __client_uat=${ahora}`,
          accept: "application/json",
        },
      }),
      {} as Parameters<typeof proxy>[1],
    );
    expect(respuesta?.headers.get("x-clerk-auth-status")).toBe("signed-out");
    expect(red).not.toHaveBeenCalled();
  },
);
