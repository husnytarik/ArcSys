# map_data_loader.py
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

    project_id = get_active_project_id(cur)
    if project_id is None:
        con.close()
        raise RuntimeError("Aktif proje bulunamadı.")

    # Proje EPSG kodu
    cur.execute(
        """
        SELECT id, name, epsg_code
        FROM projects
        WHERE id = ?
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

    return con, cur, project_id, project_name, transformer


def _load_trenches(cur, transformer, project_id) -> List[Dict[str, Any]]:
    """
    Açmaları (trenches) ve köşe koordinatlarını yükler.
    """
    # Önce temel açma bilgileri
    cur.execute(
        """
        SELECT id, project_id, code, name, description
        FROM trenches
        WHERE project_id = ?
        ORDER BY id
        """,
        (project_id,),
    )
    trench_rows = cur.fetchall()

    # Köşeler
    cur.execute(
        """
        SELECT id, trench_id, corner_index,
               x_global, y_global
        FROM trench_vertices
        WHERE trench_id IN (
          SELECT id FROM trenches WHERE project_id = ?
        )
        ORDER BY trench_id, corner_index
        """,
        (project_id,),
    )
    vertex_rows = cur.fetchall()

    vertices_by_trench: Dict[int, List[Tuple[float, float]]] = {}
    for vid, trench_id, corner_idx, xg, yg in vertex_rows:
        if xg is None or yg is None:
            continue
        lon, lat = transformer.transform(xg, yg)
        vertices_by_trench.setdefault(trench_id, []).append((lat, lon))

    trenches: List[Dict[str, Any]] = []
    for tid, proj_id, code, name, desc in trench_rows:
        verts = vertices_by_trench.get(tid, [])
        trenches.append(
            {
                "id": tid,
                "project_id": proj_id,
                "code": code,
                "name": name,
                "description": desc,
                "vertices": [{"lat": lat, "lon": lon} for (lat, lon) in verts],
                "project": "",
            }
        )

    return trenches


def _load_finds(cur, transformer, project_id) -> List[Dict[str, Any]]:
    """Buluntuları (finds) yükler — found_at dahil."""
    cur.execute(
        """
        SELECT
          f.id,
          f.trench_id,
          f.code,
          f.description,
          f.found_at,
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
    rows = cur.fetchall()

    finds: List[Dict[str, Any]] = []

    for (
        fid,
        trench_id,
        code,
        desc,
        found_at,
        xg,
        yg,
        zg,
        level_id,
        level_name,
        trench_code,
        trench_name,
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

    for lid, name, layer_type, url_template, file_path, attribution in rows:
        if layer_type == "tile":
            if not url_template:
                continue
            layers.append(
                {
                    "id": lid,
                    "name": name,
                    "kind": "tile",
                    "url_template": url_template,
                    "attribution": attribution,
                }
            )
        elif layer_type == "image":
            if not file_path:
                continue
            abs_path = Path(base_dir) / file_path
            if not abs_path.exists():
                continue

            # GeoTIFF ya da worldfile’lı raster varsayımı;
            # burada sadece önceden üretilmiş PNG/JPG’yi kullanıyoruz.
            # Örneğin: rasters/.../image.png
            rel = os.path.relpath(abs_path, base_dir).replace("\\", "/")
            file_url = f"file:///{rel}"

            # bounds bilgisi map_layers’ta tutuluyorsa çek:
            cur.execute(
                """
                SELECT min_lat, min_lon, max_lat, max_lon
                FROM map_layer_bounds
                WHERE layer_id = ?
                """,
                (lid,),
            )
            b = cur.fetchone()
            if not b:
                continue
            min_lat, min_lon, max_lat, max_lon = b

            layers.append(
                {
                    "id": lid,
                    "name": name,
                    "kind": "image",
                    "file_url": file_url,
                    "min_lat": min_lat,
                    "min_lon": min_lon,
                    "max_lat": max_lat,
                    "max_lon": max_lon,
                    "attribution": attribution,
                }
            )

    return layers


def _load_vector_layers(cur, transformer, project_id):
    """
    vector_layers tablosundan yüklenir.
    GeoJSON / KML / GPKG / SHP gibi formatların önceden
    dönüştürülmüş WGS84 koordinatlı GeoJSON path'leri gönderilir.
    """
    cur.execute(
        """
        SELECT id, name, file_path, layer_type
        FROM vector_layers
        WHERE project_id = ?
        """,
        (project_id,),
    )
    rows = cur.fetchall()

    base_dir = os.path.dirname(DB_PATH)
    layers = []

    for lid, name, file_path, layer_type in rows:
        if not file_path:
            continue

        abs_path = Path(base_dir) / file_path
        if not abs_path.exists():
            continue

        # GeoJSON olarak okunacak
        rel = os.path.relpath(abs_path, base_dir).replace("\\", "/")
        file_url = f"file:///{rel}"

        layers.append(
            {
                "id": lid,
                "name": name,
                "kind": "vector",
                "file_url": file_url,
                "layer_type": layer_type,
            }
        )

    return layers


def load_all_map_data():
    """
    Harita için gerekli tüm verileri (açmalar, buluntular, katmanlar) yükler.
    """
    con = None
    center_lat = 0.0
    center_lon = 0.0

    try:
        con, cur, project_id, project_name, transformer = _get_project_and_transformer()

        trenches_data = _load_trenches(cur, transformer, project_id)
        finds_data = _load_finds(cur, transformer, project_id)
        layers_data = _load_map_layers(cur, transformer, project_id)
        vector_layers = _load_vector_layers(cur, transformer, project_id)
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

    return trenches_data, vector_layers, finds_data, layers_data, center_lat, center_lon
