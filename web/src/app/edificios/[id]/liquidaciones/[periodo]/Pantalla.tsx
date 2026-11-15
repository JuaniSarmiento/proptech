"use client";

/**
 * Preliquidación de un período (change 7, H-011, HU-A4): una tabla "Lo que paga cada unidad"
 * (ordinaria, fondo de reserva, extraordinaria, cargos particulares, intereses y total, una fila
 * por unidad; sin la columna del fondo si el porcentaje es 0), los bloques Ordinaria y
 * Extraordinaria con sus categorías, los grupos de reparto y, al costado, los totales de la
 * liquidación. La pantalla sólo formatea: no suma ni compara montos (R07, D-046). Mirarla no
 * escribe nada en ninguna parte.
 *
 * Un 409 (el período ya emitido, el anterior sin emitir, una configuración o un grupo que falta)
 * se dice con un mensaje propio, traducido de su código; nunca un texto de la API (L-007).
 */

import type { ReactNode } from "react";
import { Ayuda } from "../../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../../componentes/EncabezadoDePantalla";
import { Panel } from "../../../../../componentes/Panel";
import type {
  BloqueDeGastos,
  Preliquidacion,
  UnidadPreliquidada,
} from "../../../../../lib/api/liquidaciones";
import { dinero, fecha, porcentaje } from "../../../../../lib/formato";
import { ArmazonDelEdificio } from "../../Armazon";
import { AYUDA_PRELIQUIDACION } from "./ayuda";

type PropsComunes = {
  id: string;
  nombreEdificio: string;
  periodoEnPalabras: string;
};

const METODOS: Record<string, string> = {
  coeficiente: "Por coeficiente",
  superficie: "Por superficie",
  partes_iguales: "En partes iguales",
};

function tieneFondo(preliquidacion: Preliquidacion): boolean {
  return preliquidacion.porcentaje_fondo !== "0.00";
}

/** A 320 px la tabla se desplaza dentro de su caja; sin ningún control adentro, el teclado no
 * llegaría a ese desplazamiento (axe: scrollable-region-focusable), así que la caja se enfoca. */
function CajaConDesplazamiento({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <section
      className="padron-de-unidades__scroll"
      aria-label={etiqueta}
      // biome-ignore lint/a11y/noNoninteractiveTabindex: región con desplazamiento, sin controles.
      tabIndex={0}
    >
      {children}
    </section>
  );
}

function CeldaDeCargos({ unidad }: { unidad: UnidadPreliquidada }) {
  if (unidad.cargos_particulares.length === 0) {
    return <>{dinero("0.00")}</>;
  }
  return (
    <>
      {unidad.cargos_particulares.map((cargo, indice) => (
        // El orden lo fija la API; el índice basta porque la lista no se reordena en pantalla.
        // biome-ignore lint/suspicious/noArrayIndexKey: lista fija sin identificador propio.
        <div key={`${cargo.concepto}-${indice}`}>
          {dinero(cargo.importe)}
          <span className="texto-secundario"> {cargo.concepto}</span>
        </div>
      ))}
    </>
  );
}

