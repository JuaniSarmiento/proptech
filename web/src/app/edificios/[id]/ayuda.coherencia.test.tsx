/**
 * @vitest-environment jsdom
 */
// pulido-2 (3d), 4.3: RB3D-4 del rompedor (verify-1, 30/10/2026), reubicado acá. Fallaba
// sobre b1ec660: la ayuda decía que un edificio recién creado "arranca en 0 de 7 pasos",
// pero la API real devuelve 4 pasos hechos (backend/tests/integracion/
// test_resumen_puesta_a_punto.py::test_edificio_recien_creado). Complementa a
// `ayuda.test.ts` (que fija el texto): este compara el arranque con la barra renderizada.
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Resumen } from "../../../lib/api/tipos";
import { AYUDA_RESUMEN } from "./ayuda";
import { PantallaResumen } from "./Pantalla";

vi.mock("../../../componentes/accionesGeoref", () => ({
  provinciasAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
  departamentosDeAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
  localidadesDeAction: vi.fn().mockResolvedValue({ estado: "ok", datos: [] }),
}));
afterEach(cleanup);

// Los `pasos` exactos que la API real da para un edificio recién creado.
const RECIEN_CREADO_SEGUN_LA_API: Resumen = {
  nombre: "Ficticio",
  localidad: "Mendoza",
  provincia_id: "50",
  departamento_id: "50007",
  localidad_id: "50007010",
  calle_y_numero: null,
  pisos: 4,
  subsuelos: 1,
  cantidad_unidades: 0,
  unidades_sin_piso_completo: 0,
  estado_migracion: "pendiente",
  informe: { suma: "0.000000", diferencia: "-1.000000", estado: "fuera_de_tolerancia" },
  pasos: {
    ubicacion: "hecho",
    unidades: "falta",
    coeficientes: "falta",
    grupos: "hecho",
    categorias: "hecho",
    intereses_y_vencimiento: "hecho",
    saldos_previos: "falta",
  },
  listo_para_liquidar: false,
};

it("RB3D-4: el arranque que cuenta la ayuda coincide con la barra de un edificio recién creado", () => {
  render(
    <PantallaResumen
      id="1"
      resumen={RECIEN_CREADO_SEGUN_LA_API}
      vigente={null}
      accionEditar={() => Promise.resolve(null)}
    />,
  );
  const barra = screen.getByText(/\d+ de 7 pasos/).textContent ?? "";
  const arranque = /arranca en (\d+ de 7 pasos)/.exec(AYUDA_RESUMEN.ejemplo)?.[1];
  expect(arranque).toBe(barra);
});
