/**
 * El cambio de titular y las cuentas de vendedores (change 4d, H-034), a pedido de la API falsa: seis
 * edificios del contrato (`aceptacion/H-034/CONTRATO.md`, "API falsa"). Contestan con las formas EXACTAS de
 * las rutas reales de H-030 a H-033 (`.../unidades/{u}/cambios-de-titular`, `.../cuentas-de-vendedores`);
 * el padrón y `/api/personal` los arma este módulo con las mismas personas. Con estado en memoria, por
 * edificio: cada test que escribe tiene su propio edificio.
 *
 * - 3401 lectura (nada se escribe) · 3402 cobros · 3403 venta con traslado y prorrateo pendiente ·
 *   3404 venta con la deuda en la unidad y prorrateo aplicado · 3405 los 422 · 3406 el recorrido a 320 px.
 *
 * Los montos son LOS DE LA API: la falsa no deriva ninguno de la pantalla. A propósito (N02) la deuda de
 * Luis Intermedio dice un centavo más que la suma de sus períodos, y su cobro devuelve un centavo más que
 * `deuda - importe`: la pantalla muestra lo que dice la API y nunca lo recalcula.
 */

import type { IncomingMessage, ServerResponse } from "node:http";

const _EDIFICIOS = [1, 2, 3, 4, 5, 6] as const;
const _PERIODOS_COMPONENTES = [
  "interes",
  "ordinaria",
  "fondo_de_reserva",
  "extraordinaria",
] as const;

export const TITULARIDAD_LECTURA = edificio(1);
export const TITULARIDAD_COBROS = edificio(2);
export const TITULARIDAD_VENTA_CON_TRASLADO = edificio(3);
export const TITULARIDAD_VENTA_EN_LA_UNIDAD = edificio(4);
export const TITULARIDAD_ERRORES = edificio(5);
export const TITULARIDAD_RECORRIDO = edificio(6);

function edificio(k: number): string {
  return `00000000-0000-0000-0000-00000000340${k}`;
}

function sub(tipo: 1 | 2 | 3 | 4, k: number, n: number): string {
  return `00000000-0000-0000-0000-0000034${tipo}0${k}${String(n).padStart(2, "0")}`;
}

const _IDS = new Set(_EDIFICIOS.map(edificio));

export function esEdificioDeTitularidad(id: string): boolean {
  return _IDS.has(id);
}

/** Las identidades de esta aceptación: el administrador y quien sólo lee (contador, auxiliar o consejo). */
export const IDENTIDADES_DE_TITULARIDAD = ["user_titular", "user_lector"];

/** Las acciones de `user_lector` (y ninguna más): lee la configuración y la morosidad; no escribe. */
export const ACCIONES_DEL_LECTOR: Record<string, string[]> = Object.fromEntries(
  _EDIFICIOS.map((k) => [edificio(k), ["ver_configuracion_del_edificio", "ver_morosidad"]]),
);

function accionesDe(identidad: string): string[] {
  if (identidad === "user_vecina") return [];
  if (identidad === "user_lector") return ["ver_morosidad"];
  return ["ver_morosidad", "confirmar_pago_informado", "registrar_cambio_de_titular"];
}

type Persona = { id: string; nombre: string; email: string | null };
type Asignacion = { personaId: string; unidadId: string; vinculo: "propietario" | "inquilino" };
type Unidad = { id: string; identificador: string; deuda: number };
type Componentes = Record<string, { debe: number; cobrado: number }>;
type Periodo = { periodo: string; componentes: Componentes };
type Movimiento = { id: string; tipo: string; sentido: string; importe: number; fecha: string };
type Cuenta = {
  id: string;
  personaId: string;
  unidades: string[];
  periodos: Periodo[];
  movimientos: Movimiento[];
  /** Centavos que la deuda de la API dice de más que la suma de los períodos (N02). */
  desvio: number;
};
type Cambio = Record<string, unknown> & { id: string; unidad_id: string; fecha: string };
type Estado = {
  k: number;
  personas: Persona[];
  asignaciones: Asignacion[];
  unidades: Unidad[];
  cambios: Cambio[]; // el más nuevo primero
  cuentas: Cuenta[];
  contador: number;
};

const _ESTADOS = new Map<string, Estado>();