function TablaDeUnidades({ preliquidacion }: { preliquidacion: Preliquidacion }) {
  const conFondo = tieneFondo(preliquidacion);
  return (
    <CajaConDesplazamiento etiqueta="Unidades, con desplazamiento horizontal">
      <table className="padron-de-unidades padron-de-unidades--envuelto">
        <caption className="sr-only">Lo que paga cada unidad</caption>
        <thead>
          <tr>
            <th scope="col">Unidad</th>
            <th scope="col" className="numero-tabular">
              Ordinaria
            </th>
            {conFondo ? (
              <th scope="col" className="numero-tabular">
                Fondo de reserva
              </th>
            ) : null}
            <th scope="col" className="numero-tabular">
              Extraordinaria
            </th>
            <th scope="col" className="numero-tabular">
              Cargos particulares
            </th>
            <th scope="col" className="numero-tabular">
              Intereses
            </th>
            <th scope="col" className="numero-tabular">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {preliquidacion.unidades.map((unidad) => (
            <tr key={unidad.unidad_id}>
              <td>{unidad.identificador}</td>
              <td className="numero-tabular">{dinero(unidad.ordinaria)}</td>
              {conFondo ? (
                <td className="numero-tabular">{dinero(unidad.fondo_de_reserva)}</td>
              ) : null}
              <td className="numero-tabular">{dinero(unidad.extraordinaria)}</td>
              <td className="numero-tabular">
                <CeldaDeCargos unidad={unidad} />
              </td>
              <td className="numero-tabular">{dinero(unidad.intereses)}</td>
              <td className="numero-tabular">
                {dinero(unidad.total)}
                {unidad.sin_obligacion ? (
                  <div className="texto-secundario">Sin obligación este período</div>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </CajaConDesplazamiento>
  );
}

function BloqueDelPeriodo({
  titulo,
  descripcion,
  bloque,
}: {
  titulo: string;
  descripcion: string;
  bloque: BloqueDeGastos;
}) {
  return (
    <Panel titulo={titulo} descripcion={descripcion}>
      {bloque.categorias.length === 0 ? (
        <p className="texto-secundario">No hay gastos de este tipo en el período.</p>
      ) : (
        <CajaConDesplazamiento etiqueta={`Categorías del bloque ${titulo.toLowerCase()}`}>
          <table className="padron-de-unidades padron-de-unidades--envuelto">
            <caption className="sr-only">Gastos por categoría</caption>
            <thead>
              <tr>
                <th scope="col">Categoría</th>
                <th scope="col" className="numero-tabular">
                  Importe
                </th>
                <th scope="col" className="numero-tabular">
                  Porcentaje
                </th>
              </tr>
            </thead>
            <tbody>
              {bloque.categorias.map((categoria) => (
                <tr key={categoria.categoria_id}>
                  <td>{categoria.nombre}</td>
                  <td className="numero-tabular">{dinero(categoria.importe)}</td>
                  <td className="numero-tabular">{porcentaje(categoria.porcentaje)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">Subtotal</th>
                <td className="numero-tabular">{dinero(bloque.subtotal)}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </CajaConDesplazamiento>
      )}
    </Panel>
  );
}

function TablaDeGrupos({ preliquidacion }: { preliquidacion: Preliquidacion }) {
  return (
    <CajaConDesplazamiento etiqueta="Grupos de reparto, con desplazamiento horizontal">
      <table className="padron-de-unidades padron-de-unidades--envuelto">
        <caption className="sr-only">Grupos de reparto con gastos en el período</caption>
        <thead>
          <tr>
            <th scope="col">Grupo</th>
            <th scope="col">Método</th>
            <th scope="col" className="numero-tabular">
              Gasto ordinario
            </th>
            <th scope="col" className="numero-tabular">
              Gasto extraordinario
            </th>
          </tr>
        </thead>
        <tbody>
          {preliquidacion.grupos.map((grupo) => (
            <tr key={grupo.grupo_id}>
              <td>{grupo.nombre}</td>
              <td>{METODOS[grupo.metodo] ?? "Otro método"}</td>
              <td className="numero-tabular">{dinero(grupo.ordinario)}</td>
              <td className="numero-tabular">{dinero(grupo.extraordinario)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </CajaConDesplazamiento>
  );
}

function Renglon({
  etiqueta,
  valor,
  fuerte,
}: {
  etiqueta: string;
  valor: string;
  fuerte?: boolean;
}) {
  return (
    <div className="renglones__fila">
      <dt>{etiqueta}</dt>
      <dd className="numero-tabular">{fuerte ? <strong>{valor}</strong> : valor}</dd>
    </div>
  );
}

function TotalesDeLaLiquidacion({ preliquidacion }: { preliquidacion: Preliquidacion }) {
  const { totales } = preliquidacion;
  return (
    <Panel titulo="Totales" variante="apoyo">
      <dl className="renglones">
        <Renglon etiqueta="Gastos" valor={dinero(totales.gastos)} />
        <Renglon etiqueta="Notas de crédito" valor={dinero(totales.notas_de_credito)} />
        {tieneFondo(preliquidacion) ? (
          <Renglon etiqueta="Fondo de reserva" valor={dinero(totales.fondo_de_reserva)} />
        ) : null}
        <Renglon etiqueta="Prorrateado" valor={dinero(totales.prorrateado)} />
        <Renglon etiqueta="Cargos particulares" valor={dinero(totales.cargos_particulares)} />
        <Renglon etiqueta="Intereses" valor={dinero(totales.intereses)} />
        <Renglon etiqueta="Total de la liquidación" valor={dinero(totales.total)} fuerte />
      </dl>
    </Panel>
  );
}

export function PantallaPreliquidacion({
  id,
  nombreEdificio,
  periodoEnPalabras,
  preliquidacion,
}: PropsComunes & { preliquidacion: Preliquidacion }) {
  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="liquidaciones">
      <EncabezadoDePantalla
        titulo={`Preliquidación de ${periodoEnPalabras}`}
        ayuda={<Ayuda {...AYUDA_PRELIQUIDACION} />}
      />
      <div className="disposicion">
        <div>
          <Panel
            titulo="Lo que paga cada unidad"
            descripcion={
              tieneFondo(preliquidacion)
                ? `Vence el ${fecha(preliquidacion.vencimiento)}. El fondo de reserva es el ${porcentaje(preliquidacion.porcentaje_fondo)} de la ordinaria.`
                : `Vence el ${fecha(preliquidacion.vencimiento)}.`
            }
          >
            <TablaDeUnidades preliquidacion={preliquidacion} />
          </Panel>
          <BloqueDelPeriodo
            titulo="Ordinaria"
            descripcion="Los gastos de todos los meses, ya con las notas de crédito restadas."
            bloque={preliquidacion.bloques.ordinario}
          />
          <BloqueDelPeriodo
            titulo="Extraordinaria"
            descripcion="Los gastos que no se repiten todos los meses."
            bloque={preliquidacion.bloques.extraordinario}
          />
          {preliquidacion.grupos.length > 0 ? (
            <Panel
              titulo="Grupos de reparto"
              descripcion="Cada gasto se reparte entre las unidades de su grupo, según el método del grupo."
            >
              <TablaDeGrupos preliquidacion={preliquidacion} />
            </Panel>
          ) : null}
        </div>
        <div className="disposicion__lateral">
          <TotalesDeLaLiquidacion preliquidacion={preliquidacion} />
        </div>
      </div>
    </ArmazonDelEdificio>
  );
}

type Aviso = { titulo: string; detalle: string; enlace?: { texto: string; ruta: string } };

/** El mensaje de cada 409 que la API sabe dar, por su código. Un código que no conoce recibe un
 * mensaje genérico: el texto de la API nunca llega a la pantalla (L-007). */
function avisoDeConflicto(id: string, campo: string, motivo: string): Aviso {
  if (campo === "periodo" && motivo === "periodo_anterior_sin_emitir") {
    return {
      titulo: "Falta emitir el período anterior.",
      detalle:
        "Los períodos se emiten en orden: para preparar este, el período anterior tiene que estar emitido.",
    };
  }
  if (campo === "periodo" && motivo === "periodo_emitido") {
    return {
      titulo: "Este período ya está emitido.",
      detalle: "Un período emitido no se vuelve a preparar, salvo que se anule su emisión.",
    };
  }
  if (campo === "configuracion") {
    return {
      titulo: "Falta configurar los intereses y el vencimiento de este edificio.",
      detalle: "Sin esa configuración no se puede calcular el fondo de reserva ni el vencimiento.",
      enlace: { texto: "Ir a intereses y vencimiento", ruta: `/edificios/${id}/configuracion` },
    };
  }
  if (campo === "grupo") {
    return {
      titulo: "Un grupo de reparto no tiene con qué repartir sus gastos.",
      detalle:
        "Revisá que el grupo tenga unidades y, si se reparte por superficie, que sus unidades tengan superficie cargada.",
      enlace: { texto: "Ir a grupos", ruta: `/edificios/${id}/grupos` },
    };
  }
  return {
    titulo: "No se puede preparar este período ahora.",
    detalle: "Revisá el estado del edificio y volvé a intentar.",
  };
}

/** El 409 de la preliquidación: el mensaje y nada de tabla, porque no hay nada que mostrar. */
export function PantallaSinPreliquidar({
  id,
  nombreEdificio,
  periodoEnPalabras,
  campo,
  motivo,
}: PropsComunes & { campo: string; motivo: string }) {
  const aviso = avisoDeConflicto(id, campo, motivo);
  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="liquidaciones">
      <EncabezadoDePantalla
        titulo={`Preliquidación de ${periodoEnPalabras}`}
        ayuda={<Ayuda {...AYUDA_PRELIQUIDACION} />}
      />
      <Panel titulo="No se puede preparar este período">
        <p role="alert" className="campo__error">
          <strong>{aviso.titulo}</strong> {aviso.detalle}
        </p>
        {aviso.enlace ? (
          <a className="boton-enlace" href={aviso.enlace.ruta}>
            {aviso.enlace.texto}
          </a>
        ) : null}
      </Panel>
    </ArmazonDelEdificio>
  );
}
