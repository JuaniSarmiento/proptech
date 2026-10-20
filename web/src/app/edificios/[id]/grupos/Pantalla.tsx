"use client";

/**
 * Grupos de reparto (tarea 4.4, D9): "Generales" primero, automático y sin
 * edición, con la línea de por qué. Crear o editar abre el panel lateral
 * con nombre, método, modo y la selección de unidades (coeficiente por
 * unidad en "propios", sin suma en vivo: D9 muestra el informe de la API
 * después de guardar, nunca lo calcula mientras se tipea). Cambiar el modo
 * en edición avisa que se reescriben los coeficientes.
 *
 * Enmienda del 20/10/2026: la lista vive en el panel principal, cada grupo
 * como fila con ícono, y al costado un panel que explica los métodos y los
 * modos con palabras simples, más lo que hay armado en este edificio (sólo
 * conteos).
 */

import { Layers, Lock, Ruler, Scale, Users } from "lucide-react";
import { useActionState, useEffect, useRef, useState } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../../../componentes/EstadoDeCoeficientes";
import { Estados } from "../../../../componentes/Estados";
import { FilaConIcono } from "../../../../componentes/FilaConIcono";
import { Campo, Formulario } from "../../../../componentes/Formulario";
import { Panel } from "../../../../componentes/Panel";
import { PanelLateral } from "../../../../componentes/PanelLateral";
import type { Grupo, Unidad } from "../../../../lib/api/tipos";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_GRUPOS } from "./ayuda";

export type EstadoFormularioGrupo = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

type AccionGrupo = (
  estadoPrevio: EstadoFormularioGrupo,
  formData: FormData,
) => Promise<EstadoFormularioGrupo>;

type ModoDeCoeficientes = "renormalizado" | "propios";

type Props = {
  id: string;
  nombreEdificio: string;
  grupos: Grupo[];
  unidadesDisponibles: Unidad[];
  accionCrear: AccionGrupo;
  accionEditar: AccionGrupo;
};

const _METODOS: Array<{ valor: string; etiqueta: string }> = [
  { valor: "coeficiente", etiqueta: "Coeficiente" },
  { valor: "superficie", etiqueta: "Superficie" },
  { valor: "partes_iguales", etiqueta: "Partes iguales" },
];

function textoDeMetodo(metodo: string): string {
  const etiqueta = _METODOS.find((m) => m.valor === metodo)?.etiqueta;
  return etiqueta ? `por ${etiqueta.toLowerCase()}` : metodo;
}

function textoDeModo(modo: string): string {
  return modo === "propios" ? "coeficientes propios" : "coeficientes renormalizados";
}

