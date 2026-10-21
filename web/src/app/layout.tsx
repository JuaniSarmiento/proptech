import { esES } from "@clerk/localizations";
import { ClerkProvider } from "@clerk/nextjs";
import type { ReactNode } from "react";
import "@fontsource/source-sans-3/400.css";
import "@fontsource/source-sans-3/600.css";
import "@fontsource/source-sans-3/700.css";
import "./tokens.css";

export const metadata = {
  title: "PropTech",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <ClerkProvider dynamic localization={esES}>
          {children}
        </ClerkProvider>
      </body>
    </html>
  );
}
