"use client";

/**
 * Pagos, la bandeja del administrador (change 8, H-025): los pagos informados del edificio, cada uno con
 * lo que se le puede hacer según su estado. Un pago `informado` se confirma o se rechaza (con motivo);
 * uno `confirmado` se revierte (con motivo) o se reimputa a otra unidad (con motivo); de cualquiera se
 * ve el comprobante por un enlace firmado que vence a los 15 minutos. Cada decisión pide confirmación en
 * el panel lateral. La pantalla no calcula nada: manda lo que hay y dice lo que la API contesta.
 */

import { useRef, useState, useTransition } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Campo, CampoDeLista } from "../../../../componentes/Formulario";
import { Panel } from "../../../../componentes/Panel";
import { PanelLateral } from "../../../../componentes/PanelLateral";
import { permite, useSesionDePantalla } from "../../../../componentes/SesionDePantalla";
import type {
  AccionSobreUnPago,
  PagoInformado,
  UnidadParaInformar,
} from "../../../../lib/api/pagos";
import { dinero } from "../../../../lib/formato";
import { ArmazonDelEdificio } from "../Armazon";
import type {
  PedidoDeResolucion,
  ResultadoDelComprobante,
  ResultadoDeResolucion,
} from "./acciones";
import { AYUDA_PAGOS } from "./ayuda";
import { FilaDePago } from "./FilaDePago";

const MOTIVO_MAXIMO = 500;

type Props = {
  id: string;
  nombreEdificio: string;
  pagos: PagoInformado[];
  /** Las unidades del edificio: el destino de una reimputación. */
  unidades: UnidadParaInformar[];
  accionResolver: (pagoId: string, pedido: PedidoDeResolucion) => Promise<ResultadoDeResolucion>;
  accionVerComprobante: (pagoId: string) => Promise<ResultadoDelComprobante>;
};

type Decision = { accion: AccionSobreUnPago; pago: PagoInformado };

const TITULO: Record<AccionSobreUnPago, string> = {
  confirmacion: "Confirmar pago",
  rechazo: "Rechazar pago",
  reversion: "Revertir pago",
  reimputacion: "Reimputar pago",
};

const BOTON: Record<AccionSobreUnPago, [string, string]> = {
  confirmacion: ["Confirmar", "Confirmando…"],
  rechazo: ["Rechazar", "Rechazando…"],
  reversion: ["Revertir", "Revirtiendo…"],
  reimputacion: ["Reimputar", "Reimputando…"],
};

function Explicacion({ decision }: { decision: Decision }) {
  const { accion, pago } = decision;
  const de = `el pago de ${dinero(pago.monto)} (operación ${pago.numero_de_operacion})`;
  if (accion === "confirmacion") {
    return (
      <p>
        Vas a confirmar {de}. Se acredita en la cuenta de cada unidad y deja de ser un pago
        pendiente.
      </p>
    );
  }
  if (accion === "rechazo") {
    return <p>Vas a rechazar {de}. No se acredita nada y el vecino ve el motivo que escribas.</p>;
  }
  if (accion === "reversion") {
    return (
      <p>
        Vas a revertir {de}. Lo acreditado se deshace en el libro, que conserva todo lo registrado.
      </p>
    );
  }
  return (
    <p>
      Vas a pasar a otra unidad lo que {de} acreditó. El libro conserva todo lo registrado, con tu
      motivo.
    </p>
  );
}

function DialogoDeDecision({
  decision,
  unidades,
  error,
  enCurso,
  alCerrar,
  alConfirmar,
  devolverFocoA,
}: {
  decision: Decision | null;
  unidades: UnidadParaInformar[];
  error: string | null;
  enCurso: boolean;
  alCerrar: () => void;
  alConfirmar: (pedido: PedidoDeResolucion) => void;
  devolverFocoA: React.RefObject<HTMLElement | null>;
}) {
  const [motivo, setMotivo] = useState("");
  const [destino, setDestino] = useState("");
  const accion = decision?.accion;

  const pide = accion !== undefined && accion !== "confirmacion";
  const reimputa = accion === "reimputacion";
  // Desde dónde está hoy la plata de la primera parte (H-026: la unidad vigente, no la original); esa
  // unidad no es un destino posible.
  const desde = decision?.pago.partes[0]?.unidad_vigente_id;
  const destinos = unidades.filter((u) => u.unidad_id !== desde);
  const falta = (pide && motivo.trim() === "") || (reimputa && destino === "");
  const [textoBoton, textoEnCurso] = accion ? BOTON[accion] : ["", ""];

  return (
    <PanelLateral
      abierto={decision !== null}
      titulo={accion ? TITULO[accion] : ""}
      alCerrar={alCerrar}
      devolverFocoA={devolverFocoA}
    >
      <div className="panel-lateral__seccion">
        {decision ? <Explicacion decision={decision} /> : null}
        <form
          onSubmit={(evento) => {
            evento.preventDefault();
            if (!accion) return;
            alConfirmar({
              accion,
              ...(pide ? { motivo } : {}),
              ...(reimputa ? { desdeUnidadId: desde ?? "", haciaUnidadId: destino } : {}),
            });
          }}
        >
          {reimputa ? (
            <CampoDeLista
              nombre="hacia_unidad_id"
              etiqueta="Unidad de destino"
              value={destino}
              onChange={(e) => setDestino(e.target.value)}
              required
            >
              <option value="">Elegí una unidad</option>
              {destinos.map((unidad) => (
                <option key={unidad.unidad_id} value={unidad.unidad_id}>
                  {unidad.identificador}
                </option>
              ))}
            </CampoDeLista>
          ) : null}
          {pide ? (
            <Campo
              nombre="motivo"
              etiqueta="Motivo"
              autoComplete="off"
              maxLength={MOTIVO_MAXIMO}
              required
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          ) : null}
          <div className="panel-lateral__acciones">
            <button type="button" className="boton-secundario" onClick={alCerrar}>
              Cancelar
            </button>
            <button
              type="submit"
              className="boton-principal"
              disabled={falta || enCurso}
              aria-busy={enCurso}
            >
              {enCurso ? textoEnCurso : textoBoton}
            </button>
          </div>
        </form>
        {error ? (
          <p role="alert" className="campo__error">
            {error}
          </p>
        ) : null}
      </div>
    </PanelLateral>
  );
}

