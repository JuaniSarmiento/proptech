/**
 * Cliente de la API del lado del servidor (D2, tarea 3.3): una unión
 * discriminada por resultado, nunca un texto que vino de la API hacia la
 * pantalla (L-007). Lee `PROPTECH_URL_API_INTERNA`: el servidor de Next
 * llama a la API directo, nunca el navegador (D11 del 3a, D1 de este
 * cambio) — sin esa variable, el resultado es `fallo` y ni se intenta
 * `fetch` (no hay a dónde llamar).
 */

import { cabecerasHaciaLaApi } from "../seguimiento";

export type ErrorDeCampo = { campo: string; motivo: string };

export type ResultadoApi<T> =
  | { estado: "ok"; datos: T }
  | { estado: "sin_sesion" }
  | { estado: "sin_permiso"; permiso: string }
  | { estado: "no_existe" }
  | { estado: "conflicto"; campo: string }
  | { estado: "invalido"; errores: ErrorDeCampo[] }
  | { estado: "fallo" };

const _TEXTO_DECIMAL_ASCII = /^-?[0-9]+\.[0-9]+$/;

/** Si `valor` es un texto decimal ASCII válido (el único formato que la
 * API usa para plata y coeficientes, L-009): nunca `Number`/`parseFloat`. */
export function esTextoDecimalAscii(valor: unknown): boolean {
  return typeof valor === "string" && _TEXTO_DECIMAL_ASCII.test(valor);
}

function leerPorCamino(objeto: unknown, camino: string): unknown {
  return camino.split(".").reduce<unknown>((actual, clave) => {
    if (actual === null || typeof actual !== "object") {
      return undefined;
    }
    return (actual as Record<string, unknown>)[clave];
  }, objeto);
}

type JsonLeido = { parseo: "ok"; valor: unknown } | { parseo: "fallo" };

/** Distingue "no se pudo leer como JSON" de "se leyó y da `null`" (p.ej.
 * `GET /configuracion` sin versión vigente): confundirlas convertía un
 * cuerpo roto en un `ok` con datos vacíos. */
async function leerJson(respuesta: Response): Promise<JsonLeido> {
  try {
    return { parseo: "ok", valor: await respuesta.json() };
  } catch {
    return { parseo: "fallo" };
  }
}

function comoRegistro(valor: unknown): Record<string, unknown> {
  return valor !== null && typeof valor === "object" ? (valor as Record<string, unknown>) : {};
}

function textoSeguro(valor: unknown, porDefecto: string): string {
  return typeof valor === "string" ? valor : porDefecto;
}

type OpcionesDePedido = {
  metodo?: "GET" | "POST" | "PATCH" | "PUT";
  cuerpo?: unknown;
  cabeceras?: Headers;
  /** Caminos (`"informe.suma"`) dentro de la respuesta 2xx que tienen que
   * ser texto decimal ASCII; si alguno no lo es, el resultado es `fallo`
   * en vez de `ok` con un valor que la pantalla no sabría mostrar (D2). */
  camposDePlata?: string[];
};

/** El único punto de entrada a la API desde el servidor de Next. Una
 * función por ruta de pantalla (3.4 en adelante) lo envuelve con su tipo y
 * sus `camposDePlata`; esta función nunca sabe de pantallas. */
export async function pedirApi<T>(
  ruta: string,
  opciones: OpcionesDePedido = {},
): Promise<ResultadoApi<T>> {
  const base = process.env.PROPTECH_URL_API_INTERNA;
  if (!base) {
    return { estado: "fallo" };
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(`${base}${ruta}`, {
      method: opciones.metodo ?? "GET",
      headers: cabecerasHaciaLaApi(opciones.cabeceras ?? new Headers()),
      body: opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo),
    });
  } catch {
    return { estado: "fallo" };
  }

  if (respuesta.status === 401) {
    return { estado: "sin_sesion" };
  }
  if (respuesta.status === 404) {
    return { estado: "no_existe" };
  }
  if (respuesta.status === 403) {
    const leido = await leerJson(respuesta);
    const cuerpo = leido.parseo === "ok" ? comoRegistro(leido.valor) : {};
    const detalle = comoRegistro(cuerpo.detail);
    const permiso = textoSeguro(detalle.permiso_faltante, "desconocido");
    return { estado: "sin_permiso", permiso };
  }
  if (respuesta.status === 409) {
    const leido = await leerJson(respuesta);
    const cuerpo = leido.parseo === "ok" ? comoRegistro(leido.valor) : {};
    return { estado: "conflicto", campo: textoSeguro(cuerpo.campo, "desconocido") };
  }
  if (respuesta.status === 422) {
    const leido = await leerJson(respuesta);
    const detalle = leido.parseo === "ok" ? comoRegistro(leido.valor).detail : undefined;
    if (!Array.isArray(detalle)) {
      return { estado: "fallo" };
    }
    const errores: ErrorDeCampo[] = detalle.map((item: unknown) => {
      const registro = comoRegistro(item);
      const loc = Array.isArray(registro.loc) ? registro.loc : [];
      // "sin el primer segmento body" (D2): el backend siempre lo manda primero.
      const campo =
        loc
          .slice(1)
          .map((segmento) => String(segmento))
          .join(".") || "desconocido";
      return { campo, motivo: textoSeguro(registro.type, "desconocido") };
    });
    return { estado: "invalido", errores };
  }
  if (respuesta.status >= 200 && respuesta.status < 300) {
    const leido = await leerJson(respuesta);
    if (leido.parseo === "fallo") {
      return { estado: "fallo" };
    }
    for (const camino of opciones.camposDePlata ?? []) {
      if (!esTextoDecimalAscii(leerPorCamino(leido.valor, camino))) {
        return { estado: "fallo" };
      }
    }
    return { estado: "ok", datos: leido.valor as T };
  }
  return { estado: "fallo" };
}
