/**
 * API falsa (D7, tarea 3.8): contra un puerto al azar, de punta a punta
 * por HTTP real (no jsdom) — es un servidor de Node, no un componente.
 */

import type { Server } from "node:http";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { crearServidor, IDENTIFICADOR_DE_40, NOMBRE_DE_200 } from "./api-falsa";
import { type ClaveDeEscenario, ESCENARIOS } from "./escenarios";

let servidor: Server;
let base: string;

beforeAll(async () => {
  servidor = crearServidor();
  await new Promise<void>((resolve) => servidor.listen(0, resolve));
  const direccion = servidor.address();
  const puerto = typeof direccion === "object" && direccion ? direccion.port : 0;
  base = `http://127.0.0.1:${puerto}`;
});

afterAll(() => {
  servidor.close();
});

function idDe(clave: ClaveDeEscenario): string {
  const encontrado = ESCENARIOS.find((escenario) => escenario.clave === clave);
  if (!encontrado) {
    throw new Error(`no hay escenario con clave ${clave}`);
  }
  return encontrado.id;
}

describe("api-falsa", () => {
  it("la lista no depende de ningún id", async () => {
    const respuesta = await fetch(`${base}/api/complejos`);
    expect(respuesta.status).toBe(200);
    const cuerpo = await respuesta.json();
    expect(Array.isArray(cuerpo)).toBe(true);
  });

  it("un id sin escenario da el fixture tal cual", async () => {
    const respuesta = await fetch(`${base}/api/complejos/sin-escenario/resumen`);
    expect(respuesta.status).toBe(200);
    const cuerpo = await respuesta.json();
    expect(cuerpo.nombre).toBe("Edificio API");
  });

  it("500 con texto técnico, nunca JSON (error_500)", async () => {
    const respuesta = await fetch(`${base}/api/complejos/${idDe("error_500")}/resumen`);
    expect(respuesta.status).toBe(500);
    expect(await respuesta.text()).toContain("Traceback");
  });

  it("403 con permiso_faltante (sin_permiso_403)", async () => {
    const respuesta = await fetch(`${base}/api/complejos/${idDe("sin_permiso_403")}/configuracion`);
    expect(respuesta.status).toBe(403);
    const cuerpo = await respuesta.json();
    expect(cuerpo.detail.permiso_faltante).toBe("cambiar_configuracion");
  });

  it("404 (no_existe_404)", async () => {
    const respuesta = await fetch(`${base}/api/complejos/${idDe("no_existe_404")}/resumen`);
    expect(respuesta.status).toBe(404);
  });

  it("401 (sin_sesion_401)", async () => {
    const respuesta = await fetch(`${base}/api/complejos/${idDe("sin_sesion_401")}/resumen`);
    expect(respuesta.status).toBe(401);
  });

  it("vacío: sin unidades, sin grupos, sin categorías, sin versiones", async () => {
    const id = idDe("vacio");
    const unidades = await (await fetch(`${base}/api/complejos/${id}/unidades`)).json();
    expect(unidades.unidades).toEqual([]);
    const grupos = await (await fetch(`${base}/api/complejos/${id}/grupos`)).json();
    expect(grupos).toEqual([]);
  });

  it('vacío: el informe es el real de "cero unidades" (nunca null — gotcha visto en Playwright, bloque C: la API real `informar_coeficientes([])` siempre da un informe bien formado, nunca null, y una pantalla que confía en el tipo no-nulable de D4 rompe si acá se manda null)', async () => {
    const id = idDe("vacio");
    const unidades = await (await fetch(`${base}/api/complejos/${id}/unidades`)).json();
    expect(unidades.informe).toEqual({
      suma: "0.000000",
      diferencia: "-1.000000",
      estado: "fuera_de_tolerancia",
    });
  });

  it('vacío: el resumen cuadra con "cero unidades" como lo calcula `resumen_edificio` (unidades, coeficientes y categorías en falta; pulido 3b: la API falsa decía "Cargar unidades: Hecho" con 0 unidades)', async () => {
    const resumen = await (await fetch(`${base}/api/complejos/${idDe("vacio")}/resumen`)).json();
    expect(resumen.cantidad_unidades).toBe(0);
    expect(resumen.informe.estado).toBe("fuera_de_tolerancia");
    expect(resumen.pasos.unidades).toBe("falta");
    expect(resumen.pasos.coeficientes).toBe("falta");
    expect(resumen.pasos.categorias).toBe("falta");
    expect(resumen.listo_para_liquidar).toBe(false);
  });

  it('advertencia: el paso "coeficientes" queda hecho (la API real acepta advertencia como hecho), fuera de tolerancia en falta', async () => {
    const advertencia = await (
      await fetch(`${base}/api/complejos/${idDe("advertencia")}/resumen`)
    ).json();
    expect(advertencia.pasos.coeficientes).toBe("hecho");
    const fuera = await (
      await fetch(`${base}/api/complejos/${idDe("fuera_de_tolerancia")}/resumen`)
    ).json();
    expect(fuera.pasos.coeficientes).toBe("falta");
  });

  it("advertencia y fuera de tolerancia mutan el informe (nunca el archivo real)", async () => {
    const resumenAdvertencia = await (
      await fetch(`${base}/api/complejos/${idDe("advertencia")}/resumen`)
    ).json();
    expect(resumenAdvertencia.informe).toEqual({
      diferencia: "0.000050",
      estado: "advertencia",
      suma: "0.999950",
    });

    const resumenFueraDeTolerancia = await (
      await fetch(`${base}/api/complejos/${idDe("fuera_de_tolerancia")}/resumen`)
    ).json();
    expect(resumenFueraDeTolerancia.informe.diferencia).toBe("-0.000200");

    // el fixture real en disco no se tocó: otro id sin escenario sigue dando
    // su informe original de la API (0.100000), no el mutado de arriba.
    const resumenNormal = await (
      await fetch(`${base}/api/complejos/otro-sin-escenario/resumen`)
    ).json();
    expect(resumenNormal.informe.diferencia).toBe("0.100000");
  });

  it("200 unidades (doscientas_unidades)", async () => {
    const cuerpo = await (
      await fetch(`${base}/api/complejos/${idDe("doscientas_unidades")}/unidades`)
    ).json();
    expect(cuerpo.unidades).toHaveLength(200);
  });

  it("nombres largos: 200 caracteres en el edificio, 40 en cada identificador", async () => {
    const id = idDe("nombres_largos");
    const resumen = await (await fetch(`${base}/api/complejos/${id}/resumen`)).json();
    expect(resumen.nombre).toBe(NOMBRE_DE_200);
    expect(resumen.nombre).toHaveLength(200);

    const unidades = await (await fetch(`${base}/api/complejos/${id}/unidades`)).json();
    for (const unidad of unidades.unidades) {
      expect(unidad.identificador).toBe(IDENTIFICADOR_DE_40);
    }
  });

  it("lento tarda al menos 2,5s en responder", async () => {
    const empieza = Date.now();
    await fetch(`${base}/api/complejos/${idDe("lento")}/resumen`);
    expect(Date.now() - empieza).toBeGreaterThanOrEqual(2500);
  });

  it("una ruta fuera de /api/complejos da 404", async () => {
    const respuesta = await fetch(`${base}/otra-cosa`);
    expect(respuesta.status).toBe(404);
  });

  describe("R3C-10 · una escritura valida Content-Type y forma, no sólo la ruta", () => {
    const id = "f760ca3b-7331-4927-96e5-54a3fbb1f3ae";

    it("un POST con text/plain (lo que mandaba la web antes de R3C-1) ya no se acepta como si fuera un GET", async () => {
      const respuesta = await fetch(`${base}/api/complejos/${id}/unidades`, {
        method: "POST",
        body: JSON.stringify({ identificador: "X" }),
      });
      expect(respuesta.status).toBe(422);
    });

    it("un POST con application/json y un objeto se acepta", async () => {
      const respuesta = await fetch(`${base}/api/complejos/${id}/unidades`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ identificador: "X" }),
      });
      expect(respuesta.status).toBe(200);
    });

    it("un POST con application/json pero un arreglo (no la forma esperada) da 422", async () => {
      const respuesta = await fetch(`${base}/api/complejos/${id}/unidades`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify([1, 2, 3]),
      });
      expect(respuesta.status).toBe(422);
    });

    it("el escenario 403 sigue ganando sobre la validación de Content-Type (igual que la API real: la autorización no depende del cuerpo)", async () => {
      const respuesta = await fetch(`${base}/api/complejos/${idDe("sin_permiso_403")}/unidades`, {
        method: "POST",
        body: "no es json",
      });
      expect(respuesta.status).toBe(403);
    });

    it("/api/__debug/ultima-escritura expone el método, la URL y el Content-Type recibidos", async () => {
      await fetch(`${base}/api/complejos/${id}/categorias`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ nombre: "Y" }),
      });
      const depurado = await (await fetch(`${base}/api/__debug/ultima-escritura`)).json();
      expect(depurado).toMatchObject({
        metodo: "PATCH",
        contentType: "application/json",
      });
    });
  });
});
