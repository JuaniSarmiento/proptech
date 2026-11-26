/**
 * El portal del vecino (change 11, H-040), a pedido de la API falsa: las rutas de H-038 y H-039 con las FORMAS
 * EXACTAS de sus contratos (`aceptacion/H-038/CONTRATO.md`, `aceptacion/H-039/CONTRATO.md`) y sus filtros reales
 * (L-107): sólo las unidades de la persona en sesión (un vínculo `vecino` sobre ellas), 404 `{"detail":
 * "no encontrado"}` para lo ajeno, el inquilino sin nada extraordinario (ni la clave) y la comparación con la
 * emisión inmediatamente anterior. Cada respuesta se comparó contra una respuesta real del backend construido
 * (la aceptación de H-038 y H-039 levantada con su base): mismas claves, mismo orden, mismos tipos.
 *
 * Identidades:
 * - `user_vecino_portal` (Ana): propietaria de `9A` en "Otro Edificio Ficticio" y de `1A` y `2B` en "Torre Ficticia".
 * - `user_inquilino_portal` (Beto): inquilino de `1B` en "Torre Ficticia" (el vínculo sin lo extraordinario).
 * Cualquier otra identidad (el personal) recibe lo que da la real: ninguna unidad.
 *
 * A propósito, para N02 (la pantalla no calcula): `conjunto.total_a_pagar` de Ana dice un centavo MÁS que la suma
 * de sus unidades y la `diferencia_total` de la comparación de `1A` dice un centavo más que el total menos el
 * anterior. La real nunca los desajusta; la pantalla tiene que mostrar lo que dice la API.
 *
 * `GET /api/documentos/descarga?token=...` (la del 7, pública: el token firmado es la autorización) baja un PDF
 * mínimo con el nombre de archivo de la real (`expensa-...pdf`); el token es `TOKEN_DE_PRUEBA`, otro da 403.
 */

import type { IncomingMessage, ServerResponse } from "node:http";
import { TOKEN_DE_PRUEBA } from "./escenarios-liquidacion";

export const IDENTIDADES_DEL_PORTAL = ["user_vecino_portal", "user_inquilino_portal"];

export const PORTAL_TORRE = "00000000-0000-0000-0000-000000004001";
export const PORTAL_OTRO = "00000000-0000-0000-0000-000000004002";

const _UNIDAD = {
  "1A": "00000000-0000-0000-0000-000000004101",
  "1B": "00000000-0000-0000-0000-000000004102",
  "2B": "00000000-0000-0000-0000-000000004103",
  "9A": "00000000-0000-0000-0000-000000004104",
} as const;
type Clave = keyof typeof _UNIDAD;

export const PORTAL_UNIDADES = _UNIDAD;

const _LIQ = {
  nov: "00000000-0000-0000-0000-000000004201",
  oct: "00000000-0000-0000-0000-000000004202",
} as const;
type Mes = keyof typeof _LIQ;

export const PORTAL_LIQUIDACIONES = _LIQ;

const _EDIFICIO_DE: Record<Clave, { id: string; nombre: string }> = {
  "1A": { id: PORTAL_TORRE, nombre: "Torre Ficticia" },
  "1B": { id: PORTAL_TORRE, nombre: "Torre Ficticia" },
  "2B": { id: PORTAL_TORRE, nombre: "Torre Ficticia" },
  "9A": { id: PORTAL_OTRO, nombre: "Otro Edificio Ficticio" },
};

type Vinculo = "propietario" | "inquilino";
const _VINCULOS: Record<string, [Clave, Vinculo][]> = {
  // Orden de la real: por nombre de edificio y, dentro, por identificador.
  user_vecino_portal: [
    ["9A", "propietario"],
    ["1A", "propietario"],
    ["2B", "propietario"],
  ],
  user_inquilino_portal: [["1B", "inquilino"]],
};

/** Las acciones de la sesión de los dos vecinos: sólo `informar_pago`, en sus edificios. */
export const ACCIONES_DEL_PORTAL: Record<string, Record<string, string[]>> = {
  user_vecino_portal: { [PORTAL_TORRE]: ["informar_pago"], [PORTAL_OTRO]: ["informar_pago"] },
  user_inquilino_portal: { [PORTAL_TORRE]: ["informar_pago"] },
};

