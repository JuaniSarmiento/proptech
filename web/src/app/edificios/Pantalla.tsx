"use client";

/**
 * "Mis edificios" (tarea 4.1, D5, D11): lista con nombre, localidad,
 * cantidad de unidades y estado de coeficientes/migración en texto, leídos
 * del resumen de cada edificio en el servidor (`page.tsx`). "Nuevo
 * edificio" abre el panel lateral; con un solo edificio la lista se
 * muestra igual (D11, no entra directo).
 */

import { useActionState, useRef, useState } from "react";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../componentes/EstadoDeCoeficientes";
import { Estados } from "../../componentes/Estados";
import { Campo, Formulario } from "../../componentes/Formulario";
import { PanelLateral } from "../../componentes/PanelLateral";
import { textoEstadoDeMigracion } from "../../lib/textoDeEstados";
import { AYUDA_MIS_EDIFICIOS } from "./ayuda";

export type EdificioConEstado = {
  id: string;
  nombre: string;
  localidad: string;
  cantidadUnidades: number | null;
  estadoCoeficientes: string | null;
  diferencia: string | null;
  estadoMigracion: string | null;
};

export type EstadoCrearEdificio = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
} | null;

type Props = {
  edificios: EdificioConEstado[];
  accionCrear: (
    estadoPrevio: EstadoCrearEdificio,
    formData: FormData,
  ) => Promise<EstadoCrearEdificio>;
};

export function PantallaMisEdificios({ edificios, accionCrear }: Props) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const botonNuevoRef = useRef<HTMLButtonElement>(null);
  const botonNuevoVacioRef = useRef<HTMLButtonElement>(null);
  const [estado, enviar] = useActionState(accionCrear, null);

  return (
    <main className="pantalla-mis-edificios">
      <EncabezadoDePantalla
        titulo="Mis edificios"
        ayuda={<Ayuda {...AYUDA_MIS_EDIFICIOS} />}
        accionPrincipal={
          <button
            ref={botonNuevoRef}
            type="button"
            className="boton-principal"
            onClick={() => setPanelAbierto(true)}
          >
            Nuevo edificio
          </button>
        }
      />

      {edificios.length === 0 ? (
        <Estados
          tipo="vacio"
          mensaje="Todavía no tenés edificios"
          accion={
            <button
              ref={botonNuevoVacioRef}
              type="button"
              className="boton-principal"
              onClick={() => setPanelAbierto(true)}
            >
              Nuevo edificio
            </button>
          }
        />
      ) : (
        <ul className="lista-de-edificios" aria-label="Edificios">
          {edificios.map((edificio) => (
            <li key={edificio.id} className="lista-de-edificios__fila">
              <a href={`/edificios/${edificio.id}`}>
                <span className="lista-de-edificios__nombre">{edificio.nombre}</span>
                <span className="lista-de-edificios__localidad">{edificio.localidad}</span>
                <span className="numero-tabular">{edificio.cantidadUnidades ?? "—"} unidades</span>
                {edificio.estadoCoeficientes && edificio.diferencia ? (
                  <EstadoDeCoeficientes
                    estado={edificio.estadoCoeficientes}
                    diferencia={edificio.diferencia}
                  />
                ) : (
                  <span>Coeficientes: sin datos</span>
                )}
                <span>
                  {edificio.estadoMigracion
                    ? textoEstadoDeMigracion(edificio.estadoMigracion)
                    : "Estado de migración: sin datos"}
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}

      <PanelLateral
        abierto={panelAbierto}
        titulo="Nuevo edificio"
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={edificios.length === 0 ? botonNuevoVacioRef : botonNuevoRef}
      >
        <Formulario
          erroresPorCampo={estado?.erroresPorCampo ?? {}}
          erroresDesconocidos={estado?.erroresDesconocidos ?? []}
          action={enviar}
        >
          <Campo nombre="nombre" etiqueta="Nombre" name="nombre" required />
          <Campo nombre="localidad" etiqueta="Localidad" name="localidad" required />
          <button type="submit" className="boton-principal">
            Crear edificio
          </button>
        </Formulario>
      </PanelLateral>
    </main>
  );
}
