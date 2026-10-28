/**
 * pulido-2 (3d), grupo 2: la API falsa de e2e conoce `PATCH /complejos/{id}`,
 * `PATCH /grupos/{id}` y las tres rutas de Georef que agregó el 3c. Hasta acá un
 * `PATCH` real a esas rutas caía en "método no declarado" (405). Archivo aparte de
 * `api-falsa.test.ts` a propósito: así un cambio de otro dev en ese archivo no choca.
 * Valida como la real (L-027): método, Content-Type, forma del cuerpo y tipos.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor } from "./api-falsa";
import { ESCENARIOS } from "./escenarios";
import { cabecerasDePrueba, PUBLICA } from "./sesion-local";

let servidor: Server;
let base: string;

beforeAll(async () => {
  servidor = crearServidor({ jwtKey: PUBLICA, origen: "http://127.0.0.1:3100" });
  await new Promise<void>((resolve) => servidor.listen(0, resolve));
  const direccion = servidor.address();
  base = `http://127.0.0.1:${typeof direccion === "object" && direccion ? direccion.port : 0}`;
});

afterAll(() => {
  servidor.close();
});

function pedir(url: string, opciones: RequestInit = {}) {
  return fetch(url, { ...opciones, headers: { ...cabecerasDePrueba(), ...opciones.headers } });
}

function patch(url: string, cuerpo: unknown) {
  return pedir(url, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

const EDIFICIO = "f760ca3b-7331-4927-96e5-54a3fbb1f3ae";
const GRUPO = "1c9d6f7e-0b0e-4f55-9f5a-2f3a6a1b7c10";

describe("PATCH /api/complejos/{id} (editar edificio y su ubicación)", () => {
  it("un cambio válido de nombre y ubicación responde 200 con el id", async () => {
    const respuesta = await patch(`${base}/api/complejos/${EDIFICIO}`, {
      nombre: "Edificio Nuevo",
      provincia_id: "50",
      departamento_id: "50007",
      localidad_id: "50007010",
      calle_y_numero: "San Martín 100",
      pisos: 6,
      subsuelos: 2,
    });
    expect(respuesta.status).toBe(200);
    expect(await respuesta.json()).toMatchObject({ id: EDIFICIO });
  });

  it("todos los campos son opcionales: un cuerpo vacío es válido", async () => {
    const respuesta = await patch(`${base}/api/complejos/${EDIFICIO}`, {});
    expect(respuesta.status).toBe(200);
  });

  it("un campo de tipo equivocado da 422 nombrando el campo, sin el valor", async () => {
    const respuesta = await patch(`${base}/api/complejos/${EDIFICIO}`, { pisos: "seis" });
    expect(respuesta.status).toBe(422);
    const cuerpo = await respuesta.json();
    expect(cuerpo.detail).toEqual([{ type: "int_type", loc: ["body", "pisos"] }]);
    expect(JSON.stringify(cuerpo)).not.toContain("seis");
  });

  it("un campo no declarado (la administración no se edita) da 422 extra_forbidden", async () => {
    const respuesta = await patch(`${base}/api/complejos/${EDIFICIO}`, {
      administracion_id: "otra",
    });
    expect(respuesta.status).toBe(422);
    expect((await respuesta.json()).detail).toEqual([
      { type: "extra_forbidden", loc: ["body", "administracion_id"] },
    ]);
  });

  it("sin Content-Type JSON da 422, como la ruta real", async () => {
    const respuesta = await pedir(`${base}/api/complejos/${EDIFICIO}`, {
      method: "PATCH",
      headers: { "content-type": "text/plain" },
      body: JSON.stringify({ nombre: "X" }),
    });
    expect(respuesta.status).toBe(422);
  });

  it("un escenario de permiso (sin_permiso_403) se respeta también al editar", async () => {
    const escenario = ESCENARIOS.find((e) => e.clave === "sin_permiso_403");
    const respuesta = await patch(`${base}/api/complejos/${escenario?.id}`, { nombre: "X" });
    expect(respuesta.status).toBe(403);
  });

  it("el edificio sigue sin aceptar POST ni PUT: 405", async () => {
    for (const metodo of ["POST", "PUT"]) {
      const respuesta = await pedir(`${base}/api/complejos/${EDIFICIO}`, {
        method: metodo,
        headers: { "content-type": "application/json" },
        body: "{}",
      });
      expect(respuesta.status).toBe(405);
    }
  });
});

describe("PATCH /api/grupos/{id} (editar y desactivar un grupo)", () => {
  it("desactivar un grupo responde 200 con el id", async () => {
    const respuesta = await patch(`${base}/api/grupos/${GRUPO}`, { activo: false });
    expect(respuesta.status).toBe(200);
    expect(await respuesta.json()).toMatchObject({ id: GRUPO });
  });

  it("renombrar y cambiar el método es válido", async () => {
    const respuesta = await patch(`${base}/api/grupos/${GRUPO}`, {
      nombre: "Torre B",
      metodo: "superficie",
    });
    expect(respuesta.status).toBe(200);
  });

  it("un tipo equivocado en activo da 422 bool_type nombrando el campo", async () => {
    const respuesta = await patch(`${base}/api/grupos/${GRUPO}`, { activo: "no" });
    expect(respuesta.status).toBe(422);
    expect((await respuesta.json()).detail).toEqual([
      { type: "bool_type", loc: ["body", "activo"] },
    ]);
  });

  it("un campo no declarado da 422 extra_forbidden", async () => {
    const respuesta = await patch(`${base}/api/grupos/${GRUPO}`, { unidades: [] });
    expect(respuesta.status).toBe(422);
    expect((await respuesta.json()).detail).toEqual([
      { type: "extra_forbidden", loc: ["body", "unidades"] },
    ]);
  });

  it("sin Content-Type JSON da 422", async () => {
    const respuesta = await pedir(`${base}/api/grupos/${GRUPO}`, {
      method: "PATCH",
      body: JSON.stringify({ activo: false }),
    });
    expect(respuesta.status).toBe(422);
  });

  it("la ruta de un grupo sólo declara PATCH: GET y POST dan 405", async () => {
    expect((await pedir(`${base}/api/grupos/${GRUPO}`)).status).toBe(405);
    const post = await pedir(`${base}/api/grupos/${GRUPO}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    expect(post.status).toBe(405);
  });

  it("sin sesión da 401 antes de mirar nada más", async () => {
    const respuesta = await fetch(`${base}/api/grupos/${GRUPO}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ activo: false }),
    });
    expect(respuesta.status).toBe(401);
  });
});

describe("Georef simulado: provincia → departamento → localidad", () => {
  async function listar(ruta: string) {
    const respuesta = await pedir(`${base}/api/georef/${ruta}`);
    return {
      estado: respuesta.status,
      cuerpo: respuesta.status === 200 ? await respuesta.json() : null,
    };
  }

  it("las provincias traen id y nombre, y incluyen Mendoza con el id del fixture", async () => {
    const { estado, cuerpo } = await listar("provincias");
    expect(estado).toBe(200);
    expect(cuerpo).toContainEqual({ id: "50", nombre: "Mendoza" });
    for (const provincia of cuerpo) {
      expect(Object.keys(provincia).sort()).toEqual(["id", "nombre"]);
    }
  });

  it("cada nivel filtra por el anterior: los departamentos son los de la provincia", async () => {
    const mendoza = await listar("provincias/50/departamentos");
    const buenosAires = await listar("provincias/06/departamentos");
    expect(mendoza.estado).toBe(200);
    expect(mendoza.cuerpo).toContainEqual({ id: "50007", nombre: "Capital" });
    expect(buenosAires.cuerpo).not.toContainEqual({ id: "50007", nombre: "Capital" });
    expect(buenosAires.cuerpo.length).toBeGreaterThan(0);
  });

  it("las localidades son las del departamento y traen la del fixture", async () => {
    const capital = await listar("departamentos/50007/localidades");
    const godoyCruz = await listar("departamentos/50028/localidades");
    expect(capital.cuerpo).toContainEqual({ id: "50007010", nombre: "Mendoza" });
    expect(godoyCruz.cuerpo).not.toContainEqual({ id: "50007010", nombre: "Mendoza" });
  });

  it("una provincia o un departamento inexistente da 404, como la API real", async () => {
    expect((await listar("provincias/99/departamentos")).estado).toBe(404);
    expect((await listar("departamentos/99999/localidades")).estado).toBe(404);
  });

  it("las rutas de Georef sólo declaran GET: un POST da 405", async () => {
    const respuesta = await pedir(`${base}/api/georef/provincias`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    expect(respuesta.status).toBe(405);
  });

  it("sin sesión da 401", async () => {
    const respuesta = await fetch(`${base}/api/georef/provincias`);
    expect(respuesta.status).toBe(401);
  });
});