const _ULTIMO = "2026-11-18";

function _cifras(unidad: Clave) {
  const cero = {
    total_a_pagar: "0.00",
    vencimiento: null as string | null,
    deuda_anterior: "0.00",
    intereses: "0.00",
    credito_aplicable: "0.00",
    credito_retenido: "0.00",
  };
  switch (unidad) {
    case "1A":
      return { ...cero, total_a_pagar: "46500.00", vencimiento: "2026-11-10" };
    case "2B":
      return {
        total_a_pagar: "40250.00",
        vencimiento: "2026-11-10",
        deuda_anterior: "10000.00",
        intereses: "1250.00",
        credito_aplicable: "1200.00",
        credito_retenido: "800.50",
      };
    case "1B":
      // El inquilino: la deuda sin el componente extraordinario.
      return { ...cero, total_a_pagar: "36500.00", vencimiento: "2026-11-10" };
    default:
      return cero;
  }
}

function _centavos(texto: string): bigint {
  return BigInt(texto.replace(".", ""));
}

function _texto(centavos: bigint): string {
  const negativo = centavos < 0n;
  const abs = negativo ? -centavos : centavos;
  return `${negativo ? "-" : ""}${abs / 100n}.${String(abs % 100n).padStart(2, "0")}`;
}

function _misUnidades(identidad: string) {
  const propias = _VINCULOS[identidad] ?? [];
  const filas = propias.map(([clave, vinculo]) => ({
    unidad_id: _UNIDAD[clave],
    identificador: clave,
    vinculo,
    complejo_id: _EDIFICIO_DE[clave].id,
    edificio: _EDIFICIO_DE[clave].nombre,
    ..._cifras(clave),
  }));
  const suma = (campo: "total_a_pagar" | "intereses" | "credito_aplicable" | "credito_retenido") =>
    filas.reduce((a, f) => a + _centavos(f[campo]), 0n);
  const conjunto = {
    // N02: Ana, un centavo de más a propósito (ver el encabezado).
    total_a_pagar: _texto(suma("total_a_pagar") + (identidad === "user_vecino_portal" ? 1n : 0n)),
    intereses: _texto(suma("intereses")),
    credito_aplicable: _texto(suma("credito_aplicable")),
    credito_retenido: _texto(suma("credito_retenido")),
  };
  return { fecha: _ULTIMO, conjunto, unidades: filas };
}

// --- Liquidaciones (H-039) ---------------------------------------------------------------------------------

type Fila = {
  ordinaria: string;
  cargos: { concepto: string; importe: string }[];
  fondo: string;
  extraordinaria: string;
  intereses: string;
  grupos: { grupo_id: string; nombre: string; ordinaria: string; extraordinaria: string }[];
};

const _GENERALES = "00000000-0000-0000-0000-000000004301";
const _ASCENSOR = "00000000-0000-0000-0000-000000004302";
const _LIMPIEZA = "00000000-0000-0000-0000-000000004311";
const _ASCENSOR_CAT = "00000000-0000-0000-0000-000000004312";
const _PINTURA = "00000000-0000-0000-0000-000000004313";

