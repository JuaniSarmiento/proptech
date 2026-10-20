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
import { useActionState, useEffect, useRef, useState } from "react";
import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../../../componentes/EstadoDeCoeficientes";
import { Estados } from "../../../../componentes/Estados";
import { FilaConIcono } from "../../../../componentes/FilaConIcono";
import { Campo, Formulario } from "../../../../componentes/Formulario";
import { Panel } from "../../../../componentes/Panel";
import { PanelLateral } from "../../../../componentes/PanelLateral";
import type { InformeDeCoeficientes, Unidad } from "../../../../lib/api/tipos";
import { coeficiente, sumaComoPorcentaje, superficie } from "../../../../lib/formato";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_PADRON } from "./ayuda";

export type EstadoFormularioUnidad = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

type AccionUnidad = (
  estadoPrevio: EstadoFormularioUnidad,
  formData: FormData,
) => Promise<EstadoFormularioUnidad>;

type Props = {
  id: string;
  nombreEdificio: string;
  unidades: Unidad[];
  informe: InformeDeCoeficientes;
  accionCrear: AccionUnidad;
  accionEditar: AccionUnidad;
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
  unidades,
  informe,
  accionCrear,
  accionEditar,
}: Props) {
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [unidadEnEdicion, setUnidadEnEdicion] = useState<Unidad | null>(null);
  const aperturaRef = useRef<HTMLElement | null>(null);

  const accionActiva = unidadEnEdicion ? accionEditar : accionCrear;
  const [estado, enviar] = useActionState(accionActiva, null);

  useEffect(() => {
    if (estado?.ok) {
      setPanelAbierto(false);
      aperturaRef.current?.focus();
    }
  }, [estado]);

  function abrirNueva(evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setUnidadEnEdicion(null);
    setPanelAbierto(true);
  }

  function abrirEdicion(unidad: Unidad, evento: { currentTarget: HTMLElement }) {
    aperturaRef.current = evento.currentTarget;
    setUnidadEnEdicion(unidad);
    setPanelAbierto(true);
  }

  const botonAgregar = (
    <button type="button" className="boton-principal" onClick={abrirNueva}>
      Agregar unidad
    </button>
  );

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
              accion={botonAgregar}
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
                  </tr>
                </thead>
                <tbody>
                  {unidades.map((unidad) => (
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
                      <td>{unidad.piso}</td>
                      <td className="numero-tabular">{superficie(unidad.superficie_m2)}</td>
                      <td className="numero-tabular">{coeficiente(unidad.coeficiente)}</td>
                    </tr>
                  ))}
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
          erroresPorCampo={estado?.erroresPorCampo ?? {}}
          erroresDesconocidos={estado?.erroresDesconocidos ?? []}
          action={enviar}
        >
          {unidadEnEdicion ? (
            <input type="hidden" name="unidad_id" value={unidadEnEdicion.id} />
          ) : null}
          <Campo
            nombre="identificador"
            etiqueta="Identificador"
            name="identificador"
            defaultValue={unidadEnEdicion?.identificador}
            required
          />
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
          <Campo nombre="piso" etiqueta="Piso" name="piso" defaultValue={unidadEnEdicion?.piso} />
          <Campo
            nombre="superficie_m2"
            etiqueta="Superficie (m²)"
            name="superficie_m2"
            defaultValue={unidadEnEdicion?.superficie_m2}
            required
          />
          <Campo
            nombre="coeficiente"
            etiqueta="Coeficiente"
            name="coeficiente"
            defaultValue={unidadEnEdicion?.coeficiente}
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
