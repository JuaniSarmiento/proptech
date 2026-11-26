"use client";

/**
 * La cuenta de un vendedor (change 4d, H-034, H-033, D-168): la deuda, lo que debe por período y
 * componente, los movimientos y, sólo con `confirmar_pago_informado` en el edificio, "Registrar cobro":
 * importe (con coma decimal) y fecha de la transferencia; "Registrar cobro" valida y abre una confirmación
 * (el mismo `PanelLateral` del ajuste: `role="dialog"`, `Esc`, foco devuelto) que dice qué se va a
 * registrar; al confirmar se muestra lo que contesta la API. La pantalla no calcula nada: la deuda nueva
 * y cada fila son las de la API, nunca la suma de los períodos (R07, D-046).
 */

import { type FormEvent, useActionState, useEffect, useRef, useState } from "react";
import { useFormStatus } from "react-dom";
import { Ayuda } from "../../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../../componentes/EncabezadoDePantalla";
import { Campo, Formulario } from "../../../../../componentes/Formulario";
import { Panel } from "../../../../../componentes/Panel";
import { PanelLateral } from "../../../../../componentes/PanelLateral";
import { permite, useSesionDePantalla } from "../../../../../componentes/SesionDePantalla";
import type { ComponenteDeCuenta, DetalleDeCuenta } from "../../../../../lib/api/titularidad";
import { dinero, fecha as fechaArgentina, mesYAnio } from "../../../../../lib/formato";
import { ArmazonDelEdificio } from "../../Armazon";
import type { EstadoDelCobro } from "./acciones";
import { AYUDA_CUENTA_DE_VENDEDOR } from "./ayuda";
import { importeParaApi, validarCobro } from "./validacion";

type Props = {
  id: string;
  nombreEdificio: string;
  cuenta: DetalleDeCuenta;
  accionCobrar: (estadoPrevio: EstadoDelCobro, formData: FormData) => Promise<EstadoDelCobro>;
};

const COMPONENTES: { clave: ComponenteDeCuenta; texto: string }[] = [
  { clave: "interes", texto: "Interés" },
  { clave: "ordinaria", texto: "Ordinaria" },
  { clave: "fondo_de_reserva", texto: "Fondo de reserva" },
  { clave: "extraordinaria", texto: "Extraordinaria" },
];

const MOVIMIENTO: Record<string, string> = {
  traslado: "Traslado de deuda",
  pago: "Cobro",
};

function BotonDeLaConfirmacion() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" className="boton-principal" disabled={pending} aria-busy={pending}>
      {pending ? "Registrando…" : "Confirmar cobro"}
    </button>
  );
}

/** Una tabla ancha se desplaza en su propio contenedor, que tiene que poder enfocarse con teclado
 * (axe: `scrollable-region-focusable`). */
function TablaDesplazable({ nombre, children }: { nombre: string; children: React.ReactNode }) {
  return (
    <section
      className="titularidad__tabla"
      aria-label={nombre}
      // biome-ignore lint/a11y/noNoninteractiveTabindex: una región que se desplaza tiene que poder enfocarse con teclado.
      tabIndex={0}
    >
      {children}
    </section>
  );
}

const _CERO = /^0+\.00$/;

