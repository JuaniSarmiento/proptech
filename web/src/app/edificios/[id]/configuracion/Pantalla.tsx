"use client";

/**
 * Intereses y vencimiento (tarea 4.6, D5, D11): la configuración VIGENTE
 * arriba, bien clara; el HISTORIAL abajo, como línea de tiempo (más nueva
 * primero), con su autor y los campos que cambiaron respecto de la
 * anterior (texto, no número, D6). "Cambiar configuración" siempre crea
 * una versión nueva (D11, shape §5: la anterior nunca se borra); "rige
 * desde" lo valida la API (422 en el campo), la web no calcula "hoy en
 * Mendoza" (D-ficha 4.6).
 */

import { useActionState, useEffect, useRef, useState } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Campo, Formulario } from "../../../../componentes/Formulario";
import { PanelLateral } from "../../../../componentes/PanelLateral";
import type { ConfiguracionVigente, VersionDelHistorial } from "../../../../lib/api/tipos";
import { ArmazonDelEdificio } from "../Armazon";
import { textoDeVigente } from "../textoDeVigente";
import { AYUDA_CONFIGURACION } from "./ayuda";
import { camposCambiados } from "./historial";

export type EstadoFormularioVersion = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

type AccionVersion = (
  estadoPrevio: EstadoFormularioVersion,
  formData: FormData,
) => Promise<EstadoFormularioVersion>;

type Modalidad = "unico" | "doble";

type Props = {
  id: string;
  nombreEdificio: string;
  vigente: ConfiguracionVigente;
  historial: VersionDelHistorial[];
  accionCrear: AccionVersion;
};

const _FORMAS_DE_CALCULO: Array<{ valor: string; etiqueta: string }> = [
  { valor: "proporcional_por_dia", etiqueta: "Proporcional por día" },
  { valor: "mes_entero", etiqueta: "Mes entero" },
];

export function PantallaConfiguracion({
  id,
  nombreEdificio,
  vigente,
  historial,
  accionCrear,
}: Props) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [modalidadFormulario, setModalidadFormulario] = useState<Modalidad>(
    vigente?.modalidad_de_vencimiento === "doble" ? "doble" : "unico",
  );
  const aperturaRef = useRef<HTMLElement | null>(null);

  const [estado, enviar] = useActionState(accionCrear, null);

  useEffect(() => {
    if (estado?.ok) {
      setPanelAbierto(false);
      aperturaRef.current?.focus();
    }
  }, [estado]);

  function abrirPanel(evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setModalidadFormulario(vigente?.modalidad_de_vencimiento === "doble" ? "doble" : "unico");
    setPanelAbierto(true);
  }

  const botonCambiar = (
    <button type="button" className="boton-principal" onClick={abrirPanel}>
      Cambiar configuración
    </button>
  );

  const masNuevaPrimero = [...historial].reverse();

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="configuracion">
      <EncabezadoDePantalla
        titulo="Intereses y vencimiento"
        ayuda={<Ayuda {...AYUDA_CONFIGURACION} />}
        accionPrincipal={botonCambiar}
      />

      <p className="configuracion__vigente">{textoDeVigente(vigente)}</p>

      <h2>Historial</h2>
      {historial.length === 0 ? (
        <p>Todavía no hay versiones.</p>
      ) : (
        <ol className="historial-de-configuracion" aria-label="Historial de configuración">
          {masNuevaPrimero.map((version) => {
            const indiceAscendente = historial.indexOf(version);
            const anterior =
              indiceAscendente > 0 ? (historial[indiceAscendente - 1] ?? null) : null;
            const cambios = camposCambiados(version, anterior);
            return (
              <li key={version.id} className="historial-de-configuracion__fila">
                <p>
                  Rige desde <strong>{version.vigente_desde}</strong> · {version.autor_nombre}
                </p>
                {cambios.length > 0 ? <p>Cambió: {cambios.join(", ")}</p> : null}
              </li>
            );
          })}
        </ol>
      )}

      <PanelLateral
        abierto={panelAbierto}
        titulo="Cambiar configuración"
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={aperturaRef}
      >
        <Formulario
          erroresPorCampo={estado?.erroresPorCampo ?? {}}
          erroresDesconocidos={estado?.erroresDesconocidos ?? []}
          action={enviar}
        >
          <p>La versión anterior no se borra: queda guardada en el historial.</p>
          <Campo
            nombre="vigente_desde"
            etiqueta="Rige desde"
            name="vigente_desde"
            type="date"
            required
          />
          <Campo
            nombre="tasa_mensual"
            etiqueta="Tasa mensual"
            name="tasa_mensual"
            defaultValue={vigente?.tasa_mensual}
            required
          />
          <Campo
            nombre="porcentaje_fondo"
            etiqueta="Fondo de reserva"
            name="porcentaje_fondo"
            defaultValue={vigente?.porcentaje_fondo}
            required
          />
          <Campo
            nombre="dias_de_gracia"
            etiqueta="Días de gracia"
            name="dias_de_gracia"
            type="number"
            min={0}
            max={31}
            defaultValue={vigente?.dias_de_gracia}
            required
          />
          <label className="campo">
            Forma de cálculo
            <select
              name="forma_de_calculo"
              defaultValue={vigente?.forma_de_calculo ?? "proporcional_por_dia"}
            >
              {_FORMAS_DE_CALCULO.map((forma) => (
                <option key={forma.valor} value={forma.valor}>
                  {forma.etiqueta}
                </option>
              ))}
            </select>
          </label>
          <Campo
            nombre="dia_de_vencimiento"
            etiqueta="Día de vencimiento"
            name="dia_de_vencimiento"
            type="number"
            min={1}
            max={28}
            defaultValue={vigente?.dia_de_vencimiento}
            required
          />
          <label className="campo">
            Modalidad de vencimiento
            <select
              name="modalidad_de_vencimiento"
              value={modalidadFormulario}
              onChange={(e) => setModalidadFormulario(e.target.value as Modalidad)}
            >
              <option value="unico">Único</option>
              <option value="doble">Doble</option>
            </select>
          </label>
          {modalidadFormulario === "doble" ? (
            <>
              <Campo
                nombre="dia_segundo_vencimiento"
                etiqueta="Segundo vencimiento"
                name="dia_segundo_vencimiento"
                type="number"
                min={1}
                max={28}
                defaultValue={vigente?.dia_segundo_vencimiento ?? undefined}
                required
              />
              <Campo
                nombre="recargo_segundo_vencimiento"
                etiqueta="Recargo del segundo vencimiento"
                name="recargo_segundo_vencimiento"
                defaultValue={vigente?.recargo_segundo_vencimiento ?? undefined}
                required
              />
            </>
          ) : null}
          <button type="submit" className="boton-principal">
            Guardar
          </button>
        </Formulario>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}
