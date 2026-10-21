import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

export default clerkMiddleware(
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
  },
);

export const config = {
  matcher: ["/((?!_next|[^?]*\\.(?:css|js|png|jpg|svg|ico|woff2?)).*)"],
};
