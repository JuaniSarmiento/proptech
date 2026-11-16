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

import { type ReactNode, useActionState, useEffect, useRef, useState } from "react";
import { useFormStatus } from "react-dom";
import { Ayuda } from "../../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../../componentes/EncabezadoDePantalla";
import { Campo } from "../../../../../componentes/Formulario";
import { Panel } from "../../../../../componentes/Panel";
import { PanelLateral } from "../../../../../componentes/PanelLateral";
import { permite, useSesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type { DocumentoDeExpensa } from "../../../../../lib/api/documentos";
import type {
  BloqueDeGastos,
  ControlAntesDeEmitir,
  EmisionRegistrada,
  EstadoDeLaLiquidacion,
  LiquidacionDeLaLista,
  NivelDeControl,
  Preliquidacion,
  UnidadPreliquidada,
} from "../../../../../lib/api/liquidaciones";
import { dinero, fecha, porcentaje } from "../../../../../lib/formato";
import { ArmazonDelEdificio } from "../../Armazon";
import { AYUDA_PRELIQUIDACION } from "./ayuda";
import { Documentos, type EstadoDeDescarga, type EstadoDeReproceso } from "./Documentos";

export type EstadoEmision = { error?: string; emitida?: EmisionRegistrada } | null;

type AccionEmitir = (estadoPrevio: EstadoEmision, formData: FormData) => Promise<EstadoEmision>;

/** Lo que devuelve distribuir o anular (H-014): el error ya dicho para la pantalla, o lo que quedó. */
export type EstadoCiclo = { error?: string; hecho?: "distribuida" | "anulada" } | null;

type AccionDelCiclo = (estadoPrevio: EstadoCiclo, formData: FormData) => Promise<EstadoCiclo>;

const MOTIVO_MAXIMO = 500;

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

const NIVELES: Record<NivelDeControl, string> = {
  duro: "Duro",
  bloqueante: "Bloqueante",
  advertencia: "Advertencia",
};

/** Los controles de R34 (H-012), en el orden de la API. El nivel va en texto, nunca sólo en color;
 * un control duro dice además que no se puede aceptar. Mostrarlos no escribe nada. */
function ControlesAntesDeEmitir({ controles }: { controles: ControlAntesDeEmitir[] }) {
  return (
    <Panel
      titulo="Controles antes de emitir"
      descripcion="Lo que hay que revisar antes de emitir este período."
    >
      {controles.length === 0 ? (
        <p className="texto-secundario">No hay controles pendientes.</p>
      ) : (
        <ul className="lista-de-filas">
          {controles.map((control) => (
            <li key={control.codigo}>
              <strong>{NIVELES[control.nivel] ?? "Control"}</strong>
              {": "}
              {control.mensaje}
              {control.nivel === "duro" ? (
                <span className="texto-secundario"> Este control no se puede aceptar.</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

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

function LiquidacionEmitida({
  periodoEnPalabras,
  emision,
  total,
  regionRef,
}: {
  periodoEnPalabras: string;
  emision: EmisionRegistrada;
  total: string;
  regionRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <div ref={regionRef} tabIndex={-1} className="comparacion__aceptadas">
      <Panel
        titulo="Liquidación emitida"
        descripcion={`Quedó emitida la liquidación de ${periodoEnPalabras}. Este paso no se deshace.`}
      >
        <dl className="renglones">
          <Renglon etiqueta="Período" valor={periodoEnPalabras} />
          <Renglon etiqueta="Total de la liquidación" valor={dinero(total)} fuerte />
          <Renglon etiqueta="Vence el" valor={fecha(emision.vencimiento)} />
          <Renglon etiqueta="Unidades con obligación" valor={String(emision.obligaciones.length)} />
        </dl>
      </Panel>
    </div>
  );
}

/** La confirmación de emitir: dice que no se deshace, con el período y el total; cada bloqueante
 * activo se acepta con su casilla (un duro no tiene casilla: con uno activo ni se abre) y el
 * vencimiento se puede correr con su motivo. "Confirmar" espera a que estén todas marcadas. */
function ConfirmarEmision({
  periodo,
  periodoEnPalabras,
  preliquidacion,
  emisionId,
  puedeAceptar,
  accion,
  alCancelar,
  error,
}: {
  periodo: string;
  periodoEnPalabras: string;
  preliquidacion: Preliquidacion;
  emisionId: string;
  puedeAceptar: boolean;
  accion: (formData: FormData) => void;
  alCancelar: () => void;
  error: string | undefined;
}) {
  const bloqueantes = preliquidacion.controles.filter((c) => c.nivel === "bloqueante");
  const advertencias = preliquidacion.controles.filter((c) => c.nivel === "advertencia");
  const [aceptados, setAceptados] = useState<Set<string>>(new Set());
  const [corrida, setCorrida] = useState(false);
  const faltan = bloqueantes.some((c) => !aceptados.has(c.codigo));

  function marcar(codigo: string, marcado: boolean) {
    setAceptados((previos) => {
      const siguientes = new Set(previos);
      if (marcado) siguientes.add(codigo);
      else siguientes.delete(codigo);
      return siguientes;
    });
  }

  return (
    <div className="panel-lateral__seccion">
      <p>
        Vas a emitir la liquidación de {periodoEnPalabras} por{" "}
        {dinero(preliquidacion.totales.total)}. Esta emisión no se deshace: cada unidad queda con su
        deuda en la cuenta corriente y lo que cambie después no modifica lo emitido.
      </p>
      <form action={accion}>
        <input type="hidden" name="emision_id" value={emisionId} />
        <input type="hidden" name="huella" value={preliquidacion.huella} />
        {bloqueantes.length > 0 ? (
          <fieldset className="emision__alertas">
            <legend>Alertas que hay que aceptar</legend>
            {bloqueantes.map((control) => (
              <Campo
                key={control.codigo}
                nombre={`aceptar_${control.codigo}`}
                etiqueta={`Acepto: ${control.mensaje}`}
                type="checkbox"
                name="alerta"
                value={control.codigo}
                checked={aceptados.has(control.codigo)}
                disabled={!puedeAceptar}
                onChange={(e) => marcar(control.codigo, e.target.checked)}
              />
            ))}
            {!puedeAceptar ? (
              <p className="texto-secundario">
                No tenés permiso para aceptar alertas en este edificio. Lo hace el administrador
                principal.
              </p>
            ) : null}
          </fieldset>
        ) : null}
        {advertencias.length > 0 ? (
          <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Advertencias">
            {advertencias.map((control) => (
              <li key={control.codigo}>
                <strong>{NIVELES[control.nivel]}</strong>
                {": "}
                {control.mensaje}
                <span className="texto-secundario"> No hace falta aceptarla.</span>
              </li>
            ))}
          </ul>
        ) : null}
        <Campo
          nombre="correr_vencimiento"
          etiqueta="Correr el vencimiento"
          type="checkbox"
          name="correr_vencimiento"
          checked={corrida}
          onChange={(e) => setCorrida(e.target.checked)}
        />
        {corrida ? (
          <>
            <Campo
              nombre="vencimiento_fecha"
              etiqueta="Nuevo vencimiento"
              type="date"
              name="vencimiento_fecha"
              min={periodo}
              required
            />
            <Campo
              nombre="motivo_del_vencimiento"
              etiqueta="Motivo"
              name="motivo_del_vencimiento"
              autoComplete="off"
              maxLength={MOTIVO_MAXIMO}
              required
            />
          </>
        ) : (
          <p className="texto-secundario">
            Vence el {fecha(preliquidacion.vencimiento)}, el día de la configuración del edificio.
          </p>
        )}
        <div className="panel-lateral__acciones">
          <button type="button" className="boton-secundario" onClick={alCancelar}>
            Cancelar
          </button>
          <ConfirmarConEspera deshabilitado={faltan || (bloqueantes.length > 0 && !puedeAceptar)} />
        </div>
      </form>
      {error ? (
        <p role="alert" className="campo__error">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function ConfirmarConEspera({ deshabilitado }: { deshabilitado: boolean }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      className="boton-principal"
      disabled={deshabilitado || pending}
      aria-busy={pending}
    >
      {pending ? "Emitiendo…" : "Confirmar"}
    </button>
  );
}

export function PantallaPreliquidacion({
  id,
  nombreEdificio,
  periodoEnPalabras,
  preliquidacion,
  accionEmitir,
}: PropsComunes & { preliquidacion: Preliquidacion; accionEmitir?: AccionEmitir }) {
  const sesion = useSesionDePantalla();
  const puedeEmitir =
    accionEmitir !== undefined && permite(sesion, "emitir_y_distribuir_liquidacion", id);
  const puedeAceptar = permite(sesion, "aceptar_alertas_bloqueantes", id);
  const hayDuro = preliquidacion.controles.some((c) => c.nivel === "duro");
  const [estado, enviar] = useActionState(accionEmitir ?? (async () => null), null);
  const [abierta, setAbierta] = useState(false);
  const [emisionId, setEmisionId] = useState("");
  const botonRef = useRef<HTMLButtonElement>(null);
  const regionRef = useRef<HTMLDivElement>(null);
  const emitida = estado?.emitida;

  // Al emitir, el botón desaparece: el foco va a la región que apareció.
  const hayEmitida = emitida !== undefined;
  useEffect(() => {
    if (hayEmitida) {
      regionRef.current?.focus();
    }
  }, [hayEmitida]);

  function abrir() {
    // Un `emision_id` por cada vez que se abre la confirmación: si el pedido se repite, la API
    // contesta lo mismo en vez de emitir dos veces.
    setEmisionId(crypto.randomUUID());
    setAbierta(true);
  }

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="liquidaciones">
      <EncabezadoDePantalla
        titulo={`Preliquidación de ${periodoEnPalabras}`}
        ayuda={<Ayuda {...AYUDA_PRELIQUIDACION} />}
        accionPrincipal={
          puedeEmitir && !emitida ? (
            <button
              ref={botonRef}
              type="button"
              className="boton-principal"
              disabled={hayDuro}
              onClick={abrir}
            >
              Emitir liquidación
            </button>
          ) : null
        }
      />
      <div className="disposicion">
        <div>
          {emitida ? (
            <LiquidacionEmitida
              periodoEnPalabras={periodoEnPalabras}
              emision={emitida}
              total={preliquidacion.totales.total}
              regionRef={regionRef}
            />
          ) : null}
          <ControlesAntesDeEmitir controles={preliquidacion.controles} />
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
      {puedeEmitir ? (
        <PanelLateral
          abierto={abierta && !hayEmitida}
          titulo="Emitir liquidación"
          alCerrar={() => setAbierta(false)}
          devolverFocoA={botonRef}
        >
          <ConfirmarEmision
            periodo={preliquidacion.periodo}
            periodoEnPalabras={periodoEnPalabras}
            preliquidacion={preliquidacion}
            emisionId={emisionId}
            puedeAceptar={puedeAceptar}
            accion={enviar}
            alCancelar={() => setAbierta(false)}
            error={estado?.error}
          />
        </PanelLateral>
      ) : null}
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

const ESTADOS: Record<EstadoDeLaLiquidacion, string> = {
  emitida: "Emitida",
  distribuida: "Distribuida",
  anulada: "Anulada",
};

function ConfirmarCiclo({
  deshabilitado,
  texto,
  enCurso,
}: {
  deshabilitado: boolean;
  texto: string;
  enCurso: string;
}) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      className="boton-principal"
      disabled={deshabilitado || pending}
      aria-busy={pending}
    >
      {pending ? enCurso : texto}
    </button>
  );
}

/** El período ya emitido (H-014): la liquidación con su estado en texto y su total. Una emitida se
 * distribuye o se anula; una distribuida ya no ofrece ninguna de las dos (desde ahí no se anula).
 * Las dos piden confirmación, y anular pide además el motivo. */
export function PantallaLiquidacionEmitida({
  id,
  nombreEdificio,
  periodoEnPalabras,
  liquidacion,
  accionDistribuir,
  accionAnular,
  documentos,
  accionReprocesar,
  accionDescargar,
}: PropsComunes & {
  liquidacion: LiquidacionDeLaLista;
  accionDistribuir?: AccionDelCiclo;
  accionAnular?: AccionDelCiclo;
  /** Los documentos de la liquidación (H-015); `null` si no se pudieron leer, `undefined` si la
   * pantalla no los pide (los tests de H-014). */
  documentos?: DocumentoDeExpensa[] | null;
  accionReprocesar?: (e: EstadoDeReproceso, f: FormData) => Promise<EstadoDeReproceso>;
  accionDescargar?: (e: EstadoDeDescarga, f: FormData) => Promise<EstadoDeDescarga>;
}) {
  const sesion = useSesionDePantalla();
  const esEmitida = liquidacion.estado === "emitida";
  const puedeDistribuir =
    esEmitida &&
    accionDistribuir !== undefined &&
    permite(sesion, "emitir_y_distribuir_liquidacion", id);
  const puedeAnular =
    esEmitida && accionAnular !== undefined && permite(sesion, "anular_liquidacion", id);
  const [estadoDistribuir, distribuir] = useActionState(
    accionDistribuir ?? (async () => null),
    null,
  );
  const [estadoAnular, anular] = useActionState(accionAnular ?? (async () => null), null);
  const [modo, setModo] = useState<"distribuir" | "anular" | null>(null);
  const [motivo, setMotivo] = useState("");
  const ultimoBoton = useRef<HTMLElement | null>(null);
  const hecho = estadoDistribuir?.hecho ?? estadoAnular?.hecho;
  const error = modo === "distribuir" ? estadoDistribuir?.error : estadoAnular?.error;

  function abrir(nuevo: "distribuir" | "anular", boton: HTMLElement) {
    ultimoBoton.current = boton;
    setMotivo("");
    setModo(nuevo);
  }

  const acciones =
    puedeDistribuir || puedeAnular ? (
      <>
        {puedeDistribuir ? (
          <button
            type="button"
            className="boton-principal"
            onClick={(e) => abrir("distribuir", e.currentTarget)}
          >
            Distribuir
          </button>
        ) : null}
        {puedeAnular ? (
          <button
            type="button"
            className="boton-secundario"
            onClick={(e) => abrir("anular", e.currentTarget)}
          >
            Anular
          </button>
        ) : null}
      </>
    ) : null;

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="liquidaciones">
      <EncabezadoDePantalla
        titulo={`Liquidación de ${periodoEnPalabras}`}
        ayuda={<Ayuda {...AYUDA_PRELIQUIDACION} />}
        accionPrincipal={acciones}
      />
      <Panel
        titulo="Liquidación emitida"
        descripcion={
          esEmitida
            ? "Está emitida y todavía no se distribuyó: mientras tanto se puede anular con su motivo."
            : liquidacion.estado === "distribuida"
              ? "Ya se distribuyó: desde ahí no se anula."
              : "Está anulada: la deuda de cada unidad volvió a la de antes de emitirla."
        }
      >
        <dl className="renglones">
          <Renglon etiqueta="Período" valor={periodoEnPalabras} />
          <Renglon etiqueta="Estado" valor={ESTADOS[liquidacion.estado]} />
          <Renglon etiqueta="Total de la liquidación" valor={dinero(liquidacion.total)} fuerte />
        </dl>
        {hecho ? (
          <p role="status">
            {hecho === "distribuida"
              ? "La liquidación quedó distribuida."
              : "La liquidación quedó anulada."}
          </p>
        ) : null}
      </Panel>
      {documentos !== undefined ? (
        <Documentos
          id={id}
          documentos={documentos}
          accionReprocesar={accionReprocesar}
          accionDescargar={accionDescargar}
        />
      ) : null}
      {puedeDistribuir || puedeAnular ? (
        <PanelLateral
          abierto={modo !== null && !hecho}
          titulo={modo === "anular" ? "Anular liquidación" : "Distribuir liquidación"}
          alCerrar={() => setModo(null)}
          devolverFocoA={ultimoBoton}
        >
          <div className="panel-lateral__seccion">
            {modo === "anular" ? (
              <>
                <p>
                  Vas a anular la liquidación de {periodoEnPalabras} por {dinero(liquidacion.total)}
                  . La deuda de cada unidad vuelve a la de antes de emitirla; el libro conserva todo
                  lo registrado. Si ya se distribuyó, no se puede anular.
                </p>
                <form action={anular}>
                  <Campo
                    nombre="motivo"
                    etiqueta="Motivo"
                    name="motivo"
                    autoComplete="off"
                    maxLength={MOTIVO_MAXIMO}
                    required
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                  />
                  <div className="panel-lateral__acciones">
                    <button
                      type="button"
                      className="boton-secundario"
                      onClick={() => setModo(null)}
                    >
                      Cancelar
                    </button>
                    <ConfirmarCiclo
                      deshabilitado={motivo.trim() === ""}
                      texto="Confirmar"
                      enCurso="Anulando…"
                    />
                  </div>
                </form>
              </>
            ) : (
              <>
                <p>
                  Vas a distribuir la liquidación de {periodoEnPalabras} por{" "}
                  {dinero(liquidacion.total)}. Una vez distribuida, ya no se puede anular.
                </p>
                <form action={distribuir}>
                  <div className="panel-lateral__acciones">
                    <button
                      type="button"
                      className="boton-secundario"
                      onClick={() => setModo(null)}
                    >
                      Cancelar
                    </button>
                    <ConfirmarCiclo
                      deshabilitado={false}
                      texto="Confirmar"
                      enCurso="Distribuyendo…"
                    />
                  </div>
                </form>
              </>
            )}
            {error ? (
              <p role="alert" className="campo__error">
                {error}
              </p>
            ) : null}
          </div>
        </PanelLateral>
      ) : null}
    </ArmazonDelEdificio>
  );
}
