/**
 * Vocabulario de perfiles (D5, D-096: la matriz de permisos del 2a), en
 * castellano simple para la lista y el panel lateral de "qué puede cada
 * perfil". `super_admin` puede aparecer en la lista (es quien la mira) pero
 * no se invita desde acá: la API lo rechaza (`CuerpoPersonal.rol`, D5).
 */
export type Rol = "super_admin" | "administrador" | "contador" | "auxiliar" | "consejo";

export const ROLES_INVITABLES: { valor: Exclude<Rol, "super_admin">; etiqueta: string }[] = [
  { valor: "administrador", etiqueta: "Administrador" },
  { valor: "contador", etiqueta: "Contador" },
  { valor: "auxiliar", etiqueta: "Auxiliar" },
  { valor: "consejo", etiqueta: "Consejo" },
];

/** `auxiliar` y `consejo` sólo existen con alcance de un edificio (D5): la
 * API rechaza "toda la empresa" para esos dos. */
export const ROLES_SOLO_EDIFICIO = new Set<Rol>(["auxiliar", "consejo"]);

const _ETIQUETAS: Record<Rol, string> = {
  super_admin: "Super admin",
  administrador: "Administrador",
  contador: "Contador",
  auxiliar: "Auxiliar",
  consejo: "Consejo",
};

export function etiquetaDePerfil(rol: string): string {
  return _ETIQUETAS[rol as Rol] ?? rol;
}

const _QUE_PUEDE: Record<Rol, string> = {
  super_admin: "Administra toda la empresa: invita personal y crea edificios.",
  administrador:
    "Carga gastos, emite liquidaciones y confirma pagos, de la empresa o de un edificio.",
  contador: "Carga gastos, emite liquidaciones y confirma pagos; no anula ni revierte pagos.",
  auxiliar: "Ve la configuración de su edificio; no carga ni aprueba nada.",
  consejo: "Ve la configuración de su edificio; no carga ni aprueba nada.",
};

export function queHaceElPerfil(rol: string): string {
  return _QUE_PUEDE[rol as Rol] ?? "Perfil sin descripción.";
}
