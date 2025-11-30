from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image
from pyproj import Transformer

from core.db import get_connection, get_active_project_id, DB_PATH


def _get_project_and_transformer():
    """
    Aktif projeyi ve projeye ait source CRS -> WGS84 dönüştürücüyü döndürür.
    """
    con = get_connection()
    cur = con.cursor()

    project_id = get_active_project_id()
    if not project_id:
        con.close()
        raise RuntimeError("Aktif proje bulunamadı.")

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
    row = cur.fetchone()
    if not row:
        con.close()
        raise RuntimeError("Veritabanında proje bulunamadı.")

    project_id, project_name, epsg_code = row

    if not epsg_code:
        con.close()
        raise RuntimeError(f"Proje '{project_name}' için EPSG kodu tanımlı değil.")

    src_crs = f"EPSG:{epsg_code}"
    transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)

    return con, transformer, project_id, project_name


def _load_trenches(
    cur, transformer, project_id
) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """
    Açmaları (trenches) ve köşe noktalarını yükler.
    """
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
    rows = cur.fetchall()

    trenches: List[Dict[str, Any]] = []
    trenches_by_id: Dict[int, Dict[str, Any]] = {}

    for tid, tcode, tname, pname in rows:
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
        vertices_latlon: List[Dict[str, Any]] = []

        for order_idx, xg, yg, zg in verts:
            if xg is None or yg is None:
                continue
            lon, lat = transformer.transform(xg, yg)
            vertices_latlon.append(
                {
                    "order": order_idx,
                    "lat": lat,
                    "lon": lon,
                    "z": zg,
                }
            )

        if vertices_latlon:
            tdata = {
                "id": tid,
                "code": tcode,
                "name": tname,
                "project": pname,
                "vertices": vertices_latlon,
            }
            trenches.append(tdata)
            trenches_by_id[tid] = tdata

    return trenches, trenches_by_id


def _load_finds(cur, transformer, project_id) -> List[Dict[str, Any]]:
    """
    Buluntuları (finds) yükler.
    """
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
          t.name AS trench_name,
          f.found_at AS found_at
        FROM finds f
        JOIN trenches t ON f.trench_id = t.id
        LEFT JOIN levels l ON f.level_id = l.id
        WHERE t.project_id = ?
        ORDER BY f.id
        """,
        (project_id,),
    )
    rows = cur.fetchall()

    finds: List[Dict[str, Any]] = []

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
        found_at,
    ) in rows:
        if xg is None or yg is None:
            continue
        lon, lat = transformer.transform(xg, yg)
        finds.append(
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
                "found_at": found_at,
            }
        )

    return finds


def _load_map_layers(cur, transformer, project_id) -> List[Dict[str, Any]]:
    """
    map_layers tablosundan hem URL tabanlı tile layer’ları
    hem de raster image layer’ları (GeoTIFF’ten üretilmiş PNG/JPG) çeker.
    """
    base_dir = os.path.dirname(DB_PATH)

    cur.execute(
        """
        SELECT id, name, type, url_template, file_path, attribution
        FROM map_layers
        WHERE project_id = ?
          AND is_active = 1
        """,
        (project_id,),
    )
    rows = cur.fetchall()

    layers: List[Dict[str, Any]] = []

    for lid, lname, ltype, url_tmpl, file_path, attr in rows:
        ltype = (ltype or "").lower()
        attr = attr or ""

        # URL Tabanlı Tile Layer
        if url_tmpl and url_tmpl.strip():
            layers.append(
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

        # Raster Image Layer (PNG/JPG + worldfile)
        if ltype == "image" and file_path:
            abs_image = os.path.abspath(os.path.join(base_dir, file_path))
            if not os.path.exists(abs_image):
                continue

            try:
                img = Image.open(abs_image)
                width, height = img.size
                img.close()
            except Exception:
                continue

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

            try:
                with open(wf_path, "r", encoding="utf-8") as wf:
                    vals = [float(line.strip()) for line in wf if line.strip()]
                if len(vals) < 6:
                    continue
                a, rot1, rot2, e, x_center_ul, y_center_ul = vals[:6]
            except Exception:
                continue

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

            # base_dir’e göre relatif path: rasters/.../image.png
            rel_image_path = os.path.relpath(abs_image, base_dir).replace("\\", "/")

            layers.append(
                {
                    "id": lid,
                    "name": lname,
                    "kind": "image",
                    "url_template": "",
                    "file_url": rel_image_path,
                    "min_lat": min_lat,
                    "min_lon": min_lon,
                    "max_lat": max_lat,
                    "max_lon": max_lon,
                    "attribution": attr,
                }
            )

    return layers


def load_map_data_for_project():
    """
    Harita için gerekli tüm verileri tek seferde döndürür.

    Returns:
        (
          trenches_data: List[dict],
          finds_data: List[dict],
          layers_data: List[dict],
          center_lat: float,
          center_lon: float,
        )
    """
    trenches_data: List[Dict[str, Any]] = []
    finds_data: List[Dict[str, Any]] = []
    layers_data: List[Dict[str, Any]] = []
    center_lat = 37.0
    center_lon = 32.0

    con = None
    try:
        con, transformer, project_id, project_name = _get_project_and_transformer()
        cur = con.cursor()

        trenches_data, trenches_by_id = _load_trenches(cur, transformer, project_id)
        finds_data = _load_finds(cur, transformer, project_id)
        layers_data = _load_map_layers(cur, transformer, project_id)

        # Merkez belirleme
        if trenches_data and trenches_data[0]["vertices"]:
            center_lat = trenches_data[0]["vertices"][0]["lat"]
            center_lon = trenches_data[0]["vertices"][0]["lon"]
        elif finds_data:
            center_lat = finds_data[0]["lat"]
            center_lon = finds_data[0]["lon"]

    finally:
        if con is not None:
            con.close()

    return trenches_data, finds_data, layers_data, center_lat, center_lon
