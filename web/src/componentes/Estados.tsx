/**
 * Estados comunes de cada pantalla (D8, tarea 3.7): cargando (esqueleto,
 * sin girador a pantalla completa), vacío, error (con "Reintentar", nunca
 * el texto técnico de la API), sin permiso, no existe y sin sesión. Cada
 * variante recibe su texto por props, ya en castellano simple: este
 * componente nunca ve el cuerpo crudo de la API, así que no puede
 * filtrarlo mal (L-007 lo cubre en la capa del cliente, 3.3).
 *
 * Bug real encontrado en el barrido de 5.1: "error"/"sinPermiso"/
 * "noExiste"/"sinSesion" siempre reemplazan TODA la pantalla (ningún
 * `page.tsx` las anida dentro de `ArmazonDelEdificio`, que es quien pone
 * el `<main>` y el título) — así que sin su propio `<main>` y su propio
 * `<h1>`, el documento quedaba sin landmark principal y sin encabezado de
 * nivel 1 (`landmark-one-main`/`page-has-heading-one` de axe), violación
 * que un test de componente en jsdom no detecta (no corre esas reglas de
 * documento completo sobre un fragmento aislado). "vacio"/"cargando" NO
 * llevan `<main>` a propósito: esas sí se anidan dentro del `<main>` que
 * ya puso `ArmazonDelEdificio` — un segundo `<main>` ahí sería la misma
 * violación al revés (dos landmarks principales).
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
        <main className="estados estados--error">
          <h1>{props.mensaje}</h1>
          <button type="button" onClick={props.onReintentar}>
            Reintentar
          </button>
        </main>
      );

    case "sinPermiso":
      return (
        <main className="estados estados--sin-permiso">
          <h1>No podés {props.queNoPuede}.</h1>
          <p>Esto lo puede hacer el titular de la administración.</p>
        </main>
      );

    case "noExiste":
      return (
        <main className="estados estados--no-existe">
          <h1>No encontramos este edificio</h1>
          <a href="/edificios">Mis edificios</a>
        </main>
      );

    case "sinSesion":
      return (
        <main className="estados estados--sin-sesion">
          <h1>Tu sesión expiró. Iniciá sesión de nuevo.</h1>
        </main>
      );
  }
}
