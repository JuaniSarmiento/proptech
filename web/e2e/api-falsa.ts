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

import { verify } from "node:crypto";
import { readFileSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { escenarioPorId } from "./escenarios";
import { ESCRITURAS_UNIDADES } from "./escenarios-escritura";
import { ADMINISTRACION, EMISOR } from "./sesion-local";

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

/** Personal de prueba (7.3): un `super_admin` ya vinculado, un `contador`
 * con invitación `fallida` (worker, sin "Reintentar") y un `auxiliar` con
 * invitación `pendiente`, ambos de "Edificio API" (`lista.json`). */
export const EDIFICIO_API = "a08ae80a-8d7e-47eb-9b37-f36b7be80114";
const _PERSONAL_DE_PRUEBA = [
  {
    persona_id: "00000000-0000-0000-0000-000000000101",
    nombre: "Ana Superadmin",
    email: "ana@test.com",
    vinculado: true,
    asignaciones: [
      {
        asignacion_id: "00000000-0000-0000-0000-000000000201",
        rol: "super_admin",
        complejo_id: null,
        unidad_id: null,
        vinculo: null,
      },
    ],
    invitacion: { invitacion_id: "00000000-0000-0000-0000-000000000301", estado: "aceptada" },
  },
  {
    persona_id: "00000000-0000-0000-0000-000000000102",
    nombre: "Beto Contador",
    email: "beto@test.com",
    vinculado: false,
    asignaciones: [
      {
        asignacion_id: "00000000-0000-0000-0000-000000000202",
        rol: "contador",
        complejo_id: EDIFICIO_API,
        unidad_id: null,
        vinculo: null,
      },
    ],
    invitacion: { invitacion_id: "00000000-0000-0000-0000-000000000302", estado: "fallida" },
  },
  {
    persona_id: "00000000-0000-0000-0000-000000000103",
    nombre: "Caro Auxiliar",
    email: "caro@test.com",
    vinculado: false,
    asignaciones: [
      {
        asignacion_id: "00000000-0000-0000-0000-000000000203",
        rol: "auxiliar",
        complejo_id: EDIFICIO_API,
        unidad_id: null,
        vinculo: null,
      },
    ],
    invitacion: { invitacion_id: "00000000-0000-0000-0000-000000000303", estado: "pendiente" },
  },
];

function _esEscritura(metodo: string | undefined): boolean {
  return metodo === "POST" || metodo === "PATCH" || metodo === "PUT";
}

const _ERROR_CONTENT_TYPE_INVALIDO = JSON.stringify({
  detail: [{ type: "model_attributes_type", loc: ["body"], msg: "Content-Type inválido" }],
});

/** Crea el servidor sin levantarlo (`listen()` queda a cargo de quien lo
 * use: así se puede probar sobre un puerto al azar). */
export function crearServidor(
  configuracion = {
    jwtKey: process.env.CLERK_JWT_KEY ?? "",
    origen: process.env.PROPTECH_URL_WEB ?? "http://127.0.0.1:3100",
  },
): Server {
  const unidadesCreadas = new Map<string, Json>();
  return createServer((pedido, respuesta) => {
    const url = new URL(pedido.url ?? "/", "http://localhost");
    const partes = url.pathname.split("/").filter(Boolean);

    // L-027: ninguna cookie autentica a la API, ni siquiera en pruebas.
    let valido = false;
    let identidad = "";
    try {
      const bearer = /^Bearer ([^.\s]+\.[^.\s]+\.[^.\s]+)$/.exec(
        pedido.headers.authorization ?? "",
      );
      if (bearer?.[1]) {
        const [cabecera, cuerpo, firma] = bearer[1].split(".");
        if (!cabecera || !cuerpo || !firma) throw new Error("formato JWT");
        const algoritmo = JSON.parse(Buffer.from(cabecera, "base64url").toString());
        const claims = JSON.parse(Buffer.from(cuerpo, "base64url").toString());
        const ahora = Date.now() / 1000;
        identidad = claims.sub;
        valido =
          algoritmo.alg === "RS256" &&
          verify(
            "RSA-SHA256",
            Buffer.from(`${cabecera}.${cuerpo}`),
            configuracion.jwtKey,
            Buffer.from(firma, "base64url"),
          ) &&
          typeof claims.exp === "number" &&
          ahora < claims.exp + 5 &&
          typeof claims.nbf === "number" &&
          ahora >= claims.nbf - 5 &&
          claims.iss === EMISOR &&
          claims.azp === configuracion.origen &&
          [
            "user_prueba",
            "user_varias",
            "user_sin_permiso",
            "user_personal_vacio",
            "user_personal_error",
            "user_personal_lento",
          ].includes(claims.sub);
      }
    } catch {
      /* Un 401 uniforme, sin errores del verificador ni credenciales. */
    }
    const esSesion = url.pathname === "/api/sesion";
    const selector = pedido.headers["x-proptech-administracion"];
    const esAceptar = url.pathname === "/api/invitaciones/aceptar";
    if (
      !valido ||
      (!esSesion &&
        !esAceptar &&
        selector !== undefined &&
        selector !== ADMINISTRACION &&
        !(identidad === "user_varias" && selector === "10000000-0000-0000-0000-000000000002"))
    ) {
      respuesta.writeHead(401).end();
      return;
    }
    if (esSesion) {
      if (pedido.method !== "GET") {
        respuesta.writeHead(405).end();
        return;
      }
      respuesta.writeHead(200, { "content-type": "application/json" }).end(
        JSON.stringify({
          persona: { nombre: "Persona de prueba" },
          administraciones: [
            { id: ADMINISTRACION, nombre: "Administración de prueba" },
            ...(identidad === "user_varias"
              ? [
                  {
                    id: "10000000-0000-0000-0000-000000000002",
                    nombre: "Administración del Parque",
                  },
                ]
              : []),
          ],
        }),
      );
      return;
    }
    if (esAceptar) {
      if (pedido.method !== "POST") {
        respuesta.writeHead(405).end();
        return;
      }
      let crudo = "";
      pedido.on("data", (t) => {
        crudo += t;
      });
      pedido.on("end", () => {
        let cuerpo: unknown;
        try {
          cuerpo = JSON.parse(crudo);
        } catch {
          cuerpo = null;
        }
        const valido =
          cuerpo !== null &&
          typeof cuerpo === "object" &&
          !Array.isArray(cuerpo) &&
          Object.keys(cuerpo).length === 1 &&
          typeof (cuerpo as Record<string, unknown>).token === "string" &&
          /^application\/json/.test(String(pedido.headers["content-type"]));
        if (!valido) {
          respuesta
            .writeHead(422, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: [{ type: "value_error", loc: ["body", "token"] }] }));
          return;
        }
        if ((cuerpo as { token: string }).token !== "sobre-valido") {
          respuesta
            .writeHead(404, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: "no encontrado" }));
          return;
        }
        respuesta
          .writeHead(200, { "content-type": "application/json" })
          .end(JSON.stringify({ aceptada: true }));
      });
      return;
    }
    if (url.pathname === "/api/sesion/ingreso") {
      respuesta
        .writeHead(pedido.method === "POST" ? 200 : 405, { "content-type": "application/json" })
        .end(JSON.stringify({ registrado: true }));
      return;
    }

    // 7.3: Personal (D5). Reusa el patrón de `esAceptar` (autentica antes
    // de mirar el cuerpo, 405 fuera de su método, 422 nombra el campo).
    if (url.pathname === "/api/personal") {
      if (pedido.method !== "GET") {
        respuesta.writeHead(405).end();
        return;
      }
      if (identidad === "user_sin_permiso") {
        respuesta.writeHead(403, { "content-type": "application/json" }).end(
          JSON.stringify({
            detail: { permiso_faltante: "invitar_usuarios_y_asignar_edificios" },
          }),
        );
        return;
      }
      if (identidad === "user_personal_error") {
        respuesta
          .writeHead(500, { "content-type": "text/plain" })
          .end("Traceback (most recent call last): algo técnico que no es para el usuario");
        return;
      }
      const responder = () => {
        respuesta
          .writeHead(200, { "content-type": "application/json" })
          .end(JSON.stringify(identidad === "user_personal_vacio" ? [] : _PERSONAL_DE_PRUEBA));
      };
      if (identidad === "user_personal_lento") {
        setTimeout(responder, 3000);
      } else {
        responder();
      }
      return;
    }
    if (url.pathname === "/api/personal/invitaciones") {
      if (pedido.method !== "POST") {
        respuesta.writeHead(405).end();
        return;
      }
      let crudo = "";
      pedido.on("data", (t) => {
        crudo += t;
      });
      pedido.on("end", () => {
        if (!/^application\/json/.test(String(pedido.headers["content-type"]))) {
          respuesta
            .writeHead(422, { "content-type": "application/json" })
            .end(_ERROR_CONTENT_TYPE_INVALIDO);
          return;
        }
        let cuerpo: Record<string, unknown>;
        try {
          const parseado = JSON.parse(crudo);
          cuerpo =
            parseado !== null && typeof parseado === "object" && !Array.isArray(parseado)
              ? parseado
              : {};
        } catch {
          respuesta
            .writeHead(422, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: [{ type: "json_invalid", loc: ["body"] }] }));
          return;
        }
        const email = String(cuerpo.email ?? "");
        const rol = String(cuerpo.rol ?? "");
        const alcance = String(cuerpo.alcance ?? "");
        const complejoId = cuerpo.complejo_id;
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
          respuesta
            .writeHead(422, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: [{ type: "value_error", loc: ["body", "email"] }] }));
          return;
        }
        const soloEdificio = rol === "auxiliar" || rol === "consejo";
        if (
          (alcance === "edificio") !== (complejoId !== undefined) ||
          (soloEdificio && alcance === "principal")
        ) {
          respuesta
            .writeHead(422, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: [{ type: "value_error", loc: ["body", "alcance"] }] }));
          return;
        }
        if (email === "ya-invitado@test.com") {
          respuesta
            .writeHead(409, { "content-type": "application/json" })
            .end(JSON.stringify({ detail: "conflicto", campo: "rol" }));
          return;
        }
        respuesta.writeHead(201, { "content-type": "application/json" }).end(
          JSON.stringify({
            persona_id: "00000000-0000-0000-0000-000000000901",
            asignacion_id: "00000000-0000-0000-0000-000000000902",
            invitacion_id: "00000000-0000-0000-0000-000000000903",
          }),
        );
      });
      return;
    }
    if (/^\/api\/invitaciones\/[^/]+\/revocar$/.test(url.pathname)) {
      if (pedido.method !== "POST") {
        respuesta.writeHead(405).end();
        return;
      }
      const id = url.pathname.split("/")[3];
      if (id === "00000000-0000-0000-0000-0000000000ee") {
        respuesta
          .writeHead(404, { "content-type": "application/json" })
          .end(JSON.stringify({ detail: "no encontrado" }));
        return;
      }
      respuesta
        .writeHead(200, { "content-type": "application/json" })
        .end(JSON.stringify({ revocada: true }));
      return;
    }
    if (/^\/api\/asignaciones\/[^/]+$/.test(url.pathname)) {
      if (pedido.method !== "DELETE") {
        respuesta.writeHead(405).end();
        return;
      }
      const id = url.pathname.split("/")[3];
      if (id === "00000000-0000-0000-0000-0000000000ee") {
        respuesta
          .writeHead(404, { "content-type": "application/json" })
          .end(JSON.stringify({ detail: "no encontrado" }));
        return;
      }
      respuesta
        .writeHead(200, { "content-type": "application/json" })
        .end(JSON.stringify({ quitada: true }));
      return;
    }

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
