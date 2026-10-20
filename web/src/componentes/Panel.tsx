/**
 * Panel de contenido (enmienda del shape del 3b, 20/10/2026): una sección
 * con borde suave y esquinas redondeadas, plana (sin sombra: The
 * Flat-By-Default Rule), con su título y una línea gris que dice para qué
 * sirve. Cada pantalla arma un panel principal y uno o más de apoyo; nunca
 * una grilla de paneles iguales.
 */

import { type ReactNode, useId } from "react";

type Props = {
  titulo: string;
  /** Una línea que dice para qué sirve el panel (más didáctico). */
  descripcion?: ReactNode;
  /** Un enlace o botón secundario a la derecha del título. */
  accion?: ReactNode;
  /** `apoyo`: el panel lateral de la pantalla, con fondo hundido. */
  variante?: "principal" | "apoyo";
  className?: string;
  children: ReactNode;
};

export function Panel({
  titulo,
  descripcion,
  accion,
  variante = "principal",
  className,
  children,
}: Props) {
  const idTitulo = useId();
  return (
    <section
      className={["panel", `panel--${variante}`, className].filter(Boolean).join(" ")}
      aria-labelledby={idTitulo}
    >
      <div className="panel__encabezado">
        <div className="panel__textos">
          <h2 id={idTitulo}>{titulo}</h2>
          {descripcion ? <p className="panel__descripcion">{descripcion}</p> : null}
        </div>
        {accion ? <div className="panel__accion">{accion}</div> : null}
      </div>
      {children}
    </section>
  );
}
