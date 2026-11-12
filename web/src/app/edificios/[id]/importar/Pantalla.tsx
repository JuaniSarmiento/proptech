"use client";

/**
 * Importar el padrón desde Excel (change 5, H-007, D11): un panel principal con el formulario (el
 * archivo, la fecha de migración, "Importar") y la descarga de la plantilla; debajo, el resultado:
 * aceptado (resumen y advertencias) o rechazado (tabla "Errores del archivo", una fila por error,
 * sin haber cargado nada). Al costado, cómo se arma el archivo. Mientras el estado de migración no
 * sea "pendiente" se muestra el estado, nunca el formulario.
 */

import { CircleCheck, FileSpreadsheet, Mail, Ruler } from "lucide-react";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { FilaConIcono } from "../../../../componentes/FilaConIcono";
import { Campo, Formulario } from "../../../../componentes/Formulario";
import { Panel } from "../../../../componentes/Panel";
import { permite, useSesionDePantalla } from "../../../../componentes/SesionDePantalla";
import type { ErrorDeArchivo } from "../../../../lib/api/cliente";
import type { ImportacionAceptada } from "../../../../lib/api/importaciones";
import { textoEstadoDeMigracion } from "../../../../lib/textoDeEstados";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_IMPORTAR } from "./ayuda";

export type EstadoImportacion = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  aceptada?: ImportacionAceptada;
  rechazo?: ErrorDeArchivo[];
} | null;

type AccionImportar = (
  estadoPrevio: EstadoImportacion,
  formData: FormData,
) => Promise<EstadoImportacion>;

type Props = {
  id: string;
  nombreEdificio: string;
  estadoMigracion: string;
  accionImportar: AccionImportar;
};

function plural(cantidad: number, uno: string, varios: string): string {
  return `${cantidad} ${cantidad === 1 ? uno : varios}`;
}

function BotonImportar() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className="boton-principal" disabled={pending} aria-busy={pending}>
      {pending ? "Importando…" : "Importar"}
    </button>
  );
}

/** "Hoja Unidades, fila 9" / "Hoja Unidades" / "Todo el archivo": dónde está el error. */
function ubicacion(error: ErrorDeArchivo): string {
  return error.hoja ?? "Todo el archivo";
}

