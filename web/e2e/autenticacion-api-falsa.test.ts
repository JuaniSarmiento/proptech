import type { Server } from "node:http";
import { afterAll, beforeAll, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { cabecerasDePrueba, crearToken, PUBLICA } from "./sesion-local";

let servidor: Server;
let base: string;
beforeAll(async () => {
  servidor = crearServidor({ jwtKey: PUBLICA, origen: "http://127.0.0.1:3100" });
  await new Promise<void>((ok) => servidor.listen(0, "127.0.0.1", ok));
  const direccion = servidor.address();
  if (!direccion || typeof direccion === "string") throw new Error("sin puerto");
  base = `http://127.0.0.1:${direccion.port}`;
});
afterAll(() => servidor.close());

it.each<Record<string, string>>([
  {},
  { cookie: `__session=${crearToken()}` },
  { ...cabecerasDePrueba(), authorization: "Bearer inventado" },
  { ...cabecerasDePrueba(), "x-proptech-administracion": "ajena" },
  { ...cabecerasDePrueba(), authorization: `Bearer ${crearToken({ exp: 1 })}` },
  { ...cabecerasDePrueba(), authorization: `Bearer ${crearToken({ iss: "https://otro" })}` },
  { ...cabecerasDePrueba(), authorization: `Bearer ${crearToken({ azp: "https://otro" })}` },
])("rechaza credenciales inválidas como la API real (%#)", async (headers) => {
  expect((await fetch(`${base}/api/complejos`, { headers })).status).toBe(401);
});
it("acepta un token local firmado y el selector propio", async () => {
  expect((await fetch(`${base}/api/complejos`, { headers: cabecerasDePrueba() })).status).toBe(200);
});
it("GET /api/sesion funciona sin selector; POST no sustituye GET", async () => {
  const headers = { authorization: `Bearer ${crearToken()}` };
  const respuesta = await fetch(`${base}/api/sesion`, { headers });
  expect(respuesta.status).toBe(200);
  expect(await respuesta.json()).toEqual({
    persona: { nombre: "Persona de prueba" },
    administraciones: [
      { id: "10000000-0000-0000-0000-000000000001", nombre: "Administración de prueba" },
    ],
  });
  expect((await fetch(`${base}/api/sesion`, { method: "POST", headers })).status).toBe(405);
});

it.each([
  { body: {}, status: 422 },
  { body: { token: 2 }, status: 422 },
  { body: { token: "sobre-valido", extra: true }, status: 422 },
  { body: { token: "sobre-vencido" }, status: 404 },
  { body: { token: "email-distinto" }, status: 404 },
  { body: { token: "sobre-valido" }, status: 200 },
])("aceptar valida el contrato firmado: %j", async ({ body, status }) => {
  const res = await fetch(`${base}/api/invitaciones/aceptar`, {
    method: "POST",
    headers: {
      ...cabecerasDePrueba(),
      "content-type": "application/json",
      "x-proptech-administracion": "ajena-ignorada-en-aceptar",
    },
    body: JSON.stringify(body),
  });
  expect(res.status).toBe(status);
  if (status === 404) expect(await res.json()).toEqual({ detail: "no encontrado" });
});
it("aceptar autentica antes del JSON roto y sólo permite POST", async () => {
  expect(
    (await fetch(`${base}/api/invitaciones/aceptar`, { method: "POST", body: "{" })).status,
  ).toBe(401);
  expect(
    (await fetch(`${base}/api/invitaciones/aceptar`, { headers: cabecerasDePrueba() })).status,
  ).toBe(405);
});
