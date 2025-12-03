from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QSplitter,
)

from core.db import get_connection, get_active_project_id

if TYPE_CHECKING:
    from app.map_panel import MapPanel


class TrenchesTab(QWidget):
    """
    Açmalar sekmesi:
    - Solda açma listesi
    - Sağda açmanın açıklaması + GLOBAL köşe koordinatları (X,Y,Z)
    - Bir açmaya çift tıklayınca haritada o açmaya odaklanır.
    """

    def __init__(self, map_panel: "MapPanel", parent=None):
        super().__init__(parent)

        self.map_panel = map_panel

        self.trench_list = QListWidget()
        self.trench_detail = QTextEdit()
        self.trench_detail.setReadOnly(True)
        self.trench_detail.setPlaceholderText(
            "Seçilen açmanın detayları (global X,Y,Z köşeleri, açıklama...)"
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.trench_list)
        splitter.addWidget(self.trench_detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.trenches_by_id: dict[int, tuple] = {}
        self.load_trenches()

        self.trench_list.currentItemChanged.connect(self.on_trench_selected)
        self.trench_list.itemDoubleClicked.connect(self.on_trench_double_clicked)

    # ------------------------------------------------------------------ #
    # Açmaları yükleme
    # ------------------------------------------------------------------ #
    def load_trenches(self) -> None:
        """Aktif projeye ait açmaları yükler."""
        self.trench_list.clear()
        self.trenches_by_id.clear()

        project_id = get_active_project_id()
        if project_id is None:
            self.trench_detail.setPlainText("Aktif proje bulunamadı.")
            return

        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute(
                """
                SELECT
                  t.id,
                  t.project_id,
                  t.code,
                  t.name,
                  t.description,
                  t.elevation_top,
                  t.elevation_bottom,
                  t.level_id,
                  t.created_at,
                  p.name AS project_name,
                  l.name AS level_name
                FROM trenches t
                JOIN projects p ON t.project_id = p.id
                LEFT JOIN levels l ON t.level_id = l.id
                WHERE t.project_id = ?
                ORDER BY t.id
                """,
                (project_id,),
            )
            rows = cur.fetchall()
            con.close()
        except Exception as e:
            self.trench_detail.setPlainText(f"Açmalar yüklenirken hata: {e}")
            return

        for row in rows:
            (
                tid,
                proj_id,
                code,
                name,
                desc,
                elev_top,
                elev_bottom,
                level_id,
                created_at,
                project_name,
                level_name,
            ) = row

            display = f"{tid} – {code} ({project_name})"
            self.trenches_by_id[tid] = row
            self.trench_list.addItem(display)

        if rows:
            self.trench_list.setCurrentRow(0)
        else:
            self.trench_detail.setPlainText("Bu projeye ait açma bulunamadı.")

    # ------------------------------------------------------------------ #
    # Seçim / detay
    # ------------------------------------------------------------------ #
    def on_trench_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current is None:
            self.trench_detail.clear()
            return

        text = current.text()
        try:
            tid_str = text.split("–", 1)[0].strip()
            tid = int(tid_str)
        except Exception:
            self.trench_detail.setPlainText("Seçilen açma ID'si çözülemedi.")
            return

        row = self.trenches_by_id.get(tid)
        if not row:
            self.trench_detail.setPlainText("Açma detayları bulunamadı.")
            return

        (
            tid,
            project_id,
            code,
            name,
            desc,
            elev_top,
            elev_bottom,
            level_id,
            created_at,
            project_name,
            level_name,
        ) = row

        # Projenin koordinat sistemini oku
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute(
                """
                SELECT cs.name, cs.epsg_code
                FROM projects p
                LEFT JOIN coordinate_systems cs
                  ON p.coordinate_system_id = cs.id
                WHERE p.id = ?
                """,
                (project_id,),
            )
            cs_row = cur.fetchone()
            con.close()
        except Exception:
            cs_row = None

        if cs_row and cs_row[0]:
            cs_name, cs_epsg = cs_row
            crs_line = f"Koordinat sistemi: {cs_name} (EPSG:{cs_epsg})"
        else:
            crs_line = "Koordinat sistemi: (tanımlı değil)"

        # Köşe noktaları: GLOBAL koordinatlar
        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute(
                """
                SELECT
                  order_index,
                  x_global,
                  y_global,
                  z_global,
                  level_id,
                  notes
                FROM trench_vertices
                WHERE trench_id = ?
                ORDER BY order_index
                """,
                (tid,),
            )
            verts = cur.fetchall()
            con.close()

            if verts:
                vertices_info_lines = []
                for v in verts:
                    order_index, xg, yg, zg, v_level_id, notes = v
                    vertices_info_lines.append(
                        f"  #{order_index}: X={xg}, Y={yg}, Z={zg}  not: {notes or '-'}"
                    )
                vertices_info = "Köşe Noktaları (global koordinat):\n" + "\n".join(
                    vertices_info_lines
                )
            else:
                vertices_info = "Köşe noktası yok."
        except Exception as e:
            vertices_info = f"Köşe noktaları okunurken hata: {e}"

        detail_lines = [
            f"ID: {tid}",
            f"Proje: {project_name} (ID: {project_id})",
            f"Kod: {code}",
            f"Ad: {name or '-'}",
            "",
            crs_line,
            "",
            f"Üst kot: {elev_top if elev_top is not None else '-'}",
            f"Alt kot: {elev_bottom if elev_bottom is not None else '-'}",
            f"Level: {level_name or '-'} (ID: {level_id or '-'})",
            "",
            "Açıklama:",
            desc or "-",
            "",
            vertices_info,
            "",
            f"Oluşturulma: {created_at or '-'}",
        ]
        self.trench_detail.setPlainText("\n".join(detail_lines))

    # ------------------------------------------------------------------ #
    # Harita odaklama
    # ------------------------------------------------------------------ #
    def on_trench_double_clicked(self, item: QListWidgetItem):
        """Açmaya çift tıklanınca haritada o açmaya odaklan."""
        if item is None:
            return

        text = item.text()
        try:
            tid_str = text.split("–", 1)[0].strip()
            tid = int(tid_str)
        except Exception:
            return

        try:
            if self.map_panel and self.map_panel.map_view:
                js_code = f"focusOnTrench({int(tid)});"
                self.map_panel.map_view.page().runJavaScript(js_code)
        except Exception as e:
            print("Haritada açmaya odaklanırken hata:", e)
