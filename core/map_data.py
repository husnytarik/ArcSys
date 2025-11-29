# core/map_data.py
import os
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from pyproj import Transformer

from .db import get_connection, get_active_project_id
from .utils import BASE_DIR, DATA_DIR, WEB_DIR


@dataclass
class MapData:
    trenches: List[Dict[str, Any]]
    finds: List[Dict[str, Any]]
    layers: List[Dict[str, Any]]
    center_lat: float
    center_lon: float
    error_message: str


def load_map_data() -> MapData:
    """
    Veritabanından:
      - Açmalar (trenches + vertices)
      - Buluntular (finds)
      - map_layers (tile + image)
    okuyup Leaflet için hazır hale getirir.
    """
    center_lat = 37.0
    center_lon = 32.0

    trenches_data: List[Dict[str, Any]] = []
    finds_data: List[Dict[str, Any]] = []
    layers_data: List[Dict[str, Any]] = []
    error_js = ""

    con = None
    try:
        con = get_connection()
        cur = con.cursor()

        project_id = get_active_project_id(con)
        if not project_id:
            raise RuntimeError("Aktif proje bulunamadı.")

        # Proje + EPSG
        cur.execute(
            """
            SELECT p.id, p.name, cs.epsg_code
            FROM projects p
            LEFT JOIN coordinate_systems cs
              ON p.coordinate_system_id = cs.id
            WHERE p.id = ?
            """,
            (project_id,),
        )
        proj_row = cur.fetchone()
        if not proj_row:
            raise RuntimeError("Veritabanında proje bulunamadı.")

        project_id, project_name, epsg_code = proj_row
        if not epsg_code:
            raise RuntimeError(f"Proje '{project_name}' için EPSG kodu tanımlı değil.")

        src_crs = f"EPSG:{epsg_code}"
        transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)

        # --- Açmalar ---
        cur.execute(
            """
            SELECT t.id, t.code, t.name, p.name
            FROM trenches t
            JOIN projects p ON t.project_id = p.id
            WHERE t.project_id = ?
            ORDER BY t.id
            """,
            (project_id,),
        )
        trench_rows = cur.fetchall()
        trenches_by_id: Dict[int, Dict[str, Any]] = {}

        for tid, tcode, tname, pname in trench_rows:
            cur.execute(
                """
                SELECT order_index, x_global, y_global, z_global
                FROM trench_vertices
                WHERE trench_id = ?
                ORDER BY order_index
                """,
                (tid,),
            )
            verts = cur.fetchall()
            vertices_latlon = []
            for order_idx, xg, yg, zg in verts:
                if xg is None or yg is None:
                    continue
                lon, lat = transformer.transform(xg, yg)
                vertices_latlon.append(
                    {"order": order_idx, "lat": lat, "lon": lon, "z": zg}
                )

            if vertices_latlon:
                tdata = {
                    "id": tid,
                    "code": tcode,
                    "name": tname,
                    "project": pname,
                    "vertices": vertices_latlon,
                }
                trenches_data.append(tdata)
                trenches_by_id[tid] = tdata

        # --- Buluntular ---
        cur.execute(
            """
            SELECT
              f.id,
              f.trench_id,
              f.code,
              f.description,
              f.x_global,
              f.y_global,
              f.z_global,
              f.level_id,
              l.name AS level_name,
              t.code AS trench_code,
              t.name AS trench_name
            FROM finds f
            JOIN trenches t ON f.trench_id = t.id
            LEFT JOIN levels l ON f.level_id = l.id
            WHERE t.project_id = ?
            ORDER BY f.id
            """,
            (project_id,),
        )
        find_rows = cur.fetchall()

        for (
            fid,
            trench_id,
            code,
            desc,
            xg,
            yg,
            zg,
            level_id,
            level_name,
            trench_code,
            trench_name,
        ) in find_rows:
            if xg is None or yg is None:
                continue
            lon, lat = transformer.transform(xg, yg)
            finds_data.append(
                {
                    "id": fid,
                    "trench_id": trench_id,
                    "trench_code": trench_code,
                    "trench_name": trench_name,
                    "code": code,
                    "description": desc,
                    "lat": lat,
                    "lon": lon,
                    "z": zg,
                    "level_id": level_id,
                    "level_name": level_name,
                }
            )

        # --- Katmanlar (map_layers) ---
        cur.execute(
            """
            SELECT id, name, type, url_template, file_path, attribution
            FROM map_layers
            WHERE project_id = ?
              AND is_active = 1
            """,
            (project_id,),
        )
        layer_rows = cur.fetchall()

        for lid, lname, ltype, url_tmpl, file_path, attr in layer_rows:
            ltype = (ltype or "").lower()
            attr = attr or ""

            # URL tabanlı tile layer
            if url_tmpl and url_tmpl.strip():
                layers_data.append(
                    {
                        "id": lid,
                        "name": lname,
                        "kind": "tile",
                        "url_template": url_tmpl,
                        "file_url": "",
                        "attribution": attr,
                    }
                )
                continue

            # PNG/JPG + worldfile image layer
            if ltype == "image" and file_path:
                # file_path hem relatif hem absolute olabilir
                if os.path.isabs(file_path):
                    abs_image = file_path
                else:
                    abs_image = os.path.join(BASE_DIR, file_path)

                if not os.path.exists(abs_image):
                    continue

                # Görüntü boyutu
                try:
                    img = Image.open(abs_image)
                    width, height = img.size
                    img.close()
                except Exception:
                    continue

                # Worldfile yolu
                root, ext = os.path.splitext(abs_image)
                ext_low = ext.lower()
                if ext_low == ".png":
                    wf_path = root + ".pgw"
                elif ext_low in (".jpg", ".jpeg"):
                    wf_path = root + ".jgw"
                else:
                    wf_path = root + ".pgw"

                if not os.path.exists(wf_path):
                    continue

                # Worldfile oku
                try:
                    with open(wf_path, "r", encoding="utf-8") as wf:
                        vals = [float(line.strip()) for line in wf if line.strip()]
                    if len(vals) < 6:
                        continue
                    a, rot1, rot2, e, x_center_ul, y_center_ul = vals[:6]
                except Exception:
                    continue

                # Piksel köşe koordinatları (proje CRS'inde)
                x_min = x_center_ul - a / 2.0
                y_max = y_center_ul - e / 2.0
                x_max = x_min + width * a
                y_min = y_max + height * e

                corners_xy = [
                    (x_min, y_min),
                    (x_min, y_max),
                    (x_max, y_min),
                    (x_max, y_max),
                ]
                lons = []
                lats = []
                for x, y in corners_xy:
                    lon, lat = transformer.transform(x, y)
                    lons.append(lon)
                    lats.append(lat)

                min_lon = min(lons)
                max_lon = max(lons)
                min_lat = min(lats)
                max_lat = max(lats)

                # HTML'de kullanmak için: proje köküne göre relatif path
                rel_path = os.path.relpath(abs_image, WEB_DIR).replace("\\", "/")

                layers_data.append(
                    {
                        "id": lid,
                        "name": lname,
                        "kind": "image",
                        "url_template": "",
                        "file_url": rel_path,
                        "min_lat": min_lat,
                        "min_lon": min_lon,
                        "max_lat": max_lat,
                        "max_lon": max_lon,
                        "attribution": attr,
                    }
                )

        # Harita merkezini belirle
        if trenches_data and trenches_data[0]["vertices"]:
            center_lat = trenches_data[0]["vertices"][0]["lat"]
            center_lon = trenches_data[0]["vertices"][0]["lon"]
        elif finds_data:
            center_lat = finds_data[0]["lat"]
            center_lon = finds_data[0]["lon"]

    except Exception as e:
        error_js = str(e).replace('"', '\\"')
    finally:
        if con is not None:
            con.close()

    return MapData(
        trenches=trenches_data,
        finds=finds_data,
        layers=layers_data,
        center_lat=center_lat,
        center_lon=center_lon,
        error_message=error_js,
    )
