/**
 * Menú de "Mi administración" (shape del 21/10/2026, tarea 7.3): por ahora
 * una sola sección, "Personal". Se arma con el mismo `MenuDelEdificio` que
 * usa el menú dentro de un edificio (mismo componente, mismo tipo de
 * sección): nunca un menú lateral duplicado.
 */
import type { SeccionDelEdificio } from "../../componentes/MenuDelEdificio";

export function seccionesDeLaAdministracion(): SeccionDelEdificio[] {
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