const _FILAS: Record<`${Clave}:${Mes}`, Fila | undefined> = {
  "1A:nov": {
    ordinaria: "30000.00",
    cargos: [],
    fondo: "1500.00",
    extraordinaria: "15000.00",
    intereses: "0.00",
    grupos: [
      {
        grupo_id: _GENERALES,
        nombre: "Generales",
        ordinaria: "30000.00",
        extraordinaria: "15000.00",
      },
    ],
  },
  "1A:oct": {
    ordinaria: "24000.00",
    cargos: [],
    fondo: "1200.00",
    extraordinaria: "6000.00",
    intereses: "0.00",
    grupos: [
      {
        grupo_id: _GENERALES,
        nombre: "Generales",
        ordinaria: "24000.00",
        extraordinaria: "6000.00",
      },
    ],
  },
  "2B:nov": {
    ordinaria: "35000.00",
    cargos: [],
    fondo: "1750.00",
    extraordinaria: "7500.00",
    intereses: "1250.00",
    grupos: [
      {
        grupo_id: _GENERALES,
        nombre: "Generales",
        ordinaria: "15000.00",
        extraordinaria: "7500.00",
      },
      { grupo_id: _ASCENSOR, nombre: "Ascensor", ordinaria: "20000.00", extraordinaria: "0.00" },
    ],
  },
  "2B:oct": {
    ordinaria: "20000.00",
    cargos: [],
    fondo: "1000.00",
    extraordinaria: "3000.00",
    intereses: "0.00",
    grupos: [
      {
        grupo_id: _GENERALES,
        nombre: "Generales",
        ordinaria: "20000.00",
        extraordinaria: "3000.00",
      },
    ],
  },
  "1B:nov": {
    ordinaria: "30000.00",
    cargos: [{ concepto: "Multa", importe: "5000.00" }],
    fondo: "1500.00",
    extraordinaria: "15000.00",
    intereses: "0.00",
    grupos: [
      {
        grupo_id: _GENERALES,
        nombre: "Generales",
        ordinaria: "30000.00",
        extraordinaria: "15000.00",
      },
    ],
  },
  "1B:oct": {
    ordinaria: "24000.00",
    cargos: [],
    fondo: "1200.00",
    extraordinaria: "6000.00",
    intereses: "0.00",
    grupos: [
      {
        grupo_id: _GENERALES,
        nombre: "Generales",
        ordinaria: "24000.00",
        extraordinaria: "6000.00",
      },
    ],
  },
  "9A:nov": undefined,
  "9A:oct": undefined,
};

const _PERIODO: Record<Mes, string> = { nov: "2026-11-01", oct: "2026-10-01" };
const _VENCE: Record<Mes, string> = { nov: "2026-11-10", oct: "2026-10-10" };

function _total(fila: Fila, vinculo: Vinculo): string {
  const cargos = fila.cargos.reduce((a, c) => a + _centavos(c.importe), 0n);
  const base =
    _centavos(fila.ordinaria) + cargos + _centavos(fila.fondo) + _centavos(fila.intereses);
  return _texto(vinculo === "propietario" ? base + _centavos(fila.extraordinaria) : base);
}

function _bloques(mes: Mes, vinculo: Vinculo) {
  const ordinario =
    mes === "nov"
      ? {
          subtotal: "140000.00",
          categorias: [
            {
              categoria_id: _LIMPIEZA,
              nombre: "Limpieza",
              importe: "100000.00",
              porcentaje: "71.43",
            },
            {
              categoria_id: _ASCENSOR_CAT,
              nombre: "Ascensor",
              importe: "40000.00",
              porcentaje: "28.57",
            },
          ],
        }
      : {
          subtotal: "80000.00",
          categorias: [
            {
              categoria_id: _LIMPIEZA,
              nombre: "Limpieza",
              importe: "80000.00",
              porcentaje: "100.00",
            },
          ],
        };
  const extraordinario = {
    subtotal: mes === "nov" ? "50000.00" : "20000.00",
    categorias: [
      {
        categoria_id: _PINTURA,
        nombre: "Pintura",
        importe: mes === "nov" ? "50000.00" : "20000.00",
        porcentaje: "100.00",
      },
    ],
  };
  // El inquilino no tiene la clave `extraordinario` (H-039).
  return vinculo === "propietario" ? { ordinario, extraordinario } : { ordinario };
}

