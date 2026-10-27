/**
 * Cliente de la API del lado del servidor (D2, tarea 3.3): una unión
 * discriminada por resultado, nunca un texto que vino de la API hacia la
 * pantalla (L-007). Lee `PROPTECH_URL_API_INTERNA`: el servidor de Next
 * llama a la API directo, nunca el navegador (D11 del 3a, D1 de este
 * cambio) — sin esa variable, el resultado es `fallo` y ni se intenta
 * `fetch` (no hay a dónde llamar).
 */

import { cabecerasHaciaLaApi } from "../seguimiento";
import { irAlIngreso, sesionActual } from "../sesion";

export type ErrorDeCampo = { campo: string; motivo: string; identificadores?: string[] };

export type ResultadoApi<T> =
  | { estado: "ok"; datos: T }
  | { estado: "sin_sesion" }
  | { estado: "sin_permiso"; permiso: string }
  | { estado: "no_existe" }
  | { estado: "conflicto"; campo: string }
  | { estado: "invalido"; errores: ErrorDeCampo[] }
  | { estado: "fallo" };

const _TEXTO_DECIMAL_ASCII = /^-?[0-9]+\.[0-9]+$/;

const _UUID = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

/** R3C-2 (rompedor 3b): todo id que compone una ruta de la API (de un
 * campo oculto del formulario, de `params.id` de la URL, o ligado con
 * `.bind`) tiene que ser un UUID — nunca se interpola crudo. Sin esto, un
 * `unidad_id` como `"../complejos/<otro>/categorias?x="` normaliza
 * (`new URL`) a una ruta y un recurso distintos de los que la pantalla
 * pensó, con el cuerpo de ESA acción. Un id que no es UUID da "no existe"
 * (D2, misma pantalla que un 404 real), nunca un pedido con él adentro. */
export function esIdValido(id: string): boolean {
  return _UUID.test(id);
}

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
  metodo?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
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

  const sesion = await sesionActual();
  if (!sesion) return irAlIngreso();
  const cabeceras = cabecerasHaciaLaApi(opciones.cabeceras ?? new Headers());
  cabeceras.set("Authorization", `Bearer ${sesion.token}`);
  if (sesion.administracionId) {
    cabeceras.set("X-Proptech-Administracion", sesion.administracionId);
  }
  if (opciones.cuerpo !== undefined) {
    // R3C-1 (rompedor 3b): sin esto, `fetch` manda un `body` string sin
    // Content-Type declarado y pone `text/plain;charset=UTF-8` (spec
    // Fetch); FastAPI sólo parsea JSON si el content-type es
    // `application/json` (o `+json`), así que daba 422 en TODA escritura.
    cabeceras.set("Content-Type", "application/json");
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(`${base}${ruta}`, {
      method: opciones.metodo ?? "GET",
      cache: "no-store",
      headers: cabeceras,
      body: opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo),
    });
  } catch {
    return { estado: "fallo" };
  }

  if (respuesta.status === 401) {
    return irAlIngreso(sesion.regreso);
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
      // `identificadores`: lista cerrada de datos propios del edificio (L-007
      // no la prohíbe, sólo prohíbe `msg`/texto libre); cada elemento se
      // valida como texto antes de confiar en el array.
      const identificadores = Array.isArray(registro.identificadores)
        ? registro.identificadores.filter((x): x is string => typeof x === "string")
        : undefined;
      return {
        campo,
        motivo: textoSeguro(registro.type, "desconocido"),
        ...(identificadores ? { identificadores } : {}),
      };
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
