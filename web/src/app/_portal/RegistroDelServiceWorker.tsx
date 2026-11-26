"use client";

/**
 * Registra el service worker mínimo (`/sw.js`, H-040) con alcance en toda la app. No renderiza nada. Si
 * el navegador no lo soporta o el registro falla, el portal sigue funcionando igual: el worker sólo
 * hace instalable la app y no guarda nada (D-170.6).
 */

import { useEffect } from "react";

export function RegistroDelServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* sin worker no hay instalación, pero tampoco error para la persona */
    });
  }, []);
  return null;
}
