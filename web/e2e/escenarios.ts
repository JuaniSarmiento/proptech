/**
 * Estados a pedido de la API falsa, sin tocar código (D7, tarea 3.8): un
 * UUID fijo por estado. Entrar a `/edificios/<id>` en el navegador real
 * muestra ese estado; la misma lista alimenta las pruebas generadas por
 * pantalla en 5.1 (L-022): no se escribe un UUID por prueba a mano.
 *
 * UUIDs secuenciales a propósito (no al azar): `grep` de un id en un fallo
 * de Playwright dice de una qué escenario es.
 */

export type ClaveDeEscenario =
  | "vacio"
  | "lento"
  | "error_500"
  | "sin_permiso_403"
  | "no_existe_404"
  | "sin_sesion_401"
  | "advertencia"
  | "fuera_de_tolerancia"
  | "doscientas_unidades"
  | "nombres_largos";

export type Escenario = {
  clave: ClaveDeEscenario;
  id: string;
  descripcion: string;
};

export const ESCENARIOS: Escenario[] = [
  { clave: "vacio", id: "00000000-0000-0000-0000-000000000001", descripcion: "sin unidades" },
  { clave: "lento", id: "00000000-0000-0000-0000-000000000002", descripcion: "responde a los 3s" },
  {
    clave: "error_500",
    id: "00000000-0000-0000-0000-000000000003",
    descripcion: "500 con texto técnico",
  },
  {
    clave: "sin_permiso_403",
    id: "00000000-0000-0000-0000-000000000004",
    descripcion: "403, colaborador sin permiso",
  },
  {
    clave: "no_existe_404",
    id: "00000000-0000-0000-0000-000000000005",
    descripcion: "404, de otra administración",
  },
  {
    clave: "sin_sesion_401",
    id: "00000000-0000-0000-0000-000000000006",
    descripcion: "401, sin sesión",
  },
  {
    clave: "advertencia",
    id: "00000000-0000-0000-0000-000000000007",
    descripcion: "coeficientes en advertencia (0,9999)",
  },
  {
    clave: "fuera_de_tolerancia",
    id: "00000000-0000-0000-0000-000000000008",
    descripcion: "coeficientes fuera de tolerancia (-0,0002)",
  },
  {
    clave: "doscientas_unidades",
    id: "00000000-0000-0000-0000-000000000009",
    descripcion: "200 unidades en el padrón",
  },
  {
    clave: "nombres_largos",
    id: "00000000-0000-0000-0000-000000000010",
    descripcion: "nombre de edificio de 200 caracteres, identificador de 40",
  },
];

export function escenarioPorId(id: string): Escenario | undefined {
  return ESCENARIOS.find((escenario) => escenario.id === id);
}
