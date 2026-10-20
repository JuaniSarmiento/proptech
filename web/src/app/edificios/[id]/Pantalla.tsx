/**
 * Resumen del edificio (tarea 4.2, D5, D11; enmienda del 20/10/2026): a la
 * izquierda el checklist de puesta a punto con su barra de progreso ("N de
 * 6 pasos"), cada paso como fila con ícono, explicación y estado; a la
 * derecha "Tu próximo paso" (la única acción principal de la pantalla) y
 * los datos del edificio. Ningún paso se decide acá (D5): se muestra tal
 * cual lo da la API, incluso si no cuadra con `cantidad_unidades` ("la web
 * no calcula"). La barra sólo CUENTA los pasos que la API ya marcó.
 */

import {
  ArrowRight,
  Building2,
  CalendarClock,
  FileCheck2,
  Layers,
  type LucideIcon,
  Percent,
  Tags,
} from "lucide-react";
import { Ayuda } from "../../../componentes/Ayuda";
import { BarraDeProgreso } from "../../../componentes/BarraDeProgreso";
import { EncabezadoDePantalla } from "../../../componentes/EncabezadoDePantalla";
import { EstadoDeCoeficientes } from "../../../componentes/EstadoDeCoeficientes";
import { FilaConIcono } from "../../../componentes/FilaConIcono";
import { Panel } from "../../../componentes/Panel";
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
    clave: "unidades",
    numero: 1,
    etiqueta: "Cargar unidades",
    explicacion: "Cada departamento, cochera o local, con su superficie y su coeficiente.",
    href: "/unidades",
    icono: Building2,
  },
  {
    clave: "coeficientes",
    numero: 2,
    etiqueta: "Revisar coeficientes (que sumen 100%)",
    explicacion: "Si la suma no da 100%, la expensa no se reparte bien entre los vecinos.",
    href: "/unidades",
    icono: Percent,
  },
  {
    clave: "grupos",
    numero: 3,
    etiqueta: "Armar los grupos de reparto",
    explicacion: "Para los gastos que pagan sólo algunas unidades, como el ascensor.",
    href: "/grupos",
    icono: Layers,
  },
  {
    clave: "categorias",
    numero: 4,
    etiqueta: "Definir las categorías de gasto",
    explicacion: "Los rubros en los que vas a anotar cada gasto del mes.",
    href: "/categorias",
    icono: Tags,
  },
  {
    clave: "intereses_y_vencimiento",
    numero: 5,
    etiqueta: "Configurar intereses y vencimiento",
    explicacion: "La tasa por pagar tarde, el fondo de reserva y el día en que vence.",
    href: "/configuracion",
    icono: CalendarClock,
  },
  {
    clave: "saldos_previos",
    numero: 6,
    etiqueta: "Confirmar que el edificio arranca sin saldos previos",
    explicacion: "Un único paso, que no se deshace: el edificio empieza sin deudas de antes.",
    href: "/saldos-previos",
    icono: FileCheck2,
  },
];

type Props = {
  id: string;
  resumen: Resumen;
  vigente: ConfiguracionVigente;
};

export function PantallaResumen({ id, resumen, vigente }: Props) {
  const estaHecho = (paso: Paso) => resumen.pasos[paso.clave] === "hecho";
  const hechos = _PASOS.filter(estaHecho).length;
  const proximo = _PASOS.find((paso) => !estaHecho(paso));

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={resumen.nombre} seccionActual="resumen">
      <EncabezadoDePantalla titulo="Resumen del edificio" ayuda={<Ayuda {...AYUDA_RESUMEN} />} />

      <div className="disposicion">
        <Panel
          titulo="Puesta a punto"
          descripcion="Seis pasos para dejar el edificio listo para liquidar las expensas. Tocá uno para ir a completarlo."
        >
          <BarraDeProgreso hechos={hechos} total={_PASOS.length} />
          <ol
            className="lista-de-filas lista-de-filas--tocable resumen__checklist"
            aria-label="Puesta a punto del edificio"
          >
            {_PASOS.map((paso) => {
              const hecho = estaHecho(paso);
              return (
                <li
                  key={paso.clave}
                  className="resumen__paso"
                  data-estado={hecho ? "hecho" : "falta"}
                >
                  <FilaConIcono
                    icono={paso.icono}
                    tono={hecho ? "listo" : "atencion"}
                    titulo={<a href={`/edificios/${id}${paso.href}`}>{paso.etiqueta}</a>}
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
                <a className="boton-principal" href={`/edificios/${id}${proximo.href}`}>
                  Completar este paso
                  <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
                </a>
              </div>
            ) : (
              <p className="texto-secundario">
                Los seis pasos están hechos. Falta que el sistema confirme que el edificio quedó
                listo para liquidar.
              </p>
            )}
          </Panel>

          <Panel titulo="Datos del edificio" variante="apoyo">
            <dl className="renglones">
              <div className="renglones__fila">
                <dt>Localidad</dt>
                <dd>{resumen.localidad}</dd>
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
    </ArmazonDelEdificio>
  );
}
