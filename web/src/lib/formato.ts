/**
 * Formato argentino sobre texto decimal, y nada más (D6, tarea 3.2).
 *
 * Todo el módulo trabaja sobre TEXTO (nunca `Number`, `parseFloat` ni
 * `Intl.NumberFormat`: el punto flotante binario pierde valores que el
 * texto decimal de la API no pierde — `web/src/lib/test/
 * sinNumeroSobrePlata.test.ts` lo exige de todo archivo que importe este
 * módulo o el cliente de la API). Validación con una expresión anclada
 * (`^...$`, clases `[0-9]` explícitas, nunca `\d` ni una bandera `i`/`u`
 * que pudiera volverlas sensibles a Unicode) antes de tocar nada, misma
 * familia que `seguimiento.ts` (L-008).
 */

const _TEXTO_SIN_SIGNO = /^[0-9]+\.[0-9]+$/;
const _COEFICIENTE_SIN_SIGNO = /^[0-9]+\.[0-9]{6}$/;
const _COEFICIENTE_CON_SIGNO = /^-?[0-9]+\.[0-9]{6}$/;

/** Punto de miles sobre la parte entera, por manipulación de texto (nunca
 * `Intl.NumberFormat`): inserta un "." cada tres dígitos desde la derecha. */
function conPuntoDeMiles(parteEntera: string): string {
  let resultado = "";
  for (let indice = 0; indice < parteEntera.length; indice += 1) {
    const posicionDesdeElFinal = parteEntera.length - indice;
    if (indice > 0 && posicionDesdeElFinal % 3 === 0) {
      resultado += ".";
    }
    resultado += parteEntera[indice];
  }
  return resultado;
}

/** Quita ceros a la izquierda, pero nunca deja la parte entera vacía. */
function sinCerosALaIzquierda(texto: string): string {
  return texto.replace(/^0+(?=[0-9])/, "");
}

function conDecimales(texto: string, decimales: number): string {
  if (!_TEXTO_SIN_SIGNO.test(texto)) {
    throw new Error(`formato decimal inválido: se esperaba texto ASCII sin signo, no ${texto}`);
  }
  const separador = texto.indexOf(".");
  const parteEntera = texto.slice(0, separador);
  const parteDecimal = texto.slice(separador + 1);
  if (parteDecimal.length !== decimales) {
    throw new Error(`se esperaban ${decimales} decimales, no ${parteDecimal.length}: ${texto}`);
  }
  return `${conPuntoDeMiles(parteEntera)},${parteDecimal}`;
}

/** Coeficiente de R01: 6 decimales, como en el reglamento. `"0.083333"` →
 * `"0,083333"`. */
export function coeficiente(texto: string): string {
  return conDecimales(texto, 6);
}

/** Superficie en m², con punto de miles: `"1234.50"` → `"1.234,50"`. */
export function superficie(texto: string): string {
  return conDecimales(texto, 2);
}

/** Tasa mensual, sin el signo "%" (el texto de la pantalla lo agrega donde
 * corresponda): `"3.00"` → `"3,00"`. */
export function tasa(texto: string): string {
  return conDecimales(texto, 2);
}

/** Un porcentaje con dos decimales y su "%": `"2.00"` → `"2,00 %"`. */
export function porcentaje(texto: string): string {
  return `${conDecimales(texto, 2)} %`;
}

/** La suma de coeficientes (R01) como porcentaje con 4 decimales: mueve la
 * coma dos lugares sobre el TEXTO de 6 decimales, nunca multiplicando por
 * 100 (The Tabular Money Rule: 0,01 % de tolerancia se perdería a 2
 * decimales). `"0.999950"` → `"99,9950 %"`. */
export function sumaComoPorcentaje(texto: string): string {
  if (!_COEFICIENTE_SIN_SIGNO.test(texto)) {
    throw new Error(`formato de coeficiente inválido: se esperaban 6 decimales, no ${texto}`);
  }
  const separador = texto.indexOf(".");
  const parteEntera = texto.slice(0, separador);
  const parteDecimal = texto.slice(separador + 1);
  const nuevaEntera = sinCerosALaIzquierda(parteEntera + parteDecimal.slice(0, 2)) || "0";
  const nuevaDecimal = parteDecimal.slice(2);
  return `${conPuntoDeMiles(nuevaEntera)},${nuevaDecimal} %`;
}

/** La diferencia de R01 como "falta"/"sobra" según su signo, leído del
 * texto (el primer carácter), nunca comparando números: `"-0.000200"` →
 * `"falta 0,0200 %"`; `"0.000100"` → `"sobra 0,0100 %"`. */
export function diferenciaComoPorcentaje(texto: string): string {
  if (!_COEFICIENTE_CON_SIGNO.test(texto)) {
    throw new Error(`formato de diferencia inválido: se esperaban 6 decimales, no ${texto}`);
  }
  const esFalta = texto.startsWith("-");
  const magnitud = esFalta ? texto.slice(1) : texto;
  return `${esFalta ? "falta" : "sobra"} ${sumaComoPorcentaje(magnitud)}`;
}
