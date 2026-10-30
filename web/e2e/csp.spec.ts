import { expect, test } from "./prueba";
import { PUBLICABLE, SECRETA_FALSA } from "./sesion-local";

function politica(valor: string | undefined) {
  expect(valor).toBeTruthy();
  const directivas = valor?.split(";").map((parte) => parte.trim().split(/\s+/)) ?? [];
  expect(new Set(directivas.map(([nombre]) => nombre)).size).toBe(directivas.length);
  return Object.fromEntries(directivas.map(([nombre, ...fuentes]) => [nombre, fuentes.sort()]));
}

test("6.2: CSP completa en Next real, nonce distinto en cada pedido público y autenticado", async ({
  page,
}) => {
  const nonces = new Set<string>();
  for (const ruta of ["/ingresar", "/edificios", "/edificios"]) {
    const respuesta = await page.request.get(ruta);
    expect(respuesta.status()).toBe(200);
    const csp = respuesta.headers()["content-security-policy"];
    expect(csp, "Next debe responder con CSP").toBeDefined();
    const nonce = /'nonce-([^']+)'/.exec(csp ?? "")?.[1];
    expect(nonce).toMatch(/^[A-Za-z0-9+/]{22}==$/);
    if (!nonce) throw new Error("falta nonce");
    nonces.add(nonce);
    expect(politica(csp)).toEqual(
      Object.fromEntries(
        Object.entries({
          "base-uri": ["'self'"],
          "connect-src": [
            "'self'",
            "https://clerk-telemetry.com",
            "https://*.clerk-telemetry.com",
            "https://api.stripe.com",
            "https://maps.googleapis.com",
            "https://img.clerk.com",
            "https://*.protect.clerk.com:*",
            "clerk.proptech-prueba.invalid",
          ],
          "default-src": ["'self'"],
          "form-action": ["'self'"],
          "frame-ancestors": ["'none'"],
          "frame-src": [
            "'self'",
            "https://challenges.cloudflare.com",
            "https://*.js.stripe.com",
            "https://js.stripe.com",
            "https://hooks.stripe.com",
            "https://*.protect.clerk.com",
          ],
          "img-src": ["'self'", "https://img.clerk.com"],
          "object-src": ["'none'"],
          "script-src": [
            "'self'",
            "https://*.js.stripe.com",
            "https://js.stripe.com",
            "https://maps.googleapis.com",
            "https://*.protect.clerk.com",
            "'strict-dynamic'",
            `'nonce-${nonce}'`,
            "https://challenges.cloudflare.com",
            "https://clerk.proptech-prueba.invalid",
          ],
          "style-src": ["'self'", "'unsafe-inline'"],
          "worker-src": ["'self'", "blob:"],
        }).map(([nombre, fuentes]) => [nombre, fuentes.sort()]),
      ),
    );
  }
  expect(nonces.size).toBe(3);
});

test("6.2: scripts de Next y Clerk llevan el nonce de la respuesta autenticada", async ({
  page,
}) => {
  const respuesta = await page.goto("/edificios");
  await expect(page.getByRole("heading", { name: "Mis edificios" })).toBeVisible();
  const csp = (await respuesta?.allHeaders())?.["content-security-policy"];
  const nonce = /'nonce-([^']+)'/.exec(csp ?? "")?.[1];
  expect(nonce).toBeTruthy();
  const scripts = await page.evaluate(() =>
    Array.from(document.scripts, (e) => ({ nonce: e.nonce, src: e.src })),
  );
  expect(scripts.length).toBeGreaterThan(0);
  const html = (await respuesta?.text()) ?? "";
  const scriptsDelServidor = await page.evaluate((contenido) => {
    const documento = new DOMParser().parseFromString(contenido, "text/html");
    return Array.from(documento.scripts, (e) => ({ nonce: e.nonce, src: e.src }));
  }, html);
  expect(scriptsDelServidor.some((e) => e.src.includes("clerk.proptech-prueba.invalid"))).toBe(
    true,
  );
  // strict-dynamic permite hijos externos insertados por scripts ya confiables.
  // Las raíces del HTML original y todo inline del DOM sí requieren este nonce.
  expect(
    [...scriptsDelServidor, ...scripts.filter((e) => !e.src)].filter((e) => e.nonce !== nonce),
  ).toEqual([]);
});

test("6.2: HTML y RSC sin token ni secreta; publicable sólo en el bootstrap de Clerk", async ({
  page,
  context,
}) => {
  const token = (await context.cookies()).find((c) => c.name === "__session")?.value;
  expect(token).toBeTruthy();
  if (!token) throw new Error("falta sesión local");
  const respuesta = await page.goto("/edificios");
  const html = (await respuesta?.text()) ?? "";
  expect(html.includes(token)).toBe(false);
  expect(html.includes(SECRETA_FALSA)).toBe(false);
  expect(html).toContain(`data-clerk-publishable-key="${PUBLICABLE}"`);
  // Únicos lugares previstos: atributo del SDK y su prop de inicialización RSC.
  const resto = html
    .replaceAll(`data-clerk-publishable-key="${PUBLICABLE}"`, "")
    .replaceAll(`\\"data-clerk-publishable-key\\":\\"${PUBLICABLE}\\"`, "")
    .replaceAll(`\\"publishableKey\\":\\"${PUBLICABLE}\\"`, "");
  expect(resto.includes(PUBLICABLE)).toBe(false);
});
