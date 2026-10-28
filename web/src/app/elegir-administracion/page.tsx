import { redirect } from "next/navigation";
import { ErrorDePantalla } from "../../componentes/ErrorDePantalla";
import type { DatosDeSesion } from "../../componentes/SesionDePantalla";
import { pedirApi } from "../../lib/api/cliente";
import { regresoSeguro } from "../../lib/sesion";
import { entrarAction } from "./acciones";
import { PantallaSelector, SesionNoUtilizable } from "./Pantalla";
export const dynamic = "force-dynamic";
export default async function Selector({
  searchParams,
}: {
  searchParams: Promise<{ regreso?: string; aceptada?: string }>;
}) {
  const q = await searchParams;
  const resultado = await pedirApi<DatosDeSesion>("/api/sesion", { alNoAutenticar: "devolver" });
  if (resultado.estado === "sin_sesion") return <SesionNoUtilizable />;
  if (resultado.estado !== "ok")
    return <ErrorDePantalla mensaje="No pudimos cargar tus administraciones." />;
  if (resultado.datos.administraciones.length === 0) redirect("/sin-acceso");
  return (
    <PantallaSelector
      datos={resultado.datos}
      aceptada={q.aceptada === "1"}
      accion={entrarAction.bind(null, regresoSeguro(q.regreso))}
    />
  );
}
