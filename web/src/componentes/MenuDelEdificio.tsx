"use client";

/**
 * Menú lateral del edificio (D10, tarea 3.5): Resumen, Unidades, Grupos,
 * Categorías e Intereses y vencimiento, encabezado por el nombre del
 * edificio. Por debajo de 768 px se pliega a un botón "Secciones" operable
 * con teclado y `Esc` (D8, `pantallas-del-edificio` › Menú plegado).
 */

import { useEffect, useId, useRef, useState } from "react";

export type SeccionDelEdificio = {
  clave: string;
  etiqueta: string;
  href: string;
};

type Props = {
  nombreEdificio: string;
  seccionActual: string;
  secciones: SeccionDelEdificio[];
};

export function MenuDelEdificio({ nombreEdificio, seccionActual, secciones }: Props) {
  const [abierto, setAbierto] = useState(false);
  const idDelMenu = useId();
  const botonRef = useRef<HTMLButtonElement>(null);

  // Escape cierra el menú plegado desde cualquier foco dentro del widget
  // (el botón o un enlace), no sólo cuando el foco está dentro de la lista:
  // por eso escucha en `document` mientras está abierto, en vez de un
  // `onKeyDown` en un contenedor sin rol interactivo.
  useEffect(() => {
    if (!abierto) {
      return;
    }
    function alTeclado(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        setAbierto(false);
        botonRef.current?.focus();
      }
    }
    document.addEventListener("keydown", alTeclado);
    return () => document.removeEventListener("keydown", alTeclado);
  }, [abierto]);

  return (
    <div className="menu-del-edificio">
      <a href="/edificios" className="menu-del-edificio__volver">
        Mis edificios
      </a>
      <p className="menu-del-edificio__nombre">{nombreEdificio}</p>
      <button
        ref={botonRef}
        type="button"
        className="menu-del-edificio__boton"
        aria-expanded={abierto}
        aria-controls={idDelMenu}
        onClick={() => setAbierto((valor) => !valor)}
      >
        Secciones
      </button>
      <nav id={idDelMenu} aria-label="Secciones del edificio">
        <ul className="menu-del-edificio__lista" data-abierto={abierto}>
          {secciones.map((seccion) => {
            const esActual = seccion.clave === seccionActual;
            return (
              <li key={seccion.clave}>
                <a href={seccion.href} aria-current={esActual ? "page" : undefined}>
                  {esActual ? "▸ " : ""}
                  {seccion.etiqueta}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
