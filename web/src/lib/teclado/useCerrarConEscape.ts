"use client";

/**
 * `Esc` cierra la capa de ARRIBA, nunca todas a la vez (D8, tarea 3.6): la
 * ayuda abierta encima de un panel lateral se cierra con el primer `Esc`,
 * sin tocar el panel; un segundo `Esc` cierra el panel.
 *
 * Una pila compartida (y un único listener en `document`) en vez de un
 * `onKeyDown` por componente: dos listeners en `document` para el mismo
 * evento se llaman los DOS (no hay "capturar y frenar" entre listeners del
 * mismo nodo), así que "sólo la de arriba" se resuelve con una pila, no con
 * `stopPropagation`.
 */

import { useEffect, useRef } from "react";

type Cierre = () => void;

const _pila: Cierre[] = [];
let _listenerInstalado = false;

function _asegurarListener() {
  if (_listenerInstalado) {
    return;
  }
  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape") {
      return;
    }
    const deArriba = _pila.at(-1);
    deArriba?.();
  });
  _listenerInstalado = true;
}

/** Mientras `activo` es verdadero, `alCerrar` queda en la pila como la capa
 * de arriba (o debajo de otra que se abrió después). `Esc` llama sólo a la
 * de arriba. */
export function useCerrarConEscape(activo: boolean, alCerrar: () => void): void {
  const alCerrarRef = useRef(alCerrar);
  alCerrarRef.current = alCerrar;

  useEffect(() => {
    if (!activo) {
      return;
    }
    _asegurarListener();
    const entrada: Cierre = () => alCerrarRef.current();
    _pila.push(entrada);
    return () => {
      const indice = _pila.lastIndexOf(entrada);
      if (indice !== -1) {
        _pila.splice(indice, 1);
      }
    };
  }, [activo]);
}
