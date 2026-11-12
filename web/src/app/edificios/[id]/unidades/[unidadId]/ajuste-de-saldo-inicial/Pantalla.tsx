"use client";

/**
 * Ajustar el saldo inicial de una unidad (change 5, H-010, D8, D11): sólo con la migración
 * `confirmada` (antes se dice y se manda a importar). Importe (con coma decimal), concepto y
 * motivo; "Registrar ajuste" valida y abre una confirmación (el mismo `PanelLateral` de Personal y
 * de la comparación: `role="dialog"`, `Esc`, foco devuelto) que dice que no se deshace; al
 * confirmar manda el pedido con una operación (`operacion_id`) que se reusa en un reintento con los
 * mismos datos, así un reenvío nunca duplica el ajuste. Con el ajuste hecho, la región "Ajuste
 * registrado" deja el importe y el motivo y el formulario se va.
 */

import { type FormEvent, useActionState, useEffect, useRef, useState } from "react";
import { useFormStatus } from "react-dom";
import { Ayuda } from "../../../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../../../componentes/EncabezadoDePantalla";
import { Estados } from "../../../../../../componentes/Estados";
import { Campo, CampoDeLista, Formulario } from "../../../../../../componentes/Formulario";
import { Panel } from "../../../../../../componentes/Panel";
import { PanelLateral } from "../../../../../../componentes/PanelLateral";
import { permite, useSesionDePantalla } from "../../../../../../componentes/SesionDePantalla";
import type { AjusteDeSaldoInicial } from "../../../../../../lib/api/importaciones";
import { decimalParaApi, dinero } from "../../../../../../lib/formato";
import { ArmazonDelEdificio } from "../../../Armazon";
import { AYUDA_AJUSTE } from "./ayuda";
import { importeParaApi, MENSAJES_DE_CAMPO, MOTIVO_MAXIMO } from "./validacion";

export type EstadoAjuste = {
  error?: string;
  erroresPorCampo?: Record<string, string>;
  ajustado?: AjusteDeSaldoInicial;
} | null;

type AccionAjustar = (estadoPrevio: EstadoAjuste, formData: FormData) => Promise<EstadoAjuste>;

type Props = {
  id: string;
  nombreEdificio: string;
  identificadorDeUnidad: string;
  estadoMigracion: string;
  accionAjustar: AccionAjustar;
};

const CONCEPTOS = [
  { valor: "ordinaria", texto: "Ordinaria" },
  { valor: "fondo_de_reserva", texto: "Fondo de reserva" },
  { valor: "extraordinaria", texto: "Extraordinaria" },
];

function BotonDeLaConfirmacion() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className="boton-principal" disabled={pending} aria-busy={pending}>
      {pending ? "Registrando…" : "Confirmar"}
    </button>
  );
}

