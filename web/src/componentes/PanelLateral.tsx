"use client";

/**
 * Panel lateral (D8, tarea 3.6): formularios de alta y edición se abren
 * acá, nunca en un modal ni en una página aparte. Atrapa el foco mientras
 * está abierto (`Tab` desde el último control vuelve al primero), se cierra
 * con un botón visible o con `Esc` (sólo la capa de arriba: si la ayuda
 * está abierta adentro, el primer `Esc` la cierra a ella, no al panel) y
 * devuelve el foco a quien lo abrió.
 *
 * `<dialog>` SIN `showModal()` a propósito: `showModal()` lo vuelve modal
 * (bloquea el resto de la página, agrega `::backdrop` y Chrome cierra con
 * `Esc` por su cuenta, pisando `useCerrarConEscape`). Con sólo el atributo
 * `open`, es un elemento de flujo normal: el foco y el `Esc` los maneja
 * este componente.
 *
 * Variante "ancho" (enmienda del 20/10/2026): el mismo panel, con el mismo
 * foco, `Esc` y devolución de foco, pero EN EL FLUJO de la pantalla y a
 * todo el ancho del contenido, para formularios largos que en una hoja de
 * 28rem quedaban como una columna angosta (Intereses y vencimiento).
 */

import { X } from "lucide-react";
import { type ReactNode, type RefObject, useEffect, useRef } from "react";
import { useCerrarConEscape } from "../lib/teclado/useCerrarConEscape";

type Props = {
  abierto: boolean;
  titulo: string;
  alCerrar: () => void;
  devolverFocoA: RefObject<HTMLElement | null>;
  /** Una línea gris debajo del título. */
  descripcion?: string;
  variante?: "lateral" | "ancho";
  children: ReactNode;
};

const _SELECTOR_FOCUSABLE =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function PanelLateral({
  abierto,
  titulo,
  alCerrar,
  devolverFocoA,
  descripcion,
  variante = "lateral",
  children,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);

  function cerrarYDevolverFoco() {
    alCerrar();
    devolverFocoA.current?.focus();
  }

  useCerrarConEscape(abierto, cerrarYDevolverFoco);

  // Al abrir, el foco entra al panel (primer control). La trampa de foco
  // incluye la ayuda acoplada de esta pantalla y vive en un listener
  // imperativo, no en `onKeyDown` del `<div>`:
  // un `<div>` sin rol interactivo con manejo de teclado dispara
  // `lint/a11y/noStaticElementInteractions` de biome (ya pasó en 3.5).
  useEffect(() => {
    if (!abierto) {
      return;
    }
    const nodo = panelRef.current;
    if (!nodo) {
      return;
    }
    // La ayuda acoplada pertenece al mismo alcance de teclado aunque su
    // región viva fuera del panel en el DOM. El resto de la pantalla no.
    const ayuda = nodo.closest("main")?.querySelector(".ayuda");
    const focosables = () =>
      [
        ...new Set([
          ...nodo.querySelectorAll<HTMLElement>(_SELECTOR_FOCUSABLE),
          ...(ayuda?.querySelectorAll<HTMLElement>(_SELECTOR_FOCUSABLE) ?? []),
        ]),
      ].filter(
        (elemento) =>
          !elemento.hasAttribute("disabled") && elemento.getAttribute("type") !== "hidden",
      );
    focosables()[0]?.focus();

    function alTeclado(evento: KeyboardEvent) {
      if (evento.key !== "Tab") {
        return;
      }
      const lista = focosables();
      if (lista.length === 0) {
        return;
      }
      const indice = lista.indexOf(document.activeElement as HTMLElement);
      const siguiente = (indice + (evento.shiftKey ? -1 : 1) + lista.length) % lista.length;
      evento.preventDefault();
      lista[siguiente]?.focus();
    }
    document.addEventListener("keydown", alTeclado);
    return () => document.removeEventListener("keydown", alTeclado);
  }, [abierto]);

  if (!abierto) {
    return null;
  }

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-label={titulo}
      aria-modal="false"
      className={variante === "ancho" ? "panel-lateral panel-lateral--ancho" : "panel-lateral"}
    >
      <div className="panel-lateral__cabecera">
        <div>
          <h2>{titulo}</h2>
          {descripcion ? <p className="panel__descripcion">{descripcion}</p> : null}
        </div>
        <button type="button" className="panel-lateral__cerrar" onClick={cerrarYDevolverFoco}>
          <X size={16} strokeWidth={2} aria-hidden="true" />
          Cerrar
        </button>
      </div>
      {children}
    </div>
  );
}
