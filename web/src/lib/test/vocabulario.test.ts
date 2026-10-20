import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { expect, it } from "vitest";

// La lista completa usa fragmentos para que este test se examine a sí mismo.
const PALABRAS_ANTERIORES = ["titu" + "lar", "cola" + "borador"];
const RAIZ = join(__dirname, "../..");

it("todo el texto de src usa los perfiles vigentes, salvo nombres de tokens CSS", () => {
  const archivos = readdirSync(RAIZ, { recursive: true, encoding: "utf8" })
    .map((ruta) => join(RAIZ, ruta))
    .filter((ruta) => statSync(ruta).isFile());
  expect(archivos).toContain(join(RAIZ, "componentes/Estados.tsx"));
  expect(archivos).toContain(join(RAIZ, "app/edificios/acciones.ts"));
  const apariciones = archivos.flatMap((ruta) =>
    readFileSync(ruta, "utf-8")
      .split("\n")
      .flatMap((linea, indice) => {
        const texto = linea.replaceAll(/--[a-z][a-z0-9-]*/gi, "").toLowerCase();
        return PALABRAS_ANTERIORES.some((palabra) => texto.includes(palabra))
          ? [`${relative(RAIZ, ruta)}:${indice + 1}:${linea.trim()}`]
          : [];
      }),
  );
  expect(apariciones).toEqual([]);
});
