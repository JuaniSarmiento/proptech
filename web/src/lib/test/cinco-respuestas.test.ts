/**
 * D7 (tarea 5.3): toda pantalla que escribe cubre las cinco respuestas del
 * cliente (ok, inválido, conflicto, sin permiso, sin sesión) — a nivel de
 * ARCHIVO (`acciones.ts`), no de cada función exportada: varias acciones
 * comparten un `_mapear*` privado que ya cubre las cinco, y el escenario
 * de la spec dice "pantalla", no "acción".
 *
 * 2d: `sin_acceso` se resuelve en pedirApi con redirect a /sin-acceso;
 * nunca llega como resultado a acciones.ts. `sin_sesion` se devuelve sólo
 * al selector que pide alNoAutenticar=devolver.
 *
 * Las excepciones están documentadas acá, con el motivo — nunca en el
 * archivo que las tiene, para que una excepción nueva no se cuele sin
 * pasar por este test.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { expect, it } from "vitest";

const RAIZ = join(__dirname, "../../app");
const ESTADOS = ["ok", "invalido", "conflicto", "sin_permiso", "sin_sesion"] as const;

const _EXCEPCIONES: Record<string, { faltan: string[]; motivo: string }> = {
  "elegir-administracion/acciones.ts": {
    faltan: ["invalido", "conflicto", "sin_permiso", "sin_sesion"],
    motivo:
      "no usa el patrón ErroresSeparados/EstadoFormulario (devuelve boolean/redirect, no " +
      "erroresPorCampo): un solo mensaje genérico es todo lo que esta pantalla puede explicar.",
  },
  "invitacion/acciones.ts": {
    faltan: ["invalido", "conflicto", "sin_permiso", "sin_sesion"],
    motivo:
      "mismo patrón boolean/redirect que elegir-administracion; aceptar una invitación no " +
      "distingue motivos de rechazo por seguridad (no confirmar qué parte del enlace falló).",
  },
  "edificios/[id]/saldos-previos/acciones.ts": {
    faltan: ["invalido"],
    motivo:
      "confirmar_sin_saldos_previos no recibe cuerpo: no hay nada que la API pueda " +
      "rechazar con 422.",
  },
};

function _archivosDeAcciones(raiz: string): string[] {
  return readdirSync(raiz, { recursive: true, encoding: "utf8" })
    .filter((ruta) => ruta.endsWith("acciones.ts") && !ruta.endsWith(".test.ts"))
    .map((ruta) => join(raiz, ruta));
}

it("cada acciones.ts cubre los cinco estados, o tiene una excepción documentada", () => {
  const archivos = _archivosDeAcciones(RAIZ);
  expect(archivos.length).toBeGreaterThanOrEqual(9);
  const fallas: string[] = [];
  for (const ruta of archivos) {
    const clave = relative(RAIZ, ruta).replaceAll("\\", "/");
    const texto = readFileSync(ruta, "utf-8");
    const faltantes = ESTADOS.filter((estado) => !texto.includes(`"${estado}"`));
    const excepcion = _EXCEPCIONES[clave];
    const sinJustificar = faltantes.filter((f) => !(excepcion?.faltan.includes(f) ?? false));
    if (sinJustificar.length > 0) {
      fallas.push(`${clave}: faltan sin excepción [${sinJustificar.join(", ")}]`);
    }
  }
  expect(fallas).toEqual([]);
});

it("ninguna excepción documentada sobra (el archivo sigue faltando lo que dice)", () => {
  const archivos = new Map(
    _archivosDeAcciones(RAIZ).map((ruta) => [
      relative(RAIZ, ruta).replaceAll("\\", "/"),
      readFileSync(ruta, "utf-8"),
    ]),
  );
  for (const [clave, excepcion] of Object.entries(_EXCEPCIONES)) {
    const texto = archivos.get(clave);
    expect(texto, `${clave} ya no existe — borrar su excepción`).toBeDefined();
    for (const estado of excepcion.faltan) {
      expect(
        texto?.includes(`"${estado}"`),
        `${clave} ya cubre "${estado}" — achicar su excepción`,
      ).toBe(false);
    }
  }
});
