"use client";

/**
 * El aviso de instalar la app en iPhone (H-040, C05). Safari de iPhone no ofrece instalarla solo: la
 * persona tiene que hacer "Compartir" y "Agregar a inicio", y el aviso se lo explica. Sólo en iPhone,
 * sólo si la app no está ya instalada y sólo hasta que la persona lo cierra: se recuerda en el
 * navegador (`localStorage`, siempre con `try/catch`: sin almacenamiento el aviso se ve igual y nada
 * se rompe). Va en el flujo de la pantalla, nunca flotando sobre el contenido.
 */

import { Share, SquarePlus } from "lucide-react";
import { useEffect, useState } from "react";

const CLAVE = "proptech-aviso-de-instalacion-cerrado";

function debeMostrarse(): boolean {
  if (!/iPhone|iPod/.test(navigator.userAgent)) return false;
  const instalada =
    (navigator as Navigator & { standalone?: boolean }).standalone === true ||
    window.matchMedia("(display-mode: standalone)").matches;
  if (instalada) return false;
  try {
    return window.localStorage.getItem(CLAVE) !== "1";
  } catch {
    return true;
  }
}

export function AvisoDeInstalacion() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(debeMostrarse());
  }, []);

  if (!visible) return null;

  function cerrar() {
    setVisible(false);
    try {
      window.localStorage.setItem(CLAVE, "1");
    } catch {
      /* se vuelve a mostrar la próxima vez, sin romper nada */
    }
  }

  return (
    <section className="aviso-de-instalacion" aria-labelledby="aviso-de-instalacion-titulo">
      <h2 id="aviso-de-instalacion-titulo">Agregar a la pantalla de inicio</h2>
      <p>Así entrás a tus expensas con un solo toque, como a cualquier otra app.</p>
      <ol>
        <li>
          <Share size={20} strokeWidth={1.75} aria-hidden="true" />
          <span>
            Tocá <strong>Compartir</strong>, el botón con la flecha hacia arriba de Safari.
          </span>
        </li>
        <li>
          <SquarePlus size={20} strokeWidth={1.75} aria-hidden="true" />
          <span>
            Elegí <strong>Agregar a inicio</strong>.
          </span>
        </li>
      </ol>
      <button type="button" onClick={cerrar}>
        Cerrar aviso
      </button>
    </section>
  );
}
