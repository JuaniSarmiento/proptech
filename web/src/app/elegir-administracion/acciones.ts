"use server";

import { cookies } from "next/headers";
import { esIdValido, pedirApi } from "../../lib/api/cliente";

export async function elegirAdministracionAction(id: string): Promise<boolean> {
  if (!esIdValido(id)) return false;
  const resultado = await pedirApi<{ administraciones: { id: string; nombre: string }[] }>(
    "/api/sesion",
  );
  if (resultado.estado !== "ok" || !resultado.datos.administraciones.some((a) => a.id === id)) {
    return false;
  }
  (await cookies()).set("proptech_administracion", id, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  await pedirApi("/api/sesion/ingreso", { metodo: "POST" });
  return true;
}
