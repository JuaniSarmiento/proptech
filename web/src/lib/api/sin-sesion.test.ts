/**
 * R3C-8 (rompedor 3b): un 401 en cualquier escritura tiene que mostrar el
 * mensaje de sesión expirada (el mismo que ya usaba `crearEdificioAction`),
 * nunca el genérico "Probá de nuevo" — hasta el 2b la API de producción
 * siempre da 401, así que ese genérico invitaría a reintentar algo que
 * nunca va a andar. Un servidor HTTP real (no un mock de `pedirApi`): así
 * se prueba la acción de punta a punta, igual que la rompe el rompedor.
 */
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));

import {
  cambiarEstadoCategoriaAction,
  crearCategoriaAction,
} from "../../app/edificios/[id]/categorias/acciones";
import { crearVersionDeConfiguracionAction } from "../../app/edificios/[id]/configuracion/acciones";
import { crearGrupoAction } from "../../app/edificios/[id]/grupos/acciones";
import { confirmarSinSaldosPreviosAction } from "../../app/edificios/[id]/saldos-previos/acciones";
import { crearUnidadAction } from "../../app/edificios/[id]/unidades/acciones";

let servidor: Server;
const UUID = "11111111-1111-1111-1111-111111111111";

beforeAll(async () => {
  servidor = createServer((_pedido, respuesta) => {
    respuesta.writeHead(401).end();
  });
  await new Promise<void>((ok) => servidor.listen(0, "127.0.0.1", ok));
  const { port } = servidor.address() as AddressInfo;
  process.env.PROPTECH_URL_API_INTERNA = `http://127.0.0.1:${port}`;
});

afterAll(async () => {
  await new Promise<void>((ok) => servidor.close(() => ok()));
});

const MENSAJE_SESION = /sesión expiró/i;

describe("R3C-8 · un 401 en una escritura dice que la sesión expiró, en toda acción", () => {
  it("unidades · crearUnidadAction", async () => {
    const datos = new FormData();
    datos.set("identificador", "1A");
    const estado = await crearUnidadAction(UUID, null, datos);
    expect(estado?.erroresDesconocidos.join(" ")).toMatch(MENSAJE_SESION);
  });

  it("categorías · crearCategoriaAction (panel)", async () => {
    const datos = new FormData();
    datos.set("clave", "ascensor");
    datos.set("nombre", "Ascensor");
    const estado = await crearCategoriaAction(UUID, null, datos);
    expect(estado?.erroresDesconocidos.join(" ")).toMatch(MENSAJE_SESION);
  });

  it("categorías · cambiarEstadoCategoriaAction (lista)", async () => {
    const datos = new FormData();
    datos.set("categoria_id", UUID);
    datos.set("activa", "false");
    const estado = await cambiarEstadoCategoriaAction(UUID, null, datos);
    expect(estado?.erroresDesconocidos.join(" ")).toMatch(MENSAJE_SESION);
  });

  it("grupos · crearGrupoAction", async () => {
    const datos = new FormData();
    datos.set("clave", "ascensor");
    datos.set("nombre", "Ascensor");
    datos.set("metodo", "coeficiente");
    const estado = await crearGrupoAction(UUID, [], null, datos);
    expect(estado?.erroresDesconocidos.join(" ")).toMatch(MENSAJE_SESION);
  });

  it("configuración · crearVersionDeConfiguracionAction", async () => {
    const datos = new FormData();
    datos.set("dias_de_gracia", "5");
    datos.set("dia_de_vencimiento", "10");
    datos.set("modalidad_de_vencimiento", "unico");
    const estado = await crearVersionDeConfiguracionAction(UUID, null, datos);
    expect(estado?.erroresDesconocidos.join(" ")).toMatch(MENSAJE_SESION);
  });

  it("saldos previos · confirmarSinSaldosPreviosAction", async () => {
    const estado = await confirmarSinSaldosPreviosAction(UUID, null, new FormData());
    expect(estado?.erroresDesconocidos.join(" ")).toMatch(MENSAJE_SESION);
  });
});
