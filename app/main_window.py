# app/main_window.py

import os
import sys
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QSplitter,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QSplashScreen,
)

from core.tiles_offline import download_osm_tiles_for_active_project
from .loading_bar import LoadingBarWidget
from core.geotiff import import_geotiff_for_project
from core.db import (
    DB_PATH,
    get_connection,
    get_active_project_id,
    set_active_project_id,
)
from app.tabs import ProjectDetailsTab, TrenchesTab, FindsTab, ReportsTab
from core.vector_import import import_vector_file
from app.map_panel import MapPanel
from core.theme import build_qt_stylesheet


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Project info ---
        self.current_project_id: Optional[int] = get_active_project_id()
        self.current_project_code: Optional[str] = self._load_project_code(
            self.current_project_id
        )

        self.setWindowTitle("ArcSys – Arkeolojik Kazı Yönetim Sistemi")
        self.resize(1400, 800)

        # --- Central layout ---
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.setCentralWidget(central)

        # --- Header bar ---
        header_text = "ArcSys – [Aktif Proje]"
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("SELECT name FROM projects ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            con.close()
            if row and row[0]:
                header_text = f"ArcSys – {row[0]}"
        except Exception:
            pass

        self.header_label = QLabel(header_text)
        self.header_label.setObjectName("HeaderLabel")

        self.top_bar = QWidget()
        self.top_bar.setObjectName("TopBar")

        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(8, 4, 8, 4)
        top_bar_layout.setSpacing(8)
        top_bar_layout.addWidget(self.header_label)
        top_bar_layout.addStretch()

        self.setStyleSheet(build_qt_stylesheet())
        central_layout.addWidget(self.top_bar)

        # --- Tab + Map splitter ---
        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.setObjectName("MainVerticalSplitter")
        central_layout.addWidget(vertical_splitter, stretch=1)

        # --- Map panel ---
        self.map_panel = MapPanel(self)

        # --- Tabs ---
        self.project_tab = ProjectDetailsTab()
        self.trenches_tab = TrenchesTab(self.map_panel)
        self.finds_tab = FindsTab(self.map_panel)
        self.reports_tab = ReportsTab()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.project_tab, "Proje Detayları")
        self.tabs.addTab(self.trenches_tab, "Açmalar")
        self.tabs.addTab(self.finds_tab, "Buluntular")
        self.tabs.addTab(self.reports_tab, "Raporlar")

        vertical_splitter.addWidget(self.tabs)
        vertical_splitter.addWidget(self.map_panel)
        vertical_splitter.setStretchFactor(0, 3)
        vertical_splitter.setStretchFactor(1, 2)

        # --- Project change: refresh tabs + map ---
        self.project_tab.projectChanged.connect(self.on_project_changed)

        # --- Loading bar ---
        self._setup_loading_bar()
        self.showMaximized()

    # --- Offline tile download ---
    def download_offline_tiles_ui(self):
        sources = {
            "ArcGIS World Imagery": (
                "https://services.arcgisonline.com/ArcGIS/rest/services/"
                "World_Imagery/MapServer/tile/{z}/{y}/{x}"
            ),
            "OpenStreetMap (Standart)": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "OpenTopoMap": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
            "Carto Light": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
            "Carto Dark": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
        }

        source_names = list(sources.keys())
        source_name, ok = QInputDialog.getItem(
            self, "Kaynak Seç", "Tile kaynağı:", source_names, 0, False
        )
        if not ok:
            return

        tile_template = sources[source_name]
        layer_name = f"{source_name} (Offline)"

        buffer_km, ok = QInputDialog.getDouble(
            self, "Buffer (km)", "Buffer değeri (km):", 0.2, 0.0, 1000.0, 2
        )
        if not ok:
            return

        min_zoom, ok = QInputDialog.getInt(self, "Min Zoom", "Minimum zoom:", 12, 0, 22)
        if not ok:
            return

        max_zoom, ok = QInputDialog.getInt(
            self, "Max Zoom", "Maksimum zoom:", 18, 0, 22
        )
        if not ok or max_zoom < min_zoom:
            QMessageBox.warning(self, "Hata", "Zoom aralığı hatalı.")
            return

        self.show_loading(
            f"Offline tile indiriliyor (zoom {min_zoom}–{max_zoom})...",
            indeterminate=False,
        )

        def progress_cb(step: int, total: int, message: str):
            if total <= 0:
                total = 1
            self.loading_bar.set_message(message)
            self.set_loading_progress(step, maximum=total)
            QCoreApplication.processEvents()

        try:
            download_osm_tiles_for_active_project(
                buffer_km=buffer_km,
                zoom_min=min_zoom,
                zoom_max=max_zoom,
                progress_cb=progress_cb,
                tile_template=tile_template,
                layer_name=layer_name,
            )
        except Exception as exc:
            self.hide_loading()
            QMessageBox.critical(self, "Hata", f"Offline indirme hatası:\n{exc}")
            return

        self.hide_loading()
        QMessageBox.information(
            self, "Tamamlandı", f"Offline tile indirildi.\nKatman: {layer_name}"
        )
        self.map_panel.refresh_map()

    # --- Raster import ---
    def import_geotiff_orthophoto(self):
        """Aktif proje için GeoTIFF ortofoto içe aktarır ve alt bardan takip eder."""
        if not self.current_project_code:
            QMessageBox.warning(
                self,
                "Proje Seçilmedi",
                "Önce bir proje seçmelisiniz.",
            )
            return

        # Alt loading bar – yüzdeyle çalışsın
        self.show_loading("GeoTIFF içe aktarılıyor.", indeterminate=False)

        def progress_cb(step: int, total: int, message: str):
            if total <= 0:
                total = 1
            if hasattr(self, "loading_bar"):
                self.loading_bar.set_message(message)
            self.set_loading_progress(step, maximum=total)
            QCoreApplication.processEvents()

        try:
            import_geotiff_for_project(
                self.current_project_code,
                progress_cb=progress_cb,
            )
        except Exception as exc:
            self.hide_loading()
            QMessageBox.critical(
                self,
                "GeoTIFF Hatası",
                f"GeoTIFF içe aktarılırken hata oluştu:\n{exc}",
            )
            return

        self.hide_loading()
        QMessageBox.information(
            self,
            "Tamamlandı",
            "GeoTIFF ortofoto içe aktarıldı ve katmanlar listesine eklendi.",
        )

        # Haritayı yenile ki sağ üstte yeni katman görünsün
        self.map_panel.refresh_map()

    # --- Vector import ---

    def import_vector_layer(self):
        """
        Aktif proje için vektör katmanı (GPKG / SHP / KML / DXF / GeoJSON) içe aktarır.

        core.vector_import.import_vector_file fonksiyonunu çağırır;
        o fonksiyon dosya seçimini, okuma ve DB'ye kaydetmeyi kendi içinde yapar.
        """
        # 1) Proje kontrolü
        project_id = self.current_project_id
        if not project_id:
            QMessageBox.warning(
                self,
                "Proje Seçilmedi",
                "Önce bir proje seçmelisiniz.",
            )
            return

        # 2) Loading bar göster
        self.show_loading("Vektör katman içe aktarılıyor...", indeterminate=True)

        try:
            # core/vector_import.py içindeki fonksiyon:
            # def import_vector_file(parent, project_id: int)
            result = import_vector_file(self, project_id)
        except Exception as exc:
            self.hide_loading()
            QMessageBox.critical(
                self,
                "Vektör İçe Aktarma Hatası",
                f"Vektör içe aktarılırken hata oluştu:\n{exc}",
            )
            return

        # 3) İş bitti
        self.hide_loading()

        if not result:
            # Kullanıcı dosya seçmediyse vs.
            return

        QMessageBox.information(
            self,
            "Tamamlandı",
            f"Vektör katmanı içe aktarıldı: {result['name']}",
        )

        # Haritayı yenile → sağdaki layer listesine + Leaflet haritasına yansısın
        self.map_panel.refresh_map()

    # --- Current project lookup ---
    def get_current_project(self):
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None

        data = self.project_combo.itemData(idx)
        if isinstance(data, int):
            return data

        name = self.project_combo.currentText()
        con = get_connection()
        cur = con.cursor()
        cur.execute("SELECT id FROM projects WHERE name=?", (name,))
        row = cur.fetchone()
        con.close()
        return row[0] if row else None

    # --- Project changed ---
    def on_project_changed(self, project_id: int):
        set_active_project_id(project_id)
        self.current_project_id = project_id
        self.current_project_code = self._load_project_code(project_id)

        self.trenches_tab.load_trenches()
        self.finds_tab.load_finds()
        self.map_panel.refresh_map()

    # --- Loading bar setup ---
    def _setup_loading_bar(self):
        if not self.statusBar():
            self.setStatusBar(QStatusBar(self))

        self.loading_bar = LoadingBarWidget(self)
        self.statusBar().addPermanentWidget(self.loading_bar, 1)
        self.loading_bar.hide()
        self.statusBar().setSizeGripEnabled(False)

    # --- Loading bar controls ---
    def show_loading(
        self, message: str = "Yükleniyor...", *, indeterminate: bool = True
    ):
        if not hasattr(self, "loading_bar"):
            return

        self.loading_bar.set_message(message)
        if indeterminate:
            self.loading_bar.set_range(0, 0)
            self.loading_bar.set_value(0)
        else:
            self.loading_bar.set_range(0, 100)
            self.loading_bar.set_value(0)

        self.loading_bar.show()
        self.statusBar().show()

    def set_loading_progress(self, value: int, maximum: int | None = None):
        if maximum is not None:
            self.loading_bar.set_range(0, maximum)
        self.loading_bar.set_value(value)

    def hide_loading(self):
        if hasattr(self, "loading_bar"):
            self.loading_bar.hide()

    # --- Project code loader ---
    def _load_project_code(self, project_id: int | None) -> str | None:
        if not project_id:
            return None
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("SELECT code FROM projects WHERE id = ?", (project_id,))
            row = cur.fetchone()
            con.close()
            return row[0] if row else None
        except Exception:
            return None


# --- Application creation (run.py entrypoint) ---
def create_app():
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

    if not os.path.exists(DB_PATH):
        QMessageBox.critical(
            None, "Veritabanı Yok", f"ArcSys.db bulunamadı:\n{DB_PATH}"
        )
        return None, None

    app = QApplication(sys.argv)

    base_dir = Path(__file__).resolve().parent.parent
    icon_path = base_dir / "assets" / "logo" / "logo_1024.png"

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash = None
    if icon_path.exists():
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                320,
                320,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            splash = QSplashScreen(pixmap)
            splash.show()
            app.processEvents()

    window = MainWindow()

    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))

    window.show()

    if splash:
        time.sleep(0.5)
        splash.finish(window)

    return app, window
