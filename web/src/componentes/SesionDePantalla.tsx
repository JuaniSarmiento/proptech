"use client";
import { createContext, type ReactNode, useContext } from "react";

/**
 * D11 (2d, 7.5/7.6): lo que calcula `acciones_permitidas` en la API, tal
 * cual llega por `GET /api/sesion`. `administracion` son las acciones de
 * toda la administración (coinciden con o sin `complejoId`, R2D-1);
 * `todos_los_edificios`, las de edificio que una asignación principal
 * permite en cualquiera; `por_edificio`, las que suma por cada edificio con
 * asignación propia.
 */
export type AccionesDeSesion = {
  administracion: string[];
  todos_los_edificios: string[];
  por_edificio: Record<string, string[]>;
};

export type DatosDeSesion = {
  persona: { nombre: string };
  administraciones: { id: string; nombre: string; acciones: AccionesDeSesion }[];
};
export type SesionVisible = { datos: DatosDeSesion; administracionId?: string };
const Contexto = createContext<SesionVisible | null>(null);
export function SesionDePantalla({
  value,
  children,
}: {
  value: SesionVisible | null;
  children: ReactNode;
}) {
  return <Contexto.Provider value={value}>{children}</Contexto.Provider>;
}
export function useSesionDePantalla() {
  return useContext(Contexto);
}

/**
 * D11: el mismo contrato que `puede` en la API, visto desde la web — nunca
 * una copia de la matriz, sólo la lectura de lo que la sesión ya trae. Para
 * una acción de administración da lo mismo con o sin `complejoId`; para una
 * de edificio, sin `complejoId` da `false`. Sin sesión en el contexto, o
 * sin la administración elegida en la lista, da `false`: la escritura se
 * oculta, nunca se muestra de más (D11, "El control oculto pedido a mano"
 * sigue frenado por la API igual).
 */
export function permite(
  sesion: SesionVisible | null,
  accion: string,
  complejoId?: string,
): boolean {
  const administracion = sesion?.datos.administraciones.find(
    (a) => a.id === sesion.administracionId,
  );
  if (!administracion) return false;
  const { acciones } = administracion;
  if (acciones.administracion.includes(accion)) return true;
  if (!complejoId) return false;
  return (
    acciones.todos_los_edificios.includes(accion) ||
    (acciones.por_edificio[complejoId] ?? []).includes(accion)
  );
}
