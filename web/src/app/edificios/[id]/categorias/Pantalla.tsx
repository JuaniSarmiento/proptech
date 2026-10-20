"use client";

/**
 * Categorías de gasto (tarea 4.5, D8): agregar, renombrar, desactivar y
 * reactivar; reordenar con "subir"/"bajar" operables con teclado, que
 * mandan el ORDEN COMPLETO a la API (D-ficha 4.5, nunca sólo la categoría
 * que se mueve). El foco queda en el botón "subir"/"bajar" que se tocó: es
 * el MISMO nodo del DOM antes y después de que el servidor revalide con el
 * nuevo orden (React lo conserva por `key={categoria.id}`), así que no hace
 * falta buscarlo de nuevo tras la revalidación.
 *
 * Enmienda del 20/10/2026: la lista en el panel principal, cada categoría
 * como fila con ícono, estado en la línea gris y sus acciones a la
 * derecha ("Subir"/"Bajar" con texto al lado del ícono); al costado,
 * cuántas hay activas y cómo se usan.
 */

import { ChevronDown, ChevronUp, Tag } from "lucide-react";
import { useActionState, useEffect, useRef, useState } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Estados } from "../../../../componentes/Estados";
import { FilaConIcono } from "../../../../componentes/FilaConIcono";
import { Campo, Formulario } from "../../../../componentes/Formulario";
import { Panel } from "../../../../componentes/Panel";
import { PanelLateral } from "../../../../componentes/PanelLateral";
import type { Categoria } from "../../../../lib/api/tipos";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_CATEGORIAS } from "./ayuda";

export type EstadoFormularioCategoria = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

