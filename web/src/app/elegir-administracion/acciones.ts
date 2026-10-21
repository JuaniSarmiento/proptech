"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { esIdValido, pedirApi } from "../../lib/api/cliente";
import { regresoSeguro } from "../../lib/sesion";

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
  const ingreso = await pedirApi("/api/sesion/ingreso", { metodo: "POST" });
  return ingreso.estado === "ok";
}

export async function entrarAction(
  regreso: string,
  _previo: string | null,
  form: FormData,
): Promise<string | null> {
  const id = String(form.get("administracion_id") ?? "");
  if (!(await elegirAdministracionAction(id)))
    return "No pudimos ingresar. Volvé a elegir tu administración.";
  redirect(regresoSeguro(regreso));
}
