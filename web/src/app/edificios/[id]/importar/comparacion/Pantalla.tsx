"use client";

/**
 * Comparación de saldos del borrador (change 5, H-008, D6, D11): una tabla "Comparación por
 * unidad" (borrador, control y diferencia, una fila por unidad, con el aviso de mes entero en la
 * fila que lo tiene) y al costado los dos totales y cuántas unidades tienen diferencia. Con
 * diferencias por aceptar y el permiso, "Aceptar diferencias" abre una confirmación (el mismo
 * `PanelLateral` que usa Personal para "Quitar": `role="dialog"`, `Esc`, foco devuelto) que nombra
 * la cantidad; al confirmar, "Diferencias aceptadas" deja la lista y quién y cuándo. Los totales
 * pueden coincidir y haber diferencias por unidad: por eso la cantidad se dice aparte.
 */

import { CircleCheck } from "lucide-react";
import { useActionState, useEffect, useRef, useState } from "react";
import { useFormStatus } from "react-dom";
import { Ayuda } from "../../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../../componentes/EncabezadoDePantalla";
import { Estados } from "../../../../../componentes/Estados";
import { FilaConIcono } from "../../../../../componentes/FilaConIcono";
import { Panel } from "../../../../../componentes/Panel";
import { PanelLateral } from "../../../../../componentes/PanelLateral";
import { permite, useSesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type {
  AceptacionDeDiferencias,
  ComparacionDelBorrador,
} from "../../../../../lib/api/importaciones";
import { dinero, fechaYHora } from "../../../../../lib/formato";
import { ArmazonDelEdificio } from "../../Armazon";
import { AYUDA_COMPARACION } from "./ayuda";

export type EstadoAceptacion = {
  error?: string;
  aceptada?: AceptacionDeDiferencias;
} | null;

type AccionAceptar = (
  estadoPrevio: EstadoAceptacion,
  formData: FormData,
) => Promise<EstadoAceptacion>;

type Props = {
  id: string;
  nombreEdificio: string;
  comparacion: ComparacionDelBorrador;
  accionAceptar: AccionAceptar;
};

function conDiferencia(cantidad: number): string {
  return `${cantidad} ${cantidad === 1 ? "unidad" : "unidades"} con diferencia`;
}

function BotonConfirmar() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className="boton-principal" disabled={pending} aria-busy={pending}>
      {pending ? "Aceptando…" : "Aceptar"}
    </button>
  );
}

