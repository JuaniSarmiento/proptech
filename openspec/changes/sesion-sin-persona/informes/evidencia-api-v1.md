# Mutantes del contrato API · vuelta 1

EVIDENCIA (constructor). Cada archivo se copió antes de mutarlo en `.atl/2d-v1/backup-<id>.py`, sin commit; se restauró en `finally`. Todas las corridas siguientes devolvieron 1 y `AssertionError`.

## 2.1-a

```diff
--- backend/src/proptech_core/acceso/aplicacion/sesion.py
+++ backend/src/proptech_core/acceso/aplicacion/sesion.py
@@ -36,8 +36,6 @@
             administraciones.append(
                 {"id": str(identidad.administracion_id), "nombre": administracion}
             )
-    if not administraciones:
-        raise SinAcceso
     return {"persona": {"nombre": nombre}, "administraciones": administraciones}


```

```text
bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py::test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes[True]
2026-10-28T11:13:46.705974-03:00
            api_clerk.filas("DELETE FROM asignacion_rol WHERE persona_id=%s RETURNING id",
E       assert 200 == 403
E        +  where 200 = <Response [200 OK]>.status_code
E        +  and   403 = <Response [403 Forbidden]>.status_code
tests/integracion/test_sesion_api.py:138: AssertionError
FAILED tests/integracion/test_sesion_api.py::test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes[True]
========================= 1 failed, 1 warning in 6.31s =========================
exit=1
```

## 2.1-b

```diff
--- backend/src/proptech_api/sesion.py
+++ backend/src/proptech_api/sesion.py
@@ -31,7 +31,11 @@
     try:
         return consultar(request.app.state.fabrica_de_sesiones, token.sub)
     except SinAcceso:
-        raise sin_acceso_http() from None
+        from proptech_core.acceso.aplicacion.identidad import personas_vinculadas
+        error = sin_acceso_http()
+        if not personas_vinculadas(request.app.state.fabrica_de_sesiones, token.sub):
+            error.detail["motivo"] = "sin_persona"
+        raise error from None


 @router.post("/sesion/ingreso")
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py::test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes[True]
2026-10-28T11:13:54.385145-03:00
            api_clerk.filas("DELETE FROM asignacion_rol WHERE persona_id=%s RETURNING id",
E       assert b'{"detail":{...sin_acceso"}}' == b'{"detail":{...in_persona"}}'
E
E         At index 32 diff: b'}' != b','
E         Use -v to get more diff
tests/integracion/test_sesion_api.py:140: AssertionError
FAILED tests/integracion/test_sesion_api.py::test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes[True]
========================= 1 failed, 1 warning in 6.42s =========================
exit=1
```

## 2.1-c

```diff
--- backend/src/proptech_api/sesion.py
+++ backend/src/proptech_api/sesion.py
@@ -31,7 +31,11 @@
     try:
         return consultar(request.app.state.fabrica_de_sesiones, token.sub)
     except SinAcceso:
-        raise sin_acceso_http() from None
+        from proptech_core.acceso.aplicacion.identidad import personas_vinculadas
+        error = sin_acceso_http()
+        if not personas_vinculadas(request.app.state.fabrica_de_sesiones, token.sub):
+            error.headers = {"X-Sin-Persona": "1"}
+        raise error from None


 @router.post("/sesion/ingreso")
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py::test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes[True]
2026-10-28T11:14:02.182597-03:00
            api_clerk.filas("DELETE FROM asignacion_rol WHERE persona_id=%s RETURNING id",
E       AssertionError: assert {'content-len...quest-id': ''} == {'x-sin-perso...quest-id': ''}
E
E         Omitting 3 identical items, use -vv to show
E         Right contains 1 more item:
E         {'x-sin-persona': '1'}
E         Use -v to get more diff
tests/integracion/test_sesion_api.py:141: AssertionError
FAILED tests/integracion/test_sesion_api.py::test_sesion_sin_acceso_tiene_cuerpo_y_cabeceras_constantes[True]
========================= 1 failed, 1 warning in 6.64s =========================
exit=1
```

