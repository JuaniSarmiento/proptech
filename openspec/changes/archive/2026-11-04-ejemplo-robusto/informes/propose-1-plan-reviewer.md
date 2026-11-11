# Revisor del plan · propose · intento 1 · ejemplo-robusto (C-27)

- **Rol**: revisión del plan hecha por el orquestador, junto con la planificación, como permite LOW. No hubo subagente.
- **Independencia**: ninguna. El autor del plan se revisa a sí mismo, y los hallazgos de abajo hay que leerlos con ese límite. El rompedor y el auditor son los primeros ojos independientes.
- **Executor declarado**: Claude Opus 5.5, sesión principal de Giuliano. Familia: Claude.
- **Fecha**: 30/10/2026, 17:53 (-03:00).
- **Revisión**: `9649471` más `openspec/changes/ejemplo-robusto/` sin commit.
- **Veredicto**: **APTO PARA CONSTRUIR**, con un defecto corregido y dos riesgos declarados. Sólo se puede construir con `uv` instalado (tarea 0.1).

## Fuentes leídas

- La guía del equipo en PDF (sección 13), `CHANGES.md` (C-27) y la ficha 3f con su tabla de deuda en `knowledge-base/12_fichas_de_changes.md`.
- `knowledge-base/15_lecciones.md` completo. D-112 y D-133 completas; de D-110, sólo la nota de portabilidad; de D-138, sólo la línea del reparto.
- `backend/src/proptech_core/complejos/aplicacion/ejemplo.py` completo; `backend/tests/integracion/test_ejemplo_casos_de_uso.py` completo.
- `compartido/configuracion.py:186-301` y `:374-443`; `acceso/aplicacion/alta_inicial.py`; `vinculacion_de_desarrollo.py`; `usuarios.py:229-302`.
- `openspec/specs/datos-semilla/spec.md:96-182`, `openspec/specs/acceso-de-desarrollo/spec.md` y las líneas de "ejemplo" de `fronteras-de-modulos/spec.md`.
- `backend/tests/unitarios/test_fronteras_de_modulos.py:326-346` y las líneas de `_sql_ajeno` y del ejemplo.
- **Sin leer**: los informes del PR #1 en `.git/informes-*`, que están en la máquina de Juani.

## Contaminación por otros informes

Ninguna: es el primer informe del change.

## EVIDENCIA

| Comprobación | Comando | Resultado |
|---|---|---|
| El plan es válido | `openspec validate ejemplo-robusto --strict` | `Change 'ejemplo-robusto' is valid` |
| Cantidad de tareas | `rg -c "^- \[ \]" tasks.md`; `openspec instructions apply` | Eran 26; quedaron 21, `state: ready` |
| Sin guiones largos ni secretos | `rg` sobre el change | Sin coincidencias |
| Tests que fijan el código 1 | `rg "returncode == 1\|resultado == 1\|else 1\)"` | `:495`, `:554`, `:642`, `:654`, `:1020`. La guarda (`:495`, `:654`) sigue en 1; se ajustan las otras tres |
| Nadie más consume el comando | `rg "ejemplo" infra/ci/*.sh .github/workflows/ci.yml` | Sólo `humo.sh:831`, que corre otro comando (`compartido.semilla`), cuyo código 1 no cambia |
| `clerk_emisor=` | `rg "clerk_emisor=" backend/src backend/tests` | Sólo `ejemplo.py:460` y la definición |
| Sin columna de fecha en `complejo` | `migraciones/versions/0003_acceso_minimo.py` y `rg add_column`/`ADD COLUMN` | Sin `creado_en`; el nombre no es único |
| Un segundo edificio es posible | `proptech_api/complejos.py:285`, `permisos.py:139` | `POST /complejos` con `CREAR_EDIFICIO` para `super_admin`. **Por lectura, sin ejecutar** |
| SQL sobre `persona` queda prohibido | `test_fronteras_de_modulos.py:738-745` y los casos con `SELECT` | La regla atrapa también lecturas |
| `listar_personal` alcanza | `usuarios.py:245-302` | Devuelve `persona_id`, `nombre`, `email` y `asignaciones`, sin filtrar por rol con el parámetro por defecto |
| El import está permitido | `_entre_modulos`, `test_fronteras_de_modulos.py:337` | `destino[2] == "aplicacion"` es público. **Por lectura, sin ejecutar** |
| Entorno | `command -v uv`; `wsl -l -q` | Sin `uv`; WSL sólo con `docker-desktop` |