export function PantallaCuentaDeVendedor({
  id,
  nombreEdificio,
  cuenta: inicial,
  accionCobrar,
}: Props) {
  const puedeCobrar = permite(useSesionDePantalla(), "confirmar_pago_informado", id);
  const [estado, enviar] = useActionState(accionCobrar, null);
  const [importe, setImporte] = useState("");
  const [fecha, setFecha] = useState("");
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [abierta, setAbierta] = useState(false);
  const botonRef = useRef<HTMLButtonElement>(null);

  // Lo que contesta la API: la deuda nueva y las dos tablas son las suyas.
  const cuenta = estado?.cuenta ?? inicial;
  const cobrado = estado?.cuenta !== undefined;

  // Cualquier respuesta cierra la confirmación: con un error, la pantalla queda con lo cargado.
  useEffect(() => {
    if (!estado) return;
    setAbierta(false);
    if (estado.cuenta) {
      setImporte("");
      setFecha("");
      setErrores({});
      return;
    }
    if (estado.erroresPorCampo) {
      setErrores(estado.erroresPorCampo);
      const primero = Object.keys(estado.erroresPorCampo)[0];
      if (primero) document.getElementById(`campo-${primero}`)?.focus();
    }
  }, [estado]);

  function alRegistrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const locales = validarCobro(importe, fecha);
    setErrores(locales);
    const primero = Object.keys(locales)[0];
    if (primero) {
      document.getElementById(`campo-${primero}`)?.focus();
      return;
    }
    setAbierta(true);
  }

  const sinDeuda = _CERO.test(cuenta.deuda);
  const importeAPI = importeParaApi(importe);

  return (
    <ArmazonDelEdificio
      id={id}
      nombreEdificio={nombreEdificio}
      seccionActual="cuentas-de-vendedores"
    >
      <EncabezadoDePantalla
        titulo={`Cuenta de ${cuenta.persona.nombre}`}
        ayuda={<Ayuda {...AYUDA_CUENTA_DE_VENDEDOR} />}
      />
      <p>
        <a className="boton-enlace" href={`/edificios/${id}/cuentas-de-vendedores`}>
          Volver a cuentas de vendedores
        </a>
      </p>

      {cobrado ? (
        <p role="status" className="estado-confirmado">
          Cobro registrado
        </p>
      ) : null}

      <Panel
        titulo="Deuda de la cuenta"
        descripcion="La que figura hoy en el libro, la haya o no cobrado alguna vez."
      >
        <p className="titularidad__total numero-tabular">{dinero(cuenta.deuda)}</p>
        <p className="texto-secundario">
          {cuenta.unidades.length === 0
            ? "Sin unidades"
            : `${cuenta.unidades.length === 1 ? "Unidad" : "Unidades"} ${cuenta.unidades
                .map((u) => u.identificador)
                .join(", ")}`}
        </p>
      </Panel>

      {puedeCobrar ? (
        <Panel
          titulo="Cobro al vendedor"
          descripcion="Registrá lo que te transfirió: se imputa a lo más viejo primero."
        >
          {sinDeuda ? (
            <p className="texto-secundario">Esta cuenta no tiene deuda: no hay nada para cobrar.</p>
          ) : (
            <Formulario
              erroresPorCampo={errores}
              onSubmit={alRegistrar}
              aria-label="Registrar cobro"
            >
              <Campo
                nombre="importe"
                etiqueta="Importe"
                inputMode="decimal"
                autoComplete="off"
                value={importe}
                onChange={(e) => setImporte(e.target.value)}
              />
              <Campo
                nombre="fecha"
                etiqueta="Fecha del cobro"
                type="date"
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
              />
              <button ref={botonRef} type="submit" className="boton-principal">
                Registrar cobro
              </button>
            </Formulario>
          )}
          {estado?.error ? (
            <p role="alert" className="campo__error">
              {estado.error}
            </p>
          ) : null}
        </Panel>
      ) : null}

      <Panel
        titulo="Deuda por período"
        descripcion="Lo trasladado, lo cobrado y lo que falta, por mes y componente."
      >
        {cuenta.periodos.length === 0 ? (
          <p className="texto-secundario">Todavía no hay períodos.</p>
        ) : (
          <TablaDesplazable nombre="Deuda por período, tabla desplazable">
            <table className="padron-de-unidades">
              <caption className="sr-only">Deuda por período</caption>
              <thead>
                <tr>
                  <th>Período</th>
                  <th>Componente</th>
                  <th className="numero-tabular">Debe</th>
                  <th className="numero-tabular">Cobrado</th>
                  <th className="numero-tabular">Pendiente</th>
                </tr>
              </thead>
              <tbody>
                {cuenta.periodos.flatMap((periodo) =>
                  COMPONENTES.filter((c) => periodo.componentes[c.clave] !== undefined).map((c) => {
                    const monto = periodo.componentes[c.clave];
                    return (
                      <tr key={`${periodo.periodo}-${c.clave}`}>
                        <td className="numero-tabular">{mesYAnio(periodo.periodo)}</td>
                        <td>{c.texto}</td>
                        <td className="numero-tabular">{dinero(monto?.debe ?? "0.00")}</td>
                        <td className="numero-tabular">{dinero(monto?.cobrado ?? "0.00")}</td>
                        <td className="numero-tabular">{dinero(monto?.pendiente ?? "0.00")}</td>
                      </tr>
                    );
                  }),
                )}
              </tbody>
            </table>
          </TablaDesplazable>
        )}
      </Panel>

      <Panel titulo="Movimientos de la cuenta" descripcion="En el orden en que se registraron.">
        {cuenta.movimientos.length === 0 ? (
          <p className="texto-secundario">Todavía no hay movimientos.</p>
        ) : (
          <TablaDesplazable nombre="Movimientos, tabla desplazable">
            <table className="padron-de-unidades">
              <caption className="sr-only">Movimientos</caption>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Movimiento</th>
                  <th className="numero-tabular">Importe</th>
                </tr>
              </thead>
              <tbody>
                {cuenta.movimientos.map((m) => (
                  <tr key={m.id}>
                    <td className="numero-tabular">{fechaArgentina(m.fecha)}</td>
                    <td>{MOVIMIENTO[m.tipo] ?? m.tipo}</td>
                    <td className="numero-tabular">{dinero(m.importe)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TablaDesplazable>
        )}
      </Panel>

      <PanelLateral
        abierto={abierta}
        titulo="Confirmar cobro"
        alCerrar={() => setAbierta(false)}
        devolverFocoA={botonRef}
      >
        <div className="panel-lateral__seccion">
          <p>
            Vas a registrar un cobro de {dinero(importeAPI ?? "0.00")} del {fechaArgentina(fecha)}.
            Queda registrado en el libro con esa fecha.
          </p>
          <form action={enviar}>
            <input type="hidden" name="importe" value={importe.trim()} />
            <input type="hidden" name="fecha" value={fecha} />
            <div className="panel-lateral__acciones">
              <button type="button" className="boton-secundario" onClick={() => setAbierta(false)}>
                Cancelar
              </button>
              <BotonDeLaConfirmacion />
            </div>
          </form>
        </div>
      </PanelLateral>
    </ArmazonDelEdificio>
  );
}
