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
from app.ui_actions import (
    action_download_tiles,
    action_import_geotiff,
)

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

        # ------------------------------------------------------------------
        # SOL: Katman ağacı (LayerTreeWidget)
        # ------------------------------------------------------------------
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
        # Harita katmanları (GeoTIFF + tile + vector)
        self.maplayers_root = self.layers_tree.add_layer_item(
            parent_item=None,
            label="Harita Katmanları",
            layer_key="group_layers",
            visible=True,
        )

        self.layers_tree.expandAll()

        # Seçim değişince haritada odaklama
        self.layers_tree.currentItemChanged.connect(self.on_layer_item_selected)

        # Göz ikonları (visibility) değişince haritaya yansıtmak için sinyal
        self.layers_tree.layerVisibilityChanged.connect(
            self.on_layer_visibility_changed
        )

        # ------------------------------------------------------------------
        # SAĞ: WebEngine (Leaflet)
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # ÜST ARAÇ ÇUBUĞU
        # ------------------------------------------------------------------
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
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.toolbar.setMinimumHeight(32)

        # Ana layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

        # Python tarafında da saklamak istersen hazır dursun
        self._map_layers_by_id: dict[int, dict] = {}

        # İlk yükleme
        self.refresh_map()

    # ------------------ UI eventleri ------------------

    def on_offline_tiles_clicked(self):
        """Offline tile indirme akışını ui_actions üzerinden çalıştırır."""
        action_download_tiles(self.main_window)

    def on_import_geotiff_clicked(self):
        """GeoTIFF ortofoto ekleme akışını ui_actions üzerinden çalıştırır."""
        action_import_geotiff(self.main_window)

    def on_import_vector_clicked(self):
        """
        Vektör (GeoJSON / Shapefile / GPKG / KML / DXF) katmanı ekleme
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

        # Root grup tıklandıysa (Açmalar / Buluntular / Seviyeler / Harita Katmanları)
        if data is None:
            text = current.text(1) if current.text(1) else current.text(0)

            if text == "Açmalar":
                js = (
                    "if (window.applyFilter && window.focusOnAllTrenches) { "
                    "applyFilter(''); focusOnAllTrenches(); }"
                )
                self.map_view.page().runJavaScript(js)

            elif text == "Buluntular":
                js = "if (window.applyFilter) { applyFilter(''); }"
                self.map_view.page().runJavaScript(js)

            elif text == "Seviyeler":
                js = "if (window.applyFilter) { applyFilter(''); }"
                self.map_view.page().runJavaScript(js)

            # Diğer grup başlıkları için (Harita Katmanları vs.) şimdilik bir şey yapmıyoruz
            return

        # Beklenmeyen formatlara karşı koruma
        try:
            item_type, payload = data
        except Exception:
            return

        js_code = None

        if item_type == "trench":
            js_code = (
                "if (window.applyFilter && window.focusOnTrench) { "
                f"applyFilter(''); focusOnTrench({int(payload)}); }}"
            )

        elif item_type == "find":
            js_code = (
                "if (window.applyFilter && window.focusOnFind) { "
                f"applyFilter(''); focusOnFind({int(payload)}); }}"
            )

        elif item_type == "level":
            level_name = payload
            escaped = json.dumps(level_name)
            js_code = "if (window.applyFilter) { " f"applyFilter({escaped}); }}"

        if js_code:
            # Fazladan '}' hatasını engellemek için düzelt
            js_code = js_code.replace("); }}", "); }")
            self.map_view.page().runJavaScript(js_code)

    def on_layer_visibility_changed(self, layer_key: str, visible: bool):
        """
        Photoshop mantığı: Soldaki göz ikonları değişince çağrılır.
        Buradan Leaflet tarafına "şu layer grubu / layer görünür/gizli" sinyali gönderiyoruz.
        Örnek:
          - group_trenches
          - trench_5
          - overlay_3
          - group_layers
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

        trenches_data = md.trenches
        finds_data = md.finds
        layers_data = md.layers
        center_lat = md.center_lat
        center_lon = md.center_lon
        error_message = md.error_message or ""

        # --------------------------------------------------
        # SOL AĞAÇ (Açmalar / Buluntular / Seviyeler)
        # --------------------------------------------------
        # Eski çocukları temizle
        self.trenches_root.takeChildren()
        self.finds_root.takeChildren()
        self.levels_root.takeChildren()
        self.maplayers_root.takeChildren()

        trenches_by_id: dict[int, dict] = {t["id"]: t for t in trenches_data}

        # --- Açmalar ---
        for t in trenches_data:
            label = t["code"]
            if t.get("name"):
                label += f" – {t['name']}"
            item = self.layers_tree.add_layer_item(
                parent_item=self.trenches_root,
                label=label,
                layer_key=f"trench_{t['id']}",
                visible=True,
            )
            item.setData(0, MAP_ROLE, ("trench", t["id"]))

        # --- Buluntular → açmalara göre grupla ---
        finds_by_trench: dict[int, list[dict]] = {}
        for f in finds_data:
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
        for f in finds_data:
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

        # --- Harita katmanları (tile + image + vector) ---
        self._map_layers_by_id.clear()
        for l in layers_data:
            lid = l.get("id")
            lname = l.get("name", f"Katman {lid}")
            kind = l.get("kind", "layer")

            label = lname
            if kind == "tile":
                label += " (Tile)"
            elif kind == "image":
                label += " (Görüntü)"
            elif kind == "vector":
                label += " (Vektör)"

            item = self.layers_tree.add_layer_item(
                parent_item=self.maplayers_root,
                label=label,
                layer_key=f"overlay_{lid}",
                visible=True,
            )
            # Şimdilik payload’a sadece id koyuyoruz
            item.setData(0, MAP_ROLE, ("overlay", lid))
            if lid is not None:
                self._map_layers_by_id[lid] = l

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

        # JSON veriler
        trenches_json = json.dumps(trenches_data, ensure_ascii=False)
        finds_json = json.dumps(finds_data, ensure_ascii=False)
        layers_json = json.dumps(layers_data, ensure_ascii=False)

        # Eski JS’te kalan window.vectorLayers bloğu boşa hata vermesin diye:
        vector_layers = [l for l in layers_data if l.get("kind") == "vector"]
        vector_layers_json = json.dumps(vector_layers, ensure_ascii=False)

        error_msg_sanitized = (error_message or "").replace('"', '\\"')

        html = (
            template_html.replace("__THEME_CSS_VARS__", theme_vars)
            .replace("__TRENCHES_JSON__", trenches_json)
            .replace("__FINDS_JSON__", finds_json)
            .replace("__LAYERS_JSON__", layers_json)
            .replace("__VECTOR_LAYERS_JSON__", vector_layers_json)
            .replace("__CENTER_LAT__", str(center_lat))
            .replace("__CENTER_LON__", str(center_lon))
            .replace("__ERROR_MSG__", error_msg_sanitized)
        )

        base_url = QUrl.fromLocalFile(str(WEB_DIR) + os.sep)
        self.map_view.setHtml(html, base_url)
