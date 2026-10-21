"use server";
import { redirect } from "next/navigation";
import { pedirApi } from "../../lib/api/cliente";
export async function aceptarInvitacionAction(
  sobre: string,
  _previo: { error: boolean } | null,
  _form: FormData,
): Promise<{ error: boolean }> {
  const resultado = await pedirApi<{ aceptada: boolean }>("/api/invitaciones/aceptar", {
    metodo: "POST",
    cuerpo: { token: sobre },
  });
  if (resultado.estado !== "ok" || resultado.datos.aceptada !== true) return { error: true };
  redirect("/elegir-administracion?aceptada=1");
}
