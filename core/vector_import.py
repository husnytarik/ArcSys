import json
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox
import geopandas as gpd

from core.db import insert_vector_layer


def import_vector_file(parent, project_id: int):
    """
    GeoJSON, Shapefile, GPKG, KML, DXF yükler.
    Geopandas bütün formatları otomatik çözer.
    """

    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Vektör Dosyası Seç",
        "",
        "Vektör Dosyaları (*.geojson *.json *.shp *.gpkg *.kml *.dxf)",
    )
    if not file_path:
        return None

    try:
        gdf = gpd.read_file(file_path)
    except Exception as e:
        QMessageBox.critical(parent, "Hata", f"Dosya okunamadı:\n{e}")
        return None

    # GeoJSON olarak saklayalım (Leaflet için en temiz format)
    geojson_data = gdf.to_json()

    layer_name = Path(file_path).stem

    # DB’ye kaydet
    layer_id = insert_vector_layer(
        project_id=project_id,
        name=layer_name,
        geojson=geojson_data,
    )

    return {"id": layer_id, "name": layer_name}