No se corrió ningún test: `uv` no está instalado, así que nada de esto prueba comportamiento en ejecución.

## Hallazgos

| # | Hallazgo | Disposición |
|---|---|---|
| PR-1 | 26 tareas contra la regla de `config.yaml` de partir un cambio de más de unas veinte | **Corregido**: 21 tareas, juntando las que comparten RED |
| PR-2 | La ficha dice que nada crea un segundo edificio, y la API lo permite | **Incorporado** al spec y a D2; corrige la ficha al cerrar |
| PR-3 | La ficha cita `ejemplo.py:463-466` como fuera de `try`, y esas líneas están dentro; los que quedan afuera son `:460`, `:461`, `:471` y `:473-477`, más el `RuntimeError` de `:388` | **Incorporado** a D4 y a 5.1 a 5.4 |
| PR-4 | M8 con el caso "falta" no muere en la aserción, sino por `KeyError` | **Incorporado**: 1.3 pide también "sobra" |
| PR-5 | "Tipo y piso" son dos mutantes, y uno solo podría sobrevivir | **Incorporado**: 1.2 lleva un caso por condición |
| PR-6 | Otras cuatro ramas de la comparación tampoco tienen test | **Incorporado** como 1.4. Es una adición a la ficha: no cambia producción y sirve al objetivo declarado |
| PR-7 | D-112 fija el código 1 para la guarda, y la ficha se queja de que "todo" sale con 1 | **Resuelto**: la guarda conserva el 1 y el resto cambia, sin reemplazar la decisión |
| PR-8 | Con el código de configuración nuevo, el orden guarda-configuración pasa a ser observable (RV-1 de D-112) | **Incorporado** en 5.2 |
| PR-9 | `alta_inicial.py` tiene el mismo defecto (L-009) y está en `acceso` | **Fuera de alcance**: deuda propuesta para el cierre |

## Cobertura del "Terminado cuando" de la ficha

| Criterio | Tareas |
|---|---|
| M5 a M8 mueren con una aserción cada uno | 1.1 a 1.3 |
| El test de concurrencia fuerza la carrera; `RuntimeError` con test | 2.1, 2.2 |
| Consulta determinística; la comparación mira la persona | 3.1 a 3.3 |
| Cada error con su mensaje y su código | 5.1 a 5.4 |
| Corre sin Redis | 4.1 a 4.3 |
| La guarda da rojo si aparece alguno de los dos | 6.1 |

## JUICIO

- **Autor**: orquestador. **Comparación**: plan contra ficha, specs, código y lecciones.
- **Confianza alta**: el alcance cubre la ficha, y no hace falta tocar `acceso`, la matriz ni `cuenta_corriente`, así que LOW se sostiene.
- **Confianza media**: que `listar_personal` no traiga sorpresas en este camino (lo usa la API, pero nunca desde este comando) y que `model_copy` alcance en todos los casos del grupo 1.
- **Confianza media**: que los códigos elegidos sean los que quieren Juani o Emiliano. La ficha pide "propios" sin fijarlos; se documentan en el spec y en la decisión de cierre.

## SUPOSICIÓN

- Qué mutante es cada número de M5 a M8: se deduce del orden de la ficha porque los informes del PR #1 no viajan con el clone. No cambia el trabajo.
- Que el `UPDATE` mueva la fila en el orden físico que necesita el RED de 3.1: sin ejecutar. El design indica qué hacer si no se logra.
- Que el host de 5.3 no responda igual en cada entorno: se verá al correrlo. Si la red rechaza al instante, sigue siendo código 5, pero deja de probar el límite de tiempo y hay que declararlo.
