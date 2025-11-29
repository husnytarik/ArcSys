# app/map_panel.py
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from core.map_data import load_map_data, MapData
from core.utils import WEB_DIR


class MapPanel(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        # Sol ağaç
        self.layer_tree = QTreeWidget()
        self.layer_tree.setHeaderLabels(["Katmanlar"])

        self.trenches_root = QTreeWidgetItem(["Açmalar"])
        self.finds_root = QTreeWidgetItem(["Buluntular"])
        self.levels_root = QTreeWidgetItem(["Seviyeler"])

        self.layer_tree.addTopLevelItem(self.trenches_root)
        self.layer_tree.addTopLevelItem(self.finds_root)
        self.layer_tree.addTopLevelItem(self.levels_root)

        self.layer_tree.expandAll()

        # Sağ: WebEngine (Leaflet)
        self.map_view = QWebEngineView()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.layer_tree)
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        # Üst araçlar barı
        top_bar = QHBoxLayout()

        # Offline tile indirme
        btn_offline_tiles = QPushButton("Offline Tile İndir")
        btn_offline_tiles.clicked.connect(self.on_offline_tiles_clicked)
        top_bar.addWidget(btn_offline_tiles)

        # GeoTIFF ortofoto ekleme
        btn_import_geotiff = QPushButton("Ortofoto (GeoTIFF) Ekle")
        btn_import_geotiff.clicked.connect(self.on_import_geotiff_clicked)
        top_bar.addWidget(btn_import_geotiff)

        top_bar.addStretch()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(top_bar)
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

        self.layer_tree.currentItemChanged.connect(self.on_layer_item_selected)

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
                "Offline tile indirme fonksiyonu ana pencerede tanımlı değil.",
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

    def on_layer_item_selected(self, current, previous):
        if current is None:
            return

        data = current.data(0, Qt.ItemDataRole.UserRole)

        if data is None:
            text = current.text(0)
            if text == "Açmalar":
                self.map_view.page().runJavaScript(
                    "applyFilter(''); focusOnAllTrenches();"
                )
            elif text == "Buluntular":
                self.map_view.page().runJavaScript("applyFilter('buluntular');")
            elif text == "Seviyeler":
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

    # ------------------ Harita yenileme ------------------

    def refresh_map(self):
        md: MapData = load_map_data()

        # Sol ağaç doldur
        self.trenches_root.takeChildren()
        self.finds_root.takeChildren()
        self.levels_root.takeChildren()

        trenches_by_id: dict[int, dict] = {t["id"]: t for t in md.trenches}

        # Açmalar
        for t in md.trenches:
            label = t["code"]
            if t.get("name"):
                label += f" – {t['name']}"
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, ("trench", t["id"]))
            self.trenches_root.addChild(item)

        # Buluntular → açmalara göre grupla
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

            trench_item = QTreeWidgetItem([tlabel])
            trench_item.setData(0, Qt.ItemDataRole.UserRole, ("trench", trench_id))
            self.finds_root.addChild(trench_item)

            for f in flist:
                label = f"{f['code']}"
                if f.get("description"):
                    label += f" – {f['description'][:30]}"
                find_item = QTreeWidgetItem([label])
                find_item.setData(0, Qt.ItemDataRole.UserRole, ("find", f["id"]))
                trench_item.addChild(find_item)

        # Seviyeler
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
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, ("level", info["name"]))
            self.levels_root.addChild(item)

        self.layer_tree.expandAll()

        # HTML template yükle
        template_path = WEB_DIR / "map_template.html"
        template_html = template_path.read_text(encoding="utf-8")

        html = (
            template_html.replace("__TRENCHES_JSON__", json.dumps(md.trenches))
            .replace("__FINDS_JSON__", json.dumps(md.finds))
            .replace("__LAYERS_JSON__", json.dumps(md.layers))
            .replace("__CENTER_LAT__", str(md.center_lat))
            .replace("__CENTER_LON__", str(md.center_lon))
            .replace("__ERROR_MSG__", md.error_message.replace('"', '\\"'))
        )

        base_url = QUrl.fromLocalFile(str(WEB_DIR) + os.sep)
        self.map_view.setHtml(html, base_url)
