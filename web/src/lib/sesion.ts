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
    administracionId: (await cookies()).get("proptech_administracion")?.value,
    regreso: regresoSeguro((await headers()).get("x-proptech-ruta")),
  };
}

export function regresoSeguro(valor: string | null | undefined): string {
  // biome-ignore lint/suspicious/noControlCharactersInRegex: rechazar controles evita URLs normalizadas a otro origen.
  if (!valor?.startsWith("/") || valor.startsWith("//") || /[\\\u0000-\u0020]/.test(valor)) {
    return "/edificios";
  }
  const url = new URL(valor, "https://proptech.invalid");
  if (url.origin !== "https://proptech.invalid" || url.pathname.startsWith("//")) {
    return "/edificios";
  }
  return `${url.pathname}${url.search}${url.hash}`;
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