function _comparacion(unidad: Clave, vinculo: Vinculo) {
  const anterior = _FILAS[`${unidad}:oct`];
  const actual = _FILAS[`${unidad}:nov`];
  if (!anterior || !actual) return null;
  const totalAnterior = _total(anterior, vinculo);
  const diferencia = _centavos(_total(actual, vinculo)) - _centavos(totalAnterior);
  const categorias = [
    {
      categoria_id: _LIMPIEZA,
      nombre: "Limpieza",
      bloque: "ordinario",
      importe: "100000.00",
      importe_anterior: "80000.00",
      diferencia: "20000.00",
    },
    {
      categoria_id: _ASCENSOR_CAT,
      nombre: "Ascensor",
      bloque: "ordinario",
      importe: "40000.00",
      importe_anterior: "0.00",
      diferencia: "40000.00",
    },
    ...(vinculo === "propietario"
      ? [
          {
            categoria_id: _PINTURA,
            nombre: "Pintura",
            bloque: "extraordinario",
            importe: "50000.00",
            importe_anterior: "20000.00",
            diferencia: "30000.00",
          },
        ]
      : []),
  ];
  return {
    liquidacion_id: _LIQ.oct,
    periodo: _PERIODO.oct,
    total_anterior: totalAnterior,
    // N02: en 1A, un centavo de más a propósito (ver el encabezado).
    diferencia_total: _texto(diferencia + (unidad === "1A" ? 1n : 0n)),
    categorias,
  };
}

function _lista(unidad: Clave, vinculo: Vinculo) {
  return (["nov", "oct"] as Mes[]).flatMap((mes) => {
    const fila = _FILAS[`${unidad}:${mes}`];
    return fila
      ? [
          {
            liquidacion_id: _LIQ[mes],
            periodo: _PERIODO[mes],
            vencimiento: _VENCE[mes],
            total: _total(fila, vinculo),
          },
        ]
      : [];
  });
}

function _detalle(unidad: Clave, vinculo: Vinculo, mes: Mes) {
  const fila = _FILAS[`${unidad}:${mes}`];
  if (!fila) return null;
  const propietario = vinculo === "propietario";
  return {
    liquidacion_id: _LIQ[mes],
    complejo_id: _EDIFICIO_DE[unidad].id,
    unidad_id: _UNIDAD[unidad],
    identificador: unidad,
    periodo: _PERIODO[mes],
    vencimiento: _VENCE[mes],
    vinculo,
    bloques: _bloques(mes, vinculo),
    grupos: fila.grupos.map((g) =>
      propietario ? g : { grupo_id: g.grupo_id, nombre: g.nombre, ordinaria: g.ordinaria },
    ),
    ordinaria: fila.ordinaria,
    cargos_particulares: fila.cargos,
    fondo_de_reserva: fila.fondo,
    ...(propietario ? { extraordinaria: fila.extraordinaria } : {}),
    intereses: fila.intereses,
    total: _total(fila, vinculo),
    comparacion: mes === "nov" ? _comparacion(unidad, vinculo) : null,
  };
}

// --- Pagos y documentos (H-038) ----------------------------------------------------------------------------

const _PAGOS: Record<Clave, Record<string, string>[]> = {
  // Del más nuevo al más viejo por fecha de transferencia; sólo los confirmados.
  "1A": [
    {
      pago_id: "00000000-0000-0000-0000-000000004401",
      fecha_de_transferencia: "2026-11-05",
      importe: "10000.00",
      banco: "Banco Nación",
      numero_de_operacion: "OP-0001",
    },
    {
      pago_id: "00000000-0000-0000-0000-000000004402",
      fecha_de_transferencia: "2026-11-03",
      importe: "1000.00",
      banco: "Banco Galicia",
      numero_de_operacion: "OP-0002",
    },
  ],
  // El pago de dos unidades aparece en cada una con su parte.
  "2B": [
    {
      pago_id: "00000000-0000-0000-0000-000000004401",
      fecha_de_transferencia: "2026-11-05",
      importe: "5000.00",
      banco: "Banco Nación",
      numero_de_operacion: "OP-0001",
    },
  ],
  // El inquilino ve sólo lo imputado sin la extraordinaria.
  "1B": [
    {
      pago_id: "00000000-0000-0000-0000-000000004407",
      fecha_de_transferencia: "2026-11-04",
      importe: "33350.00",
      banco: "Banco Santander",
      numero_de_operacion: "OP-0007",
    },
  ],
  "9A": [],
};

