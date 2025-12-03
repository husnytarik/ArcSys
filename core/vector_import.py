# core/vector_import.py

import re
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox
import geopandas as gpd

from core.db import execute_and_get_id
from core.utils import DATA_DIR, ensure_dir


def _slugify(name: str) -> str:
    """Dosya adını güvenli hale getir (Türkçe / boşluk vs. temizlenir)."""
    s = re.sub(r"[^0-9A-Za-z_-]+", "_", name).strip("_")
    return s or "layer"


def import_vector_file(parent, project_id: int):
    """
    GeoJSON, Shapefile, GPKG, KML, DXF yükler.
    Geopandas bu formatların hepsini okuyabilir.

    Artık çıktı:
      - data/vectors altına .geojson
      - map_layers tablosuna type='vector' kaydı
    """
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Vektör Katman Seç",
        "",
        "Vektör Verileri (*.gpkg *.geojson *.json *.shp *.kml *.dxf)",
    )
    if not file_path:
        return None

    try:
        gdf = gpd.read_file(file_path)

        # CRS'i WGS84'e çevir
        if gdf.crs is not None:
            gdf = gdf.to_crs("EPSG:4326")
        else:
            # CRS yoksa WGS84 varsay
            gdf.set_crs("EPSG:4326", inplace=True)

        # Hedef klasör: data/vectors
        vectors_dir = DATA_DIR / "vectors"
        ensure_dir(vectors_dir)

        # Dosya adı
        original_name = Path(file_path).stem
        slug = _slugify(original_name)
        out_name = f"proj{project_id}_{slug}.geojson"
        out_path = vectors_dir / out_name

        # GeoJSON olarak yaz
        gdf.to_file(out_path, driver="GeoJSON")

        # DATA_DIR'e göre göreli path (örn: "vectors/proj1_abc.geojson")
        rel_path = out_path.relative_to(DATA_DIR).as_posix()

        # 🟢 map_layers tablosuna type='vector' kaydı ekle
        layer_id = execute_and_get_id(
            """
            INSERT INTO map_layers (project_id, name, type, file_path, is_active)
            VALUES (?, ?, 'vector', ?, 1)
            """,
            (project_id, original_name, rel_path),
        )

        return {"id": layer_id, "name": original_name}

    except Exception as e:
        QMessageBox.critical(
            parent,
            "Vektör İçe Aktarma Hatası",
            f"Vektör içe aktarılırken hata oluştu:\n{e}",
        )
        return None
