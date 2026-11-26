/**
 * Cifras rotuladas del portal (H-040): una lista de definiciones (`<dt>` rótulo, `<dd>` valor) para que
 * cada importe se lea con su nombre. Sólo muestra: el valor llega ya formateado de quien la usa, que
 * lo toma tal cual de la API (N02). La principal pesa más que el resto.
 */

export type Cifra = { rotulo: string; valor: string; principal?: boolean };

export function Cifras({ cifras }: { cifras: Cifra[] }) {
  return (
    <dl className="cifras">
      {cifras.map((c) => (
        <div
          key={c.rotulo}
          className="cifras__par"
          data-principal={c.principal ? "true" : undefined}
        >
          <dt>{c.rotulo}</dt>
          <dd className="numero-tabular">{c.valor}</dd>
        </div>
      ))}
    </dl>
  );
}
