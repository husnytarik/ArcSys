# core/services/map_layers_service.py

from __future__ import annotations

import os
from typing import Any, Dict, List

from PIL import Image
from pyproj import Transformer

from core.db import get_connection
from core.utils import BASE_DIR, WEB_DIR


def load_map_layers_for_project(
    project_id: int,
    transformer: Transformer,
) -> List[Dict[str, Any]]:
    """
    Verilen proje için map_layers içeriğini döner.

    Tile katmanlar:
        {
          "id": ...,
          "name": ...,
          "kind": "tile",
          "url_template": ...,
          "file_url": "",
          "attribution": ...,
        }

    Image katmanlar (PNG/JPG + worldfile):
        {
          "id": ...,
          "name": ...,
          "kind": "image",
          "url_template": "",
          "file_url": "<WEB_DIR'e göre relatif path>",
          "min_lat": ...,
          "min_lon": ...,
          "max_lat": ...,
          "max_lon": ...,
          "attribution": ...,
        }

    Vector katmanlar (GeoJSON):
        {
          "id": ...,
          "name": ...,
          "kind": "vector",
          "url_template": "",
          "file_url": "<WEB_DIR'e göre relatif path>",
          "attribution": ...,
        }
    """
    layers_data: List[Dict[str, Any]] = []

    con = get_connection()
    try:
        cur = con.cursor()
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

            # --------------------------------------------------
            # 1) URL tabanlı tile layer
            # --------------------------------------------------
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

            # --------------------------------------------------
            # 2) Raster image (PNG/JPG + worldfile)
            # --------------------------------------------------
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
                lons: list[float] = []
                lats: list[float] = []
                for x, y in corners_xy:
                    lon, lat = transformer.transform(x, y)
                    lons.append(lon)
                    lats.append(lat)

                min_lon = min(lons)
                max_lon = max(lons)
                min_lat = min(lats)
                max_lat = max(lats)

                # HTML'de kullanmak için: web/ klasörüne göre relatif path
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
                continue

            # --------------------------------------------------
            # 3) Vector layer (GeoJSON)
            # --------------------------------------------------
            if ltype == "vector" and file_path:
                # file_path relatif olabilir; BASE_DIR / file_path altında arıyoruz
                if os.path.isabs(file_path):
                    abs_vec = file_path
                else:
                    # Örn: "data/vectors/..." veya "vectors/..."
                    cand_paths = [
                        os.path.join(BASE_DIR, file_path),
                        os.path.join(BASE_DIR, "data", file_path),
                    ]
                    abs_vec = None
                    for p in cand_paths:
                        if os.path.exists(p):
                            abs_vec = p
                            break

                if not abs_vec or not os.path.exists(abs_vec):
                    continue

                # web köküne göre relatif path (QWebEngine fetch için)
                rel_path = os.path.relpath(abs_vec, WEB_DIR).replace("\\", "/")

                layers_data.append(
                    {
                        "id": lid,
                        "name": lname,
                        "kind": "vector",
                        "url_template": "",
                        "file_url": rel_path,
                        "attribution": attr,
                    }
                )
                continue

    finally:
        con.close()

    return layers_data
