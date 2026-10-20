/**
 * Ayuda "?" de intereses y vencimiento (D8, D-102, tarea 4.6).
 */
export const AYUDA_CONFIGURACION = {
  paraQueSirve:
    "Acá configurás cómo se calculan los intereses y cuándo vence el pago de las expensas.",
  pasos: [
    "Revisá la configuración vigente arriba: tasa, fondo de reserva y vencimiento.",
    'Si algo cambia, abrí "Cambiar configuración" y elegí desde qué fecha rige.',
    "La versión anterior queda guardada en el historial, nunca se borra.",
  ],
  ejemplo:
    "Si desde el 1 de noviembre la tasa pasa de 3,00 % a 4,00 %, cargás una versión nueva que rige desde esa fecha. Octubre se sigue calculando con 3,00 %.",
  yDespues: "La nueva configuración se aplica a partir de la fecha que elegiste.",
};
