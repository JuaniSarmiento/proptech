/**
 * Ayuda "?" de la cuenta de un vendedor (D8, D-102, change 4d, H-034, D-168).
 */
export const AYUDA_CUENTA_DE_VENDEDOR = {
  paraQueSirve:
    "Acá ves cuánto debe este vendedor, de qué períodos viene y qué movimientos tuvo su cuenta. Es la deuda que le pasaste al vender la unidad.",
  pasos: [
    "Mirá la deuda de arriba: es la que figura hoy en el libro.",
    "En Deuda por período ves, por cada mes y componente, lo que debe, lo que ya cobraste y lo que falta.",
    "Para registrar lo que te pagó, completá el importe y la fecha de la transferencia y confirmá.",
  ],
  ejemplo:
    "Le debe 30.000,00 y te transfiere 20.000,00 el 20/11/2026: registrás el cobro y la cuenta pasa a 10.000,00.",
  yDespues:
    "El cobro se imputa a lo más viejo primero y, dentro de un mes, al interés antes que al capital. No podés cobrar más de lo que debe.",
};
