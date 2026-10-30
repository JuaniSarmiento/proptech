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

// pulido-2 (3d): el filtro propio de `proxy.ts` que le saca `'unsafe-inline'` y
// `'unsafe-eval'` a `script-src` (Clerk 7.9.19 deja el primero aun con `strict`).
// El e2e `csp.spec.ts` prueba la política completa contra Next real; esto prueba
// el filtro sin levantar Next, en las dos cabeceras donde se aplica.
it("CSP: script-src sin 'unsafe-inline' ni 'unsafe-eval' y con nonce, en la respuesta y en la cabecera que lee Next", async () => {
  vi.stubEnv("CLERK_SECRET_KEY", SECRETA_FALSA);
  vi.stubEnv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", PUBLICABLE);
  vi.stubEnv("CLERK_JWT_KEY", PUBLICA);
  vi.stubEnv("CLERK_PARTES_AUTORIZADAS", "http://127.0.0.1:3100");
  vi.stubGlobal(
    "fetch",
    vi.fn(() => {
      throw new Error("red prohibida");
    }),
  );
  const { default: proxy } = await import("./proxy");
  const ahora = Math.floor(Date.now() / 1000);
  const respuesta = await proxy(
    new NextRequest("http://127.0.0.1:3100/edificios", {
      headers: { cookie: `__session=${crearToken()}; __client_uat=${ahora}`, accept: "text/html" },
    }),
    {} as Parameters<typeof proxy>[1],
  );

  for (const cabecera of [
    "content-security-policy",
    "x-middleware-request-content-security-policy",
  ]) {
    const politica = respuesta?.headers.get(cabecera);
    expect(politica, `falta ${cabecera}`).toBeTruthy();
    const scriptSrc = (politica ?? "")
      .split("; ")
      .find((directiva) => directiva.startsWith("script-src "));
    expect(scriptSrc, `${cabecera} sin script-src`).toBeDefined();
    expect(scriptSrc).not.toContain("'unsafe-inline'");
    expect(scriptSrc).not.toContain("'unsafe-eval'");
    expect(scriptSrc).toMatch(/'nonce-[^']+'/);
  }
});