function TablaDeComparacion({ comparacion }: { comparacion: ComparacionDelBorrador }) {
  const hayAvisos = comparacion.unidades.some((unidad) => unidad.aviso !== null);
  return (
    <div className="padron-de-unidades__scroll">
      <table className="padron-de-unidades padron-de-unidades--envuelto">
        <caption className="sr-only">Comparación por unidad</caption>
        <thead>
          <tr>
            <th scope="col">Unidad</th>
            <th scope="col" className="numero-tabular">
              Borrador
            </th>
            <th scope="col" className="numero-tabular">
              Control
            </th>
            <th scope="col" className="numero-tabular">
              Diferencia
            </th>
            {hayAvisos ? <th scope="col">Aviso</th> : null}
          </tr>
        </thead>
        <tbody>
          {comparacion.unidades.map((unidad) => (
            <tr
              key={unidad.unidad_id}
              className={
                unidad.diferencia === "0.00" ? undefined : "comparacion__fila--con-diferencia"
              }
            >
              <td>{unidad.unidad}</td>
              <td className="numero-tabular">{dinero(unidad.borrador)}</td>
              <td className="numero-tabular">{dinero(unidad.control)}</td>
              <td className="numero-tabular">{dinero(unidad.diferencia)}</td>
              {hayAvisos ? <td>{unidad.aviso ?? "—"}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DiferenciasAceptadas({ aceptacion }: { aceptacion: AceptacionDeDiferencias }) {
  return (
    <Panel
      titulo="Diferencias aceptadas"
      descripcion={`Quedaron registradas el ${fechaYHora(aceptacion.aceptada_en)}.`}
    >
      <ul className="lista-de-filas" aria-label="Unidades con diferencia aceptada">
        {aceptacion.diferencias.map((diferencia) => (
          <li key={diferencia.unidad}>
            <FilaConIcono
              icono={CircleCheck}
              tono="listo"
              titulo={`${diferencia.unidad}: diferencia de ${dinero(diferencia.diferencia)}`}
              detalle={`Borrador ${dinero(diferencia.borrador)} · Control ${dinero(diferencia.control)}`}
            />
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function PantallaComparacion({ id, nombreEdificio, comparacion, accionAceptar }: Props) {
  const puedeAceptar = permite(useSesionDePantalla(), "aceptar_diferencias_de_saldos", id);
  const [estado, enviar] = useActionState(accionAceptar, null);
  const [abierta, setAbierta] = useState(false);
  const botonRef = useRef<HTMLButtonElement>(null);
  const regionRef = useRef<HTMLDivElement>(null);

  const aceptacion = estado?.aceptada ?? comparacion.aceptacion;
  const quedaPorAceptar = comparacion.requiere_aceptacion && !estado?.aceptada;
  const hayAceptada = estado?.aceptada !== undefined;

  // Al aceptar, el botón desaparece: la confirmación se cierra (ya, sin esperar un efecto) y el
  // foco va a lo que apareció.
  useEffect(() => {
    if (hayAceptada) {
      regionRef.current?.focus();
    }
  }, [hayAceptada]);

  function cancelar() {
    setAbierta(false);
    botonRef.current?.focus();
  }

  const diferenciasPorAceptar = comparacion.unidades.filter(
    (unidad) => unidad.diferencia !== "0.00",
  );

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="importar">
      <EncabezadoDePantalla
        titulo="Comparación de saldos"
        ayuda={<Ayuda {...AYUDA_COMPARACION} />}
        accionPrincipal={
          quedaPorAceptar && puedeAceptar ? (
            <button
              ref={botonRef}
              type="button"
              className="boton-principal"
              onClick={() => setAbierta(true)}
            >
              Aceptar diferencias
            </button>
          ) : null
        }
      />

      <div className="disposicion">
        <div>
          <Panel
            titulo="Saldo por unidad"
            descripcion="Borrador es lo que dice el archivo, control es el saldo que te dio el administrador anterior y diferencia es el borrador menos el control."
          >
            {comparacion.unidades.length > 0 ? (
              <TablaDeComparacion comparacion={comparacion} />
            ) : (
              <p>El archivo no trae saldos ni controles.</p>
            )}
          </Panel>
          {aceptacion ? (
            <div ref={regionRef} tabIndex={-1} className="comparacion__aceptadas">
              <DiferenciasAceptadas aceptacion={aceptacion} />
            </div>
          ) : null}
        </div>

        <div className="disposicion__lateral">
          <Panel titulo="Totales" variante="apoyo">
            <dl className="renglones">
              <div className="renglones__fila">
                <dt>Total del borrador</dt>
                <dd className="numero-tabular">{dinero(comparacion.total_borrador)}</dd>
              </div>
              <div className="renglones__fila">
                <dt>Total de control</dt>
                <dd className="numero-tabular">{dinero(comparacion.total_control)}</dd>
              </div>
            </dl>
            <p className="comparacion__cantidad">
              {conDiferencia(comparacion.unidades_con_diferencia)}
            </p>
            {quedaPorAceptar && !puedeAceptar ? (
              <p className="texto-secundario">
                No tenés permiso para aceptar diferencias en este edificio. Lo hace el administrador
                principal.
              </p>
            ) : null}
          </Panel>
        </div>
      </div>

      <PanelLateral
        abierto={abierta && !hayAceptada}
        titulo="Aceptar diferencias"
        alCerrar={() => setAbierta(false)}
        devolverFocoA={botonRef}
      >
        <div className="panel-lateral__seccion">
          <p>
            Vas a aceptar {conDiferencia(comparacion.unidades_con_diferencia)} entre el borrador y
            el control. Queda registrado quién las aceptó, cuándo y la lista de unidades.
          </p>
          <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Unidades a aceptar">
            {diferenciasPorAceptar.map((unidad) => (
              <li key={unidad.unidad_id}>
                <FilaConIcono
                  icono={CircleCheck}
                  titulo={`${unidad.unidad}: ${dinero(unidad.diferencia)}`}
                />
              </li>
            ))}
          </ul>
          <form action={enviar}>
            <input type="hidden" name="importacion_id" value={comparacion.importacion_id} />
            <div className="panel-lateral__acciones">
              <button type="button" className="boton-secundario" onClick={cancelar}>
                Cancelar
              </button>
              <BotonConfirmar />
            </div>
          </form>
          {estado?.error ? (
            <p role="alert" className="campo__error">
              {estado.error}
            </p>
          ) : null}
        </div>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}

export function PantallaSinBorrador({
  id,
  nombreEdificio,
}: {
  id: string;
  nombreEdificio: string;
}) {
  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="importar">
      <EncabezadoDePantalla
        titulo="Comparación de saldos"
        ayuda={<Ayuda {...AYUDA_COMPARACION} />}
      />
      <Estados
        tipo="vacio"
        mensaje="Todavía no hay un borrador de saldos."
        detalle="Subí un archivo con las hojas Saldos y Control para compararlo con el saldo del administrador anterior."
        accion={
          <a className="boton-enlace" href={`/edificios/${id}/importar`}>
            Importar desde Excel
          </a>
        }
      />
    </ArmazonDelEdificio>
  );
}
