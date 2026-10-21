import { Armazon } from "../../componentes/Armazon";
import { Estados } from "../../componentes/Estados";
export default function Cargando() {
  return (
    <Armazon publico>
      <h1>Tus administraciones</h1>
      <Estados tipo="cargando" />
    </Armazon>
  );
}
