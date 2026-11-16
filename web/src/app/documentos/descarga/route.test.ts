import { beforeEach, describe, expect, it, vi } from "vitest";

const descargarDocumento = vi.fn();
vi.mock("../../../lib/api/documentos", () => ({
  descargarDocumento: (...args: unknown[]) => descargarDocumento(...args),
}));

import { GET } from "./route";

const TOKEN = `eyJhIjoicHJ1ZWJhIn0.${"ab".repeat(32)}`;

describe("GET /documentos/descarga", () => {
  beforeEach(() => descargarDocumento.mockReset());

  it("entrega el PDF como archivo, sin guardarlo en ninguna caché", async () => {
    const bytes = new TextEncoder().encode("%PDF-1.7").buffer;
    descargarDocumento.mockResolvedValue({ estado: "ok", datos: bytes });
    const respuesta = await GET(new Request(`http://web/documentos/descarga?token=${TOKEN}`));
    expect(respuesta.status).toBe(200);
    expect(respuesta.headers.get("content-type")).toBe("application/pdf");
    expect(respuesta.headers.get("content-disposition")).toBe('attachment; filename="expensa.pdf"');
    expect(respuesta.headers.get("cache-control")).toBe("no-store");
    expect(new Uint8Array(await respuesta.arrayBuffer())).toEqual(new Uint8Array(bytes));
    expect(descargarDocumento).toHaveBeenCalledWith(TOKEN);
  });

  it.each([
    [{ estado: "vencido" }, 410],
    [{ estado: "invalido" }, 403],
    [{ estado: "fallo" }, 502],
  ])("%j da %i, sin cuerpo", async (resultado, estado) => {
    descargarDocumento.mockResolvedValue(resultado);
    const respuesta = await GET(new Request(`http://web/documentos/descarga?token=${TOKEN}`));
    expect(respuesta.status).toBe(estado);
    expect(await respuesta.text()).toBe("");
  });

  it("sin token pide la descarga con el texto vacío (la API da 403)", async () => {
    descargarDocumento.mockResolvedValue({ estado: "invalido" });
    const respuesta = await GET(new Request("http://web/documentos/descarga"));
    expect(descargarDocumento).toHaveBeenCalledWith("");
    expect(respuesta.status).toBe(403);
  });
});
