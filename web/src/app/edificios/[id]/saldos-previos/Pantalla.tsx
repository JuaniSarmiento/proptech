"use client";

/**
 * Confirmar "sin saldos previos" (tarea 4.7, D11): pantalla propia, sin
 * modal; la casilla "Entiendo que el edificio arranca sin deudas
 * anteriores" habilita el botón, y el envío sin tildarla (por teclado o un
 * envío directo del formulario) NUNCA llama a la API: se valida antes, en
 * el cliente (`Formulario.onSubmit`, tarea 4.7), y el error queda asociado
 * a la casilla por programa (`aria-invalid`/`aria-describedby`, igual que
 * cualquier otro campo, D8). Mientras el estado no sea "pendiente" se
 * muestra el estado, nunca el formulario (D11).
 *
 * Enmienda del 20/10/2026: la confirmación en el panel principal y, al
 * costado, qué significa en tres filas con ícono (antes, una sola vez,
 * después).
 */

import { CalendarCheck2, CircleCheck, FileX2, Undo2 } from "lucide-react";
import type { FormEvent } from "react";
import { useActionState, useState } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { FilaConIcono } from "../../../../componentes/FilaConIcono";
import { Campo, Formulario } from "../../../../componentes/Formulario";
import { Panel } from "../../../../componentes/Panel";
import { permite, useSesionDePantalla } from "../../../../componentes/SesionDePantalla";
import { textoEstadoDeMigracion } from "../../../../lib/textoDeEstados";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_SALDOS_PREVIOS } from "./ayuda";

export type EstadoConfirmacion = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

type AccionConfirmar = (
  estadoPrevio: EstadoConfirmacion,
  formData: FormData,
) => Promise<EstadoConfirmacion>;

type Props = {
  id: string;
  nombreEdificio: string;
  estadoMigracion: string;
  accionConfirmar: AccionConfirmar;
};

export function PantallaSaldosPrevios({
  id,
  nombreEdificio,
  estadoMigracion,
  accionConfirmar,
}: Props) {
  const puedeConfirmar = permite(useSesionDePantalla(), "confirmar_sin_saldos_previos", id);
  const [aceptado, setAceptado] = useState(false);
  const [errorCasilla, setErrorCasilla] = useState<string | null>(null);

  const [estado, enviar] = useActionState(accionConfirmar, null);

  function alEnviar(evento: FormEvent<HTMLFormElement>) {
    if (!aceptado) {
      evento.preventDefault();
      setErrorCasilla("Tildá la casilla para confirmar.");
      document.getElementById("campo-acepto")?.focus();
    } else {
      setErrorCasilla(null);
    }
  }

  const erroresPorCampo = {
    ...(estado?.erroresPorCampo ?? {}),
    ...(errorCasilla ? { acepto: errorCasilla } : {}),
  };

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="saldos-previos">
      <EncabezadoDePantalla
        titulo="Confirmar sin saldos previos"
        ayuda={<Ayuda {...AYUDA_SALDOS_PREVIOS} />}
      />

      <div className="disposicion">
        {estadoMigracion !== "pendiente" ? (
          <Panel
            titulo="Estado de los saldos previos"
            descripcion="Este paso ya está resuelto para este edificio."
          >
            <FilaConIcono
              icono={CircleCheck}
              tono="listo"
              titulo={
                <span role="status" className="estado-confirmado">
                  {textoEstadoDeMigracion(estadoMigracion)}
                </span>
              }
              detalle="No hace falta hacer nada más acá. Volvé al resumen para ver el próximo paso."
            />
          </Panel>
        ) : (
          <Panel
            titulo="Arrancar sin saldos previos"
            descripcion="Confirmalo una sola vez, cuando el edificio no tenga deudas ni saldos de antes para pasar."
            className="saldos-previos"
          >
            <p>
              Este edificio va a empezar a liquidarse en el sistema sin deudas ni saldos de antes:
              cualquier deuda o saldo previo queda fuera de las próximas liquidaciones.
            </p>
            <p className="aviso">
              <strong>Esta acción no se puede deshacer.</strong>
            </p>

            {puedeConfirmar ? (
              <Formulario
                erroresPorCampo={erroresPorCampo}
                erroresDesconocidos={estado?.erroresDesconocidos ?? []}
                action={enviar}
                onSubmit={alEnviar}
                aria-label="Confirmar sin saldos previos"
              >
                <Campo
                  nombre="acepto"
                  etiqueta="Entiendo que el edificio arranca sin deudas anteriores"
                  name="acepto"
                  type="checkbox"
                  checked={aceptado}
                  onChange={(e) => setAceptado(e.target.checked)}
                />
                <button type="submit" className="boton-principal" disabled={!aceptado}>
                  Confirmar
                </button>
              </Formulario>
            ) : null}
          </Panel>
        )}

        <div className="disposicion__lateral">
          <Panel titulo="Qué significa" variante="apoyo">
            <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Qué significa">
              <li>
                <FilaConIcono
                  icono={FileX2}
                  titulo="Sin deudas de antes"
                  detalle="Las deudas o saldos que traía el edificio no pasan al sistema."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={Undo2}
                  titulo="Una sola vez"
                  detalle="Después de confirmar no se puede volver atrás."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={CalendarCheck2}
                  titulo="Después"
                  detalle="El edificio se liquida desde cero, mes a mes."
                />
              </li>
            </ul>
          </Panel>
        </div>
      </div>
    </ArmazonDelEdificio>
  );
}
