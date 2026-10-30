# Mutantes del ejemplo · vuelta 1

EVIDENCIA (constructor): cada mutación de producción se hizo después de copia previa sin commit en `.atl/2d-v1/backup-<id>.py`; restauración en finally. Los dos imports prohibidos se agregaron a copias temporales de core/API/worker sin archivos `.env*`; el checker real falló nombrando cada importador.

JUICIO (constructor, confianza alta, contra D5 y tarea5.1): el mutanteg se discrimina por SQL: ambos caminos deben dar el mismo mensaje, de modo que quitar el chequeo previo no puede diferenciarse por salida si queda el except del UNIQUE. Se exige el SELECT previo, ya requerido por D5; no se agregó una regla de producción.

## 5-a

```diff
--- backend/src/proptech_core/complejos/aplicacion/ejemplo.py
+++ backend/src/proptech_core/complejos/aplicacion/ejemplo.py
@@ -453,7 +453,7 @@

     emisor_normalizado = None
     if args.clerk_usuario is not None:
-        if re.fullmatch(r"user_[A-Za-z0-9]{1,64}", args.clerk_usuario, flags=re.ASCII) is None:
+        if re.match(r"user_[A-Za-z0-9]{1,64}", args.clerk_usuario, flags=re.ASCII) is None:
             print(
                 "el id de cuenta no tiene el formato permitido; no se escribió nada",
                 file=sys.stderr,
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores
2026-10-28T11:38:39.178133-03:00
E           AssertionError: assert 'conectó' != 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
E           AssertionError: assert 'conectó' != 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_abc\n-https://x.clerk.accounts.dev-False]
=================== 2 failed, 19 passed, 1 warning in 0.45s ====================
exit=1
```

## 5-b

```diff
--- backend/src/proptech_core/complejos/aplicacion/ejemplo.py
+++ backend/src/proptech_core/complejos/aplicacion/ejemplo.py
@@ -440,7 +440,11 @@
     subparsers = parser.add_subparsers(dest="accion", required=True)
     cargar_parser = subparsers.add_parser("cargar", help="Carga el edificio de ejemplo en la base")
     cargar_parser.add_argument("--semilla", default=None)
-    cargar_parser.add_argument("--clerk-usuario", default=None)
+    def validar_id(valor: str) -> str:
+        if re.fullmatch(r"user_[A-Za-z0-9]{1,64}", valor, flags=re.ASCII) is None:
+            raise ValueError("formato inválido")
+        return valor
+    cargar_parser.add_argument("--clerk-usuario", default=None, type=validar_id)
     args = parser.parse_args(argv)

     if os.environ.get("PROPTECH_ENTORNO") != ENTORNO_DE_DESARROLLO:
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores
2026-10-28T11:38:40.557632-03:00
E         'user_ñ' is contained here:
E           d value: 'user_ñ'
E         ?           ++++++
tests/integracion/test_ejemplo_casos_de_uso.py:638: AssertionError
E       assert 2 == 1
tests/integracion/test_ejemplo_casos_de_uso.py:641: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[otra_forma-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_\xf1-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_abc\n-https://x.clerk.accounts.dev-False]
=================== 5 failed, 16 passed, 1 warning in 0.46s ====================
exit=1
```

## 5-c

```diff
--- backend/src/proptech_core/complejos/aplicacion/ejemplo.py
+++ backend/src/proptech_core/complejos/aplicacion/ejemplo.py
@@ -453,12 +453,6 @@

     emisor_normalizado = None
     if args.clerk_usuario is not None:
-        if re.fullmatch(r"user_[A-Za-z0-9]{1,64}", args.clerk_usuario, flags=re.ASCII) is None:
-            print(
-                "el id de cuenta no tiene el formato permitido; no se escribió nada",
-                file=sys.stderr,
-            )
-            return 1
         emisor_normalizado = _emisor_de_desarrollo(os.environ.get("CLERK_EMISOR"))
         if emisor_normalizado is None:
             print(
@@ -479,6 +473,12 @@
         return 1

     engine = crear_engine(configuracion)
+    if re.fullmatch(r"user_[A-Za-z0-9]{1,64}", args.clerk_usuario, flags=re.ASCII) is None:
+        print(
+            "el id de cuenta no tiene el formato permitido; no se escribió nada",
+            file=sys.stderr,
+        )
+        return 1
     try:
         verificar_rol_de_aplicacion_seguro(engine)
         verificar_tablas_de_solo_agregar(engine)
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores
2026-10-28T11:38:41.879120-03:00
E           AssertionError: assert 'conectó' != 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
E           AssertionError: assert 'conectó' != 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
E           AssertionError: assert 'conectó' != 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[otra_forma-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_\xf1-https://x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_abc\n-https://x.clerk.accounts.dev-False]
=================== 5 failed, 16 passed, 1 warning in 0.52s ====================
exit=1
```

