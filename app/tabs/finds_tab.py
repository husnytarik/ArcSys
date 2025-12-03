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


class FindsTab(QWidget):
    """
    Buluntular sekmesi:
    - Solda: buluntu listesi (kod + kısa açıklama + açma + seviye)
    - Sağda: seçilen buluntunun detay yazısı
    - Çift tıklayınca haritada focusOnFind(find_id)
    """

    def __init__(self, map_panel: "MapPanel", parent=None):
        super().__init__(parent)

        self.map_panel = map_panel

        self.finds_list = QListWidget()
        self.find_detail = QTextEdit()
        self.find_detail.setReadOnly(True)
        self.find_detail.setPlaceholderText(
            "Seçilen buluntunun detayları burada görünecek..."
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.finds_list)
        splitter.addWidget(self.find_detail)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self.finds_by_id: dict[int, tuple] = {}
        self.load_finds()

        self.finds_list.currentItemChanged.connect(self.on_find_selected)
        self.finds_list.itemDoubleClicked.connect(self.on_find_double_clicked)

    # ------------------------------------------------------------------ #
    # Buluntuları yükleme
    # ------------------------------------------------------------------ #
    def load_finds(self) -> None:
        """Aktif projeye ait buluntuları, açma ve seviye bilgisiyle birlikte yükler."""
        self.finds_list.clear()
        self.finds_by_id.clear()

        project_id = get_active_project_id()
        if project_id is None:
            self.find_detail.setPlainText("Aktif proje bulunamadı.")
            return

        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute(
                """
                SELECT
                  f.id,
                  f.trench_id,
                  f.code,
                  f.description,
                  f.x_global,
                  f.y_global,
                  f.z_global,
                  f.level_id,
                  l.name AS level_name,
                  t.code AS trench_code,
                  t.name AS trench_name
                FROM finds f
                JOIN trenches t ON f.trench_id = t.id
                LEFT JOIN levels l ON f.level_id = l.id
                WHERE t.project_id = ?
                ORDER BY f.id
                """,
                (project_id,),
            )
            rows = cur.fetchall()
            con.close()
        except Exception as e:
            self.find_detail.setPlainText(f"Buluntular yüklenirken hata: {e}")
            return

        for row in rows:
            (
                fid,
                trench_id,
                code,
                desc,
                xg,
                yg,
                zg,
                level_id,
                level_name,
                trench_code,
                trench_name,
            ) = row

            label_parts = [code]
            if trench_code:
                label_parts.append(f"[{trench_code}]")
            if level_name:
                label_parts.append(f"({level_name})")
            if desc:
                label_parts.append(f"- {desc[:40]}")
            label = " ".join(label_parts)

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, fid)
            self.finds_list.addItem(item)

            self.finds_by_id[fid] = row

        if rows:
            self.finds_list.setCurrentRow(0)
        else:
            self.find_detail.setPlainText("Bu projeye ait buluntu bulunamadı.")

    # ------------------------------------------------------------------ #
    # Seçim / detay
    # ------------------------------------------------------------------ #
    def on_find_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Listeden bir buluntu seçilince sağdaki detay panelini doldurur."""
        if current is None:
            self.find_detail.clear()
            return

        fid = current.data(Qt.ItemDataRole.UserRole)
        row = self.finds_by_id.get(fid)
        if not row:
            self.find_detail.setPlainText("Buluntu detayları bulunamadı.")
            return

        (
            fid,
            trench_id,
            code,
            desc,
            xg,
            yg,
            zg,
            level_id,
            level_name,
            trench_code,
            trench_name,
        ) = row

        detail_lines = [
            f"ID: {fid}",
            f"Buluntu kodu: {code}",
            "",
            f"Açma: {trench_code or trench_id}"
            + (f" – {trench_name}" if trench_name else ""),
            f"Seviye: {level_name or '-'}",
            "",
            f"X (global): {xg if xg is not None else '-'}",
            f"Y (global): {yg if yg is not None else '-'}",
            f"Z (global): {zg if zg is not None else '-'}",
            "",
            "Açıklama:",
            desc or "-",
        ]
        self.find_detail.setPlainText("\n".join(detail_lines))

    # ------------------------------------------------------------------ #
    # Harita odaklama
    # ------------------------------------------------------------------ #
    def on_find_double_clicked(self, item: QListWidgetItem):
        """Buluntuya çift tıklanınca haritada o buluntuya odaklan."""
        if item is None:
            return

        fid = item.data(Qt.ItemDataRole.UserRole)
        if fid is None:
            return

        try:
            if self.map_panel and self.map_panel.map_view:
                js_code = f"focusOnFind({int(fid)});"
                self.map_panel.map_view.page().runJavaScript(js_code)
        except Exception as e:
            print("Haritada buluntuya odaklanırken hata:", e)
