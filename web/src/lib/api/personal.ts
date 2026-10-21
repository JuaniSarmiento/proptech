/**
 * Personal de la administración (D5, tarea 7.3): listar, invitar, revocar
 * y quitar. Sin fixture generado por `test_contrato_web.py` todavía (ruta
 * nueva de este cambio): los tipos viven acá, no en `tipos.ts`, igual que
 * `DatosDeSesion` en `SesionDePantalla.tsx`.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type AsignacionDePersona = {
  asignacion_id: string;
  rol: string;
  complejo_id: string | null;
  unidad_id: string | null;
  vinculo: string | null;
};

export type InvitacionDePersona = {
  invitacion_id: string;
  estado: string;
};

export type Persona = {
  persona_id: string;
  nombre: string;
  email: string;
  vinculado: boolean;
  asignaciones: AsignacionDePersona[];
  invitacion: InvitacionDePersona | null;
};

export async function listarPersonal(): Promise<ResultadoApi<Persona[]>> {
  return pedirApi<Persona[]>("/api/personal");
}

export type DatosInvitacionDePersonal = {
  nombre: string;
  email: string;
  rol: string;
  alcance: string;
  complejo_id?: string;
};

export type AltaDePersona = {
  persona_id: string;
  asignacion_id: string;
  invitacion_id: string | null;
};

export async function invitarPersonal(
  datos: DatosInvitacionDePersonal,
): Promise<ResultadoApi<AltaDePersona>> {
  return pedirApi<AltaDePersona>("/api/personal/invitaciones", { metodo: "POST", cuerpo: datos });
}

export async function revocarInvitacion(
  invitacionId: string,
): Promise<ResultadoApi<{ revocada: boolean }>> {
  if (!esIdValido(invitacionId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ revocada: boolean }>(
    `/api/invitaciones/${encodeURIComponent(invitacionId)}/revocar`,
    { metodo: "POST" },
  );
}

export async function quitarAsignacion(
  asignacionId: string,
): Promise<ResultadoApi<{ quitada: boolean }>> {
  if (!esIdValido(asignacionId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ quitada: boolean }>(`/api/asignaciones/${encodeURIComponent(asignacionId)}`, {
    metodo: "DELETE",
  });
}

export type DatosDeVecino = {
  nombre: string;
  email: string;
  vinculo: string;
};

export async function altaDeVecino(
  unidadId: string,
  datos: DatosDeVecino,
): Promise<ResultadoApi<AltaDePersona>> {
  if (!esIdValido(unidadId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<AltaDePersona>(`/api/unidades/${encodeURIComponent(unidadId)}/vecinos`, {
    metodo: "POST",
    cuerpo: datos,
  });
}