## 5-d

```diff
--- backend/src/proptech_core/complejos/aplicacion/ejemplo.py
+++ backend/src/proptech_core/complejos/aplicacion/ejemplo.py
@@ -419,7 +419,7 @@
         if (
             partes.scheme != "https"
             or not partes.hostname
-            or not partes.hostname.endswith(".clerk.accounts.dev")
+            or not ("clerk.accounts.dev" in emisor)
             or partes.username is not None
             or partes.password is not None
             or partes.port not in (None, 443)
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores
2026-10-28T11:38:43.324163-03:00
E           AssertionError: assert 'conectó' != 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
E           AssertionError: assert 1 == 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:633: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev.evil.com-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://X.CLERK.ACCOUNTS.DEV-True]
=================== 2 failed, 19 passed, 1 warning in 0.45s ====================
exit=1
```

## 5-d2

```diff
--- backend/src/proptech_core/complejos/aplicacion/ejemplo.py
+++ backend/src/proptech_core/complejos/aplicacion/ejemplo.py
@@ -420,14 +420,6 @@
             partes.scheme != "https"
             or not partes.hostname
             or not partes.hostname.endswith(".clerk.accounts.dev")
-            or partes.username is not None
-            or partes.password is not None
-            or partes.port not in (None, 443)
-            or partes.query
-            or partes.fragment
-            or "?" in emisor
-            or "#" in emisor
-            or partes.path not in ("", "/")
         ):
             return None
         return f"https://{partes.hostname}"
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores
2026-10-28T11:38:44.706342-03:00
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
E           AssertionError: assert 'conectó' != 'conectó'
tests/integracion/test_ejemplo_casos_de_uso.py:635: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://u:p@x.clerk.accounts.dev-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev?x=1-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev#f-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev/ruta-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev:puerto-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev:8443-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev?-False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev#-False]
=================== 8 failed, 13 passed, 1 warning in 0.61s ====================
exit=1
```

## 5-e

```diff
--- backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
+++ backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
@@ -41,7 +41,7 @@
             sesion.execute(
                 text(
                     "UPDATE persona SET clerk_usuario_id = :sub WHERE id = :persona "
-                    "AND (clerk_usuario_id IS NULL OR clerk_usuario_id = :sub)"
+                    ""
                 ),
                 {"sub": sub, "persona": persona_id},
             ),
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_vincular_primera_carga_o_existente_e_idempotencia
2026-10-28T11:38:46.276034-03:00
E           assert (None is not None)
tests/integracion/test_ejemplo_casos_de_uso.py:700: AssertionError
E           assert (None is not None)
tests/integracion/test_ejemplo_casos_de_uso.py:700: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_vincular_primera_carga_o_existente_e_idempotencia[False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_vincular_primera_carga_o_existente_e_idempotencia[True]
========================= 2 failed, 1 warning in 6.31s =========================
exit=1
```

## 5-f

```diff
--- backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
+++ backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
@@ -41,7 +41,7 @@
             sesion.execute(
                 text(
                     "UPDATE persona SET clerk_usuario_id = :sub WHERE id = :persona "
-                    "AND (clerk_usuario_id IS NULL OR clerk_usuario_id = :sub)"
+                    ""
                 ),
                 {"sub": sub, "persona": persona_id},
             ),
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_dos_vinculaciones_a_la_vez_no_pisan_a_la_ganadora
2026-10-28T11:38:53.744598-03:00
            if "SELECT clerk_usuario_id FROM persona WHERE id" in str(args[2]):
E           assert [True, True] == [False, True]
E
E             At index 0 diff: True != False
E             Use -v to get more diff
tests/integracion/test_ejemplo_casos_de_uso.py:826: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_dos_vinculaciones_a_la_vez_no_pisan_a_la_ganadora
========================= 1 failed, 1 warning in 4.55s =========================
exit=1
```

## 5-g

```diff
--- backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
+++ backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
@@ -25,12 +25,6 @@
         or persona_id != PERSONA_SUPER_ADMIN_EJEMPLO_ID
     ):
         raise VinculacionDeDesarrolloNoDisponible("sólo se puede vincular la persona del ejemplo")
-    ajena = sesion.execute(
-        text("SELECT id FROM persona WHERE clerk_usuario_id = :sub AND id <> :persona LIMIT 1"),
-        {"sub": sub, "persona": persona_id},
-    ).first()
-    if ajena is not None:
-        raise VinculacionDeDesarrolloNoDisponible(_MENSAJE_CUENTA_AJENA)
     anterior = sesion.execute(
         text("SELECT clerk_usuario_id FROM persona WHERE id = :persona"),
         {"persona": persona_id},
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_el_id_de_otra_persona_es_error_propio_sin_datos
2026-10-28T11:38:59.480035-03:00
>           assert any("SELECT id FROM persona WHERE clerk_usuario_id" in sql for sql in sentencias)
E           assert False
E            +  where False = any(<generator object test_el_id_de_otra_persona_es_error_propio_sin_datos.<locals>.<genexpr> at 0x76971c9bdb10>)
tests/integracion/test_ejemplo_casos_de_uso.py:742: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_el_id_de_otra_persona_es_error_propio_sin_datos
========================= 1 failed, 1 warning in 4.32s =========================
exit=1
```

