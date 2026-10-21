import { test as base, expect } from "@playwright/test";
import { ADMINISTRACION, cookiesDeContextoDePrueba } from "./sesion-local";

export type { Page } from "@playwright/test";
export { expect };
export const test = base.extend({
  context: async ({ context, baseURL }, use) => {
    const url = baseURL ?? "http://127.0.0.1:3100";
    // R2B-4 (rompedor 2b): `cookiesDeContextoDePrueba` lee el reloj UNA
    // sola vez para el `iat` del token y el `__client_uat` (ver su
    // docstring en sesion-local.ts).
    const { session, clientUat } = cookiesDeContextoDePrueba();
    await context.addCookies([
      { name: "__session", value: session, url },
      { name: "__client_uat", value: clientUat, url },
      {
        name: "proptech_administracion",
        value: ADMINISTRACION,
        httpOnly: true,
        sameSite: "Lax",
        url,
      },
    ]);
    // El navegador no llama a ninguna instancia real; Next verifica la firma local.
    await context.route(/https:\/\/[^/]*(?:clerk|cloudflare)[^/]*\//, (ruta) => ruta.abort());
    await use(context);
  },
});
