# Evidencia 6.1: vocabulario vigente

EVIDENCIA del 20/10/2026. Barrido completo solicitado, sin leer `.env` ni `.env.*`.
No se alteran las migraciones históricas 0003/0017. Están fuera de los paths del
comando solicitado y su conversión usa el vocabulario anterior a propósito.

Comando en ambas corridas:

```sh
rg -n -i 'titular|colaborador|Nivel\.|\bnivel\b' backend/src backend/migraciones/ayudas_rls.py backend/tests infra -g '!.env' -g '!.env.*'
```

## Antes

174 coincidencias.

```text
infra/respaldos/respaldar.sh:62:  local nivel="$1" evento="$2" ts campos=""
infra/respaldos/respaldar.sh:68:  printf '{"ts":"%s","nivel":"%s","servicio":"respaldos","evento":"%s"%s}\n' \
infra/respaldos/respaldar.sh:69:    "$ts" "$nivel" "$evento" "$campos"
backend/src/proptech_api/cuerpos.py:10:`strict=True` a nivel del modelo entero chocaría con cómo FastAPI valida el
infra/ci/ensayo-roles.sh:49:INSERT INTO asignacion_rol (administracion_id,persona_id,rol,complejo_id,unidad_id,nivel)
infra/ci/ensayo-roles.sh:51:        CASE p.nombre WHEN 'Perfil ficticio 1' THEN 'titular'
infra/ci/ensayo-roles.sh:52:                      WHEN 'Perfil ficticio 2' THEN 'colaborador'
infra/ci/ensayo-roles.sh:53:                      WHEN 'Perfil ficticio 3' THEN 'colaborador'
infra/ci/ensayo-roles.sh:102:esperados = ({"titular": 1, "colaborador": 2, "consejo": 1, "vecino": 1}
backend/tests/unitarios/test_rompedor_cargador_yaml_clave_no_string.py:73:    """Cierra la familia (L-009): el mismo defecto, un nivel más adentro."""
backend/tests/unitarios/test_logs_configuracion.py:23:    """Guarda y restaura los handlers y el nivel de los loggers que toca
backend/tests/unitarios/test_logs_configuracion.py:32:        for nombre, (handlers, nivel) in originales.items():
backend/tests/unitarios/test_logs_configuracion.py:35:            logger.setLevel(nivel)
infra/Caddyfile:37:	# (api/web) en cada `reverse_proxy`, así que un `header` al nivel del
backend/tests/unitarios/test_middleware_error_inesperado.py:59:    assert errores[0]["nivel"] == "error"
backend/tests/integracion/test_worker_caminos_de_falla.py:115:    assert agotados[0]["nivel"] == "error"
backend/tests/integracion/test_worker_caminos_de_falla.py:164:        # contenido crudo del trabajo rechazado) y el nivel es de error.
backend/tests/integracion/test_worker_caminos_de_falla.py:168:        assert any(linea.get("nivel") == "error" for linea in lineas), lineas
backend/tests/unitarios/acceso/test_permisos.py:126:def test_sin_complejo_solo_crear_edificio_para_titular(nombre: str, perfil: int) -> None:
backend/tests/unitarios/acceso/test_permisos.py:151:# --- alcanza: titular todo; colaborador/consejo su complejo; vecino su unidad ---
backend/tests/unitarios/acceso/test_permisos.py:154:def test_alcanza_titular_cualquier_complejo_y_unidad() -> None:
backend/tests/unitarios/acceso/test_permisos.py:162:def test_alcanza_colaborador_solo_el_complejo_asignado() -> None:
backend/tests/unitarios/acceso/test_permisos.py:243:        ("titular", None, None, None),
backend/tests/unitarios/acceso/test_permisos.py:244:        ("colaborador", COMPLEJO, None, None),
backend/tests/integracion/test_422_clave_no_permitida.py:31:    api.como("titular")
backend/tests/integracion/test_422_clave_no_permitida.py:39:    api.como("titular")
backend/tests/integracion/test_422_clave_no_permitida.py:49:    api.como("titular")
backend/tests/infra/test_caddyfile_seguridad.py:149:    responde solo sin cuerpo): puestas dentro de un único `header` al nivel
backend/tests/integracion/test_asignar_edificio_api.py:6:Escenarios de `autorizacion-por-rol`: Colaborador asigna un edificio; Sin
backend/tests/integracion/test_asignar_edificio_api.py:7:permiso y fuera de alcance; Titular asigna un edificio; Asignar a una
backend/tests/integracion/test_asignar_edificio_api.py:140:        for nombre_rol in ("titular", "colaborador", "consejo", "vecino", "destinatario"):
backend/tests/integracion/test_asignar_edificio_api.py:152:            (str(admin_id), str(personas["titular"])),
backend/tests/integracion/test_asignar_edificio_api.py:158:            (str(admin_id), str(personas["colaborador"]), str(complejo_asignado)),
backend/tests/integracion/test_asignar_edificio_api.py:258:# --- El titular asigna un edificio: 201, y el colaborador pasa a verlo (5.2) ---
backend/tests/integracion/test_asignar_edificio_api.py:261:def test_titular_asigna_un_complejo_y_el_colaborador_pasa_a_verlo(
backend/tests/integracion/test_asignar_edificio_api.py:264:    _como(app_real, mundo["administracion_id"], mundo["personas"]["titular"])
backend/tests/integracion/test_asignar_edificio_api.py:282:# --- Colaborador "editar" en un complejo asignado: 403 con permiso_faltante ---
backend/tests/integracion/test_asignar_edificio_api.py:285:def test_colaborador_en_complejo_asignado_403_con_permiso_faltante(
backend/tests/integracion/test_asignar_edificio_api.py:288:    _como(app_real, mundo["administracion_id"], mundo["personas"]["colaborador"])
backend/tests/integracion/test_asignar_edificio_api.py:303:def test_mismo_colaborador_en_complejo_no_asignado_404(
backend/tests/integracion/test_asignar_edificio_api.py:306:    _como(app_real, mundo["administracion_id"], mundo["personas"]["colaborador"])
backend/tests/integracion/test_asignar_edificio_api.py:338:# --- El titular de A asignando a una persona de B: 404, nada escrito ---
backend/tests/integracion/test_asignar_edificio_api.py:341:def test_titular_asignando_a_persona_de_otra_administracion_404_y_nada_escrito(
backend/tests/integracion/test_asignar_edificio_api.py:346:    _como(app_real, mundo["administracion_id"], mundo["personas"]["titular"])
backend/tests/integracion/test_asignar_edificio_api.py:366:    api.como("titular")
backend/tests/integracion/test_asignar_edificio_api.py:380:            api.personas["titular"],
backend/tests/integracion/test_editar_metodo_de_grupo_propios.py:22:    api.como("titular")
backend/src/proptech_core/compartido/logs.py:25:#: Campos extra permitidos, además de los campos base (ts, nivel, servicio,
backend/src/proptech_core/compartido/logs.py:83:    Los campos base van en este orden: `ts`, `nivel`, `servicio`, `logger`,
backend/src/proptech_core/compartido/logs.py:96:            "nivel": record.levelname.lower(),
backend/tests/unitarios/test_logs.py:17:    nivel: int = logging.INFO,
backend/tests/unitarios/test_logs.py:25:        level=nivel,
backend/tests/unitarios/test_logs.py:68:    assert claves[:6] == ["ts", "nivel", "servicio", "logger", "evento", "request_id"]
backend/tests/unitarios/test_logs.py:84:    for nivel, esperado in niveles.items():
backend/tests/unitarios/test_logs.py:85:        datos = json.loads(_formatear(_record(nivel=nivel)))
backend/tests/unitarios/test_logs.py:86:        assert datos["nivel"] == esperado
backend/tests/integracion/test_migracion_normaliza_textos.py:23:    api.como("titular")
backend/src/proptech_core/compartido/cargador_yaml.py:25:    nivel de anidamiento."""
backend/src/proptech_core/compartido/cargador_yaml.py:41:            # cualquier nivel de anidamiento (este constructor arma todos los
backend/tests/integracion/test_catalogo_rls.py:44:#: D5/D6: hoy sólo `asignacion_rol` (el titular no tiene complejo).
backend/src/proptech_core/compartido/reintentos.py:80:    - Si es el último intento: loguea `tarea_agotada` con nivel `error` y
backend/src/proptech_core/compartido/reintentos.py:82:    - Cualquier otro error (no pasajero): loguea `tarea_fallida` con nivel
backend/tests/integracion/test_identidad_api.py:149:            # Titular (alcanza todo, D-096): esta tarea prueba el cableado de
backend/tests/integracion/test_edificios_api.py:17:@pytest.mark.parametrize("rol", ["titular", "editar", "ver", "consejo", "vecino"])
backend/tests/integracion/test_edificios_api.py:27:            if rol == "titular"
backend/tests/integracion/test_edificios_api.py:114:def test_solo_titular_crea_y_confirma_con_permiso_faltante(
backend/tests/integracion/test_asignacion_validacion.py:14:        for rol in ("super_admin", "vecino", "titular", "colaborador", "inventado")
backend/tests/integracion/test_asignacion_validacion.py:19:            ("nivel", "editar"),
backend/tests/integracion/test_asignacion_validacion.py:24:    + [({"rol": "consejo", "nivel": "ver"}, "nivel")],
backend/tests/integracion/test_asignacion_validacion.py:30:    api.como("titular")
backend/tests/integracion/test_asignacion_validacion.py:44:    api.como("titular")
backend/tests/integracion/test_autor_en_historial.py:23:def otro_titular(sesion: Session, identidad: Identidad, nombre: str) -> Identidad:
backend/tests/integracion/test_autor_en_historial.py:24:    """Un segundo titular de la MISMA administración que `identidad`."""
backend/tests/integracion/test_autor_en_historial.py:34:    nombre_titular_a = sesion_edificio.execute(
backend/tests/integracion/test_autor_en_historial.py:37:    titular_b = otro_titular(sesion_edificio, identidad_edificio, "Titular B")
backend/tests/integracion/test_autor_en_historial.py:39:    version(sesion_edificio, titular_b, edificio, date(2026, 11, 2), tasa_mensual="4.00")
backend/tests/integracion/test_autor_en_historial.py:44:    assert versiones[0]["autor_nombre"] == nombre_titular_a
backend/tests/integracion/test_autor_en_historial.py:45:    assert versiones[1]["autor_id"] == titular_b.persona_id
backend/tests/integracion/test_autor_en_historial.py:46:    assert versiones[1]["autor_nombre"] == "Titular B"
backend/tests/integracion/test_autor_en_historial.py:49:def test_edificio_recien_creado_trae_el_nombre_del_titular(
backend/tests/integracion/test_autor_en_historial.py:52:    nombre_titular = sesion_edificio.execute(
backend/tests/integracion/test_autor_en_historial.py:58:    assert versiones[0]["autor_nombre"] == nombre_titular
backend/tests/infra/test_respaldos.py:295:            assert set(linea) >= {"ts", "nivel", "servicio", "evento"}
backend/tests/infra/test_respaldos.py:370:        assert fallidas[0]["nivel"] == "error"
backend/tests/infra/test_respaldos.py:389:        assert fallidas[0]["nivel"] == "error"
backend/tests/integracion/test_alcance_api.py:7:Escenarios de `autorizacion-por-rol`: Colaborador en un edificio no
backend/tests/integracion/test_alcance_api.py:9:Titular. Lecciones: L-017 (el id de otra administración es un UUID válido y
backend/tests/integracion/test_alcance_api.py:261:        for nombre_rol in ("titular", "colaborador", "consejo", "vecino1", "vecino2"):
backend/tests/integracion/test_alcance_api.py:273:            (str(admin_id), str(personas["titular"])),
backend/tests/integracion/test_alcance_api.py:275:        # El colaborador sólo está asignado al complejo 1, nunca al 2.
backend/tests/integracion/test_alcance_api.py:279:            (str(admin_id), str(personas["colaborador"]), str(complejo_1)),
backend/tests/integracion/test_alcance_api.py:360:# --- Colaborador en un edificio no asignado: 404 ---
backend/tests/integracion/test_alcance_api.py:363:def test_colaborador_en_complejo_no_asignado_da_404(
backend/tests/integracion/test_alcance_api.py:366:    _como(app_real, mundo["administracion_id"], mundo["personas"]["colaborador"])
backend/tests/integracion/test_alcance_api.py:423:# --- El titular recibe 200 en todos los de su administración ---
backend/tests/integracion/test_alcance_api.py:426:def test_titular_200_en_todos_los_complejos_y_unidades_de_su_administracion(
backend/tests/integracion/test_alcance_api.py:429:    _como(app_real, mundo["administracion_id"], mundo["personas"]["titular"])
backend/tests/integracion/test_alcance_api.py:449:    _como(app_real, mundo["administracion_id"], mundo["personas"]["titular"])
backend/tests/integracion/test_auditoria_transaccion.py:186:            titular_id = uuid.uuid4()
backend/tests/integracion/test_auditoria_transaccion.py:187:            colaborador_id = uuid.uuid4()
backend/tests/integracion/test_auditoria_transaccion.py:188:            for persona_id, nombre in ((titular_id, "Titular"), (colaborador_id, "Colaborador")):
backend/tests/integracion/test_auditoria_transaccion.py:196:                "titular_id": titular_id,
backend/tests/integracion/test_auditoria_transaccion.py:197:                "colaborador_id": colaborador_id,
backend/tests/integracion/test_auditoria_transaccion.py:246:        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
backend/tests/integracion/test_auditoria_transaccion.py:257:            persona_id=datos["colaborador_id"],
backend/tests/integracion/test_auditoria_transaccion.py:271:        assert fila.persona_id == datos["titular_id"]
backend/tests/integracion/test_auditoria_transaccion.py:291:        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
backend/tests/integracion/test_auditoria_transaccion.py:310:                persona_id=datos["colaborador_id"],
backend/tests/integracion/test_auditoria_transaccion.py:334:        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
backend/tests/integracion/test_auditoria_transaccion.py:349:                persona_id=datos["colaborador_id"],
backend/tests/integracion/test_auditoria_transaccion.py:379:        administracion_id=datos["administracion_id"], persona_id=datos["titular_id"]
backend/tests/integracion/test_auditoria_transaccion.py:416:            persona_id=datos["colaborador_id"],
backend/tests/integracion/conftest.py:198:    personas = {rol: uuid4() for rol in ("titular", "editar", "ver", "consejo", "vecino")}
backend/tests/integracion/conftest.py:213:            identidad = Identidad(admin, personas["titular"])
backend/tests/integracion/conftest.py:254:                            "titular": "super_admin",
backend/tests/integracion/conftest.py:258:                        "edificio": None if rol == "titular" else edificios[0],
backend/tests/integracion/conftest.py:300:        api.como("titular")
backend/tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py:44:def test_titular_de_otra_administracion_no_alcanza_nada_de_a(api_edificio: ApiEdificio) -> None:
backend/tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py:45:    """Frente 1, tercer caso: identidad válida de B (titular, con su fila en
backend/tests/integracion/test_regresiones_de_aislamiento_y_grupos_vacios.py:100:    api.como("titular")
backend/src/proptech_core/acceso/dominio/permisos.py:58:    #: que es del vecino, no del titular/colaborador/consejo.
backend/src/proptech_core/acceso/dominio/permisos.py:142:    """D-096. El titular no tiene una asignación por complejo (D6: su fila
backend/tests/integracion/test_texto_recortado_en_el_borde.py:31:    api.como("titular")
backend/tests/integracion/test_texto_recortado_en_el_borde.py:40:    api.como("titular")
backend/tests/integracion/test_texto_recortado_en_el_borde.py:52:    api.como("titular")
backend/tests/integracion/test_texto_recortado_en_el_borde.py:60:    api.como("titular")
backend/tests/integracion/test_texto_recortado_en_el_borde.py:79:    api.como("titular")
backend/tests/integracion/test_texto_recortado_en_el_borde.py:95:    api.como("titular")
backend/tests/integracion/test_texto_sin_caracteres_de_control.py:54:    api.como("titular")
backend/tests/integracion/test_texto_sin_caracteres_de_control.py:67:    api.como("titular")
backend/tests/integracion/test_texto_sin_caracteres_de_control.py:92:    api.como("titular")
backend/tests/integracion/test_perfiles_api.py:158:    api.como("titular")
backend/tests/integracion/test_perfiles_api.py:196:    api.como("titular")
backend/tests/integracion/test_worker_logs_de_arq.py:5:`arq.worker`/`arq.jobs` (nivel info). El formatter propio descarta
backend/tests/integracion/test_422_sin_el_valor.py:26:    api.como("titular")
backend/tests/integracion/test_422_sin_el_valor.py:50:    api.como("titular")
backend/tests/integracion/test_422_sin_el_valor.py:65:    api.como("titular")
backend/tests/integracion/test_altas_sin_id_del_cliente.py:201:        titular_id = uuid.uuid4()
backend/tests/integracion/test_altas_sin_id_del_cliente.py:203:        for pid, nombre in ((titular_id, "titular"), (destinatario_id, "destinatario")):
backend/tests/integracion/test_altas_sin_id_del_cliente.py:212:            (str(admin_id), str(titular_id)),
backend/tests/integracion/test_altas_sin_id_del_cliente.py:218:        "titular": titular_id,
backend/tests/integracion/test_altas_sin_id_del_cliente.py:317:    _como(app_real, mundo["administracion_id"], mundo["titular"])
backend/tests/integracion/test_texto_unicode_seguro.py:28:    api.como("titular")
backend/tests/integracion/test_texto_unicode_seguro.py:52:    api.como("titular")
backend/tests/integracion/test_configuracion_api.py:133:    assert nueva["autor_id"] == str(api.personas["titular"])
backend/tests/integracion/test_identidad_antes_del_cuerpo.py:4:`api_edificio` deja inyectado al titular al final del fixture; acá se saca
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:101:            for persona, rol, nivel in zip(
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:103:                ("titular", "colaborador", "colaborador", "consejo", "vecino"),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:114:                    "(administracion_id,persona_id,rol,complejo_id,unidad_id,nivel) "
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:120:                        None if rol == "titular" else complejo,
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:122:                        nivel,
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:150:    assert columna in ("nivel", "vinculo")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:193:    assert "nivel" not in {fila[0] for fila in catalogo["columnas"]}
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:217:        '    op.drop_column("asignacion_rol", "nivel")',
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:219:        '    op.drop_column("asignacion_rol", "nivel")',
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:250:    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:254:    assert _filas(base_roles, datos, "nivel") == filas
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:271:    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:278:    assert _filas(base_roles, datos, "nivel") == filas
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:358:                ("titular", None, None, None),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:359:                ("colaborador", complejo, None, None),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:443:    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:446:    assert _filas(base_roles, datos, "nivel") == filas
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:521:    for persona, rol, edificio, nivel in [
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:522:        (personas[0], "titular", None, None),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:523:        (personas[1], "colaborador", complejo, "ver"),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:529:                "(administracion_id,persona_id,rol,complejo_id,nivel) "
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:531:                (admin, persona, rol, edificio, nivel),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:535:        catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:541:        assert _filas(base_roles, datos, "nivel") == filas
backend/tests/integracion/test_tasa_fuera_de_rango.py:24:    api.como("titular")
backend/tests/integracion/test_padron_api.py:104:def test_consejo_y_colaborador_ver_leen_padron_y_no_escriben(
backend/tests/integracion/test_contrato_web_escritura.py:25:    api.como("titular")
backend/tests/integracion/test_contrato_web_escritura.py:42:    api.como("titular")
```

