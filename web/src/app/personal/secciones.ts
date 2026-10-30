/**
 * Menú de "Mi administración" (shape del 21/10/2026, tarea 7.3): por ahora
 * una sola sección, "Personal". Se arma con el mismo `MenuDelEdificio` que
 * usa el menú dentro de un edificio (mismo componente, mismo tipo de
 * sección): nunca un menú lateral duplicado.
 *
 * 2d/7.6 (D11): "Personal" se oculta sin `ver_personal` — el super admin y
 * el administrador principal la ven, nadie más.
 */
import type { SeccionDelEdificio } from "../../componentes/MenuDelEdificio";
import { permite, type SesionVisible } from "../../componentes/SesionDePantalla";

export function seccionesDeLaAdministracion(sesion: SesionVisible | null): SeccionDelEdificio[] {
  if (!permite(sesion, "ver_personal")) return [];
  return [
    {
      clave: "personal",
      etiqueta: "Personal",
      href: "/personal",
      grupo: "Mi administración",
      icono: "personal",
    },
  ];
}
