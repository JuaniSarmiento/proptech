/**
 * El cambio de titular y las cuentas de vendedores (change 4d, H-034): las lecturas y escrituras de
 * H-030 a H-033. La pantalla sólo formatea: cada monto llega como texto con dos decimales y se muestra
 * tal cual, nunca sumado ni redondeado (R07, D-046). El texto de un 422 de la API nunca llega a la
 * pantalla (L-007): quien llama traduce por campo.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";

export type CompradorDelCambio = { nombre: string; email: string | null; persona_id: string };

export type ProrrateoDelCambio = {
  estado: "pendiente" | "aplicado";
  periodo: string;
  dias_del_vendedor: number;
  dias_del_mes: number;
  parte_del_vendedor: string | null;
};

export type CambioDeTitular = {
  id: string;
  unidad_id: string;
  fecha: string;
  vendedores: string[];
  /** Con `con_nombres=true` (H-035): los vendedores con su nombre, en el orden de `vendedores`. */
  vendedores_detalle?: { persona_id: string; nombre: string }[];
  compradores: CompradorDelCambio[];
  expensa_del_mes: "entera" | "prorrateo";
  deuda_previa: "en_la_unidad" | "a_nombre_del_vendedor";
  trasladado?: string;
  cuenta_del_vendedor?: string | null;
  prorrateo?: ProrrateoDelCambio;
};

export type CambioRegistrado = CambioDeTitular & { aviso: { deuda: string } | null };

export type PedidoDeCambio = {
  fecha: string;
  vendedores: string[];
  compradores: { nombre: string; email: string | null }[];
  expensa_del_mes: "entera" | "prorrateo";
  deuda_previa: "en_la_unidad" | "a_nombre_del_vendedor";
  vendedor_deudor?: string;
};

export type ComponenteDeCuenta = "interes" | "ordinaria" | "fondo_de_reserva" | "extraordinaria";

export type CuentaDeVendedor = {
  cuenta_id: string;
  persona: { id: string; nombre: string };
  deuda: string;
  unidades: { id: string; identificador: string }[];
};

export type DetalleDeCuenta = CuentaDeVendedor & {
  periodos: {
    periodo: string;
    componentes: Partial<
      Record<ComponenteDeCuenta, { debe: string; cobrado: string; pendiente: string }>
    >;
  }[];
  movimientos: { id: string; tipo: string; sentido: string; importe: string; fecha: string }[];
};

const _MONTO = /^-?[0-9]+\.[0-9]{2}$/;
const _FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

function esMonto(valor: unknown): valor is string {
  return typeof valor === "string" && _MONTO.test(valor);
}

function esFecha(valor: unknown): valor is string {
  return typeof valor === "string" && _FECHA.test(valor);
}

function esRegistro(valor: unknown): valor is Record<string, unknown> {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor);
}

function prorrateoValido(valor: unknown): boolean {
  if (!esRegistro(valor)) return false;
  return (
    (valor.estado === "pendiente" || valor.estado === "aplicado") &&
    esFecha(valor.periodo) &&
    Number.isInteger(valor.dias_del_vendedor) &&
    Number.isInteger(valor.dias_del_mes) &&
    (valor.parte_del_vendedor === null || esMonto(valor.parte_del_vendedor))
  );
}

function cambioValido(valor: unknown): valor is CambioDeTitular {
  if (!esRegistro(valor)) return false;
  return (
    typeof valor.id === "string" &&
    esFecha(valor.fecha) &&
    Array.isArray(valor.vendedores) &&
    valor.vendedores.every((v) => typeof v === "string") &&
    Array.isArray(valor.compradores) &&
    valor.compradores.every((c) => esRegistro(c) && typeof c.nombre === "string") &&
    (valor.expensa_del_mes === "entera" || valor.expensa_del_mes === "prorrateo") &&
    (valor.deuda_previa === "en_la_unidad" || valor.deuda_previa === "a_nombre_del_vendedor") &&
    (valor.vendedores_detalle === undefined ||
      (Array.isArray(valor.vendedores_detalle) &&
        valor.vendedores_detalle.every(
          (v) => esRegistro(v) && typeof v.persona_id === "string" && typeof v.nombre === "string",
        ))) &&
    (valor.trasladado === undefined || esMonto(valor.trasladado)) &&
    (valor.prorrateo === undefined || prorrateoValido(valor.prorrateo))
  );
}

function cuentaValida(valor: unknown): valor is CuentaDeVendedor {
  if (!esRegistro(valor)) return false;
  return (
    typeof valor.cuenta_id === "string" &&
    esRegistro(valor.persona) &&
    typeof valor.persona.nombre === "string" &&
    esMonto(valor.deuda) &&
    Array.isArray(valor.unidades) &&
    valor.unidades.every((u) => esRegistro(u) && typeof u.identificador === "string")
  );
}

function detalleValido(valor: unknown): valor is DetalleDeCuenta {
  if (!cuentaValida(valor)) return false;
  const d = valor as unknown as Record<string, unknown>;
  return (
    Array.isArray(d.periodos) &&
    d.periodos.every(
      (p) =>
        esRegistro(p) &&
        esFecha(p.periodo) &&
        esRegistro(p.componentes) &&
        Object.values(p.componentes).every(
          (c) => esRegistro(c) && esMonto(c.debe) && esMonto(c.cobrado) && esMonto(c.pendiente),
        ),
    ) &&
    Array.isArray(d.movimientos) &&
    d.movimientos.every(
      (m) => esRegistro(m) && typeof m.tipo === "string" && esMonto(m.importe) && esFecha(m.fecha),
    )
  );
}

