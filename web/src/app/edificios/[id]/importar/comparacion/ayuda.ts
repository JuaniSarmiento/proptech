/**
 * Ayuda "?" de la comparación de saldos (D8, D-102, D11, change 5).
 */
export const AYUDA_COMPARACION = {
  paraQueSirve:
    "Acá ves, unidad por unidad, lo que dice el archivo que subiste contra el saldo que te dio el administrador anterior. Los dos totales pueden coincidir y aun así haber unidades que no cierran.",
  pasos: [
    "Mirá la columna Diferencia: es el borrador menos el control. Con signo menos, el borrador tiene menos deuda que el control.",
    "Si todo coincide, no hay nada que aceptar.",
    "Si hay diferencias, revisalas y corregí el archivo, o aceptalas tal cual con Aceptar diferencias. Queda registrado quién las aceptó y cuándo.",
  ],
  ejemplo:
    "La 1A figura con 169.000,00 en el borrador y 159.000,00 en el control: la diferencia es 10.000,00. La 2A figura con 10.000,00 de menos. Los totales coinciden, pero son dos unidades con diferencia.",
  yDespues:
    "Si subís un archivo nuevo, el borrador anterior se descarta y hay que aceptar de nuevo las diferencias del nuevo.",
};
