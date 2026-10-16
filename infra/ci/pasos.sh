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

reportar_fallo_paso() {
  local linea="$1"
  local comando="$2"
  echo "ERROR: paso ${_PASO_NUMERO:-?} (${_PASO_DESCRIPCION:-sin descripción}) falló en la línea ${linea}: ${comando}" >&2
}

trap 'reportar_fallo_paso "$LINENO" "$BASH_COMMAND"' ERR
