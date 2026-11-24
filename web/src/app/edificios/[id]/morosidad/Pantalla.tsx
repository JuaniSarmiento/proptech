"use client";

/**
 * Morosidad (change 10a, H-029, HU-A8): las unidades con deuda vencida del edificio, en el orden que
 * manda la API, con su resumen y, sólo con `exportar_morosidad` en el edificio, el link que baja el
 * Excel. La pantalla no calcula nada: cada monto y el total del resumen son los de la API (R07, D-046).
 */

import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Panel } from "../../../../componentes/Panel";
import { permite, useSesionDePantalla } from "../../../../componentes/SesionDePantalla";
import type { EtiquetaDeMorosidad, Morosidad } from "../../../../lib/api/morosidad";
import { dinero, fecha } from "../../../../lib/formato";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_MOROSIDAD } from "./ayuda";

const SITUACION: Record<EtiquetaDeMorosidad, string> = {
  moroso_critico: "Moroso crítico",
  con_deuda_vencida: "Con deuda vencida",
  deuda_de_intereses: "Deuda de intereses",
  bajo_umbral: "Bajo el umbral",
};

type Props = {
  id: string;
  nombreEdificio: string;
  morosidad: Morosidad;
};

function Dato({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="morosidad__dato">
      <dt>{rotulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export function PantallaMorosidad({ id, nombreEdificio, morosidad }: Props) {
  const sesion = useSesionDePantalla();
  const puedeExportar = permite(sesion, "exportar_morosidad", id);
  const { resumen, unidades } = morosidad;
  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="morosidad">
      <EncabezadoDePantalla
        titulo="Morosidad"
        ayuda={<Ayuda {...AYUDA_MOROSIDAD} />}
        accionPrincipal={
          puedeExportar ? (
            <a className="boton-principal" href={`/edificios/${id}/morosidad/excel`}>
              Exportar a Excel
            </a>
          ) : undefined
        }
      />
      <section className="morosidad__resumen" aria-label="Resumen de la morosidad">
        <dl className="morosidad__cifras">
          <Dato rotulo="Unidades que deben">
            <span className="numero-tabular">{resumen.unidades_con_deuda}</span>
          </Dato>
          <Dato rotulo="Morosos críticos">
            <span className="numero-tabular">{resumen.morosos_criticos}</span>
          </Dato>
          <Dato rotulo="Total vencido">
            <span className="numero-tabular">{dinero(resumen.total_vencido)}</span>
          </Dato>
        </dl>
        <p className="texto-secundario">
          {morosidad.intereses_al === null
            ? "Sin intereses registrados"
            : `Intereses al ${fecha(morosidad.intereses_al)}`}
        </p>
      </section>
      <Panel
        titulo="Unidades con deuda"
        descripcion="Primero los morosos críticos; después, de mayor a menor deuda."
      >
        {unidades.length === 0 ? (
          <p role="status" className="texto-secundario">
            No hay unidades con deuda vencida
          </p>
        ) : (
          <ul className="lista-de-filas" aria-label="Unidades con deuda">
            {unidades.map((u) => (
              <li key={u.unidad_id} className="morosidad__fila">
                <div className="morosidad__cabecera">
                  <strong className="morosidad__unidad">{u.unidad}</strong>
                  <span className="morosidad__situacion" data-situacion={u.etiqueta}>
                    {SITUACION[u.etiqueta]}
                  </span>
                </div>
                <p className="texto-secundario morosidad__propietarios">
                  {u.propietarios.length === 0
                    ? "Sin propietarios cargados"
                    : u.propietarios.join(", ")}
                </p>
                <dl className="morosidad__datos">
                  <Dato rotulo="Total vencido">
                    <span className="numero-tabular">{dinero(u.total_vencido)}</span>
                  </Dato>
                  <Dato rotulo="Capital">
                    <span className="numero-tabular">{dinero(u.capital)}</span>
                  </Dato>
                  <Dato rotulo="Intereses">
                    <span className="numero-tabular">{dinero(u.intereses)}</span>
                  </Dato>
                  <Dato rotulo="Liquidaciones vencidas">
                    <span className="numero-tabular">{u.liquidaciones_vencidas}</span>
                  </Dato>
                </dl>
                <p className="texto-secundario">
                  {`Desde el ${fecha(u.vencida_desde)} · ${u.dias} ${u.dias === 1 ? "día" : "días"}`}
                </p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </ArmazonDelEdificio>
  );
}
