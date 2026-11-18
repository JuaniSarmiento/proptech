import { beforeEach, describe, expect, it, vi } from "vitest";

const descargarComprobante = vi.fn();
vi.mock("../../../lib/api/pagos", () => ({
  descargarComprobante: (...args: unknown[]) => descargarComprobante(...args),
}));

import { GET } from "./route";

const TOKEN = `eyJhIjoicHJ1ZWJhIn0.${"ab".repeat(32)}`;

describe("GET /comprobantes/descarga", () => {
  beforeEach(() => descargarComprobante.mockReset());

  it("entrega el comprobante para verlo, con su tipo y sin guardarlo en ninguna caché", async () => {
    const bytes = new TextEncoder().encode("%PDF-1.4").buffer;
    descargarComprobante.mockResolvedValue({ estado: "ok", datos: bytes, tipo: "application/pdf" });
    const respuesta = await GET(new Request(`http://web/comprobantes/descarga?token=${TOKEN}`));
    expect(respuesta.status).toBe(200);
    expect(respuesta.headers.get("content-type")).toBe("application/pdf");
    expect(respuesta.headers.get("content-disposition")).toBe('inline; filename="comprobante.pdf"');
    expect(respuesta.headers.get("cache-control")).toBe("no-store");
    expect(respuesta.headers.get("x-content-type-options")).toBe("nosniff");
    expect(new Uint8Array(await respuesta.arrayBuffer())).toEqual(new Uint8Array(bytes));
    expect(descargarComprobante).toHaveBeenCalledWith(TOKEN);
  });

  it("una imagen sale con su extensión", async () => {
    descargarComprobante.mockResolvedValue({
      estado: "ok",
      datos: new ArrayBuffer(4),
      tipo: "image/png",
    });
    const respuesta = await GET(new Request(`http://web/comprobantes/descarga?token=${TOKEN}`));
    expect(respuesta.headers.get("content-disposition")).toBe('inline; filename="comprobante.png"');
  });

  it.each([
    [{ estado: "vencido" }, 410],
    [{ estado: "invalido" }, 403],
    [{ estado: "fallo" }, 502],
  ])("%j da %i, sin cuerpo", async (resultado, estado) => {
    descargarComprobante.mockResolvedValue(resultado);
    const respuesta = await GET(new Request(`http://web/comprobantes/descarga?token=${TOKEN}`));
    expect(respuesta.status).toBe(estado);
    expect(await respuesta.text()).toBe("");
  });

  it("sin token pide la descarga con el texto vacío", async () => {
    descargarComprobante.mockResolvedValue({ estado: "invalido" });
    const respuesta = await GET(new Request("http://web/comprobantes/descarga"));
    expect(descargarComprobante).toHaveBeenCalledWith("");
    expect(respuesta.status).toBe(403);
  });
});
