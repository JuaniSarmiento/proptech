#!/usr/bin/env bash
# Servicio de respaldos de PostgreSQL (D9): genera un backup al arrancar y
# después cada RESPALDO_INTERVALO_SEGUNDOS, con retención, límite de tiempo
# por volcado y chequeo de salud (`--salud`). Testeable sin Docker con
# `--una-vez` y herramientas falsas en el PATH (ver tasks.md, convención).
set -euo pipefail
export LC_ALL=C
umask 077

CARPETA="${RESPALDO_CARPETA:-/respaldos}"
PREFIJO="proptech"

error_salir() {
  echo "error: $1" >&2
  exit 1
}

rechazar_si_root() {
  local uid
  uid="$(id -u)"
  if [ "$uid" = "0" ]; then
    error_salir "PROPTECH_UID: el servicio de respaldos no puede correr como root"
  fi
}

# Entero ASCII puro, sin ceros a la izquierda, sin signo, fullmatch (L-008).
validar_entero() {
  local nombre="$1" valor="$2" minimo="$3" maximo="$4"
  if [[ ! "$valor" =~ ^[1-9][0-9]{0,6}$ ]]; then
    error_salir "$nombre: falta, está vacío o no es un entero válido"
  fi
  if (( valor < minimo || valor > maximo )); then
    error_salir "$nombre: fuera de rango ($minimo..$maximo)"
  fi
}

validar_carpeta() {
  if [ ! -d "$CARPETA" ]; then
    error_salir "la carpeta de respaldos no existe: $CARPETA"
  fi
  if [ ! -w "$CARPETA" ]; then
    error_salir "la carpeta de respaldos no tiene permiso de escritura: $CARPETA"
  fi
}

validar_configuracion() {
  rechazar_si_root
  validar_entero RESPALDO_INTERVALO_SEGUNDOS "${RESPALDO_INTERVALO_SEGUNDOS:-}" 60 604800
  validar_entero RESPALDO_CONSERVAR "${RESPALDO_CONSERVAR:-}" 1 365
  validar_entero RESPALDO_LIMITE_SEGUNDOS "${RESPALDO_LIMITE_SEGUNDOS:-}" 5 86400
  if (( RESPALDO_LIMITE_SEGUNDOS >= RESPALDO_INTERVALO_SEGUNDOS )); then
    error_salir "RESPALDO_LIMITE_SEGUNDOS: tiene que ser menor que RESPALDO_INTERVALO_SEGUNDOS"
  fi
  validar_carpeta
}

# Línea JSON con los campos base (L-007: sólo valores propios, nunca la
# salida de una herramienta de terceros). Los pares clave=valor adicionales
# son siempre texto que el propio script generó (nombres de archivo con el
# patrón fijo, nombres de variable), nunca texto ajeno.
logear() {
  local nivel="$1" evento="$2" ts campos=""
  shift 2
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for par in "$@"; do
    campos+=",\"${par%%=*}\":\"${par#*=}\""
  done
  printf '{"ts":"%s","nivel":"%s","servicio":"respaldos","evento":"%s"%s}\n' \
    "$ts" "$nivel" "$evento" "$campos"
}

# Borra cualquier `.parcial` que haya sobrevivido a un corte anterior,
# siempre dentro del patrón de nombre propio (L-006).
borrar_parciales_huerfanos() {
  local archivo
  for archivo in "$CARPETA/${PREFIJO}-"*.dump.parcial; do
    [ -e "$archivo" ] || continue
    rm -f -- "$archivo"
  done
}

# Conserva los RESPALDO_CONSERVAR backups correctos más recientes. El archivo
# del ciclo en curso se excluye por nombre exacto antes de ordenar: si el
# reloj del host atrasa, puede ordenar como el más viejo por nombre y una
# retención ingenua lo borraría (M22). Sólo entran nombres que cumplen el
# patrón completo (L-006, L-008): un archivo ajeno o con otra extensión nunca
# se toca.
aplicar_retencion() {
  local archivo_actual="$1" nombre_actual listado total permitidos a_borrar
  local fallo=0
  nombre_actual="$(basename -- "$archivo_actual")"

  listado="$(
    for candidato in "$CARPETA/${PREFIJO}-"*.dump; do
      [ -e "$candidato" ] || continue
      local nombre_candidato
      nombre_candidato="$(basename -- "$candidato")"
      [[ "$nombre_candidato" =~ ^proptech-[0-9]{8}T[0-9]{6}Z\.dump$ ]] || continue
      [ "$nombre_candidato" = "$nombre_actual" ] && continue
      printf '%s\n' "$nombre_candidato"
    done | sort
  )"

  total=0
  if [ -n "$listado" ]; then
    total="$(printf '%s\n' "$listado" | wc -l)"
  fi

  permitidos=$(( RESPALDO_CONSERVAR - 1 ))
  if (( permitidos < 0 )); then
    permitidos=0
  fi
  a_borrar=$(( total - permitidos ))

  if (( a_borrar > 0 )); then
    # Proceso substitution (`< <(...)`), no un pipe: así la variable `fallo`
    # que fija el `while` vive en ESTE shell, no en un subshell que
    # desaparece al terminar el pipe (B2, L-014: `rm` fallando acá no debía
    # pasar desapercibido).
    while IFS= read -r nombre_a_borrar; do
      [ -n "$nombre_a_borrar" ] || continue
      if ! rm -f -- "$CARPETA/$nombre_a_borrar"; then
        fallo=1
      fi
    done < <(printf '%s\n' "$listado" | head -n "$a_borrar")
  fi
  return "$fallo"
}

