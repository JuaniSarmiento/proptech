"use client";

/**
 * Resumen del edificio (tarea 4.2, D5, D11; enmienda del 20/10/2026; D3,
 * tarea 6.1: paso "ubicación" nuevo y edición desde acá): a la izquierda
 * el checklist de puesta a punto con su barra de progreso ("N de 7
 * pasos"), cada paso como fila con ícono, explicación y estado; a la
 * derecha "Tu próximo paso" (la única acción principal de la pantalla) y
 * los datos del edificio, con "Editar" para corregir ubicación, calle,
 * pisos y subsuelos sin salir de la pantalla. Ningún paso se decide acá
 * (D5): se muestra tal cual lo da la API, incluso si no cuadra con
 * `cantidad_unidades` ("la web no calcula"). La barra sólo CUENTA los
 * pasos que la API ya marcó.
 */

import {
  ArrowRight,
  Building2,
  CalendarClock,
  FileCheck2,
  Layers,
  type LucideIcon,
  MapPin,
  Percent,
  Tags,
} from "lucide-react";
import { useActionState, useEffect, useRef, useState } from "react";
import { Ayuda } from "../../../componentes/Ayuda";
import { BarraDeProgreso } from "../../../componentes/BarraDeProgreso";
import { EncabezadoDePantalla } from "../../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../../componentes/EstadoDeCoeficientes";
import { FilaConIcono } from "../../../componentes/FilaConIcono";
import { Campo, Formulario } from "../../../componentes/Formulario";
import { Panel } from "../../../componentes/Panel";
import { PanelLateral } from "../../../componentes/PanelLateral";
import { SelectorDeUbicacion } from "../../../componentes/SelectorDeUbicacion";
import type { ConfiguracionVigente, Resumen } from "../../../lib/api/tipos";
import { textoEstadoDeMigracion } from "../../../lib/textoDeEstados";
import { ArmazonDelEdificio } from "./Armazon";
import { AYUDA_RESUMEN } from "./ayuda";
import { textoDeVigente } from "./textoDeVigente";

type ClavePaso = keyof Resumen["pasos"];

type Paso = {
  clave: ClavePaso;
  numero: number;
  etiqueta: string;
  explicacion: string;
  href: string;
  icono: LucideIcon;
};

const _PASOS: Paso[] = [
  {
    clave: "ubicacion",
    numero: 1,
    etiqueta: "Completar la ubicación",
    explicacion: "Provincia, departamento y localidad, más pisos y subsuelos del edificio.",
    href: "",
    icono: MapPin,
  },
  {
    clave: "unidades",
    numero: 2,
    etiqueta: "Cargar unidades",
    explicacion: "Cada departamento, cochera o local, con su superficie y su coeficiente.",
    href: "/unidades",
    icono: Building2,
  },
  {
    clave: "coeficientes",
    numero: 3,
    etiqueta: "Revisar coeficientes (que sumen 100%)",
    explicacion: "Si la suma no da 100%, la expensa no se reparte bien entre los vecinos.",
    href: "/unidades",
    icono: Percent,
  },
  {
    clave: "grupos",
    numero: 4,
    etiqueta: "Armar los grupos de reparto",
    explicacion: "Para los gastos que pagan sólo algunas unidades, como el ascensor.",
    href: "/grupos",
    icono: Layers,
  },
  {
    clave: "categorias",
    numero: 5,
    etiqueta: "Definir las categorías de gasto",
    explicacion: "Los rubros en los que vas a anotar cada gasto del mes.",
    href: "/categorias",
    icono: Tags,
  },
  {
    clave: "intereses_y_vencimiento",
    numero: 6,
    etiqueta: "Configurar intereses y vencimiento",
    explicacion: "La tasa por pagar tarde, el fondo de reserva y el día en que vence.",
    href: "/configuracion",
    icono: CalendarClock,
  },
  {
    clave: "saldos_previos",
    numero: 7,
    etiqueta: "Confirmar que el edificio arranca sin saldos previos",
    explicacion: "Un único paso, que no se deshace: el edificio empieza sin deudas de antes.",
    href: "/saldos-previos",
    icono: FileCheck2,
  },
];

