/**
 * El inicio del portal del vecino (change 11, H-040, C01): todas las unidades de la persona, de todos
 * sus edificios, con lo que debe, cuándo vence y sus créditos, y el total del conjunto. La pantalla no
 * suma ni resta nada (N02): muestra lo que la API contesta, con formato argentino. El inquilino no ve
 * nada extraordinario porque la API no se lo manda (D-170.2).
 */

import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Panel } from "../../componentes/Panel";
import type { MisUnidades, UnidadDelVecino } from "../../lib/api/vecino";
import { dinero, fecha } from "../../lib/formato";
import { ArmazonDelPortal } from "../_portal/ArmazonDelPortal";
import { Cifras } from "../_portal/Cifras";
import { AvisoDeInstalacion } from "./AvisoDeInstalacion";
import { AYUDA_INICIO } from "./ayuda";

const VINCULO = { propietario: "Propietario", inquilino: "Inquilino" } as const;

function FilaDeUnidad({ unidad }: { unidad: UnidadDelVecino }) {
  return (
    <li className="unidad-del-vecino">
      <div className="unidad-del-vecino__cabecera">
        <p className="unidad-del-vecino__nombre">{unidad.identificador}</p>
        <p className="texto-secundario">
          {unidad.edificio} · {VINCULO[unidad.vinculo]}
        </p>
      </div>
      <Cifras
        cifras={[
          { rotulo: "Total a pagar", valor: dinero(unidad.total_a_pagar), principal: true },
          {
            rotulo: "Vencimiento",
            valor: unidad.vencimiento === null ? "Sin vencimiento" : fecha(unidad.vencimiento),
          },
          { rotulo: "Crédito aplicable", valor: dinero(unidad.credito_aplicable) },
          { rotulo: "Crédito retenido", valor: dinero(unidad.credito_retenido) },
        ]}
      />
      <a className="unidad-del-vecino__enlace" href={`/mis-liquidaciones/${unidad.unidad_id}`}>
        Ver liquidaciones de {unidad.identificador}
      </a>
    </li>
  );
}

export function PantallaInicio({ datos }: { datos: MisUnidades }) {
  const { conjunto, unidades } = datos;
  return (
    <ArmazonDelPortal seccionActual="inicio" unidades={unidades}>
      <EncabezadoDePantalla titulo="Inicio" ayuda={<Ayuda {...AYUDA_INICIO} />} />
      <AvisoDeInstalacion />
      {unidades.length === 0 ? (
        <Panel titulo="Mis unidades">
          <p role="status" className="texto-secundario">
            Todavía no tenés unidades asociadas a tu cuenta. Pedile al administrador que te dé de
            alta como vecino.
          </p>
        </Panel>
      ) : (
        <>
          {unidades.length > 1 ? (
            <Panel
              titulo="Total del conjunto"
              descripcion={`Todas tus unidades juntas, al ${fecha(datos.fecha)}.`}
            >
              <Cifras
                cifras={[
                  {
                    rotulo: "Total a pagar",
                    valor: dinero(conjunto.total_a_pagar),
                    principal: true,
                  },
                  { rotulo: "Intereses", valor: dinero(conjunto.intereses) },
                  { rotulo: "Crédito aplicable", valor: dinero(conjunto.credito_aplicable) },
                  { rotulo: "Crédito retenido", valor: dinero(conjunto.credito_retenido) },
                ]}
              />
            </Panel>
          ) : null}
          <Panel
            titulo="Tus unidades"
            descripcion={`Lo que debés en cada una, al ${fecha(datos.fecha)}.`}
          >
            <ul className="lista-de-unidades" aria-label="Mis unidades">
              {unidades.map((u) => (
                <FilaDeUnidad key={u.unidad_id} unidad={u} />
              ))}
            </ul>
          </Panel>
        </>
      )}
    </ArmazonDelPortal>
  );
}
