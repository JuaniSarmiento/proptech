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
} from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

export type IconoDeSeccion = "resumen" | "unidades" | "grupos" | "categorias" | "configuracion";

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
};

type Props = {
  seccionActual: string;
  secciones: SeccionDelEdificio[];
};

/** Las secciones agrupadas en el orden en que aparece cada grupo. */
function agrupar(secciones: SeccionDelEdificio[]): Array<[string, SeccionDelEdificio[]]> {
  const grupos = new Map<string, SeccionDelEdificio[]>();
  for (const seccion of secciones) {
    grupos.set(seccion.grupo, [...(grupos.get(seccion.grupo) ?? []), seccion]);
  }
  return [...grupos.entries()];
}

export function MenuDelEdificio({ seccionActual, secciones }: Props) {
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
    <nav className="menu-del-edificio" aria-label="Secciones del edificio">
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