export type EstadoEdicionEdificio = {
  erroresPorCampo: Record<string, string>;
  erroresDesconocidos: string[];
  ok?: boolean;
} | null;

type AccionEditar = (
  estadoPrevio: EstadoEdicionEdificio,
  formData: FormData,
) => Promise<EstadoEdicionEdificio>;

type Props = {
  id: string;
  resumen: Resumen;
  vigente: ConfiguracionVigente;
  accionEditar: AccionEditar;
};

export function PantallaResumen({ id, resumen, vigente, accionEditar }: Props) {
  const estaHecho = (paso: Paso) => resumen.pasos[paso.clave] === "hecho";
  const hechos = _PASOS.filter(estaHecho).length;
  const proximo = _PASOS.find((paso) => !estaHecho(paso));

  const [panelAbierto, setPanelAbierto] = useState(false);
  const editarRef = useRef<HTMLButtonElement>(null);
  const [estado, enviar] = useActionState(accionEditar, null);

  useEffect(() => {
    if (estado?.ok) {
      setPanelAbierto(false);
    }
  }, [estado]);

  function abrirEdicion() {
    setPanelAbierto(true);
  }

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={resumen.nombre} seccionActual="resumen">
      <EncabezadoDePantalla titulo="Resumen del edificio" ayuda={<Ayuda {...AYUDA_RESUMEN} />} />

      <div className="disposicion">
        <Panel
          titulo="Puesta a punto"
          descripcion="Siete pasos para dejar el edificio listo para liquidar las expensas. Tocá uno para ir a completarlo."
        >
          <BarraDeProgreso hechos={hechos} total={_PASOS.length} />
          <ol
            className="lista-de-filas lista-de-filas--tocable resumen__checklist"
            aria-label="Puesta a punto del edificio"
          >
            {_PASOS.map((paso) => {
              const hecho = estaHecho(paso);
              const titulo =
                paso.clave === "ubicacion" && !hecho ? (
                  <button type="button" className="boton-enlace" onClick={abrirEdicion}>
                    {paso.etiqueta}
                  </button>
                ) : paso.clave === "ubicacion" ? (
                  // Hecho: editar ya vive en "Datos del edificio" → "Editar"
                  // (abajo). Repetirlo acá sería un segundo botón para la
                  // misma acción.
                  <span>{paso.etiqueta}</span>
                ) : (
                  <a href={`/edificios/${id}${paso.href}`}>{paso.etiqueta}</a>
                );
              return (
                <li
                  key={paso.clave}
                  className="resumen__paso"
                  data-estado={hecho ? "hecho" : "falta"}
                >
                  <FilaConIcono
                    icono={paso.icono}
                    tono={hecho ? "listo" : "atencion"}
                    titulo={titulo}
                    detalle={paso.explicacion}
                    fin={<span className="resumen__estado">{hecho ? "Hecho" : "Falta"}</span>}
                  />
                </li>
              );
            })}
          </ol>
        </Panel>

        <div className="disposicion__lateral">
          <Panel titulo="Tu próximo paso" variante="apoyo">
            {resumen.listo_para_liquidar ? (
              <div className="resumen__proximo">
                <p className="resumen__listo" role="status">
                  Listo para liquidar
                </p>
                <p className="texto-secundario">
                  Completaste la puesta a punto. Ya podés generar las expensas del mes.
                </p>
              </div>
            ) : proximo ? (
              <div className="resumen__proximo">
                <p className="resumen__proximo-titulo">
                  <span className="numero-tabular">Paso {proximo.numero}.</span> {proximo.etiqueta}
                </p>
                <p className="texto-secundario">{proximo.explicacion}</p>
                {proximo.clave === "ubicacion" ? (
                  <button type="button" className="boton-principal" onClick={abrirEdicion}>
                    Completar este paso
                    <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
                  </button>
                ) : (
                  <a className="boton-principal" href={`/edificios/${id}${proximo.href}`}>
                    Completar este paso
                    <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
                  </a>
                )}
              </div>
            ) : (
              <p className="texto-secundario">
                Los siete pasos están hechos. Falta que el sistema confirme que el edificio quedó
                listo para liquidar.
              </p>
            )}
          </Panel>

          <Panel
            titulo="Datos del edificio"
            variante="apoyo"
            accion={
              <button ref={editarRef} type="button" onClick={abrirEdicion}>
                Editar
              </button>
            }
          >
            <dl className="renglones">
              <div className="renglones__fila">
                <dt>Localidad</dt>
                <dd>{resumen.localidad ?? "Sin completar"}</dd>
              </div>
              <div className="renglones__fila">
                <dt>Calle y número</dt>
                <dd>{resumen.calle_y_numero ?? "Sin completar"}</dd>
              </div>
              <div className="renglones__fila">
                <dt>Pisos</dt>
                <dd>
                  <span className="numero-tabular">{resumen.pisos ?? "Sin completar"}</span>
                </dd>
              </div>
              <div className="renglones__fila">
                <dt>Subsuelos</dt>
                <dd>
                  <span className="numero-tabular">{resumen.subsuelos ?? "Sin completar"}</span>
                </dd>
              </div>
              <div className="renglones__fila">
                <dt>Unidades</dt>
                <dd>
                  <span className="numero-tabular">{resumen.cantidad_unidades}</span>
                </dd>
              </div>
              <div className="renglones__fila renglones__fila--apilada">
                <dt>Coeficientes</dt>
                <dd>
                  <EstadoDeCoeficientes
                    estado={resumen.informe.estado}
                    diferencia={resumen.informe.diferencia}
                  />
                </dd>
              </div>
              <div className="renglones__fila renglones__fila--apilada">
                <dt>Saldos previos</dt>
                <dd>{textoEstadoDeMigracion(resumen.estado_migracion)}</dd>
              </div>
              <div className="renglones__fila renglones__fila--apilada">
                <dt>Intereses y vencimiento</dt>
                <dd className="resumen__datos">{textoDeVigente(vigente)}</dd>
              </div>
            </dl>
          </Panel>
        </div>
      </div>

      <PanelLateral
        abierto={panelAbierto}
        titulo="Editar edificio"
        alCerrar={() => setPanelAbierto(false)}
        devolverFocoA={editarRef}
      >
        <Formulario
          erroresPorCampo={estado?.erroresPorCampo ?? {}}
          erroresDesconocidos={estado?.erroresDesconocidos ?? []}
          action={enviar}
        >
          <Campo nombre="nombre" etiqueta="Nombre" name="nombre" defaultValue={resumen.nombre} />
          <SelectorDeUbicacion
            valorInicial={
              resumen.provincia_id && resumen.departamento_id && resumen.localidad_id
                ? {
                    provinciaId: resumen.provincia_id,
                    departamentoId: resumen.departamento_id,
                    localidadId: resumen.localidad_id,
                  }
                : null
            }
          />
          <Campo
            nombre="calle_y_numero"
            etiqueta="Calle y número"
            name="calle_y_numero"
            defaultValue={resumen.calle_y_numero ?? ""}
          />
          <Campo
            nombre="pisos"
            etiqueta="Pisos"
            name="pisos"
            type="number"
            min={1}
            max={60}
            defaultValue={resumen.pisos ?? undefined}
          />
          <Campo
            nombre="subsuelos"
            etiqueta="Subsuelos"
            name="subsuelos"
            type="number"
            min={0}
            max={5}
            defaultValue={resumen.subsuelos ?? undefined}
          />
          <button type="submit" className="boton-principal">
            Guardar
          </button>
        </Formulario>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}