function TablaDeErrores({ errores }: { errores: ErrorDeArchivo[] }) {
  return (
    <div className="padron-de-unidades__scroll">
      <table className="padron-de-unidades padron-de-unidades--envuelto">
        <caption className="sr-only">Errores del archivo</caption>
        <thead>
          <tr>
            <th scope="col">Hoja</th>
            <th scope="col" className="numero-tabular">
              Fila
            </th>
            <th scope="col">Columna</th>
            <th scope="col">Motivo</th>
          </tr>
        </thead>
        <tbody>
          {errores.map((error, posicion) => (
            // El orden en que llegan es el que se muestra: la posición es la clave estable.
            // biome-ignore lint/suspicious/noArrayIndexKey: lista fija, sin reordenar ni quitar.
            <tr key={posicion}>
              <td>{ubicacion(error)}</td>
              <td className="numero-tabular">{error.fila ?? "—"}</td>
              <td>{error.columna ?? "—"}</td>
              <td>{error.motivo}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResumenAceptado({ id, aceptada }: { id: string; aceptada: ImportacionAceptada }) {
  return (
    <Panel titulo="Importación aceptada" descripcion="El padrón ya está cargado en el edificio.">
      <ul className="lista-de-filas" aria-label="Resumen de la importación">
        <li>
          <FilaConIcono
            icono={CircleCheck}
            tono="listo"
            titulo={plural(aceptada.unidades_creadas, "unidad creada", "unidades creadas")}
          />
        </li>
        <li>
          <FilaConIcono
            icono={CircleCheck}
            tono="listo"
            titulo={plural(
              aceptada.propietarios_creados,
              "propietario nuevo",
              "propietarios nuevos",
            )}
          />
        </li>
        {aceptada.propietarios_reusados > 0 ? (
          <li>
            <FilaConIcono
              icono={CircleCheck}
              tono="listo"
              titulo={plural(
                aceptada.propietarios_reusados,
                "propietario que ya existía",
                "propietarios que ya existían",
              )}
              detalle="Se usó la persona que ya estaba cargada con ese email."
            />
          </li>
        ) : null}
      </ul>
      {aceptada.advertencias.length > 0 ? (
        <div className="aviso">
          <p>
            <strong>Revisá estas advertencias:</strong>
          </p>
          <ul>
            {aceptada.advertencias.map((advertencia, posicion) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: lista fija, sin reordenar ni quitar.
              <li key={posicion}>{advertencia.motivo}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <p>
        {aceptada.filas_de_saldo > 0 ? (
          <a className="boton-enlace" href={`/edificios/${id}/importar/comparacion`}>
            Ver la comparación de saldos
          </a>
        ) : null}{" "}
        <a className="boton-enlace" href={`/edificios/${id}/unidades`}>
          Ver las unidades
        </a>
      </p>
    </Panel>
  );
}

export function PantallaImportar({ id, nombreEdificio, estadoMigracion, accionImportar }: Props) {
  const puedeImportar = permite(useSesionDePantalla(), "importar_padron_y_saldos", id);
  const [estado, enviar] = useActionState(accionImportar, null);

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="importar">
      <EncabezadoDePantalla titulo="Importar desde Excel" ayuda={<Ayuda {...AYUDA_IMPORTAR} />} />

      <div className="disposicion">
        <div>
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
                detalle="Ya no se puede importar de nuevo. Volvé al resumen para ver el próximo paso."
              />
            </Panel>
          ) : (
            <Panel
              titulo="Subir el padrón"
              descripcion="Un archivo .xlsx armado con la plantilla. Si algo está mal no se carga nada."
              accion={
                <a className="boton-enlace" href={`/edificios/${id}/importar/plantilla`} download>
                  Descargar plantilla
                </a>
              }
            >
              {puedeImportar ? (
                <Formulario
                  erroresPorCampo={estado?.erroresPorCampo ?? {}}
                  erroresDesconocidos={estado?.erroresDesconocidos ?? []}
                  action={enviar}
                  aria-label="Importar desde Excel"
                >
                  <Campo
                    nombre="archivo"
                    etiqueta="Archivo de Excel"
                    name="archivo"
                    type="file"
                    accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                  />
                  <Campo
                    nombre="fecha_de_migracion"
                    etiqueta="Fecha de migración"
                    name="fecha_de_migracion"
                    type="date"
                  />
                  <BotonImportar />
                </Formulario>
              ) : (
                <div role="alert" className="aviso">
                  <p>No podés importar en este edificio.</p>
                </div>
              )}
            </Panel>
          )}

          {estado?.rechazo ? (
            <Panel
              titulo="No se cargó nada"
              descripcion="Corregí el archivo y volvé a subirlo: estos son todos los errores que encontramos."
            >
              <TablaDeErrores errores={estado.rechazo} />
            </Panel>
          ) : null}
          {estado?.aceptada ? <ResumenAceptado id={id} aceptada={estado.aceptada} /> : null}
        </div>

        <div className="disposicion__lateral">
          <Panel titulo="Cómo se arma el archivo" variante="apoyo">
            <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Cómo se arma">
              <li>
                <FilaConIcono
                  icono={FileSpreadsheet}
                  titulo="Una fila por unidad"
                  detalle="En la hoja Unidades: identificador, tipo, piso, coeficiente y superficie."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={Ruler}
                  titulo="Los coeficientes suman 1"
                  detalle="Con una tolerancia de 0,0001. Si no, el archivo no se carga."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={Mail}
                  titulo="Sin invitaciones"
                  detalle="Importar no manda ningún email: a los vecinos los invitás vos después."
                />
              </li>
            </ul>
          </Panel>
        </div>
      </div>
    </ArmazonDelEdificio>
  );
}