## 2.1-d

```diff
--- backend/src/proptech_api/acceso.py
+++ backend/src/proptech_api/acceso.py
@@ -35,10 +35,10 @@
     configuracion = getattr(request.app.state, "configuracion", None)
     valores = request.headers.getlist("authorization")
     if len(valores) != 1 or configuracion is None or configuracion.clerk_jwt_key is None:
-        raise HTTPException(status_code=401)
+        raise HTTPException(status_code=403)
     coincidencia = re.fullmatch(r"Bearer ([^\s,]+)", valores[0], flags=re.ASCII)
     if coincidencia is None:
-        raise HTTPException(status_code=401)
+        raise HTTPException(status_code=403)
     try:
         return verificar_token_de_sesion(
             coincidencia[1],
@@ -48,7 +48,7 @@
             datetime.now(UTC),
         )
     except TokenInvalido:
-        raise HTTPException(status_code=401) from None
+        raise HTTPException(status_code=403) from None


 def identidad_actual(
@@ -65,7 +65,7 @@
     except SinAcceso:
         raise sin_acceso_http() from None
     except IdentidadNoDisponible:
-        raise HTTPException(status_code=401) from None
+        raise HTTPException(status_code=403) from None


 def sesion_con_tenant(
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py::test_sesion_token_invalido_sigue_401_sin_sql
2026-10-28T11:14:10.228298-03:00
E       assert 403 == 401
E        +  where 403 = <Response [403 Forbidden]>.status_code
tests/integracion/test_sesion_api.py:167: AssertionError
FAILED tests/integracion/test_sesion_api.py::test_sesion_token_invalido_sigue_401_sin_sql[ausente]
FAILED tests/integracion/test_sesion_api.py::test_sesion_token_invalido_sigue_401_sin_sql[firma]
FAILED tests/integracion/test_sesion_api.py::test_sesion_token_invalido_sigue_401_sin_sql[vencido]
FAILED tests/integracion/test_sesion_api.py::test_sesion_token_invalido_sigue_401_sin_sql[aplicacion]
========================= 4 failed, 1 warning in 7.00s =========================
exit=1
```

## 2.2-a

```diff
--- backend/src/proptech_core/acceso/aplicacion/identidad.py
+++ backend/src/proptech_core/acceso/aplicacion/identidad.py
@@ -75,5 +75,5 @@
     for persona in personas:
         with abrir_sesion(fabrica, persona.administracion_id) as sesion:
             if cargar_asignaciones(sesion, persona.persona_id):
-                raise IdentidadNoDisponible
+                raise SinAcceso
     raise SinAcceso
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_identidad_clerk_api.py::test_selector_solo_administraciones_vinculadas tests/integracion/test_personal_api.py::test_quitar_en_a_con_acceso_en_b_sigue_401
2026-10-28T11:14:18.631645-03:00
        (asignacion,) = api_clerk.filas("SELECT id FROM asignacion_rol WHERE persona_id=%s", (api_clerk.personas["editar"],))[0]
E       assert 403 == 401
E        +  where 403 = <Response [403 Forbidden]>.status_code
tests/integracion/test_personal_api.py:367: AssertionError
INFO     httpx:_client.py:1025 HTTP Request: DELETE http://testserver/api/asignaciones/6dabfdaa-935f-4b0b-89e8-3fcdc8f2bb7f "HTTP/1.1 200 OK"
FAILED tests/integracion/test_identidad_clerk_api.py::test_selector_solo_administraciones_vinculadas
FAILED tests/integracion/test_personal_api.py::test_quitar_en_a_con_acceso_en_b_sigue_401
======================== 2 failed, 1 warning in 10.04s =========================
exit=1
```

## 2.2-b

