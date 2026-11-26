import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// H-040: la app instalable. Los archivos públicos son lo que el navegador baja sin sesión.
const PUBLICO = join(import.meta.dirname, "..", "..", "public");
const leer = (nombre: string) => readFileSync(join(PUBLICO, nombre), "utf8");

describe("manifest.webmanifest", () => {
  const manifest = JSON.parse(leer("manifest.webmanifest"));

  it("abre en el inicio del portal, a pantalla completa, en castellano", () => {
    expect(manifest.start_url).toBe("/inicio");
    expect(manifest.scope).toBe("/");
    expect(manifest.display).toBe("standalone");
    expect(manifest.lang).toMatch(/^es/);
    expect(manifest.short_name.length).toBeLessThanOrEqual(12);
  });

  it("trae íconos de 192, 512 y uno maskable, todos PNG que existen", () => {
    const tamanios = manifest.icons.map((i: { sizes: string }) => i.sizes);
    expect(tamanios).toContain("192x192");
    expect(tamanios).toContain("512x512");
    expect(manifest.icons.some((i: { purpose: string }) => i.purpose.includes("maskable"))).toBe(
      true,
    );
    for (const icono of manifest.icons as { src: string; type: string }[]) {
      expect(icono.type).toBe("image/png");
      const bytes = readFileSync(join(PUBLICO, icono.src.slice(1)));
      expect(bytes.subarray(1, 4).toString()).toBe("PNG");
    }
  });
});

describe("sw.js (D-170.6, N03)", () => {
  const sw = leer("sw.js");

  it("no guarda nada: no abre ninguna caché ni agrega ni responde pedidos", () => {
    const codigo = sw.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
    for (const prohibido of ["caches.open", "cache.put", "addAll", "respondWith", ".match("]) {
      expect(codigo, prohibido).not.toContain(prohibido);
    }
  });

  it("al activarse borra las cachés que hubiera dejado otra versión y toma el control", () => {
    expect(sw).toContain("caches.delete");
    expect(sw).toContain("clients.claim");
  });
});
