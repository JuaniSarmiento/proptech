import { esES } from "@clerk/localizations";
import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata, Viewport } from "next";
import { cookies, headers } from "next/headers";
import type { ReactNode } from "react";
import { type DatosDeSesion, SesionDePantalla } from "../componentes/SesionDePantalla";
import { pedirApi } from "../lib/api/cliente";
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/600.css";
import "@fontsource/source-sans-3/700.css";
import "./tokens.css";

export const metadata: Metadata = {
  title: "PropTech",
  // H-040: la app instalable. El manifest y los íconos son archivos públicos (`web/public/`).
  manifest: "/manifest.webmanifest",
  icons: { apple: "/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  themeColor: "#723222",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const ruta = (await headers()).get("x-proptech-ruta") ?? "/";
  const invitacion = ruta.startsWith("/invitacion/");
  const protegida =
    ruta.startsWith("/edificios") ||
    ruta.startsWith("/personal") ||
    // H-040: las pantallas del portal del vecino llevan la cuenta en la barra.
    ruta.startsWith("/inicio") ||
    ruta.startsWith("/mis-liquidaciones") ||
    ruta.startsWith("/comprobantes");
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
