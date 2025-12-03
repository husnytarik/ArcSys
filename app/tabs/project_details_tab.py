from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QComboBox,
    QTextEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QDialog,
)

from core.db import (
    get_connection,
    get_active_project_id,
    set_active_project_id,
    execute_and_get_id,
    execute,
    fetch_one,
    fetch_all,
)

from app.dialogs.project_edit_dialog import ProjectEditDialog


class ProjectDetailsTab(QWidget):

    projectChanged = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # -----------------------------
        # ÜST ARAÇ ÇUBUĞU
        # -----------------------------
        toolbar = QHBoxLayout()

        self.btn_new = QPushButton("Yeni Proje +")
        self.btn_new.clicked.connect(self.on_new_project)

        toolbar.addWidget(self.btn_new)
        toolbar.addStretch()

        # -----------------------------
        # PROJE SEÇİMİ
        # -----------------------------
        self.project_combo = QComboBox()
        self.project_combo.setObjectName("ProjectCombo")

        # -----------------------------
        # BİLGİ PANELİ + SAĞ ÜSTTE DÜZENLE
        # -----------------------------
        self.project_info = QTextEdit()
        self.project_info.setReadOnly(True)

        self.btn_edit = QPushButton("Düzenle")
        self.btn_edit.setObjectName("ProjectEditButton")

        info_header_layout = QHBoxLayout()
        info_header_label = QLabel("Proje Bilgileri")
        info_header_layout.addWidget(info_header_label)
        info_header_layout.addStretch()
        info_header_layout.addWidget(self.btn_edit)

        layout = QVBoxLayout()
        layout.addLayout(toolbar)
        layout.addWidget(QLabel("Aktif Proje:"))
        layout.addWidget(self.project_combo)
        layout.addLayout(info_header_layout)
        layout.addWidget(self.project_info)
        self.setLayout(layout)

        self.projects: dict[int, tuple] = {}

        self.btn_edit.clicked.connect(self.on_edit_project)
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)

        self.load_projects()

    # ------------------------------------------------------------------
    # PROJELERİ YÜKLE
    # ------------------------------------------------------------------
    def load_projects(self) -> None:
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
                  p.center_x,
                  p.center_y,
                  p.center_z,
                  p.coordinate_system_id,
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
                center_x,
                center_y,
                center_z,
                cs_id,
                crs_name,
                epsg_code,
            ) = row

            self.projects[pid] = row
            label = f"{code or pid} – {name}"
            self.project_combo.addItem(label, pid)

            if active_id is None:
                active_id = pid

        if active_id is not None:
            set_active_project_id(active_id)
            idx = self.project_combo.findData(active_id)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)

        self.project_combo.blockSignals(False)
        self.refresh_project_info()

    # ------------------------------------------------------------------
    # COMBO CHANGE
    # ------------------------------------------------------------------
    def on_project_changed(self, index: int) -> None:
        pid = self.project_combo.itemData(index)
        if pid is None:
            self.project_info.setPlainText("Seçili proje yok.")
            return

        pid = int(pid)
        set_active_project_id(pid)
        self.refresh_project_info()

        row = self.projects.get(pid)
        code = row[2] if row else None
        self.projectChanged.emit(pid, code or "")

    # ------------------------------------------------------------------
    # BİLGİ PANELİ GÜNCELLE
    # ------------------------------------------------------------------
    def refresh_project_info(self) -> None:
        pid = self.project_combo.currentData()
        if pid is None:
            self.project_info.setPlainText("Seçili proje yok.")
            return

        pid = int(pid)
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
            center_x,
            center_y,
            center_z,
            cs_id,
            crs_name,
            epsg_code,
        ) = row

        crs_line = (
            f"{crs_name} (EPSG:{epsg_code})"
            if crs_name and epsg_code is not None
            else "(tanımlı değil)"
        )

        center_line = (
            f"X: {center_x}, Y: {center_y}, Z: {center_z}"
            if center_x is not None and center_y is not None and center_z is not None
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
            f"Merkez Koordinat: {center_line}",
            f"Koordinat Sistemi: {crs_line}",
            "",
            "Açıklama:",
            desc or "-",
        ]
        self.project_info.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    # AKTİF PROJE (MainWindow için)
    # ------------------------------------------------------------------
    def get_current_project(self):
        """
        Aktif seçili projeyi (id, code) olarak döner.
        Seçim yoksa (None, "") döner.
        """
        pid = self.project_combo.currentData()
        if pid is None:
            return None, ""

        pid = int(pid)
        row = self.projects.get(pid)
        code = ""
        if row:
            code = row[2] or ""
        return pid, code

    # ------------------------------------------------------------------
    # YARDIMCILAR
    # ------------------------------------------------------------------
    def _parse_float(self, s: str):
        if not s:
            return None
        s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def _load_crs_options(self) -> list[tuple[int, str]]:
        """
        coordinate_systems tablosundan seçenekleri yükler.
        (id, "Ad (EPSG:xxxx)") şeklinde döner.
        """
        rows = fetch_all(
            "SELECT id, name, epsg_code FROM coordinate_systems ORDER BY id"
        )
        options: list[tuple[int, str]] = []
        for r in rows:
            cid = int(r["id"])
            name = r["name"]
            epsg = r["epsg_code"]
            if name and epsg is not None:
                label = f"{name} (EPSG:{epsg})"
            elif epsg is not None:
                label = f"EPSG:{epsg}"
            else:
                label = f"ID {cid}"
            options.append((cid, label))
        return options

    # ------------------------------------------------------------------
    # YENİ PROJE
    # ------------------------------------------------------------------
    def on_new_project(self):
        crs_options = self._load_crs_options()
        dlg = ProjectEditDialog(parent=self, crs_options=crs_options)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                name,
                code,
                desc,
                start,
                end,
                cx,
                cy,
                cz,
                crs_id,
            ) = dlg.get_data()

            center_x = self._parse_float(cx)
            center_y = self._parse_float(cy)
            center_z = self._parse_float(cz)

            pid = execute_and_get_id(
                """
                INSERT INTO projects
                  (name, code, description, start_date, end_date,
                   center_x, center_y, center_z, coordinate_system_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    code,
                    desc,
                    start,
                    end,
                    center_x,
                    center_y,
                    center_z,
                    crs_id,
                ),
            )

            self.load_projects()
            QMessageBox.information(self, "Başarılı", "Yeni proje oluşturuldu.")

    # ------------------------------------------------------------------
    # PROJE DÜZENLE
    # ------------------------------------------------------------------
    def on_edit_project(self):
        pid = self.project_combo.currentData()
        if pid is None:
            return

        row = self.projects.get(pid)
        if not row:
            return

        (
            pid,
            name,
            code,
            desc,
            start_date,
            end_date,
            center_x,
            center_y,
            center_z,
            cs_id,
            crs_name,
            epsg_code,
        ) = row

        crs_options = self._load_crs_options()

        dlg = ProjectEditDialog(
            parent=self,
            name=name,
            code=code,
            desc=desc,
            start=start_date,
            end=end_date,
            center_x=center_x,
            center_y=center_y,
            center_z=center_z,
            crs_options=crs_options,
            selected_crs_id=cs_id,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                new_name,
                new_code,
                new_desc,
                new_start,
                new_end,
                cx,
                cy,
                cz,
                new_cs_id,
            ) = dlg.get_data()

            center_x = self._parse_float(cx)
            center_y = self._parse_float(cy)
            center_z = self._parse_float(cz)

            execute(
                """
                UPDATE projects
                SET
                  name = ?,
                  code = ?,
                  description = ?,
                  start_date = ?,
                  end_date = ?,
                  center_x = ?,
                  center_y = ?,
                  center_z = ?,
                  coordinate_system_id = ?
                WHERE id = ?
                """,
                (
                    new_name,
                    new_code,
                    new_desc,
                    new_start,
                    new_end,
                    center_x,
                    center_y,
                    center_z,
                    new_cs_id,
                    pid,
                ),
            )

            self.load_projects()
            QMessageBox.information(self, "Güncellendi", "Proje bilgileri güncellendi.")
