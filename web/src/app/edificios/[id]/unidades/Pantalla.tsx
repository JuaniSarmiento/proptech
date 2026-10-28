"use client";

/**
 * Padrón de unidades (tarea 4.3, D6, D8; enmienda del 20/10/2026): la tabla
 * grande en el panel principal y, al costado, la suma de coeficientes, las
 * unidades por tipo y qué falta. La suma y su estado vienen de la API (D2,
 * "la web no calcula"); lo único que se cuenta acá son unidades por tipo
 * (conteos, nunca plata ni coeficientes). Tocar una fila o "Agregar
 * unidad" abre el panel lateral con el formulario; guardar cierra el
 * panel, devuelve el foco y muestra lo que da la API (tras revalidar, D1).
 */

import {
  Car,
  CircleCheck,
  CircleDashed,
  DoorOpen,
  type LucideIcon,
  Package,
  Store,
} from "lucide-react";
import { type FormEvent, useActionState, useEffect, useRef, useState } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../../../componentes/EstadoDeCoeficientes";
import { Estados } from "../../../../componentes/Estados";
import { FilaConIcono } from "../../../../componentes/FilaConIcono";
import { Campo, CampoDeLista, Formulario } from "../../../../componentes/Formulario";
import { Panel } from "../../../../componentes/Panel";
import { PanelLateral } from "../../../../componentes/PanelLateral";
import { permite, useSesionDePantalla } from "../../../../componentes/SesionDePantalla";
import type { InformeDeCoeficientes, Unidad } from "../../../../lib/api/tipos";
import { etiquetaDeVinculo, type VecinoDeUnidad } from "../../../../lib/api/vecinos";
import {
  coeficiente,
  decimalParaCampo,
  sumaComoPorcentaje,
  superficie,
} from "../../../../lib/formato";
import {
  IDENTIFICADOR_MAXIMO,
  identificadorDemasiadoLargo,
  pareceCoeficienteComoPorcentaje,
} from "../../../../lib/limites";
import { vocabularioDePisos } from "../../../../lib/pisos";
import { ESTADOS_REVOCABLES, textoDeEstadoDeInvitacion } from "../../../personal/estados";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_PADRON } from "./ayuda";

export type EstadoFormularioUnidad = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

export type EstadoFormularioVecino = EstadoFormularioUnidad;
export type EstadoAccionSimple = { ok?: boolean; error?: string } | null;

type AccionUnidad = (
  estadoPrevio: EstadoFormularioUnidad,
  formData: FormData,
) => Promise<EstadoFormularioUnidad>;

type AccionVecino = (
  estadoPrevio: EstadoFormularioVecino,
  formData: FormData,
) => Promise<EstadoFormularioVecino>;

type AccionSimple = (
  estadoPrevio: EstadoAccionSimple,
  formData: FormData,
) => Promise<EstadoAccionSimple>;

type Props = {
  id: string;
  nombreEdificio: string;
  /** D3 (tarea 6.2): `null` si el edificio todavía no completó la
   * ubicación — sin vocabulario propio, el piso se carga como texto. */
  pisosDelEdificio: number | null;
  subsuelosDelEdificio: number | null;
  unidades: Unidad[];
  informe: InformeDeCoeficientes;
  accionCrear: AccionUnidad;
  accionEditar: AccionUnidad;
  /** 7.4: `null` cuando quien mira no puede leer `/api/personal` (D5, sólo
   * super admin) — esta pantalla entonces no muestra la sección Vecinos. */
  vecinosPorUnidad?: Map<string, VecinoDeUnidad[]> | null;
  accionAltaVecino?: AccionVecino;
  accionRevocarVecino?: AccionSimple;
  accionQuitarVecino?: AccionSimple;
};

const _TIPOS: Array<{ valor: string; etiqueta: string; plural: string; icono: LucideIcon }> = [
  { valor: "departamento", etiqueta: "Departamento", plural: "Departamentos", icono: DoorOpen },
  { valor: "cochera", etiqueta: "Cochera", plural: "Cocheras", icono: Car },
  { valor: "baulera", etiqueta: "Baulera", plural: "Bauleras", icono: Package },
  { valor: "local", etiqueta: "Local", plural: "Locales", icono: Store },
];

function etiquetaDeTipo(valor: string): string {
  return _TIPOS.find((tipo) => tipo.valor === valor)?.etiqueta ?? valor;
}

