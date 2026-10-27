# Procedencia de `config/georef/`

**Fuente**: Georef, Servicio de Normalización de Datos Geográficos de Argentina
(https://datos.gob.ar/dataset/georef-argentina), API pública en
`https://apis.datos.gob.ar/georef/api/`.

**Fecha de descarga**: 26/10/2026.

**Licencia**: Creative Commons Atribución 4.0 Internacional (CC BY 4.0). Atribución: "Georef /
datos.gob.ar". El uso acá es la reducción a tres columnas (`id`, `nombre`, id del padre), nunca el
dataset completo de Georef (que incluye centroides, categoría, fuente, etc.).

**Qué hay en esta carpeta**:

- `provincias.json`: 24 jurisdicciones de primer nivel (23 provincias + CABA), cada una
  `{"id": ..., "nombre": ...}`.
- `departamentos.json`: 529 departamentos/partidos, cada uno
  `{"id": ..., "nombre": ..., "provincia_id": ...}`.
- `localidades.json`: 4037 localidades (BAHRA), cada una
  `{"id": ..., "nombre": ..., "departamento_id": ...}`.

**Comando exacto que regenera el dato** (`curl` + un script Python de una vez, que se arma y se
borra en la misma corrida — no queda versionado en el repositorio):

```bash
cd config/georef

curl -s "https://apis.datos.gob.ar/georef/api/provincias?campos=id,nombre&max=30&orden=nombre" \
  -o provincias_raw.json
curl -s "https://apis.datos.gob.ar/georef/api/departamentos?campos=id,nombre,provincia.id&max=1000&orden=nombre" \
  -o departamentos_raw.json
curl -s "https://apis.datos.gob.ar/georef/api/localidades?campos=id,nombre,departamento.id&max=5000&orden=nombre" \
  -o localidades_raw.json

python - <<'PY'
import json

with open("provincias_raw.json", encoding="utf-8") as f:
    provincias = sorted(
        ({"id": p["id"], "nombre": p["nombre"]} for p in json.load(f)["provincias"]),
        key=lambda p: p["nombre"],
    )
with open("provincias.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(provincias, f, ensure_ascii=False, separators=(",", ":"))

with open("departamentos_raw.json", encoding="utf-8") as f:
    departamentos = sorted(
        (
            {"id": d["id"], "nombre": d["nombre"], "provincia_id": d["provincia"]["id"]}
            for d in json.load(f)["departamentos"]
        ),
        key=lambda d: (d["provincia_id"], d["nombre"]),
    )
with open("departamentos.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(departamentos, f, ensure_ascii=False, separators=(",", ":"))

with open("localidades_raw.json", encoding="utf-8") as f:
    localidades = sorted(
        (
            {
                "id": loc["id"],
                "nombre": loc["nombre"],
                "departamento_id": loc["departamento"]["id"],
            }
            for loc in json.load(f)["localidades"]
        ),
        key=lambda loc: (loc["departamento_id"], loc["nombre"]),
    )
with open("localidades.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(localidades, f, ensure_ascii=False, separators=(",", ":"))
PY

rm provincias_raw.json departamentos_raw.json localidades_raw.json
```

**Nota de auditoría (26/10/2026)**: el escenario "Trío coherente" de `ubicacion-del-edificio` nombra
"la localidad Ciudad de Mendoza" como ejemplo ilustrativo; el registro real de Georef para la capital
de Mendoza (departamento Capital, id `50007`) se llama simplemente `"Mendoza"` (id `50007010`), no
"Ciudad de Mendoza" — Georef no usa ese nombre para ninguna localidad. Los tests de este change usan
el nombre real (`"Mendoza"`) para ese escenario; es la misma localidad que la spec describe, con el
nombre que el archivo de verdad trae.
