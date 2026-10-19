import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { archivosConNumeroSobrePlata } from "./sinNumeroSobrePlata";

const _RAIZ_WEB_SRC = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

describe("archivosConNumeroSobrePlata", () => {
  it("detecta un parseFloat puesto a propósito, sobre una copia (L-013, L-019)", () => {
    const copia = mkdtempSync(join(tmpdir(), "sweep-formato-"));
    try {
      writeFileSync(
        join(copia, "pantalla-ofensora.tsx"),
        'import { coeficiente } from "../lib/formato";\n' + 'export const feo = parseFloat("1");\n',
      );
      expect(archivosConNumeroSobrePlata(copia)).toHaveLength(1);
    } finally {
      rmSync(copia, { recursive: true, force: true });
    }
  });

  it("no marca un archivo que no importa formato ni el cliente de la API", () => {
    const copia = mkdtempSync(join(tmpdir(), "sweep-formato-"));
    try {
      writeFileSync(join(copia, "sin-relacion.ts"), 'export const feo = Number("1");\n');
      expect(archivosConNumeroSobrePlata(copia)).toEqual([]);
    } finally {
      rmSync(copia, { recursive: true, force: true });
    }
  });

  it("el árbol real de web/src está limpio", () => {
    expect(archivosConNumeroSobrePlata(_RAIZ_WEB_SRC)).toEqual([]);
  });
});
