# Revisor del plan · propose · intento 3 · ejemplo-robusto (C-27)

- **Rol**: disposición de los hallazgos del rompedor, corrección del plan y su revisión, hechas por el orquestador, como permite LOW. No hubo subagente.
- **Independencia**: ninguna. El autor del plan corrige sus propios huecos. El rompedor de verify 2 y el auditor lo miran después.
- **Executor declarado**: Claude Opus 5.5, sesión principal de Giuliano. Familia: Claude.
- **Fecha**: 31/10/2026.
- **Revisión**: base `9649471` más el árbol sin commit, `git diff | sha256sum` en `22bb0402eb35deb1fd38d49c209ddfe77d1a8d5b1522fce7ef9af0e199373d41`, y `test_puntos_de_entrada_prohibidos.py` en `af17cd1f...`.
- **Veredicto**: **APTO PARA CONSTRUIR LA CORRECCIÓN**. Se agrega el grupo 9 de `tasks.md` y se desmarca 8.2. LOW se sostiene: nada toca `acceso`, la matriz de permisos ni `cuenta_corriente`.

## Fuentes leídas

- `informes/verify-1-breaker.md` completo.
- `specs/datos-semilla/spec.md`, `design.md` y `proposal.md`.
- `complejos/aplicacion/ejemplo.py:80-99` y `:495-639`, `complejos/aplicacion/errores.py`, `compartido/cargador_yaml.py:55-125`, `compartido/parametros.py:285-303` y `compartido/semilla.py:144-190`.
- `openspec/specs/datos-semilla/spec.md`: el requisito vigente del lector.
- **Sin leer**: los informes de `.git/informes-*` e `infra/.env`.

## Contaminación por otros informes

Este informe parte del rompedor, así que hereda lo que eligió mirar. F1, F2, F3 y O4 se contrastaron por lectura contra el código. **No volví a ejecutar sus reproducciones**: lo harán los RED del constructor.

## EVIDENCIA

| Comprobación | Comando o lectura | Resultado |
|---|---|---|
| El árbol sigue como lo dejó el rompedor | `git diff \| sha256sum` y `sha256sum` del test sin trackear | `22bb0402...` y `af17cd1f...`, iguales a su informe |
| F1, de dónde sale la ruta | `cargador_yaml.py`, `leer_archivo`; `semilla.py:241-244`; `parametros.py:293-296` | El lector de archivos es el único que la pone, en `no se puede leer el archivo: {ruta}`, y los dos llamadores reenvían ese texto entero. Por eso alcanza una comparación exacta. **Por lectura** |
| F1, la línea en cuestión | `ejemplo.py:560-565` | `str.replace` corre sobre todo el mensaje, como dice el informe |
| F2, si el campo es seguro | `errores.py:23-41` | `motivo` "nunca llega al cliente", y `error_de_validacion` arma `campo` sólo con nombres |
| F2, si algún test fija el `NotImplementedError` | `grep "NotImplementedError\|confirmada"` en `test_ejemplo_casos_de_uso.py` | Sin coincidencias |
| F3, el comentario | `ejemplo.py:91-93` y `_main`, `:623-630` | `except Exception` no captura `KeyboardInterrupt`, así que el comentario es falso |
| F4, el requisito que choca | `openspec/specs/datos-semilla/spec.md:68-70` | Pide rechazar "nombrando el campo y la unidad" |
| O4 | `ejemplo.py:552` | `args.semilla or ...`: el vacío cae en la semilla por defecto |

No se corrió ningún test en esta revisión: las correcciones todavía no existen.

## Disposición de los hallazgos

