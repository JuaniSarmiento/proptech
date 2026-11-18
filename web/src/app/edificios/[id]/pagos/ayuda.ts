/**
 * Ayuda "?" de Pagos, la bandeja del administrador (D8, D-102, change 8, H-025).
 */
export const AYUDA_PAGOS = {
  paraQueSirve:
    "Acá están los pagos que informaron los vecinos del edificio. Los revisás contra el comprobante y decidís: confirmarlos, rechazarlos, y si ya confirmaste uno, revertirlo o pasarlo a otra unidad.",
  pasos: [
    "Tocá Ver comprobante para abrir lo que subió el vecino y compararlo con lo que informó.",
    "Confirmar acredita el pago en la cuenta de la unidad; Rechazar te pide el motivo y se lo muestra al vecino.",
    "Un pago ya confirmado se puede Revertir (con motivo) o Reimputar a otra unidad si el vecino se equivocó; si ya lo reimputaste, el renglón dice dónde está ahora.",
    "Si un vecino te pasó el comprobante por otro lado, tocá Informar un pago y cargalo vos por él.",
  ],
  ejemplo:
    "Un vecino informó $43.350,00 para la 1A. Abrís el comprobante, el monto y el número de operación coinciden: tocás Confirmar y queda acreditado.",
  yDespues:
    "Lo que confirmás entra al libro de la unidad y baja su deuda. Nada se borra: revertir o reimputar deja registrado quién lo hizo y por qué.",
};
