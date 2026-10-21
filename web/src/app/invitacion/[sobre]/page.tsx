import { sesionActual } from "../../../lib/sesion";
import { aceptarInvitacionAction } from "../acciones";
import { PantallaInvitacion } from "../Pantalla";
export const dynamic = "force-dynamic";
export default async function Invitacion({ params }: { params: Promise<{ sobre: string }> }) {
  const { sobre } = await params;
  const sesion = await sesionActual();
  const regreso = `/invitacion/${encodeURIComponent(sobre)}`;
  return (
    <PantallaInvitacion
      accion={sesion ? aceptarInvitacionAction.bind(null, sobre) : null}
      ingreso={`/ingresar?${new URLSearchParams({ regreso, ...(sesion ? { cerrar: "1" } : {}) })}`}
      registro={`/registrarse?${new URLSearchParams({ regreso })}`}
    />
  );
}