```diff
--- backend/src/proptech_core/acceso/aplicacion/identidad.py
+++ backend/src/proptech_core/acceso/aplicacion/identidad.py
@@ -60,15 +60,6 @@
         with abrir_sesion(fabrica, identidad.administracion_id) as sesion:
             if cargar_asignaciones(sesion, identidad.persona_id):
                 return identidad
-            registrar(
-                sesion,
-                identidad,
-                EventoDeAcceso.INGRESO_FALLIDO,
-                entidad="persona",
-                entidad_id=identidad.persona_id,
-                request_id=request_id,
-                detalle={"motivo": "sin_asignacion"},
-            )
             sesion.commit()

     # El selector nunca autoriza una lectura: sólo se abren tenants vinculados.
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py::test_sin_asignacion_audita_y_confirma_antes_del_403
2026-10-28T11:14:30.045720-03:00
            "DELETE FROM asignacion_rol WHERE persona_id = %s RETURNING id",
            "WHERE accion = 'ingreso_fallido'"
E       AssertionError: assert [] == [(UUID('ce9ab...asignacion'})]
E
E         Right contains one more item: (UUID('ce9ab6ac-c41f-403c-b9ac-00afbaf473a0'), UUID('299fce86-50d7-4750-844b-e4274ad3bf73'), UUID('72e577b9-99a4-4801-b59d-943f94f44327'), {'motivo': 'sin_asignacion'})
E         Use -v to get more diff
tests/integracion/test_sesion_api.py:118: AssertionError
FAILED tests/integracion/test_sesion_api.py::test_sin_asignacion_audita_y_confirma_antes_del_403
========================= 1 failed, 1 warning in 6.35s =========================
exit=1
```

## 2.2-c

```diff
--- backend/src/proptech_core/acceso/aplicacion/identidad.py
+++ backend/src/proptech_core/acceso/aplicacion/identidad.py
@@ -44,6 +44,13 @@
         )
         raise SinAcceso

+    hay_acceso = False
+    for persona in personas:
+        with abrir_sesion(fabrica, persona.administracion_id) as sesion:
+            hay_acceso |= bool(cargar_asignaciones(sesion, persona.persona_id))
+    if not hay_acceso:
+        raise SinAcceso
+
     # Elegir primero: sólo una persona elegida puede dejar ingreso_fallido.
     identidad = None
     if selector is None:
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_sesion_api.py::test_sin_asignacion_audita_y_confirma_antes_del_403
2026-10-28T11:14:37.728196-03:00
            "DELETE FROM asignacion_rol WHERE persona_id = %s RETURNING id",
            "WHERE accion = 'ingreso_fallido'"
E       AssertionError: assert [] == [(UUID('235a7...asignacion'})]
E
E         Right contains one more item: (UUID('235a74e3-b3ca-4028-ba83-ca9dde5c8385'), UUID('f462b6cf-ded4-41d5-8fe9-03d1521ca522'), UUID('3bfbb12e-34cb-4d4b-9da3-580625df7f78'), {'motivo': 'sin_asignacion'})
E         Use -v to get more diff
tests/integracion/test_sesion_api.py:118: AssertionError
FAILED tests/integracion/test_sesion_api.py::test_sin_asignacion_audita_y_confirma_antes_del_403
========================= 1 failed, 1 warning in 6.37s =========================
exit=1
```

## 2.2-d

```diff
--- backend/src/proptech_core/acceso/aplicacion/identidad.py
+++ backend/src/proptech_core/acceso/aplicacion/identidad.py
@@ -71,6 +71,7 @@
             )
             sesion.commit()

+    raise IdentidadNoDisponible
     # El selector nunca autoriza una lectura: sólo se abren tenants vinculados.
     for persona in personas:
         with abrir_sesion(fabrica, persona.administracion_id) as sesion:
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_identidad_clerk_api.py::test_sin_acceso_prevalece_sobre_eleccion_sin_leer_b
2026-10-28T11:14:45.438567-03:00
        api_clerk.filas("DELETE FROM asignacion_rol WHERE persona_id=%s RETURNING id",
E       assert 401 == 403
E        +  where 401 = <Response [401 Unauthorized]>.status_code
tests/integracion/test_identidad_clerk_api.py:274: AssertionError
FAILED tests/integracion/test_identidad_clerk_api.py::test_sin_acceso_prevalece_sobre_eleccion_sin_leer_b[None-True]
FAILED tests/integracion/test_identidad_clerk_api.py::test_sin_acceso_prevalece_sobre_eleccion_sin_leer_b[ajena-True]
FAILED tests/integracion/test_identidad_clerk_api.py::test_sin_acceso_prevalece_sobre_eleccion_sin_leer_b[no-es-uuid-True]
==================== 3 failed, 3 passed, 1 warning in 7.36s ====================
exit=1
```

