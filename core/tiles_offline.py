# core/tiles_offline.py
from __future__ import annotations
import re
import math
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from pyproj import Transformer

from .db import get_connection, get_active_project_id
from .utils import TILES_DIR, ensure_dir


ProgressCallback = Callable[[int, int, str], None]
# step, total, message


def bbox_from_center(lat: float, lon: float, buffer_km: float):
    buffer_m = buffer_km * 1000.0
    dlat = buffer_m / 111000.0
    cos_lat = math.cos(math.radians(lat)) or 1e-6
    dlon = buffer_m / (111000.0 * cos_lat)
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon


def deg2num(lat_deg: float, lon_deg: float, zoom: int):
    lat_rad = math.radians(lat_deg)
    n = 2.0**zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int(
        (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi)
        / 2.0
        * n
    )
    return xtile, ytile


DEFAULT_ARCGIS_URL = (
    "https://services.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)


def download_osm_tiles_for_active_project(
    buffer_km: float,
    zoom_min: int,
    zoom_max: int,
    progress_cb=None,
    tile_template: str = DEFAULT_ARCGIS_URL,
    layer_name: str = "OSM Offline",
):
    """
    Aktif proje için, kazı merkezine buffer ekleyip verilen zoom aralığındaki
    tile'ları indirir ve map_layers tablosuna 'layer_name' ile kaydeder.

    progress_cb(step, total, message) şeklindedir.
    """
    if zoom_max < zoom_min:
        raise ValueError("zoom_max, zoom_min'den küçük olamaz.")

    con = get_connection()
    cur = con.cursor()

    project_id = get_active_project_id(con)
    if not project_id:
        con.close()
        raise RuntimeError("Aktif proje bulunamadı.")

    cur.execute(
        """
        SELECT p.center_x, p.center_y, cs.epsg_code, p.code
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
        raise RuntimeError("Proje kaydı bulunamadı.")

    center_x, center_y, epsg_code, project_code = row

    if center_x is None or center_y is None:
        con.close()
        raise RuntimeError(
            "Bu proje için center_x / center_y tanımlı değil.\n"
            "Lütfen veritabanında center_x, center_y değerlerini doldurun."
        )

    if not epsg_code:
        con.close()
        raise RuntimeError("Proje için EPSG kodu tanımlı değil.")

    # Proje CRS → WGS84 (lon, lat)
    src_crs = f"EPSG:{epsg_code}"
    transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
    center_lon, center_lat = transformer.transform(center_x, center_y)

    # Tek bir bbox: tüm zoom seviyelerinde aynı coğrafi alan kullanılacak
    lat_min, lat_max, lon_min, lon_max = bbox_from_center(
        center_lat, center_lon, buffer_km
    )

    # Katman adı slug + zoom etiketi → her kombinasyon için ayrı klasör
    safe_layer_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", layer_name).lower()
    zoom_suffix = f"z{zoom_min}_{zoom_max}"
    tiles_root = (
        TILES_DIR / f"project_{project_id}" / f"{safe_layer_slug}_{zoom_suffix}"
    )
    ensure_dir(tiles_root)

    # ---- Tile sayısını ve aralıkları hesapla ----
    total_tiles = 0
    zoom_ranges: list[tuple[int, int, int, int, int]] = []

    for z in range(zoom_min, zoom_max + 1):
        # Aynı bbox, her zoom için yeniden tile index'e çevriliyor
        x1, y1 = deg2num(lat_max, lon_min, z)
        x2, y2 = deg2num(lat_min, lon_max, z)
        x_min = min(x1, x2)
        x_max = max(x1, x2)
        y_min = min(y1, y2)
        y_max = max(y1, y2)
        zoom_ranges.append((z, x_min, x_max, y_min, y_max))
        total_tiles += (x_max - x_min + 1) * (y_max - y_min + 1)

    if total_tiles == 0:
        con.close()
        raise RuntimeError("Belirlenen alan için tile bulunamadı.")

    if progress_cb:
        progress_cb(0, total_tiles, "Offline tile indirme başlatılıyor...")

    # ---- İndirme döngüsü ----
    downloaded = 0

    for z, x_min, x_max, y_min, y_max in zoom_ranges:
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                msg = (
                    f"Tile indiriliyor: z={z}, x={x}, y={y} "
                    f"({downloaded + 1}/{total_tiles})"
                )

                if progress_cb:
                    progress_cb(downloaded, total_tiles, msg)

                z_dir = tiles_root / str(z)
                x_dir = z_dir / str(x)
                ensure_dir(x_dir)
                out_path = x_dir / f"{y}.png"

                if not out_path.exists():
                    url = tile_template.format(z=z, x=x, y=y)
                    try:
                        with urllib.request.urlopen(url, timeout=5) as resp:
                            if resp.status == 200:
                                data = resp.read()
                                out_path.write_bytes(data)
                    except Exception:
                        # Hata durumunda o tile'ı atla, süreci durdurma
                        pass

                downloaded += 1

                if progress_cb:
                    progress_cb(downloaded, total_tiles, msg)

    # ---- Layer kaydını güncelle / ekle ----
    tiles_root_uri = tiles_root.as_uri()
    url_template = tiles_root_uri + "/{z}/{x}/{y}.png"

    # Aynı proje + aynı isimde katman varsa güncelle, yoksa ekle
    cur.execute(
        """
        SELECT id FROM map_layers
        WHERE project_id = ? AND name = ?
        """,
        (project_id, layer_name),
    )
    row = cur.fetchone()

    if row:
        layer_id = row[0]
        cur.execute(
            """
            UPDATE map_layers
            SET type = 'tile',
                file_path = NULL,
                url_template = ?,
                attribution = '© OpenStreetMap katkıcıları (offline kopya)',
                is_active = 1
            WHERE id = ?
            """,
            (url_template, layer_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO map_layers
                (project_id, name, type, file_path, url_template, attribution, is_active)
            VALUES (?, ?, 'tile', NULL, ?, '© OpenStreetMap katkıcıları (offline kopya)', 1)
            """,
            (project_id, layer_name, url_template),
        )

    con.commit()
    con.close()
