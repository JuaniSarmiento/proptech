/**
 * API falsa para el navegador real (D7, tarea 3.8): un servidor HTTP de
 * Node SIN DEPENDENCIAS que sirve los fixtures de 3.4
 * (`web/src/lib/api/fixtures/*.json`, generados desde la API real) y los
 * muta por escenario según el id del edificio (`escenarios.ts`).
 *
 * `crearServidor()` no escucha por sí sola (así `api-falsa.test.ts` la
 * prueba sobre un puerto al azar, sin pisar el puerto real); quien corre
 * este archivo como script (`test-web-navegador.sh`) es quien la levanta.
 */

import { readFileSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { escenarioPorId } from "./escenarios";
import { ESCRITURAS_UNIDADES } from "./escenarios-escritura";

const _AQUI = dirname(fileURLToPath(import.meta.url));
const _DIR_FIXTURES = join(_AQUI, "../src/lib/api/fixtures");

// biome-ignore lint/suspicious/noExplicitAny: los fixtures son JSON de forma variable (lista, objeto).
type Json = any;

function leerFixture(nombre: string): Json {
  // Una lectura fresca por pedido (no cachear en memoria): mutar el
  // resultado más abajo nunca puede mutar accidentalmente lo que lee el
  // próximo pedido.
  return JSON.parse(readFileSync(join(_DIR_FIXTURES, `${nombre}.json`), "utf-8"));
}

const _RUTAS: Record<string, string> = {
  "": "edificio",
  resumen: "resumen",
  unidades: "unidades",
  grupos: "grupos",
  categorias: "categorias",
  configuracion: "vigente",
  "configuracion/versiones": "versiones",
};

// `slice(0, 200)` sobre una base que repite de más: 200 caracteres EXACTOS,
// sin depender de que la cuenta de `repeat` cierre justo.
export const NOMBRE_DE_200 = "Consorcio Edificio Modelo ".repeat(8).slice(0, 200);
export const IDENTIFICADOR_DE_40 = "UNIDAD-".padEnd(40, "0");

function informeConEstado(estado: string, diferencia: string, suma: string) {
  return { diferencia, estado, suma };
}

function unidadSintetica(indice: number) {
  return {
    coeficiente: "0.005000",
    complejo_id: "00000000-0000-0000-0000-00000000aaaa",
    id: `00000000-0000-0000-0000-${String(indice).padStart(12, "0")}`,
    identificador: `U${indice}`,
    piso: String(Math.floor(indice / 4) + 1),
    superficie_m2: "40.00",
    tipo: "departamento",
  };
}

/** Aplica la mutación del escenario sobre el fixture YA LEÍDO (nunca sobre
 * el archivo): cada pedido parte de una copia nueva (`leerFixture`). */
function mutarParaElEscenario(claveEscenario: string, nombreFixture: string, datos: Json): Json {
  if (claveEscenario === "vacio") {
    // El informe de "cero unidades" NUNCA es `null`: la API real
    // (`informar_coeficientes([])`) siempre da un informe bien formado
    // (suma 0, diferencia -1, fuera de tolerancia) — `Padron.informe` no es
    // nulable (D4). Gotcha real, visto romper una pantalla en Playwright
    // (bloque C, 4.3): `null` acá hacía que `EstadoDeCoeficientes` leyera
    // `.estado` de `null` durante el render.
    if (nombreFixture === "unidades")
      return {
        informe: informeConEstado("fuera_de_tolerancia", "-1.000000", "0.000000"),
        unidades: [],
      };
    if (nombreFixture === "grupos") return [];
    if (nombreFixture === "categorias") return [];
    if (nombreFixture === "versiones") return [];
    if (nombreFixture === "resumen") {
      // Los pasos tienen que cuadrar con lo que daría `resumen_edificio`
      // (backend, lectura.py) para cero unidades y cero categorías: con sólo
      // `cantidad_unidades: 0`, el fixture seguía diciendo "Cargar unidades:
      // Hecho" (visto en el pulido visual del 3b, 19/10/2026).
      return {
        ...datos,
        cantidad_unidades: 0,
        informe: informeConEstado("fuera_de_tolerancia", "-1.000000", "0.000000"),
        pasos: { ...datos.pasos, unidades: "falta", coeficientes: "falta", categorias: "falta" },
        listo_para_liquidar: false,
      };
    }
    return datos;
  }

  if (claveEscenario === "advertencia" || claveEscenario === "fuera_de_tolerancia") {
    const informe =
      claveEscenario === "advertencia"
        ? informeConEstado("advertencia", "0.000050", "0.999950")
        : informeConEstado("fuera_de_tolerancia", "-0.000200", "0.999800");
    if (nombreFixture === "resumen") {
      // `resumen_edificio` da "coeficientes: hecho" con ok o advertencia y
      // "falta" fuera de tolerancia: el paso sigue al informe, no al fixture.
      const coeficientes = claveEscenario === "advertencia" ? "hecho" : "falta";
      return { ...datos, informe, pasos: { ...datos.pasos, coeficientes } };
    }
    if (nombreFixture === "unidades") return { ...datos, informe };
    return datos;
  }

  if (claveEscenario === "doscientas_unidades") {
    if (nombreFixture === "unidades") {
      return {
        informe: informeConEstado("ok", "0.000000", "1.000000"),
        unidades: Array.from({ length: 200 }, (_, indice) => unidadSintetica(indice)),
      };
    }
    if (nombreFixture === "resumen") return { ...datos, cantidad_unidades: 200 };
    return datos;
  }

  if (claveEscenario === "nombres_largos") {
    if (nombreFixture === "edificio" || nombreFixture === "resumen") {
      return { ...datos, nombre: NOMBRE_DE_200 };
    }
    if (nombreFixture === "unidades") {
      return {
        ...datos,
        unidades: datos.unidades.map((unidad: Json) => ({
          ...unidad,
          identificador: IDENTIFICADOR_DE_40,
        })),
      };
    }
    return datos;
  }

  return datos;
}

/** R3C-10 (rompedor 3b): la última escritura (POST/PATCH/PUT) que recibió
 * el servidor, para que un test externo (e2e, otro proceso) pueda leerla
 * por HTTP en `/api/__debug/ultima-escritura` — la API falsa no tenía
 * ninguna forma de ver qué le llegó, y por eso escondió R3C-1 (el POST de
 * la web viajaba como `text/plain` y nadie lo notó). */
type EscrituraRecibida = { metodo: string; url: string; contentType: string; cuerpo: string };
let _ultimaEscritura: EscrituraRecibida | null = null;

function _esEscritura(metodo: string | undefined): boolean {
  return metodo === "POST" || metodo === "PATCH" || metodo === "PUT";
}

const _ERROR_CONTENT_TYPE_INVALIDO = JSON.stringify({
  detail: [{ type: "model_attributes_type", loc: ["body"], msg: "Content-Type inválido" }],
});

/** Crea el servidor sin levantarlo (`listen()` queda a cargo de quien lo
 * use: así se puede probar sobre un puerto al azar). */
export function crearServidor(): Server {
  const unidadesCreadas = new Map<string, Json>();
  return createServer((pedido, respuesta) => {
    const url = new URL(pedido.url ?? "/", "http://localhost");
    const partes = url.pathname.split("/").filter(Boolean);

    if (partes[0] === "api" && partes[1] === "__debug" && partes[2] === "ultima-escritura") {
      respuesta
        .writeHead(200, { "content-type": "application/json" })
        .end(JSON.stringify(_ultimaEscritura));
      return;
    }

    if (partes[0] !== "api" || partes[1] !== "complejos") {
      respuesta.writeHead(404).end();
      return;
    }

    if (!partes[2]) {
      respuesta
        .writeHead(200, { "content-type": "application/json" })
        .end(JSON.stringify(leerFixture("lista")));
      return;
    }

    const id = partes[2];
    const resto = partes.slice(3).join("/");
    const escenario = escenarioPorId(id);

    const responderSegunEscenario = () => {
      switch (escenario?.clave) {
        case "error_500":
          // Texto técnico a propósito (L-007): la pantalla NUNCA lo
          // muestra, el cliente de la API (3.3) ya lo filtra antes de
          // llegar a React.
          respuesta
            .writeHead(500, { "content-type": "text/plain" })
            .end("Traceback (most recent call last): algo técnico que no es para el usuario");
          return true;
        case "sin_permiso_403":
          respuesta
            .writeHead(403, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: { permiso_faltante: "cambiar_configuracion" } }));
          return true;
        case "no_existe_404":
          respuesta.writeHead(404).end();
          return true;
        case "sin_sesion_401":
          respuesta.writeHead(401).end();
          return true;
        default:
          return false;
      }
    };

    const nombreFixture = _RUTAS[resto];
    if (!nombreFixture) {
      respuesta.writeHead(404).end();
      return;
    }

    const enviar = () => {
      if (responderSegunEscenario()) {
        return;
      }
      const datos = leerFixture(nombreFixture);
      let mutado = escenario ? mutarParaElEscenario(escenario.clave, nombreFixture, datos) : datos;
      if (
        resto === "unidades" &&
        Object.values(ESCRITURAS_UNIDADES).some((valor) => valor === id)
      ) {
        const unidad = unidadesCreadas.get(id);
        mutado = {
          unidades: unidad ? [unidad] : [],
          informe: unidad
            ? informeConEstado("ok", "0.000000", "1.000000")
            : informeConEstado("fuera_de_tolerancia", "-1.000000", "0.000000"),
        };
      }
      respuesta.writeHead(200, { "content-type": "application/json" }).end(JSON.stringify(mutado));
    };

    if (!_esEscritura(pedido.method)) {
      if (escenario?.clave === "lento") {
        setTimeout(enviar, 3000);
      } else {
        enviar();
      }
      return;
    }

    // R3C-10: a diferencia de un GET, una escritura SÍ mira el cuerpo que
    // llega — antes, cualquier POST/PATCH/PUT caía en la misma `enviar()`
    // de arriba sin que nadie leyera `pedido.method` ni el body, así que
    // contestaba 200 con el fixture de lectura sin importar el
    // Content-Type ni la forma del cuerpo (por eso R3C-1 pasó inadvertido
    // en todo el barrido del navegador).
    let cuerpo = "";
    pedido.on("data", (trozo) => {
      cuerpo += trozo;
    });
    pedido.on("end", () => {
      const contentType = String(pedido.headers["content-type"] ?? "");
      _ultimaEscritura = {
        metodo: pedido.method ?? "",
        url: pedido.url ?? "",
        contentType,
        cuerpo,
      };

      if (responderSegunEscenario()) {
        return;
      }
      if (!/^application\/json/.test(contentType)) {
        respuesta
          .writeHead(422, { "content-type": "application/json" })
          .end(_ERROR_CONTENT_TYPE_INVALIDO);
        return;
      }
      let cuerpoParseado: unknown;
      try {
        cuerpoParseado = cuerpo === "" ? {} : JSON.parse(cuerpo);
      } catch {
        respuesta
          .writeHead(422, { "content-type": "application/json" })
          .end(JSON.stringify({ detail: [{ type: "json_invalid", loc: ["body"] }] }));
        return;
      }
      if (
        cuerpoParseado === null ||
        typeof cuerpoParseado !== "object" ||
        Array.isArray(cuerpoParseado)
      ) {
        respuesta
          .writeHead(422, { "content-type": "application/json" })
          .end(JSON.stringify({ detail: [{ type: "model_attributes_type", loc: ["body"] }] }));
        return;
      }
      if (pedido.method === "POST" && resto === "unidades") {
        if (id === ESCRITURAS_UNIDADES.rechazo403) {
          respuesta
            .writeHead(403, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: { permiso_faltante: "modificar_unidades" } }));
          return;
        }
        if (id === ESCRITURAS_UNIDADES.rechazo422) {
          respuesta
            .writeHead(422, { "content-type": "application/json" })
            .end(
              JSON.stringify({ detail: [{ type: "value_error", loc: ["body", "identificador"] }] }),
            );
          return;
        }
        if (id === ESCRITURAS_UNIDADES.alta) {
          // Este escenario siempre carga una sola unidad con coeficiente 1.
          // Guarda en memoria y permite verificar la revalidación de Next.
          const unidad = {
            ...cuerpoParseado,
            id: "00000000-0000-0000-0000-000000000201",
            complejo_id: id,
          };
          unidadesCreadas.set(id, unidad);
          respuesta
            .writeHead(201, { "content-type": "application/json" })
            .end(JSON.stringify(unidad));
          return;
        }
      }
      enviar();
    });
  });
}

const _esPuntoDeEntrada = process.argv[1] === fileURLToPath(import.meta.url);
if (_esPuntoDeEntrada) {
  const puerto = Number(process.env.PROPTECH_PUERTO_API_FALSA ?? 4100);
  crearServidor().listen(puerto, () => {
    console.log(`api-falsa escuchando en :${puerto}`);
  });
}
