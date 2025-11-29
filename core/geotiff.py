# core/geotiff.py
"""
GeoTIFF içe aktarma modülü.

Bu modül:
- Kullanıcıya GeoTIFF seçtirir
- GeoTIFF'i rasters/ altına kopyalar
- PNG + worldfile (.pgw) üretir
- PNG + worldfile'dan WGS84 bbox hesaplar
- map_layers tablosuna "image" katmanı olarak kaydeder
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable

from PyQt6.QtWidgets import QFileDialog

from PIL import Image
from osgeo import gdal
from pyproj import Transformer

from core.utils import RASTERS_DIR, BASE_DIR, ensure_dir
from core.db import get_connection, get_active_project_id

ProgressCallback = Callable[[int, int, str], None]
# step, total, message


# -------------------------------------------------------------
# Yardımcı: GeoTIFF → PNG + worldfile üret
# -------------------------------------------------------------
def _export_png_and_worldfile(tiff_path: str, out_png: str, out_pgw: str) -> None:
    """
    GDAL ile GeoTIFF içinden PNG üretir.
    Worldfile (.pgw) dosyasını da oluşturur.
    """
    ds = gdal.Open(tiff_path)
    if ds is None:
        raise RuntimeError(f"GeoTIFF açılamadı: {tiff_path}")

    # PNG export
    driver = gdal.GetDriverByName("PNG")
    driver.CreateCopy(out_png, ds, strict=0)

    # GeoTIFF’den worldfile bilgisi al
    gt = ds.GetGeoTransform()
    # gt: (originX, pixelWidth, rot1, originY, rot2, pixelHeight)
    # worldfile: A, D, B, E, C, F (basit senaryoda rot1=rot2=0)

    with open(out_pgw, "w", encoding="utf-8") as f:
        f.write(f"{gt[1]}\n")  # pixel width (A)
        f.write(f"{gt[2]}\n")  # rot1 (D)
        f.write(f"{gt[4]}\n")  # rot2 (B)
        f.write(f"{gt[5]}\n")  # pixel height (E)
        f.write(f"{gt[0] + gt[1] / 2}\n")  # C (üst sol piksel merkez X)
        f.write(f"{gt[3] + gt[5] / 2}\n")  # F (üst sol piksel merkez Y)


# -------------------------------------------------------------
# GeoTIFF import ana fonksiyon
# -------------------------------------------------------------
def import_geotiff_for_project(
    project_code: str,
    progress_cb: Optional[ProgressCallback] = None,
) -> None:
    """
    Kullanıcıya GeoTIFF seçtirir, PNG + worldfile üretir ve map_layers tablosuna ekler.
    progress_cb(step, total, message) → alt loading bar için callback.
    """
    total_steps = 4

    def emit(step: int, msg: str):
        if progress_cb:
            progress_cb(step, total_steps, msg)

    # 0) Dosya seçtir
    tiff_file, _ = QFileDialog.getOpenFileName(
        None, "GeoTIFF Seç (.tif, .tiff)", "", "GeoTIFF (*.tif *.tiff)"
    )
    if not tiff_file:
        return

    emit(0, "GeoTIFF dosyası seçildi, hazırlanıyor...")

    # Proje klasörü
    project_raster_dir = RASTERS_DIR / project_code
    ensure_dir(project_raster_dir)

    # Çıktı dosya adları
    name = Path(tiff_file).stem
    out_png = project_raster_dir / f"{name}.png"
    out_pgw = project_raster_dir / f"{name}.pgw"

    # 1) PNG + worldfile üret
    emit(1, "PNG ve worldfile (.pgw) üretiliyor...")
    _export_png_and_worldfile(tiff_file, str(out_png), str(out_pgw))

    # PNG boyutları
    img = Image.open(out_png)
    width, height = img.size
    img.close()

    # Worldfile oku
    with open(out_pgw, "r", encoding="utf-8") as f:
        vals = [float(v.strip()) for v in f.readlines()]
    if len(vals) < 6:
        raise RuntimeError("Worldfile bozuk.")

    A, rot1, rot2, E, C, F = vals[:6]

    # Proje CRS'inde köşe koordinatlarını hesapla
    x_min = C - A / 2.0
    y_max = F - E / 2.0
    x_max = x_min + A * width
    y_min = y_max + E * height

    emit(2, "Koordinatlar hesaplanıyor...")

    # Aktif proje CRS → WGS84 dönüşümü için EPSG al
    con = get_connection()
    try:
        project_id = get_active_project_id(con)
        cur = con.cursor()
        cur.execute(
            """
            SELECT cs.epsg_code
            FROM projects p
            JOIN coordinate_systems cs ON cs.id = p.coordinate_system_id
            WHERE p.id = ?
            """,
            (project_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("EPSG kodu bulunamadı.")
        epsg = row[0]

        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)

        # 4 köşeyi WGS84'e çevir
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

        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        emit(3, "Veritabanına ortofoto katmanı ekleniyor...")

        # Veritabanına yaz (BASE_DIR'e göre relatif path)
        abs_png = out_png
        rel_path = os.path.relpath(abs_png, BASE_DIR).replace("\\", "/")

        cur.execute(
            """
            INSERT INTO map_layers
                (project_id, name, type, file_path, url_template, attribution, is_active)
            VALUES
                (?, ?, 'image', ?, NULL, ?, 1)
            """,
            (
                project_id,
                name,
                rel_path,
                "GeoTIFF kaynaklı raster",
            ),
        )

        con.commit()
    finally:
        con.close()

    emit(total_steps, "GeoTIFF ortofoto başarıyla eklendi.")