## 5-g2

```diff
--- backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
+++ backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
@@ -47,6 +47,7 @@
             ),
         )
     except IntegrityError as error:
+        raise
         if (
             isinstance(error.orig, UniqueViolation)
             and error.orig.diag.constraint_name == "uq_persona_clerk_administracion"
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_carrera_de_unicidad_se_traduce_sin_parametros
2026-10-28T11:39:04.932918-03:00
            if "UPDATE persona SET clerk_usuario_id" in str(args[2]) and not disparo:
                    c.execute("UPDATE persona SET clerk_usuario_id='user_Dev123' WHERE id=%s", (otra,))
E           AssertionError: assert 'esa cuenta ya está vinculada a otra persona del ejemplo' in 'no se pudo completar la carga; no se escribió nada\n'
E            +  where 'no se pudo completar la carga; no se escribió nada\n' = CaptureResult(out='ejemplo cargado: 00000000-0000-4000-8000-0000000000e0\n', err='no se pudo completar la carga; no se escribió nada\n').err
tests/integracion/test_ejemplo_casos_de_uso.py:789: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_carrera_de_unicidad_se_traduce_sin_parametros
========================= 1 failed, 1 warning in 4.45s =========================
exit=1
```

## 5-h

```diff
--- backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
+++ backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
@@ -20,11 +20,6 @@

 def vincular(sesion: Session, administracion_id: UUID, persona_id: UUID, sub: str) -> str:
     """El caller conserva la transacción y el tenant; sólo acepta el ejemplo."""
-    if (
-        administracion_id != ADMINISTRACION_EJEMPLO_ID
-        or persona_id != PERSONA_SUPER_ADMIN_EJEMPLO_ID
-    ):
-        raise VinculacionDeDesarrolloNoDisponible("sólo se puede vincular la persona del ejemplo")
     ajena = sesion.execute(
         text("SELECT id FROM persona WHERE clerk_usuario_id = :sub AND id <> :persona LIMIT 1"),
         {"sub": sub, "persona": persona_id},
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_la_funcion_de_vinculacion_rechaza_otra_persona_sin_escribir
2026-10-28T11:39:10.551840-03:00
E               assert None is not None
tests/integracion/test_ejemplo_casos_de_uso.py:913: AssertionError
E               assert None is not None
tests/integracion/test_ejemplo_casos_de_uso.py:913: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_la_funcion_de_vinculacion_rechaza_otra_persona_sin_escribir[False]
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_la_funcion_de_vinculacion_rechaza_otra_persona_sin_escribir[True]
========================= 2 failed, 1 warning in 6.28s =========================
exit=1
```

## 5-i

```diff
--- backend/src/proptech_core/complejos/aplicacion/ejemplo.py
+++ backend/src/proptech_core/complejos/aplicacion/ejemplo.py
@@ -21,6 +21,7 @@

 from __future__ import annotations

+from typing import Any
 import argparse
 import os
 import re
@@ -333,7 +334,7 @@
         raise EjemploDistinto("; ".join(diferencias))


-def cargar(
+def _cargar_original(
     fabrica: sessionmaker[Session],
     *,
     parametros: Parametros,
@@ -411,6 +412,15 @@
     )


+
+def cargar(*args: Any, **kwargs: Any) -> ResultadoCarga:
+    usuario = kwargs.pop("clerk_usuario", None)
+    resultado = _cargar_original(*args, **kwargs)
+    if usuario is not None:
+        with abrir_sesion(args[0], ADMINISTRACION_EJEMPLO_ID) as sesion, sesion.begin():
+            vincular(sesion, ADMINISTRACION_EJEMPLO_ID, PERSONA_SUPER_ADMIN_EJEMPLO_ID, usuario)
+    return resultado
+
 def _emisor_de_desarrollo(emisor: str | None) -> str | None:
     if not emisor:
         return None
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_conflicto_al_crear_revierte_toda_la_carga
2026-10-28T11:39:18.006632-03:00
                text("UPDATE persona SET clerk_usuario_id='user_Otra' WHERE id=:id"),
E           AssertionError: assert {'administrac...uditoria': 18} == {'administrac...auditoria': 0}
E
E             Differing items:
E             {'auditoria': 18} != {'auditoria': 0}
E             {'complejo': 1} != {'complejo': 0}
E             {'administracion': 1} != {'administracion': 0}
E             {'persona': 1} != {'persona': 0}
E             Use -v to get more diff
tests/integracion/test_ejemplo_casos_de_uso.py:856: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_conflicto_al_crear_revierte_toda_la_carga
========================= 1 failed, 1 warning in 4.49s =========================
exit=1
```