export function PantallaPagos({
  id,
  nombreEdificio,
  pagos,
  unidades,
  accionResolver,
  accionVerComprobante,
}: Props) {
  const sesion = useSesionDePantalla();
  const puedeResolver = permite(sesion, "confirmar_pago_informado", id);
  const puedeRevertir = permite(sesion, "revertir_o_reimputar_pago", id);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hecho, setHecho] = useState<string | null>(null);
  const [errorDelComprobante, setErrorDelComprobante] = useState<string | null>(null);
  const [enCurso, empezar] = useTransition();
  const [, empezarComprobante] = useTransition();
  const ultimoBoton = useRef<HTMLElement | null>(null);

  function abrir(accion: AccionSobreUnPago, pago: PagoInformado, boton: HTMLElement) {
    ultimoBoton.current = boton;
    setError(null);
    setHecho(null);
    setDecision({ accion, pago });
  }

  function confirmar(pedido: PedidoDeResolucion) {
    if (!decision) return;
    empezar(async () => {
      const resultado = await accionResolver(decision.pago.pago_id, pedido);
      if (resultado.hecho) {
        setDecision(null);
        setHecho(resultado.hecho);
      } else {
        setError(resultado.error ?? "No pudimos completar la acción. Probá de nuevo.");
      }
    });
  }

  function verComprobante(pago: PagoInformado) {
    setErrorDelComprobante(null);
    // La pestaña se abre ya, con el toque de la persona (si no, el navegador la bloquea); cuando
    // llega el enlace se le pone la dirección. Si no se pudo abrir, se navega en esta pestaña.
    const ventana = window.open("", "_blank");
    if (ventana) ventana.opener = null;
    empezarComprobante(async () => {
      const resultado = await accionVerComprobante(pago.pago_id);
      if (resultado.ruta) {
        if (ventana) ventana.location.href = resultado.ruta;
        else window.location.assign(resultado.ruta);
      } else {
        ventana?.close();
        setErrorDelComprobante(resultado.error ?? "No pudimos preparar el comprobante.");
      }
    });
  }

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="pagos">
      <EncabezadoDePantalla
        titulo="Pagos"
        ayuda={<Ayuda {...AYUDA_PAGOS} />}
        accionPrincipal={
          puedeResolver ? (
            <a className="boton-principal" href={`/edificios/${id}/pagos/informar`}>
              Informar un pago
            </a>
          ) : null
        }
      />
      <Panel
        titulo="Pagos informados"
        descripcion="Del más nuevo al más viejo. Revisá cada comprobante antes de confirmar."
      >
        {hecho ? (
          <p role="status" className="estado-confirmado">
            {hecho}
          </p>
        ) : null}
        {errorDelComprobante ? (
          <p role="alert" className="campo__error">
            {errorDelComprobante}
          </p>
        ) : null}
        {pagos.length === 0 ? (
          <p className="texto-secundario">Todavía no se informó ningún pago en este edificio.</p>
        ) : (
          <ul className="lista-de-filas" aria-label="Pagos del edificio">
            {pagos.map((pago) => (
              <li key={pago.pago_id}>
                <FilaDePago
                  pago={pago}
                  mostrarDondeEsta
                  acciones={
                    <>
                      {pago.estado === "informado" && puedeResolver ? (
                        <>
                          <button
                            type="button"
                            className="boton-principal"
                            onClick={(e) => abrir("confirmacion", pago, e.currentTarget)}
                          >
                            Confirmar
                          </button>
                          <button
                            type="button"
                            className="boton-secundario"
                            onClick={(e) => abrir("rechazo", pago, e.currentTarget)}
                          >
                            Rechazar
                          </button>
                        </>
                      ) : null}
                      {pago.estado === "confirmado" && puedeRevertir ? (
                        <>
                          <button
                            type="button"
                            className="boton-secundario"
                            onClick={(e) => abrir("reversion", pago, e.currentTarget)}
                          >
                            Revertir
                          </button>
                          <button
                            type="button"
                            className="boton-secundario"
                            onClick={(e) => abrir("reimputacion", pago, e.currentTarget)}
                          >
                            Reimputar
                          </button>
                        </>
                      ) : null}
                      <button
                        type="button"
                        className="boton-secundario"
                        onClick={() => verComprobante(pago)}
                      >
                        Ver comprobante
                      </button>
                    </>
                  }
                />
              </li>
            ))}
          </ul>
        )}
      </Panel>
      {puedeResolver || puedeRevertir ? (
        <DialogoDeDecision
          // Cada decisión empieza con el motivo y el destino vacíos.
          key={`${decision?.accion ?? ""}|${decision?.pago.pago_id ?? ""}`}
          decision={decision}
          unidades={unidades}
          error={error}
          enCurso={enCurso}
          alCerrar={() => setDecision(null)}
          alConfirmar={confirmar}
          devolverFocoA={ultimoBoton}
        />
      ) : null}
    </ArmazonDelEdificio>
  );
}
