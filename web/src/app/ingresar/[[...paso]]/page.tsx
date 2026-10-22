import { regresoSeguro, ticketSeguro } from "../../../lib/sesion";
import { PantallaIngreso } from "../Pantalla";
export default async function Ingresar({
  searchParams,
}: {
  searchParams: Promise<{ regreso?: string; cerrar?: string; __clerk_ticket?: string }>;
}) {
  const q = await searchParams;
  return (
    <PantallaIngreso
      regreso={regresoSeguro(q.regreso)}
      cerrar={q.cerrar === "1"}
      ticket={ticketSeguro(q.__clerk_ticket)}
    />
  );
}
