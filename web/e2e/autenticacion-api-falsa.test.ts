import type { Server } from "node:http";
import { afterAll, beforeAll, expect, it } from "vitest";
import { crearServidor, EDIFICIO_API } from "./api-falsa";
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

it("GET /api/personal: super admin ve la lista; sin permiso da 403; sólo GET", async () => {
  const lista = await fetch(`${base}/api/personal`, { headers: cabecerasDePrueba() });
  expect(lista.status).toBe(200);
  const datos = await lista.json();
  expect(datos).toHaveLength(3);
  expect(datos[1].invitacion).toEqual({
    invitacion_id: "00000000-0000-0000-0000-000000000302",
    estado: "fallida",
  });

  const sinPermiso = await fetch(`${base}/api/personal`, {
    headers: { authorization: `Bearer ${crearToken({ sub: "user_sin_permiso" })}` },
  });
  expect(sinPermiso.status).toBe(403);
  expect(await sinPermiso.json()).toEqual({
    detail: { permiso_faltante: "invitar_usuarios_y_asignar_edificios" },
  });

  expect(
    (await fetch(`${base}/api/personal`, { method: "POST", headers: cabecerasDePrueba() })).status,
  ).toBe(405);
});

it.each([
  {
    body: { nombre: "A", email: "sin-arroba", rol: "contador", alcance: "principal" },
    status: 422,
  },
  {
    body: { nombre: "A", email: "a@test.com", rol: "auxiliar", alcance: "principal" },
    status: 422,
  },
  {
    body: {
      nombre: "A",
      email: "a@test.com",
      rol: "contador",
      alcance: "edificio",
      complejo_id: EDIFICIO_API,
    },
    status: 201,
  },
  {
    body: { nombre: "A", email: "ya-invitado@test.com", rol: "contador", alcance: "principal" },
    status: 409,
  },
])(
  "POST /api/personal/invitaciones valida el contrato firmado (D5): %j",
  async ({ body, status }) => {
    const res = await fetch(`${base}/api/personal/invitaciones`, {
      method: "POST",
      headers: { ...cabecerasDePrueba(), "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    expect(res.status).toBe(status);
  },
);
it("invitar exige Content-Type y POST", async () => {
  expect(
    (
      await fetch(`${base}/api/personal/invitaciones`, {
        method: "POST",
        headers: cabecerasDePrueba(),
        body: "{}",
      })
    ).status,
  ).toBe(422);
  expect(
    (await fetch(`${base}/api/personal/invitaciones`, { headers: cabecerasDePrueba() })).status,
  ).toBe(405);
});

it("revocar y quitar: 200 con un id real, 404 con el sentinel, sólo su método", async () => {
  const revocar = await fetch(
    `${base}/api/invitaciones/00000000-0000-0000-0000-000000000302/revocar`,
    { method: "POST", headers: cabecerasDePrueba() },
  );
  expect(revocar.status).toBe(200);
  expect(await revocar.json()).toEqual({ revocada: true });
  expect(
    (
      await fetch(`${base}/api/invitaciones/00000000-0000-0000-0000-0000000000ee/revocar`, {
        method: "POST",
        headers: cabecerasDePrueba(),
      })
    ).status,
  ).toBe(404);
  expect(
    (
      await fetch(`${base}/api/invitaciones/00000000-0000-0000-0000-000000000302/revocar`, {
        headers: cabecerasDePrueba(),
      })
    ).status,
  ).toBe(405);

  const quitar = await fetch(`${base}/api/asignaciones/00000000-0000-0000-0000-000000000202`, {
    method: "DELETE",
    headers: cabecerasDePrueba(),
  });
  expect(quitar.status).toBe(200);
  expect(await quitar.json()).toEqual({ quitada: true });
  expect(
    (
      await fetch(`${base}/api/asignaciones/00000000-0000-0000-0000-0000000000ee`, {
        method: "DELETE",
        headers: cabecerasDePrueba(),
      })
    ).status,
  ).toBe(404);
});
