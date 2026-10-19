/**
 * Configuración vigente del edificio (tarea 4.2). Sin `camposDePlata`: un
 * edificio sin configuración todavía da `null` LEGÍTIMO (cliente.test.ts ya
 * lo prueba sobre esta misma ruta), y el camino de un campo de plata sobre
 * un objeto `null` daría `fallo` por error, no por un dato roto.
 */

import { pedirApi, type ResultadoApi } from "./cliente";
import type { ConfiguracionVigente } from "./tipos";

export async function configuracionVigente(
  id: string,
): Promise<ResultadoApi<ConfiguracionVigente>> {
  return pedirApi<ConfiguracionVigente>(`/api/complejos/${id}/configuracion`);
}
