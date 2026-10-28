import "server-only";
import { auth } from "@clerk/nextjs/server";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

/** Único acceso a auth(): el token queda en el servidor, nunca en props. */
export async function sesionActual() {
  const sesion = await auth();
  if (!sesion.userId) return null;
  const token = await sesion.getToken();
  if (!token) return null;
  return {
    token,
    email: claimDeEmail(sesion.sessionClaims),
    administracionId: (await cookies()).get("proptech_administracion")?.value,
    regreso: regresoSeguro((await headers()).get("x-proptech-ruta")),
  };
}

/**
 * B-3 (2d, 7.8, D10): el mismo claim `email` que la API verifica
 * (`acceso/dominio/token.py`) — SUPUESTO sin comprobar si el Clerk de
 * desarrollo lo manda en el token de sesión (se comprueba con Clerk real
 * en la tarea 8.2 e). `null`, nunca una cadena vacía, si no viene.
 */
function claimDeEmail(sessionClaims: unknown): string | null {
  const claims = sessionClaims as { email?: unknown } | null | undefined;
  return typeof claims?.email === "string" && claims.email.length > 0 ? claims.email : null;
}

export function regresoSeguro(valor: string | null | undefined): string {
  if (
    !valor?.startsWith("/") ||
    valor.length > 512 ||
    valor.startsWith("//") ||
    // biome-ignore lint/suspicious/noControlCharactersInRegex: rechazar controles evita URLs normalizadas a otro origen.
    /[\\\u0000-\u0020]/.test(valor)
  ) {
    return "/edificios";
  }
  const url = new URL(valor, "https://proptech.invalid");
  if (url.origin !== "https://proptech.invalid" || url.pathname.startsWith("//")) {
    return "/edificios";
  }
  let camino: string;
  try {
    camino = decodeURIComponent(url.pathname).replace(/\/+$/, "");
  } catch {
    return "/edificios";
  }
  const pantallasDeAcceso = ["/ingresar", "/registrarse", "/elegir-administracion", "/sin-acceso"];
  if (pantallasDeAcceso.some((ruta) => camino === ruta || camino.startsWith(`${ruta}/`))) {
    return "/edificios";
  }
  const salida = `${url.pathname}${url.search}${url.hash}`;
  return salida.length > 512 ? "/edificios" : salida;
}

/**
 * Clerk manda el ticket de invitación (`__clerk_ticket`) como query param en
 * la URL de `redirect_url`; `<SignUp>`/`<SignIn>` lo leen directo de esa URL
 * (ver context7, @clerk/nextjs 7.9.19). Lo tratamos como texto opaco: un
 * largo acotado y el alfabeto base64url + punto que usan los JWT de Clerk.
 * Nunca se mezcla con `regreso`, que sigue siendo sólo una ruta.
 */
export function ticketSeguro(valor: string | null | undefined): string | null {
  if (!valor || valor.length > 2048 || !/^[A-Za-z0-9_.-]+$/.test(valor)) return null;
  return valor;
}

export async function irAlIngreso(regreso?: string): Promise<never> {
  const ruta = regreso ?? (await headers()).get("x-proptech-ruta");
  redirect(`/ingresar?${new URLSearchParams({ regreso: regresoSeguro(ruta) })}`);
}