export function PantallaAjuste({
  id,
  nombreEdificio,
  identificadorDeUnidad,
  estadoMigracion,
  accionAjustar,
}: Props) {
  const puedeAjustar = permite(useSesionDePantalla(), "ajustar_saldo_inicial", id);
  const [estado, enviar] = useActionState(accionAjustar, null);
  const [importe, setImporte] = useState("");
  const [componente, setComponente] = useState("ordinaria");
  const [motivo, setMotivo] = useState("");
  const [erroresLocales, setErroresLocales] = useState<Record<string, string>>({});
  const [abierta, setAbierta] = useState(false);
  // Una operación por intento: se reusa mientras los datos no cambian (un reenvío no duplica).
  const operacion = useRef<{ clave: string; id: string } | null>(null);
  const [operacionId, setOperacionId] = useState("");
  const botonRef = useRef<HTMLButtonElement>(null);
  const regionRef = useRef<HTMLDivElement>(null);

  const ajustado = estado?.ajustado;
  const hayAjustado = ajustado !== undefined;

  // Cualquier respuesta cierra la confirmación: con un error, la pantalla queda con lo cargado.
  useEffect(() => {
    if (estado) setAbierta(false);
  }, [estado]);

  useEffect(() => {
    if (hayAjustado) regionRef.current?.focus();
  }, [hayAjustado]);

  function operacionDelIntento(): string {
    const clave = JSON.stringify([importe.trim(), componente, motivo.trim()]);
    if (operacion.current?.clave !== clave) {
      operacion.current = { clave, id: crypto.randomUUID() };
    }
    return operacion.current.id;
  }

  function alRegistrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const errores: Record<string, string> = {};
    if (importeParaApi(decimalParaApi(importe.trim())) === null) {
      errores.importe = MENSAJES_DE_CAMPO.importe ?? "";
    }
    if (motivo.trim() === "" || motivo.trim().length > MOTIVO_MAXIMO) {
      errores.motivo = MENSAJES_DE_CAMPO.motivo ?? "";
    }
    setErroresLocales(errores);
    const primero = Object.keys(errores)[0];
    if (primero) {
      document.getElementById(`campo-${primero}`)?.focus();
      return;
    }
    setOperacionId(operacionDelIntento());
    setAbierta(true);
  }

  const erroresPorCampo = { ...(estado?.erroresPorCampo ?? {}), ...erroresLocales };

  let cuerpo: React.ReactNode;
  if (estadoMigracion !== "confirmada") {
    cuerpo = (
      <Estados
        tipo="vacio"
        mensaje="Los saldos iniciales de este edificio todavía no están confirmados."
        detalle="Un ajuste corrige un saldo ya cargado. Primero hay que importar y confirmar los saldos del edificio."
        accion={
          <a className="boton-enlace" href={`/edificios/${id}/importar`}>
            Importar desde Excel
          </a>
        }
      />
    );
  } else if (ajustado) {
    cuerpo = (
      <div ref={regionRef} tabIndex={-1}>
        <Panel
          titulo="Ajuste registrado"
          descripcion={`La unidad ${identificadorDeUnidad} tiene una deuda nueva. Este paso no se deshace.`}
        >
          <dl className="renglones">
            <div className="renglones__fila">
              <dt>Importe</dt>
              <dd className="numero-tabular">{dinero(ajustado.importe)}</dd>
            </div>
            <div className="renglones__fila">
              <dt>Motivo</dt>
              <dd>{ajustado.motivo}</dd>
            </div>
          </dl>
          <a className="boton-enlace" href={`/edificios/${id}/unidades`}>
            Volver al padrón
          </a>
        </Panel>
      </div>
    );
  } else if (!puedeAjustar) {
    cuerpo = (
      <Panel
        titulo="Sin permiso"
        descripcion="Ajustar un saldo inicial lo hace el administrador principal."
      >
        <p>No tenés permiso para ajustar saldos iniciales en este edificio.</p>
      </Panel>
    );
  } else {
    cuerpo = (
      <Panel
        titulo={`Unidad ${identificadorDeUnidad}`}
        descripcion="Lo que se ajusta se suma como una deuda nueva de la unidad. Queda registrado quién lo hizo y por qué."
      >
        <Formulario
          erroresPorCampo={erroresPorCampo}
          onSubmit={alRegistrar}
          aria-label="Ajustar saldo inicial"
        >
          <Campo
            nombre="importe"
            etiqueta="Importe"
            inputMode="decimal"
            autoComplete="off"
            value={importe}
            onChange={(e) => setImporte(e.target.value)}
          />
          <CampoDeLista
            nombre="componente"
            etiqueta="Concepto"
            value={componente}
            onChange={(e) => setComponente(e.target.value)}
          >
            {CONCEPTOS.map((concepto) => (
              <option key={concepto.valor} value={concepto.valor}>
                {concepto.texto}
              </option>
            ))}
          </CampoDeLista>
          <Campo
            nombre="motivo"
            etiqueta="Motivo"
            autoComplete="off"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
          <button ref={botonRef} type="submit" className="boton-principal">
            Registrar ajuste
          </button>
        </Formulario>
        {estado?.error ? (
          <p role="alert" className="campo__error">
            {estado.error}
          </p>
        ) : null}
      </Panel>
    );
  }

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="unidades">
      <EncabezadoDePantalla titulo="Ajustar saldo inicial" ayuda={<Ayuda {...AYUDA_AJUSTE} />} />
      {cuerpo}

      <PanelLateral
        abierto={abierta && !hayAjustado}
        titulo="Confirmar ajuste"
        alCerrar={() => setAbierta(false)}
        devolverFocoA={botonRef}
      >
        <div className="panel-lateral__seccion">
          <p>
            Vas a sumar {importe.trim()} a la deuda de la unidad {identificadorDeUnidad}. Este
            ajuste no se deshace: queda registrado con su motivo.
          </p>
          <form action={enviar}>
            <input type="hidden" name="operacion_id" value={operacionId} />
            <input type="hidden" name="importe" value={importe.trim()} />
            <input type="hidden" name="componente" value={componente} />
            <input type="hidden" name="motivo" value={motivo.trim()} />
            <div className="panel-lateral__acciones">
              <button type="button" className="boton-secundario" onClick={() => setAbierta(false)}>
                Cancelar
              </button>
              <BotonDeLaConfirmacion />
            </div>
          </form>
        </div>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}