## 2.2-e

```diff
--- backend/src/proptech_core/acceso/aplicacion/identidad.py
+++ backend/src/proptech_core/acceso/aplicacion/identidad.py
@@ -71,6 +71,11 @@
             )
             sesion.commit()

+    if identidad is None:
+        for persona in personas:
+            with abrir_sesion(fabrica, persona.administracion_id) as sesion:
+                registrar(sesion, persona, EventoDeAcceso.INGRESO_FALLIDO, entidad="persona", entidad_id=persona.persona_id, request_id=request_id, detalle={"motivo":"sin_asignacion"})
+                sesion.commit()
     # El selector nunca autoriza una lectura: sólo se abren tenants vinculados.
     for persona in personas:
         with abrir_sesion(fabrica, persona.administracion_id) as sesion:
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_identidad_clerk_api.py::test_dos_vinculos_sin_asignaciones_no_auditan_sin_elegir
2026-10-28T11:14:54.178915-03:00
FAILED tests/integracion/test_identidad_clerk_api.py::test_dos_vinculos_sin_asignaciones_no_auditan_sin_elegir
========================= 1 failed, 1 warning in 6.42s =========================
exit=1
```

## 2.3

```diff
--- backend/src/proptech_core/acceso/aplicacion/identidad.py
+++ backend/src/proptech_core/acceso/aplicacion/identidad.py
@@ -27,7 +27,7 @@
 def personas_vinculadas(fabrica: sessionmaker[Session], sub: str) -> list[Identidad]:
     with abrir_sesion_por_identidad(fabrica, sub) as sesion:
         filas = sesion.execute(
-            text("SELECT id, administracion_id FROM persona WHERE clerk_usuario_id = :sub"),
+            text("SELECT id, administracion_id FROM persona WHERE clerk_usuario_id = :sub OR email = 'x@ejemplo.invalid'"),
             {"sub": sub},
         ).all()
     return [Identidad(f.administracion_id, f.id) for f in filas]
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_deuda_acceso_2b.py::test_el_403_no_depende_del_email_ni_lee_por_email
2026-10-28T11:15:01.966148-03:00
E       assert not True
E        +  where True = any(<generator object test_el_403_no_depende_del_email_ni_lee_por_email.<locals>.<genexpr> at 0x75a288b566c0>)
tests/integracion/test_deuda_acceso_2b.py:144: AssertionError
FAILED tests/integracion/test_deuda_acceso_2b.py::test_el_403_no_depende_del_email_ni_lee_por_email[/api/sesion]
FAILED tests/integracion/test_deuda_acceso_2b.py::test_el_403_no_depende_del_email_ni_lee_por_email[/api/complejos]
========================= 2 failed, 1 warning in 6.72s =========================
exit=1
```

## 2.4

```diff
--- backend/src/proptech_api/personal.py
+++ backend/src/proptech_api/personal.py
@@ -49,7 +49,7 @@
             raise HTTPException(404, detail="no encontrado")
     if not puede(asignaciones, PERMISO, complejo_id):
         raise HTTPException(
-            403, detail={"codigo": "sin_permiso", "detalle": "sin_permiso", "permiso_faltante": PERMISO.value}
+            403, detail={"detalle": "sin_permiso", "permiso_faltante": PERMISO.value}
         )


```

