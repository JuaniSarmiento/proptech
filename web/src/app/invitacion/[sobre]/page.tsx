import { sesionActual, ticketSeguro } from "../../../lib/sesion";
import { aceptarInvitacionAction } from "../acciones";
import { PantallaInvitacion } from "../Pantalla";
export const dynamic = "force-dynamic";
export default async function Invitacion({
  params,
  searchParams,
}: {
  params: Promise<{ sobre: string }>;
  searchParams: Promise<{ __clerk_ticket?: string }>;
}) {
  const { sobre } = await params;
  const sesion = await sesionActual();
  const ticket = ticketSeguro((await searchParams).__clerk_ticket);
  const regreso = `/invitacion/${encodeURIComponent(sobre)}`;
  const conTicket = (base: Record<string, string>) =>
    new URLSearchParams({ ...base, ...(ticket ? { __clerk_ticket: ticket } : {}) });
  return (
    <PantallaInvitacion
      accion={sesion ? aceptarInvitacionAction.bind(null, sobre) : null}
      ingreso={`/ingresar?${conTicket({ regreso })}`}
      registro={`/registrarse?${conTicket({ regreso })}`}
      claimEmail={sesion?.email ?? null}
      volverAInvitacion={`${regreso}${ticket ? `?${new URLSearchParams({ __clerk_ticket: ticket })}` : ""}`}
    />
  );
}
