# app/main_window.py
import os
from typing import Optional
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QVBoxLayout,
    QTabWidget,
    QSplitter,
    QStatusBar,
    QMessageBox,
    QInputDialog,
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
from app.map_panel import MapPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Aktif proje bilgisi ---
        self.current_project_id: Optional[int] = get_active_project_id()
        self.current_project_code: Optional[str] = self._load_project_code(
            self.current_project_id
        )

        self.setWindowTitle("ArcSys – Arkeolojik Kazı Yönetim Sistemi")
        self.resize(1400, 800)

        # ---------------------------
        # Merkez widget ve layout
        # ---------------------------
        central = QWidget()
        central_layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Üst bar: aktif proje adı (varsa)
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
            # DB yoksa / erişilemezse sessiz geç, başlık generic kalsın
            pass

        self.header_label = QLabel(header_text)
        self.header_label.setStyleSheet(
            """
            QLabel {
                background-color: #333333;
                color: #f0f0f0;
                padding: 8px 12px;
                font-size: 16px;
                font-weight: bold;
            }
            """
        )
        central_layout.addWidget(self.header_label)

        # Üstte sekmeler, altta harita olacak şekilde dikey splitter
        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        central_layout.addWidget(vertical_splitter, stretch=1)

        # Alt harita paneli
        self.map_panel = MapPanel(self)

        # Sekmeler
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

        # Proje değişince diğerlerini güncelle
        self.project_tab.projectChanged.connect(self.on_project_changed)

        # ALTTAKİ LOADING BAR'I BAŞTAN OLUŞTUR
        self._setup_loading_bar()

    def download_offline_tiles_ui(self):
        """Kazı merkezi etrafında buffer + min/max zoom ile offline tile indirir."""

        # 0) Kaynak seçimi
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
            self,
            "Kaynak Seç",
            "Hangi tile kaynağından indirilsin?",
            source_names,
            0,
            False,
        )
        if not ok:
            return

        tile_template = sources[source_name]
        layer_name = f"{source_name} (Offline)"

        # 1) Buffer (km)
        buffer_km, ok = QInputDialog.getDouble(
            self,
            "Buffer (km)",
            "Kazı alanı etrafında ne kadar buffer kullanılsın? (km)",
            0.2,
            0.0,
            1000.0,
            2,
        )
        if not ok:
            return

        # 2) Min zoom
        min_zoom, ok = QInputDialog.getInt(
            self,
            "Min Zoom",
            "Minimum zoom seviyesi:",
            12,
            0,
            22,
        )
        if not ok:
            return

        # 3) Max zoom
        max_zoom, ok = QInputDialog.getInt(
            self,
            "Max Zoom",
            "Maksimum zoom seviyesi:",
            18,
            0,
            22,
        )
        if not ok:
            return

        if max_zoom < min_zoom:
            QMessageBox.warning(
                self,
                "Zoom Hatası",
                "Maksimum zoom, minimum zoom'dan küçük olamaz.",
            )
            return

        # 4) Alt loading bar'ı başlat
        self.show_loading(
            f"Offline tile indiriliyor (zoom {min_zoom}–{max_zoom})...",
            indeterminate=False,
        )

        def progress_cb(step: int, total: int, message: str):
            if total <= 0:
                total = 1
            if hasattr(self, "loading_bar"):
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
            QMessageBox.critical(
                self,
                "İndirme Hatası",
                f"Offline tile indirilirken hata oluştu:\n{exc}",
            )
            return

        self.hide_loading()
        QMessageBox.information(
            self,
            "Tamamlandı",
            f"Offline tile indirme tamamlandı.\n\nKatman adı: {layer_name}",
        )

        # Haritayı yenile ki sağ üstte layer listesine yansısın
        self.map_panel.refresh_map()

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
        self.show_loading("GeoTIFF içe aktarılıyor...", indeterminate=False)

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

    # ------------------------------------
    # Proje değiştiğinde sekmeleri / haritayı yenile
    # ------------------------------------
    def on_project_changed(self, project_id: int):
        set_active_project_id(project_id)
        self.current_project_id = project_id
        self.current_project_code = self._load_project_code(project_id)

        # Sekmeler ve harita yenilensin
        self.trenches_tab.load_trenches()
        self.finds_tab.load_finds()
        self.map_panel.load_embedded_leaflet_map()

    def _setup_loading_bar(self):
        """En altta, sadece gerektiğinde görünen ince loading bar oluşturur."""
        # Status bar yoksa oluştur
        if not self.statusBar():
            self.setStatusBar(QStatusBar(self))

        self.loading_bar = LoadingBarWidget(self)
        # Permanent widget olarak en alta yerleştiriyoruz
        self.statusBar().addPermanentWidget(self.loading_bar, 1)
        self.loading_bar.hide()

        # Rahatsız etmesin diye status bar'ı da ince tutabiliriz
        self.statusBar().setSizeGripEnabled(False)

    # --- Loading bar kontrol metotları ---

    def show_loading(
        self, message: str = "Veriler yükleniyor...", *, indeterminate: bool = True
    ):
        """Loading bar'ı gösterir.

        indeterminate=True ise sonsuz (busy) modda çalışır.
        """
        if not hasattr(self, "loading_bar"):
            return

        self.loading_bar.set_message(message)

        if indeterminate:
            # 0,0 → Qt'de 'belirsiz' anlamına gelir (marquee tarzı animasyon)
            self.loading_bar.set_range(0, 0)
            self.loading_bar.set_value(0)
        else:
            self.loading_bar.set_range(0, 100)
            self.loading_bar.set_value(0)

        self.loading_bar.show()
        self.statusBar().show()  # emin olalım

    def set_loading_progress(self, value: int, maximum: int | None = None):
        """Yüzde bazlı ilerleme günceller (indeterminate modda kullanma)."""
        if not hasattr(self, "loading_bar"):
            return

        if maximum is not None:
            self.loading_bar.set_range(0, maximum)

        self.loading_bar.set_value(value)

    def hide_loading(self):
        """İşlem bittiğinde loading bar'ı gizler."""
        if not hasattr(self, "loading_bar"):
            return

        self.loading_bar.hide()

    def _load_project_code(self, project_id: int | None) -> str | None:
        """Verilen project_id için projects.code döner; yoksa None."""
        if not project_id:
            return None
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute("SELECT code FROM projects WHERE id = ?", (project_id,))
            row = cur.fetchone()
            con.close()
            if row and row[0]:
                return row[0]
        except Exception:
            pass
        return None


def create_app():
    """
    run.py için yardımcı: QApplication + MainWindow oluşturur.
    """
    # GPU uyarılarını azaltmak için yazılımsal OpenGL
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

    if not os.path.exists(DB_PATH):
        QMessageBox.critical(
            None,
            "Veritabanı bulunamadı",
            f"ArcSys.db dosyası şu klasörde bulunamadı:\n{DB_PATH}",
        )
        return None, None

        # Eğer DB yoksa Qt uygulaması oluşturulmadan çıkılır
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app, window
