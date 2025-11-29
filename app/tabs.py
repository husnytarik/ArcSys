# app/tabs.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QSplitter,
    QComboBox,
)

# Sadece type checking sırasında import et, runtime'da import döngüsü olmasın
if TYPE_CHECKING:
    from app.map_panel import MapPanel

from core.db import get_connection, get_active_project_id, set_active_project_id


# =========================
#  SEKME: PROJE DETAYLARI
# =========================


class ProjectDetailsTab(QWidget):
    """
    Proje Detayları sekmesi:
    - Üstte: Proje seçimi için combo box
    - Altta: Seçilen projenin detay bilgileri
    Proje değiştiğinde projectChanged(project_id) sinyali yayar.
    """

    projectChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project_combo = QComboBox()
        self.project_info = QTextEdit()
        self.project_info.setReadOnly(True)
        self.project_info.setPlaceholderText(
            "Seçilen projenin adı, açıklaması, tarihleri ve koordinat sistemi burada görünecek..."
        )

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Aktif Proje:"))
        layout.addWidget(self.project_combo)
        layout.addWidget(self.project_info)
        self.setLayout(layout)

        self.projects: dict[int, tuple] = {}  # id -> row
        self.load_projects()

        # Proje seçimi değişince kendi sinyalini emit edecek
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)

    def load_projects(self) -> None:
        """Veritabanından projeleri yükler ve combo'ya doldurur."""
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.projects.clear()

        try:
            con = get_connection()
            cur = con.cursor()
            cur.execute(
                """
                SELECT
                  p.id,
                  p.name,
                  p.code,
                  p.description,
                  p.start_date,
                  p.end_date,
                  cs.name AS crs_name,
                  cs.epsg_code
                FROM projects p
                LEFT JOIN coordinate_systems cs
                  ON p.coordinate_system_id = cs.id
                ORDER BY p.id
                """
            )
            rows = cur.fetchall()
            con.close()
        except Exception as e:
            self.project_info.setPlainText(f"Projeler yüklenirken hata: {e}")
            self.project_combo.blockSignals(False)
            return

        active_id = get_active_project_id()

        for row in rows:
            (
                pid,
                name,
                code,
                desc,
                start_date,
                end_date,
                crs_name,
                epsg_code,
            ) = row

            self.projects[pid] = row
            label = f"{code or pid} – {name}"
            self.project_combo.addItem(label, pid)

            if active_id is None:
                active_id = pid

        # Aktif projeyi ayarla
        if active_id is not None:
            set_active_project_id(active_id)
            index = self.project_combo.findData(active_id)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)

        self.project_combo.blockSignals(False)
        self.refresh_project_info()

    def on_project_changed(self, index: int) -> None:
        """
        ComboBox değiştiğinde:
        - aktif proje ID'sini günceller
        - info panelini tazeler
        - projectChanged sinyali yayar (MainWindow bunu dinliyor)
        """
        pid = self.project_combo.itemData(index)
        if pid is None:
            set_active_project_id(None)
            self.project_info.setPlainText("Seçili proje yok.")
            return

        set_active_project_id(pid)
        self.refresh_project_info()
        self.projectChanged.emit(int(pid))

    def refresh_project_info(self) -> None:
        """Seçili projeyi ayrıntılı olarak gösterir."""
        pid = self.project_combo.currentData()
        if pid is None:
            self.project_info.setPlainText("Seçili proje yok.")
            return

        row = self.projects.get(pid)
        if not row:
            self.project_info.setPlainText("Proje bilgisi bulunamadı.")
            return

        (
            pid,
            name,
            code,
            desc,
            start_date,
            end_date,
            crs_name,
            epsg_code,
        ) = row

        crs_line = (
            f"{crs_name} (EPSG:{epsg_code})"
            if crs_name and epsg_code is not None
            else "(tanımlı değil)"
        )

        lines = [
            f"ID: {pid}",
            f"Ad: {name}",
            f"Kod: {code or '-'}",
            "",
            f"Başlangıç: {start_date or '-'}",
            f"Bitiş: {end_date or '-'}",
            "",
            f"Koordinat Sistemi: {crs_line}",
            "",
            "Açıklama:",
            desc or "-",
        ]
        self.project_info.setPlainText("\n".join(lines))


# =========================
#  SEKME: AÇMALAR
# =========================


class TrenchesTab(QWidget):
    """
    Açmalar sekmesi:
    - Solda açma listesi (trenches + projects + levels)
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

        # Köşe noktaları: sadece GLOBAL koordinatlar
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


# =========================
#  SEKME: BULUNTULAR
# =========================


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


# =========================
#  SEKME: RAPORLAR (dummy)
# =========================


class ReportsTab(QWidget):
    """
    Raporlar sekmesi:
    Şimdilik sadece iskelet.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.group_list = QListWidget()
        self.group_list.addItems(
            [
                "Açma T1 – Günlük Raporlar (dummy)",
                "Açma T2 – Günlük Raporlar (dummy)",
            ]
        )

        self.report_list = QListWidget()
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText(
            "Rapor içeriği (ileride DB'den yüklenecek)..."
        )

        splitter_main = QSplitter(Qt.Orientation.Horizontal)
        splitter_main.addWidget(self.group_list)
        splitter_main.addWidget(self.report_list)
        splitter_main.addWidget(self.report_view)
        splitter_main.setStretchFactor(0, 1)
        splitter_main.setStretchFactor(1, 1)
        splitter_main.setStretchFactor(2, 3)

        layout = QVBoxLayout()
        layout.addWidget(splitter_main)
        self.setLayout(layout)

        self.group_list.currentTextChanged.connect(self.on_group_selected)
        self.report_list.currentTextChanged.connect(self.on_report_selected)

    def on_group_selected(self, group_name: str) -> None:
        self.report_list.clear()
        if not group_name:
            return

        self.report_list.addItems(
            [
                f"{group_name} – Rapor 1 (dummy)",
                f"{group_name} – Rapor 2 (dummy)",
            ]
        )

    def on_report_selected(self, report_title: str) -> None:
        if not report_title:
            self.report_view.clear()
            return

        self.report_view.setPlainText(
            f"{report_title}\n\n"
            "Bu alan ileride veritabanından çekilen rapor metni ile dolacak.\n"
            "Şu an sadece iskelet hazır."
        )
