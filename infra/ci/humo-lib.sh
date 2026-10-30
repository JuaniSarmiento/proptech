#!/usr/bin/env bash
# shellcheck shell=bash
# shellcheck disable=SC2016  # `fallar_paso` recibe la condición como TEXTO (2e): las comillas simples son a propósito.
# Funciones del humo que se prueban sin Docker (backend/tests/infra/test_humo_lib.py). Las fuentea
# `humo.sh` después de `pasos.sh` (necesitan `fallar_paso`); los tests las fuentean con un
# `contar_dumps` y un arreglo `CAPBND_ESPERADO` propios.

#: C2-1 (rompedor/auditor, vuelta 1 del 2c): no alcanza con que la cabecera
#: exista, hace falta su VALOR — una Referrer-Policy: unsafe-url pasaba
#: todo. Juani confirmó `no-referrer` (como la spec y D1), no
#: `strict-origin-when-cross-origin`.
#: N-a (2e): cada cabecera de seguridad aparece UNA sola vez (un duplicado podía esconder un valor
#: distinto detrás del primero) y las directivas de Permissions-Policy se buscan como palabra
#: entera (`xcamera=()` no niega `camera=()`).
verificar_cabeceras() {
  local descripcion="$1" encabezados="$2" cabecera valor_obtenido repeticiones
  local encabezados_sin_cr
  encabezados_sin_cr=$(echo "$encabezados" | tr -d '\r')

  for cabecera in X-Content-Type-Options Referrer-Policy X-Frame-Options Permissions-Policy; do
    repeticiones=$(echo "$encabezados_sin_cr" | grep -ci "^${cabecera}:" || true)
    if [ "$repeticiones" = "0" ]; then
      echo "ERROR: falta $cabecera en $descripcion" >&2
      echo "$encabezados"
      fallar_paso 'grep -ci "^${cabecera}:" = 0'
    fi
    if [ "$repeticiones" != "1" ]; then
      echo "ERROR: $cabecera aparece $repeticiones veces en $descripcion (tiene que aparecer una sola vez)" >&2
      echo "$encabezados"
      fallar_paso 'grep -ci "^${cabecera}:" = 1'
    fi
  done

  for cabecera in Server Via X-Powered-By; do
    if echo "$encabezados_sin_cr" | grep -qi "^${cabecera}:"; then
      echo "ERROR: $cabecera presente en $descripcion (tiene que estar ausente)" >&2
      echo "$encabezados"
      fallar_paso '! echo "$encabezados_sin_cr" | grep -qi "^${cabecera}:"'
    fi
  done

  for cabecera in X-Content-Type-Options:nosniff Referrer-Policy:no-referrer X-Frame-Options:DENY; do
    valor_obtenido=$(echo "$encabezados_sin_cr" | grep -i "^${cabecera%%:*}:" | head -n1 \
      | sed "s/^[^:]*:[[:space:]]*//")
    if [ "$valor_obtenido" != "${cabecera#*:}" ]; then
      echo "ERROR: ${cabecera%%:*} en $descripcion tiene el valor '$valor_obtenido'," \
        "se esperaba '${cabecera#*:}'" >&2
      echo "$encabezados"
      fallar_paso '[ "$valor_obtenido" = "${cabecera#*:}" ]'
    fi
  done

  local permissions_policy directiva
  permissions_policy=$(echo "$encabezados_sin_cr" | grep -i "^Permissions-Policy:" | head -n1)
  for directiva in camera microphone geolocation; do
    if ! echo "$permissions_policy" | grep -qiE "(^|[:,[:space:]])${directiva}=\(\)([,[:space:]]|$)"; then
      echo "ERROR: Permissions-Policy en $descripcion no niega $directiva ($permissions_policy)" >&2
      fallar_paso 'echo "$permissions_policy" | grep -qiE "(^|[:,[:space:]])${directiva}=\(\)([,[:space:]]|$)"'
    fi
  done
}

#: Sólo las cuatro cabeceras de seguridad, en minúsculas y ordenadas: lo
#: que varía entre un GET y su HEAD (Date, Content-Length, X-Request-ID
#: con otro UUID) queda afuera de la comparación a propósito.
cabeceras_de_seguridad_normalizadas() {
  echo "$1" | tr -d '\r' | tr '[:upper:]' '[:lower:]' \
    | grep -E '^(x-content-type-options|referrer-policy|x-frame-options|permissions-policy):' \
    | sort
}

# C2-7 (2e): el healthcheck de `respaldos` sólo pasa cuando ya hubo un primer ciclo de backup, pero el
# volcado puede tardar en aparecer en la carpeta: se espera, con un plazo acotado (`$2`, segundos), a
# que haya `$1` archivos y recién ahí se exige el número exacto. Más de los esperados falla enseguida.
# Necesita una función `contar_dumps` (la define quien fuentea este archivo).
esperar_dumps() {
  local esperado="$1" plazo="${2:-15}" intentos=0 actual
  actual=$(contar_dumps)
  while [ "$actual" -lt "$esperado" ] && [ "$intentos" -lt $((plazo * 2)) ]; do
    sleep 0.5
    intentos=$((intentos + 1))
    actual=$(contar_dumps)
  done
  if [ "$actual" != "$esperado" ]; then
    echo "ERROR: se esperaban $esperado .dump y hay $actual (plazo: ${plazo}s)" >&2
    fallar_paso '[ "$(contar_dumps)" = "$esperado" ]'
  fi
}

