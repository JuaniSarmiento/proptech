"use client";

/**
 * Error de carga del servidor con "Reintentar" (D1, tarea 4.1): la carga
 * real pasa por el componente de servidor de cada pantalla; "Reintentar"
 * sólo le pide a Next que vuelva a correrlo (`router.refresh()`), sin
 * mantener estado de carga propio.
 */

import { useRouter } from "next/navigation";
import { Estados } from "./Estados";

type Props = {
  mensaje: string;
};

export function ErrorDePantalla({ mensaje }: Props) {
  const router = useRouter();
  return <Estados tipo="error" mensaje={mensaje} onReintentar={() => router.refresh()} />;
}
