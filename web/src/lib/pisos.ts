/**
 * D3 (tarea 6.2): el mismo vocabulario de pisos que el backend
 * (`backend/src/proptech_core/compartido/pisos.py`, tarea 3.1): `PB`
 * siempre, `SS1..SS<subsuelos>`, `1..<pisos>`. La web nunca valida contra
 * este vocabulario (eso es del servidor, L-047 es sobre límites/patrones
 * de ENTRADA; esto es sólo para armar las opciones de la lista).
 */

export function vocabularioDePisos(pisos: number, subsuelos: number): string[] {
  const opciones = ["PB"];
  for (let n = 1; n <= pisos; n++) {
    opciones.push(String(n));
  }
  for (let n = 1; n <= subsuelos; n++) {
    opciones.push(`SS${n}`);
  }
  return opciones;
}
