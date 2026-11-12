/**
 * Ayuda "?" de ajustar el saldo inicial de una unidad (D8, D-102, D11, change 5, H-010).
 */
export const AYUDA_AJUSTE = {
  paraQueSirve:
    "Acá corregís el saldo inicial de una unidad cuando el archivo cargó de menos, una vez confirmados los saldos del edificio. El ajuste suma una deuda nueva: no toca lo que ya estaba cargado.",
  pasos: [
    "Escribí el importe que falta, sin signo, con coma para los decimales.",
    "Elegí a qué concepto corresponde: ordinaria, fondo de reserva o extraordinaria.",
    "Contá el motivo: queda registrado junto con quién lo hizo y cuándo.",
    "Registrá el ajuste y confirmalo: no se deshace.",
  ],
  ejemplo:
    "A la 1A le faltó la expensa extraordinaria de julio: cargás 5.000,00 como Extraordinaria, con ese motivo, y la unidad pasa a deber 5.000,00 más.",
  yDespues:
    "La deuda nueva vence el día del ajuste y, si no se paga, genera interés desde el día siguiente, como cualquier otra. Para corregir un ajuste de más, usá una corrección del libro.",
};
