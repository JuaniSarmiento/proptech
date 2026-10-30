import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { PantallaSinAcceso } from "./Pantalla";

export const dynamic = "force-dynamic";
export default async function SinAcceso() {
  const sesion = await auth();
  if (!sesion.userId) redirect("/ingresar");
  return <PantallaSinAcceso />;
}