## Después

65 coincidencias a las 13:19:54. Cada una está justificada en la tabla siguiente.

```text
infra/Caddyfile:37:	# (api/web) en cada `reverse_proxy`, así que un `header` al nivel del
infra/respaldos/respaldar.sh:62:  local nivel="$1" evento="$2" ts campos=""
infra/respaldos/respaldar.sh:68:  printf '{"ts":"%s","nivel":"%s","servicio":"respaldos","evento":"%s"%s}\n' \
infra/respaldos/respaldar.sh:69:    "$ts" "$nivel" "$evento" "$campos"
infra/ci/ensayo-roles.sh:49:INSERT INTO asignacion_rol (administracion_id,persona_id,rol,complejo_id,unidad_id,nivel)
infra/ci/ensayo-roles.sh:51:        CASE p.nombre WHEN 'Perfil ficticio 1' THEN 'titular'
infra/ci/ensayo-roles.sh:52:                      WHEN 'Perfil ficticio 2' THEN 'colaborador'
infra/ci/ensayo-roles.sh:53:                      WHEN 'Perfil ficticio 3' THEN 'colaborador'
infra/ci/ensayo-roles.sh:102:esperados = ({"titular": 1, "colaborador": 2, "consejo": 1, "vecino": 1}
backend/tests/unitarios/test_rompedor_cargador_yaml_clave_no_string.py:73:    """Cierra la familia (L-009): el mismo defecto, un nivel más adentro."""
backend/tests/infra/test_respaldos.py:295:            assert set(linea) >= {"ts", "nivel", "servicio", "evento"}
backend/tests/infra/test_respaldos.py:370:        assert fallidas[0]["nivel"] == "error"
backend/tests/infra/test_respaldos.py:389:        assert fallidas[0]["nivel"] == "error"
backend/tests/unitarios/test_logs_configuracion.py:23:    """Guarda y restaura los handlers y el nivel de los loggers que toca
backend/tests/unitarios/test_logs_configuracion.py:32:        for nombre, (handlers, nivel) in originales.items():
backend/tests/unitarios/test_logs_configuracion.py:35:            logger.setLevel(nivel)
backend/tests/unitarios/test_logs.py:17:    nivel: int = logging.INFO,
backend/tests/unitarios/test_logs.py:25:        level=nivel,
backend/tests/unitarios/test_logs.py:68:    assert claves[:6] == ["ts", "nivel", "servicio", "logger", "evento", "request_id"]
backend/tests/unitarios/test_logs.py:84:    for nivel, esperado in niveles.items():
backend/tests/unitarios/test_logs.py:85:        datos = json.loads(_formatear(_record(nivel=nivel)))
backend/tests/unitarios/test_logs.py:86:        assert datos["nivel"] == esperado
backend/tests/infra/test_caddyfile_seguridad.py:149:    responde solo sin cuerpo): puestas dentro de un único `header` al nivel
backend/tests/unitarios/acceso/test_permisos.py:243:        ("titular", None, None, None),
backend/tests/unitarios/acceso/test_permisos.py:244:        ("colaborador", COMPLEJO, None, None),
backend/tests/unitarios/test_middleware_error_inesperado.py:59:    assert errores[0]["nivel"] == "error"
backend/src/proptech_core/compartido/reintentos.py:80:    - Si es el último intento: loguea `tarea_agotada` con nivel `error` y
backend/src/proptech_core/compartido/reintentos.py:82:    - Cualquier otro error (no pasajero): loguea `tarea_fallida` con nivel
backend/src/proptech_api/cuerpos.py:10:`strict=True` a nivel del modelo entero chocaría con cómo FastAPI valida el
backend/src/proptech_core/compartido/logs.py:25:#: Campos extra permitidos, además de los campos base (ts, nivel, servicio,
backend/src/proptech_core/compartido/logs.py:83:    Los campos base van en este orden: `ts`, `nivel`, `servicio`, `logger`,
backend/src/proptech_core/compartido/logs.py:96:            "nivel": record.levelname.lower(),
backend/src/proptech_core/compartido/cargador_yaml.py:25:    nivel de anidamiento."""
backend/src/proptech_core/compartido/cargador_yaml.py:41:            # cualquier nivel de anidamiento (este constructor arma todos los
backend/tests/integracion/test_worker_logs_de_arq.py:5:`arq.worker`/`arq.jobs` (nivel info). El formatter propio descarta
backend/tests/integracion/test_worker_caminos_de_falla.py:115:    assert agotados[0]["nivel"] == "error"
backend/tests/integracion/test_worker_caminos_de_falla.py:164:        # contenido crudo del trabajo rechazado) y el nivel es de error.
backend/tests/integracion/test_worker_caminos_de_falla.py:168:        assert any(linea.get("nivel") == "error" for linea in lineas), lineas
backend/tests/integracion/test_asignacion_validacion.py:14:        for rol in ("super_admin", "vecino", "titular", "colaborador", "inventado")
backend/tests/integracion/test_asignacion_validacion.py:19:            ("nivel", "editar"),
backend/tests/integracion/test_asignacion_validacion.py:24:    + [({"rol": "consejo", "nivel": "ver"}, "nivel")],
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:101:            for persona, rol, nivel in zip(
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:103:                ("titular", "colaborador", "colaborador", "consejo", "vecino"),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:114:                    "(administracion_id,persona_id,rol,complejo_id,unidad_id,nivel) "
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:120:                        None if rol == "titular" else complejo,
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:122:                        nivel,
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:150:    assert columna in ("nivel", "vinculo")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:193:    assert "nivel" not in {fila[0] for fila in catalogo["columnas"]}
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:217:        '    op.drop_column("asignacion_rol", "nivel")',
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:219:        '    op.drop_column("asignacion_rol", "nivel")',
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:250:    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:254:    assert _filas(base_roles, datos, "nivel") == filas
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:271:    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:278:    assert _filas(base_roles, datos, "nivel") == filas
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:358:                ("titular", None, None, None),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:359:                ("colaborador", complejo, None, None),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:443:    catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:446:    assert _filas(base_roles, datos, "nivel") == filas
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:521:    for persona, rol, edificio, nivel in [
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:522:        (personas[0], "titular", None, None),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:523:        (personas[1], "colaborador", complejo, "ver"),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:529:                "(administracion_id,persona_id,rol,complejo_id,nivel) "
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:531:                (admin, persona, rol, edificio, nivel),
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:535:        catalogo, filas = _catalogo(base_roles), _filas(base_roles, datos, "nivel")
backend/tests/integracion/test_migracion_roles_de_la_empresa.py:541:        assert _filas(base_roles, datos, "nivel") == filas
```

