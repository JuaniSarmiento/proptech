"use client";
import { createContext, type ReactNode, useContext } from "react";
export type DatosDeSesion = {
  persona: { nombre: string };
  administraciones: { id: string; nombre: string }[];
};
type SesionVisible = { datos: DatosDeSesion; administracionId?: string };
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