# C2V2-7 (2e): la lista de servicios sale de `compose config --services`; cada uno tiene que tener su
# CapBnd esperado en el arreglo CAPBND_ESPERADO (y al revés: una entrada de un servicio que ya no
# existe también es un error). Un noveno servicio sin declarar da rojo en vez de pasar sin que nadie
# lo mire.
verificar_servicios_declarados() {
  local servicio
  for servicio in "$@"; do
    if [ -z "${CAPBND_ESPERADO[$servicio]+x}" ]; then
      echo "ERROR: el servicio '$servicio' de Compose no tiene su CapBnd esperado en CAPBND_ESPERADO (humo.sh)" >&2
      fallar_paso '[ -n "${CAPBND_ESPERADO[$servicio]+x}" ]'
    fi
  done
  for servicio in "${!CAPBND_ESPERADO[@]}"; do
    case " $* " in
      *" $servicio "*) ;;
      *)
        echo "ERROR: CAPBND_ESPERADO declara '$servicio', que ya no es un servicio de Compose" >&2
        fallar_paso 'case " $* " in *" $servicio "*)'
        ;;
    esac
  done
}

# C2V2-3 (2e): las políticas de RLS de una tabla se comparan por CONTENIDO (tabla, nombre, permisiva,
# roles, comando, USING y WITH CHECK), no por cantidad: una política renombrada o debilitada a
# `USING (true)` con la misma cantidad ya no pasa. `$2` y `$3` son las filas de `pg_policies`
# (una por política, campos separados por `|`) de la base en uso y de la restaurada.
verificar_politicas_iguales() {
  local tabla="$1" en_uso="$2" restaurada="$3" fila nombre otra
  if [ "$en_uso" = "$restaurada" ]; then
    return 0
  fi
  while IFS= read -r fila; do
    [ -n "$fila" ] || continue
    if ! grep -qxF -- "$fila" <<< "$restaurada"; then
      nombre=$(cut -d'|' -f2 <<< "$fila")
      otra=$(grep -F -- "|${nombre}|" <<< "$restaurada" || true)
      echo "ERROR: la política '$nombre' de la tabla $tabla difiere en la base restaurada" >&2
      echo "  en uso:     $fila" >&2
      echo "  restaurada: ${otra:-(no existe)}" >&2
      echo "  políticas de $tabla en la restaurada: $(cut -d'|' -f2 <<< "$restaurada" | tr '\n' ' ')" >&2
      fallar_paso 'grep -qxF -- "$fila" <<< "$restaurada"'
    fi
  done <<< "$en_uso"
  while IFS= read -r fila; do
    [ -n "$fila" ] || continue
    if ! grep -qxF -- "$fila" <<< "$en_uso"; then
      nombre=$(cut -d'|' -f2 <<< "$fila")
      echo "ERROR: la base restaurada tiene en la tabla $tabla una política que la base en uso no tiene: '$nombre'" >&2
      echo "  restaurada: $fila" >&2
      fallar_paso 'grep -qxF -- "$fila" <<< "$en_uso"'
    fi
  done <<< "$restaurada"
}

# L-047 (2e): los scripts que hacen `up --build` y `down -v` (el humo y el ensayo de roles) corren sólo
# en un proyecto de Compose propio, y se niegan ANTES de ejecutar ningún `compose`. Tres rechazos, cada
# uno con su causa y cómo correr el script:
#  (a) falta PROPTECH_COMPOSE_PROYECTO;
#  (b) vale `proptech` (el proyecto de uso real), SIEMPRE: haya o no contenedores corriendo, porque el
#      stack real detenido conserva sus volúmenes y `down -v` se los lleva (D15 del 2e; cambia lo
#      aprobado antes, que sólo lo rechazaba con contenedores corriendo);
#  (c) el puerto 80 o el 443 del host están ocupados: Caddy los publica fijos (infra/compose.yaml), así
#      que no pueden correr en paralelo con otro stack. PROPTECH_HUMO_PUERTOS (por defecto "80 443")
#      existe para que los tests prueben (c) con un puerto que ellos mismos ocupan.
# `$1` es la forma de correr el script (se imprime en el mensaje); el rechazo usa `exit 1` porque corre
# antes de cualquier `paso` y de cualquier `trap` de limpieza.
exigir_proyecto_de_compose_propio() {
  local como_correrlo="$1" puerto
  if [ -z "${PROPTECH_COMPOSE_PROYECTO:-}" ]; then
    echo "ERROR: falta PROPTECH_COMPOSE_PROYECTO: este script corre sólo en un proyecto de Compose propio." >&2
    echo "Corrélo así: $como_correrlo" >&2
    exit 1
  fi
  if [ "$PROPTECH_COMPOSE_PROYECTO" = "proptech" ]; then
    echo "ERROR: el proyecto 'proptech' es el del stack de uso real y este script haría 'down -v' sobre él, con o sin contenedores corriendo." >&2
    echo "Corré el script en otro proyecto: $como_correrlo" >&2
    exit 1
  fi
  for puerto in ${PROPTECH_HUMO_PUERTOS:-80 443}; do
    if (exec 3<>"/dev/tcp/127.0.0.1/$puerto") 2>/dev/null; then
      echo "ERROR: el puerto $puerto del host está ocupado: Caddy lo publica fijo y este script no puede correr en paralelo con otro stack." >&2
      echo "Bajá lo que lo usa y volvé a correr: $como_correrlo" >&2
      exit 1
    fi
  done
}
