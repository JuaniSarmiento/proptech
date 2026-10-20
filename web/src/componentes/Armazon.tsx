/**
 * Armazón de toda pantalla del administrador (enmienda del shape del 3b,
 * 20/10/2026): barra superior con dónde está y quién es, el menú (si la
 * pantalla tiene uno) y el contenido a todo el ancho. Composición pura, sin
 * estado: el menú y la ayuda manejan su propia interactividad.
 *
 * La ayuda "?" acoplada empuja el contenido por CSS (`.armazon:has(...)`),
 * no por estado compartido: así cada pantalla sigue dueña de su `Ayuda` y
 * el armazón no necesita saber si está abierta.
 */

import { Building2, ChevronRight, UserRound } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  /** El edificio en el que está parado el administrador, si está dentro de
   * uno: la barra muestra "Mis edificios › <nombre>". */
  edificio?: { nombre: string };
  menu?: ReactNode;
  children: ReactNode;
};

export function Armazon({ edificio, menu, children }: Props) {
  return (
    <div className="armazon" data-con-menu={menu ? "true" : "false"}>
      <header className="barra-superior">
        <a href="/edificios" className="barra-superior__marca">
          <span className="barra-superior__logo" aria-hidden="true">
            <Building2 size={18} strokeWidth={2} />
          </span>
          PropTech
        </a>
        {edificio ? (
          <nav aria-label="Estás en" className="barra-superior__migas">
            <ol>
              <li>
                <a href="/edificios">Mis edificios</a>
              </li>
              <li aria-current="page" title={edificio.nombre}>
                <ChevronRight size={16} aria-hidden="true" className="barra-superior__separador" />
                <span className="barra-superior__edificio">{edificio.nombre}</span>
              </li>
            </ol>
          </nav>
        ) : null}
        {/* La API todavía no expone quién inició sesión (no hay un "yo"):
         * se muestra el rol de esta superficie, nunca un nombre inventado. */}
        <p className="barra-superior__usuario">
          <span className="barra-superior__avatar" aria-hidden="true">
            <UserRound size={16} strokeWidth={2} />
          </span>
          Administración
        </p>
      </header>
      <div className="armazon__cuerpo">
        {menu}
        <main className="armazon__contenido">{children}</main>
      </div>
    </div>
  );
}
