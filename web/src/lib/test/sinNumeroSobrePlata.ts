/**
 * Barrido de `web/src` (D6, tarea 3.2, L-019): ningún archivo que importe
 * `lib/formato` o el cliente de la API (`lib/api`, todavía por nacer en
 * 3.3) usa `Number(`, `parseFloat` ni `Intl.NumberFormat` — los tres
 * pierden lo que el texto decimal de la API no pierde.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const _PATRONES_PROHIBIDOS = [/\bNumber\(/, /\bparseFloat\(/, /\bIntl\.NumberFormat\b/];
const _IMPORTA_FORMATO_O_API = /from\s+["'][^"']*\/(formato|api)(\/[^"']*)?["']/;

function archivosTs(raiz: string): string[] {
  const resultado: string[] = [];
  for (const nombre of readdirSync(raiz)) {
    const ruta = join(raiz, nombre);
    const info = statSync(ruta);
    if (info.isDirectory()) {
      resultado.push(...archivosTs(ruta));
    } else if (/\.tsx?$/.test(nombre) && !/\.test\.tsx?$/.test(nombre)) {
      // Los tests quedan afuera (D6 es sobre código de producción): sin
      // esto, este mismo archivo se marcaría a sí mismo, por traer los
      // patrones prohibidos como texto dentro de sus propios fixtures.
      resultado.push(ruta);
    }
  }
  return resultado;
}

/** Devuelve los archivos de `raiz` que importan `formato` o `api` y
 * contienen algún patrón prohibido. Vacío cuando el árbol está limpio. */
export function archivosConNumeroSobrePlata(raiz: string): string[] {
  const ofensores: string[] = [];
  for (const archivo of archivosTs(raiz)) {
    const contenido = readFileSync(archivo, "utf-8");
    if (!_IMPORTA_FORMATO_O_API.test(contenido)) {
      continue;
    }
    if (_PATRONES_PROHIBIDOS.some((patron) => patron.test(contenido))) {
      ofensores.push(archivo);
    }
  }
  return ofensores;
}
