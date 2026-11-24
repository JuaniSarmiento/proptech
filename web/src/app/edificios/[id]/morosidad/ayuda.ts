/**
 * Ayuda "?" de Morosidad (D8, D-102, change 10a, H-029).
 */
export const AYUDA_MOROSIDAD = {
  paraQueSirve:
    "Acá ves qué unidades tienen deuda vencida hoy, cuánto deben entre capital e intereses y desde cuándo. Los morosos críticos van primero y, dentro de cada grupo, los que más deben.",
  pasos: [
    "Mirá el resumen de arriba: cuántas unidades deben, cuántas son morosos críticos y el total vencido.",
    "Recorré la lista: cada unidad dice quiénes son sus propietarios, su situación y desde qué vencimiento debe.",
    "Si lo necesitás en una planilla, tocá Exportar a Excel (sólo aparece si tu perfil lo permite).",
  ],
  ejemplo:
    "La 1A figura como moroso crítico: debe tres liquidaciones, la más vieja venció hace 69 días y ya tiene intereses registrados.",
  yDespues:
    "El interés es el que ya está registrado en el libro hasta la fecha que indica la pantalla. Para cobrar, el vecino informa su pago y se confirma en Pagos.",
};
