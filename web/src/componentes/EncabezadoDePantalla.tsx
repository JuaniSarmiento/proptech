/**
 * Encabezado de pantalla (D8, tarea 3.5): título, "?" de ayuda y acción
 * principal, siempre en ese orden. El contenido de la ayuda y de la acción
 * los trae cada pantalla; este componente sólo pone el layout en común.
 */

import type { ReactNode } from "react";

type Props = {
  titulo: string;
  ayuda: ReactNode;
  accionPrincipal?: ReactNode;
};

export function EncabezadoDePantalla({ titulo, ayuda, accionPrincipal }: Props) {
  return (
    <header className="encabezado-de-pantalla">
      <div className="encabezado-de-pantalla__titulo">
        <h1>{titulo}</h1>
        {ayuda}
      </div>
      {accionPrincipal ? (
        <div className="encabezado-de-pantalla__accion">{accionPrincipal}</div>
      ) : null}
    </header>
  );
}
