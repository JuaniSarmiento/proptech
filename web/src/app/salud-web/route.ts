/**
 * `GET /salud-web`: ruta técnica, sin interfaz, que informa el estado de la
 * web y el que le reporta la API (D8).
 *
 * Contrato (spec "Contrato de respuesta de /salud-web"): responde siempre
 * `Content-Type: application/json` con exactamente dos campos, `web` y
 * `api`; 200 sólo cuando `api` es `"ok"`, 503 en cualquier otro caso. `api`
 * se deriva sólo del código de estado de la respuesta de la API (nunca de
 * su cuerpo, L-007): 200 es `"ok"`, cualquier otro código es `"degradado"`;
 * sin conexión o sin respuesta en 2 s es `"sin_conexion"`; sin
 * `PROPTECH_URL_API_INTERNA` es `"sin_configurar"` sin llamar a `fetch`.
 *
 * El límite de 2 s se implementa con `AbortController` y `setTimeout`
 * propios (no `AbortSignal.timeout`, que no respeta los temporizadores
 * falsos de los tests: la tarea 6.3 afirma esta cota con ellos).
 */

import { cabecerasHaciaLaApi } from "../../lib/seguimiento";

export const dynamic = "force-dynamic";

const LIMITE_MS = 2000;

type EstadoApi = "ok" | "degradado" | "sin_conexion" | "sin_configurar";

export async function GET(request: Request): Promise<Response> {
  const urlApiInterna = process.env.PROPTECH_URL_API_INTERNA;
  let estadoApi: EstadoApi;
  let requestId: string;

  if (!urlApiInterna) {
    // Sin dirección de la API: no se intenta ninguna conexión. El
    // request_id de la respuesta sigue existiendo (viaja aunque la API no
    // esté configurada).
    requestId = cabecerasHaciaLaApi(request.headers).get("X-Request-ID") ?? "";
    estadoApi = "sin_configurar";
  } else {
    const cabecerasApi = cabecerasHaciaLaApi(request.headers);
    requestId = cabecerasApi.get("X-Request-ID") ?? "";
    const controlador = new AbortController();
    const temporizador = setTimeout(() => controlador.abort(), LIMITE_MS);
    try {
      const respuestaApi = await fetch(`${urlApiInterna}/api/salud`, {
        headers: cabecerasApi,
        signal: controlador.signal,
      });
      estadoApi = respuestaApi.status === 200 ? "ok" : "degradado";
    } catch {
      // Nunca el texto del error ni la dirección interna (L-007): ante
      // cualquier falla (timeout, conexión rechazada) el estado es fijo.
      estadoApi = "sin_conexion";
    } finally {
      clearTimeout(temporizador);
    }
  }

  const codigo = estadoApi === "ok" ? 200 : 503;
  return new Response(JSON.stringify({ web: "ok", api: estadoApi }), {
    status: codigo,
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": requestId,
    },
  });
}
