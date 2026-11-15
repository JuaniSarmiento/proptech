import { Estados } from "../../../../../componentes/Estados";

/** `loading.tsx` reemplaza toda la pantalla mientras carga (R3C-7): `main` y `h1` propios. */
export default function Cargando() {
  return (
    <main>
      <h1 className="sr-only">Cargando</h1>
      <Estados tipo="cargando" />
    </main>
  );
}
