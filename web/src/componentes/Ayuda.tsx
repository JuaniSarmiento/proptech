"use client";

/**
 * Ayuda "?" de cada pantalla (D8, The Always-Help Rule; enmienda del
 * 20/10/2026): un panel ACOPLADO a la derecha que empuja el contenido (no
 * lo tapa) y queda abierto mientras se trabaja. Tiene las tres partes de
 * siempre ("¿Para qué sirve esta pantalla?", "¿Qué hago acá?", "¿Y
 * después?") más un ejemplo concreto.
 *
 * Abrirla NO mueve el foco: sigue en el botón, que pasa a decir que está
 * abierta (`aria-expanded`), y el panel queda justo después en el orden del
 * documento, así que el siguiente `Tab` entra a leerlo. Se cierra con el
 * mismo botón, con "Cerrar" o con `Esc` (`useCerrarConEscape`: sólo la capa
 * de arriba, así un panel lateral abierto después se cierra primero), y el
 * foco vuelve al botón.
 *
 * Quién empuja a quién lo resuelve el CSS (`.armazon:has(.ayuda__panel)`):
 * el panel sólo existe en el DOM mientras está abierto.
 */

import { CircleHelp, X } from "lucide-react";
import { useId, useRef, useState } from "react";
import { useCerrarConEscape } from "../lib/teclado/useCerrarConEscape";

type Props = {
  paraQueSirve: string;
  pasos: string[];
  /** Un caso concreto, con números o nombres de ejemplo. */
  ejemplo?: string;
  yDespues: string;
};

export function Ayuda({ paraQueSirve, pasos, ejemplo, yDespues }: Props) {
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
        onClick={() => (abierta ? cerrar() : setAbierta(true))}
      >
        <CircleHelp size={18} strokeWidth={1.75} aria-hidden="true" />
        Ayuda
      </button>
      {abierta ? (
        <section
          id={idPanel}
          aria-label="Ayuda: para qué sirve esta pantalla"
          className="ayuda__panel"
        >
          <div className="ayuda__cabecera">
            <p className="ayuda__titulo">
              <CircleHelp size={18} strokeWidth={1.75} aria-hidden="true" />
              Ayuda de esta pantalla
            </p>
            {/* Se ve "Cerrar"; el nombre accesible empieza igual (WCAG
             * 2.5.3) y aclara qué cierra. */}
            <button
              type="button"
              className="ayuda__cerrar"
              aria-label="Cerrar ayuda"
              onClick={cerrar}
            >
              <X size={16} strokeWidth={2} aria-hidden="true" />
              Cerrar
            </button>
          </div>
          <h2>¿Para qué sirve esta pantalla?</h2>
          <p>{paraQueSirve}</p>
          <h2>¿Qué hago acá?</h2>
          <ol className="ayuda__pasos">
            {pasos.map((paso) => (
              <li key={paso}>{paso}</li>
            ))}
          </ol>
          {ejemplo ? (
            <>
              <h2>Un ejemplo</h2>
              <p className="ayuda__ejemplo">{ejemplo}</p>
            </>
          ) : null}
          <h2>¿Y después?</h2>
          <p>{yDespues}</p>
        </section>
      ) : null}
    </div>
  );
}
