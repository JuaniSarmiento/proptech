/**
 * R3C-6 (rompedor 3b): `dias_de_gracia`/`dia_de_vencimiento`/
 * `dia_segundo_vencimiento` son enteros simples (no plata, D6), pero
 * `Number.parseInt` trunca en silencio lo que no es un entero estricto:
 * `"1e1"` es válido en `<input type="number">` (vale 10, cumple `step=1`)
 * y `Number.parseInt("1e1")` da 1 — un día de gracia o de vencimiento mal
 * mandado sin que nadie lo note. Servidor HTTP real (no un mock de
 * `pedirApi`): se prueba el cuerpo que la acción manda de punta a punta.
 */
import { createServer, type IncomingMessage, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import { crearVersionDeConfiguracionAction } from "./acciones";

const UUID = "11111111-1111-1111-1111-111111111111";

let servidor: Server;
let ultimoCuerpo: string;

beforeAll(async () => {
  servidor = createServer((pedido: IncomingMessage, respuesta) => {
    let cuerpo = "";
    pedido.on("data", (trozo) => {
      cuerpo += trozo;
    });
    pedido.on("end", () => {
      ultimoCuerpo = cuerpo;
      respuesta
        .writeHead(201, { "content-type": "application/json" })
        .end(JSON.stringify({ id: "v1" }));
    });
  });
  await new Promise<void>((ok) => servidor.listen(0, "127.0.0.1", ok));
  const { port } = servidor.address() as AddressInfo;
  process.env.PROPTECH_URL_API_INTERNA = `http://127.0.0.1:${port}`;
});

afterAll(async () => {
  await new Promise<void>((ok) => servidor.close(() => ok()));
});

afterEach(() => {
  vi.clearAllMocks();
});

async function enviar(datos: Record<string, string>) {
  const formData = new FormData();
  for (const [clave, valor] of Object.entries(datos)) {
    formData.set(clave, valor);
  }
  await crearVersionDeConfiguracionAction(UUID, null, formData);
  return JSON.parse(ultimoCuerpo);
}

describe("R3C-6 · enteros estrictos, sin parseInt permisivo", () => {
  it('dias_de_gracia "1e1" (parseInt da 1) NO se manda como 1', async () => {
    const cuerpo = await enviar({
      dias_de_gracia: "1e1",
      dia_de_vencimiento: "10",
      modalidad_de_vencimiento: "unico",
    });
    expect(cuerpo.dias_de_gracia).not.toBe(1);
  });

  it('dia_de_vencimiento "3,5" (parseInt da 3) NO se manda como 3', async () => {
    const cuerpo = await enviar({
      dias_de_gracia: "5",
      dia_de_vencimiento: "3,5",
      modalidad_de_vencimiento: "unico",
    });
    expect(cuerpo.dia_de_vencimiento).not.toBe(3);
  });

  it('dias_de_gracia "5" (entero estricto) sí se manda como 5', async () => {
    const cuerpo = await enviar({
      dias_de_gracia: "5",
      dia_de_vencimiento: "10",
      modalidad_de_vencimiento: "unico",
    });
    expect(cuerpo.dias_de_gracia).toBe(5);
  });

  it('dia_segundo_vencimiento "2e1" (modalidad doble) NO se manda como 2', async () => {
    const cuerpo = await enviar({
      dias_de_gracia: "5",
      dia_de_vencimiento: "10",
      modalidad_de_vencimiento: "doble",
      dia_segundo_vencimiento: "2e1",
      recargo_segundo_vencimiento: "1.00",
    });
    expect(cuerpo.dia_segundo_vencimiento).not.toBe(2);
  });
});
