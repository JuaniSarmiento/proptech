/**
 * Vocabulario cerrado de `estado_migracion` (D5, tarea 4.1), traducido a
 * castellano simple para la lista de edificios y el resumen.
 */
export function textoEstadoDeMigracion(valor: string): string {
  if (valor === "pendiente") {
    return "Pendiente de confirmar saldos previos";
  }
  if (valor === "sin_saldos_previos") {
    return "Confirmado: arranca sin saldos previos";
  }
  return "Estado de migración desconocido";
}
