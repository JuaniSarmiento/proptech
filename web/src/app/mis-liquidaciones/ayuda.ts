/**
 * Ayudas "?" de las pantallas de liquidaciones del portal del vecino (D8, D-102, change 11, H-040).
 */
export const AYUDA_MIS_LIQUIDACIONES = {
  paraQueSirve: "Elegí una de tus unidades para ver las expensas que el administrador ya emitió.",
  pasos: [
    "Buscá la unidad que querés mirar.",
    "Tocá Ver liquidaciones para abrir la lista de sus meses.",
  ],
  ejemplo: "Si tenés la 1A y la 2B, abrís cada una por separado y ves sus propios importes.",
  yDespues: "En la lista de la unidad elegís un mes y ves cómo se arma tu expensa.",
};

export const AYUDA_LIQUIDACIONES_DE_LA_UNIDAD = {
  paraQueSirve:
    "Acá están todas las expensas emitidas de tu edificio, de la más nueva a la más vieja, con lo que te toca pagar de esta unidad.",
  pasos: [
    "Mirá el mes, la fecha de vencimiento y el total de tu unidad.",
    "Tocá Ver expensa para abrir el detalle de ese mes.",
  ],
  ejemplo:
    "Noviembre de 2026 vence el 10/11/2026: ese día tendría que estar pagado el total que figura en la lista.",
  yDespues: "Dentro de cada expensa ves el detalle y la comparación con el mes anterior.",
};

export const AYUDA_EXPENSA = {
  paraQueSirve:
    "Te explica tu expensa de un mes: cuánto te toca pagar y de dónde sale cada importe, y cómo cambió respecto del mes anterior.",
  pasos: [
    "Mirá la tabla Tu expensa: es lo que te corresponde a vos, concepto por concepto.",
    "Los gastos del edificio muestran en qué se gastó y qué parte del total es cada categoría.",
    "Abajo comparás con el mes anterior: la diferencia dice cuánto subió o bajó tu total.",
  ],
  ejemplo:
    "Si Limpieza pasó de 80.000,00 a 100.000,00, la diferencia de esa categoría es 20.000,00.",
  yDespues:
    "Cuando pagues, informá tu pago desde Mis pagos con el comprobante, y bajá el PDF de la expensa desde Comprobantes.",
};