## Justificación por aparición

| Referencia | Justificación |
|---|---|
| `infra/Caddyfile:37` | G: nivel de anidamiento, ubicación de directiva o configuración del modelo; no es una asignación de acceso. |
| `infra/respaldos/respaldar.sh:62` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `infra/respaldos/respaldar.sh:68` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `infra/respaldos/respaldar.sh:69` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `infra/ci/ensayo-roles.sh:49` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `infra/ci/ensayo-roles.sh:51` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `infra/ci/ensayo-roles.sh:52` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `infra/ci/ensayo-roles.sh:53` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `infra/ci/ensayo-roles.sh:102` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/unitarios/test_rompedor_cargador_yaml_clave_no_string.py:73` | G: nivel de anidamiento, ubicación de directiva o configuración del modelo; no es una asignación de acceso. |
| `backend/tests/infra/test_respaldos.py:295` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/infra/test_respaldos.py:370` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/infra/test_respaldos.py:389` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs_configuracion.py:23` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs_configuracion.py:32` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs_configuracion.py:35` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs.py:17` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs.py:25` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs.py:68` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs.py:84` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs.py:85` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/unitarios/test_logs.py:86` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/infra/test_caddyfile_seguridad.py:149` | G: nivel de anidamiento, ubicación de directiva o configuración del modelo; no es una asignación de acceso. |
| `backend/tests/unitarios/acceso/test_permisos.py:243` | R: entradas obsoletas/fuera de contrato que dominio o API deben rechazar. |
| `backend/tests/unitarios/acceso/test_permisos.py:244` | R: entradas obsoletas/fuera de contrato que dominio o API deben rechazar. |
| `backend/tests/unitarios/test_middleware_error_inesperado.py:59` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/src/proptech_core/compartido/reintentos.py:80` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/src/proptech_core/compartido/reintentos.py:82` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/src/proptech_api/cuerpos.py:10` | G: nivel de anidamiento, ubicación de directiva o configuración del modelo; no es una asignación de acceso. |
| `backend/src/proptech_core/compartido/logs.py:25` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/src/proptech_core/compartido/logs.py:83` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/src/proptech_core/compartido/logs.py:96` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/src/proptech_core/compartido/cargador_yaml.py:25` | G: nivel de anidamiento, ubicación de directiva o configuración del modelo; no es una asignación de acceso. |
| `backend/src/proptech_core/compartido/cargador_yaml.py:41` | G: nivel de anidamiento, ubicación de directiva o configuración del modelo; no es una asignación de acceso. |
| `backend/tests/integracion/test_worker_logs_de_arq.py:5` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/integracion/test_worker_caminos_de_falla.py:115` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/integracion/test_worker_caminos_de_falla.py:164` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/integracion/test_worker_caminos_de_falla.py:168` | L: severidad/campo de logs (JSON, logger o reintentos), conservado por su significado vigente. |
| `backend/tests/integracion/test_asignacion_validacion.py:14` | R: entradas obsoletas/fuera de contrato que dominio o API deben rechazar. |
| `backend/tests/integracion/test_asignacion_validacion.py:19` | R: entradas obsoletas/fuera de contrato que dominio o API deben rechazar. |
| `backend/tests/integracion/test_asignacion_validacion.py:24` | R: entradas obsoletas/fuera de contrato que dominio o API deben rechazar. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:101` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:103` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:114` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:120` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:122` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:150` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:193` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:217` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:219` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:250` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:254` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:271` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:278` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:358` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:359` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:443` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:446` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:521` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:522` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:523` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:529` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:531` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:535` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |
| `backend/tests/integracion/test_migracion_roles_de_la_empresa.py:541` | H: vocabulario y columna de 0016, conversión a 0017 y downgrade; también se verifica su rechazo en head. |

JUICIO: ninguna aparición restante nombra un perfil vigente con el vocabulario
anterior. El guardián nuevo recorre los mismos paths, comprueba las excepciones
por significado y rechaza los nombres anteriores en código o comentarios vivos.
Su rojo detectó 110 apariciones no justificadas antes de corregir los nombres.
La excepción de complejo nulo no cambió: su comentario ahora dice alcance principal.

SUPUESTO: ninguno sobre las coincidencias. Las salidas son las del rg real;
el test recorre texto local y excluye archivos/carpetas ocultos y bytecode.