const _DOCUMENTO: Record<Clave, string> = {
  "1A": "00000000-0000-0000-0000-000000004501",
  "2B": "00000000-0000-0000-0000-000000004502",
  "1B": "00000000-0000-0000-0000-000000004503",
  "9A": "00000000-0000-0000-0000-000000004504",
};

function _documentos(unidad: Clave, vinculo: Vinculo) {
  if (unidad === "9A") return [];
  return [
    {
      documento_id: _DOCUMENTO[unidad],
      liquidacion_id: _LIQ.nov,
      complejo_id: _EDIFICIO_DE[unidad].id,
      periodo: _PERIODO.nov,
      variante: vinculo === "propietario" ? "completa" : "sin_extraordinaria",
      url: `/api/documentos/descarga?token=${TOKEN_DE_PRUEBA}`,
      vence_en: "2026-11-18T15:15:00+00:00",
    },
  ];
}

// --- Las rutas ---------------------------------------------------------------------------------------------

function _json(respuesta: ServerResponse, estado: number, cuerpo: unknown): void {
  respuesta.writeHead(estado, { "content-type": "application/json" }).end(JSON.stringify(cuerpo));
}

const _UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const _NO_ENCONTRADO = { detail: "no encontrado" };

/** `GET /api/documentos/descarga`: pública (el token firmado es la autorización). `true` si la contestó. */
export function responderDescargaDePdf(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  url: URL,
): boolean {
  if (url.pathname !== "/api/documentos/descarga") return false;
  if (pedido.method !== "GET") {
    respuesta.writeHead(405).end();
    return true;
  }
  if (url.searchParams.get("token") !== TOKEN_DE_PRUEBA) {
    _json(respuesta, 403, { detail: "enlace_invalido" });
    return true;
  }
  respuesta
    .writeHead(200, {
      "content-type": "application/pdf",
      "content-disposition": 'attachment; filename="expensa-2026-11-unidad-completa.pdf"',
    })
    .end(Buffer.from("%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"));
  return true;
}

/** Las rutas `/api/mis-unidades...`. `true` si la ruta es del portal (y ya contestó). */
export function responderPortal(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  url: URL,
  identidad: string,
): boolean {
  const partes = url.pathname.split("/").filter(Boolean);
  if (partes[0] !== "api" || partes[1] !== "mis-unidades") return false;
  if (pedido.method !== "GET") {
    respuesta.writeHead(405).end();
    return true;
  }
  if (!partes[2]) {
    _json(respuesta, 200, _misUnidades(identidad));
    return true;
  }
  if (!_UUID.test(partes[2])) {
    _json(respuesta, 422, { detail: [{ type: "uuid_parsing", loc: ["path", "unidad_id"] }] });
    return true;
  }
  const propia = (_VINCULOS[identidad] ?? []).find(([clave]) => _UNIDAD[clave] === partes[2]);
  if (!propia) {
    _json(respuesta, 404, _NO_ENCONTRADO);
    return true;
  }
  const [unidad, vinculo] = propia;
  const resto = partes.slice(3);
  if (resto.length === 1 && resto[0] === "pagos") {
    _json(respuesta, 200, _PAGOS[unidad]);
    return true;
  }
  if (resto.length === 1 && resto[0] === "documentos") {
    _json(respuesta, 200, _documentos(unidad, vinculo));
    return true;
  }
  if (resto[0] === "liquidaciones") {
    if (resto.length === 1) {
      _json(respuesta, 200, _lista(unidad, vinculo));
      return true;
    }
    if (resto.length === 2) {
      if (!_UUID.test(resto[1] ?? "")) {
        _json(respuesta, 422, {
          detail: [{ type: "uuid_parsing", loc: ["path", "liquidacion_id"] }],
        });
        return true;
      }
      const mes = (Object.keys(_LIQ) as Mes[]).find((m) => _LIQ[m] === resto[1]);
      const detalle = mes ? _detalle(unidad, vinculo, mes) : null;
      if (detalle) _json(respuesta, 200, detalle);
      else _json(respuesta, 404, _NO_ENCONTRADO);
      return true;
    }
  }
  _json(respuesta, 404, _NO_ENCONTRADO);
  return true;
}
