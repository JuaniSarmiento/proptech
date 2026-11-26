/**
 * Ayuda "?" de Cuentas de vendedores (D8, D-102, change 4d, H-034, D-168).
 */
export const AYUDA_CUENTAS_DE_VENDEDORES = {
  paraQueSirve:
    'Acá ves la deuda que pasó a nombre de quienes vendieron una unidad con la opción "a nombre del vendedor". Esa deuda ya no está en la unidad ni suma a la morosidad: se le cobra al vendedor desde su cuenta.',
  pasos: [
    "Mirá la lista: va primero quien más debe, y también quedan las cuentas que ya están en cero.",
    "Abrí una cuenta para ver la deuda por período y todos sus movimientos.",
    "Si el vendedor te paga, registrá el cobro con su importe y la fecha de la transferencia.",
  ],
  ejemplo:
    "Ana vendió la 1A y le pasaste 30.000,00. Cuando te transfiere 20.000,00, el cobro se imputa a lo más viejo primero y su cuenta baja a 10.000,00.",
  yDespues:
    "El cobro queda registrado en el libro y la cuenta muestra la deuda nueva. La deuda del vendedor no genera interés nuevo.",
};
