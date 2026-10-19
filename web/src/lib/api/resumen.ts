/**
 * Resumen del edificio (D5, tareas 4.1 y 4.2): el checklist de puesta a
 * punto y "listo para liquidar" viven en la API, nunca calculados acá.
 * `informe.suma`/`informe.diferencia` son plata (D2): si no son texto
 * decimal ASCII, el resultado es `fallo`, nunca un `ok` con un valor que
 * la pantalla no podría mostrar.
 */

import { pedirApi, type ResultadoApi } from "./cliente";
import type { Resumen } from "./tipos";

export async function resumenDelEdificio(id: string): Promise<ResultadoApi<Resumen>> {
  return pedirApi<Resumen>(`/api/complejos/${id}/resumen`, {
    camposDePlata: ["informe.suma", "informe.diferencia"],
  });
}
