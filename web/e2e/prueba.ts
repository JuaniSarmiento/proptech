import { test as base, expect } from "@playwright/test";
import { ADMINISTRACION, crearToken } from "./sesion-local";

export type { Page } from "@playwright/test";
export { expect };
export const test = base.extend({
  context: async ({ context, baseURL }, use) => {
    const url = baseURL ?? "http://127.0.0.1:3100";
    await context.addCookies([
      { name: "__session", value: crearToken(), url },
      { name: "__client_uat", value: String(Math.floor(Date.now() / 1000)), url },
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
