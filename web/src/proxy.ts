import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const apiDeClerk = Buffer.from(
  (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "").slice(8),
  "base64",
)
  .toString()
  .replace(/\$$/, "");

const middlewareDeClerk = clerkMiddleware(
  (_auth, pedido) => {
    const cabeceras = new Headers(pedido.headers);
    cabeceras.set("x-proptech-ruta", `${pedido.nextUrl.pathname}${pedido.nextUrl.search}`);
    return NextResponse.next({ request: { headers: cabeceras } });
  },
  {
    jwtKey: process.env.CLERK_JWT_KEY,
    authorizedParties: process.env.CLERK_PARTES_AUTORIZADAS?.split(","),
    signInUrl: "/ingresar",
    signUpUrl: "/registrarse",
    contentSecurityPolicy: {
      strict: true,
      directives: {
        "default-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "frame-ancestors": ["'none'"],
        "form-action": ["'self'"],
        "script-src": [`https://${apiDeClerk}`, "https://challenges.cloudflare.com"],
      },
    },
  },
);

export default async function proxy(...argumentos: Parameters<typeof middlewareDeClerk>) {
  const respuesta = await middlewareDeClerk(...argumentos);
  if (!respuesta) return respuesta;
  const pedido = argumentos[0];
  // El ticket de invitación de Clerk (`__clerk_ticket`) viaja en la URL hasta
  // /registrarse e /ingresar (8.2): mismas cabeceras que /invitacion/ cuando
  // lo llevan, para no dejarlo en el referrer ni en una caché intermedia.
  const { pathname } = pedido.nextUrl;
  const conTicket = pedido.nextUrl.searchParams.has("__clerk_ticket");
  if (
    pathname.startsWith("/invitacion/") ||
    (conTicket && (pathname === "/ingresar" || pathname === "/registrarse"))
  ) {
    respuesta.headers.set("Referrer-Policy", "no-referrer");
    respuesta.headers.set("Cache-Control", "no-store");
  }
  // Clerk 7.9.19 conserva unsafe-inline incluso con strict. Quitarlo tanto de
  // la respuesta como de la CSP que Next lee para aplicar el nonce al render.
  for (const nombre of [
    "content-security-policy",
    "x-middleware-request-content-security-policy",
  ]) {
    const csp = respuesta.headers.get(nombre);
    if (!csp) continue;
    const estricta = csp
      .split("; ")
      .map((directiva) => {
        if (!directiva.startsWith("script-src ")) return directiva;
        return directiva
          .split(" ")
          .filter((fuente) => fuente !== "'unsafe-inline'" && fuente !== "'unsafe-eval'")
          .join(" ");
      })
      .join("; ");
    respuesta.headers.set(nombre, estricta);
  }
  return respuesta;
}

export const config = {
  matcher: ["/((?!_next|[^?]*\\.(?:css|js|png|jpg|svg|ico|woff2?)).*)"],
};