| # | Hallazgo | Disposición |
|---|---|---|
| F1 | El `replace` deforma el mensaje | **Constructor, TDD** (9.1). La causa es de mi D4 corregido: dije "la reemplaza en el mensaje" sin acotar dónde |
| F2 | Semilla que el caso de uso rechaza termina en 9 | **Constructor, TDD** (9.2) y D10. El escenario nuevo declara que ahí ya se conectó |
| F3 | Ctrl-C deja traceback | **Plan decide: 130**, y constructor por TDD (9.3) |
| F4 | El spec y D4 prometen no repetir valores en la semilla | **Plan corregido**: se exceptúan el identificador de una unidad y la clave de un grupo, porque el requisito vigente los pide. El test rojo del rompedor para F4 se descarta, porque contradice ese requisito |
| F5 a F9 | Mutantes sobrevivientes | **Constructor, TDD** (9.4). Sólo tests |
| O1 | Argumentos antes de la guarda | **Se queda como está, y se escribe**: un error de uso o `--help` no corren el comando y no se conectan. Cambian D4, el spec y el docstring (9.5). **Lo mira el auditor**, porque D-112 dice "lo dice" y esto lo interpreta sin editarla |
| O2 | La comparación no mira `pisos`, `subsuelos`, ubicación ni `activo` | **Deuda propuesta** para el próximo change que toque `ejemplo.py`. Está en "Fuera de este cambio" de `proposal.md`. No es defecto del spec |
| O3 | `lock_timeout` da 5 con "no se pudo conectar" | **Se acepta, y se escribe** en D4: sólo se llega con esos ajustes en la base, y una base lenta ya está fuera del change |
| O4 | `--semilla=` vacío usa la semilla por defecto | **Constructor, TDD** (9.3). Es un cambio de dos líneas, y el resultado actual es cargar otra semilla sin avisar |
| O5 | La guarda de QA-5 no ve variantes | **Se queda como está**: `proposal.md` acota a los dos archivos. Sólo se corrige el docstring (9.5) |
| S1 | El límite de conexión parece ser por dirección | **Queda visible, sin reproducir**. Falta medir la causa, y el escenario "La base no responde" no distingue una dirección de dos |
| S2 | `print` con la salida cerrada da 9 después del commit | **Queda visible, sin reproducir**. Falta correrlo en Linux |
| S3 | `--semilla` con un archivo especial | **Queda visible, sin reproducir**. `cargador_yaml.py` está fuera del change |
| S4 | Parámetros que existen y no se dejan leer | **Queda visible, sin reproducir**. Falta correrlo en Linux, sin root |

## Hallazgos de esta revisión

| # | Hallazgo | Disposición |
|---|---|---|
| PR3-1 | 8.2 seguía marcada, con evidencia anterior a las correcciones | **Desmarcada**: se repite sobre la revisión de apply 3 |
| PR3-2 | El grupo 9 lleva el total a 26 tareas | **Se acepta**: son correcciones de una vuelta, y juntarlas con los grupos originales perdería de dónde salió cada una |
| PR3-3 | La suite completa sigue sin resultado | **Sigue abierto**: se corre después de verify 2, si Giuliano la pide. Sin ella el auditor no se despacha |

## JUICIO

- **Autor**: orquestador. **Comparación**: los hallazgos del rompedor contra el plan, el código y el spec vigente.
- **Confianza alta**: F1, F2 y F3 son defectos que el texto del plan ya prohibía, y F4 es un error del plan.
- **Confianza alta**: `EntradaInvalida` no expone datos si sólo sale `campo`.
- **Confianza media**: que no quede otra excepción de un caso de uso que debería tener código propio. `Conflicto` queda en el 9, sin reproducir.
- **Confianza media**: O1. Me parece la lectura razonable de D-112, pero es una interpretación mía, no una decisión de quienes la firmaron.

## SUPOSICIÓN

- Que comparar el mensaje entero alcance para F1: si alguien cambia el texto de `leer_archivo`, la ruta volvería a salir. Lo frena el test que usa el id como ruta, que sigue exigiendo que no aparezca.
- Que `campo` nombre algo útil en los tres casos de 9.2: lo comprueba el RED.