export function PantallaPadron({
  id,
  nombreEdificio,
  pisosDelEdificio,
  subsuelosDelEdificio,
  unidades,
  informe,
  accionCrear,
  accionEditar,
  vecinosPorUnidad = null,
  accionAltaVecino = async () => null,
  accionRevocarVecino = async () => null,
  accionQuitarVecino = async () => null,
}: Props) {
  const sesion = useSesionDePantalla();
  const puedeConfigurar = permite(sesion, "configurar_padron", id);
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [unidadEnEdicion, setUnidadEnEdicion] = useState<Unidad | null>(null);
  const agregarRef = useRef<HTMLButtonElement>(null);
  const aperturaRef = useRef<HTMLElement | null>(null);

  const accionActiva = unidadEnEdicion ? accionEditar : accionCrear;
  const [estado, enviar] = useActionState(accionActiva, null);
  // D7 (tarea 5.4): validación previa al envío, con el mismo `error`
  // explícito de `Campo` — nunca `maxLength`/`pattern` nativos, que dan
  // una burbuja del navegador sin `aria-describedby`. Se limpia en cada
  // envío nuevo (éxito o 422/409 reales la reemplazan, nunca conviven).
  const [erroresPrevios, setErroresPrevios] = useState<Record<string, string>>({});

  function alEnviarUnidad(evento: FormEvent<HTMLFormElement>) {
    const datos = new FormData(evento.currentTarget);
    const identificador = String(datos.get("identificador") ?? "");
    const coeficiente = String(datos.get("coeficiente") ?? "");
    const errores: Record<string, string> = {};
    if (identificadorDemasiadoLargo(identificador)) {
      errores.identificador = `No puede tener más de ${IDENTIFICADOR_MAXIMO} caracteres.`;
    }
    if (pareceCoeficienteComoPorcentaje(coeficiente)) {
      errores.coeficiente = 'Cargalo como proporción (0 a 1), no como porcentaje. Ej.: "0.5".';
    }
    setErroresPrevios(errores);
    if (Object.keys(errores).length > 0) {
      evento.preventDefault();
    }
  }

  useEffect(() => {
    if (estado?.ok) {
      setPanelAbierto(false);
      aperturaRef.current?.focus();
    }
  }, [estado]);

  function abrirNueva() {
    aperturaRef.current = agregarRef.current;
    setUnidadEnEdicion(null);
    setPanelAbierto(true);
  }

  function abrirEdicion(unidad: Unidad, evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setUnidadEnEdicion(unidad);
    setPanelAbierto(true);
  }

  const botonAgregar = puedeConfigurar ? (
    <button ref={agregarRef} type="button" className="boton-principal" onClick={abrirNueva}>
      Agregar unidad
    </button>
  ) : undefined;

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="unidades">
      <EncabezadoDePantalla
        titulo="Padrón de unidades"
        ayuda={<Ayuda {...AYUDA_PADRON} />}
        accionPrincipal={botonAgregar}
      />

      <div className="disposicion">
        <Panel
          titulo="Unidades del edificio"
          descripcion="Tocá el identificador de una unidad para corregir sus datos."
        >
          {unidades.length === 0 ? (
            <Estados
              tipo="vacio"
              mensaje="Todavía no cargaste unidades"
              detalle="Empezá por la primera: identificador, tipo, superficie y coeficiente. Los datos los podés copiar de tu planilla."
              accion={
                puedeConfigurar ? (
                  <button type="button" onClick={abrirNueva}>
                    Agregar unidad
                  </button>
                ) : undefined
              }
            />
          ) : (
            <div className="padron-de-unidades__scroll">
              <table className="padron-de-unidades">
                <caption className="sr-only">Unidades del edificio</caption>
                <thead>
                  <tr>
                    <th>Identificador</th>
                    <th>Tipo</th>
                    <th>Piso</th>
                    <th className="numero-tabular">Superficie (m²)</th>
                    <th className="numero-tabular">Coeficiente</th>
                    {vecinosPorUnidad ? <th>Vecinos</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {unidades.map((unidad) => {
                    const vecinos = vecinosPorUnidad?.get(unidad.id) ?? [];
                    const pendientes = vecinos.filter(
                      (v) => v.invitacion && v.invitacion.estado !== "aceptada",
                    ).length;
                    return (
                      <tr key={unidad.id}>
                        <td>
                          <button
                            type="button"
                            className="boton-enlace"
                            onClick={(e) => abrirEdicion(unidad, e)}
                          >
                            {unidad.identificador}
                          </button>
                        </td>
                        <td>{etiquetaDeTipo(unidad.tipo)}</td>
                        <td>{unidad.piso ?? "Sin completar"}</td>
                        <td className="numero-tabular">{superficie(unidad.superficie_m2)}</td>
                        <td className="numero-tabular">{coeficiente(unidad.coeficiente)}</td>
                        {vecinosPorUnidad ? (
                          <td>
                            {vecinos.length}
                            {pendientes > 0
                              ? ` (${pendientes} pendiente${pendientes > 1 ? "s" : ""})`
                              : ""}
                          </td>
                        ) : null}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <div className="disposicion__lateral">
          <Panel
            titulo="Suma de coeficientes"
            variante="apoyo"
            descripcion="La calcula el sistema con todas las unidades cargadas. Tiene que dar 100%."
          >
            <p className="padron__suma numero-tabular">{sumaComoPorcentaje(informe.suma)}</p>
            <EstadoDeCoeficientes estado={informe.estado} diferencia={informe.diferencia} />
          </Panel>

          <Panel titulo="Unidades por tipo" variante="apoyo">
            <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Unidades por tipo">
              {_TIPOS.map((tipo) => (
                <li key={tipo.valor}>
                  <FilaConIcono
                    icono={tipo.icono}
                    titulo={tipo.plural}
                    fin={
                      <span className="numero-tabular">
                        {unidades.filter((unidad) => unidad.tipo === tipo.valor).length}
                      </span>
                    }
                  />
                </li>
              ))}
            </ul>
          </Panel>

          <Panel titulo="Qué falta" variante="apoyo">
            {unidades.length > 0 && informe.estado === "ok" ? (
              <FilaConIcono
                icono={CircleCheck}
                tono="listo"
                titulo="Nada por ahora"
                detalle="El padrón tiene unidades y los coeficientes suman 100%. Ya podés armar los grupos."
              />
            ) : (
              <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Qué falta">
                {unidades.length === 0 ? (
                  <li>
                    <FilaConIcono
                      icono={CircleDashed}
                      tono="atencion"
                      titulo="Agregar la primera unidad"
                      detalle="Sin unidades no hay a quién repartirle la expensa."
                    />
                  </li>
                ) : null}
                {informe.estado !== "ok" ? (
                  <li>
                    <FilaConIcono
                      icono={CircleDashed}
                      tono="atencion"
                      titulo="Corregir los coeficientes"
                      detalle="Revisá la unidad que tenga el coeficiente mal hasta que la suma dé 100%."
                    />
                  </li>
                ) : null}
              </ul>
            )}
          </Panel>
        </div>
      </div>

      <PanelLateral
        abierto={panelAbierto}
        titulo={unidadEnEdicion ? "Editar unidad" : "Agregar unidad"}
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={aperturaRef}
      >
        {/* R3C-4 (rompedor 3b): sin `key`, tocar otra fila con el panel
         * abierto sólo cambiaba el `defaultValue` de los `Campo` (no
         * controlados) — React no remonta el input ya montado, así que un
         * campo ya tocado conservaba lo tipeado para la unidad anterior y
         * el oculto `unidad_id` lo mandaba sobre la unidad nueva. La `key`
         * por unidad (o "nueva") fuerza el remonte del formulario entero. */}
        <Formulario
          key={unidadEnEdicion?.id ?? "nueva"}
          erroresPorCampo={{ ...erroresPrevios, ...estado?.erroresPorCampo }}
          erroresDesconocidos={estado?.erroresDesconocidos ?? []}
          action={enviar}
          onSubmit={alEnviarUnidad}
        >
          {unidadEnEdicion ? (
            <input type="hidden" name="unidad_id" value={unidadEnEdicion.id} />
          ) : null}
          <Campo
            nombre="identificador"
            etiqueta="Identificador"
            name="identificador"
            defaultValue={unidadEnEdicion?.identificador}
            maxLength={IDENTIFICADOR_MAXIMO}
            required
          />
          <p className="campo__ayuda">
            Hasta {IDENTIFICADOR_MAXIMO} caracteres, letras y números como quieras (por ejemplo
            "1A", "PB 2" o "Local 3"): no hay un formato fijo.
          </p>
          <label className="campo">
            Tipo
            <select name="tipo" defaultValue={unidadEnEdicion?.tipo ?? "departamento"}>
              {_TIPOS.map((tipo) => (
                <option key={tipo.valor} value={tipo.valor}>
                  {tipo.etiqueta}
                </option>
              ))}
            </select>
          </label>
          {pisosDelEdificio !== null && subsuelosDelEdificio !== null ? (
            // D3 (tarea 6.2, F2): opción vacía EXPLÍCITA primero — sin
            // ella, abrir el panel de una unidad migrada con `piso: null`
            // selecciona (y guardaría) la primera opción real de la lista
            // sin que nadie la haya elegido.
            <CampoDeLista
              nombre="piso"
              etiqueta="Piso"
              name="piso"
              defaultValue={unidadEnEdicion?.piso ?? ""}
            >
              <option value="">Sin completar</option>
              {vocabularioDePisos(pisosDelEdificio, subsuelosDelEdificio).map((piso) => (
                <option key={piso} value={piso}>
                  {piso}
                </option>
              ))}
            </CampoDeLista>
          ) : (
            <Campo
              nombre="piso"
              etiqueta="Piso"
              name="piso"
              defaultValue={unidadEnEdicion?.piso ?? ""}
            />
          )}
          <Campo
            nombre="superficie_m2"
            etiqueta="Superficie (m²)"
            name="superficie_m2"
            inputMode="decimal"
            defaultValue={decimalParaCampo(unidadEnEdicion?.superficie_m2)}
            required
          />
          <Campo
            nombre="coeficiente"
            etiqueta="Coeficiente"
            name="coeficiente"
            inputMode="decimal"
            defaultValue={decimalParaCampo(unidadEnEdicion?.coeficiente)}
            required
          />
          <button type="submit" className="boton-principal">
            Guardar
          </button>
        </Formulario>

        {/* 7.4: sólo con una unidad existente (no al crear) y sólo si esta
         * sesión puede leer vecinos (super admin, D5). Formulario propio,
         * HERMANO del de arriba: dos `<form>` anidados no son válidos. */}
        {unidadEnEdicion && vecinosPorUnidad ? (
          <SeccionVecinos
            unidadId={unidadEnEdicion.id}
            vecinos={vecinosPorUnidad.get(unidadEnEdicion.id) ?? []}
            accionAlta={accionAltaVecino}
            accionRevocar={accionRevocarVecino}
            accionQuitar={accionQuitarVecino}
          />
        ) : null}
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}

function SeccionVecinos({
  unidadId,
  vecinos,
  accionAlta,
  accionRevocar,
  accionQuitar,
}: {
  unidadId: string;
  vecinos: VecinoDeUnidad[];
  accionAlta: AccionVecino;
  accionRevocar: AccionSimple;
  accionQuitar: AccionSimple;
}) {
  const [estado, enviar] = useActionState(accionAlta, null);
  return (
    <div className="panel-lateral__seccion">
      <h3>Vecinos</h3>
      {vecinos.length === 0 ? (
        <p className="texto-secundario">Todavía no hay vecinos cargados.</p>
      ) : (
        <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Vecinos">
          {vecinos.map((vecino) => (
            <li key={vecino.asignacion_id} className="fila-de-asignacion">
              <span>
                <strong>{vecino.nombre}</strong>
                <span className="texto-secundario">
                  {" "}
                  · {etiquetaDeVinculo(vecino.vinculo)}
                  {vecino.invitacion
                    ? ` · ${textoDeEstadoDeInvitacion(vecino.invitacion.estado)}`
                    : ""}
                </span>
              </span>
              <BotonesDeVecino
                vecino={vecino}
                accionRevocar={accionRevocar}
                accionQuitar={accionQuitar}
              />
            </li>
          ))}
        </ul>
      )}
      <Formulario
        erroresPorCampo={estado?.erroresPorCampo ?? {}}
        erroresDesconocidos={estado?.erroresDesconocidos ?? []}
        action={enviar}
        aria-label="Agregar vecino"
      >
        <input type="hidden" name="unidad_id" value={unidadId} />
        <Campo nombre="nombre" etiqueta="Nombre del vecino" name="nombre" required />
        <Campo nombre="email" etiqueta="Email del vecino" name="email" type="email" required />
        <label className="campo">
          Vínculo
          <select name="vinculo" defaultValue="propietario">
            <option value="propietario">Propietario</option>
            <option value="inquilino">Inquilino</option>
          </select>
        </label>
        <button type="submit" className="boton-principal">
          Agregar vecino
        </button>
      </Formulario>
    </div>
  );
}

function BotonesDeVecino({
  vecino,
  accionRevocar,
  accionQuitar,
}: {
  vecino: VecinoDeUnidad;
  accionRevocar: AccionSimple;
  accionQuitar: AccionSimple;
}) {
  const [estadoRevocar, enviarRevocar] = useActionState(accionRevocar, null);
  const [estadoQuitar, enviarQuitar] = useActionState(accionQuitar, null);
  if (estadoQuitar?.ok) {
    return <span className="texto-secundario">Quitado</span>;
  }
  const puedeRevocar =
    vecino.invitacion && ESTADOS_REVOCABLES.has(vecino.invitacion.estado) && !estadoRevocar?.ok;
  return (
    <span className="fila-de-asignacion__accion">
      {puedeRevocar ? (
        <form action={enviarRevocar}>
          <input type="hidden" name="invitacion_id" value={vecino.invitacion?.invitacion_id} />
          <button type="submit" className="boton-enlace">
            Revocar
          </button>
        </form>
      ) : estadoRevocar?.ok ? (
        <span className="texto-secundario">Revocada</span>
      ) : null}
      <form action={enviarQuitar}>
        <input type="hidden" name="asignacion_id" value={vecino.asignacion_id} />
        <button type="submit" className="boton-enlace">
          Quitar
        </button>
      </form>
      {estadoQuitar?.error ? (
        <p role="alert" className="campo__error">
          {estadoQuitar.error}
        </p>
      ) : null}
    </span>
  );
}
