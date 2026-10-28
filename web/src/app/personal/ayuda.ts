/**
 * Ayuda "?" de Personal (D-102, tarea 7.3), texto del shape (sección 6)
 * palabra por palabra.
 */
export const AYUDA_PERSONAL = {
  paraQueSirve: "Acá ves quién trabaja con vos y qué puede hacer cada uno.",
  pasos: [
    "Tocá 'Invitar a alguien'.",
    "Elegí su perfil y dónde trabaja.",
    "Le llega un mail para entrar.",
  ],
  yDespues: "Cuando acepte, aparece como 'Aceptada' y ya puede ingresar.",
};

/**
 * 2d/7.6 (D11, D13): la misma pantalla, sólo lectura, para el administrador
 * principal — ve a su personal de abajo, pero invitar, revocar y quitar
 * los hace el super admin.
 */
export const AYUDA_PERSONAL_SOLO_LECTURA = {
  paraQueSirve: "Acá ves quién trabaja con vos y qué puede hacer cada uno.",
  pasos: ["La gestión (invitar, revocar, quitar) la hace el super admin."],
  yDespues: "Si necesitás sumar o sacar a alguien, pedíselo al super admin.",
};
