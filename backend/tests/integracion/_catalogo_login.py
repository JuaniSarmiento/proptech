"""Foto estructural completa del contrato 0019/0020, sin OIDs físicos (L-022)."""

from typing import Any

from ._edificios import BaseDeEdificio


def catalogo(base: BaseDeEdificio) -> dict[str, Any]:
    foto: dict[str, Any] = {}
    with base.conectar_migrador() as c:
        for tabla in ("persona", "accion_de_auditoria", "invitacion"):
            relacion = c.execute(
                "SELECT pg_get_userbyid(relowner),relkind,relpersistence,relrowsecurity,"
                "relforcerowsecurity,relreplident,reloptions FROM pg_class "
                "WHERE oid=to_regclass(%s)",
                ("public." + tabla,),
            ).fetchone()
            foto[tabla] = relacion
            if relacion is None:
                continue
            columnas = c.execute(
                "SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,"
                "a.attgenerated,co.collname,pg_get_expr(d.adbin,d.adrelid),a.attstorage,"
                "a.attcompression,a.attstattarget,a.attoptions,a.attacl::text "
                "FROM pg_attribute a LEFT JOIN pg_attrdef d "
                "ON d.adrelid=a.attrelid AND d.adnum=a.attnum "
                "LEFT JOIN pg_collation co ON co.oid=a.attcollation "
                "WHERE a.attrelid=%s::regclass AND a.attnum>0 AND NOT a.attisdropped "
                "ORDER BY a.attnum",
                (tabla,),
            ).fetchall()
            foto[f"{tabla}.orden_columnas"] = tuple(f[0] for f in columnas)
            for fila in columnas:
                foto[f"{tabla}.columna.{fila[0]}"] = fila[1:]
            for fila in c.execute(
                "SELECT conname,contype,condeferrable,condeferred,convalidated,connoinherit,"
                "pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid=%s::regclass",
                (tabla,),
            ):
                foto[f"{tabla}.restriccion.{fila[0]}"] = fila[1:]
            for fila in c.execute(
                "SELECT r.relname,pg_get_indexdef(i.indexrelid),i.indisunique,i.indisprimary,"
                "i.indisexclusion,i.indimmediate,i.indisclustered,i.indisvalid,i.indcheckxmin,"
                "i.indisready,i.indislive,i.indisreplident,r.reloptions,"
                "pg_get_userbyid(r.relowner) "
                "FROM pg_index i JOIN pg_class r ON r.oid=i.indexrelid "
                "WHERE i.indrelid=%s::regclass",
                (tabla,),
            ):
                foto[f"{tabla}.indice.{fila[0]}"] = fila[1:]
            for fila in c.execute(
                "SELECT CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,"
                "a.privilege_type,a.is_grantable,pg_get_userbyid(a.grantor) "
                "FROM pg_class c CROSS JOIN LATERAL "
                "aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a "
                "WHERE c.oid=%s::regclass",
                (tabla,),
            ):
                foto[f"{tabla}.permiso.{fila[0]}.{fila[1]}"] = fila[2:]
            for fila in c.execute(
                "SELECT tgname,pg_get_triggerdef(oid),tgenabled FROM pg_trigger "
                "WHERE tgrelid=%s::regclass AND NOT tgisinternal",
                (tabla,),
            ):
                foto[f"{tabla}.trigger.{fila[0]}"] = fila[1:]
        # Se comparan todas las políticas de public, no sólo las dos nuevas.
        for fila in c.execute(
            "SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check "
            "FROM pg_policies WHERE schemaname='public'"
        ):
            foto[f"politica.{fila[0]}.{fila[1]}.{fila[2]}"] = fila[3:]
        foto["vocabulario"] = tuple(
            f[0] for f in c.execute("SELECT nombre FROM accion_de_auditoria ORDER BY nombre")
        )
    return foto


def comparar(esperado: dict[str, Any], obtenido: dict[str, Any]) -> None:
    diferencias = sorted(
        clave
        for clave in esperado.keys() | obtenido.keys()
        if clave not in esperado or clave not in obtenido or esperado[clave] != obtenido[clave]
    )
    assert diferencias == [], "Catálogo distinto: " + ", ".join(diferencias)
