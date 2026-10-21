import { Estados } from "../../componentes/Estados";

/** R3C-7 (rompedor 3b, repetido en 7.3): reemplaza toda la pantalla
 * mientras el segmento carga, con su propio `<main>`/`<h1>` (nunca anidado
 * dentro de `Armazon`), para no violar `landmark-one-main` en axe. */
export default function Cargando() {
  return (
    <main>
      <h1 className="sr-only">Cargando</h1>
      <Estados tipo="cargando" />
    </main>
  );
}
