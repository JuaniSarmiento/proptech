/**
 * Ayuda "?" de la preliquidación (D8, D-102, change 7, H-011).
 */
export const AYUDA_PRELIQUIDACION = {
  paraQueSirve:
    "Acá ves, antes de emitir, lo que va a pagar cada unidad en este período: su parte de los gastos, el fondo de reserva, los cargos particulares y el interés por mora. Mirarla no guarda nada ni emite nada.",
  pasos: [
    "Mirá el total de cada unidad y el total de la liquidación.",
    "En los bloques Ordinaria y Extraordinaria ves cuánto pesa cada categoría de gasto, ya con las notas de crédito restadas.",
    "Si algo no cierra, corregí el gasto o el cargo y volvé a abrir esta pantalla: se calcula de nuevo cada vez.",
  ],
  ejemplo:
    "Un gasto de limpieza de 100.000,00 se reparte entre todas las unidades según su coeficiente; con una nota de crédito de 10.000,00 queda en 90.000,00. El fondo de reserva es un porcentaje de la ordinaria, sin los cargos particulares.",
  yDespues:
    "Cuando esté todo bien, el paso siguiente es emitir la liquidación. Un período se prepara cuando el anterior ya está emitido.",
};
