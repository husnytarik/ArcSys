# core/geotiff.py

"""
GeoTIFF içe aktarma modülü (core).

Bu modül:
- Verilen GeoTIFF dosyasını proje için rasters/ altına kopyalar
- PNG + worldfile (.pgw) üretir
- PNG + worldfile'dan WGS84 bbox hesaplar (ileride lazım olabilir)
- map_layers tablosuna "image" katmanı olarak kaydeder

NOT: Burada HİÇBİR Qt / UI kodu yok. Dosya seçtirme gibi işler app tarafında yapılmalı.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable

from PIL import Image
from osgeo import gdal
from pyproj import Transformer

from core.utils import RASTERS_DIR, BASE_DIR, ensure_dir
from core.db import get_connection

ProgressCallback = Callable[[int, int, str], None]
# step, total, message


# -------------------------------------------------------------
# Yardımcı: GeoTIFF → PNG + worldfile üret
# -------------------------------------------------------------
def _export_png_and_worldfile(tiff_path: Path, out_png: Path, out_pgw: Path) -> None:
    """
    GDAL ile GeoTIFF içinden PNG üretir.
    Worldfile (.pgw) dosyasını da oluşturur.
    """
    ds = gdal.Open(str(tiff_path))
    if ds is None:
        raise RuntimeError(f"GeoTIFF açılamadı: {tiff_path}")

    # PNG export
    driver = gdal.GetDriverByName("PNG")
    driver.CreateCopy(str(out_png), ds, strict=0)

    # GeoTIFF’den worldfile bilgisi al
    gt = ds.GetGeoTransform()
    # gt: (originX, pixelWidth, rot1, originY, rot2, pixelHeight)
    # worldfile: A, D, B, E, C, F (basit senaryoda rot1=rot2=0)

    with out_pgw.open("w", encoding="utf-8") as f:
        f.write(f"{gt[1]}\n")  # pixel width (A)
        f.write(f"{gt[2]}\n")  # rot1 (D)
        f.write(f"{gt[4]}\n")  # rot2 (B)
        f.write(f"{gt[5]}\n")  # pixel height (E)
        f.write(f"{gt[0] + gt[1] / 2}\n")  # C (üst sol piksel merkez X)
        f.write(f"{gt[3] + gt[5] / 2}\n")  # F (üst sol piksel merkez Y)


# -------------------------------------------------------------
# GeoTIFF import ana fonksiyon (UI'siz)
# -------------------------------------------------------------
def import_geotiff_for_project(
    project_id: int,
    tiff_path: str | Path,
    progress_cb: Optional[ProgressCallback] = None,
) -> str:
    """
    Verilen proje için, verilen GeoTIFF dosyasını içe aktarır.

    - GeoTIFF → PNG + worldfile
    - Proje CRS'ine göre bbox hesabı
    - WGS84 bbox (şimdilik sadece hesaplanıyor, istenirse map_layers'a eklenebilir)
    - map_layers tablosuna 'image' katmanı eklenir

    Parametreler:
        project_id: Projenin ID'si
        tiff_path : GeoTIFF dosyasının tam yolu
        progress_cb: İsteğe bağlı callback (step, total, message)

    Dönüş:
        layer_name (png / layer ismi)
    """
    tiff_path = Path(tiff_path)
    if not tiff_path.exists():
        raise FileNotFoundError(f"GeoTIFF bulunamadı: {tiff_path}")

    total_steps = 4

    def emit(step: int, msg: str) -> None:
        if progress_cb:
            progress_cb(step, total_steps, msg)

    emit(0, "GeoTIFF işleniyor...")

    # --- Proje bilgilerini veritabanından çek ---
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            """
            SELECT p.code, cs.epsg_code
            FROM projects p
            JOIN coordinate_systems cs ON cs.id = p.coordinate_system_id
            WHERE p.id = ?
            """,
            (project_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Proje veya EPSG kodu bulunamadı.")

        project_code, epsg_code = row
        if not project_code:
            raise RuntimeError("Proje kodu tanımlı değil.")
        if not epsg_code:
            raise RuntimeError("EPSG kodu tanımlı değil.")

        # --- Proje klasörü ---
        project_raster_dir = RASTERS_DIR / project_code
        ensure_dir(project_raster_dir)

        # Çıktı dosya adları
        layer_name = tiff_path.stem
        out_png = project_raster_dir / f"{layer_name}.png"
        out_pgw = project_raster_dir / f"{layer_name}.pgw"

        # 1) PNG + worldfile üret
        emit(1, "PNG ve worldfile (.pgw) üretiliyor...")
        _export_png_and_worldfile(tiff_path, out_png, out_pgw)

        # PNG boyutları
        img = Image.open(out_png)
        width, height = img.size
        img.close()

        # Worldfile oku
        with out_pgw.open("r", encoding="utf-8") as f:
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

        # Proje CRS → WGS84 dönüşümü için transformer
        transformer = Transformer.from_crs(
            f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True
        )

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

        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        # Şimdilik bu bbox sadece hesaplanıyor, istenirse map_layers'a eklenebilir

        emit(3, "Veritabanına ortofoto katmanı ekleniyor...")

        # Veritabanına yaz (BASE_DIR'e göre relatif path)
        rel_path = os.path.relpath(out_png, BASE_DIR).replace("\\", "/")

        cur.execute(
            """
            INSERT INTO map_layers
                (project_id, name, type, file_path, url_template, attribution, is_active)
            VALUES
                (?, ?, 'image', ?, NULL, ?, 1)
            """,
            (
                project_id,
                layer_name,
                rel_path,
                "GeoTIFF kaynaklı raster",
            ),
        )

        con.commit()
    finally:
        con.close()

    emit(total_steps, "GeoTIFF ortofoto başarıyla eklendi.")
    return layer_name
