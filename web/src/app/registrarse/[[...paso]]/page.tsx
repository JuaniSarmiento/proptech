import { redirect } from "next/navigation";
import { regresoSeguro } from "../../../lib/sesion";
import { PantallaIngreso } from "../../ingresar/Pantalla";
export default async function Registrarse({
  searchParams,
}: {
  searchParams: Promise<{ regreso?: string }>;
}) {
  const regreso = regresoSeguro((await searchParams).regreso);
  if (!regreso.startsWith("/invitacion/")) redirect("/ingresar");
  return <PantallaIngreso regreso={regreso} registro />;
}
