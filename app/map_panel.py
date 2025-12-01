# app/map_panel.py
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

from core.map_data import load_map_data, MapData
from core.theme import build_map_css_vars

from app.layer_tree import LayerTreeWidget

# Haritada kullanacağımız payload için ayrı bir rol:
MAP_ROLE = Qt.ItemDataRole.UserRole + 1

# Bu dosyanın konumuna göre web klasörünü bulalım
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
MAP_TEMPLATE_PATH = WEB_DIR / "map_template.html"


class MapPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        # Map panel QSS için isim
        self.setObjectName("MapPanel")

        # ---------------------------
        # SOL: Katman ağacı (LayerTreeWidget)
        # ---------------------------
        self.layers_tree = LayerTreeWidget(self)
        self.layers_tree.setObjectName("MapLayersTree")

        # Kök gruplar – Photoshop mantığında "grup layer" gibi
        self.trenches_root = self.layers_tree.add_layer_item(
            parent_item=None,
            label="Açmalar",
            layer_key="group_trenches",
            visible=True,
        )
        self.finds_root = self.layers_tree.add_layer_item(
            parent_item=None,
            label="Buluntular",
            layer_key="group_finds",
            visible=True,
        )
        self.levels_root = self.layers_tree.add_layer_item(
            parent_item=None,
            label="Seviyeler",
            layer_key="group_levels",
            visible=True,
        )

        self.layers_tree.expandAll()

        # Seçim değişince haritada odaklama
        self.layers_tree.currentItemChanged.connect(self.on_layer_item_selected)

        # Göz ikonları (visibility) değişince haritaya yansıtmak için sinyal
        self.layers_tree.layerVisibilityChanged.connect(
            self.on_layer_visibility_changed
        )

        # ---------------------------
        # SAĞ: WebEngine (Leaflet)
        # ---------------------------
        self.map_view = QWebEngineView()
        self.map_view.setObjectName("MapWebView")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MapSplitter")
        splitter.addWidget(self.layers_tree)
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        # Soldaki paneli biraz daha geniş başlat
        splitter.setSizes([320, 880])

        # ---------------------------
        # ÜST ARAÇ ÇUBUĞU (tamamen temadan boyansın)
        # ---------------------------
        self.toolbar = QWidget()
        self.toolbar.setObjectName("MapToolbar")

        top_bar = QHBoxLayout(self.toolbar)
        top_bar.setContentsMargins(4, 4, 4, 4)
        top_bar.setSpacing(6)

        # Offline tile indirme
        self.btn_offline_tiles = QPushButton("Çevrimdışı Harita Ekle")
        self.btn_offline_tiles.setObjectName("MapToolbarButtonOffline")
        self.btn_offline_tiles.clicked.connect(self.on_offline_tiles_clicked)
        top_bar.addWidget(self.btn_offline_tiles)

        # Vektör katman ekleme
        self.btn_import_vector = QPushButton("Vektör Katman Ekle")
        self.btn_import_vector.setObjectName("MapToolbarButtonVector")
        self.btn_import_vector.clicked.connect(self.on_import_vector_clicked)
        top_bar.addWidget(self.btn_import_vector)

        # GeoTIFF ortofoto ekleme
        self.btn_import_geotiff = QPushButton("Ortofoto (GeoTIFF) Ekle")
        self.btn_import_geotiff.setObjectName("MapToolbarButtonGeotiff")
        self.btn_import_geotiff.clicked.connect(self.on_import_geotiff_clicked)
        top_bar.addWidget(self.btn_import_geotiff)

        top_bar.addStretch()

        # Toolbar yüksekliği sabit kalsın
        self.toolbar.setSizePolicy(
            QSizePolicy.Policy.Expanding,  # yatayda esnek
            QSizePolicy.Policy.Fixed,  # dikeyde sabit
        )
        self.toolbar.setMinimumHeight(32)

        # Ana layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

        # İlk yükleme
        self.refresh_map()

    # ------------------ UI eventleri ------------------

    def on_offline_tiles_clicked(self):
        """Offline tile indirme akışını ana pencereden çalıştırır."""
        if hasattr(self.main_window, "download_offline_tiles_ui"):
            self.main_window.download_offline_tiles_ui()
        else:
            QMessageBox.warning(
                self,
                "Eksik Özellik",
                "Çevrimdışı harita indirme fonksiyonu ana pencerede tanımlı değil.",
            )

    def on_import_geotiff_clicked(self):
        """GeoTIFF ortofoto ekleme akışını ana pencereden çalıştırır."""
        if hasattr(self.main_window, "import_geotiff_orthophoto"):
            self.main_window.import_geotiff_orthophoto()
        else:
            QMessageBox.warning(
                self,
                "Eksik Özellik",
                "GeoTIFF içe aktarma fonksiyonu ana pencerede tanımlı değil.",
            )

    def on_import_vector_clicked(self):
        """
        Vektör (ör. GeoJSON / Shapefile / GPKG / KML / DXF) katmanı ekleme
        akışını ana pencereden çalıştırır.
        """
        if hasattr(self.main_window, "import_vector_layer"):
            self.main_window.import_vector_layer()
        else:
            QMessageBox.warning(
                self,
                "Eksik Özellik",
                "Vektör veri içe aktarma fonksiyonu ana pencerede tanımlı değil.",
            )

    def on_layer_item_selected(self, current, previous):
        """Soldaki ağaçta seçim değişince haritayı odakla / filtrele."""
        if current is None:
            return

        # Harita payload'ını MAP_ROLE'den okuyoruz
        data = current.data(0, MAP_ROLE)

        if data is None:
            # Root grup tıklandı (Açmalar / Buluntular / Seviyeler)
            text = current.text(1) if current.text(1) else current.text(0)
            if text == "Açmalar":
                self.map_view.page().runJavaScript(
                    "applyFilter(''); focusOnAllTrenches();"
                )
            elif text == "Buluntular":
                self.map_view.page().runJavaScript("applyFilter('buluntular');")
            elif text == "Seviyeler":
                # Şimdilik özel bir odak yok; istersen buraya z-range odak ekleriz.
                pass
            return

        item_type, payload = data

        if item_type == "trench":
            js_code = f"applyFilter(''); focusOnTrench({int(payload)});"
            self.map_view.page().runJavaScript(js_code)

        elif item_type == "find":
            js_code = f"applyFilter(''); focusOnFind({int(payload)});"
            self.map_view.page().runJavaScript(js_code)

        elif item_type == "level":
            level_name = payload
            escaped = json.dumps(level_name)
            js_code = f"applyFilter({escaped});"
            self.map_view.page().runJavaScript(js_code)

    def on_layer_visibility_changed(self, layer_key: str, visible: bool):
        """
        Photoshop mantığı: Soldaki göz ikonları değişince çağrılır.
        Buradan Leaflet tarafına "şu layer grubu görünür/gizli" sinyali gönderebiliriz.
        """
        js = (
            "if (window.setLayerVisibilityFromQt) "
            f"setLayerVisibilityFromQt({json.dumps(layer_key)}, {str(visible).lower()});"
        )
        self.map_view.page().runJavaScript(js)

    # ------------------ Harita yenileme ------------------

    def refresh_map(self) -> None:
        """Aktif proje için verileri yükler, sol ağaç panelini ve haritayı yeniler."""
        md: MapData = load_map_data()

        # --------------------------------------------------
        # SOL AĞAÇ (Açmalar / Buluntular / Seviyeler)
        # --------------------------------------------------
        # Eski çocukları temizle
        self.trenches_root.takeChildren()
        self.finds_root.takeChildren()
        self.levels_root.takeChildren()

        trenches_by_id: dict[int, dict] = {t["id"]: t for t in md.trenches}

        # --- Açmalar ---
        for t in md.trenches:
            label = t["code"]
            if t.get("name"):
                label += f" – {t['name']}"
            item = self.layers_tree.add_layer_item(
                parent_item=self.trenches_root,
                label=label,
                layer_key=f"trench_{t['id']}",
                visible=True,
            )
            # Haritada kullanacağımız payload:
            item.setData(0, MAP_ROLE, ("trench", t["id"]))

        # --- Buluntular → açmalara göre grupla ---
        finds_by_trench: dict[int, list[dict]] = {}
        for f in md.finds:
            finds_by_trench.setdefault(f["trench_id"], []).append(f)

        for trench_id, flist in finds_by_trench.items():
            tinfo = trenches_by_id.get(trench_id)
            if tinfo:
                tlabel = tinfo["code"]
                if tinfo.get("name"):
                    tlabel += f" – {tinfo['name']}"
            else:
                tlabel = f"Açma {trench_id}"

            trench_item = self.layers_tree.add_layer_item(
                parent_item=self.finds_root,
                label=tlabel,
                layer_key=f"finds_trench_{trench_id}",
                visible=True,
            )
            trench_item.setData(0, MAP_ROLE, ("trench", trench_id))

            for f in flist:
                label = f"{f['code']}"
                if f.get("description"):
                    label += f" – {f['description'][:30]}"
                find_item = self.layers_tree.add_layer_item(
                    parent_item=trench_item,
                    label=label,
                    layer_key=f"find_{f['id']}",
                    visible=True,
                )
                find_item.setData(0, MAP_ROLE, ("find", f["id"]))

        # --- Seviyeler ---
        levels_map: dict[int, dict] = {}
        for f in md.finds:
            lid = f["level_id"]
            lname = f["level_name"]
            if lid is None or lname is None:
                continue
            if lid not in levels_map:
                levels_map[lid] = {"name": lname, "trenches": set()}
            levels_map[lid]["trenches"].add(f["trench_code"])

        for lid, info in levels_map.items():
            t_codes = ", ".join(sorted(info["trenches"]))
            label = info["name"]
            if t_codes:
                label += f" – Açmalar: {t_codes}"
            item = self.layers_tree.add_layer_item(
                parent_item=self.levels_root,
                label=label,
                layer_key=f"level_{lid}",
                visible=True,
            )
            item.setData(0, MAP_ROLE, ("level", info["name"]))

        self.layers_tree.expandAll()

        # --------------------------------------------------
        # HTML TEMPLATE YÜKLE VE PLACEHOLDER'LARI DOLDUR
        # --------------------------------------------------
        try:
            with open(MAP_TEMPLATE_PATH, "r", encoding="utf-8") as f:
                template_html = f.read()
        except OSError as e:
            QMessageBox.critical(
                self,
                "Şablon Hatası",
                f"Harita HTML şablonu açılamadı:\n{e}",
            )
            return

        # Tema değişkenleri (:root içindeki CSS var'lar)
        theme_vars = build_map_css_vars()

        # JSON veriler (bunlar map_template.html'deki şu satıra gidiyor:
        # const trenchesData = __TRENCHES_JSON__; vs.)
        trenches_json = json.dumps(md.trenches, ensure_ascii=False)
        finds_json = json.dumps(md.finds, ensure_ascii=False)
        layers_json = json.dumps(md.layers, ensure_ascii=False)
        error_msg_sanitized = (md.error_message or "").replace('"', '\\"')

        # Placeholder doldurma
        html = (
            template_html.replace("__THEME_CSS_VARS__", theme_vars)
            .replace("__TRENCHES_JSON__", trenches_json)
            .replace("__FINDS_JSON__", finds_json)
            .replace("__LAYERS_JSON__", layers_json)
            .replace("__CENTER_LAT__", str(md.center_lat))
            .replace("__CENTER_LON__", str(md.center_lon))
            .replace("__ERROR_MSG__", error_msg_sanitized)
        )

        # HTML’i QWebEngineView’e bas
        base_url = QUrl.fromLocalFile(str(WEB_DIR) + os.sep)
        self.map_view.setHtml(html, base_url)