ciclo_backup() {
  local marca archivo_final archivo_parcial
  marca="$(date -u +%Y%m%dT%H%M%SZ)"
  archivo_final="$CARPETA/${PREFIJO}-${marca}.dump"
  archivo_parcial="${archivo_final}.parcial"

  if ! PGCONNECT_TIMEOUT=5 timeout --kill-after=5 "$RESPALDO_LIMITE_SEGUNDOS" \
        pg_dump --format=custom "--file=${archivo_parcial}" >/dev/null 2>/dev/null; then
    rm -f -- "$archivo_parcial"
    logear error respaldo_fallido etapa=pg_dump
    return 1
  fi

  if ! pg_restore --list "$archivo_parcial" >/dev/null 2>/dev/null; then
    rm -f -- "$archivo_parcial"
    logear error respaldo_fallido etapa=pg_restore_list
    return 1
  fi

  # B2 (auditor, vuelta 2, F2/L-014): en modo continuo esta función se llama
  # como `ciclo_backup || true` (ver el `case` de más abajo), y en bash una
  # función a la izquierda de `||` corre con `set -e` DESACTIVADO en todo su
  # cuerpo. Los dos pasos de arriba ya se manejaban con `if !` explícito;
  # estos tres (antes confiaban en `set -e`) ahora también, y el evento de
  # éxito se loguea recién al final, cuando los tres ya pasaron: así ningún
  # paso que falla DESPUÉS de `pg_restore --list` puede dejar una línea
  # `respaldo_generado` sin que el backup esté de verdad completo.
  if ! mv -- "$archivo_parcial" "$archivo_final"; then
    rm -f -- "$archivo_parcial" "$archivo_final"
    logear error respaldo_fallido etapa=mv
    return 1
  fi

  if ! date +%s > "$CARPETA/.ultimo-ok"; then
    logear error respaldo_fallido etapa=marca_ultimo_ok
    return 1
  fi

  if ! aplicar_retencion "$archivo_final"; then
    logear error respaldo_fallido etapa=retencion
    return 1
  fi

  logear info respaldo_generado "archivo=$(basename -- "$archivo_final")"
  return 0
}

# `--salud`: no saludable sin `.ultimo-ok`, si su contenido no es un entero
# válido (misma batería de L-008 que el resto de la configuración) o si es
# más viejo que 1,5 intervalos.
verificar_salud() {
  local marca="$CARPETA/.ultimo-ok" contenido ahora limite antiguedad
  if [ ! -f "$marca" ]; then
    return 1
  fi
  contenido="$(cat "$marca")"
  if [[ ! "$contenido" =~ ^[0-9]{1,12}$ ]]; then
    return 1
  fi
  ahora="$(date +%s)"
  limite=$(( RESPALDO_INTERVALO_SEGUNDOS * 3 / 2 ))
  antiguedad=$(( ahora - contenido ))
  # B3 (auditor, vuelta 2, F3): una marca en el FUTURO (antigüedad negativa)
  # no es una marca válida del último backup, aunque pase el fullmatch de
  # arriba (hasta 12 dígitos). Sin este chequeo, una marca adelantada deja
  # la salud en OK para siempre, hasta que el reloj real la alcance.
  if (( antiguedad > limite || antiguedad < 0 )); then
    return 1
  fi
  return 0
}

modo="${1:-}"

if [ "$modo" = "--salud" ]; then
  validar_configuracion
  if verificar_salud; then
    exit 0
  else
    exit 1
  fi
fi

validar_configuracion
borrar_parciales_huerfanos

case "$modo" in
  --una-vez)
    ciclo_backup
    exit $?
    ;;
  *)
    # Modo continuo (D9): un ciclo al arrancar y después uno por intervalo,
    # para siempre. Una falla logueada nunca termina el proceso (L-001): el
    # próximo ciclo es la única reintentada.
    ciclo_backup || true
    while true; do
      sleep "$RESPALDO_INTERVALO_SEGUNDOS"
      ciclo_backup || true
    done
    ;;
esac
