/**
 * Comprobantes (change 11, H-040, C03): por cada unidad de la persona, los PDFs de sus expensas y los
 * pagos confirmados. El PDF baja por la ruta propia de la web (`/documentos/descarga?token=...`) con
 * el token del enlace firmado que dio la API: el navegador nunca recibe una dirección de `/api`. Los
 * importes se muestran tal como vienen (N02); al inquilino la API le manda lo suyo (D-170.2).
 */

import { Download } from "lucide-react";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";
import { Panel } from "../../componentes/Panel";
import {
  direccionDeDescarga,
  type PagoConfirmadoDelVecino,
  type PdfDelVecino,
  type UnidadDelVecino,
} from "../../lib/api/vecino";
import { dinero, fecha, periodoEnPalabras } from "../../lib/formato";
import { ArmazonDelPortal } from "../_portal/ArmazonDelPortal";
import { AYUDA_COMPROBANTES } from "./ayuda";

export type ComprobantesDeLaUnidad = {
  unidad: UnidadDelVecino;
  pdfs: PdfDelVecino[];
  pagos: PagoConfirmadoDelVecino[];
};

export function PantallaComprobantes({
  unidades,
  porUnidad,
}: {
  unidades: UnidadDelVecino[];
  porUnidad: ComprobantesDeLaUnidad[];
}) {
  return (
    <ArmazonDelPortal seccionActual="comprobantes" unidades={unidades}>
      <EncabezadoDePantalla titulo="Comprobantes" ayuda={<Ayuda {...AYUDA_COMPROBANTES} />} />
      {porUnidad.length === 0 ? (
        <Panel titulo="Tus unidades">
          <p role="status" className="texto-secundario">
            Todavía no tenés unidades asociadas a tu cuenta.
          </p>
        </Panel>
      ) : (
        porUnidad.map(({ unidad, pdfs, pagos }) => (
          <Panel
            key={unidad.unidad_id}
            titulo={`Comprobantes de ${unidad.identificador}`}
            descripcion={unidad.edificio}
          >
            <div className="comprobantes__bloque">
              <h3>Expensas en PDF</h3>
              <p className="texto-secundario">
                El enlace de cada PDF vale 15 minutos: si venció, recargá la página.
              </p>
              {pdfs.length === 0 ? (
                <p role="status" className="texto-secundario">
                  No hay PDFs disponibles.
                </p>
              ) : (
                <ul className="lista-de-filas" aria-label={`PDFs de ${unidad.identificador}`}>
                  {pdfs.map((pdf) => {
                    const periodo = periodoEnPalabras(pdf.periodo) ?? pdf.periodo;
                    const direccion = direccionDeDescarga(pdf.url);
                    return (
                      <li key={pdf.documento_id}>
                        <span className="comprobantes__periodo">{periodo}</span>
                        {direccion === null ? null : (
                          <a className="comprobantes__descarga" href={direccion}>
                            <Download size={18} strokeWidth={1.75} aria-hidden="true" />
                            Descargar PDF de {periodo}
                          </a>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
            <div className="comprobantes__bloque">
              <h3>Pagos confirmados</h3>
              {pagos.length === 0 ? (
                <p role="status" className="texto-secundario">
                  No hay pagos confirmados.
                </p>
              ) : (
                <ul
                  className="lista-de-filas"
                  aria-label={`Pagos confirmados de ${unidad.identificador}`}
                >
                  {pagos.map((pago) => (
                    <li key={pago.pago_id} className="pago-confirmado">
                      <div className="pago-confirmado__textos">
                        <span className="pago-confirmado__fecha">
                          {fecha(pago.fecha_de_transferencia)}
                        </span>
                        <span className="texto-secundario">
                          {pago.banco} · {pago.numero_de_operacion}
                        </span>
                      </div>
                      <span className="numero-tabular pago-confirmado__importe">
                        {dinero(pago.importe)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Panel>
        ))
      )}
    </ArmazonDelPortal>
  );
}