function rutaDeCambios(id: string, unidadId: string): string {
  return `/api/complejos/${encodeURIComponent(id)}/unidades/${encodeURIComponent(unidadId)}/cambios-de-titular`;
}

/** Los cambios de titular de una unidad, el más nuevo primero (H-030). */
export async function cambiosDeUnaUnidad(
  id: string,
  unidadId: string,
): Promise<ResultadoApi<CambioDeTitular[]>> {
  if (!esIdValido(id) || !esIdValido(unidadId)) return { estado: "no_existe" };
  const resultado = await pedirApi<CambioDeTitular[]>(
    `${rutaDeCambios(id, unidadId)}?con_nombres=true`,
  );
  if (resultado.estado !== "ok") return resultado;
  return Array.isArray(resultado.datos) && resultado.datos.every(cambioValido)
    ? resultado
    : { estado: "fallo" };
}

export type PropietarioDeUnidad = { persona_id: string; nombre: string };

/** Los propietarios actuales de la unidad, por nombre (H-035); no pasa por `/api/personal`. */
export async function propietariosDeUnaUnidad(
  id: string,
  unidadId: string,
): Promise<ResultadoApi<PropietarioDeUnidad[]>> {
  if (!esIdValido(id) || !esIdValido(unidadId)) return { estado: "no_existe" };
  const resultado = await pedirApi<{ propietarios: PropietarioDeUnidad[] }>(
    `/api/complejos/${encodeURIComponent(id)}/unidades/${encodeURIComponent(unidadId)}/propietarios`,
  );
  if (resultado.estado !== "ok") return resultado;
  const lista = resultado.datos?.propietarios;
  return Array.isArray(lista) &&
    lista.every(
      (p) => esRegistro(p) && typeof p.persona_id === "string" && typeof p.nombre === "string",
    )
    ? { estado: "ok", datos: lista }
    : { estado: "fallo" };
}

/** Registra el cambio (H-030 a H-032). Sólo viajan las claves del contrato. */
export async function registrarCambioDeTitular(
  id: string,
  unidadId: string,
  pedido: PedidoDeCambio,
): Promise<ResultadoApi<CambioRegistrado>> {
  if (!esIdValido(id) || !esIdValido(unidadId)) return { estado: "no_existe" };
  const resultado = await pedirApi<CambioRegistrado>(rutaDeCambios(id, unidadId), {
    metodo: "POST",
    cuerpo: {
      fecha: pedido.fecha,
      vendedores: pedido.vendedores,
      compradores: pedido.compradores.map((c) => ({ nombre: c.nombre, email: c.email })),
      expensa_del_mes: pedido.expensa_del_mes,
      deuda_previa: pedido.deuda_previa,
      ...(pedido.vendedor_deudor ? { vendedor_deudor: pedido.vendedor_deudor } : {}),
    },
  });
  if (resultado.estado !== "ok") return resultado;
  const { datos } = resultado;
  const avisoBien =
    datos.aviso === null ||
    (esRegistro(datos.aviso) && esMonto((datos.aviso as { deuda: unknown }).deuda));
  return cambioValido(datos) && avisoBien ? resultado : { estado: "fallo" };
}

export type ListaDeCuentas = { cuentas: CuentaDeVendedor[] };

/** Las cuentas de los vendedores del edificio, en el orden de la API (H-033). */
export async function cuentasDeVendedores(id: string): Promise<ResultadoApi<ListaDeCuentas>> {
  if (!esIdValido(id)) return { estado: "no_existe" };
  const resultado = await pedirApi<ListaDeCuentas>(
    `/api/complejos/${encodeURIComponent(id)}/cuentas-de-vendedores`,
  );
  if (resultado.estado !== "ok") return resultado;
  return Array.isArray(resultado.datos?.cuentas) && resultado.datos.cuentas.every(cuentaValida)
    ? resultado
    : { estado: "fallo" };
}

function rutaDeCuenta(id: string, cuentaId: string): string {
  return `/api/complejos/${encodeURIComponent(id)}/cuentas-de-vendedores/${encodeURIComponent(cuentaId)}`;
}

/** El detalle de una cuenta: deuda, períodos y movimientos (H-033). */
export async function cuentaDeVendedor(
  id: string,
  cuentaId: string,
): Promise<ResultadoApi<DetalleDeCuenta>> {
  if (!esIdValido(id) || !esIdValido(cuentaId)) return { estado: "no_existe" };
  const resultado = await pedirApi<DetalleDeCuenta>(rutaDeCuenta(id, cuentaId));
  if (resultado.estado !== "ok") return resultado;
  return detalleValido(resultado.datos) ? resultado : { estado: "fallo" };
}

/** Registra el cobro (`importe` y `fecha`, nada más) y devuelve el detalle ya actualizado (H-033). */
export async function registrarCobroDeVendedor(
  id: string,
  cuentaId: string,
  pedido: { importe: string; fecha: string },
): Promise<ResultadoApi<DetalleDeCuenta>> {
  if (!esIdValido(id) || !esIdValido(cuentaId)) return { estado: "no_existe" };
  const resultado = await pedirApi<DetalleDeCuenta>(`${rutaDeCuenta(id, cuentaId)}/cobros`, {
    metodo: "POST",
    cuerpo: { importe: pedido.importe, fecha: pedido.fecha },
  });
  if (resultado.estado !== "ok") return resultado;
  return detalleValido(resultado.datos) ? resultado : { estado: "fallo" };
}
