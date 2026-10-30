#!/usr/bin/env bash
# Pasos con nombre para humo.sh (D6, tarea 2.1): cada paso se anuncia con
# `paso N "descripción"` y, si algo dentro de él falla, un único
# `trap ... ERR` (con `set -E`, para que el trap también salte dentro de
# funciones) imprime el número del paso, su descripción, la línea y el
# comando que falló. Así se cubren los 35 `[ ]` y los 11 `grep -q` sueltos
# de humo.sh sin reescribir cada uno a `if !`.
#
# L-014: `trap ... ERR` NO salta dentro de una condición (`if cmd; then`),
# ni a la izquierda de `&&`/`||`: los `if !` que humo.sh ya tiene (con su
# propio `echo "ERROR: ..." >&2; exit 1`) se quedan como están, fuera de
# este mecanismo. `reportar_fallo_paso` (abajo) es el mismo formateador que
# usa el trap, expuesto para quien necesite nombrar un paso a mano desde un
# `if`; no se usa hoy en humo.sh, pero prueba que el mecanismo no depende de
# la detección automática para dar el mismo formato (test de 2.1).
#
# Este archivo sólo declara funciones y arma el trap: no tiene que
# ejecutarse con Docker para probar su efecto (tests/infra/test_pasos_humo.py).

set -E

_PASO_NUMERO=""
_PASO_DESCRIPCION=""

paso() {
  _PASO_NUMERO="$1"
  _PASO_DESCRIPCION="$2"
  echo "--- ($_PASO_NUMERO) $_PASO_DESCRIPCION ---"
}

# `$3` (opcional): las líneas de BASH_LINENO tal como las ve el trap (separadas por espacios). Si la
# falla ocurrió dentro de una función (`compose()`, un helper), la última línea distinta de cero es la
# del llamado en el script principal, y se informa además de la línea de adentro (2e, C2V2-8).
reportar_fallo_paso() {
  local linea="$1"
  local comando="$2"
  local lineas_de_llamada="${3:-}"
  local llamado="" candidata
  for candidata in $lineas_de_llamada; do
    if [ "$candidata" != "0" ]; then
      llamado="$candidata"
    fi
  done
  local desde=""
  if [ -n "$llamado" ]; then
    desde=" (llamado desde la línea ${llamado})"
  fi
  echo "ERROR: paso ${_PASO_NUMERO:-?} (${_PASO_DESCRIPCION:-sin descripción}) falló en la línea ${linea}: ${comando}${desde}" >&2
}

# 2e, C2-5: el camino de falla explícito (`exit 1` tras un `echo "ERROR: ..."`) que `trap ERR` no ve
# (L-014). `$1` es la condición que no se cumplió, tal como está escrita en el script. La línea es
# la de quien llama a `fallar_paso`, no la de esta función.
fallar_paso() {
  reportar_fallo_paso "${BASH_LINENO[0]}" "$1"
  exit 1
}

trap 'reportar_fallo_paso "$LINENO" "$BASH_COMMAND" "${BASH_LINENO[*]}"' ERR
