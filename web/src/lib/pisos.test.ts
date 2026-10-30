import { expect, it } from "vitest";
import { vocabularioDePisos } from "./pisos";

it("PB siempre presente, incluso con 0 pisos y 0 subsuelos", () => {
  expect(vocabularioDePisos(0, 0)).toEqual(["PB"]);
});

// pulido-2 (3d), escenarios "Edificio con dos subsuelos / un subsuelo / sin subsuelos":
// orden de altura, `SS<n>`..`SS1`, `PB`, `1`..`N`. Con un solo subsuelo no se
// distingue el orden de los subsuelos entre sí, por eso hay un caso con dos.
it("edificio con dos subsuelos: SS2, SS1, PB y después los pisos", () => {
  expect(vocabularioDePisos(4, 2)).toEqual(["SS2", "SS1", "PB", "1", "2", "3", "4"]);
});

it("edificio con un subsuelo: SS1, PB y después los pisos", () => {
  expect(vocabularioDePisos(4, 1)).toEqual(["SS1", "PB", "1", "2", "3", "4"]);
});

it("edificio sin subsuelos: PB y después los pisos", () => {
  expect(vocabularioDePisos(4, 0)).toEqual(["PB", "1", "2", "3", "4"]);
});
