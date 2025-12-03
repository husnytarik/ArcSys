# app/ui_actions.py

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QInputDialog,
)

from core.geotiff import import_geotiff_for_project
from core.vector_import import import_vector_file
from core.tiles_offline import download_osm_tiles_for_active_project

if TYPE_CHECKING:
    from app.main_window import MainWindow


# ----------------------------------------------------------------------
# GeoTIFF içe aktarma
# ----------------------------------------------------------------------
def action_import_geotiff(window: "MainWindow") -> None:
    project_id = window.current_project_id
    if not project_id:
        QMessageBox.warning(window, "Proje Yok", "Önce bir proje seçmelisiniz.")
        return

    file_path, _ = QFileDialog.getOpenFileName(
        window,
        "GeoTIFF Seç",
        "",
        "GeoTIFF (*.tif *.tiff)",
    )
    if not file_path:
        return

    file_path = Path(file_path)

    # Status bar'da loading barı göster
    window.show_loading("GeoTIFF içe aktarılıyor...")

    def progress_cb(step: int, total: int, message: str) -> None:
        window.update_loading(step, total, message)

    try:
        layer_name = import_geotiff_for_project(
            project_id=project_id,
            tiff_path=file_path,
            progress_cb=progress_cb,
        )
    except Exception as e:
        window.hide_loading()
        QMessageBox.critical(
            window,
            "GeoTIFF Hatası",
            f"GeoTIFF içe aktarılırken hata oluştu:\n{e}",
        )
        return

    window.hide_loading()
    window.show_message(f"GeoTIFF içe aktarıldı: {layer_name}")
    window.map_panel.refresh_map()


# ----------------------------------------------------------------------
# Vektör katman içe aktarma
# ----------------------------------------------------------------------
def action_import_vector(window: "MainWindow") -> None:
    project_id = window.current_project_id
    if not project_id:
        QMessageBox.warning(window, "Proje Yok", "Önce bir proje seçmelisiniz.")
        return

    file_path, _ = QFileDialog.getOpenFileName(
        window,
        "Vektör Katman Seç",
        "",
        "Vektör Verileri (*.gpkg *.geojson *.json *.shp *.kml *.dxf)",
    )
    if not file_path:
        return

    file_path = Path(file_path)

    window.show_loading("Vektör katmanı içe aktarılıyor...")

    try:
        result = import_vector_file(project_id=project_id, file_path=file_path)
    except Exception as e:
        window.hide_loading()
        QMessageBox.critical(
            window,
            "Vektör İçe Aktarma Hatası",
            f"Vektör içe aktarılırken hata oluştu:\n{e}",
        )
        return

    window.hide_loading()
    layer_name = result.get("name", file_path.stem)
    window.show_message(f"Vektör katmanı içe aktarıldı: {layer_name}")
    window.map_panel.refresh_map()


# ----------------------------------------------------------------------
# Offline tile indirme
# ----------------------------------------------------------------------
def action_download_tiles(window: "MainWindow") -> None:
    project_id = window.current_project_id
    if not project_id:
        QMessageBox.warning(window, "Proje Yok", "Önce bir proje seçmelisiniz.")
        return

    sources = {
        "ArcGIS World Imagery": (
            "https://services.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        "OpenStreetMap (Standart)": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "OpenTopoMap": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
        "Carto Light": (
            "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
        ),
        "Carto Dark": (
            "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
        ),
    }

    source_names = list(sources.keys())
    source_name, ok = QInputDialog.getItem(
        window, "Kaynak Seç", "Tile kaynağı:", source_names, 0, False
    )
    if not ok or not source_name:
        return

    tile_template = sources[source_name]
    layer_name = f"{source_name} (Offline)"

    buffer_km, ok = QInputDialog.getDouble(
        window, "Buffer (km)", "Buffer değeri (km):", 0.2, 0.0, 1000.0, 2
    )
    if not ok:
        return

    min_zoom, ok = QInputDialog.getInt(window, "Min Zoom", "Minimum zoom:", 12, 0, 22)
    if not ok:
        return

    max_zoom, ok = QInputDialog.getInt(window, "Max Zoom", "Maksimum zoom:", 18, 0, 22)
    if not ok or max_zoom < min_zoom:
        QMessageBox.warning(window, "Hata", "Zoom aralığı hatalı.")
        return

    window.show_loading("Offline tile indiriliyor...")

    def progress_cb(step: int, total: int, message: str) -> None:
        window.update_loading(step, total, message)

    try:
        download_osm_tiles_for_active_project(
            buffer_km=buffer_km,
            zoom_min=min_zoom,
            zoom_max=max_zoom,
            progress_cb=progress_cb,
            tile_template=tile_template,
            layer_name=layer_name,
        )
    except Exception as e:
        window.hide_loading()
        QMessageBox.critical(
            window,
            "Offline Tile Hatası",
            f"Offline tile indirirken hata oluştu:\n{e}",
        )
        return

    window.hide_loading()
    window.show_message(f"Offline tile indirildi: {layer_name}")
    window.map_panel.refresh_map()
