/**
 * Ayuda "?" de importar desde Excel (D8, D-102, D11, change 5).
 */
export const AYUDA_IMPORTAR = {
  paraQueSirve:
    "Acá cargás de una vez el padrón del edificio (unidades, coeficientes y propietarios) desde una planilla de Excel, en vez de cargar cada unidad a mano.",
  pasos: [
    "Descargá la plantilla y completá la hoja Unidades, una fila por unidad.",
    "Elegí el archivo y la fecha desde la que el sistema arranca a llevar las cuentas.",
    "Tocá Importar: si hay errores te decimos hoja, fila y columna, y no se carga nada.",
  ],
  ejemplo:
    "Una torre con doce unidades: completás doce filas con el identificador, el tipo, el piso, el coeficiente y la superficie. Si el propietario trae email, queda registrado, pero no le mandamos ninguna invitación.",
  yDespues:
    "Las unidades quedan cargadas en el edificio. Después podés revisar el padrón y los coeficientes, e invitar a los vecinos cuando quieras.",
};
