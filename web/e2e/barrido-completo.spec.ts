/**
 * Barrido completo del navegador real (D7, tarea 5.1): las pantallas del
 * edificio por CADA escenario de `escenarios.ts` (L-022: sacados de la
 * lista, nunca escritos uno por uno), a 320 px y a 1280 px, con un
 * recorrido de teclado y axe con contraste real (D7). La verificación de
 * la tarea pide que la salida liste pantallas por escenarios SIN HUECOS:
 * `test.describe`/`test` quedan generados por los dos `for` de abajo, así
 * que el reporter de Playwright (`list`, `playwright.config.ts`) imprime
 * una línea por cada combinación real, sin que nadie las haya tipeado.
 *
 * Decisión declarada: "Mis edificios" (`/edificios`) NO toma el id de un
 * edificio — la API falsa sirve siempre `lista.json` sin mirar la URL
 * (`api-falsa.ts`, ruta `""` del propio `/api/complejos`, sin id en el
 * camino) — así que el concepto de "escenario por id" no se le puede
 * aplicar: se cubre aparte, una vez por ancho, más abajo. Las otras seis
 * pantallas SÍ toman el id del edificio en la URL y entran al cruce
 * completo con los diez escenarios (60 combinaciones), más las 2 de "Mis
 * edificios": 62 pruebas en total, listadas explícitamente al correr
 * `test-web-navegador.sh --list` o en la salida de la corrida.
 */

import { sinViolacionesEnElNavegador } from "./accesibilidad";
import {
  anchoExcedeLaVentana,
  contornoDelElementoEnfocado,
  elFocoVolvioAlCuerpo,
} from "./comprobaciones";
import { ESCENARIOS } from "./escenarios";
import { expect, test } from "./prueba";

type Pantalla = {
  clave: string;
  nombre: string;
  ruta: (id: string) => string;
};

const _PANTALLAS_POR_EDIFICIO: Pantalla[] = [
  { clave: "resumen", nombre: "Resumen del edificio", ruta: (id) => `/edificios/${id}` },
  { clave: "unidades", nombre: "Padrón de unidades", ruta: (id) => `/edificios/${id}/unidades` },
  { clave: "grupos", nombre: "Grupos de reparto", ruta: (id) => `/edificios/${id}/grupos` },
  {
    clave: "categorias",
    nombre: "Categorías de gasto",
    ruta: (id) => `/edificios/${id}/categorias`,
  },
  {
    clave: "configuracion",
    nombre: "Intereses y vencimiento",
    ruta: (id) => `/edificios/${id}/configuracion`,
  },
  {
    clave: "saldos-previos",
    nombre: 'Confirmar "sin saldos previos"',
    ruta: (id) => `/edificios/${id}/saldos-previos`,
  },
];

const _ANCHOS = [320, 1280] as const;

/** Recorrido de teclado (tarea 5.1): varios `Tab` seguidos, con el foco
 * SIEMPRE visible en cada parada real — no sólo en la primera. Una
 * pantalla con menos de tres controles enfocables (p.ej. "sin permiso"/
 * "sin sesión", D8) agota el recorrido antes: eso no es "foco invisible",
 * así que el recorrido se corta ahí sin fallar. */
async function recorridoDeTecladoConFocoVisible(
  page: import("@playwright/test").Page,
): Promise<void> {
  for (let paso = 0; paso < 3; paso += 1) {
    await page.keyboard.press("Tab");
    if (await elFocoVolvioAlCuerpo(page)) {
      return;
    }
    const contorno = await contornoDelElementoEnfocado(page);
    expect(contorno, `paso ${paso + 1} del recorrido de teclado sin foco visible`).not.toBe("none");
  }
}

for (const pantalla of _PANTALLAS_POR_EDIFICIO) {
  test.describe(`5.1 ${pantalla.nombre}`, () => {
    for (const escenario of ESCENARIOS) {
      for (const ancho of _ANCHOS) {
        test(`${escenario.clave} (${escenario.descripcion}) a ${ancho}px`, async ({ page }) => {
          await page.setViewportSize({ width: ancho, height: 900 });
          const respuesta = await page.goto(pantalla.ruta(escenario.id));
          expect(respuesta?.status() ?? 0, "no puede ser un 5xx").toBeLessThan(500);
          await page.waitForLoadState("networkidle");

          expect(
            await anchoExcedeLaVentana(page),
            `${pantalla.nombre} / ${escenario.clave} desborda la página a ${ancho}px`,
          ).toBe(false);

          await recorridoDeTecladoConFocoVisible(page);
          await sinViolacionesEnElNavegador(page);
        });
      }
    }
  });
}

test.describe("5.1 Mis edificios", () => {
  for (const ancho of _ANCHOS) {
    test(`lista de edificios a ${ancho}px`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: 900 });
      const respuesta = await page.goto("/edificios");
      expect(respuesta?.status() ?? 0, "no puede ser un 5xx").toBeLessThan(500);
      await page.waitForLoadState("networkidle");

      expect(
        await anchoExcedeLaVentana(page),
        `Mis edificios desborda la página a ${ancho}px`,
      ).toBe(false);

      await recorridoDeTecladoConFocoVisible(page);
      await sinViolacionesEnElNavegador(page);
    });
  }
});
