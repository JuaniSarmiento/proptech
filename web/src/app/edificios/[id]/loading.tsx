import { Estados } from "../../../componentes/Estados";

/** R3C-7 (rompedor 3b): `loading.tsx` REEMPLAZA toda la pantalla mientras
 * el segmento carga (nunca se anida dentro de `ArmazonDelEdificio`, a
 * diferencia de "cargando" en el flujo normal) — sin esto, axe en el
 * navegador real da `landmark-one-main`/`page-has-heading-one`. El `h1`
 * es visualmente oculto (`sr-only`): el esqueleto ya comunica "cargando"
 * con `role="status"`. */
export default function Cargando() {
  return (
    <main>
      <h1 className="sr-only">Cargando</h1>
      <Estados tipo="cargando" />
    </main>
  );
}
