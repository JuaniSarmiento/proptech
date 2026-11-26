"use client";

/**
 * Cuentas de vendedores (change 4d, H-034, D-168): la deuda que el cambio de titular pasó a nombre de
 * cada vendedor, en el orden que manda la API (la que más debe primero, también las que están en cero).
 * La pantalla no calcula nada: cada deuda es la de la API (R07, D-046).
 */

import { Ayuda } from "../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../componentes/EncabezadoDePantalla";
import { Panel } from "../../../../componentes/Panel";
import type { CuentaDeVendedor } from "../../../../lib/api/titularidad";
import { dinero } from "../../../../lib/formato";
import { ArmazonDelEdificio } from "../Armazon";
import { AYUDA_CUENTAS_DE_VENDEDORES } from "./ayuda";

type Props = {
  id: string;
  nombreEdificio: string;
  cuentas: CuentaDeVendedor[];
};

export function PantallaCuentasDeVendedores({ id, nombreEdificio, cuentas }: Props) {
  return (
    <ArmazonDelEdificio
      id={id}
      nombreEdificio={nombreEdificio}
      seccionActual="cuentas-de-vendedores"
    >
      <EncabezadoDePantalla
        titulo="Cuentas de vendedores"
        ayuda={<Ayuda {...AYUDA_CUENTAS_DE_VENDEDORES} />}
      />
      <Panel
        titulo="Quién debe"
        descripcion="Primero quien más debe. Abrí una cuenta para ver sus períodos y registrar un cobro."
      >
        {cuentas.length === 0 ? (
          <p role="status" className="texto-secundario">
            Todavía no hay cuentas de vendedores. Aparecen cuando vendés una unidad con la deuda a
            nombre del vendedor.
          </p>
        ) : (
          <ul className="lista-de-filas" aria-label="Cuentas de vendedores">
            {cuentas.map((cuenta) => (
              <li key={cuenta.cuenta_id} className="titularidad__cuenta">
                <a
                  className="titularidad__persona"
                  href={`/edificios/${id}/cuentas-de-vendedores/${cuenta.cuenta_id}`}
                >
                  {cuenta.persona.nombre}
                </a>
                <span className="numero-tabular titularidad__deuda">{dinero(cuenta.deuda)}</span>
                <span className="texto-secundario titularidad__unidades">
                  {cuenta.unidades.length === 0
                    ? "Sin unidades"
                    : `${cuenta.unidades.length === 1 ? "Unidad" : "Unidades"} ${cuenta.unidades
                        .map((u) => u.identificador)
                        .join(", ")}`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </ArmazonDelEdificio>
  );
}
