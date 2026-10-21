import { esES } from "@clerk/localizations";
import { ClerkProvider } from "@clerk/nextjs";
import { cookies, headers } from "next/headers";
import type { ReactNode } from "react";
import { type DatosDeSesion, SesionDePantalla } from "../componentes/SesionDePantalla";
import { pedirApi } from "../lib/api/cliente";
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/600.css";
import "@fontsource/source-sans-3/700.css";
import "./tokens.css";

export const metadata = {
  title: "PropTech",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const ruta = (await headers()).get("x-proptech-ruta") ?? "/";
  const invitacion = ruta.startsWith("/invitacion/");
  const protegida = ruta.startsWith("/edificios") || ruta.startsWith("/personal");
  const resultado = protegida ? await pedirApi<DatosDeSesion>("/api/sesion") : null;
  const valor =
    resultado?.estado === "ok"
      ? {
          datos: resultado.datos,
          administracionId: (await cookies()).get("proptech_administracion")?.value,
        }
      : null;
  const contenido = <SesionDePantalla value={valor}>{children}</SesionDePantalla>;
  return (
    <html lang="es">
      <body>
        {invitacion ? (
          contenido
        ) : (
          <ClerkProvider dynamic localization={esES}>
            {contenido}
          </ClerkProvider>
        )}
      </body>
    </html>
  );
}