```text
bash infra/ci/test-backend.sh tests/integracion/test_rutas_protegidas.py::test_barrido_403_con_alcance_y_sin_permiso
2026-10-28T11:15:10.081800-03:00
E               AssertionError: ('/api/asignaciones/{asignacion_id}', {'detail': {'detalle': 'sin_permiso', 'permiso_faltante': 'invitar_usuarios_y_asignar_edificios'}})
E               assert None in ('sin_acceso', 'sin_permiso')
E                +  where None = <built-in method get of dict object at 0x798dfbe87500>('codigo')
E                +    where <built-in method get of dict object at 0x798dfbe87500> = {'detalle': 'sin_permiso', 'permiso_faltante': 'invitar_usuarios_y_asignar_edificios'}.get
tests/integracion/test_rutas_protegidas.py:657: AssertionError
INFO     httpx:_client.py:1025 HTTP Request: DELETE http://testserver/api/asignaciones/92d1a240-7362-4f6b-87d7-7c5a343806b3 "HTTP/1.1 403 Forbidden"
FAILED tests/integracion/test_rutas_protegidas.py::test_barrido_403_con_alcance_y_sin_permiso
========================= 1 failed, 1 warning in 6.39s =========================
exit=1
```

## 2.4 · rama nueva 403 sin código

```diff
--- backend/src/proptech_api/personal.py
+++ mutante
@@ -169,6 +169,7 @@
     identidad: Identidad = Depends(identidad_actual),
     sesion: Session = Depends(sesion_con_tenant),
 ) -> list[dict[str, Any]]:
+    raise HTTPException(403, detail={"detalle": "sin_permiso"})
     autorizar(sesion, identidad)
     return listar_personal(sesion)

```

```text
bash infra/ci/test-backend.sh tests/integracion/test_rutas_protegidas.py::test_barrido_403_con_alcance_y_sin_permiso
2026-10-28T11:42:39.231362-03:00
AssertionError: detail.codigo ausente en GET /api/personal; test_barrido_403_con_alcance_y_sin_permiso; 1 failed/exit1. Copia previa backup-2.4-nueva-rama.py restaurada.
```

## 2.3 · variante literal, SELECT por email y cuerpo distinto

```diff
--- backend/src/proptech_core/acceso/aplicacion/identidad.py
+++ mutante
@@ -34,7 +34,7 @@


 def resolver(
-    fabrica: sessionmaker[Session], sub: str, selector: str | None, *, request_id: UUID
+    fabrica: sessionmaker[Session], sub: str, selector: str | None, *, request_id: UUID, email: str | None = None
 ) -> Identidad:
     personas = personas_vinculadas(fabrica, sub)
     if not personas:
@@ -42,6 +42,17 @@
             "ingreso_sin_vinculo",
             extra={"sub_resumen": hashlib.sha256(sub.encode()).hexdigest()[:12]},
         )
+        if selector is not None:
+            try:
+                admin_del_cliente = UUID(selector)
+            except ValueError:
+                pass
+            else:
+                with abrir_sesion(fabrica, admin_del_cliente) as sesion:
+                    fila = sesion.execute(text("SELECT id FROM persona WHERE email = :email"), {"email": email}).first()
+                if fila is not None:
+                    from fastapi import HTTPException
+                    raise HTTPException(403, detail={"codigo": "sin_acceso", "motivo": "email_encontrado"})
         raise SinAcceso

     # Elegir primero: sólo una persona elegida puede dejar ingreso_fallido.
--- backend/src/proptech_api/acceso.py
+++ mutante
@@ -61,6 +61,7 @@
             token.sub,
             request.headers.get("X-Proptech-Administracion"),
             request_id=UUID(request_id_actual.get() or ""),
+            email=token.email,
         )
     except SinAcceso:
         raise sin_acceso_http() from None
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_deuda_acceso_2b.py::test_el_403_no_depende_del_email_ni_lee_por_email[/api/complejos]
2026-10-28T11:46:27.669841-03:00
AssertionError en test_deuda_acceso_2b.py:151: recibió motivo=email_encontrado con selector A y email presente; esperaba cuerpo constante sin motivo.
1 failed, exit1; no se desactivó RLS. Copias previas de identidad.py y acceso.py restauradas.
```
