/**
 * Ayuda "?" de Cambiar titular (D8, D-102, change 4d, H-034, R32).
 */
export const AYUDA_CAMBIO_DE_TITULAR = {
  paraQueSirve:
    "Acá registrás que una unidad cambió de dueño. Los vendedores dejan de ser propietarios, los compradores pasan a serlo, y vos elegís qué pasa con la expensa del mes y con la deuda de los meses anteriores.",
  pasos: [
    "Poné la fecha del cambio y marcá quién vende: sólo aparecen los propietarios actuales de la unidad.",
    "Cargá a quien compra, con su email si lo tenés. Si son varios, agregalos uno por uno.",
    "Elegí la expensa del mes: entera para la unidad o prorrateada por días entre vendedor y comprador.",
    "Elegí qué pasa con la deuda anterior: queda en la unidad o pasa a una cuenta del vendedor.",
  ],
  ejemplo:
    "La 1A se vende el 10 de noviembre y debe 45.230,10. Con la deuda a nombre del vendedor, la unidad queda sin esa deuda y se la cobrás después desde Cuentas de vendedores.",
  yDespues:
    "Te mostramos el resultado y el historial de la unidad. Si la deuda quedó en la unidad, el aviso dice cuánto hereda el comprador: avisale. Este paso no se deshace.",
};
