/**
 * Estados comunes de cada pantalla (D8, tarea 3.7): cargando (esqueleto,
 * sin girador a pantalla completa), vacío, error (con "Reintentar", nunca
 * el texto técnico de la API), sin permiso, no existe y sin sesión. Cada
 * variante recibe su texto por props, ya en castellano simple: este
 * componente nunca ve el cuerpo crudo de la API, así que no puede
 * filtrarlo mal (L-007 lo cubre en la capa del cliente, 3.3).
 */

import type { ReactNode } from "react";

type Props =
  | { tipo: "cargando" }
  | { tipo: "vacio"; mensaje: string; accion?: ReactNode }
  | { tipo: "error"; mensaje: string; onReintentar: () => void }
  | { tipo: "sinPermiso"; queNoPuede: string }
  | { tipo: "noExiste" }
  | { tipo: "sinSesion" };

export function Estados(props: Props) {
  switch (props.tipo) {
    case "cargando":
      return (
        <div role="status" aria-label="Cargando" className="estados estados--cargando">
          <div className="estados__esqueleto-linea" />
          <div className="estados__esqueleto-linea" />
          <div className="estados__esqueleto-linea" />
        </div>
      );

    case "vacio":
      return (
        <div className="estados estados--vacio">
          <p>{props.mensaje}</p>
          {props.accion}
        </div>
      );

    case "error":
      return (
        <div className="estados estados--error">
          <p>{props.mensaje}</p>
          <button type="button" onClick={props.onReintentar}>
            Reintentar
          </button>
        </div>
      );

    case "sinPermiso":
      return (
        <div className="estados estados--sin-permiso">
          <p>No podés {props.queNoPuede}.</p>
          <p>Esto lo puede hacer el titular de la administración.</p>
        </div>
      );

    case "noExiste":
      return (
        <div className="estados estados--no-existe">
          <p>No encontramos este edificio</p>
          <a href="/edificios">Mis edificios</a>
        </div>
      );

    case "sinSesion":
      return (
        <div className="estados estados--sin-sesion">
          <p>Tu sesión expiró. Iniciá sesión de nuevo.</p>
        </div>
      );
  }
}
