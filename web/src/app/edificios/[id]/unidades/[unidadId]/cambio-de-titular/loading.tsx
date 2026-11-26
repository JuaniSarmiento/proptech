import { Estados } from "../../../../../../componentes/Estados";

/** Igual que el resto de las pantallas del edificio: `loading.tsx` reemplaza toda la pantalla
 * mientras el segmento carga (R3C-7), con su `h1` visualmente oculto. */
export default function Cargando() {
  return (
    <main>
      <h1 className="sr-only">Cargando</h1>
      <Estados tipo="cargando" />
    </main>
  );
}
