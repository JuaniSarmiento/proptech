/**
 * Configuración vigente del edificio (tarea 4.2). Sin `camposDePlata`: un
 * edificio sin configuración todavía da `null` LEGÍTIMO (cliente.test.ts ya
 * lo prueba sobre esta misma ruta), y el camino de un campo de plata sobre
 * un objeto `null` daría `fallo` por error, no por un dato roto.
 */

import { esIdValido, pedirApi, type ResultadoApi } from "./cliente";
import type { ConfiguracionVigente, VersionDelHistorial } from "./tipos";

export async function configuracionVigente(
  id: string,
): Promise<ResultadoApi<ConfiguracionVigente>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<ConfiguracionVigente>(`/api/complejos/${encodeURIComponent(id)}/configuracion`);
}

/**
 * Historial de versiones (D5, tarea 4.6): `autor_nombre` viene de la API
 * (`JOIN persona`), nunca calculado acá. Sin `camposDePlata`: es un
 * arreglo, igual que `grupos.ts`/`categorias.ts` (D2).
 */
export async function versionesDeConfiguracion(
  id: string,
): Promise<ResultadoApi<VersionDelHistorial[]>> {
  if (!esIdValido(id)) {
    return { estado: "no_existe" };
  }
  return pedirApi<VersionDelHistorial[]>(
    `/api/complejos/${encodeURIComponent(id)}/configuracion/versiones`,
  );
}

export type DatosNuevaVersion = {
  tasa_mensual: string;
  dias_de_gracia: number;
  forma_de_calculo: string;
  porcentaje_fondo: string;
  dia_de_vencimiento: number;
  modalidad_de_vencimiento: string;
  dia_segundo_vencimiento: number | null;
  recargo_segundo_vencimiento: string | null;
  vigente_desde: string;
};

/** Crea una versión nueva; la anterior no se borra (D11, shape §5). La
 * validación de "rige desde hoy en Mendoza o después" la hace la API
 * (422 en `vigente_desde`): la web nunca calcula "hoy" (D-ficha 4.6). */
export async function crearVersionDeConfiguracion(
  complejoId: string,
  datos: DatosNuevaVersion,
): Promise<ResultadoApi<{ id: string }>> {
  if (!esIdValido(complejoId)) {
    return { estado: "no_existe" };
  }
  return pedirApi<{ id: string }>(
    `/api/complejos/${encodeURIComponent(complejoId)}/configuracion/versiones`,
    { metodo: "POST", cuerpo: datos },
  );
}
