import { expect, it } from "vitest";
import { vocabularioDePisos } from "./pisos";

it("PB siempre presente, incluso con 0 pisos y 0 subsuelos", () => {
  expect(vocabularioDePisos(0, 0)).toEqual(["PB"]);
});

it("pisos 1..n y subsuelos SS1..SSn, en ese orden", () => {
  expect(vocabularioDePisos(4, 1)).toEqual(["PB", "1", "2", "3", "4", "SS1"]);
});
