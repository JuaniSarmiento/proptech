"use client";

/**
 * Informar un pago (change 8, H-025): la persona sube el comprobante y, al elegirlo, la API lo lee con
 * IA y la pantalla muestra lo que leyó para que lo revise y lo corrija (si no se pudo leer, los campos
 * quedan vacíos y se cargan a mano). Después elige cuánto corresponde a cada unidad suya y envía. La
 * pantalla no suma ni redondea ningún monto: manda lo que hay y, si las partes no suman, muestra lo que
 * dice la API (R07). Con una sola unidad, el importe acompaña al monto mientras nadie lo toque.
 */

import { useState, useTransition } from "react";
import { Ayuda } from "../../../../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../../../../componentes/EncabezadoDePantalla";
import { Campo, Formulario } from "../../../../../componentes/Formulario";
import { Panel } from "../../../../../componentes/Panel";
import type { UnidadParaInformar } from "../../../../../lib/api/pagos";
import { ArmazonDelEdificio } from "../../Armazon";
import type { DatosDelPago, ResultadoDeLectura, ResultadoDelEnvio } from "./acciones";
import { AYUDA_INFORMAR_PAGO } from "./ayuda";

type Props = {
  id: string;
  nombreEdificio: string;
  unidades: UnidadParaInformar[];
  accionLeer: (formData: FormData) => Promise<ResultadoDeLectura>;
  accionEnviar: (datos: DatosDelPago) => Promise<ResultadoDelEnvio>;
};

type Leido = { comprobanteId: string; sePudoLeer: boolean };

