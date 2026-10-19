"use client";

/**
 * Ayuda "?" de cada pantalla (D8, The Always-Help Rule): panel no modal con
 * las tres partes ("¿Para qué sirve esta pantalla?", "¿Qué hago acá?",
 * "¿Y después?") y su texto por props, para que cada pantalla lo cambie en
 * el mismo commit que la construye. Se abre al tocar o con clic, y con
 * `Enter`/`Espacio` por ser un `<button>` nativo (el navegador los activa
 * solo, no hace falta código). Se cierra con un botón visible o con `Esc`
 * (`useCerrarConEscape`, que cierra sólo la capa de arriba si la ayuda está
 * anidada dentro de un panel lateral) y devuelve el foco al "?".
 */

import { useId, useRef, useState } from "react";
import { useCerrarConEscape } from "../lib/teclado/useCerrarConEscape";

type Props = {
  paraQueSirve: string;
  pasos: string[];
  yDespues: string;
};

export function Ayuda({ paraQueSirve, pasos, yDespues }: Props) {
  const [abierta, setAbierta] = useState(false);
  const botonRef = useRef<HTMLButtonElement>(null);
  const idPanel = useId();

  function cerrar() {
    setAbierta(false);
    botonRef.current?.focus();
  }

  useCerrarConEscape(abierta, cerrar);

  return (
    <div className="ayuda">
      <button
        ref={botonRef}
        type="button"
        className="ayuda__boton"
        aria-expanded={abierta}
        aria-controls={idPanel}
        onClick={() => setAbierta(true)}
      >
        <span aria-hidden="true">?</span>
        <span className="sr-only">Ayuda</span>
      </button>
      {abierta ? (
        <section
          id={idPanel}
          aria-label="Ayuda: para qué sirve esta pantalla"
          className="ayuda__panel"
        >
          <button type="button" className="ayuda__cerrar" onClick={cerrar}>
            Cerrar ayuda
          </button>
          <h2>¿Para qué sirve esta pantalla?</h2>
          <p>{paraQueSirve}</p>
          <h2>¿Qué hago acá?</h2>
          <ol>
            {pasos.map((paso) => (
              <li key={paso}>{paso}</li>
            ))}
          </ol>
          <h2>¿Y después?</h2>
          <p>{yDespues}</p>
        </section>
      ) : null}
    </div>
  );
}