export type EstadoAccionDeLista = {
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

type AccionCategoria = (
  estadoPrevio: EstadoFormularioCategoria,
  formData: FormData,
) => Promise<EstadoFormularioCategoria>;

type AccionDeLista = (
  estadoPrevio: EstadoAccionDeLista,
  formData: FormData,
) => Promise<EstadoAccionDeLista>;

type Props = {
  id: string;
  nombreEdificio: string;
  categorias: Categoria[];
  accionCrear: AccionCategoria;
  accionEditar: AccionCategoria;
  accionEstado: AccionDeLista;
  accionReordenar: AccionDeLista;
};

/** Todos los ids en el orden actual, con `id` movido una posición en
 * `direccion` (-1 sube, +1 baja). Sin movimiento posible (primera al subir,
 * última al bajar) devuelve el mismo orden. */
function ordenConMovimiento(categorias: Categoria[], id: string, direccion: -1 | 1): string[] {
  const ids = categorias.map((c) => c.id);
  const indice = ids.indexOf(id);
  const destino = indice + direccion;
  if (destino < 0 || destino >= ids.length) {
    return ids;
  }
  const nuevo = [...ids];
  [nuevo[indice], nuevo[destino]] = [nuevo[destino] as string, nuevo[indice] as string];
  return nuevo;
}

export function PantallaCategorias({
  id,
  nombreEdificio,
  categorias,
  accionCrear,
  accionEditar,
  accionEstado,
  accionReordenar,
}: Props) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [categoriaEnEdicion, setCategoriaEnEdicion] = useState<Categoria | null>(null);
  const agregarRef = useRef<HTMLButtonElement>(null);
  const aperturaRef = useRef<HTMLElement | null>(null);
  const botonMovidoRef = useRef<HTMLButtonElement | null>(null);

  const accionActiva = categoriaEnEdicion ? accionEditar : accionCrear;
  const [estadoPanel, enviarPanel] = useActionState(accionActiva, null);
  const [estadoReordenar, enviarReordenar] = useActionState(accionReordenar, null);
  const [estadoEstado, enviarEstado] = useActionState(accionEstado, null);

  useEffect(() => {
    if (estadoPanel?.ok) {
      setPanelAbierto(false);
      aperturaRef.current?.focus();
    }
  }, [estadoPanel]);

  useEffect(() => {
    if (estadoReordenar?.ok) {
      botonMovidoRef.current?.focus();
    }
  }, [estadoReordenar]);

  function abrirNueva() {
    aperturaRef.current = agregarRef.current;
    setCategoriaEnEdicion(null);
    setPanelAbierto(true);
  }

  function abrirEdicion(categoria: Categoria, evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setCategoriaEnEdicion(categoria);
    setPanelAbierto(true);
  }

  const botonAgregar = (
    <button ref={agregarRef} type="button" className="boton-principal" onClick={abrirNueva}>
      Agregar categoría
    </button>
  );

  const erroresDeLista = [
    ...(estadoReordenar?.erroresDesconocidos ?? []),
    ...(estadoEstado?.erroresDesconocidos ?? []),
  ];

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="categorias">
      <EncabezadoDePantalla
        titulo="Categorías de gasto"
        ayuda={<Ayuda {...AYUDA_CATEGORIAS} />}
        accionPrincipal={botonAgregar}
      />

      {erroresDeLista.length > 0 ? (
        <div role="alert" className="formulario__resumen">
          <ul>
            {erroresDeLista.map((mensaje) => (
              <li key={mensaje}>{mensaje}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="disposicion">
        <Panel
          titulo="Categorías del edificio"
          descripcion="Los rubros en los que anotás cada gasto. Tocá un nombre para cambiarlo."
        >
          {categorias.length === 0 ? (
            <Estados
              tipo="vacio"
              mensaje="Todavía no tenés categorías"
              detalle="Sumá una por cada tipo de gasto que pagás todos los meses, como limpieza o seguridad."
              accion={
                <button type="button" onClick={abrirNueva}>
                  Agregar categoría
                </button>
              }
            />
          ) : (
            <ul className="lista-de-filas categorias-de-gasto" aria-label="Categorías de gasto">
              {categorias.map((categoria, indice) => {
                const ordenSiSube = ordenConMovimiento(categorias, categoria.id, -1);
                const ordenSiBaja = ordenConMovimiento(categorias, categoria.id, 1);
                return (
                  <li
                    key={categoria.id}
                    className="categorias-de-gasto__fila"
                    data-activa={categoria.activa}
                  >
                    <FilaConIcono
                      icono={Tag}
                      tono={categoria.activa ? "neutro" : "listo"}
                      titulo={
                        <button
                          type="button"
                          className="boton-enlace categorias-de-gasto__nombre"
                          onClick={(e) => abrirEdicion(categoria, e)}
                        >
                          {categoria.nombre}
                        </button>
                      }
                      detalle={
                        <span className="categorias-de-gasto__estado">
                          {categoria.activa ? "Activa" : "Desactivada"}
                        </span>
                      }
                      fin={
                        <>
                          <form action={enviarEstado} className="categorias-de-gasto__accion">
                            <input type="hidden" name="categoria_id" value={categoria.id} />
                            <input
                              type="hidden"
                              name="activa"
                              value={categoria.activa ? "false" : "true"}
                            />
                            <button type="submit" className="boton-secundario">
                              {categoria.activa ? "Desactivar" : "Reactivar"}{" "}
                              <span className="sr-only">{categoria.nombre}</span>
                            </button>
                          </form>

                          <div className="categorias-de-gasto__orden">
                            {indice > 0 ? (
                              <form action={enviarReordenar} className="categorias-de-gasto__subir">
                                {ordenSiSube.map((idOrdenado) => (
                                  <input
                                    key={idOrdenado}
                                    type="hidden"
                                    name="orden"
                                    value={idOrdenado}
                                  />
                                ))}
                                <button
                                  type="submit"
                                  className="boton-icono"
                                  aria-label={`Subir ${categoria.nombre}`}
                                  onClick={(e) => {
                                    botonMovidoRef.current = e.currentTarget;
                                  }}
                                >
                                  <ChevronUp size={16} strokeWidth={2} aria-hidden="true" />
                                  Subir
                                </button>
                              </form>
                            ) : null}
                            {indice < categorias.length - 1 ? (
                              <form action={enviarReordenar} className="categorias-de-gasto__bajar">
                                {ordenSiBaja.map((idOrdenado) => (
                                  <input
                                    key={idOrdenado}
                                    type="hidden"
                                    name="orden"
                                    value={idOrdenado}
                                  />
                                ))}
                                <button
                                  type="submit"
                                  className="boton-icono"
                                  aria-label={`Bajar ${categoria.nombre}`}
                                  onClick={(e) => {
                                    botonMovidoRef.current = e.currentTarget;
                                  }}
                                >
                                  <ChevronDown size={16} strokeWidth={2} aria-hidden="true" />
                                  Bajar
                                </button>
                              </form>
                            ) : null}
                          </div>
                        </>
                      }
                    />
                  </li>
                );
              })}
            </ul>
          )}
        </Panel>

        <div className="disposicion__lateral">
          <Panel titulo="En este edificio" variante="apoyo">
            <dl className="renglones">
              <div className="renglones__fila">
                <dt>Activas</dt>
                <dd className="numero-tabular">{categorias.filter((c) => c.activa).length}</dd>
              </div>
              <div className="renglones__fila">
                <dt>Desactivadas</dt>
                <dd className="numero-tabular">{categorias.filter((c) => !c.activa).length}</dd>
              </div>
            </dl>
          </Panel>

          <Panel titulo="Cómo se usan" variante="apoyo">
            <ul className="lista-de-filas lista-de-filas--compacta" aria-label="Cómo se usan">
              <li>
                <FilaConIcono
                  icono={Tag}
                  titulo="Renombrar"
                  detalle="Cambiás el nombre sin perder su historial."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={Tag}
                  titulo="Desactivar"
                  detalle="La dejás de usar sin borrarla. La podés reactivar cuando quieras."
                />
              </li>
              <li>
                <FilaConIcono
                  icono={ChevronUp}
                  titulo="Subir y bajar"
                  detalle="Ordenan la lista como vos quieras."
                />
              </li>
            </ul>
          </Panel>
        </div>
      </div>

      <PanelLateral
        abierto={panelAbierto}
        titulo={categoriaEnEdicion ? "Renombrar categoría" : "Agregar categoría"}
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={aperturaRef}
      >
        {/* R3C-4: misma `key` por entidad que en unidades/Pantalla.tsx —
         * fuerza el remonte del formulario al cambiar de fila con el panel
         * abierto (ver comentario allá). */}
        <Formulario
          key={categoriaEnEdicion?.id ?? "nueva"}
          erroresPorCampo={estadoPanel?.erroresPorCampo ?? {}}
          erroresDesconocidos={estadoPanel?.erroresDesconocidos ?? []}
          action={enviarPanel}
        >
          {categoriaEnEdicion ? (
            <input type="hidden" name="categoria_id" value={categoriaEnEdicion.id} />
          ) : (
            <Campo nombre="clave" etiqueta="Clave" name="clave" required />
          )}
          <Campo
            nombre="nombre"
            etiqueta="Nombre"
            name="nombre"
            defaultValue={categoriaEnEdicion?.nombre}
            required
          />
          <button type="submit" className="boton-principal">
            Guardar
          </button>
        </Formulario>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}
