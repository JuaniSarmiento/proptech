import { describe, expect, it } from "vitest";
import { queHaceElPerfil } from "./perfiles";

/**
 * Corrección del orquestador (L-026, mirada de `personal-1440.png`,
 * 21/10/2026): el texto de "Qué puede cada perfil" describía al contador
 * como si cargara, emitiera y confirmara pagos. La matriz real es D-106
 * (`knowledge-base/09_decisiones_y_supuestos.md`) y, en código,
 * `backend/src/proptech_core/acceso/dominio/permisos.py`: el contador NO
 * tiene ninguna celda de escritura en `_MATRIZ` (sólo
 * `VER_CONFIGURACION_DEL_EDIFICIO`, con `_CP`/`_CE`), así que es de sólo
 * lectura. El administrador sí escribe, pero anular, revertir o condonar
 * son sólo del principal (`_AP`, sin `_AE`, en esas tres filas de la
 * matriz) — ninguna de las dos cosas estaba en el texto de la pantalla.
 */
describe("queHaceElPerfil, contra la matriz de D-106 / permisos.py", () => {
  it("el contador es de sólo lectura: nunca dice que carga, emite ni confirma pagos", () => {
    const texto = queHaceElPerfil("contador");
    expect(texto).not.toMatch(/carga gastos/i);
    expect(texto).not.toMatch(/emite liquidaciones/i);
    expect(texto).not.toMatch(/confirma pagos/i);
    expect(texto).toMatch(/sólo lectura/i);
  });

  it("el administrador aclara que anular, revertir o condonar es sólo del principal", () => {
    const texto = queHaceElPerfil("administrador");
    expect(texto).toMatch(/carga gastos, emite liquidaciones y confirma pagos/i);
    expect(texto).toMatch(/principal/i);
    expect(texto).toMatch(/anula|anular/i);
  });

  it("super admin, auxiliar y consejo ya coincidían con la matriz (sin cambios)", () => {
    expect(queHaceElPerfil("super_admin")).toBe(
      "Administra toda la empresa: invita personal y crea edificios.",
    );
    expect(queHaceElPerfil("auxiliar")).toBe(
      "Ve la configuración de su edificio; no carga ni aprueba nada.",
    );
    expect(queHaceElPerfil("consejo")).toBe(
      "Ve la configuración de su edificio; no carga ni aprueba nada.",
    );
  });
});