export function PantallaGrupos({
  id,
  nombreEdificio,
  grupos,
  unidadesDisponibles,
  accionCrear,
  accionEditar,
}: Props) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [grupoEnEdicion, setGrupoEnEdicion] = useState<Grupo | null>(null);
  const [modoFormulario, setModoFormulario] = useState<ModoDeCoeficientes>("renormalizado");
  const agregarRef = useRef<HTMLButtonElement>(null);
  const aperturaRef = useRef<HTMLElement | null>(null);

  const accionActiva = grupoEnEdicion ? accionEditar : accionCrear;
  const [estado, enviar] = useActionState(accionActiva, null);

  useEffect(() => {
    if (estado?.ok) {
      setPanelAbierto(false);
      aperturaRef.current?.focus();
    }
  }, [estado]);

  function abrirNuevo() {
    aperturaRef.current = agregarRef.current;
    setGrupoEnEdicion(null);
    setModoFormulario("renormalizado");
    setPanelAbierto(true);
  }

  function abrirEdicion(grupo: Grupo, evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setGrupoEnEdicion(grupo);
    setModoFormulario(grupo.modo_de_coeficientes === "propios" ? "propios" : "renormalizado");
    setPanelAbierto(true);
  }

  const idsSeleccionados = new Set(grupoEnEdicion?.unidades.map((m) => m.unidad_id) ?? []);
  const coeficientesPrevios = new Map(
    grupoEnEdicion?.unidades.map((m) => [m.unidad_id, m.coeficiente ?? ""]) ?? [],
  );

  const botonAgregar = (
    <button ref={agregarRef} type="button" className="boton-principal" onClick={abrirNuevo}>
      Agregar grupo
    </button>
  );

  const generales = grupos.filter((g) => g.es_generales);
  const resto = grupos.filter((g) => !g.es_generales);

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="grupos">
      <EncabezadoDePantalla
        titulo="Grupos de reparto"
        ayuda={<Ayuda {...AYUDA_GRUPOS} />}
        accionPrincipal={botonAgregar}
      />

      <div className="disposicion">
        <Panel
          titulo="Grupos del edificio"
          descripcion="Cada grupo dice qué unidades pagan un gasto y cómo se lo reparten. Tocá un grupo para cambiarlo."
        >
          {grupos.length === 0 ? (
            <Estados
              tipo="vacio"
              mensaje="Todavía no armaste ningún grupo"
              detalle="Armá uno para cada gasto que no pagan todas las unidades, por ejemplo el ascensor."
              accion={
                <button type="button" onClick={abrirNuevo}>
                  Agregar grupo
                </button>
              }
            />
          ) : (
            <ul
              className="lista-de-filas lista-de-filas--tocable grupos-de-reparto"
              aria-label="Grupos de reparto"
            >
              {[...generales, ...resto].map((grupo) => (
                <li
                  key={grupo.id}
                  className="grupos-de-reparto__fila"
                  data-editable={!grupo.es_generales}
                >
                  <FilaConIcono
                    icono={grupo.es_generales ? Lock : Layers}
                    tono={grupo.es_generales ? "listo" : "neutro"}
                    titulo={
                      grupo.es_generales ? (
                        <span className="grupos-de-reparto__datos">
                          <span className="grupos-de-reparto__nombre">{grupo.nombre}</span>
                          <span className="grupos-de-reparto__meta">
                            Automático ·{" "}
                            <span className="numero-tabular">{grupo.unidades.length}</span> unidades
                          </span>
                        </span>
                      ) : (
                        <button
                          type="button"
                          className="boton-enlace grupos-de-reparto__datos"
                          onClick={(e) => abrirEdicion(grupo, e)}
                        >
                          <span className="grupos-de-reparto__nombre">{grupo.nombre}</span>
                          <span className="grupos-de-reparto__meta">
                            {textoDeMetodo(grupo.metodo)} ·{" "}
                            {textoDeModo(grupo.modo_de_coeficientes)} · {grupo.unidades.length}{" "}
                            unidades
                          </span>
                        </button>
                      )
                    }
                    detalle={
                      grupo.es_generales ? (
                        <p className="grupos-de-reparto__nota">
                          Agrupa todo lo que no entra en un grupo propio: se calcula solo y no se
                          edita.
                        </p>
                      ) : undefined
                    }
                    fin={
                      grupo.modo_de_coeficientes === "propios" && grupo.informe ? (
                        <EstadoDeCoeficientes
                          estado={grupo.informe.estado}
                          diferencia={grupo.informe.diferencia}
                        />
                      ) : undefined
                    }
                  />
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <div className="disposicion__lateral">
          <Panel
            titulo="Cómo se reparte"
            variante="apoyo"
            descripcion="Lo que elegís al armar un grupo, en palabras simples."
          >
            <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Métodos de reparto">
              <li>
                <FilaConIcono
                  icono={Scale}
                  titulo="Por coeficiente"
                  detalle="Cada unidad paga según su coeficiente del padrón."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={Ruler}
                  titulo="Por superficie"
                  detalle="Cada unidad paga según sus metros cuadrados."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={Users}
                  titulo="Partes iguales"
                  detalle="Todas las unidades del grupo pagan lo mismo."
                />
              </li>
            </ul>
            <dl className="renglones renglones--explicacion">
              <div className="renglones__fila renglones__fila--apilada">
                <dt>Coeficientes renormalizados</dt>
                <dd>Se usan los del padrón, ajustados para que el grupo sume 100%.</dd>
              </div>
              <div className="renglones__fila renglones__fila--apilada">
                <dt>Coeficientes propios</dt>
                <dd>Cargás uno distinto para cada unidad del grupo.</dd>
              </div>
            </dl>
          </Panel>

          <Panel titulo="En este edificio" variante="apoyo">
            <dl className="renglones">
              <div className="renglones__fila">
                <dt>Grupos armados</dt>
                <dd className="numero-tabular">{grupos.length}</dd>
              </div>
              <div className="renglones__fila">
                <dt>Con coeficientes propios</dt>
                <dd className="numero-tabular">
                  {grupos.filter((g) => g.modo_de_coeficientes === "propios").length}
                </dd>
              </div>
              <div className="renglones__fila">
                <dt>Unidades en el padrón</dt>
                <dd className="numero-tabular">{unidadesDisponibles.length}</dd>
              </div>
            </dl>
          </Panel>
        </div>
      </div>

      <PanelLateral
        abierto={panelAbierto}
        titulo={grupoEnEdicion ? "Editar grupo" : "Agregar grupo"}
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={aperturaRef}
      >
        {/* R3C-4: misma `key` por entidad que en unidades/Pantalla.tsx —
         * fuerza el remonte del formulario al cambiar de fila con el panel
         * abierto (ver comentario allá). */}
        <Formulario
          key={grupoEnEdicion?.id ?? "nuevo"}
          erroresPorCampo={estado?.erroresPorCampo ?? {}}
          erroresDesconocidos={estado?.erroresDesconocidos ?? []}
          action={enviar}
        >
          {grupoEnEdicion ? (
            <input type="hidden" name="grupo_id" value={grupoEnEdicion.id} />
          ) : (
            <Campo nombre="clave" etiqueta="Clave" name="clave" required />
          )}
          <Campo
            nombre="nombre"
            etiqueta="Nombre"
            name="nombre"
            defaultValue={grupoEnEdicion?.nombre}
            required
          />
          <label className="campo">
            Método
            <select name="metodo" defaultValue={grupoEnEdicion?.metodo ?? "coeficiente"}>
              {_METODOS.map((metodo) => (
                <option key={metodo.valor} value={metodo.valor}>
                  {metodo.etiqueta}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            Modo
            <select
              name="modo_de_coeficientes"
              value={modoFormulario}
              onChange={(e) => setModoFormulario(e.target.value as ModoDeCoeficientes)}
            >
              <option value="renormalizado">Renormalizado</option>
              <option value="propios">Propios</option>
            </select>
          </label>
          {grupoEnEdicion && modoFormulario !== grupoEnEdicion.modo_de_coeficientes ? (
            <p role="status">
              Al guardar, se van a reescribir los coeficientes de las unidades de este grupo.
            </p>
          ) : null}
          <fieldset>
            <legend>Unidades</legend>
            {unidadesDisponibles.map((unidad) => (
              <div key={unidad.id} className="grupos-de-reparto__unidad">
                <label>
                  <input
                    type="checkbox"
                    name={`unidad_${unidad.id}`}
                    defaultChecked={idsSeleccionados.has(unidad.id)}
                  />
                  {unidad.identificador}
                </label>
                {modoFormulario === "propios" ? (
                  <input
                    type="text"
                    name={`coeficiente_${unidad.id}`}
                    aria-label={`Coeficiente de ${unidad.identificador}`}
                    defaultValue={coeficientesPrevios.get(unidad.id) ?? ""}
                  />
                ) : null}
              </div>
            ))}
          </fieldset>
          <button type="submit" className="boton-principal">
            Guardar
          </button>
        </Formulario>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}
