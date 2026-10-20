/**
 * R3C-9 (rompedor 3b): coherencia de `lib/api/fixtures/*.json` entre sí.
 * `grupos.json` y `unidades.json` tenían unidades distintas (ids que no
 * existían en el padrón), así que "Editar grupo" nunca se veía con
 * unidades pre-marcadas en el navegador real (ese camino de la web no se
 * ejercía). Mejor regenerar los fixtures desde la API real
 * (`PROPTECH_ACTUALIZAR_FIXTURES=1`, `tests/integracion/test_contrato_web.py`)
 * cuando el contrato cambie; mientras tanto, esta guarda evita que un
 * fixture tocado a mano vuelva a desalinearse con el resto.
 */
import { describe, expect, it } from "vitest";
import grupos from "./fixtures/grupos.json";
import padron from "./fixtures/unidades.json";

describe("R3C-9 · coherencia entre grupos.json y unidades.json", () => {
  it("cada unidad de un grupo existe en el padrón del mismo edificio", () => {
    const idsDelPadron = new Set(padron.unidades.map((u) => u.id));
    const huerfanas = grupos.flatMap((g) =>
      g.unidades.map((m) => m.unidad_id).filter((id) => !idsDelPadron.has(id)),
    );
    expect(huerfanas).toEqual([]);
  });
});

type Informe = {
  suma: string;
  diferencia: string;
  // `string` y no la unión literal: viene de un `import ... from "*.json"`,
  // que TypeScript tipa como `string` ancho, nunca como literal.
  estado: string;
};

/** Réplica de `informar_coeficientes` (backend,
 * `compartido/coeficientes.py`): `diferencia = suma - 1`, en micro-unidades
 * (×1e6) para no comparar `float` — las dos puntas usan `Decimal`/texto de
 * 6 decimales. */
function estadoCoherente(informe: Informe): string[] {
  const problemas: string[] = [];
  const suma = Math.round(Number(informe.suma) * 1e6);
  const diferencia = Math.round(Number(informe.diferencia) * 1e6);
  const esperada = suma - 1_000_000;
  if (diferencia !== esperada) {
    problemas.push(
      `diferencia ${informe.diferencia} no es suma(${informe.suma}) - 1 = ${esperada / 1e6}`,
    );
  }
  const esperado =
    diferencia === 0 ? "ok" : Math.abs(diferencia) <= 100 ? "advertencia" : "fuera_de_tolerancia";
  if (informe.estado !== esperado) {
    problemas.push(`estado "${informe.estado}" no coincide con "${esperado}" para esa diferencia`);
  }
  return problemas;
}

describe("R3C-9 · el informe de cada fixture es coherente con su propia suma/diferencia", () => {
  it("unidades.json (padrón)", () => {
    expect(estadoCoherente(padron.informe)).toEqual([]);
  });

  it("grupos.json (sólo los grupos con informe, D9: 'generales')", () => {
    for (const grupo of grupos) {
      if (grupo.informe) {
        expect(estadoCoherente(grupo.informe)).toEqual([]);
      }
    }
  });
});
