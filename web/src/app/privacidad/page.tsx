import { Armazon } from "../../componentes/Armazon";
import { Ayuda } from "../../componentes/Ayuda";
import { EncabezadoDePantalla } from "../../componentes/EncabezadoDePantalla";

/** D7 (tarea 5.5): el borrador de 7.2 queda pendiente de los datos legales
 * del responsable; el texto de esta página es para quien la lee, nunca una
 * nota de trabajo interno (requisito "El aviso de privacidad no muestra
 * notas internas"). */
export default function Privacidad() {
  return (
    <Armazon publico>
      <div className="pagina-lectura">
        <EncabezadoDePantalla
          titulo="Aviso de privacidad"
          ayuda={
            <Ayuda
              paraQueSirve="Acá podés leer cómo se usan tus datos al entrar a PropTech."
              pasos={[
                "Leé qué datos se usan y dónde se guardan.",
                "Revisá tus derechos y cómo pedir ayuda a tu administración.",
              ]}
              ejemplo="Si tu nombre está mal escrito, podés pedir que lo corrijan."
              yDespues="Podés volver al ingreso o consultar a la administración que te invitó."
            />
          }
        />
        <p className="texto-secundario">
          Este aviso todavía está en revisión: faltan completar el responsable, el contacto y el
          plazo de conservación antes de la versión definitiva.
        </p>
        <section aria-labelledby="datos">
          <h2 id="datos">Qué datos usamos</h2>
          <p>
            Para ingresar, Clerk guarda tu email y tu nombre. PropTech guarda tu relación con la
            administración y los permisos que te asigna.
          </p>
        </section>
        <section aria-labelledby="donde">
          <h2 id="donde">Dónde se guardan</h2>
          <p>
            Clerk es el servicio que comprueba tu identidad. El email y el nombre se transfieren y
            se procesan fuera de la Argentina. Los datos del edificio y tus permisos se administran
            en PropTech.
          </p>
        </section>
        <section aria-labelledby="finalidad">
          <h2 id="finalidad">Para qué los usamos</h2>
          <p>
            Usamos esos datos para enviarte la invitación, permitirte ingresar y recuperar el acceso
            a tu cuenta. Los permisos para ver o cambiar información los define tu administración en
            PropTech.
          </p>
        </section>
        <section aria-labelledby="tiempo">
          <h2 id="tiempo">Cuánto tiempo</h2>
          <p>
            El plazo de conservación y el procedimiento de baja están pendientes de confirmación
            antes de publicar la versión definitiva de este aviso.
          </p>
        </section>
        <section aria-labelledby="responsable">
          <h2 id="responsable">Responsable y contacto</h2>
          <p>
            Falta confirmar la identidad legal, el domicilio y el contacto del responsable. Mientras
            se revisa este borrador, consultá a la administración que te invitó.
          </p>
        </section>
        <section aria-labelledby="derechos">
          <h2 id="derechos">Tus derechos</h2>
          <p>
            La ley 25.326 reconoce tus derechos de acceso, rectificación y supresión de tus datos
            personales. Podés pedir conocer tus datos, corregirlos o solicitar su eliminación cuando
            corresponda.
          </p>
          <p>
            El canal para enviar esas solicitudes se completará con los datos del responsable antes
            de aprobar este aviso.
          </p>
          <a href="https://www.argentina.gob.ar/aaip/datospersonales/derechos">
            Conocé tus derechos en la AAIP
          </a>
        </section>
        <a href="/ingresar">Volver al ingreso</a>
      </div>
    </Armazon>
  );
}
