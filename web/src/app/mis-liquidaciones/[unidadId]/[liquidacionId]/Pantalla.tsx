/**
 * La expensa de un mes para una unidad (change 11, H-040, C02): cuánto le toca y de dónde sale, por
 * categoría del edificio, por grupo de reparto y concepto por concepto, y la comparación con el mes
 * anterior si lo hay. La pantalla NO calcula nada (N02): muestra, con formato argentino, lo que la API
 * guardó al emitir. Al inquilino la API no le manda nada extraordinario (D-170.2): las partes que
 * llegan sin esa clave no se dibujan, y la pantalla tampoco las deriva (N01).
 */

import { ChevronLeft } from "lucide-react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Panel } from "../../../../componentes/Panel";
import type {
  BloqueDeLaExpensa,
  ExpensaDeLaUnidad,
  UnidadDelVecino,
} from "../../../../lib/api/vecino";
import { dinero, fecha, periodoEnPalabras, porcentaje } from "../../../../lib/formato";
import { ArmazonDelPortal } from "../../../_portal/ArmazonDelPortal";
import { Cifras } from "../../../_portal/Cifras";
import { AYUDA_EXPENSA } from "../../ayuda";

function Gastos({ titulo, bloque }: { titulo: string; bloque: BloqueDeLaExpensa }) {
  return (
    <Panel titulo={titulo} descripcion="Lo que gastó el edificio en el mes, por categoría.">
      <dl className="cifras">
        <div className="cifras__par">
          <dt>Subtotal</dt>
          <dd className="numero-tabular">{dinero(bloque.subtotal)}</dd>
        </div>
      </dl>
      <ul className="lista-de-categorias">
        {bloque.categorias.map((c) => (
          <li key={c.categoria_id}>
            <span className="lista-de-categorias__nombre">{c.nombre}</span>
            <span className="numero-tabular">{dinero(c.importe)}</span>
            <span className="numero-tabular texto-secundario">{porcentaje(c.porcentaje)}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

type Props = {
  expensa: ExpensaDeLaUnidad;
  unidad: UnidadDelVecino;
  unidades: UnidadDelVecino[];
};

export function PantallaExpensa({ expensa, unidad, unidades }: Props) {
  const periodo = periodoEnPalabras(expensa.periodo) ?? expensa.periodo;
  const { comparacion } = expensa;
  return (
    <ArmazonDelPortal seccionActual="mis-liquidaciones" unidades={unidades}>
      <a className="enlace-de-vuelta" href={`/mis-liquidaciones/${expensa.unidad_id}`}>
        <ChevronLeft size={18} strokeWidth={1.75} aria-hidden="true" />
        Volver a las liquidaciones de {expensa.identificador}
      </a>
      <EncabezadoDePantalla titulo={`Expensa de ${periodo}`} ayuda={<Ayuda {...AYUDA_EXPENSA} />} />
      <p className="texto-secundario">
        {expensa.identificador} · {unidad.edificio} · Vence el {fecha(expensa.vencimiento)}
      </p>

      <Panel titulo="Tu expensa" descripcion="Lo que te corresponde pagar en este mes.">
        <table className="tabla-de-importes" aria-label="Tu expensa">
          <tbody>
            <tr>
              <th scope="row">Ordinaria</th>
              <td className="numero-tabular">{dinero(expensa.ordinaria)}</td>
            </tr>
            {expensa.cargos_particulares.map((cargo, indice) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: la API no da id al cargo y dos pueden tener el mismo concepto; la lista es fija
              <tr key={`${cargo.concepto}-${indice}`}>
                <th scope="row">{cargo.concepto}</th>
                <td className="numero-tabular">{dinero(cargo.importe)}</td>
              </tr>
            ))}
            <tr>
              <th scope="row">Fondo de reserva</th>
              <td className="numero-tabular">{dinero(expensa.fondo_de_reserva)}</td>
            </tr>
            {expensa.extraordinaria === undefined ? null : (
              <tr>
                <th scope="row">Extraordinaria</th>
                <td className="numero-tabular">{dinero(expensa.extraordinaria)}</td>
              </tr>
            )}
            <tr>
              <th scope="row">Intereses</th>
              <td className="numero-tabular">{dinero(expensa.intereses)}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Total</th>
              <td className="numero-tabular">{dinero(expensa.total)}</td>
            </tr>
          </tfoot>
        </table>
      </Panel>

      <div className="disposicion disposicion--mitades">
        <Gastos titulo="Gastos ordinarios" bloque={expensa.bloques.ordinario} />
        {expensa.bloques.extraordinario === undefined ? null : (
          <Gastos titulo="Gastos extraordinarios" bloque={expensa.bloques.extraordinario} />
        )}
      </div>

      <Panel
        titulo="Por grupo de reparto"
        descripcion="Los grupos en los que participa tu unidad y lo que te toca de cada uno."
      >
        <ul className="lista-de-filas">
          {expensa.grupos.map((g) => (
            <li key={g.grupo_id} className="grupo-de-la-expensa">
              <span className="grupo-de-la-expensa__nombre">{g.nombre}</span>
              <span className="numero-tabular">Ordinaria {dinero(g.ordinaria)}</span>
              {g.extraordinaria === undefined ? null : (
                <span className="numero-tabular">Extraordinaria {dinero(g.extraordinaria)}</span>
              )}
            </li>
          ))}
        </ul>
      </Panel>

      {comparacion === null ? (
        <p role="status" className="texto-secundario">
          No hay una liquidación anterior para comparar.
        </p>
      ) : (
        <Panel
          titulo="Comparación con el mes anterior"
          descripcion="Cómo cambió tu total y cada categoría del edificio."
        >
          <h3 className="comparacion__periodo">
            Comparación con {periodoEnPalabras(comparacion.periodo) ?? comparacion.periodo}
          </h3>
          <Cifras
            cifras={[
              { rotulo: "Total del mes anterior", valor: dinero(comparacion.total_anterior) },
              { rotulo: "Diferencia", valor: dinero(comparacion.diferencia_total) },
            ]}
          />
          <section
            className="tabla-con-scroll"
            // biome-ignore lint/a11y/noNoninteractiveTabindex: una región que se desplaza tiene que poder enfocarse para usarla con teclado
            tabIndex={0}
            aria-label="Cuadro de comparación por categoría"
          >
            <table
              className="tabla-de-importes tabla-de-importes--comparacion"
              aria-label="Comparación por categoría"
            >
              <thead>
                <tr>
                  <th scope="col">Categoría</th>
                  <th scope="col">Este mes</th>
                  <th scope="col">Mes anterior</th>
                  <th scope="col">Diferencia</th>
                </tr>
              </thead>
              <tbody>
                {comparacion.categorias.map((c) => (
                  <tr key={`${c.bloque}-${c.categoria_id}`}>
                    <th scope="row">{c.nombre}</th>
                    <td className="numero-tabular">{dinero(c.importe)}</td>
                    <td className="numero-tabular">{dinero(c.importe_anterior)}</td>
                    <td className="numero-tabular">{dinero(c.diferencia)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </Panel>
      )}
    </ArmazonDelPortal>
  );
}
