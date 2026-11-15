/** La preliquidación de la base de los ejemplos (H-011), para los tests de la pantalla y del
 * cliente de la API: los mismos importes que `aceptacion/H-011` (datos inventados). */

import type { Preliquidacion } from "../api/liquidaciones";

const EDIFICIO = "11111111-1111-1111-1111-111111111111";

export const PRELIQUIDACION: Preliquidacion = {
  complejo_id: EDIFICIO,
  periodo: "2026-11-01",
  vencimiento: "2026-11-10",
  porcentaje_fondo: "5.00",
  huella: "a".repeat(64),
  totales: {
    gastos: "190000.00",
    notas_de_credito: "10000.00",
    fondo_de_reserva: "6500.00",
    prorrateado: "186500.00",
    cargos_particulares: "5000.00",
    intereses: "0.00",
    total: "191500.00",
  },
  bloques: {
    ordinario: {
      subtotal: "130000.00",
      categorias: [
        { categoria_id: "c1", nombre: "Limpieza", importe: "90000.00", porcentaje: "69.23" },
        { categoria_id: "c2", nombre: "Ascensor", importe: "40000.00", porcentaje: "30.77" },
      ],
    },
    extraordinario: {
      subtotal: "50000.00",
      categorias: [
        { categoria_id: "c3", nombre: "Pintura", importe: "50000.00", porcentaje: "100.00" },
      ],
    },
  },
  grupos: [
    {
      grupo_id: "g1",
      nombre: "Generales",
      metodo: "coeficiente",
      ordinario: "90000.00",
      extraordinario: "50000.00",
    },
  ],
  unidades: [
    {
      unidad_id: "u1",
      identificador: "1A",
      ordinaria: "27000.00",
      fondo_de_reserva: "1350.00",
      extraordinaria: "15000.00",
      cargos_particulares: [{ concepto: "Multa", importe: "5000.00" }],
      intereses: "0.00",
      total: "48350.00",
      sin_obligacion: false,
      por_grupo: [{ grupo_id: "g1", ordinaria: "27000.00", extraordinaria: "15000.00" }],
    },
  ],
  controles: [],
};
