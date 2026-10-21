/**
 * Estado de la invitación en castellano simple (D7: `pendiente | enviada |
 * aceptada | fallida | revocada`, más `vencida` calculada por la API).
 * Ajuste del shape resuelto por el orquestador, 21/10/2026: sin "Reenviar"
 * ni "Reintentar"; "fallida" dice que el worker reintenta solo (E8).
 */
const _ESTADOS: Record<string, string> = {
  pendiente: "Pendiente",
  enviada: "Enviada",
  aceptada: "Aceptada",
  vencida: "Vencida",
  fallida: "No se pudo enviar todavía; se reintenta solo",
  revocada: "Revocada",
};

export function textoDeEstadoDeInvitacion(estado: string): string {
  return _ESTADOS[estado] ?? estado;
}

/** Estados en los que "Revocar" tiene sentido: una invitación todavía
 * abierta o que puede reintentarse. Ya aceptada o ya revocada no se
 * vuelve a revocar (la API responde 404, `InvitacionNoRevocable`). */
export const ESTADOS_REVOCABLES = new Set(["pendiente", "enviada", "vencida", "fallida"]);