## 5-normalizacion

```diff
--- backend/src/proptech_core/complejos/aplicacion/ejemplo.py
+++ backend/src/proptech_core/complejos/aplicacion/ejemplo.py
@@ -467,7 +467,7 @@
             )
             return 1

-    configuracion = Configuracion(clerk_emisor=emisor_normalizado)
+    configuracion = Configuracion()
     parametros = leer_parametros(configuracion.proptech_parametros)
     try:
         georef = leer_georef(str(_ruta_georef_por_defecto(configuracion)))
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores
2026-10-28T11:39:23.679190-03:00
E           AssertionError: assert 'configuració...es del engine' == 'conectó'
E
E             - conectó
E             + configuración rechazada antes del engine
tests/integracion/test_ejemplo_casos_de_uso.py:633: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_opcion_clerk_valida_antes_de_conectar_sin_repetir_valores[user_Dev123-https://x.clerk.accounts.dev/-True]
=================== 1 failed, 20 passed, 1 warning in 0.41s ====================
exit=1
```

## 5-otra-integridad

```diff
--- backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
+++ backend/src/proptech_core/acceso/aplicacion/vinculacion_de_desarrollo.py
@@ -47,10 +47,7 @@
             ),
         )
     except IntegrityError as error:
-        if (
-            isinstance(error.orig, UniqueViolation)
-            and error.orig.diag.constraint_name == "uq_persona_clerk_administracion"
-        ):
+        if True:
             raise VinculacionDeDesarrolloNoDisponible(_MENSAJE_CUENTA_AJENA) from None
         raise
     if resultado.rowcount != 1:
```

```text
bash infra/ci/test-backend.sh tests/integracion/test_ejemplo_casos_de_uso.py::test_otro_integrity_error_no_se_disfraza_de_cuenta_ajena
2026-10-28T11:39:24.982953-03:00
            c.execute("ALTER TABLE persona ADD CONSTRAINT ck_solo_nulo_de_prueba CHECK (clerk_usuario_id IS NULL)")
E       AssertionError: assert 'no se pudo completar la carga' in 'esa cuenta ya está vinculada a otra persona del ejemplo\n'
E        +  where 'esa cuenta ya está vinculada a otra persona del ejemplo\n' = CaptureResult(out='ejemplo cargado: 00000000-0000-4000-8000-0000000000e0\n', err='esa cuenta ya está vinculada a otra persona del ejemplo\n').err
tests/integracion/test_ejemplo_casos_de_uso.py:950: AssertionError
FAILED tests/integracion/test_ejemplo_casos_de_uso.py::test_otro_integrity_error_no_se_disfraza_de_cuenta_ajena
========================= 1 failed, 1 warning in 4.36s =========================
exit=1
```

## 5.3-api

```diff
from proptech_core.acceso.aplicacion.vinculacion_de_desarrollo import vincular
```

```text
cd backend && uv run python -c 'import os; from pathlib import Path; import tests.unitarios.test_fronteras_de_modulos as f; f.RAIZ_SRC=Path(os.environ["COPIA_SRC"])/"proptech_core"; f.RAIZ_API=Path(os.environ["COPIA_SRC"])/"proptech_api"; f.test_vinculacion_de_desarrollo_solo_desde_ejemplo()'
2026-10-28T11:39:30.519547-03:00
AssertionError: ['proptech_core/complejos/aplicacion/ejemplo.py', 'proptech_api/sesion.py']
exit=1
```

## 5.3-acceso

```diff
import proptech_core.acceso.aplicacion.vinculacion_de_desarrollo
```

```text
cd backend && uv run python -c 'import os; from pathlib import Path; import tests.unitarios.test_fronteras_de_modulos as f; f.RAIZ_SRC=Path(os.environ["COPIA_SRC"])/"proptech_core"; f.RAIZ_API=Path(os.environ["COPIA_SRC"])/"proptech_api"; f.test_vinculacion_de_desarrollo_solo_desde_ejemplo()'
2026-10-28T11:39:30.729510-03:00
AssertionError: ['proptech_core/acceso/aplicacion/invitaciones.py', 'proptech_core/complejos/aplicacion/ejemplo.py']
exit=1
```
