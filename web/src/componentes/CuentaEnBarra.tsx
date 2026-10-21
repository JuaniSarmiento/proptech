"use client";
import { UserRound } from "lucide-react";
import { useSesionDePantalla } from "./SesionDePantalla";
export function CuentaEnBarra() {
  const sesion = useSesionDePantalla();
  if (!sesion) return null;
  const admin = sesion.datos.administraciones.find((a) => a.id === sesion.administracionId);
  return (
    <details className="cuenta-en-barra">
      <summary>
        <UserRound size={18} aria-hidden="true" />
        <span>
          {sesion.datos.persona.nombre}
          <small>{admin?.nombre ?? "Elegí una administración"}</small>
        </span>
      </summary>
      <nav aria-label="Tu cuenta" className="cuenta-en-barra__opciones">
        {sesion.datos.administraciones.length > 1 ? (
          <a href="/elegir-administracion">Cambiar de administración</a>
        ) : null}
        <a href="/ingresar?cerrar=1">Cerrar sesión</a>
      </nav>
    </details>
  );
}