function texto(centavos: number): string {
  const negativo = centavos < 0;
  const abs = Math.abs(centavos);
  return `${negativo ? "-" : ""}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, "0")}`;
}

function centavos(valor: string): number {
  const [entera = "0", decimales = ""] = valor.split(".");
  return Number(entera) * 100 + Number(decimales.padEnd(2, "0"));
}

function periodo(mes: string, componentes: Record<string, number>, cobrado = 0): Periodo {
  return {
    periodo: mes,
    componentes: Object.fromEntries(
      Object.entries(componentes).map(([c, debe]) => [
        c,
        { debe, cobrado: c === "interes" ? 0 : cobrado },
      ]),
    ),
  };
}

function deudaDe(cuenta: Cuenta): number {
  let suma = cuenta.desvio;
  for (const p of cuenta.periodos) {
    for (const c of Object.values(p.componentes)) suma += c.debe - c.cobrado;
  }
  return suma;
}

function estadoDe(id: string): Estado {
  const hecho = _ESTADOS.get(id);
  if (hecho) return hecho;
  const k = _EDIFICIOS.find((n) => edificio(n) === id) ?? 1;
  const persona = (n: number, nombre: string, correo: string): Persona => ({
    id: sub(2, k, n),
    nombre,
    email: `${correo}@prueba.test`,
  });
  const [ana, bruno, carla, dario, pedro, luis, eva] = [
    persona(1, "Ana Prueba", "ana"),
    persona(2, "Bruno Prueba", "bruno"),
    persona(3, "Carla Prueba", "carla"),
    persona(4, "Dario Inquilino", "dario"),
    persona(5, "Pedro Anterior", "pedro"),
    persona(6, "Luis Intermedio", "luis"),
    persona(7, "Eva Previa", "eva"),
  ] as [Persona, Persona, Persona, Persona, Persona, Persona, Persona];
  const u1A = sub(1, k, 1);
  const u1B = sub(1, k, 2);
  const u2A = sub(1, k, 3);
  const comprador = (p: Persona) => ({ nombre: p.nombre, email: p.email, persona_id: p.id });
  const cambio = (n: number, resto: Record<string, unknown>): Cambio =>
    ({
      id: sub(4, k, n),
      unidad_id: u1A,
      registrado_por: sub(2, k, 90),
      registrado_en: "2026-11-01T15:00:00+00:00",
      ...resto,
    }) as unknown as Cambio;
  const cambios: Cambio[] = [
    cambio(2, {
      fecha: "2025-09-11",
      vendedores: [luis.id],
      compradores: [comprador(ana), comprador(bruno)],
      expensa_del_mes: "prorrateo",
      deuda_previa: "a_nombre_del_vendedor",
      trasladado: "9000.50",
      cuenta_del_vendedor: sub(3, k, 2),
      prorrateo: {
        estado: "aplicado",
        periodo: "2025-09-01",
        dias_del_vendedor: 10,
        dias_del_mes: 30,
        parte_del_vendedor: "3500.00",
      },
    }),
    cambio(1, {
      fecha: "2024-05-20",
      vendedores: [pedro.id],
      compradores: [comprador(luis)],
      expensa_del_mes: "entera",
      deuda_previa: "en_la_unidad",
    }),
  ];
  if (k === 5) {
    // Un prorrateo pendiente de noviembre de 2026 en la `1A`: otro igual da 422 en `expensa_del_mes`.
    cambios.unshift(
      cambio(3, {
        fecha: "2026-11-05",
        vendedores: [pedro.id],
        compradores: [comprador(eva)],
        expensa_del_mes: "prorrateo",
        deuda_previa: "en_la_unidad",
        prorrateo: {
          estado: "pendiente",
          periodo: "2026-11-01",
          dias_del_vendedor: 4,
          dias_del_mes: 30,
          parte_del_vendedor: null,
        },
      }),
    );
  }
  const traslado = (n: number, importe: number, fecha: string): Movimiento => ({
    id: sub(4, k, 50 + n),
    tipo: "traslado",
    sentido: "debito",
    importe,
    fecha,
  });
  const cuentas: Cuenta[] = [
    {
      id: sub(3, k, 1),
      personaId: ana.id,
      unidades: [u1B, u2A],
      desvio: 0,
      periodos: [
        periodo("2026-09-01", { interes: 150000, ordinaria: 1850000 }),
        periodo("2026-10-01", { ordinaria: 1000000 }),
      ],
      movimientos: [traslado(1, 2000000, "2026-10-31"), traslado(2, 1000000, "2026-11-05")],
    },
    {
      id: sub(3, k, 2),
      personaId: luis.id,
      unidades: [u1A],
      desvio: 1,
      periodos: [
        periodo("2025-08-01", { ordinaria: 900050 }),
        periodo("2025-09-01", { ordinaria: 350000 }),
      ],
      movimientos: [traslado(3, 900050, "2025-09-11"), traslado(4, 350000, "2025-09-11")],
    },
    {
      id: sub(3, k, 3),
      personaId: pedro.id,
      unidades: [u1A],
      desvio: 0,
      periodos: [periodo("2024-06-01", { ordinaria: 500000 }, 500000)],
      movimientos: [
        traslado(5, 500000, "2024-05-20"),
        {
          id: sub(4, k, 56),
          tipo: "pago",
          sentido: "credito",
          importe: 500000,
          fecha: "2024-06-10",
        },
      ],
    },
  ];
  const estado: Estado = {
    k,
    personas: [ana, bruno, carla, dario, pedro, luis, eva],
    asignaciones: [
      { personaId: ana.id, unidadId: u1A, vinculo: "propietario" },
      { personaId: bruno.id, unidadId: u1A, vinculo: "propietario" },
      { personaId: carla.id, unidadId: u1B, vinculo: "propietario" },
      { personaId: carla.id, unidadId: u2A, vinculo: "propietario" },
      { personaId: dario.id, unidadId: u2A, vinculo: "inquilino" },
    ],
    unidades: [
      { id: u1A, identificador: "1A", deuda: 4523010 },
      { id: u1B, identificador: "1B", deuda: 0 },
      { id: u2A, identificador: "2A", deuda: 0 },
    ],
    cambios,
    cuentas,
    contador: 10,
  };
  _ESTADOS.set(id, estado);
  return estado;
}

