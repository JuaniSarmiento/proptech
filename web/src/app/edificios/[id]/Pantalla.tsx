/**
 * Resumen del edificio (tarea 4.2, D5, D11): el checklist de puesta a
 * punto con "hecho"/"falta" y su enlace, "Listo para liquidar" cuando la
 * API lo dice, y los datos del edificio más la configuración vigente en
 * una línea. Ningún paso se decide acá (D5): se muestra tal cual lo da la
 * API, incluso si no cuadra con `cantidad_unidades` ("la web no calcula").
 */

import { Ayuda } from "../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../componentes/EncabezadoDePantalla";
import type { ConfiguracionVigente, Resumen } from "../../../lib/api/tipos";
import { ArmazonDelEdificio } from "./Armazon";
import { AYUDA_RESUMEN } from "./ayuda";
import { textoDeVigente } from "./textoDeVigente";

type ClavePaso = keyof Resumen["pasos"];

const _PASOS: Array<{ clave: ClavePaso; numero: number; etiqueta: string; href: string }> = [
  { clave: "unidades", numero: 1, etiqueta: "Cargar unidades", href: "/unidades" },
  {
    clave: "coeficientes",
    numero: 2,
    etiqueta: "Revisar coeficientes (que sumen 100%)",
    href: "/unidades",
  },
  { clave: "grupos", numero: 3, etiqueta: "Armar los grupos de reparto", href: "/grupos" },
  {
    clave: "categorias",
    numero: 4,
    etiqueta: "Definir las categorías de gasto",
    href: "/categorias",
  },
  {
    clave: "intereses_y_vencimiento",
    numero: 5,
    etiqueta: "Configurar intereses y vencimiento",
    href: "/configuracion",
  },
  {
    clave: "saldos_previos",
    numero: 6,
    etiqueta: "Confirmar que el edificio arranca sin saldos previos",
    href: "/saldos-previos",
  },
];

type Props = {
  id: string;
  resumen: Resumen;
  vigente: ConfiguracionVigente;
};

export function PantallaResumen({ id, resumen, vigente }: Props) {
  return (
    <ArmazonDelEdificio id={id} nombreEdificio={resumen.nombre} seccionActual="resumen">
      <EncabezadoDePantalla titulo="Resumen del edificio" ayuda={<Ayuda {...AYUDA_RESUMEN} />} />

      {resumen.listo_para_liquidar ? (
        <p className="resumen__listo" role="status">
          Listo para liquidar
        </p>
      ) : null}

      <ol className="resumen__checklist" aria-label="Puesta a punto del edificio">
        {_PASOS.map((paso) => {
          const hecho = resumen.pasos[paso.clave] === "hecho";
          return (
            <li key={paso.clave} className="resumen__paso" data-estado={hecho ? "hecho" : "falta"}>
              <a href={`/edificios/${id}${paso.href}`}>
                <span className="resumen__numero numero-tabular">{paso.numero}.</span>{" "}
                {paso.etiqueta}
              </a>{" "}
              <span className="resumen__estado">{hecho ? "Hecho" : "Falta"}</span>
            </li>
          );
        })}
      </ol>

      <p className="resumen__datos">
        {resumen.localidad} · <span className="numero-tabular">{resumen.cantidad_unidades}</span>{" "}
        unidades · {textoDeVigente(vigente)}
      </p>
    </ArmazonDelEdificio>
  );
}
