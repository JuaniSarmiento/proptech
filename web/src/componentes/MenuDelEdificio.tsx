"use client";

/**
 * Menú lateral del edificio (D10, enmienda del 20/10/2026): las secciones
 * agrupadas ("El edificio", "Configuración"), cada una con su ícono de
 * línea y su texto al lado (nunca sólo el ícono). El nombre del edificio y
 * "Mis edificios" pasaron a la barra superior (`Armazon`). Por debajo de
 * 768 px se pliega a un botón "Secciones" operable con teclado y `Esc`
 * (D8, `pantallas-del-edificio` › Menú plegado).
 *
 * Todo vive dentro de un único `<nav>` con nombre: el barrido de 5.1 ya
 * encontró una vez contenido del menú fuera de todo landmark (violación
 * `region` de axe en el navegador real).
 */

import {
  CalendarClock,
  House,
  Layers,
  type LucideIcon,
  Tags,
  Building2 as Unidades,
  Users,
} from "lucide-react";
import { useId, useRef, useState } from "react";

import { useCerrarConEscape } from "../lib/teclado/useCerrarConEscape";

export type IconoDeSeccion =
  | "resumen"
  | "unidades"
  | "grupos"
  | "categorias"
  | "configuracion"
  | "personal";

export type SeccionDelEdificio = {
  clave: string;
  etiqueta: string;
  href: string;
  grupo: string;
  icono: IconoDeSeccion;
};

const _ICONOS: Record<IconoDeSeccion, LucideIcon> = {
  resumen: House,
  unidades: Unidades,
  grupos: Layers,
  categorias: Tags,
  configuracion: CalendarClock,
  personal: Users,
};

type Props = {
  seccionActual: string;
  secciones: SeccionDelEdificio[];
  /** El menú se reusa fuera de un edificio (7.3, grupo "Mi administración");
   * el nombre accesible del `<nav>` cambia según el contexto, nunca el
   * layout ni el resto del comportamiento. */
  nombreAccesible?: string;
};

/** Las secciones agrupadas en el orden en que aparece cada grupo. */
function agrupar(secciones: SeccionDelEdificio[]): Array<[string, SeccionDelEdificio[]]> {
  const grupos = new Map<string, SeccionDelEdificio[]>();
  for (const seccion of secciones) {
    grupos.set(seccion.grupo, [...(grupos.get(seccion.grupo) ?? []), seccion]);
  }
  return [...grupos.entries()];
}

export function MenuDelEdificio({
  seccionActual,
  secciones,
  nombreAccesible = "Secciones del edificio",
}: Props) {
  const [abierto, setAbierto] = useState(false);
  const idDelMenu = useId();
  const botonRef = useRef<HTMLButtonElement>(null);

  useCerrarConEscape(abierto, () => {
    setAbierto(false);
    botonRef.current?.focus();
  });

  return (
    <nav className="menu-del-edificio" aria-label={nombreAccesible}>
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
      <div id={idDelMenu} className="menu-del-edificio__lista" data-abierto={abierto}>
        {agrupar(secciones).map(([grupo, delGrupo], indice) => (
          <div key={grupo} className="menu-del-edificio__grupo">
            <p className="menu-del-edificio__titulo-grupo" id={`${idDelMenu}-grupo-${indice}`}>
              {grupo}
            </p>
            <ul aria-labelledby={`${idDelMenu}-grupo-${indice}`}>
              {delGrupo.map((seccion) => {
                const esActual = seccion.clave === seccionActual;
                const Icono = _ICONOS[seccion.icono];
                return (
                  <li key={seccion.clave}>
                    <a href={seccion.href} aria-current={esActual ? "page" : undefined}>
                      <Icono size={18} strokeWidth={1.75} aria-hidden="true" />
                      <span>{seccion.etiqueta}</span>
                      {/* La sección actual se marca también con forma, no
                       * sólo con el fondo (The Never Color Alone Rule). */}
                      {esActual ? (
                        <span className="menu-del-edificio__marca" aria-hidden="true">
                          ›
                        </span>
                      ) : null}
                    </a>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}
