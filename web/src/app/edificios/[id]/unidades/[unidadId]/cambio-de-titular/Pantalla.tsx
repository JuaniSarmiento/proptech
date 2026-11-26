"use client";

/**
 * Cambiar titular de una unidad (change 4d, H-034, R32, D-168): un formulario con la fecha, los
 * vendedores (los propietarios actuales), uno o más compradores, la expensa del mes y la deuda previa, cada
 * opción con su línea que explica qué pasa. Un solo paso, sin confirmación aparte. Con el 201, el resultado
 * (aviso de deuda, lo trasladado al vendedor, el prorrateo) reemplaza al formulario y el historial de la
 * unidad queda debajo. La pantalla no calcula nada: cada monto y cada día son los de la API (R07).
 */

import {
  type FormEvent,
  useActionState,
  useEffect,
  useId,
  useRef,
  useState,
  useTransition,
} from "react";
import { Ayuda } from "../../../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../../../componentes/EncabezadoDePantalla";
import { Campo, Formulario } from "../../../../../../componentes/Formulario";
import { Panel } from "../../../../../../componentes/Panel";
import type { CambioDeTitular, ProrrateoDelCambio } from "../../../../../../lib/api/titularidad";
import { dinero, fecha, mesYAnio } from "../../../../../../lib/formato";
import { ArmazonDelEdificio } from "../../../Armazon";
import type { EstadoDelCambio } from "./acciones";
import { AYUDA_CAMBIO_DE_TITULAR } from "./ayuda";
import { type BorradorDeCambio, hayQueElegirDeudor, validarBorrador } from "./validacion";

type Propietario = { persona_id: string; nombre: string };

type Props = {
  id: string;
  nombreEdificio: string;
  identificadorDeUnidad: string;
  propietarios: Propietario[];
  historial: CambioDeTitular[];
  accionRegistrar: (
    estadoPrevio: EstadoDelCambio,
    borrador: BorradorDeCambio,
  ) => Promise<EstadoDelCambio>;
};

const EXPENSA = {
  entera: "Entera",
  prorrateo: "Prorrateo por días",
} as const;

const DEUDA = {
  en_la_unidad: "Queda en la unidad",
  a_nombre_del_vendedor: "A nombre del vendedor",
} as const;

const EXPLICACION = {
  entera: "La expensa del mes completa queda en la unidad.",
  prorrateo:
    "El vendedor paga los días del mes anteriores a la fecha del cambio y la unidad el resto.",
  en_la_unidad:
    "La deuda de meses anteriores queda en la unidad y el comprador la hereda; se le avisa el monto.",
  a_nombre_del_vendedor:
    "La deuda de meses anteriores pasa a una cuenta del vendedor y la unidad queda sin ella.",
} as const;

/** El estado del prorrateo en palabras, con sus días y, si ya se aplicó, la parte del vendedor. */
function Prorrateo({ prorrateo }: { prorrateo: ProrrateoDelCambio }) {
  const dias = `${prorrateo.dias_del_vendedor} de ${prorrateo.dias_del_mes} días`;
  if (prorrateo.estado === "aplicado" && prorrateo.parte_del_vendedor !== null) {
    return (
      <>
        <strong>Aplicado</strong>
        {" · parte del vendedor "}
        <span className="numero-tabular">{dinero(prorrateo.parte_del_vendedor)}</span>
        {` · ${dias}`}
      </>
    );
  }
  return (
    <>
      <strong>Pendiente</strong>
      {` · período ${mesYAnio(prorrateo.periodo)} · ${dias}`}
    </>
  );
}