function json(respuesta: ServerResponse, estado: number, cuerpo: unknown): void {
  respuesta.writeHead(estado, { "content-type": "application/json" }).end(JSON.stringify(cuerpo));
}

function sinPermiso(respuesta: ServerResponse, permiso: string): void {
  json(respuesta, 403, {
    detail: { codigo: "sin_permiso", detalle: "sin_permiso", permiso_faltante: permiso },
  });
}

function invalido(respuesta: ServerResponse, campo: string): void {
  json(respuesta, 422, {
    detail: [{ type: "value_error", loc: ["body", campo], msg: "valor inválido" }],
  });
}

function leerCuerpo(pedido: IncomingMessage, alTerminar: (cuerpo: unknown) => void): void {
  const trozos: Buffer[] = [];
  pedido.on("data", (t: Buffer) => trozos.push(t));
  pedido.on("end", () => {
    try {
      alTerminar(JSON.parse(Buffer.concat(trozos).toString("utf8")));
    } catch {
      alTerminar(null);
    }
  });
}

const _FECHA = /^\d{4}-\d{2}-\d{2}$/;

function hoy(): string {
  return new Date().toISOString().slice(0, 10);
}

function fechaValida(valor: unknown): valor is string {
  if (typeof valor !== "string" || !_FECHA.test(valor)) return false;
  const d = new Date(`${valor}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === valor && valor <= hoy();
}

function diasDelMes(fecha: string): number {
  const [a, m] = fecha.split("-").map(Number);
  return new Date(Date.UTC(a ?? 2026, m ?? 1, 0)).getUTCDate();
}

function primeroDelMes(fecha: string, atras = 0): string {
  const [a = 2026, m = 1] = fecha.split("-").map(Number);
  const d = new Date(Date.UTC(a, m - 1 - atras, 1));
  return d.toISOString().slice(0, 10);
}

function detalleDeCuenta(e: Estado, c: Cuenta) {
  const persona = e.personas.find((p) => p.id === c.personaId);
  return {
    cuenta_id: c.id,
    persona: { id: c.personaId, nombre: persona?.nombre ?? "" },
    deuda: texto(deudaDe(c)),
    unidades: c.unidades
      .map((uid) => e.unidades.find((u) => u.id === uid))
      .filter((u): u is Unidad => u !== undefined)
      .sort((x, y) => x.identificador.localeCompare(y.identificador))
      .map((u) => ({ id: u.id, identificador: u.identificador })),
    periodos: [...c.periodos]
      .sort((x, y) => x.periodo.localeCompare(y.periodo))
      .map((p) => ({
        periodo: p.periodo,
        componentes: Object.fromEntries(
          _PERIODOS_COMPONENTES
            .filter((n) => p.componentes[n] !== undefined)
            .map((n) => {
              const x = p.componentes[n] ?? { debe: 0, cobrado: 0 };
              return [
                n,
                {
                  debe: texto(x.debe),
                  cobrado: texto(x.cobrado),
                  pendiente: texto(x.debe - x.cobrado),
                },
              ];
            }),
        ),
      })),
    movimientos: c.movimientos.map((m) => ({
      id: m.id,
      tipo: m.tipo,
      sentido: m.sentido,
      importe: texto(m.importe),
      fecha: m.fecha,
    })),
  };
}

function padron(e: Estado, id: string) {
  return {
    unidades: e.unidades.map((u) => ({
      id: u.id,
      complejo_id: id,
      identificador: u.identificador,
      tipo: "departamento",
      piso: "1",
      coeficiente: "0.333333",
      superficie_m2: "60.00",
    })),
    informe: { suma: "0.999999", diferencia: "-0.000001", estado: "ok" },
  };
}

function cambioParaLista(c: Cambio) {
  const { aviso: _aviso, ...resto } = c as Record<string, unknown>;
  return resto;
}

/** Contrato de H-035: sólo con `?con_nombres=true`, el cambio suma `vendedores_detalle` (`persona_id` y `nombre`,
 * sin email, en el orden de `vendedores`); sin el parámetro la respuesta es la de H-030 a H-033, intacta. */
function conNombres<T extends Record<string, unknown>>(e: Estado, c: T, pedido: boolean): T {
  if (!pedido) return c;
  const ids = (c.vendedores as string[]) ?? [];
  return {
    ...c,
    vendedores_detalle: ids.map((id) => ({
      persona_id: id,
      nombre: e.personas.find((p) => p.id === id)?.nombre ?? "",
    })),
  };
}

function pideNombres(pedido: IncomingMessage): boolean {
  return new URL(pedido.url ?? "/", "http://falsa.test").searchParams.get("con_nombres") === "true";
}

function cobrar(c: Cuenta, importe: number): void {
  let falta = importe;
  const ordenados = [...c.periodos].sort((x, y) => x.periodo.localeCompare(y.periodo));
  for (const p of ordenados) {
    for (const n of _PERIODOS_COMPONENTES) {
      const x = p.componentes[n];
      if (!x || falta === 0) continue;
      const aplica = Math.min(falta, x.debe - x.cobrado);
      x.cobrado += aplica;
      falta -= aplica;
    }
  }
}

function cobro(
  respuesta: ServerResponse,
  e: Estado,
  c: Cuenta,
  cuerpo: unknown,
  identidad: string,
  id: string,
): void {
  if (!accionesDe(identidad).includes("confirmar_pago_informado")) {
    sinPermiso(respuesta, "confirmar_pago_informado");
    return;
  }
  const dato = cuerpo as Record<string, unknown> | null;
  if (
    dato === null ||
    typeof dato !== "object" ||
    Array.isArray(dato) ||
    Object.keys(dato).sort().join() !== "fecha,importe"
  ) {
    invalido(respuesta, "importe");
    return;
  }
  const importe = dato.importe;
  if (typeof importe !== "string" || !/^\d+(\.\d{1,2})?$/.test(importe) || centavos(importe) <= 0) {
    invalido(respuesta, "importe");
    return;
  }
  if (!fechaValida(dato.fecha)) {
    invalido(respuesta, "fecha");
    return;
  }
  const monto = centavos(importe);
  if (monto > deudaDe(c)) {
    invalido(respuesta, "importe");
    return;
  }
  cobrar(c, monto);
  // N02: la deuda de Luis tiene un centavo de desvío en la API y su cobro suma otro (el interés del día):
  // la deuda nueva NO es `deuda - importe`, y la pantalla muestra la que dice la API.
  if (c.desvio > 0) c.desvio += 1;
  e.contador += 1;
  c.movimientos.push({
    id: sub(4, e.k, e.contador),
    tipo: "pago",
    sentido: "credito",
    importe: monto,
    fecha: dato.fecha,
  });
  void id;
  json(respuesta, 201, detalleDeCuenta(e, c));
}

function registrar(
  respuesta: ServerResponse,
  e: Estado,
  id: string,
  unidad: Unidad,
  cuerpo: unknown,
  identidad: string,
  detalle: boolean,
): void {
  if (!accionesDe(identidad).includes("registrar_cambio_de_titular")) {
    sinPermiso(respuesta, "registrar_cambio_de_titular");
    return;
  }
  const dato = cuerpo as Record<string, unknown> | null;
  if (dato === null || typeof dato !== "object" || Array.isArray(dato)) {
    invalido(respuesta, "fecha");
    return;
  }
  if (!fechaValida(dato.fecha)) {
    invalido(respuesta, "fecha");
    return;
  }
  const fecha = dato.fecha;
  const expensa = dato.expensa_del_mes ?? "entera";
  const deuda = dato.deuda_previa ?? "en_la_unidad";
  if (expensa !== "entera" && expensa !== "prorrateo") {
    invalido(respuesta, "expensa_del_mes");
    return;
  }
  if (deuda !== "en_la_unidad" && deuda !== "a_nombre_del_vendedor") {
    invalido(respuesta, "deuda_previa");
    return;
  }
  const propietarios = e.asignaciones
    .filter((a) => a.unidadId === unidad.id && a.vinculo === "propietario")
    .map((a) => a.personaId);
  const vendedores = dato.vendedores;
  if (
    !Array.isArray(vendedores) ||
    vendedores.length === 0 ||
    new Set(vendedores).size !== vendedores.length ||
    !vendedores.every((v) => typeof v === "string" && propietarios.includes(v))
  ) {
    invalido(respuesta, "vendedores");
    return;
  }
  const compradores = dato.compradores;
  if (
    !Array.isArray(compradores) ||
    compradores.length === 0 ||
    !compradores.every(
      (c) =>
        c !== null &&
        typeof c === "object" &&
        typeof (c as { nombre?: unknown }).nombre === "string" &&
        (c as { nombre: string }).nombre.trim() !== "" &&
        ((c as { email?: unknown }).email === null ||
          (c as { email?: unknown }).email === undefined ||
          typeof (c as { email?: unknown }).email === "string"),
    )
  ) {
    invalido(respuesta, "compradores");
    return;
  }
  const pedidos = compradores as { nombre: string; email?: string | null }[];
  const mismoDeAmbosLados = pedidos.some((c) => {
    const previa = c.email ? e.personas.find((p) => p.email === c.email) : undefined;
    return previa !== undefined && (vendedores as string[]).includes(previa.id);
  });
  if (mismoDeAmbosLados) {
    invalido(respuesta, "compradores");
    return;
  }
  const hayDeudor = deuda === "a_nombre_del_vendedor" || expensa === "prorrateo";
  let deudor = dato.vendedor_deudor;
  if (hayDeudor) {
    if (deudor === undefined || deudor === null) {
      if (vendedores.length > 1) {
        invalido(respuesta, "vendedor_deudor");
        return;
      }
      deudor = vendedores[0];
    } else if (typeof deudor !== "string" || !(vendedores as string[]).includes(deudor)) {
      invalido(respuesta, "vendedor_deudor");
      return;
    }
  }
  const mes = primeroDelMes(fecha);
  if (
    expensa === "prorrateo" &&
    e.cambios.some(
      (c) =>
        c.unidad_id === unidad.id &&
        (c.prorrateo as { periodo?: string } | undefined)?.periodo === mes,
    )
  ) {
    invalido(respuesta, "expensa_del_mes");
    return;
  }

  // Todo en orden: efectos.
  const resueltos = pedidos.map((c) => {
    const previa = c.email ? e.personas.find((p) => p.email === c.email) : undefined;
    if (previa) return previa;
    e.contador += 1;
    const nueva: Persona = {
      id: sub(2, e.k, e.contador),
      nombre: c.nombre.trim(),
      email: c.email ?? null,
    };
    e.personas.push(nueva);
    return nueva;
  });
  e.asignaciones = e.asignaciones.filter(
    (a) =>
      !(
        a.unidadId === unidad.id &&
        a.vinculo === "propietario" &&
        (vendedores as string[]).includes(a.personaId)
      ),
  );
  for (const r of resueltos)
    e.asignaciones.push({ personaId: r.id, unidadId: unidad.id, vinculo: "propietario" });

  const cuentaDe = (personaId: string): Cuenta => {
    const hecha = e.cuentas.find((c) => c.personaId === personaId);
    if (hecha) return hecha;
    e.contador += 1;
    const nueva: Cuenta = {
      id: sub(3, e.k, e.contador),
      personaId,
      unidades: [],
      periodos: [],
      movimientos: [],
      desvio: 0,
    };
    e.cuentas.push(nueva);
    return nueva;
  };
  const sumar = (c: Cuenta, mesDelPeriodo: string, importe: number): void => {
    c.periodos.push(periodo(mesDelPeriodo, { ordinaria: importe }));
    e.contador += 1;
    c.movimientos.push({
      id: sub(4, e.k, e.contador),
      tipo: "traslado",
      sentido: "debito",
      importe,
      fecha,
    });
    if (!c.unidades.includes(unidad.id)) c.unidades.push(unidad.id);
  };

  let trasladado: string | undefined;
  let cuentaDelVendedor: string | undefined;
  if (deuda === "a_nombre_del_vendedor") {
    const c = cuentaDe(deudor as string);
    cuentaDelVendedor = c.id;
    if (unidad.deuda > 0) {
      sumar(c, primeroDelMes(fecha, 1), unidad.deuda);
      trasladado = texto(unidad.deuda);
      unidad.deuda = 0;
    } else {
      trasladado = "0.00";
      cuentaDelVendedor = undefined;
    }
  }
  let prorrateo: Record<string, unknown> | undefined;
  if (expensa === "prorrateo") {
    const dias = Number(fecha.slice(8, 10)) - 1;
    const aplicado = e.k === 4;
    prorrateo = {
      estado: aplicado ? "aplicado" : "pendiente",
      periodo: mes,
      dias_del_vendedor: dias,
      dias_del_mes: diasDelMes(fecha),
      parte_del_vendedor: aplicado ? "8333.33" : null,
    };
    if (aplicado) sumar(cuentaDe(deudor as string), mes, 833333);
  }
  e.contador += 1;
  const nuevo: Cambio = {
    id: sub(4, e.k, e.contador),
    unidad_id: unidad.id,
    fecha,
    vendedores,
    compradores: resueltos.map((r) => ({ nombre: r.nombre, email: r.email, persona_id: r.id })),
    expensa_del_mes: expensa,
    deuda_previa: deuda,
    registrado_por: sub(2, e.k, 90),
    registrado_en: new Date().toISOString(),
    ...(trasladado !== undefined ? { trasladado } : {}),
    ...(deuda === "a_nombre_del_vendedor"
      ? { cuenta_del_vendedor: cuentaDelVendedor ?? null }
      : {}),
    ...(prorrateo ? { prorrateo } : {}),
  } as Cambio;
  e.cambios.unshift(nuevo);
  void id;
  json(respuesta, 201, {
    ...conNombres(e, nuevo, detalle),
    aviso: unidad.deuda > 0 ? { deuda: texto(unidad.deuda) } : null,
  });
}

/**
 * Contesta las rutas del contrato de H-034 de los seis edificios. Devuelve `false` si no es de su
 * incumbencia (otro recurso, que contesta la API falsa como a cualquier edificio).
 */
export function responderTitularidad(
  pedido: IncomingMessage,
  respuesta: ServerResponse,
  id: string,
  resto: string,
  identidad: string,
): boolean {
  const e = estadoDe(id);
  const metodo = pedido.method ?? "GET";
  if (resto === "unidades" && metodo === "GET") {
    json(respuesta, 200, padron(e, id));
    return true;
  }
  const dePropietarios = /^unidades\/([^/]+)\/propietarios$/.exec(resto);
  if (dePropietarios) {
    // H-035: los propietarios actuales de la unidad, por nombre y sin más datos que el id (la real los lee de
    // `asignacion_rol` con el permiso `registrar_cambio_de_titular`; `/api/personal` no trae vecinos).
    const unidad = e.unidades.find((u) => u.id === dePropietarios[1]);
    if (!unidad) {
      json(respuesta, 404, { detail: "no encontrado" });
      return true;
    }
    if (!accionesDe(identidad).includes("registrar_cambio_de_titular")) {
      sinPermiso(respuesta, "registrar_cambio_de_titular");
      return true;
    }
    if (metodo !== "GET") {
      respuesta.writeHead(405).end();
      return true;
    }
    const propietarios = e.asignaciones
      .filter((a) => a.unidadId === unidad.id && a.vinculo === "propietario")
      .map((a) => e.personas.find((p) => p.id === a.personaId))
      .filter((p): p is Persona => p !== undefined)
      .sort((x, y) => x.nombre.localeCompare(y.nombre))
      .map((p) => ({ persona_id: p.id, nombre: p.nombre }));
    json(respuesta, 200, { propietarios });
    return true;
  }
  const deCambios = /^unidades\/([^/]+)\/cambios-de-titular$/.exec(resto);
  if (deCambios) {
    const unidad = e.unidades.find((u) => u.id === deCambios[1]);
    if (!unidad) {
      json(respuesta, 404, { detail: "no encontrado" });
      return true;
    }
    if (!accionesDe(identidad).includes("registrar_cambio_de_titular")) {
      sinPermiso(respuesta, "registrar_cambio_de_titular");
      return true;
    }
    if (metodo === "GET") {
      const conDetalle = pideNombres(pedido);
      json(
        respuesta,
        200,
        e.cambios
          .filter((c) => c.unidad_id === unidad.id)
          .map((c) => conNombres(e, cambioParaLista(c), conDetalle)),
      );
      return true;
    }
    if (metodo === "POST") {
      leerCuerpo(pedido, (cuerpo) =>
        registrar(respuesta, e, id, unidad, cuerpo, identidad, pideNombres(pedido)),
      );
      return true;
    }
    respuesta.writeHead(405).end();
    return true;
  }
  const deCuentas = /^cuentas-de-vendedores(?:\/([^/]+)(\/cobros)?)?$/.exec(resto);
  if (deCuentas) {
    const acciones = accionesDe(identidad);
    const cuentaId = deCuentas[1];
    const esCobro = deCuentas[2] !== undefined;
    const permiso = esCobro ? "confirmar_pago_informado" : "ver_morosidad";
    if (!acciones.includes(permiso)) {
      sinPermiso(respuesta, permiso);
      return true;
    }
    if (cuentaId === undefined) {
      if (metodo !== "GET") {
        respuesta.writeHead(405).end();
        return true;
      }
      const cuentas = [...e.cuentas].sort((x, y) => deudaDe(y) - deudaDe(x));
      json(respuesta, 200, {
        cuentas: cuentas.map((c) => {
          const { cuenta_id, persona, deuda, unidades } = detalleDeCuenta(e, c);
          return { cuenta_id, persona, deuda, unidades };
        }),
      });
      return true;
    }
    const cuenta = e.cuentas.find((c) => c.id === cuentaId);
    if (!cuenta) {
      json(respuesta, 404, { detail: "no encontrado" });
      return true;
    }
    if (esCobro) {
      if (metodo !== "POST") {
        respuesta.writeHead(405).end();
        return true;
      }
      leerCuerpo(pedido, (cuerpo) => cobro(respuesta, e, cuenta, cuerpo, identidad, id));
      return true;
    }
    if (metodo !== "GET") {
      respuesta.writeHead(405).end();
      return true;
    }
    json(respuesta, 200, detalleDeCuenta(e, cuenta));
    return true;
  }
  return false;
}

/** Los ids que la aceptación usa para llegar a cada fila (los de la semilla). */
export const IDS_DE_SEMILLA = {
  unidad1A: (k: number) => sub(1, k, 1),
  unidad1B: (k: number) => sub(1, k, 2),
  unidad2A: (k: number) => sub(1, k, 3),
  cuentaAna: (k: number) => sub(3, k, 1),
  cuentaLuis: (k: number) => sub(3, k, 2),
  cuentaPedro: (k: number) => sub(3, k, 3),
};
