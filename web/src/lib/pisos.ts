/**
 * D3 (tarea 6.2): el mismo conjunto de pisos que el backend
 * (`backend/src/proptech_core/compartido/pisos.py`, tarea 3.1): `PB`
 * siempre, `SS1..SS<subsuelos>`, `1..<pisos>` (el orden de la lista es el
 * de más abajo). La web nunca valida contra
 * este vocabulario (eso es del servidor, L-051 es sobre límites/patrones
 * de ENTRADA; esto es sólo para armar las opciones de la lista).
 *
 * pulido-2 (3d): la lista va en orden de altura, de abajo hacia arriba:
 * `SS<n>`..`SS1`, `PB`, `1`..`<pisos>`. `SS1` queda pegado a `PB`. El orden
 * es sólo de presentación; los valores válidos no cambian.
 */

export function vocabularioDePisos(pisos: number, subsuelos: number): string[] {
  const opciones: string[] = [];
  for (let n = subsuelos; n >= 1; n--) {
    opciones.push(`SS${n}`);
  }
  opciones.push("PB");
  for (let n = 1; n <= pisos; n++) {
    opciones.push(String(n));
  }
  return opciones;
}
