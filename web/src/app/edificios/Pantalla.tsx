"use client";

/**
 * "Mis edificios" (tarea 4.1, D5, D11): lista con nombre, localidad,
 * cantidad de unidades y estado de coeficientes/migración en texto, leídos
 * del resumen de cada edificio en el servidor (`page.tsx`). "Nuevo
 * edificio" abre el panel lateral; con un solo edificio la lista se
 * muestra igual (D11, no entra directo).
 *
 * Enmienda del 20/10/2026: el armazón con barra superior y la lista a todo
 * el ancho en un panel, con más información por fila (cada dato con su
 * rótulo) y su ícono, como una lista de movimientos de home banking.
 */

import { Building2, ChevronRight } from "lucide-react";
import { useActionState, useRef, useState } from "react";
import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { BarraDeProgreso } from "../../componentes/BarraDeProgreso";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../componentes/EstadoDeCoeficientes";
import { Estados } from "../../componentes/Estados";
import { Campo, Formulario } from "../../componentes/Formulario";
import { MenuDelEdificio } from "../../componentes/MenuDelEdificio";
import { Panel } from "../../componentes/Panel";
import { PanelLateral } from "../../componentes/PanelLateral";
import { SelectorDeUbicacion } from "../../componentes/SelectorDeUbicacion";
import { permite, useSesionDePantalla } from "../../componentes/SesionDePantalla";
import { textoEstadoDeMigracion } from "../../lib/textoDeEstados";
import { seccionesDeLaAdministracion } from "../personal/secciones";
import { AYUDA_MIS_EDIFICIOS } from "./ayuda";

export type EdificioConEstado = {
  id: string;
  nombre: string;
  localidad: string | null;
  cantidadUnidades: number | null;
  estadoCoeficientes: string | null;
  diferencia: string | null;
  estadoMigracion: string | null;
  /** Pasos de la puesta a punto que la API ya marcó como hechos (un
   * conteo, nunca una regla de negocio) y si está listo para liquidar. */
  pasosHechos?: number | null;
  listoParaLiquidar?: boolean;
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
  const sesion = useSesionDePantalla();
  const puedeCrear = permite(sesion, "crear_edificio");
  const [panelAbierto, setPanelAbierto] = useState(false);
  const botonNuevoRef = useRef<HTMLButtonElement>(null);
  const botonNuevoVacioRef = useRef<HTMLButtonElement>(null);
  const [estado, enviar] = useActionState(accionCrear, null);

  return (
    <Armazon
      menu={
        <MenuDelEdificio
          seccionActual=""
          secciones={seccionesDeLaAdministracion(sesion)}
          nombreAccesible="Tu administración"
        />
      }
    >
      <EncabezadoDePantalla
        titulo="Mis edificios"
        ayuda={<Ayuda {...AYUDA_MIS_EDIFICIOS} />}
        accionPrincipal={
          puedeCrear ? (
            <button
              ref={botonNuevoRef}
              type="button"
              className="boton-principal"
              onClick={() => setPanelAbierto(true)}
            >
              Nuevo edificio
            </button>
          ) : undefined
        }
      />

      <Panel
        titulo="Tus edificios"
        descripcion="Entrá a un edificio para ver qué le falta antes de liquidar."
      >
        {edificios.length === 0 ? (
          <Estados
            tipo="vacio"
            mensaje="Todavía no tenés edificios"
            detalle="Creá el primero con su nombre y su localidad. Las unidades y lo demás se cargan adentro."
            accion={
              puedeCrear ? (
                <button
                  ref={botonNuevoVacioRef}
                  type="button"
                  className="boton-principal"
                  onClick={() => setPanelAbierto(true)}
                >
                  Nuevo edificio
                </button>
              ) : undefined
            }
          />
        ) : (
          <ul className="lista-de-edificios" aria-label="Edificios">
            {edificios.map((edificio) => (
              <li key={edificio.id} className="lista-de-edificios__fila">
                <span
                  className="fila-con-icono__icono lista-de-edificios__icono"
                  aria-hidden="true"
                >
                  <Building2 size={20} strokeWidth={1.75} />
                </span>
                <div className="lista-de-edificios__identidad">
                  <a href={`/edificios/${edificio.id}`} className="lista-de-edificios__nombre">
                    {edificio.nombre}
                  </a>
                  <span className="lista-de-edificios__localidad">
                    {edificio.localidad ?? "Sin completar"}
                  </span>
                </div>
                <div className="lista-de-edificios__dato lista-de-edificios__unidades">
                  <span className="lista-de-edificios__rotulo">Unidades</span>
                  <span className="numero-tabular">{edificio.cantidadUnidades ?? "Sin datos"}</span>
                </div>
                <div className="lista-de-edificios__dato lista-de-edificios__coeficientes">
                  <span className="lista-de-edificios__rotulo">Coeficientes</span>
                  {edificio.estadoCoeficientes && edificio.diferencia ? (
                    <EstadoDeCoeficientes
                      estado={edificio.estadoCoeficientes}
                      diferencia={edificio.diferencia}
                    />
                  ) : (
                    <p>Sin datos</p>
                  )}
                </div>
                <div className="lista-de-edificios__dato lista-de-edificios__migracion">
                  <span className="lista-de-edificios__rotulo">Saldos previos</span>
                  <p>
                    {edificio.estadoMigracion
                      ? textoEstadoDeMigracion(edificio.estadoMigracion)
                      : "Sin datos"}
                  </p>
                </div>
                <div className="lista-de-edificios__dato lista-de-edificios__puesta">
                  <span className="lista-de-edificios__rotulo">Puesta a punto</span>
                  {edificio.listoParaLiquidar ? (
                    <p>Listo para liquidar</p>
                  ) : typeof edificio.pasosHechos === "number" ? (
                    <BarraDeProgreso hechos={edificio.pasosHechos} total={7} />
                  ) : (
                    <p>Sin datos</p>
                  )}
                </div>
                <ChevronRight size={20} className="lista-de-edificios__flecha" aria-hidden="true" />
              </li>
            ))}
          </ul>
        )}
      </Panel>

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
          <SelectorDeUbicacion />
          <Campo nombre="calle_y_numero" etiqueta="Calle y número" name="calle_y_numero" />
          <Campo
            nombre="pisos"
            etiqueta="Pisos"
            name="pisos"
            type="number"
            min={1}
            max={60}
            required
          />
          <Campo
            nombre="subsuelos"
            etiqueta="Subsuelos"
            name="subsuelos"
            type="number"
            min={0}
            max={5}
            required
          />
          <button type="submit" className="boton-principal">
            Crear edificio
          </button>
        </Formulario>
      </PanelLateral>
    </Armazon>
  );
}
