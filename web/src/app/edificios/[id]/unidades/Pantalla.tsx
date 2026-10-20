"use client";

/**
 * Padrón de unidades (tarea 4.3, D6, D8): tabla con números tabulares en
 * formato argentino; la suma de coeficientes y su estado vienen de la API
 * (D2, "la web no calcula"); tocar una fila o "Agregar unidad" abre el
 * panel lateral con el formulario; guardar cierra el panel, devuelve el
 * foco y muestra lo que da la API (tras revalidar la ruta, D1).
 */

import { useActionState, useEffect, useRef, useState } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../../../componentes/EstadoDeCoeficientes";
import { Estados } from "../../../../componentes/Estados";
import { Campo, Formulario } from "../../../../componentes/Formulario";
import { PanelLateral } from "../../../../componentes/PanelLateral";
import type { InformeDeCoeficientes, Unidad } from "../../../../lib/api/tipos";
import { coeficiente, superficie } from "../../../../lib/formato";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_PADRON } from "./ayuda";

export type EstadoFormularioUnidad = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

type AccionUnidad = (
  estadoPrevio: EstadoFormularioUnidad,
  formData: FormData,
) => Promise<EstadoFormularioUnidad>;

type Props = {
  id: string;
  nombreEdificio: string;
  unidades: Unidad[];
  informe: InformeDeCoeficientes;
  accionCrear: AccionUnidad;
  accionEditar: AccionUnidad;
};

const _TIPOS: Array<{ valor: string; etiqueta: string }> = [
  { valor: "departamento", etiqueta: "Departamento" },
  { valor: "cochera", etiqueta: "Cochera" },
  { valor: "baulera", etiqueta: "Baulera" },
  { valor: "local", etiqueta: "Local" },
];

function etiquetaDeTipo(valor: string): string {
  return _TIPOS.find((tipo) => tipo.valor === valor)?.etiqueta ?? valor;
}

export function PantallaPadron({
  id,
  nombreEdificio,
  unidades,
  informe,
  accionCrear,
  accionEditar,
}: Props) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [unidadEnEdicion, setUnidadEnEdicion] = useState<Unidad | null>(null);
  const aperturaRef = useRef<HTMLElement | null>(null);

  const accionActiva = unidadEnEdicion ? accionEditar : accionCrear;
  const [estado, enviar] = useActionState(accionActiva, null);

  useEffect(() => {
    if (estado?.ok) {
      setPanelAbierto(false);
      aperturaRef.current?.focus();
    }
  }, [estado]);

  function abrirNueva(evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setUnidadEnEdicion(null);
    setPanelAbierto(true);
  }

  function abrirEdicion(unidad: Unidad, evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setUnidadEnEdicion(unidad);
    setPanelAbierto(true);
  }

  const botonAgregar = (
    <button type="button" className="boton-principal" onClick={abrirNueva}>
      Agregar unidad
    </button>
  );

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="unidades">
      <EncabezadoDePantalla
        titulo="Padrón de unidades"
        ayuda={<Ayuda {...AYUDA_PADRON} />}
        accionPrincipal={botonAgregar}
      />

      <EstadoDeCoeficientes estado={informe.estado} diferencia={informe.diferencia} />

      {unidades.length === 0 ? (
        <Estados tipo="vacio" mensaje="Todavía no cargaste unidades" accion={botonAgregar} />
      ) : (
        <div className="padron-de-unidades__scroll">
          <table className="padron-de-unidades">
            <caption className="sr-only">Unidades del edificio</caption>
            <thead>
              <tr>
                <th>Identificador</th>
                <th>Tipo</th>
                <th>Piso</th>
                <th className="numero-tabular">Superficie (m²)</th>
                <th className="numero-tabular">Coeficiente</th>
              </tr>
            </thead>
            <tbody>
              {unidades.map((unidad) => (
                <tr key={unidad.id}>
                  <td>
                    <button
                      type="button"
                      className="boton-enlace"
                      onClick={(e) => abrirEdicion(unidad, e)}
                    >
                      {unidad.identificador}
                    </button>
                  </td>
                  <td>{etiquetaDeTipo(unidad.tipo)}</td>
                  <td>{unidad.piso}</td>
                  <td className="numero-tabular">{superficie(unidad.superficie_m2)}</td>
                  <td className="numero-tabular">{coeficiente(unidad.coeficiente)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <PanelLateral
        abierto={panelAbierto}
        titulo={unidadEnEdicion ? "Editar unidad" : "Agregar unidad"}
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={aperturaRef}
      >
        <Formulario
          erroresPorCampo={estado?.erroresPorCampo ?? {}}
          erroresDesconocidos={estado?.erroresDesconocidos ?? []}
          action={enviar}
        >
          {unidadEnEdicion ? (
            <input type="hidden" name="unidad_id" value={unidadEnEdicion.id} />
          ) : null}
          <Campo
            nombre="identificador"
            etiqueta="Identificador"
            name="identificador"
            defaultValue={unidadEnEdicion?.identificador}
            required
          />
          <label className="campo">
            Tipo
            <select name="tipo" defaultValue={unidadEnEdicion?.tipo ?? "departamento"}>
              {_TIPOS.map((tipo) => (
                <option key={tipo.valor} value={tipo.valor}>
                  {tipo.etiqueta}
                </option>
              ))}
            </select>
          </label>
          <Campo nombre="piso" etiqueta="Piso" name="piso" defaultValue={unidadEnEdicion?.piso} />
          <Campo
            nombre="superficie_m2"
            etiqueta="Superficie (m²)"
            name="superficie_m2"
            defaultValue={unidadEnEdicion?.superficie_m2}
            required
          />
          <Campo
            nombre="coeficiente"
            etiqueta="Coeficiente"
            name="coeficiente"
            defaultValue={unidadEnEdicion?.coeficiente}
            required
          />
          <button type="submit" className="boton-principal">
            Guardar
          </button>
        </Formulario>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}
