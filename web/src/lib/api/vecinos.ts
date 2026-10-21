/**
 * Vecinos del padrón (7.4), funciones puras sin dependencia del servidor:
 * a diferencia de `personal.ts`, este archivo lo importa un componente de
 * CLIENTE (`unidades/Pantalla.tsx`) por valor, no sólo por tipo — si
 * importara `pedirApi`/`sesion.ts`, arrastraría `server-only` al cliente
 * (gotcha real, visto en `vitest`: "Failed to resolve import server-only").
 */
import type { Persona } from "./personal";

export type VecinoDeUnidad = {
  persona_id: string;
  asignacion_id: string;
  nombre: string;
  vinculo: string;
  invitacion: { invitacion_id: string; estado: string } | null;
};

export function vecinosPorUnidad(personas: Persona[]): Map<string, VecinoDeUnidad[]> {
  const mapa = new Map<string, VecinoDeUnidad[]>();
  for (const persona of personas) {
    for (const asignacion of persona.asignaciones) {
      if (asignacion.rol !== "vecino" || !asignacion.unidad_id) continue;
      const lista = mapa.get(asignacion.unidad_id) ?? [];
      lista.push({
        persona_id: persona.persona_id,
        asignacion_id: asignacion.asignacion_id,
        nombre: persona.nombre,
        vinculo: asignacion.vinculo ?? "propietario",
        invitacion: persona.invitacion,
      });
      mapa.set(asignacion.unidad_id, lista);
    }
  }
  return mapa;
}

export function etiquetaDeVinculo(vinculo: string): string {
  return vinculo === "inquilino" ? "Inquilino" : "Propietario";
}