function Dato({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="titularidad__dato">
      <dt>{rotulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

type OpcionProps<V extends string> = {
  grupo: string;
  valor: V;
  etiqueta: string;
  explicacion: string;
  marcada: boolean;
  alElegir: (valor: V) => void;
};

/** Un radio cuya línea explicativa es su descripción (no parte de su nombre accesible). */
function Opcion<V extends string>({
  grupo,
  valor,
  etiqueta,
  explicacion,
  marcada,
  alElegir,
}: OpcionProps<V>) {
  const idRadio = useId();
  const idExplicacion = `${idRadio}-explicacion`;
  return (
    <div className="opcion">
      <input
        id={idRadio}
        type="radio"
        name={grupo}
        value={valor}
        checked={marcada}
        aria-describedby={idExplicacion}
        onChange={() => alElegir(valor)}
      />
      <div className="opcion__texto">
        <label htmlFor={idRadio}>{etiqueta}</label>
        <p id={idExplicacion} className="texto-secundario">
          {explicacion}
        </p>
      </div>
    </div>
  );
}

function ErroresDelGrupo({ id, mensajes }: { id: string; mensajes: string[] }) {
  return (
    <>
      {mensajes.map((mensaje) => (
        <p key={mensaje} id={id} className="campo__error">
          {mensaje}
        </p>
      ))}
    </>
  );
}

export function PantallaCambioDeTitular({
  id,
  nombreEdificio,
  identificadorDeUnidad,
  propietarios,
  historial,
  accionRegistrar,
}: Props) {
  const [estado, enviar] = useActionState(accionRegistrar, null);
  const [enCurso, empezar] = useTransition();
  const [borrador, setBorrador] = useState<BorradorDeCambio>({
    fecha: "",
    vendedores: [],
    compradores: [{ nombre: "", email: "" }],
    expensa: "entera",
    deuda: "en_la_unidad",
    deudor: "",
  });
  const [errores, setErrores] = useState<Record<string, string>>({});
  const regionRef = useRef<HTMLElement>(null);

  const registrado = estado?.registrado;

  // Lo que dice la API (un 422 por campo) se muestra en su campo y lleva el foco al primero.
  useEffect(() => {
    const deLaApi = estado?.erroresPorCampo;
    if (!deLaApi) return;
    setErrores(deLaApi);
    const primero = Object.keys(deLaApi)[0];
    if (primero) document.getElementById(`campo-${primero}`)?.focus();
  }, [estado]);

  useEffect(() => {
    if (registrado) regionRef.current?.focus();
  }, [registrado]);

  function cambiar(parcial: Partial<BorradorDeCambio>) {
    setBorrador((actual) => ({ ...actual, ...parcial }));
  }

  function marcarVendedor(personaId: string, marcado: boolean) {
    const vendedores = marcado
      ? [...borrador.vendedores, personaId]
      : borrador.vendedores.filter((v) => v !== personaId);
    cambiar({
      vendedores,
      deudor: vendedores.includes(borrador.deudor) ? borrador.deudor : "",
    });
  }

  function cambiarComprador(indice: number, parcial: { nombre?: string; email?: string }) {
    cambiar({
      compradores: borrador.compradores.map((c, i) => (i === indice ? { ...c, ...parcial } : c)),
    });
  }

  function alRegistrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const locales = validarBorrador(borrador);
    setErrores(locales);
    const primero = Object.keys(locales)[0];
    if (primero) {
      document.getElementById(`campo-${primero}`)?.focus();
      return;
    }
    empezar(() => enviar(borrador));
  }

  const hayDeudor = hayQueElegirDeudor(borrador);
  const erroresDeVendedores = [errores.vendedores, errores.vendedor_deudor].filter(
    (m): m is string => m !== undefined,
  );
  const sinPropietarios = propietarios.length === 0;

  let cuerpo: React.ReactNode;
  if (registrado) {
    const aviso = registrado.aviso;
    cuerpo = (
      <section
        ref={regionRef}
        tabIndex={-1}
        className="panel panel--principal titularidad__resultado"
        aria-label="Resultado del cambio de titular"
      >
        <div className="panel__encabezado">
          <div className="panel__textos">
            <h2>Cambio de titular registrado</h2>
            <p className="panel__descripcion">
              La unidad {identificadorDeUnidad} ya tiene a sus nuevos propietarios. Este paso no se
              deshace.
            </p>
          </div>
        </div>
        <dl className="titularidad__datos">
          <Dato rotulo="Aviso de deuda">
            {aviso === null ? (
              "La unidad no tiene deuda para avisar."
            ) : (
              <>
                {"La unidad queda con una deuda de "}
                <span className="numero-tabular">{dinero(aviso.deuda)}</span>.
              </>
            )}
          </Dato>
          {registrado.trasladado !== undefined && registrado.cuenta_del_vendedor ? (
            <Dato rotulo="Deuda pasada al vendedor">
              <span className="numero-tabular">{dinero(registrado.trasladado)}</span>
              <a
                className="boton-enlace"
                href={`/edificios/${id}/cuentas-de-vendedores/${registrado.cuenta_del_vendedor}`}
              >
                Ver la cuenta del vendedor
              </a>
            </Dato>
          ) : null}
          {registrado.prorrateo ? (
            <Dato rotulo="Prorrateo de la expensa">
              <Prorrateo prorrateo={registrado.prorrateo} />
            </Dato>
          ) : null}
        </dl>
        <a className="boton-enlace" href={`/edificios/${id}/unidades`}>
          Volver al padrón
        </a>
      </section>
    );
  } else if (sinPropietarios) {
    cuerpo = (
      <Panel
        titulo="Sin propietarios cargados"
        descripcion="Un cambio de titular necesita al menos un propietario actual que venda."
      >
        <p>Esta unidad no tiene propietarios en el padrón. Cargalos primero.</p>
        <a className="boton-enlace" href={`/edificios/${id}/unidades`}>
          Volver al padrón
        </a>
      </Panel>
    );
  } else {
    cuerpo = (
      <Panel
        titulo="Datos del cambio"
        descripcion="Un solo paso: al registrar, los propietarios de la unidad cambian."
      >
        <Formulario
          erroresPorCampo={errores}
          onSubmit={alRegistrar}
          aria-label={`Cambiar titular de ${identificadorDeUnidad}`}
        >
          <Campo
            nombre="fecha"
            etiqueta="Fecha del cambio"
            type="date"
            value={borrador.fecha}
            onChange={(e) => cambiar({ fecha: e.target.value })}
          />

          <fieldset
            id="campo-vendedores"
            tabIndex={-1}
            aria-describedby={erroresDeVendedores.length > 0 ? "campo-vendedores-error" : undefined}
          >
            <legend>Vendedores</legend>
            {propietarios.map((p) => (
              <Campo
                key={p.persona_id}
                nombre={`vendedor_${p.persona_id}`}
                etiqueta={p.nombre}
                type="checkbox"
                checked={borrador.vendedores.includes(p.persona_id)}
                onChange={(e) => marcarVendedor(p.persona_id, e.target.checked)}
              />
            ))}
            {hayDeudor ? (
              <div className="campo">
                <label htmlFor="campo-vendedor_deudor">Vendedor que queda con la deuda</label>
                <select
                  id="campo-vendedor_deudor"
                  value={borrador.deudor}
                  aria-invalid={errores.vendedor_deudor !== undefined}
                  onChange={(e) => cambiar({ deudor: e.target.value })}
                >
                  <option value="">Elegí un vendedor</option>
                  {borrador.vendedores.map((personaId) => (
                    <option key={personaId} value={personaId}>
                      {propietarios.find((p) => p.persona_id === personaId)?.nombre ??
                        "Propietario"}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
            <ErroresDelGrupo id="campo-vendedores-error" mensajes={erroresDeVendedores} />
          </fieldset>

          <fieldset
            id="campo-compradores"
            tabIndex={-1}
            aria-describedby={errores.compradores ? "campo-compradores-error" : undefined}
          >
            <legend>Compradores</legend>
            {borrador.compradores.map((comprador, indice) => {
              const numero = indice + 1;
              return (
                // biome-ignore lint/suspicious/noArrayIndexKey: filas sin identidad propia; el orden es el del pedido.
                <div key={indice} className="titularidad__comprador">
                  <Campo
                    nombre={`comprador_${numero}_nombre`}
                    etiqueta={`Nombre del comprador ${numero}`}
                    autoComplete="off"
                    value={comprador.nombre}
                    onChange={(e) => cambiarComprador(indice, { nombre: e.target.value })}
                  />
                  <Campo
                    nombre={`comprador_${numero}_email`}
                    etiqueta={`Email del comprador ${numero} (opcional)`}
                    inputMode="email"
                    autoComplete="off"
                    value={comprador.email}
                    onChange={(e) => cambiarComprador(indice, { email: e.target.value })}
                  />
                  {indice > 0 ? (
                    <button
                      type="button"
                      className="boton-enlace"
                      onClick={() =>
                        cambiar({
                          compradores: borrador.compradores.filter((_, i) => i !== indice),
                        })
                      }
                    >
                      {`Quitar comprador ${numero}`}
                    </button>
                  ) : null}
                </div>
              );
            })}
            <button
              type="button"
              onClick={() =>
                cambiar({ compradores: [...borrador.compradores, { nombre: "", email: "" }] })
              }
            >
              Agregar otro comprador
            </button>
            <ErroresDelGrupo
              id="campo-compradores-error"
              mensajes={errores.compradores ? [errores.compradores] : []}
            />
          </fieldset>

          <fieldset
            id="campo-expensa_del_mes"
            tabIndex={-1}
            aria-describedby={errores.expensa_del_mes ? "campo-expensa_del_mes-error" : undefined}
          >
            <legend>Expensa del mes</legend>
            {(["entera", "prorrateo"] as const).map((valor) => (
              <Opcion
                key={valor}
                grupo="expensa_del_mes"
                valor={valor}
                etiqueta={EXPENSA[valor]}
                explicacion={EXPLICACION[valor]}
                marcada={borrador.expensa === valor}
                alElegir={(v) => cambiar({ expensa: v })}
              />
            ))}
            <ErroresDelGrupo
              id="campo-expensa_del_mes-error"
              mensajes={errores.expensa_del_mes ? [errores.expensa_del_mes] : []}
            />
          </fieldset>

          <fieldset
            id="campo-deuda_previa"
            tabIndex={-1}
            aria-describedby={errores.deuda_previa ? "campo-deuda_previa-error" : undefined}
          >
            <legend>Deuda previa</legend>
            {(["en_la_unidad", "a_nombre_del_vendedor"] as const).map((valor) => (
              <Opcion
                key={valor}
                grupo="deuda_previa"
                valor={valor}
                etiqueta={DEUDA[valor]}
                explicacion={EXPLICACION[valor]}
                marcada={borrador.deuda === valor}
                alElegir={(v) => cambiar({ deuda: v })}
              />
            ))}
            <ErroresDelGrupo
              id="campo-deuda_previa-error"
              mensajes={errores.deuda_previa ? [errores.deuda_previa] : []}
            />
          </fieldset>

          <button type="submit" className="boton-principal" disabled={enCurso} aria-busy={enCurso}>
            {enCurso ? "Registrando…" : "Registrar cambio de titular"}
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
      <EncabezadoDePantalla
        titulo={`Cambiar titular de ${identificadorDeUnidad}`}
        ayuda={<Ayuda {...AYUDA_CAMBIO_DE_TITULAR} />}
      />
      {registrado || sinPropietarios ? null : (
        <p>
          <a className="boton-enlace" href={`/edificios/${id}/unidades`}>
            Volver al padrón
          </a>
        </p>
      )}
      {cuerpo}
      <div id="historial">
        <Panel
          titulo="Historial de la unidad"
          descripcion="Los cambios de titular que ya se registraron, el más nuevo primero."
        >
          {historial.length === 0 ? (
            <p role="status" className="texto-secundario">
              Esta unidad todavía no tuvo cambios de titular
            </p>
          ) : (
            <ul className="lista-de-filas" aria-label="Historial de cambios de titular">
              {historial.map((cambio) => (
                <li key={cambio.id} className="titularidad__cambio">
                  <strong className="titularidad__fecha">{fecha(cambio.fecha)}</strong>
                  <dl className="titularidad__datos">
                    <Dato rotulo="Vendedores">
                      {(cambio.vendedores_detalle ?? []).map((v) => v.nombre).join(", ")}
                    </Dato>
                    <Dato rotulo="Compradores">
                      {cambio.compradores.map((c) => c.nombre).join(", ")}
                    </Dato>
                    <Dato rotulo="Expensa del mes">
                      {EXPENSA[cambio.expensa_del_mes]}
                      {cambio.prorrateo ? (
                        <>
                          {" · "}
                          <Prorrateo prorrateo={cambio.prorrateo} />
                        </>
                      ) : null}
                    </Dato>
                    <Dato rotulo="Deuda previa">
                      {DEUDA[cambio.deuda_previa]}
                      {cambio.trasladado !== undefined && cambio.cuenta_del_vendedor ? (
                        <>
                          {" · Deuda pasada al vendedor "}
                          <span className="numero-tabular">{dinero(cambio.trasladado)}</span>
                        </>
                      ) : null}
                    </Dato>
                  </dl>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </ArmazonDelEdificio>
  );
}
