import { redirect } from "next/navigation";
import { regresoSeguro, ticketSeguro } from "../../../lib/sesion";
import { PantallaIngreso } from "../../ingresar/Pantalla";
export default async function Registrarse({
  searchParams,
}: {
  searchParams: Promise<{ regreso?: string; __clerk_ticket?: string }>;
}) {
  const q = await searchParams;
  const regreso = regresoSeguro(q.regreso);
  if (!regreso.startsWith("/invitacion/")) redirect("/ingresar");
  return <PantallaIngreso regreso={regreso} registro ticket={ticketSeguro(q.__clerk_ticket)} />;
}