export function PantallaInformarPago({
  id,
  nombreEdificio,
  unidades,
  accionLeer,
  accionEnviar,
}: Props) {
  const [leyendo, leer] = useTransition();
  const [enviando, enviar] = useTransition();
  const [leido, setLeido] = useState<Leido | null>(null);
  const [errorDelArchivo, setErrorDelArchivo] = useState<string | null>(null);
  const [banco, setBanco] = useState("");
  const [numero, setNumero] = useState("");
  const [fecha, setFecha] = useState("");
  const [monto, setMonto] = useState("");
  const [cbu, setCbu] = useState("");
  const [importes, setImportes] = useState<Record<string, string>>({});
  const [importeEditado, setImporteEditado] = useState(false);
  const [resultado, setResultado] = useState<ResultadoDelEnvio | null>(null);

  const unaSolaUnidad = unidades.length === 1 ? unidades[0] : undefined;

  function alElegirElArchivo(archivo: File | undefined) {
    setResultado(null);
    setErrorDelArchivo(null);
    setLeido(null);
    if (!archivo) return;
    const cuerpo = new FormData();
    cuerpo.append("archivo", archivo, archivo.name);
    leer(async () => {
      const respuesta = await accionLeer(cuerpo);
      if ("error" in respuesta) {
        setErrorDelArchivo(respuesta.error);
        return;
      }
      const p = respuesta.propuesta;
      setBanco(p.banco ?? "");
      setNumero(p.numero_de_operacion ?? "");
      setFecha(p.fecha ?? "");
      setMonto(p.monto ?? "");
      setCbu(p.cbu_origen ?? "");
      setImporteEditado(false);
      setImportes(unaSolaUnidad && p.monto ? { [unaSolaUnidad.unidad_id]: p.monto } : {});
      setLeido({ comprobanteId: respuesta.comprobanteId, sePudoLeer: respuesta.lectura === "ok" });
    });
  }

  function cambiarMonto(nuevo: string) {
    setMonto(nuevo);
    // Una sola unidad: el importe copia el texto del monto mientras la persona no lo toque.
    if (unaSolaUnidad && !importeEditado) {
      setImportes({ [unaSolaUnidad.unidad_id]: nuevo });
    }
  }

  function alEnviar() {
    if (!leido) return;
    enviar(async () => {
      const respuesta = await accionEnviar({
        comprobanteId: leido.comprobanteId,
        banco,
        numeroDeOperacion: numero,
        fechaDeTransferencia: fecha,
        monto,
        cbuDeOrigen: cbu,
        partes: unidades.map((unidad) => ({
          unidadId: unidad.unidad_id,
          importe: importes[unidad.unidad_id] ?? "",
        })),
      });
      // Con éxito la acción redirige y no vuelve; si vuelve, trae los errores.
      setResultado(respuesta);
    });
  }

  return (
    <ArmazonDelEdificio id={id} nombreEdificio={nombreEdificio} seccionActual="mis-pagos">
      <EncabezadoDePantalla titulo="Informar un pago" ayuda={<Ayuda {...AYUDA_INFORMAR_PAGO} />} />
      {unidades.length === 0 ? (
        <Panel titulo="Tus unidades">
          <p className="texto-secundario">
            No tenés unidades en este edificio para informar un pago.
          </p>
        </Panel>
      ) : (
        <Formulario
          erroresPorCampo={{
            ...(errorDelArchivo ? { comprobante: errorDelArchivo } : {}),
            ...(resultado?.erroresPorCampo ?? {}),
          }}
          erroresDesconocidos={resultado?.erroresDesconocidos ?? []}
          onSubmit={(evento) => {
            evento.preventDefault();
            alEnviar();
          }}
          aria-label="Informar un pago"
        >
          <Panel
            titulo="Tu comprobante"
            descripcion="Una foto o un PDF de la transferencia, de hasta 10 MB. Lo leemos para completar los datos."
          >
            <Campo
              nombre="comprobante"
              etiqueta="Comprobante"
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              onChange={(e) => alElegirElArchivo(e.target.files?.[0])}
            />
            {leyendo ? (
              <p role="status" className="texto-secundario">
                Leyendo el comprobante…
              </p>
            ) : null}
            {leido && !leido.sePudoLeer ? (
              <p role="alert" className="aviso">
                No pudimos leer el comprobante. Cargá los datos a mano.
              </p>
            ) : null}
          </Panel>

          {leido ? (
            <>
              <Panel
                titulo="Datos del pago"
                descripcion={
                  leido.sePudoLeer
                    ? "Esto es lo que leímos. Revisalo contra tu comprobante y corregí lo que haga falta."
                    : "Completalo con lo que dice tu comprobante."
                }
              >
                <Campo
                  nombre="banco"
                  etiqueta="Banco"
                  autoComplete="off"
                  maxLength={100}
                  required
                  value={banco}
                  onChange={(e) => setBanco(e.target.value)}
                />
                <Campo
                  nombre="numero_de_operacion"
                  etiqueta="Número de operación"
                  autoComplete="off"
                  maxLength={100}
                  required
                  value={numero}
                  onChange={(e) => setNumero(e.target.value)}
                />
                <Campo
                  nombre="fecha_de_transferencia"
                  etiqueta="Fecha de la transferencia"
                  type="date"
                  required
                  value={fecha}
                  onChange={(e) => setFecha(e.target.value)}
                />
                <Campo
                  nombre="monto"
                  etiqueta="Monto"
                  inputMode="decimal"
                  autoComplete="off"
                  required
                  value={monto}
                  onChange={(e) => cambiarMonto(e.target.value)}
                />
                <Campo
                  nombre="cbu_origen"
                  etiqueta="CBU de origen"
                  inputMode="numeric"
                  autoComplete="off"
                  maxLength={22}
                  value={cbu}
                  onChange={(e) => setCbu(e.target.value)}
                />
              </Panel>

              <Panel
                titulo="Cuánto es de cada unidad"
                descripcion={
                  unidades.length === 1
                    ? "El pago es de tu unidad."
                    : "Si pagaste por más de una unidad, escribí cuánto corresponde a cada una. Dejá vacías las que no pagaste."
                }
              >
                {unidades.map((unidad) => (
                  <Campo
                    key={unidad.unidad_id}
                    nombre={`importe_${unidad.unidad_id}`}
                    etiqueta={`Importe para ${unidad.identificador}`}
                    inputMode="decimal"
                    autoComplete="off"
                    value={importes[unidad.unidad_id] ?? ""}
                    onChange={(e) => {
                      setImporteEditado(true);
                      setImportes({ ...importes, [unidad.unidad_id]: e.target.value });
                    }}
                  />
                ))}
              </Panel>

              <p>
                <button
                  type="submit"
                  className="boton-principal"
                  disabled={enviando}
                  aria-busy={enviando}
                >
                  {enviando ? "Enviando…" : "Enviar"}
                </button>
              </p>
            </>
          ) : null}
        </Formulario>
      )}
    </ArmazonDelEdificio>
  );
}
