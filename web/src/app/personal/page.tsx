/**
 * Personal de la administración (D5, tarea 7.3): lee el personal y la
 * lista de edificios (para el selector "elegir edificio" del alta y para
 * mostrar el nombre del alcance) en paralelo.
 */

import { ErrorDePantalla } from "../../componentes/ErrorDePantalla";
import { Estados } from "../../componentes/Estados";
import { listaDeEdificios } from "../../lib/api/edificios";
import { listarPersonal } from "../../lib/api/personal";
import { invitarAction, quitarAction, revocarAction } from "./acciones";
import { PantallaPersonal } from "./Pantalla";

export const dynamic = "force-dynamic";

export default async function PaginaPersonal() {
  const [personal, edificios] = await Promise.all([listarPersonal(), listaDeEdificios()]);

  if (personal.estado === "sin_sesion") {
    return <Estados tipo="sinSesion" />;
  }
  if (personal.estado === "sin_permiso") {
    return (
      <Estados
        tipo="sinPermiso"
        queNoPuede="ver el personal de la administración"
        permisoFaltante={personal.permiso}
      />
    );
  }
  if (personal.estado !== "ok") {
    return <ErrorDePantalla mensaje="No pudimos cargar el personal." />;
  }

  return (
    <PantallaPersonal
      personas={personal.datos}
      edificios={edificios.estado === "ok" ? edificios.datos : []}
      accionInvitar={invitarAction}
      accionRevocar={revocarAction}
      accionQuitar={quitarAction}
    />
  );
}
