# app/main_window.py

from typing import Optional

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtWidgets import (
    QMainWindow,
    QLabel,
    QStatusBar,
    QSplitter,
    QTabWidget,
    QMessageBox,
)

from app.tabs import ProjectDetailsTab, TrenchesTab, FindsTab, ReportsTab
from app.map_panel import MapPanel
from app.loading_bar import LoadingBarWidget
from core.theme import build_qt_stylesheet
from core.vector_import import import_vector_file


class MainWindow(QMainWindow):
    """
    ArcSys ana penceresi
    - Üst: Tabs (projeler, açmalar, buluntular, raporlar)
    - Alt: MapPanel (solda katman ağacı, sağda harita)
    - En alt: StatusBar (solda proje, ortada loading bar, sağda mesaj + koordinat)
    """

    def __init__(self):
        super().__init__()

        # Uygulama durumu (sadece UI tarafında tutuluyor)
        self.current_project_id: Optional[int] = None
        self.current_project_code: Optional[str] = None

        # Pencere ayarları
        self._init_window()
        self._init_central_widgets()
        self._init_statusbar()
        self._apply_theme()

        # Sinyaller & ilk proje durumunu bağla
        self._connect_signals()
        self._init_state_from_project_tab()

        self.showMaximized()

    # --------------------------------------
    # VEKTÖR KATMAN İÇE AKTARMA
    # --------------------------------------
    def import_vector_layer(self):
        """
        Aktif proje için vektör katmanı (GPKG / SHP / KML / DXF / GeoJSON) içe aktarır.
        core.vector_import.import_vector_file fonksiyonunu kullanır.
        """
        project_id = self.current_project_id
        if not project_id:
            QMessageBox.warning(
                self,
                "Proje Seçilmedi",
                "Önce bir proje seçmelisiniz.",
            )
            return

        # İsteğe bağlı loading bar
        if hasattr(self, "show_loading"):
            self.show_loading("Vektör katmanı içe aktarılıyor...")

        try:
            # core/vector_import.py --> def import_vector_file(parent, project_id: int)
            result = import_vector_file(self, project_id)
        except Exception as exc:
            if hasattr(self, "hide_loading"):
                self.hide_loading()
            QMessageBox.critical(
                self,
                "Vektör İçe Aktarma Hatası",
                f"Vektör içe aktarılırken hata oluştu:\n{exc}",
            )
            return

        if hasattr(self, "hide_loading"):
            self.hide_loading()

        if not result:
            # Kullanıcı dosya seçmediyse veya işlem iptal olduysa
            return

        QMessageBox.information(
            self,
            "Tamamlandı",
            f"Vektör katmanı içe aktarıldı: {result['name']}",
        )

        # Haritayı yenile
        if hasattr(self, "map_panel"):
            # Bizde fonksiyon adı refresh_map
            self.map_panel.refresh_map()

    # ---------- Pencere Ayarları ----------

    def _init_window(self):
        self.setWindowTitle("ArcSys – Arkeolojik Kazı Yönetim Sistemi")
        self.resize(1400, 800)

    # ---------- Merkez Düzen ----------

    def _init_central_widgets(self):
        # Önce harita panelini oluştur (bazı tab'lar buna ihtiyaç duyuyor)
        self.map_panel = MapPanel(self)

        # Sekmeler
        self.tabs = QTabWidget()

        self.project_tab = ProjectDetailsTab()
        self.trenches_tab = TrenchesTab(self.map_panel)
        self.finds_tab = FindsTab(self.map_panel)
        self.reports_tab = ReportsTab()

        self.tabs.addTab(self.project_tab, "Proje")
        self.tabs.addTab(self.trenches_tab, "Açmalar")
        self.tabs.addTab(self.finds_tab, "Buluntular")
        self.tabs.addTab(self.reports_tab, "Raporlar")

        # Dikey splitter: ÜSTTE tabs, ALTA harita paneli
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.map_panel)

        # Haritaya daha çok alan vermek için oran
        splitter.setStretchFactor(0, 0)  # tablar
        splitter.setStretchFactor(1, 1)  # harita

        self.setCentralWidget(splitter)

    # ---------- Status Bar ----------

    def _init_statusbar(self):
        status = QStatusBar(self)

        self.lbl_project = QLabel("Proje: yok")
        self.loading_bar = LoadingBarWidget(self)
        self.lbl_message = QLabel("")
        self.lbl_coords = QLabel("")

        # Solda: proje (stretch)
        status.addWidget(self.lbl_project, 1)

        # Ortada: loading bar (başlangıçta gizli)
        status.addPermanentWidget(self.loading_bar)
        self.loading_bar.hide()

        # Sağda: mesaj + koordinat
        status.addPermanentWidget(self.lbl_message)
        status.addPermanentWidget(self.lbl_coords)

        self.setStatusBar(status)

    # ---------- Tema ----------

    def _apply_theme(self):
        self.setStyleSheet(build_qt_stylesheet())

    # ---------- Sinyaller & ilk durum ----------

    def _connect_signals(self):
        """
        Tablar ile MainWindow arasındaki bağlantıları kur.
        """
        # Proje sekmesi proje değiştiğinde bilgi verir
        self.project_tab.projectChanged.connect(self._on_project_changed_from_tab)

        # MapPanel, eğer coordinatesChanged sinyali sunuyorsa koordinatları güncelle
        if hasattr(self.map_panel, "coordinatesChanged"):
            try:
                self.map_panel.coordinatesChanged.connect(self.set_coordinates)
            except Exception:
                # Sinyal yoksa sessizce geç
                pass

    def _init_state_from_project_tab(self):
        """
        Uygulama açıldığında ProjectDetailsTab içindeki mevcut seçili projeyi
        okuyup UI'ı ona göre senkronize eder.
        """
        pid, code = self.project_tab.get_current_project()
        if pid is None:
            return

        # StatusBar & state
        self.set_project(pid, code)

        # Diğer tabları ve haritayı aktif projeye göre doldur
        self.trenches_tab.load_trenches()
        self.finds_tab.load_finds()
        self.map_panel.refresh_map()

    # ---------- Proje değişimi ----------

    def _on_project_changed_from_tab(self, project_id: int, project_code: str):
        """
        ProjectDetailsTab'ten gelen sinyali yakalar:
        - StatusBar'ı günceller
        - Açmalar, buluntular ve haritayı yeniden yükler
        """
        code_clean = project_code or None
        self.set_project(project_id, code_clean)

        self.trenches_tab.load_trenches()
        self.finds_tab.load_finds()
        self.map_panel.refresh_map()

        self.show_message("Aktif proje değişti.")

    # ---------- Loading bar yönetimi ----------

    def show_loading(self, message: str = "") -> None:
        """Herhangi bir uzun işlem başlamadan önce çağrılır."""
        if message:
            self.loading_bar.set_message(message)
        self.loading_bar.set_range(0, 0)  # belirsiz başlangıç
        self.loading_bar.set_value(0)
        self.loading_bar.show()
        QCoreApplication.processEvents()

    def update_loading(self, step: int, total: int, message: str = "") -> None:
        """
        core fonksiyonlarından gelen progress callback'leri burayı çağırır.
        """
        if total <= 0:
            total = 1
        self.loading_bar.set_range(0, total)
        self.loading_bar.set_value(step)
        if message:
            self.loading_bar.set_message(message)
        self.loading_bar.show()
        QCoreApplication.processEvents()

    def hide_loading(self) -> None:
        """İşlem bittiğinde çağrılır."""
        self.loading_bar.hide()
        self.loading_bar.set_message("")
        self.loading_bar.set_value(0)
        QCoreApplication.processEvents()

    # ---------- MainWindow'ın Görevleri (UI güncelleme) ----------

    def set_project(self, project_id: int, project_code: str | None):
        self.current_project_id = project_id
        self.current_project_code = project_code
        self.lbl_project.setText(
            f"Proje: {project_code} (ID {project_id})"
            if project_code
            else f"Proje ID: {project_id}"
        )

    def set_coordinates(self, x: float, y: float, z: float | None = None):
        """
        Harita paneli, mouse koordinatını gönderirse sağ altta gösterilir.
        """
        if z is None:
            self.lbl_coords.setText(f"X: {x:.3f}  Y: {y:.3f}")
        else:
            self.lbl_coords.setText(f"X: {x:.3f}  Y: {y:.3f}  Z: {z:.3f}")

    def show_message(self, text: str):
        """StatusBar mesaj alanını günceller."""
        self.lbl_message.setText(text)
